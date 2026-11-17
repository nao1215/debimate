#!/bin/sh
# slot_cap.sh: max_slot_wal_keep_size=256MB にすると、slot が保持できる量を超えた時に
# slot の方が無効（wal_status=lost）になり、pg_wal の膨らみが止まることを見る。
#   sh slot_cap.sh > slot_cap_output.txt
set -eu
C=walslot
q() { docker exec $C psql -U postgres -At -c "$1"; }
docker rm -f $C >/dev/null 2>&1 || true
docker volume rm walslotdata >/dev/null 2>&1 || true
docker run -d --name $C -e POSTGRES_PASSWORD=pw -v walslotdata:/var/lib/postgresql postgres:18-alpine -c max_slot_wal_keep_size=256MB >/dev/null
sleep 6
q "CREATE TABLE t (id bigserial PRIMARY KEY, pad text)" >/dev/null
q "SELECT pg_create_physical_replication_slot('standby1', true)" >/dev/null
start=$(q "SELECT pg_current_wal_lsn()")
echo "# max_slot_wal_keep_size=$(q "SHOW max_slot_wal_keep_size")"
for step in 1 2 3 4 5 6 7 8 9 10; do
  q "INSERT INTO t (pad) SELECT repeat('x', 200) FROM generate_series(1, 200000)" >/dev/null
  q "CHECKPOINT" >/dev/null
  echo "cap step=$step written_mb=$(q "SELECT (pg_current_wal_lsn() - '$start'::pg_lsn) / 1024 / 1024") pg_wal_mb=$(q "SELECT sum(size) / 1024 / 1024 FROM pg_ls_waldir()") wal_status=$(q "SELECT wal_status FROM pg_replication_slots")"
done
docker rm -f $C >/dev/null
docker volume rm walslotdata >/dev/null
