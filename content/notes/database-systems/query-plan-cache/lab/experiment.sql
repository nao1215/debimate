-- PostgreSQL 17 で、prepared statement の計画が custom plan から generic plan に
-- 切り替わる様子と、計画が作り直される条件を確かめる。
-- run.sh から psql で実行する。

\echo '=== 1. 準備: 1 店舗が 99% を占める注文の表 ==='
CREATE TABLE orders (
  id      bigint PRIMARY KEY,
  shop_id int    NOT NULL,
  amount  int    NOT NULL
) WITH (autovacuum_enabled = off);   -- 実験中に自動の ANALYZE が走らないようにする
INSERT INTO orders
  SELECT g,
         CASE WHEN g % 100 = 0 THEN 2 + (g / 100) % 1000 ELSE 1 END,
         g % 1000
  FROM generate_series(1, 1000000) AS g;
CREATE INDEX orders_shop_id_idx ON orders (shop_id);
VACUUM ANALYZE orders;

SELECT shop_id, count(*) FROM orders GROUP BY shop_id ORDER BY count(*) DESC LIMIT 3;
SELECT n_distinct, most_common_vals, most_common_freqs
  FROM pg_stats WHERE schemaname = 'public' AND tablename = 'orders' AND attname = 'shop_id';

\echo '=== 2. 同じ大口店舗 (shop_id = 1) で 7 回実行する ==='
PREPARE q(int) AS SELECT sum(amount) FROM orders WHERE shop_id = $1;
\echo '--- 1 回目'
EXPLAIN (ANALYZE) EXECUTE q(1);
\echo '--- 2〜5 回目'
EXECUTE q(1);
EXECUTE q(1);
EXECUTE q(1);
EXECUTE q(1);
\echo '--- 6 回目'
EXPLAIN (ANALYZE) EXECUTE q(1);
\echo '--- 7 回目'
EXPLAIN (ANALYZE) EXECUTE q(1);
SELECT name, generic_plans, custom_plans FROM pg_prepared_statements WHERE name = 'q';

\echo '=== 3. 同じ generic plan で小さい店舗 (shop_id = 500) を引く ==='
EXPLAIN (ANALYZE) EXECUTE q(500);

\echo '=== 4. force_custom_plan で値ごとの計画に戻す ==='
SET plan_cache_mode = force_custom_plan;
EXPLAIN (ANALYZE) EXECUTE q(1);
RESET plan_cache_mode;

\echo '=== 5. 小さい店舗で 6 回実行すると、generic plan に切り替わらない ==='
PREPARE small(int) AS SELECT sum(amount) FROM orders WHERE shop_id = $1;
EXECUTE small(2);
EXECUTE small(3);
EXECUTE small(4);
EXECUTE small(5);
EXECUTE small(6);
EXPLAIN EXECUTE small(7);
SELECT name, generic_plans, custom_plans FROM pg_prepared_statements WHERE name = 'small';

\echo '=== 6. 索引を消す・作ると、generic plan が作り直される ==='
EXPLAIN (COSTS OFF) EXECUTE q(1);
DROP INDEX orders_shop_id_idx;
EXPLAIN (COSTS OFF) EXECUTE q(1);
CREATE INDEX orders_shop_id_idx ON orders (shop_id);
EXPLAIN (COSTS OFF) EXECUTE q(1);

\echo '=== 7. 列を足すと、SELECT * の prepared statement はエラーになる ==='
PREPARE one(bigint) AS SELECT * FROM orders WHERE id = $1;
EXECUTE one(100);
ALTER TABLE orders ADD COLUMN note text;
EXECUTE one(100);
DEALLOCATE one;
PREPARE one(bigint) AS SELECT * FROM orders WHERE id = $1;
EXECUTE one(100);
ALTER TABLE orders DROP COLUMN note;

\echo '=== 8. search_path を変えると、表の名前が解決し直される ==='
CREATE SCHEMA archive;
CREATE TABLE archive.orders (id bigint, shop_id int, amount int);
INSERT INTO archive.orders VALUES (1, 1, 100);
PREPARE cnt AS SELECT count(*) FROM orders;
EXECUTE cnt;
SET search_path = archive;
EXECUTE cnt;
RESET search_path;

\echo '=== 9. 統計を更新しても、作り直されない場合がある ==='
-- n_distinct の上書きは次の ANALYZE から統計に反映される
ALTER TABLE orders ALTER COLUMN shop_id SET (n_distinct = 2);
PREPARE st(int) AS SELECT sum(amount) FROM orders WHERE shop_id = $1;
EXECUTE st(1);
EXECUTE st(1);
EXECUTE st(1);
EXECUTE st(1);
EXECUTE st(1);
\echo '--- ANALYZE 前の generic plan'
EXPLAIN EXECUTE st(1);
SELECT relpages, reltuples FROM pg_class WHERE oid = 'public.orders'::regclass;
ANALYZE orders;
SELECT n_distinct FROM pg_stats WHERE schemaname = 'public' AND tablename = 'orders' AND attname = 'shop_id';
SELECT relpages, reltuples FROM pg_class WHERE oid = 'public.orders'::regclass;
\echo '--- 行数もページ数も変わらない ANALYZE の後'
EXPLAIN EXECUTE st(1);
\echo '--- 新しく PREPARE した文の generic plan'
PREPARE st_new(int) AS SELECT sum(amount) FROM orders WHERE shop_id = $1;
SET plan_cache_mode = force_generic_plan;
EXPLAIN EXECUTE st_new(1);
RESET plan_cache_mode;
\echo '--- 1 件足してから ANALYZE した後'
INSERT INTO orders VALUES (1000001, 1, 1);
ANALYZE orders;
SELECT relpages, reltuples FROM pg_class WHERE oid = 'public.orders'::regclass;
EXPLAIN EXECUTE st(1);
