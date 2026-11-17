-- 退会（A）と一時停止（B）を同時に走らせる。:lock が FOR UPDATE なら行を押さえて読む
-- 使い方: psql -v who=A -v to=退会済み -v wait=0 -v lock='' -f transition.sql
\set QUIET on
SELECT pg_sleep(:wait) AS slept \gset
BEGIN;
SELECT status AS s, status = '有効' AS ok FROM members WHERE id = 1 :lock \gset
\echo :who が読んだ状態: :s
-- アプリが遷移を判断している間
SELECT pg_sleep(1) AS slept \gset
\if :ok
  UPDATE members SET status = :'to' WHERE id = 1;
  INSERT INTO member_status_changes (member_id, from_status, to_status) VALUES (1, :'s', :'to');
  \echo :who が :s から :to に変えた
\else
  \echo :who は :s からの遷移を拒否した
\endif
COMMIT;
