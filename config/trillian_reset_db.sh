#!/bin/sh -eux

TMPFILE=$(mktemp)
DONE_FILENAME=$1

$GOPATH/src/github.com/google/trillian/scripts/resetdb.sh > $TMPFILE && mv $TMPFILE $DONE_FILENAME
