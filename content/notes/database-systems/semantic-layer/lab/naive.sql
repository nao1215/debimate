-- 地域別の支払い額と販売点数を、4 つのテーブルを 1 回の JOIN でつないで数える
SELECT c.region,
       SUM(p.amount)   AS paid,
       SUM(i.quantity) AS qty,
       COUNT(*)        AS joined_rows
FROM orders o
JOIN customers   c ON c.customer_id = o.customer_id
JOIN order_items i ON i.order_id    = o.order_id
JOIN payments    p ON p.order_id    = o.order_id
GROUP BY c.region
ORDER BY c.region;
