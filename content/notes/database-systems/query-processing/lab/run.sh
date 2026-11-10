#!/bin/sh
# Docker の postgres:17 で experiment.sql を流す。ホストのポートは公開せず、
# 終了時にコンテナを削除する。
#
#   ./run.sh > output.txt
set -eu
cd "$(dirname "$0")"
C=note-query-processing
docker rm -f "$C" >/dev/null 2>&1 || true
docker run -d --name "$C" -e POSTGRES_PASSWORD=x postgres:17 >/dev/null
trap 'docker rm -f "$C" >/dev/null 2>&1' EXIT
until docker exec "$C" psql -U postgres -qAtc 'SELECT 1' >/dev/null 2>&1; do :; done
sleep 2
until docker exec "$C" psql -U postgres -qAtc 'SELECT 1' >/dev/null 2>&1; do :; done
docker cp experiment.sql "$C:/tmp/experiment.sql"
docker exec "$C" psql -U postgres -qAt -c "SELECT version()"
docker exec "$C" psql -U postgres -q -v ON_ERROR_STOP=1 -f /tmp/experiment.sql
