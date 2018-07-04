TRAFFIC_COUNT_DEMO_LOG_ID_FILE=/home/vagrant/.trillian/traffic_count_demo_log_id.txt

.PHONY: run_trillian_log_server
run_trillian_log_server: $(TRAFFIC_COUNT_DEMO_LOG_ID_FILE)
	trillian_log_server

.PHONY: run_trillian_log_signer
run_trillian_log_signer: $(TRAFFIC_COUNT_DEMO_LOG_ID_FILE)
	trillian_log_signer \
		--logtostderr \
		--force_master \
		--http_endpoint=localhost:8092 \
		--batch_size=50 \
		--sequencer_guard_window=0 \
		--sequencer_interval=10000ms

/home/vagrant/.reset_db_run:
	/vagrant/config/trillian_reset_db.sh $@

$(TRAFFIC_COUNT_DEMO_LOG_ID_FILE): /home/vagrant/.reset_db_run
	@mkdir -p ~/.trillian
	/vagrant/config/create_trillian_log.sh $@


.PHONY: run_webserver
run_webserver: $(TRAFFIC_COUNT_DEMO_LOG_ID_FILE)
	cd /vagrant/webserver ; \
	make run

.PHONY: watch_sass
watch_sass:
	cd /vagrant/webserver ; \
	make watch_sass
