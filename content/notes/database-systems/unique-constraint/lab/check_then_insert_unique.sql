-- 各クライアントは同じ順に user1, user2, ... を登録しようとする。
-- SELECT で 0 件を確かめた時だけ INSERT する（自動コミット、READ COMMITTED）。
\set i :i + 1
SELECT count(*) AS n FROM users_unique WHERE email = 'user' || :i \gset
\if :n = 0
SELECT register_unique('user' || :i);
\endif
