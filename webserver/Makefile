SOURCES := $(shell find sass -iname '*.scss')

.PHONY: code
code: venv/bin/activate protobuf/trillian_log_api.proto
	. venv/bin/activate; \
	python3 -m grpc_tools.protoc -I./protobuf --python_out=. --grpc_python_out=. \
	    protobuf/trillian_admin_api.proto \
	    protobuf/trillian_log_api.proto \
	    protobuf/trillian.proto \
	    protobuf/google/protobuf/duration.proto \
	    protobuf/google/api/annotations.proto \
	    protobuf/google/api/http.proto \
	    protobuf/google/rpc/status.proto \
	    protobuf/crypto/keyspb/keyspb.proto \
	    protobuf/crypto/sigpb/sigpb.proto

venv/bin/activate: requirements.txt
	test -f venv/bin/activate || virtualenv -p /usr/bin/python3 venv
	. venv/bin/activate ;\
	pip install -r requirements.txt
	touch venv/bin/activate  # update so it's as new as requirements.txt

.PHONY: run
run: venv/bin/activate code static/style.css
	. venv/bin/activate ; \
	python3 app.py


static/style.css: $(SOURCES)
	sass sass/style.scss > $@

.PHONY: watch_sass
watch_sass:
	sass --watch sass/style.scss:static/style.css

.PHONY: initdb
initdb: venv/bin/activate
	. venv/bin/activate ; \
	FLASK_APP=app FLASK_DEBUG=1 python3 -m flask initdb
