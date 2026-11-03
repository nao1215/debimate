"""SQLiteの全索引走査。python3 scan.pyで実行。"""
import sqlite3
with sqlite3.connect(":memory:") as db:
    db.executescript("""
    CREATE TABLE scan_demo (id INTEGER PRIMARY KEY, v INTEGER);
    INSERT INTO scan_demo VALUES (1, 30), (2, 10), (3, 20);
    CREATE INDEX scan_demo_v ON scan_demo(v);
    """)
    print("SQLite", sqlite3.sqlite_version)
    for row in db.execute("EXPLAIN QUERY PLAN SELECT v FROM scan_demo ORDER BY v"):
        print(row[3])
    assert db.execute("SELECT v FROM scan_demo ORDER BY v").fetchall() == [(10,), (20,), (30,)]
