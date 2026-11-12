#!/usr/bin/env bash
# PostgreSQL の版 × postgres_exporter の版ごとに、exporter の /metrics から
# pg_up と collector ごとの成否（pg_scrape_collector_success）と、checkpoint の回数のメトリクスの名前を取り出す。
# v0.17.1 以降は、既定で無効の stat_checkpointer collector を有効にした場合（+ckpt）も試す。
# 使い方: bash matrix.sh > output_matrix.txt
set -u
PGS="15 16 17 18"
docker network create adnet >/dev/null 2>&1 || true
for pg in $PGS; do
  docker rm -f adpg >/dev/null 2>&1
  docker run -d --name adpg --network adnet -e POSTGRES_PASSWORD=pw postgres:${pg}-alpine >/dev/null
  until docker exec adpg pg_isready -U postgres >/dev/null 2>&1; do sleep 1; done
  sleep 2
  echo "== PostgreSQL $(docker exec adpg psql -U postgres -tAc 'SHOW server_version')"
  for exf in v0.15.0 v0.16.0 v0.17.1 v0.17.1+ckpt v0.20.1 v0.20.1+ckpt; do
    ex=${exf%+ckpt}; flag=""; [ "$exf" != "$ex" ] && flag="--collector.stat_checkpointer"
    docker rm -f adex >/dev/null 2>&1
    docker run -d --name adex --network adnet \
      -e DATA_SOURCE_NAME="postgresql://postgres:pw@adpg:5432/postgres?sslmode=disable" \
      prometheuscommunity/postgres-exporter:${ex} $flag >/dev/null
    sleep 4
    m=$(docker run --rm --network adnet curlimages/curl:8.10.1 -s http://adex:9187/metrics)
    up=$(echo "$m" | grep -E '^pg_up ' | awk '{print $2}')
    fails=$(echo "$m" | grep -E '^pg_scrape_collector_success\{' | grep -E ' 0$' | sed -E 's/.*collector="([^"]+)".*/\1/' | tr '\n' ' ')
    total=$(echo "$m" | grep -cE '^pg_scrape_collector_success\{')
    names=$(echo "$m" | grep -vE '^#' | grep -E '^pg_' | sed -E 's/[{ ].*//' | sort -u | wc -l)
    ck=$(echo "$m" | grep -oE '^pg_stat_(bgwriter_checkpoints_timed|checkpointer_num_timed)[a-z_]*' | head -1)
    echo "exporter $exf: pg_up=$up collectors=$total failed=[${fails% }] pg_metric_names=$names checkpoint_timed=${ck:-なし}"
  done
done
docker rm -f adpg adex >/dev/null 2>&1
docker network rm adnet >/dev/null 2>&1
