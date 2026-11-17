#!/bin/sh
# waldump.sh: checkpoint の直後に UPDATE を 1 回だけ実行し、その間に書かれた WAL を pg_waldump で読む。
# 表は id（主キー）と balance（索引なし）の 2 列で、balance を 400 から 500 に変える。
#   sh waldump.sh > waldump_output.txt
set -eu
C=walwaldump
q() { docker exec $C psql -U postgres -At -c "$1"; }
docker rm -f $C >/dev/null 2>&1 || true
docker volume rm walwaldumpdata >/dev/null 2>&1 || true
docker run -d --name $C -e POSTGRES_PASSWORD=pw -v walwaldumpdata:/var/lib/postgresql postgres:18-alpine >/dev/null
sleep 6
echo "# $(q "SELECT version()")"
echo "# data_checksums=$(q "SHOW data_checksums") full_page_writes=$(q "SHOW full_page_writes")"
q "CREATE TABLE accounts (id int PRIMARY KEY, balance int)" >/dev/null
q "INSERT INTO accounts VALUES (1, 400)" >/dev/null
q "CHECKPOINT" >/dev/null
start=$(q "SELECT pg_current_wal_insert_lsn()")
q "UPDATE accounts SET balance = 500 WHERE id = 1" >/dev/null
end=$(q "SELECT pg_current_wal_insert_lsn()")
echo "# relation=$(q "SELECT pg_relation_filepath('accounts')") start=$start end=$end"
echo "# pg_waldump --start $start --end $end"
docker exec $C sh -c "pg_waldump -p \$PGDATA/pg_wal --start $start --end $end"
docker rm -f $C >/dev/null
docker volume rm walwaldumpdata >/dev/null
