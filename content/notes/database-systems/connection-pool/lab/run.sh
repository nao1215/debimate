#!/usr/bin/env bash
# CPU を 2 コア（30 番と 31 番）に固定した PostgreSQL 17 に、別のコンテナの pgbench から接続数を変えて負荷を掛ける。
# ホストのポートは公開せず、専用の docker network だけで繋ぐ。最後にコンテナと network を消す。
#   ./run.sh > output.txt     （結果の表は bench.csv にも書く）
set -euo pipefail

here=$(cd "$(dirname "$0")" && pwd)
net=note-pool-net
db=note-pool-db
docker network create "$net" >/dev/null
trap 'docker rm -f "$db" >/dev/null 2>&1 || true; docker network rm "$net" >/dev/null 2>&1 || true' EXIT

docker run -d --rm --name "$db" --network "$net" --cpuset-cpus=30,31 -e POSTGRES_PASSWORD=postgres postgres:17 \
  -c max_connections=600 -c shared_buffers=256MB >/dev/null
for _ in $(seq 1 60); do
  if docker exec "$db" pg_isready -U postgres -h 127.0.0.1 >/dev/null 2>&1; then break; fi
  sleep 1
done
sleep 2
docker exec "$db" psql -X -U postgres -Atc 'SELECT version()'

pgb() { docker run --rm --network "$net" -e PGPASSWORD=postgres postgres:17 pgbench -h "$db" -U postgres "$@"; }
pgb -i -s 20 -q postgres 2>&1 | tail -1

echo "clients,run,tps,latency_ms" > "$here/bench.csv"
for c in 1 2 4 8 16 32 64 128 256 512; do
  j=$(( c < 8 ? c : 8 ))
  for r in 1 2 3 4 5; do
    out=$(pgb -S -c "$c" -j "$j" -T 10 postgres 2>&1)
    tps=$(echo "$out" | sed -n 's/^tps = \([0-9.]*\).*/\1/p')
    lat=$(echo "$out" | sed -n 's/^latency average = \([0-9.]*\) ms/\1/p')
    echo "clients=$c run=$r tps=$tps latency_ms=$lat load1=$(cut -d' ' -f1 /proc/loadavg)"
    echo "$c,$r,$tps,$lat" >> "$here/bench.csv"
  done
done
