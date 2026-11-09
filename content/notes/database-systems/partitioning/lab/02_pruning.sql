-- 月ごとの range パーティションを作り、条件の書き方で読むパーティションが変わるかを見る
SET client_min_messages = warning;
DROP TABLE IF EXISTS events;
CREATE TABLE events (
    id         bigint    NOT NULL,
    user_id    int       NOT NULL,
    created_at timestamp NOT NULL
) PARTITION BY RANGE (created_at);

CREATE TABLE events_2026_01 PARTITION OF events FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');
CREATE TABLE events_2026_02 PARTITION OF events FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');
CREATE TABLE events_2026_03 PARTITION OF events FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');
CREATE TABLE events_2026_04 PARTITION OF events FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');
CREATE TABLE events_2026_05 PARTITION OF events FOR VALUES FROM ('2026-05-01') TO ('2026-06-01');
CREATE TABLE events_2026_06 PARTITION OF events FOR VALUES FROM ('2026-06-01') TO ('2026-07-01');

-- 1 分に 1 件、半年分（約 26 万件）
INSERT INTO events
SELECT g, (g % 1000) + 1, timestamp '2026-01-01' + (g - 1) * interval '1 minute'
FROM generate_series(1, 260640) AS g;
ANALYZE events;
-- 並列実行の行を出さず、プランを読みやすくする
SET max_parallel_workers_per_gather = 0;

\echo '== (1) 範囲で書いた条件'
EXPLAIN (ANALYZE, COSTS OFF, TIMING OFF, SUMMARY OFF)
SELECT count(*) FROM events
WHERE created_at >= '2026-03-01' AND created_at < '2026-04-01';

\echo '== (2) 関数で包んだ条件'
EXPLAIN (ANALYZE, COSTS OFF, TIMING OFF, SUMMARY OFF)
SELECT count(*) FROM events
WHERE date_trunc('month', created_at) = '2026-03-01';

\echo '== (3) パラメータを後から渡す generic plan'
PREPARE q(timestamp, timestamp) AS
  SELECT count(*) FROM events WHERE created_at >= $1 AND created_at < $2;
SET plan_cache_mode = force_generic_plan;
EXPLAIN (ANALYZE, COSTS OFF, TIMING OFF, SUMMARY OFF) EXECUTE q('2026-03-01', '2026-04-01');
