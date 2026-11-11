#!/usr/bin/env bash
# 同じ DB（CPU 2 コアに固定）に、毎秒の件数を固定して（pgbench -R）負荷を掛け、接続数 8 本と 256 本で待ち時間を比べる。
# -R では、空いている接続が無い間の待ち（schedule lag）も待ち時間に含まれる。アプリ側の接続プールで待つのと同じ形になる。
# 接続を使い回す場合と張り直す場合も比べる。最後に、max_connections を既定の 100 にした DB へ 101 本目の接続を張った時のエラーを見る。
#   ./run_rate.sh > output_rate.txt
set -euo pipefail

here=$(cd "$(dirname "$0")" && pwd)
net=note-pool-net
db=note-pool-db
docker network create "$net" >/dev/null
trap 'docker rm -f "$db" note-pool-db100 >/dev/null 2>&1 || true; docker network rm "$net" >/dev/null 2>&1 || true' EXIT

docker run -d --rm --name "$db" --network "$net" --cpuset-cpus=30,31 -e POSTGRES_PASSWORD=postgres postgres:17 \
  -c max_connections=600 -c shared_buffers=256MB >/dev/null
for _ in $(seq 1 60); do
  if docker exec "$db" pg_isready -U postgres -h 127.0.0.1 >/dev/null 2>&1; then break; fi
  sleep 1
done
sleep 2

pgb() { docker run --rm --network "$net" -e PGPASSWORD=postgres postgres:17 pgbench -h "$1" -U postgres "${@:2}"; }
pgb "$db" -i -s 20 -q postgres 2>&1 | tail -1
uptime

echo "clients,rate,run,tps,latency_ms,lag_ms" > "$here/rate.csv"
for rate in 10000 20000 30000 40000; do
  for c in 8 256; do
    j=8
    for r in 1 2 3; do
      out=$(pgb "$db" -S -c "$c" -j "$j" -R "$rate" -T 10 postgres 2>&1)
      tps=$(echo "$out" | sed -n 's/^tps = \([0-9.]*\).*/\1/p')
      lat=$(echo "$out" | sed -n 's/^latency average = \([0-9.]*\) ms/\1/p')
      lag=$(echo "$out" | sed -n 's/^rate limit schedule lag: avg \([0-9.]*\) .*/\1/p')
      echo "clients=$c rate=$rate run=$r tps=$tps latency_ms=$lat lag_ms=$lag"
      echo "$c,$rate,$r,$tps,$lat,$lag" >> "$here/rate.csv"
    done
  done
done

# 接続を使い回す場合と、取引ごとに接続を張り直す場合（pgbench -C）を、同じ 8 本で比べる
echo "reconnect,run,tps,latency_ms" > "$here/connect.csv"
for mode in reuse reconnect; do
  flag=""; [ "$mode" = reconnect ] && flag="-C"
  for r in 1 2 3; do
    out=$(pgb "$db" -S -c 8 -j 8 $flag -T 10 postgres 2>&1)
    tps=$(echo "$out" | sed -n 's/^tps = \([0-9.]*\).*/\1/p')
    lat=$(echo "$out" | sed -n 's/^latency average = \([0-9.]*\) ms/\1/p')
    echo "mode=$mode run=$r tps=$tps latency_ms=$lat"
    echo "$mode,$r,$tps,$lat" >> "$here/connect.csv"
  done
done

# max_connections が既定（100）の DB に、101 本の接続を張る
docker run -d --rm --name note-pool-db100 --network "$net" -e POSTGRES_PASSWORD=postgres postgres:17 >/dev/null
for _ in $(seq 1 60); do
  if docker exec note-pool-db100 pg_isready -U postgres -h 127.0.0.1 >/dev/null 2>&1; then break; fi
  sleep 1
done
sleep 2
docker exec note-pool-db100 psql -X -U postgres -Atc 'SHOW max_connections; SHOW superuser_reserved_connections;'
pgb note-pool-db100 -i -s 1 -q postgres >/dev/null 2>&1
pgb note-pool-db100 -S -c 101 -j 4 -T 3 postgres 2>&1 | grep -m 3 -iE "FATAL|error|too many" || true
