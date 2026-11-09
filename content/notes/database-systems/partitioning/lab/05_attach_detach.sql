-- 新しい月のパーティションを、検証の走査ありとなしで ATTACH し、DEFAULT と DETACH の制約を見る
SET client_min_messages = warning;
DROP TABLE IF EXISTS metrics, metrics_2026_11, metrics_2026_12, metrics_2027_01;
CREATE TABLE metrics (id bigint NOT NULL, created_at timestamp NOT NULL)
  PARTITION BY RANGE (created_at);
CREATE TABLE metrics_2026_11 PARTITION OF metrics FOR VALUES FROM ('2026-11-01') TO ('2026-12-01');

-- 親表の外で、翌月と翌々月の表に 500 万行ずつ先に入れておく
CREATE TABLE metrics_2026_12 (LIKE metrics INCLUDING ALL);
CREATE TABLE metrics_2027_01 (LIKE metrics INCLUDING ALL);
INSERT INTO metrics_2026_12
SELECT g, timestamp '2026-12-01' + (g % 2678400) * interval '1 second' FROM generate_series(1, 5000000) AS g;
INSERT INTO metrics_2027_01
SELECT g, timestamp '2027-01-01' + (g % 2678400) * interval '1 second' FROM generate_series(1, 5000000) AS g;
-- 2027-01 の表にだけ、パーティションの範囲と同じ CHECK 制約を付ける
ALTER TABLE metrics_2027_01 ADD CONSTRAINT metrics_2027_01_range
  CHECK (created_at >= '2027-01-01' AND created_at < '2027-02-01');
CHECKPOINT;

SET client_min_messages = debug1;  -- 走査したかどうかを DEBUG で出す
\timing on
\echo '== (1) CHECK 制約なしで ATTACH'
ALTER TABLE metrics ATTACH PARTITION metrics_2026_12 FOR VALUES FROM ('2026-12-01') TO ('2027-01-01');
\echo '== (2) CHECK 制約ありで ATTACH'
ALTER TABLE metrics ATTACH PARTITION metrics_2027_01 FOR VALUES FROM ('2027-01-01') TO ('2027-02-01');
\timing off
SET client_min_messages = warning;

\echo '== (3) DEFAULT パーティションに入ったレコードと、後から作る月'
CREATE TABLE metrics_default PARTITION OF metrics DEFAULT;
INSERT INTO metrics VALUES (1, '2027-02-03 10:00');
SELECT tableoid::regclass AS partition, * FROM metrics WHERE created_at >= '2027-02-01';
CREATE TABLE metrics_2027_02 PARTITION OF metrics FOR VALUES FROM ('2027-02-01') TO ('2027-03-01');

\echo '== (4) DEFAULT パーティションがある間の DETACH CONCURRENTLY'
ALTER TABLE metrics DETACH PARTITION metrics_2026_11 CONCURRENTLY;

\echo '== (5) トランザクションの中での DETACH CONCURRENTLY'
DROP TABLE metrics_default;
BEGIN;
ALTER TABLE metrics DETACH PARTITION metrics_2026_11 CONCURRENTLY;
ROLLBACK;

\echo '== (6) DETACH CONCURRENTLY の後に残る CHECK 制約'
ALTER TABLE metrics DETACH PARTITION metrics_2026_11 CONCURRENTLY;
SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint
WHERE conrelid = 'metrics_2026_11'::regclass AND contype = 'c';

