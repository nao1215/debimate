-- Query Processing のノートの実験で使う表（PostgreSQL 18）

-- 1. events: 500 万行。1,000 人の古い利用者の行は id の全体に散らばり、
--    最後の 10,000 行だけが、新しく大量に使い始めた利用者 1 の行になる。
DROP TABLE IF EXISTS events;
CREATE TABLE events (id bigint PRIMARY KEY, user_id int NOT NULL, payload text);
INSERT INTO events
SELECT i, 2 + (i % 1000), 'x' FROM generate_series(1, 4990000) i;
INSERT INTO events
SELECT i, 1, 'x' FROM generate_series(4990001, 5000000) i;
CREATE INDEX events_user_id_idx ON events (user_id);
ANALYZE events;

-- 2. customers: city が決まれば pref と region も決まる（列どうしが無関係ではない）。
--    city は 1,000 通り、pref は 50 通り、region は 5 通り。
DROP TABLE IF EXISTS orders, customers;
CREATE TABLE customers (id int PRIMARY KEY, city int, pref int, region int);
INSERT INTO customers
SELECT i, i % 1000, (i % 1000) / 20, (i % 1000) / 200
FROM generate_series(1, 1000000) i;
CREATE TABLE orders (id int PRIMARY KEY, customer_id int, amount int);
INSERT INTO orders
SELECT i, 1 + ((i::bigint * 7919) % 1000000)::int, i % 1000
FROM generate_series(1, 5000000) i;
CREATE INDEX orders_customer_id_idx ON orders (customer_id);
ANALYZE customers;
ANALYZE orders;

-- 3. t1 〜 t16: 結合する表の数と、計画を作る時間を測るための 1,000 行の表。
DO $$
BEGIN
  FOR k IN 1..16 LOOP
    EXECUTE format('DROP TABLE IF EXISTS t%s', k);
    EXECUTE format('CREATE TABLE t%s (id int PRIMARY KEY, v int)', k);
    EXECUTE format('INSERT INTO t%s SELECT i, i %% 100 FROM generate_series(1, 1000) i', k);
    EXECUTE format('ANALYZE t%s', k);
  END LOOP;
END $$;
