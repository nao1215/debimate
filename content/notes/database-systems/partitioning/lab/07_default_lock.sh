#!/usr/bin/env bash
# DEFAULT パーティションがある表に、CHECK 制約付きの表を ATTACH PARTITION する。
# 走査は省けても、DEFAULT パーティションに ACCESS EXCLUSIVE を取るので、
# DEFAULT を読んでいるトランザクションがあると、DDL と後続の SELECT が待つ
set -euo pipefail
C=${CONTAINER:-note-partitioning}
# 1 つ目の引数を application_name にして psql を呼ぶ
psql_() { local app=$1; shift; docker exec -i -e PGAPPNAME="$app" "$C" psql -U postgres -X -q -v ON_ERROR_STOP=1 "$@"; }
# 実行にかかった秒数を表示する
timed() { local label=$1; shift; local s; s=$(date +%s.%N); "$@" >/dev/null 2>&1
  printf '%-8s finished after %.1f s\n' "$label" "$(echo "$(date +%s.%N) - $s" | bc)"; }

psql_ setup <<'SQL'
SET client_min_messages = warning;
DROP TABLE IF EXISTS d_events, d_events_2027_01;
CREATE TABLE d_events (id bigint NOT NULL, created_at timestamp NOT NULL)
  PARTITION BY RANGE (created_at);
CREATE TABLE d_events_2026_11 PARTITION OF d_events FOR VALUES FROM ('2026-11-01') TO ('2026-12-01');
CREATE TABLE d_events_default PARTITION OF d_events DEFAULT;
-- DEFAULT 側にも、新しい範囲を含まない CHECK 制約を付けて走査を省けるようにする
ALTER TABLE d_events_default ADD CONSTRAINT d_events_default_not_2027_01
  CHECK (NOT (created_at >= '2027-01-01' AND created_at < '2027-02-01'));
INSERT INTO d_events VALUES (1, '2026-11-10');
CREATE TABLE d_events_2027_01 (LIKE d_events INCLUDING ALL);
ALTER TABLE d_events_2027_01 ADD CONSTRAINT d_events_2027_01_range
  CHECK (created_at >= '2027-01-01' AND created_at < '2027-02-01');
SQL

echo "== ATTACH PARTITION（DEFAULT パーティションあり、両方に CHECK 制約あり）"
# A: 親表を読んだまま 6 秒間トランザクションを開いておく（長い集計の代わり）
psql_ A_reader -c "BEGIN; SELECT count(*) FROM d_events; SELECT pg_sleep(6); COMMIT;" >/dev/null &
sleep 1
# B: ATTACH PARTITION
timed B_ddl psql_ B_ddl -c "ALTER TABLE d_events ATTACH PARTITION d_events_2027_01 FOR VALUES FROM ('2027-01-01') TO ('2027-02-01');" &
sleep 1
# C: B の後から来た、普通の SELECT
timed C_select psql_ C_select -c "SELECT count(*) FROM d_events;" &
sleep 1
psql_ observer -c "SELECT application_name, wait_event_type, left(query, 30) AS query
          FROM pg_stat_activity WHERE application_name IN ('B_ddl', 'C_select')
          ORDER BY application_name;"
wait

echo "== 走査を省けたか（DEBUG）"
psql_ setup <<'SQL'
SET client_min_messages = warning;
ALTER TABLE d_events DETACH PARTITION d_events_2027_01;
SET client_min_messages = debug1;
ALTER TABLE d_events ATTACH PARTITION d_events_2027_01 FOR VALUES FROM ('2027-01-01') TO ('2027-02-01');
SQL
