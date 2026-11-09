-- 注文表と、日別の売上を事前に集計した materialized view を作る
DROP MATERIALIZED VIEW IF EXISTS daily_sales;
DROP TABLE IF EXISTS orders;

CREATE TABLE orders (
    id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ordered_at timestamptz NOT NULL,
    amount     integer     NOT NULL
);

-- 2026-01-01 から 365 日に 500 万件を散らす（乱数の種を固定する）
SELECT setseed(0.42);
INSERT INTO orders (ordered_at, amount)
SELECT timestamptz '2026-01-01 00:00:00+09' + random() * interval '365 days',
       (random() * 9000)::int + 100
FROM generate_series(1, 5000000);
ANALYZE orders;

CREATE MATERIALIZED VIEW daily_sales AS
SELECT (ordered_at AT TIME ZONE 'Asia/Tokyo')::date AS day,
       count(*)    AS orders,
       sum(amount) AS total
FROM orders
GROUP BY 1;
