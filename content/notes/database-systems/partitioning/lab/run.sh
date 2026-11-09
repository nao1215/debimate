#!/usr/bin/env bash
# PostgreSQL 17 のコンテナを起動し、全ての実験を順に流して output.txt に保存する
set -euo pipefail
cd "$(dirname "$0")"
C=${CONTAINER:-note-partitioning}
export CONTAINER=$C

docker run -d --rm --name "$C" -e POSTGRES_PASSWORD=pass postgres:17 >/dev/null
trap 'docker rm -f "$C" >/dev/null' EXIT
until docker exec "$C" pg_isready -U postgres -q; do sleep 1; done
sleep 2

{
  docker exec "$C" psql -U postgres -X -At -c 'SELECT version()'
  for f in 01_delete_vs_drop.sql 02_pruning.sql 03_hot_partition.sql 04_unique.sql 05_attach_detach.sql; do
    echo "#### $f"
    docker exec -i "$C" sh -c 'psql -U postgres -X -q 2>&1' < "$f"
  done
  echo "#### 06_lock_queue.sh"
  ./06_lock_queue.sh 2>&1
  echo "#### 07_default_lock.sh"
  ./07_default_lock.sh 2>&1
} | tee output.txt
