-- 退会（deleted_at に日時）した人と同じメールアドレスで、再登録できるか
-- 有効な会員どうしで同じメールアドレスを止められるか
\set ON_ERROR_STOP 0
\set VERBOSITY terse

\echo '== (1) UNIQUE (email)'
CREATE TABLE m1 (id int PRIMARY KEY, email text NOT NULL, deleted_at timestamptz, UNIQUE (email));
INSERT INTO m1 VALUES (1, 'a@example.com', now());   -- 退会済み
INSERT INTO m1 VALUES (2, 'a@example.com', NULL);    -- 再登録
INSERT INTO m1 VALUES (3, 'b@example.com', NULL), (4, 'b@example.com', NULL);  -- 有効どうしの重複

\echo '== (2) UNIQUE (email, deleted_at)'
CREATE TABLE m2 (id int PRIMARY KEY, email text NOT NULL, deleted_at timestamptz, UNIQUE (email, deleted_at));
INSERT INTO m2 VALUES (1, 'a@example.com', now());
INSERT INTO m2 VALUES (2, 'a@example.com', NULL);
INSERT INTO m2 VALUES (3, 'b@example.com', NULL), (4, 'b@example.com', NULL);
SELECT count(*) AS active_b FROM m2 WHERE email = 'b@example.com' AND deleted_at IS NULL;

\echo '== (3) 部分一意索引 WHERE deleted_at IS NULL'
CREATE TABLE m3 (id int PRIMARY KEY, email text NOT NULL, deleted_at timestamptz);
CREATE UNIQUE INDEX m3_email_active ON m3 (email) WHERE deleted_at IS NULL;
INSERT INTO m3 VALUES (1, 'a@example.com', now());
INSERT INTO m3 VALUES (2, 'a@example.com', NULL);
INSERT INTO m3 VALUES (3, 'b@example.com', NULL), (4, 'b@example.com', NULL);

\echo '== (4) UNIQUE NULLS NOT DISTINCT (email, deleted_at)'
CREATE TABLE m4 (id int PRIMARY KEY, email text NOT NULL, deleted_at timestamptz,
                 UNIQUE NULLS NOT DISTINCT (email, deleted_at));
INSERT INTO m4 VALUES (1, 'a@example.com', now());
INSERT INTO m4 VALUES (2, 'a@example.com', NULL);
INSERT INTO m4 VALUES (3, 'b@example.com', NULL), (4, 'b@example.com', NULL);
