#!/usr/bin/env bash
# MySQL 8.4 の XA トランザクションで、run_postgres.sh の 1・2 と同じことを試す。
# 使い方: bash run_mysql.sh > output_mysql.txt
set -euo pipefail

IMG=mysql:8.4
T0=$(date +%s.%N)
ts() { printf '[%6.2f] ' "$(echo "$(date +%s.%N) - $T0" | bc)"; }
log() { ts; echo "$*"; }
q() { docker exec -i tpc-mysql mysql -uroot -ppw -N -B shop "$@" 2>&1 | { grep -v 'Using a password' || true; }; }

cleanup() { docker rm -f tpc-mysql >/dev/null 2>&1 || true; }
trap cleanup EXIT
cleanup

# 初期化の一時サーバーではなく、3306 で待ち受ける本番のサーバーが n 回目に起動するまで待つ
wait_ready() {
  until [ "$(docker logs tpc-mysql 2>&1 | grep -c 'ready for connections.*port: 3306 ')" -ge "$1" ]; do sleep 0.2; done
}

docker run -d --name tpc-mysql -e MYSQL_ROOT_PASSWORD=pw -e MYSQL_DATABASE=shop "$IMG" >/dev/null
wait_ready 1
q -e 'CREATE TABLE points(user_id int PRIMARY KEY, balance int); INSERT INTO points VALUES (1, 1000)'

echo "== 1. XA PREPARE の後に接続が切れる"
T0=$(date +%s.%N)
q <<'SQL'
XA START 'order-42';
UPDATE points SET balance = balance - 300 WHERE user_id = 1;
XA END 'order-42';
XA PREPARE 'order-42';
SQL
log "mysql が終了（XA COMMIT しないまま接続が切れた）"
echo "-- XA RECOVER"
q -e 'XA RECOVER'
log "別のセッションの UPDATE を開始（innodb_lock_wait_timeout 10）"
q -e 'SET SESSION innodb_lock_wait_timeout = 10; UPDATE points SET balance = balance + 50 WHERE user_id = 1' || true
log "UPDATE が終わった"

log "MySQL を再起動"
docker restart tpc-mysql >/dev/null
wait_ready 2
log "再起動が終わった"
echo "-- XA RECOVER"
q -e 'XA RECOVER'
q -e "XA COMMIT 'order-42'"
q -e 'SELECT * FROM points'
