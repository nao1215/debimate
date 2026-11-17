#!/usr/bin/env bash
# 2PC の参加者として PostgreSQL 17 を 2 台動かし、コーディネータが途中で止まった時の
# 準備済みトランザクション（prepared transaction）の振る舞いを記録する。
# 使い方: bash run_postgres.sh > output_postgres.txt
# 必要なもの: docker と postgres:17-alpine のイメージ。終わるとコンテナを消す。
set -euo pipefail

IMG=postgres:17-alpine
T0=$(date +%s.%N)
ts() { printf '[%6.2f] ' "$(echo "$(date +%s.%N) - $T0" | bc)"; }
log() { ts; echo "$*"; }
q() { local c=$1; shift; docker exec -i "$c" psql -U postgres -At -v ON_ERROR_STOP=1 "$@"; }

cleanup() { docker rm -f tpc-orders tpc-points tpc-default >/dev/null 2>&1 || true; }
trap cleanup EXIT
cleanup

wait_ready() {
  until docker exec "$1" pg_isready -U postgres -q 2>/dev/null &&
        docker exec "$1" psql -U postgres -Atc 'select 1' >/dev/null 2>&1; do sleep 0.2; done
}

echo "== 0. 既定の設定では PREPARE TRANSACTION が使えない"
docker run -d --name tpc-default -e POSTGRES_PASSWORD=pw "$IMG" >/dev/null
wait_ready tpc-default
q tpc-default -c 'show max_prepared_transactions'
q tpc-default <<'SQL' 2>&1 || true
BEGIN;
CREATE TABLE t(x int);
PREPARE TRANSACTION 'x';
SQL
docker rm -f tpc-default >/dev/null

# 参加者 2 台。注文の DB とポイントの DB
for c in tpc-orders tpc-points; do
  docker run -d --name "$c" -e POSTGRES_PASSWORD=pw "$IMG" -c max_prepared_transactions=10 >/dev/null
done
wait_ready tpc-orders; wait_ready tpc-points
q tpc-orders -c 'CREATE TABLE orders(id int PRIMARY KEY, user_id int, points int)'
q tpc-points <<'SQL'
CREATE TABLE points(user_id int PRIMARY KEY, balance int);
INSERT INTO points VALUES (1, 1000);
SQL

echo
echo "== 1. 普通のトランザクションは、接続が切れれば中止されてロックが外れる"
T0=$(date +%s.%N)
q tpc-points <<'SQL'
BEGIN;
UPDATE points SET balance = balance - 300 WHERE user_id = 1;
SQL
log "psql が終了（COMMIT しないまま接続が切れた）"
q tpc-points -c "SET lock_timeout = '3s'" -c 'UPDATE points SET balance = balance WHERE user_id = 1'
log "別のセッションの UPDATE はすぐ通った"

echo
echo "== 2. コーディネータが、注文の DB だけコミットした所で止まる"
T0=$(date +%s.%N)
log "準備: orders"
q tpc-orders <<'SQL'
BEGIN;
INSERT INTO orders VALUES (42, 1, 300);
PREPARE TRANSACTION 'order-42';
SQL
log "準備: points"
q tpc-points <<'SQL'
BEGIN;
UPDATE points SET balance = balance - 300 WHERE user_id = 1;
PREPARE TRANSACTION 'order-42';
SQL
log "決定: orders に COMMIT PREPARED"
q tpc-orders -c "COMMIT PREPARED 'order-42'"
log "コーディネータが停止（points には決定が届かない）"

echo "-- points に残った準備済みトランザクション"
q tpc-points -c "SELECT gid, prepared, owner FROM pg_prepared_xacts"
echo "-- そのトランザクションに接続はあるか（pg_stat_activity で xact_start のあるセッション）"
q tpc-points -c "SELECT count(*) FROM pg_stat_activity WHERE xact_start IS NOT NULL AND pid <> pg_backend_pid()"
echo "-- 行のロックを持つ者（pg_locks の pid が空）"
q tpc-points -c "SELECT locktype, mode, coalesce(pid::text,'(null)'), virtualtransaction FROM pg_locks WHERE locktype = 'transactionid'"
echo "-- 外から見えるもの: 注文はある、ポイントは減っていない"
q tpc-orders -c 'SELECT * FROM orders'
q tpc-points -c 'SELECT * FROM points'

log "別のアプリの UPDATE を開始（lock_timeout 10s）"
(
  q tpc-points -c "SET lock_timeout = '10s'" -c 'UPDATE points SET balance = balance + 50 WHERE user_id = 1' 2>&1 || true
  log "UPDATE が lock_timeout で失敗"
) &
BG=$!
sleep 2
echo "-- 待っているセッションから、待たせている相手を引く"
q tpc-points -c "SELECT state, wait_event_type, wait_event, pg_blocking_pids(pid) FROM pg_stat_activity WHERE query LIKE 'UPDATE points%'"
q tpc-points -c "SELECT pg_terminate_backend(0)" 2>&1 || true
wait "$BG"

log "points の PostgreSQL を再起動"
docker restart tpc-points >/dev/null
wait_ready tpc-points
log "再起動が終わった"
q tpc-points -c "SELECT gid, prepared FROM pg_prepared_xacts"

log "別のアプリの UPDATE を再開（lock_timeout 30s、裏で待たせる）"
(
  q tpc-points -c "SET lock_timeout = '30s'" -c 'UPDATE points SET balance = balance + 50 WHERE user_id = 1' >/dev/null 2>&1 \
    && log "待っていた UPDATE が通った" || log "待っていた UPDATE が失敗"
) &
BG=$!
sleep 4

echo "-- 運用者が判断する: orders に order-42 の準備済みは残っているか"
q tpc-orders -c "SELECT count(*) FROM pg_prepared_xacts WHERE gid = 'order-42'"
q tpc-orders -c 'SELECT count(*) FROM orders WHERE id = 42'
log "orders ではコミット済みなので、points も COMMIT PREPARED"
q tpc-points -c "COMMIT PREPARED 'order-42'"
wait "$BG"
q tpc-points -c 'SELECT * FROM points'

echo
echo "== 3. 準備済みが残っている間は、VACUUM が消せない"
vac() {
  q tpc-points -c 'CREATE TABLE IF NOT EXISTS junk(x int)' -c 'TRUNCATE junk' \
    -c 'INSERT INTO junk SELECT generate_series(1, 100000)' -c 'DELETE FROM junk' >/dev/null
  q tpc-points -c 'VACUUM (VERBOSE) junk' 2>&1 | grep -E 'tuples:|removable cutoff' | sed 's/^INFO: *//; s/^ *//'
}
echo "-- 準備済みが無い時の VACUUM"
vac
q tpc-points <<'SQL'
BEGIN;
UPDATE points SET balance = balance WHERE user_id = 1;
PREPARE TRANSACTION 'left-behind';
SQL
echo "-- 準備済みが 1 つ残っている時の VACUUM"
vac
q tpc-points -c "ROLLBACK PREPARED 'left-behind'"
echo "-- ROLLBACK PREPARED の後の VACUUM（行は消したまま）"
q tpc-points -c 'VACUUM (VERBOSE) junk' 2>&1 | grep -E 'tuples:|removable cutoff' | sed 's/^INFO: *//; s/^ *//'
