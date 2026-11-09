#!/usr/bin/env bash
# PostgreSQL 17 のコンテナを起動して experiment.sql を流し、最後にコンテナを削除する。
# ホストのポートは公開しない。出力は標準出力に出る。
set -euo pipefail

name=note-query-plan-cache
here=$(cd "$(dirname "$0")" && pwd)

docker run -d --rm --name "$name" -e POSTGRES_PASSWORD=postgres postgres:17 >/dev/null
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
# 端末として実行し、エラーの行が実行順に並ぶようにする（改行の \r は取り除く）
docker exec -t "$name" psql -X -U postgres -P pager=off -e -f /tmp/experiment.sql | tr -d '\r'
