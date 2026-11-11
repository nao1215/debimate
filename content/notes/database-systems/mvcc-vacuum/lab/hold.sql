-- 別の接続で REPEATABLE READ のトランザクションを開き、スナップショットを持ったまま待つ。
-- experiment.sql が持つ advisory lock 42 が外れたら COMMIT して終わる
SET application_name = 'holder';
BEGIN ISOLATION LEVEL REPEATABLE READ;
SELECT count(*) FROM items_hold;
SELECT pg_advisory_lock(42);
COMMIT;
