#!/usr/bin/env bash
# exporter 1 個が使うメモリを、10 秒ごとに 6 回集めた後で測る。
# 使い方: bash memory.sh > output_memory.txt
set -euo pipefail
NET=adapterlab
docker network create "$NET" >/dev/null 2>&1 || true
docker run -d --rm --name memdb --network "$NET" -e POSTGRES_PASSWORD=secret postgres:17 >/dev/null
until docker exec memdb pg_isready -U postgres >/dev/null 2>&1; do sleep 1; done; sleep 2
for ex in v0.15.0 v0.20.1; do
  docker run -d --rm --name memex --network "$NET" -p 9187:9187 \
    -e DATA_SOURCE_NAME="postgresql://postgres:secret@memdb:5432/postgres?sslmode=disable" \
    "prometheuscommunity/postgres-exporter:$ex" >/dev/null
  sleep 3
  for i in 1 2 3 4 5 6; do curl -s localhost:9187/metrics >/dev/null; sleep 10; done
  echo "exporter $ex: $(docker stats --no-stream --format '{{.MemUsage}}' memex)"
  docker rm -f memex >/dev/null
done
echo "postgres 17: $(docker stats --no-stream --format '{{.MemUsage}}' memdb)"
docker rm -f memdb >/dev/null; docker network rm "$NET" >/dev/null
