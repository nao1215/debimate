#!/usr/bin/env bash
# 同じ PostgreSQL に版の違う exporter を当て、出るメトリクス名の集合を比べる。
# 使い方: bash names.sh > output_names.txt
set -euo pipefail
export LC_ALL=C
NET=adapterlab
W=$(mktemp -d -p "${WORK:-.}")
docker network create "$NET" >/dev/null 2>&1 || true
names() { # $1=pg の版 $2=exporter の版
  docker run -d --rm --name pgn --network "$NET" -e POSTGRES_PASSWORD=secret "postgres:$1" >/dev/null
  until docker exec pgn pg_isready -U postgres >/dev/null 2>&1; do sleep 1; done; sleep 2
  docker run -d --rm --name exn --network "$NET" -p 9187:9187 \
    -e DATA_SOURCE_NAME="postgresql://postgres:secret@pgn:5432/postgres?sslmode=disable" \
    "prometheuscommunity/postgres-exporter:$2" >/dev/null
  sleep 3
  curl -s localhost:9187/metrics > "$W/raw-pg$1-$2"
  grep -E '^pg_' "$W/raw-pg$1-$2" | sed -E 's/[{ ].*//' | sort -u > "$W/pg$1-$2"
  docker rm -f exn pgn >/dev/null
}
names 16 v0.15.0; names 17 v0.15.0; names 17 v0.17.1; names 17 v0.20.1
for f in pg16-v0.15.0 pg17-v0.15.0 pg17-v0.17.1 pg17-v0.20.1; do echo "$f: $(wc -l < "$W/$f") names"; done
echo "## pg16-v0.15.0 にあり pg17-v0.15.0 に無い"; comm -23 "$W/pg16-v0.15.0" "$W/pg17-v0.15.0"
echo "## pg16-v0.15.0 にあり pg17-v0.17.1 に無い（DB と exporter の両方を上げた前後）"; comm -23 "$W/pg16-v0.15.0" "$W/pg17-v0.17.1"
echo "## pg17-v0.17.1 にあり pg17-v0.20.1 に無い"; comm -23 "$W/pg17-v0.17.1" "$W/pg17-v0.20.1"
echo "## pg17-v0.20.1 にあり pg17-v0.17.1 に無い（数だけ）"; comm -13 "$W/pg17-v0.17.1" "$W/pg17-v0.20.1" | wc -l
echo "## pg17-v0.17.1 の checkpoint 関連"; grep -E 'checkpoint' "$W/pg17-v0.17.1"
echo "## pg17-v0.15.0 の /metrics から pg_up と collector ごとの成否（本文の抜粋の元）"
grep -E '^# HELP pg_up |^pg_up |^# HELP pg_scrape_collector_success |^pg_scrape_collector_success' "$W/raw-pg17-v0.15.0"
echo "## pg17-v0.17.1 の /metrics から pg_stat_bgwriter_ の値（本文の抜粋の元）"
grep -E '^pg_stat_bgwriter_' "$W/raw-pg17-v0.17.1"
rm -rf "$W"; docker network rm "$NET" >/dev/null
