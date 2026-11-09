#!/usr/bin/env bash
# 親表を読み続けるトランザクションがある間に、CREATE TABLE ... PARTITION OF と
# ATTACH PARTITION を実行し、後から来た SELECT が待たされるかを比べる
set -euo pipefail
C=${CONTAINER:-note-partitioning}
# 1 つ目の引数を application_name にして psql を呼ぶ
psql_() { local app=$1; shift; docker exec -i -e PGAPPNAME="$app" "$C" psql -U postgres -X -q -v ON_ERROR_STOP=1 "$@"; }
# 実行にかかった秒数を表示する
timed() { local label=$1; shift; local s; s=$(date +%s.%N); "$@" >/dev/null
  printf '%-8s finished after %.1f s\n' "$label" "$(echo "$(date +%s.%N) - $s" | bc)"; }

psql_ setup <<'SQL'
SET client_min_messages = warning;
DROP TABLE IF EXISTS q_events, q_events_2026_12, q_events_2027_01;
CREATE TABLE q_events (id bigint NOT NULL, created_at timestamp NOT NULL)
  PARTITION BY RANGE (created_at);
CREATE TABLE q_events_2026_11 PARTITION OF q_events FOR VALUES FROM ('2026-11-01') TO ('2026-12-01');
INSERT INTO q_events VALUES (1, '2026-11-10');
-- ATTACH 用の表は、親表の外で CHECK 制約付きで用意しておく
CREATE TABLE q_events_2027_01 (LIKE q_events INCLUDING ALL);
ALTER TABLE q_events_2027_01 ADD CONSTRAINT q_events_2027_01_range
  CHECK (created_at >= '2027-01-01' AND created_at < '2027-02-01');
SQL

run_case() {
  local label=$1 ddl=$2
  echo "== $label"
  # A: 親表を読んだまま 6 秒間トランザクションを開いておく（長い集計の代わり）
  psql_ A_reader -c "BEGIN; SELECT count(*) FROM q_events; SELECT pg_sleep(6); COMMIT;" >/dev/null &
  sleep 1
  # B: パーティションを追加する DDL
  timed B_ddl psql_ B_ddl -c "$ddl" &
  sleep 1
  # C: B の後から来た、普通の SELECT
  timed C_select psql_ C_select -c "SELECT count(*) FROM q_events;" &
  sleep 1
  psql_ observer -c "SELECT application_name, wait_event_type, left(query, 30) AS query
            FROM pg_stat_activity WHERE application_name IN ('B_ddl', 'C_select')
            ORDER BY application_name;"
  wait
}

run_case "(1) CREATE TABLE ... PARTITION OF" \
  "CREATE TABLE q_events_2026_12 PARTITION OF q_events FOR VALUES FROM ('2026-12-01') TO ('2027-01-01');"
run_case "(2) ATTACH PARTITION" \
  "ALTER TABLE q_events ATTACH PARTITION q_events_2027_01 FOR VALUES FROM ('2027-01-01') TO ('2027-02-01');"
