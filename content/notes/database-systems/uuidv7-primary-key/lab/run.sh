#!/usr/bin/env bash
# PostgreSQL 18 のコンテナを起動して experiment.sql を流し、最後にコンテナを削除する。
# ホストのポートは公開せず、永続ボリュームも作らない。
#   ./run.sh > output.txt
# 追加した 10,000 件で書き換わった索引のページの番号は dirty_blocks.csv に書く。
set -euo pipefail

name=note-uuidv7-primary-key
here=$(cd "$(dirname "$0")" && pwd)

docker run -d --rm --name "$name" -e POSTGRES_PASSWORD=postgres postgres:18 >/dev/null
trap 'docker rm -f "$name" >/dev/null 2>&1 || true' EXIT

for _ in $(seq 1 60); do
  # 初期化中の一時サーバーではなく、本番の起動を待つ
  if docker exec "$name" pg_isready -U postgres -h 127.0.0.1 >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
sleep 2
docker exec "$name" psql -X -U postgres -Atc 'SELECT version()'

docker cp "$here/experiment.sql" "$name:/tmp/experiment.sql"
docker exec -t "$name" psql -X -U postgres -P pager=off -e -f /tmp/experiment.sql | tr -d '\r'
docker exec "$name" psql -X -U postgres -q -A -F, -P footer=off -c 'SELECT * FROM dirty_blocks ORDER BY key_type, blk' > "$here/dirty_blocks.csv"
docker exec "$name" psql -X -U postgres -c "CREATE DATABASE sw" >/dev/null
docker cp "$here/switch.sql" "$name:/tmp/switch.sql"
docker exec -t "$name" psql -X -U postgres -d sw -P pager=off -e -f /tmp/switch.sql | tr -d '\r' > "$here/output_switch.txt"
