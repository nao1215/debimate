#!/usr/bin/env bash
# Prometheus で 5 秒ごとに集めながら、DB と exporter を順に入れ替える。
#   0 秒: PostgreSQL 16 + exporter v0.15.0
#  60 秒: DB だけ PostgreSQL 17 に入れ替える（同じホスト名 db）
# 120 秒: exporter を v0.17.1 に上げる
# 180 秒: exporter に --collector.stat_checkpointer を付ける
# 240 秒: 終わり。query_range の結果を output_timeline.json に書く
set -euo pipefail
cd "$(dirname "$0")"
NET=adapterlab
DSN="postgresql://postgres:secret@db:5432/postgres?sslmode=disable"
docker network create "$NET" >/dev/null 2>&1 || true
db() { docker rm -f db >/dev/null 2>&1 || true
  docker run -d --rm --name db --network "$NET" -e POSTGRES_PASSWORD=secret "postgres:$1" >/dev/null
  until docker exec db pg_isready -U postgres >/dev/null 2>&1; do sleep 1; done
  # checkpoint の数が動くように、10 秒ごとに CHECKPOINT を打つ
  docker exec -d db sh -c 'while true; do psql -U postgres -qc CHECKPOINT; sleep 10; done'; }
exporter() { docker rm -f exporter >/dev/null 2>&1 || true
  docker run -d --rm --name exporter --network "$NET" -e DATA_SOURCE_NAME="$DSN" \
    "prometheuscommunity/postgres-exporter:$1" "${@:2}" >/dev/null; }
docker run -d --rm --name prom --network "$NET" -p 9090:9090 \
  -v "$PWD/prometheus.yml:/etc/prometheus/prometheus.yml:ro" \
  -v "$PWD/rules.yml:/etc/prometheus/rules.yml:ro" prom/prometheus:v3.5.0 >/dev/null
db 16; exporter v0.15.0
until curl -sf localhost:9090/-/ready >/dev/null; do sleep 1; done
T0=$(date +%s); echo "start $T0"
at() { while (( $(date +%s) - T0 < $1 )); do sleep 1; done; echo "t=$1 $2"; }
at 60 "db -> postgres:17"; db 17
at 120 "exporter -> v0.17.1"; exporter v0.17.1
at 180 "exporter -> v0.17.1 --collector.stat_checkpointer"; exporter v0.17.1 --collector.stat_checkpointer
at 240 "end"
q() { curl -s --get localhost:9090/api/v1/query_range --data-urlencode "query=$1" \
  --data-urlencode "start=$T0" --data-urlencode "end=$((T0+240))" --data-urlencode step=5; }
{ echo "{\"t0\": $T0,"
  echo "\"pg_up\": $(q pg_up),"
  echo "\"bgwriter_success\": $(q 'pg_scrape_collector_success{collector="stat_bgwriter"}'),"
  echo "\"checkpoints_req\": $(q pg_stat_bgwriter_checkpoints_req_total),"
  echo "\"checkpointer_num_requested\": $(q pg_stat_checkpointer_num_requested_total),"
  echo "\"alerts\": $(q 'ALERTS')}"; } > output_timeline.json
docker rm -f prom exporter db >/dev/null; docker network rm "$NET" >/dev/null
