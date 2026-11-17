-- 外部キーは deleted_at を見ない
\set ON_ERROR_STOP 0
\set VERBOSITY terse
CREATE TABLE members (id int PRIMARY KEY, name text NOT NULL, deleted_at timestamptz);
CREATE TABLE orders (
  id        int PRIMARY KEY,
  member_id int NOT NULL REFERENCES members (id) ON DELETE CASCADE,
  deleted_at timestamptz
);
INSERT INTO members VALUES (1, '佐藤', NULL);
INSERT INTO orders VALUES (100, 1, NULL);

\echo '-- 佐藤さんが退会（論理削除）'
UPDATE members SET deleted_at = now() WHERE id = 1;
\echo '-- ON DELETE CASCADE は動かず、注文は有効のまま'
SELECT id, member_id, deleted_at IS NULL AS active FROM orders;
\echo '-- 退会した会員への新しい注文も通る'
INSERT INTO orders VALUES (101, 1, NULL);
SELECT count(*) AS active_orders_of_withdrawn
FROM orders o JOIN members m ON m.id = o.member_id
WHERE m.deleted_at IS NOT NULL AND o.deleted_at IS NULL;

\echo '-- 比べる: 本当に DELETE すると'
CREATE TABLE members2 (id int PRIMARY KEY, name text NOT NULL);
CREATE TABLE orders2 (id int PRIMARY KEY, member_id int NOT NULL REFERENCES members2 (id));
INSERT INTO members2 VALUES (1, '佐藤');
INSERT INTO orders2 VALUES (100, 1);
DELETE FROM members2 WHERE id = 1;

\echo '-- 状態を含めた複合キーで参照する'
CREATE TABLE members3 (
  id     int PRIMARY KEY,
  status text NOT NULL,
  UNIQUE (id, status)
);
CREATE TABLE orders3 (
  id            int PRIMARY KEY,
  member_id     int  NOT NULL,
  member_status text NOT NULL DEFAULT '有効' CHECK (member_status = '有効'),
  FOREIGN KEY (member_id, member_status) REFERENCES members3 (id, status)
);
INSERT INTO members3 VALUES (1, '有効'), (2, '退会済み');
INSERT INTO orders3 (id, member_id) VALUES (100, 1);
\echo '-- 退会済みの会員への注文'
INSERT INTO orders3 (id, member_id) VALUES (101, 2);
\echo '-- 注文が 1 件でもある会員を退会させる'
UPDATE members3 SET status = '退会済み' WHERE id = 1;
