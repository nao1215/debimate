-- 「10 月の売上」を 4 通りの定義で数える
SELECT 'items, all'       AS definition, SUM(i.quantity * i.price) AS value FROM order_items i
UNION ALL
SELECT 'items, completed', SUM(i.quantity * i.price) FROM order_items i JOIN orders o USING (order_id) WHERE o.status = 'completed'
UNION ALL
SELECT 'payments, all',    SUM(p.amount) FROM payments p
UNION ALL
SELECT 'payments, completed', SUM(p.amount) FROM payments p JOIN orders o USING (order_id) WHERE o.status = 'completed';
