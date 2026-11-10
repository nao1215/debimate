#!/bin/sh
# 同じメールアドレスの登録が c 件同時に届いた時、SELECT で確かめてから INSERT する
# 方式で何件のレコードが残るかを、一意制約の無い表とある表で数える。
# Docker の postgres:17 を使い、ホストのポートは公開しない。終了時にコンテナを削除する。
#
#   ./run.sh > output.txt
#
# 前提: c 個のクライアント（pgbench -c）が user1, user2, ... user$KEYS の順に
# 同じアドレスを登録しようとする。1 回の登録は SELECT count(*) → 0 件なら INSERT。
# 各文は自動コミットで、分離レベルは既定の READ COMMITTED。各条件を 3 回繰り返す。
set -eu
cd "$(dirname "$0")"
C=note-unique-constraint
KEYS=1000
REPEAT=3
docker rm -f "$C" >/dev/null 2>&1 || true
docker run -d --name "$C" -e POSTGRES_PASSWORD=x postgres:17 >/dev/null
trap 'docker rm -f "$C" >/dev/null 2>&1' EXIT
until docker exec "$C" pg_isready -q -U postgres 2>/dev/null; do :; done
# 初期化直後の再起動を待つ
until docker exec "$C" psql -U postgres -qAtc 'SELECT 1' >/dev/null 2>&1; do :; done
for f in setup.sql check_then_insert_plain.sql check_then_insert_unique.sql; do
  docker cp "$f" "$C:/tmp/$f"
done
docker exec "$C" psql -U postgres -qAt -c "SELECT version()"
docker exec "$C" psql -U postgres -q -f /tmp/setup.sql 2>/dev/null
echo "keys=$KEYS repeat=$REPEAT"
echo "clients run table rows_per_email emails_with_dup unique_violation"
for c in 1 2 4 8 16 32; do
  for r in $(seq 1 "$REPEAT"); do
    for t in plain unique; do
      docker exec "$C" psql -U postgres -qc "TRUNCATE users_plain, users_unique, violations"
      docker exec "$C" pgbench -U postgres -n -c "$c" -j "$c" -t "$KEYS" -D i=0 \
        -f "/tmp/check_then_insert_$t.sql" postgres >/dev/null
      docker exec "$C" psql -U postgres -qAt -F ' ' -c "
        SELECT $c, $r, '$t',
               round(count(*)::numeric / count(DISTINCT email), 2),
               (SELECT count(*) FROM (SELECT email FROM users_$t GROUP BY email HAVING count(*) > 1) d),
               (SELECT count(*) FROM violations)
          FROM users_$t"
    done
  done
done
