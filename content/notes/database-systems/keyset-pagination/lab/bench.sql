-- OFFSET とキーセットで、同じ位置の 20 件を読む時間を 7 回ずつ測り、中央値を出す（ms）
\set ON_ERROR_STOP on
CREATE OR REPLACE FUNCTION median_ms(q text, n int DEFAULT 7) RETURNS numeric LANGUAGE plpgsql AS $$
DECLARE t0 timestamptz; ts numeric[] := '{}'; r record;
BEGIN
  EXECUTE q;  -- 1 回目はキャッシュを温めるために捨てる
  FOR k IN 1..n LOOP
    t0 := clock_timestamp();
    FOR r IN EXECUTE q LOOP END LOOP;
    ts := ts || (extract(epoch FROM clock_timestamp() - t0) * 1000)::numeric;
  END LOOP;
  RETURN (SELECT round(percentile_cont(0.5) WITHIN GROUP (ORDER BY x)::numeric, 3) FROM unnest(ts) AS x);
END $$;

\pset footer off
SELECT o AS offset_rows,
       median_ms(format('SELECT id, created_at, title FROM posts ORDER BY created_at DESC, id DESC LIMIT 20 OFFSET %s', o)) AS offset_ms,
       median_ms(format('SELECT id, created_at, title FROM posts WHERE (created_at, id) < (%L, %s) ORDER BY created_at DESC, id DESC LIMIT 20', c.created_at, c.id)) AS keyset_ms
FROM unnest(ARRAY[20, 1000, 10000, 50000, 100000, 200000, 400000, 600000, 800000, 999980]) AS o
CROSS JOIN LATERAL (SELECT created_at, id FROM posts ORDER BY created_at DESC, id DESC OFFSET o - 1 LIMIT 1) AS c;
