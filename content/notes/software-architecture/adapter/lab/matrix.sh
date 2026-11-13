#!/usr/bin/env bash
# PostgreSQL の版 × postgres_exporter の版で、collector ごとの成否を集める。
# 使い方: bash matrix.sh > output_matrix.txt
set -euo pipefail
NET=adapterlab
docker network create "$NET" >/dev/null 2>&1 || true
for pg in 15 16 17 18; do
  docker run -d --rm --name "pg$pg" --network "$NET" \
    -e POSTGRES_PASSWORD=secret "postgres:$pg" >/dev/null
  until docker exec "pg$pg" pg_isready -U postgres >/dev/null 2>&1; do sleep 1; done
  sleep 2
  for ex in v0.15.0 v0.16.0 v0.17.1 v0.20.1; do
    docker run -d --rm --name exporter --network "$NET" -p 9187:9187 \
      -e DATA_SOURCE_NAME="postgresql://postgres:secret@pg$pg:5432/postgres?sslmode=disable" \
      "prometheuscommunity/postgres-exporter:$ex" >/dev/null
    sleep 3
    echo "## postgres $pg / exporter $ex"
    curl -s localhost:9187/metrics | grep -E '^(pg_up|pg_scrape_collector_success)' || true
    docker logs exporter 2>&1 | grep -m1 'collector failed' || true
    docker rm -f exporter >/dev/null
  done
  docker rm -f "pg$pg" >/dev/null
done
docker network rm "$NET" >/dev/null
