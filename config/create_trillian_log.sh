#!/bin/sh -eux

LOG_ID_FILENAME=$1

kill_log_server() {
  for i in seq 1 10
  do
    PID=$(pidof trillian_log_server || true)
    if [ "$PID" != "" ]; then
      kill $PID
      sleep 2s
    else
      echo "Dead."
      break
    fi
  done
}

kill_log_server

trillian_log_server &
sleep 4s

TMP=$(mktemp)

${GOPATH}/src/github.com/google/trillian/createtree \
  --admin_server=localhost:8090 > ${TMP}

mv ${TMP} ${LOG_ID_FILENAME}

kill_log_server
