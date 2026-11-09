-- PostgreSQL 17 で実行する。psql -f orders_pg.sql
CREATE TABLE orders_sorted AS
  SELECT g AS id, (g - 1) / 100 + 1 AS user_id, g % 1000 AS amount,
         (ARRAY['paid', 'new', 'sent'])[g % 3 + 1] AS status
  FROM generate_series(1, 1000000) AS g;
CREATE TABLE orders_random AS SELECT * FROM orders_sorted ORDER BY random();
CREATE INDEX orders_sorted_user_id_idx ON orders_sorted(user_id);
CREATE INDEX orders_random_user_id_idx ON orders_random(user_id);
VACUUM ANALYZE;
SELECT tablename, correlation FROM pg_stats
  WHERE attname = 'user_id' AND tablename LIKE 'orders_%';
-- サーバーを再起動して共有バッファを空にしてから実行する
SET enable_bitmapscan = off;
EXPLAIN (ANALYZE, BUFFERS, COSTS OFF, TIMING OFF, SUMMARY OFF)
  SELECT status FROM orders_sorted WHERE user_id = 4242;
EXPLAIN (ANALYZE, BUFFERS, COSTS OFF, TIMING OFF, SUMMARY OFF)
  SELECT status FROM orders_random WHERE user_id = 4242;
