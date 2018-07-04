#!/usr/bin/env python

import base64
import json

from os.path import join as pjoin
from collections import Counter, OrderedDict


from pathlib import Path
from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_json import FlaskJSON, JsonError, as_json

from trillian_client import TrillianLogClient, TrillianAdminClient

import crypto.sigpb.sigpb_pb2


HOME_DIR = str(Path.home())

app = Flask(__name__)
FlaskJSON(app)
app.config['JSON_ADD_STATUS'] = False

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////vagrant/database.sqlite3'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config.from_object(__name__)  # load config from this file
app.config.from_envvar('FLASK_SETTINGS_FILE', silent=True)
app.config['JSON_USE_ENCODE_METHODS'] = True

DB = SQLAlchemy(app)
FlaskJSON(app)
CORS(app)


class LogEntry(DB.Model):
    id = DB.Column(DB.Integer, primary_key=True)
    raw_data = DB.Column(DB.LargeBinary)

    log_id = DB.Column(
        DB.Integer,
        DB.ForeignKey('log.id'),
        nullable=False
    )
    log = DB.relationship(
        'Log',
        backref=DB.backref('entries', lazy=True)
    )


class Log(DB.Model):
    id = DB.Column(DB.Integer, primary_key=True)
    slug = DB.Column(DB.String(200), unique=True, nullable=False)
    name = DB.Column(DB.String(200), unique=False, nullable=False)

    def __str__(self):
        return '{} [{}]'.format(self.slug, self.url)

    def __repr__(self):
        return 'Log(slug={}, url={})'.format(self.slug, self.url)

    def __json__(self):
        return OrderedDict([
            ('slug', self.slug),
            ('name', self.name),
            ('log_id', self.id),
        ])


class SignedLogRootSerializer():
    def __init__(self, signed_log_root):
        self.__slr = signed_log_root

    def json(self):
        return OrderedDict([
            ('_timestamp_nanos', self.__slr.timestamp_nanos),
            ('_root_hash', to_b64(self.__slr.root_hash)),
            ('_tree_size', self.__slr.tree_size),
            ('_tree_revision', self.__slr.tree_revision),
            ('key_hint', to_b64(self.__slr.key_hint)),
            ('log_root', to_b64(self.__slr.log_root)),
            ('log_root_signature', to_b64(self.__slr.log_root_signature)),
        ])


def make_log_client(log_id):
    return TrillianLogClient('localhost', '8090', log_id)


TRILLIAN_ADMIN = TrillianAdminClient('localhost', '8090')


@app.route('/logs')
@as_json
def log_index():

    def serialize_public_key(tree):
        hash_algorithm = {
            crypto.sigpb.sigpb_pb2.DigitallySigned.SHA256: 'SHA256',
        }.get(tree.hash_algorithm)

        signature_algorithm = {
            crypto.sigpb.sigpb_pb2.DigitallySigned.ECDSA: 'ECDSA',
        }.get(tree.signature_algorithm)

        return {
            'hash_algorithm': hash_algorithm,
            'signature_algorithm': signature_algorithm,
            'der': to_b64(tree.public_key.der),
        }

    def serialize_log_tree(log_tree):
        db_log = Log.query.filter_by(id=log_tree.tree_id).first()

        return OrderedDict([
            ('log_id', log_tree.tree_id),
            ('log_url', '{}v1beta1/logs/{}'.format(
                 request.url_root, log_tree.tree_id
                 )),
            ('public_key', serialize_public_key(log_tree)),
            ('name', db_log.name if db_log is not None else None),
            ('slug', db_log.slug if db_log is not None else None),
        ])

    return {
        'logs': map(serialize_log_tree, TRILLIAN_ADMIN.logs())
    }


def to_b64(binary):
    return base64.b64encode(binary).decode('ascii')


@app.route('/v1beta1/logs/<int:log_id>/roots:latest')
@as_json
def get_latest_signed_log_root(log_id):

    signed_log_root = make_log_client(log_id).get_signed_log_root()

    return SignedLogRootSerializer(signed_log_root).json()


@app.route('/v1beta1/logs/<int:log_id>:consistency_proof')
@as_json
def get_consistency_proof(log_id):
    try:
        first_tree_size = int(request.args['first_tree_size'])
        second_tree_size = int(request.args['second_tree_size'])
    except (KeyError, ValueError):
        raise JsonError(
            status=400,
            description='Request requires integer arguments `first_tree_size` '
                        'and `second_tree_size'
        )

    try:
        response = make_log_client(log_id).get_consistency_proof(
            first_tree_size=first_tree_size,
            second_tree_size=second_tree_size,
        )
    except ValueError as e:
        raise JsonError(
            status=400,
            description=str(e)
        )

    return {
        'proof': [to_b64(h) for h in response.proof.hashes],
        'signed_log_root': SignedLogRootSerializer(
            response.signed_log_root
        ).json(),
    }


@app.route('/v1beta1/logs/<int:log_id>/roots:latest')
@as_json
def get_leaves_by_range(log_id):
    # TODO: ensure the return value mirrors https://github.com/google/trillian/blob/5647e7fe6360890ef906a11b3b7dd2da15514762/trillian_log_api.proto#L269

    def serialize(leaf):
        return {
            'leaf_index': leaf.leaf_index,
            'leaf_value': base64.b64encode(leaf.leaf_value).decode('ascii')
        }

    entries = map(
        serialize,
        make_log_client(log_id).get_leaves_by_range(
            start_index=int(request.args['start_index']),
            count=int(request.args['count'])
        )
    )

    return {
        'entries': entries
    }


# @app.route('/api/v1/dataset/<dataset>/record/', methods=['POST'])
# @as_json
# def record_single_record(dataset):
#     assert dataset == 'reasons-for-access'  # currently only support 1
#
#     record = request.json
#
#     try:
#         validate_reasons_for_access_record(record)
#     except ValueError as e:
#         raise JsonError(description=str(e), status=400)
#
#     binary = make_normalized_json(record)
#
#     trillian = make_log_client(KNOWN_LOGS[REASONS_FOR_ACCESS])
#     trillian.queue_leaf(binary)
#     return {'message': 'OK, queued record for inclusion in merkle tree'}


def make_normalized_json(some_dict):
    ordered = OrderedDict(some_dict.items())
    return json.dumps(ordered, indent=0).encode('utf-8')


def decode_json(binary):
    return json.loads(binary.decode('utf-8'))


@app.route('/')
def view_index():
    return render_template(
        'index.html'
    )


@app.cli.command('initdb')
def initdb_command():
    DB.create_all()

    # demo_log = Log(
    #     slug='reasons-for-data-access',
    #     name='Reasons for data access',
    #     url='http://10.0.0.3:5000',
    #     publisher=dm
    # )

    # DB.session.add(dm)
    # DB.session.add(reasons_for_access)
    # DB.session.commit()

    # print('Initialized the database and added sample dataset.')
    print('Initialized database')
