"""Count lost updates when Save overwrites the whole Order aggregate.

Setup (SQLite through Python's sqlite3, a file DB, one connection per worker):
  - orders(id, version) and order_lines(order_id, sku, quantity).
  - Order A-1 starts with no lines. Each worker adds one line of its own
    (sku = "W<round>-<worker>") to the order.
  - FindByID reads the order and its lines in one transaction.
    Save deletes all lines and inserts the aggregate's lines (saveLines in the
    note), then commits. With the version check, Save first runs
    UPDATE orders SET version = v + 1 WHERE id = ? AND version = v
    and rolls back when 0 rows are updated (the note's ErrConflict).
  - The workers are interleaved by a scheduler seeded with SEED: every worker
    does FindByID, then Save, and the scheduler picks at random which worker
    takes its next step. The SQL itself runs on the real DB.
  - One round = K workers each adding 1 line. Expected lines after a round: K.
    Lost updates = K - lines actually stored by successful Saves that remain.
  - ROUNDS rounds per K, K = 1..8.

With the version check a conflicting Save fails instead of overwriting;
the caller (as the note says) re-reads with FindByID and retries. We count
the lines lost and the conflicts the callers saw.

Run: python3 lost_update.py   (Python 3.10+, standard library only)
"""

import os
import random
import sqlite3
import tempfile

SEED = 20261110
ROUNDS = 200
KS = range(1, 9)


def setup(path):
    con = sqlite3.connect(path, isolation_level=None)
    con.executescript("""
        DROP TABLE IF EXISTS orders; DROP TABLE IF EXISTS order_lines;
        CREATE TABLE orders(id TEXT PRIMARY KEY, version INTEGER NOT NULL);
        CREATE TABLE order_lines(order_id TEXT, sku TEXT, quantity INTEGER);
        INSERT INTO orders VALUES ('A-1', 0);
    """)
    con.close()


def find_by_id(con):
    con.execute("BEGIN")
    (version,) = con.execute("SELECT version FROM orders WHERE id='A-1'").fetchone()
    lines = con.execute(
        "SELECT sku, quantity FROM order_lines WHERE order_id='A-1'").fetchall()
    con.execute("COMMIT")
    return version, lines


def save(con, version, lines, check_version):
    """Returns True on success, False on conflict (ErrConflict)."""
    con.execute("BEGIN IMMEDIATE")
    if check_version:
        cur = con.execute(
            "UPDATE orders SET version = ? WHERE id='A-1' AND version = ?",
            (version + 1, version))
        if cur.rowcount == 0:  # ErrConflict
            con.execute("ROLLBACK")
            return False
    con.execute("DELETE FROM order_lines WHERE order_id='A-1'")
    con.executemany("INSERT INTO order_lines VALUES ('A-1', ?, ?)", lines)
    con.execute("COMMIT")
    return True


def worker(con, sku, check_version, retry):
    """A generator: each next() runs one step (FindByID or Save)."""
    stats = {"conflicts": 0}
    while True:
        version, lines = find_by_id(con)
        yield
        ok = save(con, version, lines + [(sku, 1)], check_version)
        if ok:
            break
        stats["conflicts"] += 1
        if not retry:
            break
        yield
    return stats["conflicts"]


def run_round(cons, k, rnd, rng, check_version, retry):
    path_con = cons[0]
    path_con.execute("DELETE FROM order_lines")
    path_con.execute("UPDATE orders SET version = 0")
    gens = {i: worker(cons[i], f"W{rnd}-{i}", check_version, retry) for i in range(k)}
    conflicts = 0
    while gens:
        i = rng.choice(sorted(gens))
        try:
            next(gens[i])
        except StopIteration as stop:
            conflicts += stop.value
            del gens[i]
    (stored,) = path_con.execute("SELECT COUNT(*) FROM order_lines").fetchone()
    return stored, conflicts


def main():
    tmp = tempfile.mkdtemp()
    path = os.path.join(tmp, "orders.db")
    setup(path)
    cons = [sqlite3.connect(path, isolation_level=None) for _ in range(max(KS))]
    print(f"SQLite {sqlite3.sqlite_version}, seed {SEED}, {ROUNDS} rounds per K")
    print("K = workers that read the same order and each add 1 line")
    print(f"{'K':>2} {'added':>6} | {'no version: lost':>16} | "
          f"{'version + retry: lost':>21} {'conflicts':>9}")
    for k in KS:
        row = [k, k * ROUNDS]
        for check in (False, True):
            rng = random.Random(SEED + k)
            lost = conflicts = 0
            for rnd in range(ROUNDS):
                stored, c = run_round(cons, k, rnd, rng, check, retry=check)
                lost += k - stored
                conflicts += c
            row += [lost, conflicts]
        print(f"{row[0]:>2} {row[1]:>6} | {row[2]:>16} | {row[4]:>21} {row[5]:>9}")
    for c in cons:
        c.close()


if __name__ == "__main__":
    main()
