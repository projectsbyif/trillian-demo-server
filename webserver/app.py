#!/usr/bin/env python

import base64
import json

from os.path import join as pjoin
from collections import Counter, OrderedDict

import grpc

from pathlib import Path
from flask import Flask, render_template, request
from flask_cors import CORS
from flask_json import FlaskJSON, JsonError, as_json

from trillian_client import TrillianLogClient, TrillianAdminClient

import crypto.sigpb.sigpb_pb2


HOME_DIR = str(Path.home())

app = Flask(__name__)
FlaskJSON(app)
app.config['JSON_ADD_STATUS'] = False

app.config.from_object(__name__)  # load config from this file
app.config.from_envvar('FLASK_SETTINGS_FILE', silent=True)
app.config['JSON_USE_ENCODE_METHODS'] = True

FlaskJSON(app)
CORS(app)


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


@app.route('/demoapi/logs', methods=['GET'])
@as_json
def log_index():
    return {
        'logs': map(serialize_log_tree, TRILLIAN_ADMIN.logs())
    }


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
    return OrderedDict([
        ('log_id', str(log_tree.tree_id)),
        ('log_url', '{}v1beta1/logs/{}'.format(
             request.url_root, log_tree.tree_id
             )),
        ('public_key', serialize_public_key(log_tree)),
        ('name', log_tree.display_name),
        ('description', log_tree.description),
    ])


@app.route('/demoapi/logs', methods=['POST'])
@as_json
def log_create():
    def validate(data):
        if not data:
            raise JsonError(
                description=(
                    'No JSON content found. Did you use '
                    '`Content-Type: application/json`'
                    )
                )
        try:
            if not isinstance(data['name'], str):
                raise JsonError(
                    description='`name` must be a string'
                )
            if not isinstance(data['description'], str):
                raise JsonError(
                    description='`description` must be a string'
                )
        except KeyError:
            raise JsonError(
                description='Must pass `name` and `description`'
            )

        return data

    data = validate(request.json)

    log_tree = TRILLIAN_ADMIN.create_log(
        display_name=data['name'],
        description=data['description']
    )

    log_client = make_log_client(log_tree.tree_id)
    log_client.init_log()

    return {
        'log': serialize_log_tree(log_tree)
    }


def to_b64(binary):
    return base64.b64encode(binary).decode('ascii')


@app.route('/demoapi/logs/<int:id>', methods=['DELETE'])
@as_json
def log_delete(id):
    try:
        result = TRILLIAN_ADMIN.delete_log(
            log_id=id
        )

        return {"foo": "OK"}, 200
    except grpc.RpcError:
        raise JsonError(
            description='Requested log to delete not found'
        )


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


@app.route('/v1beta1/logs/<int:log_id>/leaves:by_range')
@as_json
def get_leaves_by_range(log_id):
    def serialize(leaf):
        # This should look like a `LogLeaf` message from
        # https://github.com/google/trillian/blob/master/trillian_log_api.proto

        return {
            'merkle_leaf_hash': to_b64(leaf.merkle_leaf_hash),
            'leaf_value': to_b64(leaf.leaf_value),
            'extra_data': None,             # TODO
            'leaf_index': leaf.leaf_index,
            'leaf_identity_hash': None,     # TODO
            'queue_timestamp': None,        # TODO
            'integrate_timestamp': None,    # TODO
        }

    leaves = map(
        serialize,
        make_log_client(log_id).get_leaves_by_range(
            start_index=int(request.args['start_index']),
            count=int(request.args['count'])
        )
    )

    return {
        'leaves': leaves
    }


@app.route('/v1beta1/logs/<int:log_id>/leaves', methods=['POST'])
@as_json
def insert_single_log_entry(log_id):
    log_client = make_log_client(log_id)

    try:
        log_client.queue_entry_dictionary(request.json)
    except ValueError as e:
        raise JsonError(description=str(e))

    return {'message': 'OK, queued entry for inclusion in merkle tree'}


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
