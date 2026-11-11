#!/usr/bin/env bash
# 実験 3: 同じ SQL を SQLite と PostgreSQL に渡す。
#
# GROUP BY に無く、集約もしていない列 a を SELECT する。
# SQLite はグループごとに 1 行を選んで答え、PostgreSQL は拒否する。
# PostgreSQL は docker の postgres:17-alpine で一時的に起動する。
set -u

SQL_SETUP="CREATE TABLE g (a INTEGER, b INTEGER); INSERT INTO g VALUES (1,10),(2,10),(3,20);"
QUERIES=(
  "SELECT a, b FROM g GROUP BY b ORDER BY b;"
  "SELECT a, max(b) FROM g;"
)

echo "== SQLite $(python3 -c 'import sqlite3; print(sqlite3.sqlite_version)')"
for q in "${QUERIES[@]}"; do
  echo "> $q"
  python3 - "$SQL_SETUP" "$q" <<'EOF'
import sqlite3, sys
db = sqlite3.connect(":memory:")
db.executescript(sys.argv[1])
for row in db.execute(sys.argv[2]):
    print(row)
EOF
done

name="difftest-pg-$$"
docker run -d --rm --name "$name" -e POSTGRES_PASSWORD=x postgres:17-alpine >/dev/null
trap 'docker stop "$name" >/dev/null' EXIT
until docker exec "$name" pg_isready -q -U postgres; do sleep 0.5; done
sleep 1

echo "== $(docker exec "$name" postgres --version)"
docker exec "$name" psql -q -U postgres -c "$SQL_SETUP" >/dev/null
for q in "${QUERIES[@]}"; do
  echo "> $q"
  docker exec "$name" psql -q -U postgres -At -F ', ' -c "$q" 2>&1
done
