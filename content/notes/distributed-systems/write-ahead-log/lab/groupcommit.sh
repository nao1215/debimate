#!/bin/sh
# groupcommit.sh: 1 行の INSERT を 1 トランザクションとして、同時に送る数（クライアント数）を
# 変えながら pgbench で 10 秒ずつ流し、コミットの数と WAL の fsync の数を比べる。
# 最後に、synchronous_commit = off の場合も同じ形で流す。
#   sh groupcommit.sh > groupcommit_output.txt
set -eu
C=walbench
docker rm -f $C >/dev/null 2>&1 || true
docker volume rm walbenchdata >/dev/null 2>&1 || true
docker run -d --name $C -e POSTGRES_PASSWORD=pw -v walbenchdata:/var/lib/postgresql postgres:18-alpine >/dev/null
sleep 6
q() { docker exec $C psql -U postgres -At -c "$1"; }
q "CREATE TABLE t (id bigserial PRIMARY KEY, v int)" >/dev/null
docker exec $C sh -c "echo 'INSERT INTO t (v) VALUES (1);' > /tmp/insert.sql"
q "SELECT version()"
bench() { # $1: PGOPTIONS
echo "# PGOPTIONS='$1'"
echo "clients commits commits_per_s wal_fsyncs fsyncs_per_s commits_per_fsync"
for n in 1 2 4 8 16 32 64; do
  q "SELECT pg_stat_force_next_flush()" >/dev/null
  before=$(q "SELECT sum(fsyncs) FROM pg_stat_io WHERE object = 'wal'")
  tx=$(docker exec -e PGOPTIONS="$1" $C pgbench -U postgres -n -c $n -j $n -T 10 -f /tmp/insert.sql postgres 2>/dev/null \
       | awk '/number of transactions actually processed/ {split($0,a,": "); split(a[2],b,"/"); print b[1]}')
  sleep 1
  after=$(q "SELECT sum(fsyncs) FROM pg_stat_io WHERE object = 'wal'")
  f=$((after - before))
  awk -v n=$n -v t=$tx -v f=$f 'BEGIN { printf "%d %d %.0f %d %.0f %.1f\n", n, t, t/10, f, f/10, (f > 0 ? t/f : 0) }'
done
}
bench ""
bench "-c synchronous_commit=off"
docker rm -f $C >/dev/null
docker volume rm walbenchdata >/dev/null
