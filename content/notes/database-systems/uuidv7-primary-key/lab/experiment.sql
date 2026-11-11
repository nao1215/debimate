\set ON_ERROR_STOP on
CREATE EXTENSION pageinspect;
CREATE EXTENSION pgstattuple;
CREATE EXTENSION pg_buffercache;

-- 1. uuidv7() の値は、先頭の 48 ビットが生成した時刻（ミリ秒）になる
SELECT uuidv4() AS v4, uuidv7() AS v7 FROM generate_series(1, 5);
SELECT u, uuid_extract_version(u) AS version, uuid_extract_timestamp(u) AS ts
FROM (VALUES (uuidv4()), (uuidv7())) AS t(u);

-- 2. 主キーだけが違う 3 つの表に、100 万件を 1 万件ずつ入れる
CREATE TABLE t_bigint (id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, body text NOT NULL);
CREATE TABLE t_v4     (id uuid DEFAULT uuidv4() PRIMARY KEY, body text NOT NULL);
CREATE TABLE t_v7     (id uuid DEFAULT uuidv7() PRIMARY KEY, body text NOT NULL);

CREATE TABLE load_result (key_type text, seconds numeric, wal_mb numeric);
CREATE PROCEDURE load(tbl text, n int, batch int) LANGUAGE plpgsql AS $$
DECLARE t0 timestamptz := clock_timestamp(); l0 pg_lsn := pg_current_wal_lsn();
BEGIN
  FOR k IN 1..n / batch LOOP
    EXECUTE format('INSERT INTO %I (body) SELECT md5(i::text) FROM generate_series(1, %s) AS i', tbl, batch);
    COMMIT;
  END LOOP;
  INSERT INTO load_result VALUES (tbl,
    round(extract(epoch FROM clock_timestamp() - t0)::numeric, 2),
    round((pg_current_wal_lsn() - l0) / 1024.0 / 1024.0, 1));
  COMMIT;
END $$;

CALL load('t_bigint', 1000000, 10000);
CALL load('t_v4', 1000000, 10000);
CALL load('t_v7', 1000000, 10000);
SELECT * FROM load_result;

-- 3. 主キーの索引の大きさと、葉のページの埋まり具合
SELECT c.relname AS index,
       pg_size_pretty(pg_relation_size(c.oid)) AS size,
       s.leaf_pages, s.avg_leaf_density, s.leaf_fragmentation
FROM pg_class AS c, LATERAL pgstatindex(c.oid) AS s
WHERE c.relname IN ('t_bigint_pkey', 't_v4_pkey', 't_v7_pkey')
ORDER BY c.relname;

-- 4. CHECKPOINT の直後に 1 万件を足し、書き換わった索引のページの数と WAL の量を見る
CREATE TABLE dirty_blocks (key_type text, blk bigint);
CREATE TABLE add_result (key_type text, dirty_index_pages bigint, wal_mb numeric);
CREATE PROCEDURE add_and_count(tbl text) LANGUAGE plpgsql AS $$
DECLARE l0 pg_lsn;
BEGIN
  CHECKPOINT;
  l0 := pg_current_wal_lsn();
  EXECUTE format('INSERT INTO %I (body) SELECT md5(i::text) FROM generate_series(1, 10000) AS i', tbl);
  COMMIT;
  INSERT INTO dirty_blocks
  SELECT tbl, b.relblocknumber FROM pg_buffercache AS b
  WHERE b.relfilenode = pg_relation_filenode(tbl || '_pkey') AND b.isdirty;
  INSERT INTO add_result
  SELECT tbl, count(*), round((pg_current_wal_lsn() - l0) / 1024.0 / 1024.0, 1)
  FROM dirty_blocks WHERE key_type = tbl;
  COMMIT;
END $$;

CALL add_and_count('t_bigint');
CALL add_and_count('t_v4');
CALL add_and_count('t_v7');
SELECT a.*, pg_relation_size(a.key_type || '_pkey') / 8192 AS index_pages FROM add_result AS a;

-- 5. 主キーの大きさは、それを参照する外部キーと索引にも広がる
CREATE TABLE c_bigint (id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, parent bigint NOT NULL REFERENCES t_bigint);
CREATE TABLE c_v7     (id uuid DEFAULT uuidv7() PRIMARY KEY, parent uuid NOT NULL REFERENCES t_v7);
INSERT INTO c_bigint (parent) SELECT id FROM t_bigint;
INSERT INTO c_v7 (parent) SELECT id FROM t_v7;
CREATE INDEX ON c_bigint (parent);
CREATE INDEX ON c_v7 (parent);
VACUUM ANALYZE c_bigint, c_v7;
SELECT relname, pg_size_pretty(pg_relation_size(oid)) AS size
FROM pg_class WHERE relname IN ('c_bigint', 'c_bigint_pkey', 'c_bigint_parent_idx', 'c_v7', 'c_v7_pkey', 'c_v7_parent_idx')
ORDER BY relname;

-- 6. 同じ接続の中では、同じミリ秒に作った値も順に並ぶ
SELECT count(*) AS total,
       count(*) FILTER (WHERE u > prev) AS ascending,
       count(DISTINCT uuid_extract_timestamp(u)) AS distinct_ms
FROM (SELECT u, lag(u) OVER (ORDER BY n) AS prev
      FROM (SELECT n, uuidv7() AS u FROM generate_series(1, 100000) AS n) AS g) AS t
WHERE prev IS NOT NULL;

-- 7. 時刻をずらして作る（uuidv7 の shift 引数）。値から時刻が読めることにも注意
SELECT uuid_extract_timestamp(uuidv7(interval '-1 year')) - now() AS shifted;
