\set ON_ERROR_STOP on
CREATE EXTENSION pageinspect;

-- 1. UPDATE は古い版を残したまま、新しい版を足す。DELETE は版に削除の印を付けるだけ。VACUUM が場所を空ける
CREATE TABLE acct (id int PRIMARY KEY, balance int NOT NULL) WITH (autovacuum_enabled = off);
INSERT INTO acct VALUES (1, 100), (2, 500);
SELECT ctid, xmin, xmax, * FROM acct ORDER BY id;
UPDATE acct SET balance = 200 WHERE id = 1;
SELECT ctid, xmin, xmax, * FROM acct ORDER BY id;
SELECT lp, t_xmin, t_xmax, t_ctid FROM heap_page_items(get_raw_page('acct', 0));
DELETE FROM acct WHERE id = 1;
SELECT lp, t_xmin, t_xmax, t_ctid FROM heap_page_items(get_raw_page('acct', 0));
VACUUM acct;
SELECT lp, lp_flags, t_xmin, t_xmax, t_ctid FROM heap_page_items(get_raw_page('acct', 0));

-- 2. 10 万件の表の全件を 10 回更新し、回ごとに表の大きさを記録する
--    none: VACUUM しない / vacuum: 回ごとに VACUUM / hold: 回ごとに VACUUM するが、古いスナップショットを持つ接続がある
CREATE TABLE sizes (cond text, round int, mb numeric, dead bigint);
SELECT format('CREATE TABLE %I (id int PRIMARY KEY, n int NOT NULL, pad text NOT NULL) WITH (autovacuum_enabled = off)', t),
       format('INSERT INTO %I SELECT i, 0, repeat(''x'', 100) FROM generate_series(1, 100000) AS i', t),
       format('VACUUM ANALYZE %I', t),
       format('INSERT INTO sizes VALUES (%L, 0, round(pg_relation_size(%L) / 1048576.0, 1), 0)', c, t)
FROM (VALUES ('none', 'items_none'), ('vacuum', 'items_vacuum'), ('hold', 'items_hold')) AS v(c, t) \gexec

-- 各回: 全件を UPDATE → （none 以外は）VACUUM → 大きさと死んだ版の数を記録
SELECT format('UPDATE %I SET n = n + 1', t),
       CASE WHEN c = 'none' THEN 'SELECT 1' ELSE format('VACUUM %I', t) END,
       'SELECT pg_stat_force_next_flush()',
       format('INSERT INTO sizes SELECT %L, %s, round(pg_relation_size(%L) / 1048576.0, 1), n_dead_tup '
              'FROM pg_stat_user_tables WHERE relname = %L', c, r, t, t)
FROM (VALUES ('none', 'items_none'), ('vacuum', 'items_vacuum')) AS v(c, t), generate_series(1, 10) AS r
ORDER BY c, r \gexec

-- hold の条件だけ、別の接続で items_hold を読んだまま開いておく。
-- 古いスナップショットは DB 全体の VACUUM を止めるので、none と vacuum を終えてから始める
SELECT pg_advisory_lock(42);
\! (psql -X -U postgres -q -f /tmp/hold.sql > /dev/null 2>&1 &)
SELECT pg_sleep(2);
SELECT application_name, state, backend_xmin FROM pg_stat_activity WHERE application_name = 'holder';
SELECT format('UPDATE %I SET n = n + 1', t),
       CASE WHEN c = 'none' THEN 'SELECT 1' ELSE format('VACUUM %I', t) END,
       'SELECT pg_stat_force_next_flush()',
       format('INSERT INTO sizes SELECT %L, %s, round(pg_relation_size(%L) / 1048576.0, 1), n_dead_tup '
              'FROM pg_stat_user_tables WHERE relname = %L', c, r, t, t)
FROM (VALUES ('hold', 'items_hold')) AS v(c, t), generate_series(1, 10) AS r
ORDER BY c, r \gexec
SELECT * FROM sizes ORDER BY cond, round;

-- 3. 古いスナップショットがある間の VACUUM は、死んだ版を消せない
VACUUM (VERBOSE) items_hold;

-- 4. スナップショットを持つトランザクションが終わると、次の VACUUM で消せる
SELECT pg_advisory_unlock(42);
SELECT pg_sleep(1);
SELECT count(*) AS holders FROM pg_stat_activity WHERE application_name = 'holder';
VACUUM (VERBOSE) items_hold;

-- 5. VACUUM は空きを再利用できるようにするだけで、ファイルは小さくならない。VACUUM FULL は表を作り直す
SELECT pg_size_pretty(pg_relation_size('items_none')) AS before_vacuum;
VACUUM items_none;
SELECT pg_size_pretty(pg_relation_size('items_none')) AS after_vacuum;
UPDATE items_none SET n = n + 1;
SELECT pg_size_pretty(pg_relation_size('items_none')) AS after_one_more_update;
VACUUM FULL items_none;
SELECT pg_size_pretty(pg_relation_size('items_none')) AS after_vacuum_full;

-- 6. トランザクション ID の年齢と、自動 VACUUM の既定の設定
SELECT datname, age(datfrozenxid) FROM pg_database WHERE datname = 'postgres';
SELECT name, setting FROM pg_settings
WHERE name IN ('autovacuum', 'autovacuum_vacuum_threshold', 'autovacuum_vacuum_scale_factor',
               'autovacuum_freeze_max_age', 'idle_in_transaction_session_timeout')
ORDER BY name;
