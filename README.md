# Verifiable Dataset Server

This is a virtual machine with a demo of a working verifiable dataset with two components:

1. An instance of [Trillian](https://github.com/google/trillian), providing the Merkle tree implementation using MySQL for storage

2. A flask app (webserver) which:

   * Provides Trillian API endpoints to allow a client to synchronise and check the merkle tree
   * Provides a demo UI to create and delete logs
   * Provides a demo API endpoint for inserting new log records
   * Provides API endpoints for synchronising and checking the merkle tree

## Run

- Download Virtualbox and Vagrant
- Run `mkdir -p ~/.cache/vagrant-apt-archives`
- Run `vagrant box update`
- Run `vagrant up --provision`
- Run `vagrant ssh`
- In different terminals run:

  * `make run_trillian_log_server`
  * `make run_trillian_log_signer`
  * `make run_webserver`

## Play


### Add a log

Once everything's running, try adding a log by browsing to [192.168.99.4:5000](http://192.168.99.4:5000)


### Look at the log's metadata

In the UI, click on the log metadata, which takes you to `/v1beta1/logs/<LOG ID>`

* The `log_url` is the base URL needed to interact with the log
* the `public_key` is used to sign log roots. In order to verify anything from the log, you'll need to take a copy of this public key to verify those signatures.

### Insert a log entry

You can `POST` data into a log (although the [python API client](https://github.com/projectsbyif/trillian-demo-python-api-client) can do this for you):

```
curl -X POST -H 'Content-type: application/json' http://192.168.99.4:5000/logs/<LOG ID>/leaves -d '{"foo": "bar"}'
```

### Get the latest signed log root

This Trillian endpoint provides the `tree_size` and the `root_hash` (the bottom of the Merkle tree), *signed* by the log's public key.

```
curl 'http://192.168.99.4:5000/v1beta1/logs/<LOG ID>/roots:latest'
```

### Get a Merkle consistency proof between two tree sizes:

This Trillian endpoint provides the information you need to validate that one tree is a *subtree* of a larger tree.

```
curl 'http://192.168.99.4:5000/v1beta1/logs/<LOG ID>:consistency_proof?first_tree_size=10&second_tree_size=20'
```

For example, suppose you previously validated the tree with 10 entries in it. Later, the tree has 20 entries. You want to check that smaller tree you previously validated is *completely contained* inside the new, larger tree.

## Trillian

Trillian is built [from source, from the latest commit on Github.](https://github.com/google/trillian)

The `./gocode` directory is shared from the host machine into the VM as a cache, reducing the time it takes to `vagrant destroy && vagrant up`

## Webserver

The webserver is a [Flask](http://flask.pocoo.org/) app.

It lives inside the [webserver/](https://github.com/projectsbyif/trillian-demo-log-server/blob/master/webserver) directory.

In Trillian's terminology, the webserver implements a *personality*. Trillian aims to be a generic Merkle tree implementation, while the personality implements the public interface.

The webserver communicates with Trillian using [gRPC](https://grpc.io/), where the API is defined in these main protobuf files:


* [trillian_admin_api.proto](https://github.com/google/trillian/blob/master/trillian_admin_api.proto) — Used to create and delete logs.

* [trillian_log_api.proto](https://github.com/google/trillian/blob/master/trillian_log_api.proto) — Used to insert and get log entries (leaves), get signed log roots, etc.

* [trillian.proto](https://github.com/google/trillian/blob/master/trillian.proto) — describes object types like `Tree`

The webserver has a local copy of all the protobuf files requires in the [protobuf/](https://github.com/projectsbyif/trillian-demo-log-server/blob/master/webserver/protobuf) directory.
