"""SQLite で取り出すカラムと条件を変えた実行計画を比べる。python3 orders_sqlite.py で実行。"""
import random
import sqlite3

random.seed(0)
db = sqlite3.connect(":memory:")
db.execute("CREATE TABLE orders (id INTEGER PRIMARY KEY, user_id INTEGER, amount INTEGER, status TEXT)")
db.executemany(
    "INSERT INTO orders (user_id, amount, status) VALUES (?, ?, 'paid')",
    ((random.randint(1, 10000), random.randint(1, 1000)) for _ in range(1_000_000)),
)
db.execute("CREATE INDEX idx_orders_user_amount ON orders(user_id, amount)")
queries = [
    "SELECT status FROM orders WHERE user_id = 42",
    "SELECT amount FROM orders WHERE user_id = 42",
    "SELECT status FROM orders WHERE user_id + 0 = 42",
    "SELECT status FROM orders WHERE amount = 42",
]
for q in queries:
    print(db.execute("EXPLAIN QUERY PLAN " + q).fetchone()[3])
db.execute("ANALYZE")
print("ANALYZE 後:", db.execute("EXPLAIN QUERY PLAN " + queries[3]).fetchone()[3])
