#!/usr/bin/env bash
# PostgreSQL 17 の Leader 1 台と Follower 1 台（ストリーミングレプリケーション）を Docker で作る。
#   ./cluster.sh up      作る（既にあれば作り直す）
#   ./cluster.sh down    消す
set -euo pipefail
IMG=postgres:17
NET=lf-net
case "${1:-up}" in
down)
  docker rm -f lf-leader lf-follower >/dev/null 2>&1 || true
  docker network rm $NET >/dev/null 2>&1 || true
  ;;
up)
  "$0" down
  docker network create $NET >/dev/null
  # Leader: 複製の接続を受け付けるように pg_hba.conf に 1 行足す
  docker run -d --name lf-leader --network $NET -p 55432:5432 \
    -e POSTGRES_HOST_AUTH_METHOD=trust \
    $IMG -c wal_level=replica -c max_wal_senders=5 >/dev/null
  until docker exec lf-leader pg_isready -U postgres >/dev/null 2>&1; do sleep 0.5; done
  # 初期化の途中で一度再起動するので、ログに 2 回目の ready が出るまで待つ
  until [ "$(docker logs lf-leader 2>&1 | grep -c "ready to accept connections")" -ge 2 ]; do sleep 0.5; done
  docker exec lf-leader bash -c 'echo "host replication all all trust" >> "$PGDATA/pg_hba.conf"'
  docker exec -u postgres lf-leader psql -qc "select pg_reload_conf()" >/dev/null
  docker exec -u postgres lf-leader psql -qc "create table t (id int primary key, v int)"
  # Follower: Leader の複製（pg_basebackup）から始め、-R で Leader に繋ぎ続ける設定を書く
  docker run -d --name lf-follower --network $NET -p 55433:5432 --user postgres \
    --entrypoint bash $IMG -c '
      pg_basebackup -h lf-leader -U postgres -D "$PGDATA" -R -X stream -C -S follower1 &&
      chmod 700 "$PGDATA" &&
      exec postgres -D "$PGDATA"' >/dev/null
  for i in $(seq 60); do docker exec lf-follower pg_isready -U postgres >/dev/null 2>&1 && break; sleep 0.5; done
  docker exec -u postgres lf-leader psql -Atc "select application_name, state, sync_state from pg_stat_replication"
  ;;
esac
