-- パーティションを分けた表に、パーティションキーを含まない主キーを付けようとする
SET client_min_messages = warning;
DROP TABLE IF EXISTS orders;
CREATE TABLE orders (
    id         bigint    NOT NULL,
    created_at timestamp NOT NULL
) PARTITION BY RANGE (created_at);
CREATE TABLE orders_2026_10 PARTITION OF orders FOR VALUES FROM ('2026-10-01') TO ('2026-11-01');
CREATE TABLE orders_2026_11 PARTITION OF orders FOR VALUES FROM ('2026-11-01') TO ('2026-12-01');

\echo '== (1) id だけの主キー'
ALTER TABLE orders ADD PRIMARY KEY (id);

\echo '== (2) パーティションキーを含めた主キー'
ALTER TABLE orders ADD PRIMARY KEY (id, created_at);

\echo '== (3) 同じ id を別の月に入れる'
INSERT INTO orders VALUES (1, '2026-10-31 23:59'), (1, '2026-11-01 00:00');
SELECT tableoid::regclass AS partition, id, created_at FROM orders ORDER BY created_at;

\echo '== (4) 親表の索引と、各パーティションの索引'
SELECT indexrelid::regclass AS index, indrelid::regclass AS on_table
FROM pg_index WHERE indrelid::regclass::text LIKE 'orders%' ORDER BY 1;
