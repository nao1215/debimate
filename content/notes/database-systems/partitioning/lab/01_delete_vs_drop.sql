-- 古い 1 か月分を、DELETE で消す場合と、パーティションごと DROP で消す場合を比べる
SET client_min_messages = warning;
DROP TABLE IF EXISTS access_log;
CREATE TABLE access_log (id bigint NOT NULL, created_at timestamp NOT NULL)
  PARTITION BY RANGE (created_at);
CREATE TABLE access_log_2026_09 PARTITION OF access_log FOR VALUES FROM ('2026-09-01') TO ('2026-10-01');
CREATE TABLE access_log_2026_10 PARTITION OF access_log FOR VALUES FROM ('2026-10-01') TO ('2026-11-01');

-- 各月に 500 万件
INSERT INTO access_log
SELECT g, timestamp '2026-09-01' + (g % 2592000) * interval '1 second' FROM generate_series(1, 5000000) AS g;
INSERT INTO access_log
SELECT g, timestamp '2026-10-01' + (g % 2678400) * interval '1 second' FROM generate_series(1, 5000000) AS g;
VACUUM ANALYZE access_log;
CHECKPOINT;

\timing on
\echo '== (1) 9 月分を DELETE で消す'
DELETE FROM access_log WHERE created_at >= '2026-09-01' AND created_at < '2026-10-01';
\echo '== (2) 10 月分をパーティションごと DROP で消す'
DROP TABLE access_log_2026_10;
\timing off

\echo '== (3) DELETE の後に残った、回収待ちのレコード'
SELECT pg_stat_force_next_flush() \gset
SELECT relname, n_live_tup, n_dead_tup,
       pg_size_pretty(pg_relation_size(relid)) AS size
FROM pg_stat_user_tables WHERE relname = 'access_log_2026_09';
