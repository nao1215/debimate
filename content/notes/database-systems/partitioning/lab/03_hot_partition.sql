-- 同じ 1 日分の書き込みを、時刻の range と id の hash に入れて、行き先の偏りを比べる
SET client_min_messages = warning;
DROP TABLE IF EXISTS logs_range, logs_hash;
SET max_parallel_workers_per_gather = 0;

CREATE TABLE logs_range (id bigint NOT NULL, created_at timestamp NOT NULL)
  PARTITION BY RANGE (created_at);
CREATE TABLE logs_range_10 PARTITION OF logs_range FOR VALUES FROM ('2026-10-01') TO ('2026-11-01');
CREATE TABLE logs_range_11 PARTITION OF logs_range FOR VALUES FROM ('2026-11-01') TO ('2026-12-01');
CREATE TABLE logs_range_12 PARTITION OF logs_range FOR VALUES FROM ('2026-12-01') TO ('2027-01-01');

CREATE TABLE logs_hash (id bigint NOT NULL, created_at timestamp NOT NULL)
  PARTITION BY HASH (id);
CREATE TABLE logs_hash_0 PARTITION OF logs_hash FOR VALUES WITH (MODULUS 3, REMAINDER 0);
CREATE TABLE logs_hash_1 PARTITION OF logs_hash FOR VALUES WITH (MODULUS 3, REMAINDER 1);
CREATE TABLE logs_hash_2 PARTITION OF logs_hash FOR VALUES WITH (MODULUS 3, REMAINDER 2);

-- 2026-11-10 の 1 日に、1 秒 1 件の書き込みが来たとする
INSERT INTO logs_range
SELECT g, timestamp '2026-11-10' + (g - 1) * interval '1 second' FROM generate_series(1, 86400) AS g;
INSERT INTO logs_hash
SELECT g, timestamp '2026-11-10' + (g - 1) * interval '1 second' FROM generate_series(1, 86400) AS g;
ANALYZE logs_range, logs_hash;

\echo '== (1) パーティションごとに入った件数'
SELECT pg_stat_force_next_flush() \gset
SELECT relname AS partition, n_tup_ins AS inserted
FROM pg_stat_user_tables
WHERE relname ~ '^logs_(range|hash)_[0-9]+$'
ORDER BY relname;

\echo '== (2) hash で分けた表を時刻の範囲で読む'
EXPLAIN (COSTS OFF)
SELECT count(*) FROM logs_hash
WHERE created_at >= '2026-11-10 09:00' AND created_at < '2026-11-10 10:00';

\echo '== (3) hash で分けた表をキーの等値で読む'
EXPLAIN (COSTS OFF)
SELECT * FROM logs_hash WHERE id = 42;
