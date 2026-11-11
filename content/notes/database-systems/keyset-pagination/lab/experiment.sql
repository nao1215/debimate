-- 1. 投稿 100 万件の表を作る。created_at は 2 件ずつ同じ時刻にし、並び順の同点を作る
CREATE TABLE posts (
  id         bigint PRIMARY KEY,
  created_at timestamptz NOT NULL,
  title      text NOT NULL
);
INSERT INTO posts
SELECT i, timestamptz '2026-01-01 00:00:00+00' + (i / 2) * interval '1 second', 'post ' || i
FROM generate_series(1, 1000000) AS i;
CREATE INDEX posts_created_id ON posts (created_at DESC, id DESC);
VACUUM ANALYZE posts;

-- 2. OFFSET で 1 ページ目と 5 万ページ目（後ろから 1 ページ目）を読む
EXPLAIN (ANALYZE, BUFFERS, COSTS OFF)
SELECT id, created_at, title FROM posts
ORDER BY created_at DESC, id DESC
LIMIT 20 OFFSET 0;

EXPLAIN (ANALYZE, BUFFERS, COSTS OFF)
SELECT id, created_at, title FROM posts
ORDER BY created_at DESC, id DESC
LIMIT 20 OFFSET 999980;

-- 3. キーセットで同じ 5 万ページ目を読む。前のページの最後の行は (created_at, id) = ('2026-01-01 00:00:10+00', 21)
SELECT created_at, id FROM posts ORDER BY created_at DESC, id DESC OFFSET 999979 LIMIT 1;

EXPLAIN (ANALYZE, BUFFERS, COSTS OFF)
SELECT id, created_at, title FROM posts
WHERE (created_at, id) < ('2026-01-01 00:00:10+00', 21)
ORDER BY created_at DESC, id DESC
LIMIT 20;

-- 4. ページを読む間に新しい投稿が 3 件入ると、OFFSET の 2 ページ目は 1 ページ目と重なる
CREATE TABLE feed (id int PRIMARY KEY, created_at timestamptz NOT NULL);
INSERT INTO feed SELECT i, timestamptz '2026-01-01 00:00:00+00' + i * interval '1 minute'
FROM generate_series(1, 20) AS i;

SELECT id FROM feed ORDER BY created_at DESC, id DESC LIMIT 5 OFFSET 0;   -- 1 ページ目
INSERT INTO feed SELECT i, timestamptz '2026-01-01 00:00:00+00' + i * interval '1 minute'
FROM generate_series(21, 23) AS i;                                         -- 新しい投稿が 3 件
SELECT id FROM feed ORDER BY created_at DESC, id DESC LIMIT 5 OFFSET 5;   -- OFFSET の 2 ページ目
SELECT id FROM feed
WHERE (created_at, id) < (timestamptz '2026-01-01 00:16:00+00', 16)
ORDER BY created_at DESC, id DESC LIMIT 5;                                 -- キーセットの 2 ページ目

-- 5. 逆に 1 ページ目の投稿が 2 件消えると、OFFSET の 2 ページ目は 2 件を飛ばす
DELETE FROM feed WHERE id IN (21, 22, 23);
SELECT id FROM feed ORDER BY created_at DESC, id DESC LIMIT 5 OFFSET 0;   -- 1 ページ目
DELETE FROM feed WHERE id IN (19, 18);                                     -- 1 ページ目の 2 件が消える
SELECT id FROM feed ORDER BY created_at DESC, id DESC LIMIT 5 OFFSET 5;   -- OFFSET の 2 ページ目
SELECT id FROM feed
WHERE (created_at, id) < (timestamptz '2026-01-01 00:16:00+00', 16)
ORDER BY created_at DESC, id DESC LIMIT 5;                                 -- キーセットの 2 ページ目

-- 6. キーに created_at しか使わないと、同じ時刻の行がページの境目で消える
CREATE TABLE tie (id int PRIMARY KEY, created_at timestamptz NOT NULL);
INSERT INTO tie VALUES
  (1, '2026-01-01 10:00+00'), (2, '2026-01-01 10:01+00'), (3, '2026-01-01 10:02+00'),
  (4, '2026-01-01 10:02+00'), (5, '2026-01-01 10:03+00'), (6, '2026-01-01 10:04+00');
SELECT id, created_at FROM tie ORDER BY created_at DESC, id DESC LIMIT 3;         -- 1 ページ目
SELECT id, created_at FROM tie WHERE created_at < '2026-01-01 10:02+00'
ORDER BY created_at DESC LIMIT 3;                                                  -- created_at だけ
SELECT id, created_at FROM tie WHERE (created_at, id) < ('2026-01-01 10:02+00', 4)
ORDER BY created_at DESC, id DESC LIMIT 3;                                         -- (created_at, id)

-- 7. 行の比較を OR で書いた場合と、昇順と降順が混ざる並びの場合（2 万 5001 ページ目。前のページの最後は id 500001）
SELECT created_at, id FROM posts ORDER BY created_at DESC, id DESC OFFSET 499999 LIMIT 1;

EXPLAIN (ANALYZE, BUFFERS, COSTS OFF)
SELECT id FROM posts
WHERE created_at < '2026-01-03 21:26:40+00'
   OR (created_at = '2026-01-03 21:26:40+00' AND id < 500001)
ORDER BY created_at DESC, id DESC
LIMIT 20;

-- 索引で絞れる条件 created_at <= x を外側に出す（同じ索引のまま）
EXPLAIN (ANALYZE, BUFFERS, COSTS OFF)
SELECT id FROM posts
WHERE created_at <= '2026-01-03 21:26:40+00'
  AND (created_at < '2026-01-03 21:26:40+00' OR id < 500001)
ORDER BY created_at DESC, id DESC
LIMIT 20;

-- created_at は新しい順、同じ時刻の中は id の小さい順に並べたい場合。行の比較 (a, b) < (x, y) は使えない
EXPLAIN (ANALYZE, BUFFERS, COSTS OFF)
SELECT id FROM posts
WHERE created_at < '2026-01-03 21:26:40+00'
   OR (created_at = '2026-01-03 21:26:40+00' AND id > 500001)
ORDER BY created_at DESC, id ASC
LIMIT 20;

-- 並びに合わせた索引を作り、索引で絞れる条件 created_at <= x を外側に出す
CREATE INDEX posts_created_desc_id_asc ON posts (created_at DESC, id ASC);
EXPLAIN (ANALYZE, BUFFERS, COSTS OFF)
SELECT id FROM posts
WHERE created_at <= '2026-01-03 21:26:40+00'
  AND (created_at < '2026-01-03 21:26:40+00' OR id > 500001)
ORDER BY created_at DESC, id ASC
LIMIT 20;
DROP INDEX posts_created_desc_id_asc;

-- 8. 総件数を数える COUNT(*) は、ページを何ページ目まで読んでも全件を読む
EXPLAIN (ANALYZE, BUFFERS, COSTS OFF)
SELECT count(*) FROM posts;
