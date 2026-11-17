#!/bin/sh
# 実験を PostgreSQL 17 と MySQL 8.4 のコンテナで走らせ、出力を out/ に残す
set -eu
cd "$(dirname "$0")"
mkdir -p out
docker rm -f sd-pg sd-my >/dev/null 2>&1 || true
docker run -d --name sd-pg -e POSTGRES_PASSWORD=pw postgres:17 >/dev/null
docker run -d --name sd-my -e MYSQL_ROOT_PASSWORD=pw mysql:8.4 >/dev/null
until docker exec sd-pg pg_isready -U postgres >/dev/null 2>&1; do sleep 1; done
sleep 2
psql() { docker exec -i sd-pg psql -U postgres -X -q "$@"; }
docker exec sd-pg psql -U postgres -Atc 'SHOW server_version' > out/pg_version.txt
for t in join unique_pg fk deleted_record archive; do
  psql -c "DROP DATABASE IF EXISTS lab_$t" >/dev/null 2>&1 || true
  psql -c "CREATE DATABASE lab_$t"
  psql -d "lab_$t" < "$t.sql" > "out/$t.txt" 2>&1 || true
done
# 状態の遷移を 2 つのセッションで同時に走らせる
for lock in '' 'FOR UPDATE'; do
  name=transition_plain; [ -n "$lock" ] && name=transition_for_update
  psql < transition_setup.sql >/dev/null
  psql -v who=A -v to=退会済み -v wait=0 -v lock="$lock" < transition.sql > out/$name.A.txt 2>&1 &
  psql -v who=B -v to=一時停止 -v wait=0.3 -v lock="$lock" < transition.sql > out/$name.B.txt 2>&1 &
  wait
  { cat out/$name.A.txt out/$name.B.txt
    psql -c 'SELECT status FROM members' -c 'SELECT from_status, to_status FROM member_status_changes ORDER BY id'; } > out/$name.txt
  rm out/$name.A.txt out/$name.B.txt
done
until docker exec sd-my mysqladmin -uroot -ppw ping >/dev/null 2>&1; do sleep 2; done
sleep 5
docker exec sd-my mysql -uroot -ppw -Nse 'SELECT version()' 2>/dev/null > out/mysql_version.txt
docker exec -i sd-my mysql -uroot -ppw --force -t < unique_mysql.sql 2>&1 | grep -v 'Using a password' > out/unique_mysql.txt || true
docker rm -f sd-pg sd-my >/dev/null
