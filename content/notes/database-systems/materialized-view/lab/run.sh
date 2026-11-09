#!/usr/bin/env bash
# materialized view の実験。setup.sql を流した後に実行する。
# 使い方: bash run.sh [コンテナ名]
set -u
C=${1:-note-materialized-view}
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
psql_() { docker exec -i -e PGAPPNAME="$1" "$C" psql -U postgres -X -q -P pager=off "${@:2}"; }

echo '== (a) 元の表と materialized view の問い合わせ時間'
for i in 1 2 3; do
psql_ reader <<'SQL'
\timing on
SELECT sum(total) FROM (
  SELECT (ordered_at AT TIME ZONE 'Asia/Tokyo')::date AS day, sum(amount) AS total
  FROM orders GROUP BY 1) t
WHERE day BETWEEN '2026-03-01' AND '2026-03-31';
SELECT sum(total) FROM daily_sales
WHERE day BETWEEN '2026-03-01' AND '2026-03-31';
SQL
done

echo '== 表の大きさ'
psql_ admin -c "SELECT relname, pg_size_pretty(pg_relation_size(oid)) FROM pg_class WHERE relname IN ('orders', 'daily_sales');"

echo '== (b) INSERT した後の materialized view'
psql_ writer <<'SQL'
INSERT INTO orders (ordered_at, amount)
VALUES ('2026-03-01 12:00:00+09', 1000000);
SELECT 'orders' AS source, sum(amount) AS total FROM orders
WHERE (ordered_at AT TIME ZONE 'Asia/Tokyo')::date = '2026-03-01'
UNION ALL
SELECT 'daily_sales', total FROM daily_sales WHERE day = '2026-03-01';
REFRESH MATERIALIZED VIEW daily_sales;
SELECT 'daily_sales (refresh 後)' AS source, total FROM daily_sales WHERE day = '2026-03-01';
SQL

# daily_sales に対するロックを、接続名・モード・付与済みかで並べて表示する
show_locks() {
  psql_ observer <<'SQL'
SELECT a.application_name, l.mode, l.granted
FROM pg_locks l
JOIN pg_stat_activity a ON a.pid = l.pid
WHERE l.relation = 'daily_sales'::regclass
ORDER BY a.application_name, l.mode;
SQL
}

now_ms() { echo $(( $(date +%s%N) / 1000000 )); }

# 3 月 1 日に 1 件足してから refresh を始める。
# 時機に頼らないよう、refresher がロックを取ったのを pg_locks で見てから reader を動かし、
# reader がロック待ち（granted = f）になるか、reader が終わるまで pg_locks を読み続ける。
# どちらも上限は 200 回（docker exec 1 回で約 0.1 秒）。
blocking_test() {
  local stmt=$1
  psql_ writer -c "INSERT INTO orders (ordered_at, amount) VALUES ('2026-03-01 13:00:00+09', 1);"
  local t0; t0=$(now_ms)
  psql_ refresher -c '\timing on' -c "$stmt" > "$TMP/refresh.out" 2>&1 &
  local bg=$!
  local i
  for i in $(seq 200); do        # refresher がロックを取るまで待つ
    show_locks > "$TMP/locks.out"
    grep -q 'refresher .*| t' "$TMP/locks.out" && break
  done
  local t1; t1=$(now_ms)
  psql_ reader -c '\timing on' -c "SELECT total FROM daily_sales WHERE day = '2026-03-01';" > "$TMP/reader.out" 2>&1 &
  local rd=$!
  for i in $(seq 200); do        # reader がロック待ちになるか、終わるまで読む
    show_locks > "$TMP/locks.out"
    grep -q 'reader .*| f' "$TMP/locks.out" && break
    kill -0 "$rd" 2>/dev/null || { show_locks > "$TMP/locks.out"; break; }
  done
  echo "-- reader は refresh の開始から約 $((t1 - t0)) ms 後に開始（docker exec の起動時間を含む）"
  echo '-- pg_locks'; cat "$TMP/locks.out"
  wait $bg $rd
  echo '-- refresher'; cat "$TMP/refresh.out"
  echo '-- reader';    cat "$TMP/reader.out"
  echo '-- refresh の完了後'
  psql_ reader -c "SELECT total FROM daily_sales WHERE day = '2026-03-01';"
}

echo '== (c-1) REFRESH の実行中に別の接続から SELECT'
blocking_test 'REFRESH MATERIALIZED VIEW daily_sales;'

echo '== (d) UNIQUE 索引が無い状態で CONCURRENTLY'
psql_ refresher -c 'REFRESH MATERIALIZED VIEW CONCURRENTLY daily_sales;'

echo '== (c-2) UNIQUE 索引を作ってから CONCURRENTLY'
psql_ admin -c 'CREATE UNIQUE INDEX daily_sales_day ON daily_sales (day);'
blocking_test 'REFRESH MATERIALIZED VIEW CONCURRENTLY daily_sales;'

echo '== (e) refresh と最終更新時刻を同じトランザクションで記録'
psql_ admin <<'SQL'
CREATE TABLE IF NOT EXISTS mv_refresh_log (
  name         text PRIMARY KEY,
  refreshed_at timestamptz NOT NULL
);
BEGIN;
REFRESH MATERIALIZED VIEW CONCURRENTLY daily_sales;
INSERT INTO mv_refresh_log VALUES ('daily_sales', now())
ON CONFLICT (name) DO UPDATE SET refreshed_at = EXCLUDED.refreshed_at;
COMMIT;
SELECT d.day, d.total, l.refreshed_at
FROM daily_sales d CROSS JOIN mv_refresh_log l
WHERE l.name = 'daily_sales' AND d.day = '2026-03-01';
SQL

echo '== (f) refresh の前後で、表と索引の格納先ファイルが変わるか'
psql_ admin <<'SQL'
SELECT 'before' AS at, relname, relfilenode FROM pg_class
WHERE relname IN ('daily_sales', 'daily_sales_day') ORDER BY relname;
REFRESH MATERIALIZED VIEW CONCURRENTLY daily_sales;
SELECT 'after CONCURRENTLY' AS at, relname, relfilenode FROM pg_class
WHERE relname IN ('daily_sales', 'daily_sales_day') ORDER BY relname;
REFRESH MATERIALIZED VIEW daily_sales;
SELECT 'after plain' AS at, relname, relfilenode FROM pg_class
WHERE relname IN ('daily_sales', 'daily_sales_day') ORDER BY relname;
SQL
