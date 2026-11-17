#!/bin/sh
# slot.sh: 読み手のいない replication slot が 1 つあるだけで pg_wal が膨らむことを見る。
# 行を足して CHECKPOINT するのを 10 回繰り返し、書いた WAL の量と pg_wal の大きさを記録する。
# slot が無い場合と、ある場合（最後に slot を消して CHECKPOINT する）を比べる。
#   sh slot.sh > slot_output.txt
set -eu
C=walslot
q() { docker exec $C psql -U postgres -At -c "$1"; }
for mode in no_slot slot; do
  docker rm -f $C >/dev/null 2>&1 || true
  docker volume rm walslotdata >/dev/null 2>&1 || true
  docker run -d --name $C -e POSTGRES_PASSWORD=pw -v walslotdata:/var/lib/postgresql postgres:18-alpine >/dev/null
  sleep 6
  q "CREATE TABLE t (id bigserial PRIMARY KEY, pad text)" >/dev/null
  if [ $mode = slot ]; then
    q "SELECT pg_create_physical_replication_slot('standby1', true)" >/dev/null
  fi
  start=$(q "SELECT pg_current_wal_lsn()")
  size() { q "SELECT sum(size) / 1024 / 1024 FROM pg_ls_waldir()"; }
  written() { q "SELECT (pg_current_wal_lsn() - '$start'::pg_lsn) / 1024 / 1024"; }
  echo "# mode=$mode $(q "SHOW max_wal_size") max_slot_wal_keep_size=$(q "SHOW max_slot_wal_keep_size")"
  echo "$mode step=0 written_mb=0 pg_wal_mb=$(size)"
  for step in 1 2 3 4 5 6 7 8 9 10; do
    q "INSERT INTO t (pad) SELECT repeat('x', 200) FROM generate_series(1, 200000)" >/dev/null
    q "CHECKPOINT" >/dev/null
    echo "$mode step=$step written_mb=$(written) pg_wal_mb=$(size)"
  done
  if [ $mode = slot ]; then
    echo "$mode restart_lsn=$(q "SELECT restart_lsn FROM pg_replication_slots") start=$start current=$(q "SELECT pg_current_wal_lsn()")"
    q "SELECT pg_drop_replication_slot('standby1')" >/dev/null
    q "CHECKPOINT" >/dev/null
    echo "$mode step=drop written_mb=$(written) pg_wal_mb=$(size)"
  fi
done
docker rm -f $C >/dev/null
docker volume rm walslotdata >/dev/null
