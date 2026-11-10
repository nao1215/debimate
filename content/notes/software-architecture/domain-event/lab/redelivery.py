"""Reproduce at-least-once delivery and count stock reserved twice.

This is a simulation of the failure, but the handler's SQL runs on a real
SQLite DB (Python's sqlite3, a file DB).

Setup:
  - N = 10,000 OrderConfirmed events, each reserving 1 unit of SKU X.
    The stock starts at N units, so every event can be reserved once.
  - The broker delivers each event to the handler. The handler runs one
    transaction and commits; after the commit it acks the broker.
  - With probability P the consumer crashes between the commit and the ack.
    The broker never saw the ack, so it delivers the same event again.
    The redelivery can crash at the same point again (each attempt is
    independent), so an event is delivered until one ack gets through.
  - Handler without the record: UPDATE stock SET quantity = quantity - 1.
  - Handler with the record (the note's Handle): in the same transaction,
    INSERT OR IGNORE INTO processed(event_id); if no row was inserted, the
    event was already processed and the handler does nothing.
  - Over-reserved units = units taken from the stock minus N.

P = 0, 0.1 %, 1 %, 5 %, 10 %, 20 %. The random crashes use a fixed seed and
the same sequence of crashes for both handlers.

Run: python3 redelivery.py   (Python 3.10+, standard library only)
"""

import os
import random
import sqlite3
import tempfile

SEED = 20261110
N = 10_000
RATES = [0.0, 0.001, 0.01, 0.05, 0.10, 0.20]


def setup(con):
    con.executescript(f"""
        DROP TABLE IF EXISTS stock; DROP TABLE IF EXISTS processed;
        CREATE TABLE stock(sku TEXT PRIMARY KEY, quantity INTEGER NOT NULL);
        CREATE TABLE processed(event_id TEXT PRIMARY KEY);
        INSERT INTO stock VALUES ('X', {N});
    """)


def handle(con, event_id, idempotent):
    con.execute("BEGIN")
    if idempotent:
        cur = con.execute("INSERT OR IGNORE INTO processed VALUES (?)", (event_id,))
        if cur.rowcount == 0:  # already processed: do nothing
            con.execute("COMMIT")
            return
    con.execute("UPDATE stock SET quantity = quantity - 1 WHERE sku = 'X'")
    con.execute("COMMIT")


def run(con, rate, idempotent):
    setup(con)
    rng = random.Random(SEED)
    deliveries = 0
    for i in range(N):
        event_id = f"e{i}"
        while True:
            handle(con, event_id, idempotent)
            deliveries += 1
            if rng.random() >= rate:  # the ack reached the broker
                break
            # crashed after the commit, before the ack: the broker redelivers
    (left,) = con.execute("SELECT quantity FROM stock WHERE sku='X'").fetchone()
    return deliveries, (N - left) - N


def main():
    path = os.path.join(tempfile.mkdtemp(), "stock.db")
    con = sqlite3.connect(path, isolation_level=None)
    con.execute("PRAGMA synchronous = OFF")
    print(f"SQLite {sqlite3.sqlite_version}, seed {SEED}, {N:,} events, 1 unit each")
    print(f"{'crash rate':>10} {'deliveries':>10} | {'over-reserved units':>19} "
          f"| {'over-reserved units':>19}")
    print(f"{'':>10} {'':>10} | {'(no record)':>19} | {'(processed record)':>19}")
    for rate in RATES:
        d1, over_plain = run(con, rate, idempotent=False)
        d2, over_idem = run(con, rate, idempotent=True)
        assert d1 == d2
        print(f"{rate * 100:>9.1f}% {d1:>10,} | {over_plain:>19,} | {over_idem:>19,}")
    con.close()


if __name__ == "__main__":
    main()
