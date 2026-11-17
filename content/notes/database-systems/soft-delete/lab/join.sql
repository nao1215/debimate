-- 予約を取り消すと deleted_at に日時が入る、削除フラグの表
CREATE TABLE products (
  id         int PRIMARY KEY,
  name       text NOT NULL,
  deleted_at timestamptz
);
CREATE TABLE reservations (
  id         int PRIMARY KEY,
  product_id int NOT NULL REFERENCES products (id),
  deleted_at timestamptz
);
INSERT INTO products VALUES (1, 'カメラ', NULL), (2, '三脚', NULL), (3, 'レンズ', NULL);
INSERT INTO reservations VALUES
  (10, 2, NULL),    -- 三脚: 有効な予約が 1 件
  (11, 3, now());   -- レンズ: 予約が 1 件あったが取り消し済み

\echo '-- (A) 取り消した予約を WHERE で除く'
SELECT p.name, count(r.id) AS active_count
FROM products p
LEFT JOIN reservations r ON r.product_id = p.id
WHERE p.deleted_at IS NULL
  AND r.deleted_at IS NULL
GROUP BY p.id, p.name
ORDER BY p.id;

\echo '-- (B) 取り消した予約を ON で除く'
SELECT p.name, count(r.id) AS active_count
FROM products p
LEFT JOIN reservations r ON r.product_id = p.id AND r.deleted_at IS NULL
WHERE p.deleted_at IS NULL
GROUP BY p.id, p.name
ORDER BY p.id;

\echo '-- (C) 絞り込みを忘れる'
SELECT p.name, count(r.id) AS active_count
FROM products p
LEFT JOIN reservations r ON r.product_id = p.id
WHERE p.deleted_at IS NULL
GROUP BY p.id, p.name
ORDER BY p.id;

\echo '-- (D) 有効な予約だけを返すビューを結合する'
CREATE VIEW active_reservations AS
  SELECT * FROM reservations WHERE deleted_at IS NULL;
SELECT p.name, count(r.id) AS active_count
FROM products p
LEFT JOIN active_reservations r ON r.product_id = p.id
WHERE p.deleted_at IS NULL
GROUP BY p.id, p.name
ORDER BY p.id;

\echo '-- (A) の WHERE の前の行（結合した直後）'
SELECT p.name, r.id AS reservation_id, r.deleted_at IS NOT NULL AS canceled
FROM products p
LEFT JOIN reservations r ON r.product_id = p.id
ORDER BY p.id;
