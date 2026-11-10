-- Query Processing ノートの 2 つの図の元になる実測。PostgreSQL 17 で流す。
-- 並列実行と JIT は切り、計画の形を本文の 3 候補にそろえる。
SET max_parallel_workers_per_gather = 0;
SET jit = off;
\pset pager off

-- 利用者 1 万件。country と city はどの値も 1%（100 件）で、
-- id が 1〜100 の利用者は日本の東京、残りは 99 組の国と都市に 100 件ずつ。
CREATE TABLE users (id int PRIMARY KEY, country text, city text);
INSERT INTO users
SELECT n,
       CASE WHEN n <= 100 THEN 'JP' ELSE 'C' || (n % 99) END,
       CASE WHEN n <= 100 THEN '東京' ELSE 'T' || (n % 99) END
  FROM generate_series(1, 10000) AS n;

-- 注文 100 万件。1 人あたり 100 件ずつ、利用者ごとに連続して入れ、user_id に索引を張る。
CREATE TABLE orders (id int PRIMARY KEY, user_id int, amount int);
INSERT INTO orders SELECT n, (n - 1) / 100 + 1, n % 1000 FROM generate_series(1, 1000000) AS n;
CREATE INDEX idx_orders_user_id ON orders (user_id);
-- 比較用: 本文の SQLite の例と同じく、注文を利用者に散らして入れた表。
CREATE TABLE orders_scattered (id int PRIMARY KEY, user_id int, amount int);
INSERT INTO orders_scattered SELECT n, n % 10000 + 1, n % 1000 FROM generate_series(1, 1000000) AS n;
CREATE INDEX idx_orders_scattered_user_id ON orders_scattered (user_id);
ANALYZE users;
ANALYZE orders;
ANALYZE orders_scattered;

-- 問い合わせの見積もりコスト（EXPLAIN）と、実行時間の中央値（EXPLAIN ANALYZE を 5 回）を返す。
-- 呼ぶ前に SET した enable_* がそのまま効く。
CREATE FUNCTION measure(q text) RETURNS TABLE (plan text, total_cost numeric, median_ms numeric) AS $$
DECLARE j json; t numeric[] := '{}';
BEGIN
  EXECUTE 'EXPLAIN (FORMAT JSON) ' || q INTO j;
  plan := j->0->'Plan'->>'Node Type';
  total_cost := (j->0->'Plan'->>'Total Cost')::numeric;
  EXECUTE q;  -- 1 回目はキャッシュを温めるだけ
  FOR i IN 1..5 LOOP
    EXECUTE 'EXPLAIN (ANALYZE, FORMAT JSON) ' || q INTO j;
    t := t || (j->0->>'Execution Time')::numeric;
  END LOOP;
  SELECT round(percentile_cont(0.5) WITHIN GROUP (ORDER BY x)::numeric, 1)
    INTO median_ms FROM unnest(t) AS x;
  RETURN NEXT;
END $$ LANGUAGE plpgsql;

\echo '== selectivity: no extended statistics'
\echo '-- country only'
EXPLAIN (ANALYZE, TIMING OFF, SUMMARY OFF) SELECT * FROM users WHERE country = 'JP';
\echo '-- city only'
EXPLAIN (ANALYZE, TIMING OFF, SUMMARY OFF) SELECT * FROM users WHERE city = '東京';
\echo '-- country AND city'
EXPLAIN (ANALYZE, TIMING OFF, SUMMARY OFF) SELECT * FROM users WHERE country = 'JP' AND city = '東京';

CREATE STATISTICS users_dep (dependencies) ON country, city FROM users;
ANALYZE users;
\echo '== selectivity: with CREATE STATISTICS (dependencies)'
\echo '-- country AND city'
EXPLAIN (ANALYZE, TIMING OFF, SUMMARY OFF) SELECT * FROM users WHERE country = 'JP' AND city = '東京';
DROP STATISTICS users_dep;
ANALYZE users;

-- 日本の利用者の注文を取り出す問い合わせ。enable_* で他の候補を外し、
-- 3 つの候補それぞれの見積もりコストと実行時間を測る。
\set q 'SELECT u.id, o.amount FROM orders o JOIN users u ON o.user_id = u.id WHERE u.country = ''JP'''
\echo '== plan: default (planner choice)'
EXPLAIN SELECT u.id, o.amount FROM orders o JOIN users u ON o.user_id = u.id WHERE u.country = 'JP';

\echo '== plan 1: seq scan orders, hash join'
SET enable_nestloop = off; SET enable_mergejoin = off;
SET enable_indexscan = off; SET enable_bitmapscan = off;
EXPLAIN SELECT u.id, o.amount FROM orders o JOIN users u ON o.user_id = u.id WHERE u.country = 'JP';
SELECT * FROM measure(:'q');
RESET enable_nestloop; RESET enable_mergejoin; RESET enable_indexscan; RESET enable_bitmapscan;

\echo '== plan 2: filter users, index lookup (nested loop)'
SET enable_hashjoin = off; SET enable_mergejoin = off; SET enable_bitmapscan = off;
EXPLAIN SELECT u.id, o.amount FROM orders o JOIN users u ON o.user_id = u.id WHERE u.country = 'JP';
SELECT * FROM measure(:'q');
RESET enable_hashjoin; RESET enable_mergejoin; RESET enable_bitmapscan;

\echo '== plan 3: sort both, merge join'
SET enable_hashjoin = off; SET enable_nestloop = off;
SET enable_indexscan = off; SET enable_bitmapscan = off;
EXPLAIN SELECT u.id, o.amount FROM orders o JOIN users u ON o.user_id = u.id WHERE u.country = 'JP';
SELECT * FROM measure(:'q');
RESET enable_hashjoin; RESET enable_nestloop; RESET enable_indexscan; RESET enable_bitmapscan;

\echo '== orders_scattered: default (planner choice), then plan 2 forced'
EXPLAIN SELECT u.id, o.amount FROM orders_scattered o JOIN users u ON o.user_id = u.id WHERE u.country = 'JP';
SET enable_hashjoin = off; SET enable_mergejoin = off; SET enable_bitmapscan = off;
EXPLAIN SELECT u.id, o.amount FROM orders_scattered o JOIN users u ON o.user_id = u.id WHERE u.country = 'JP';
