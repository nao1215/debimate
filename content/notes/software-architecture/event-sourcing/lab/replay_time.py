"""Measure how long restoring an Order takes, by stream length and snapshot interval.

Event store (SQLite through Python's sqlite3, a file DB):
  events(stream_id, version, type, payload)  PRIMARY KEY (stream_id, version)
  snapshots(stream_id, version, state)       PRIMARY KEY (stream_id, version)
  payload and state are JSON text.

The stream of order-1 has events of three kinds: OrderPlaced (version 1),
then LineAdded / LineRemoved alternating with a fixed pattern, so the order
keeps about 5 lines. A snapshot is the JSON of the Order state at that version.

Restore (measured):
  1. read the latest snapshot whose version <= the stream's last version
     (skipped for "no snapshot"),
  2. SELECT the events after that version ORDER BY version,
  3. json.loads each payload and apply it to the Order (the note's apply).
The restore runs on a new connection opened after the stream was written.
The DB file is still in the OS page cache, so the time is mostly the reading,
decoding and applying of the events, not disk I/O.

Stream lengths: 0 to 5,000 events every 25 (not a multiple of 100, so the
points fall between snapshots too). Snapshot interval: none, 500, 100.
Each point is the fastest of 30 restores: the whole set of streams is swept
15 times, 2 restores each time. The machine was shared with other jobs, and a
busy spell lasts several seconds; spreading the tries over the ~45 s run keeps
such a spell from deciding a point. The garbage collector is off during the
timing, as timeit does.

Run: python3 replay_time.py   (Python 3.10+, standard library only)
Timings depend on the machine; the restored version and the count of replayed
events are deterministic.
"""

import gc
import json
import os
import shutil
import sqlite3
import tempfile
import time

MAX_EVENTS = 5000
STEP = 25
INTERVALS = [None, 500, 100]
SWEEPS = 15
REPEATS = 2


def event_at(v):
    if v == 1:
        return "OrderPlaced", {"order_id": "order-1", "lines": []}
    sku = f"SKU-{v % 7}"
    if v % 2 == 0:
        return "LineAdded", {"sku": sku, "quantity": 1 + v % 3, "unit_price": 1000 + v % 5 * 100}
    return "LineRemoved", {"sku": f"SKU-{(v - 1) % 7}"}


class Order:
    def __init__(self):
        self.id, self.status, self.lines, self.version = None, None, {}, 0

    def apply(self, kind, e):
        if kind == "OrderPlaced":
            self.id, self.status = e["order_id"], "draft"
            self.lines = {}
        elif kind == "LineAdded":
            self.lines[e["sku"]] = (e["quantity"], e["unit_price"])
        elif kind == "LineRemoved":
            self.lines.pop(e["sku"], None)
        else:
            raise ValueError(f"unsupported event: {kind}")
        self.version += 1

    def to_json(self):
        return json.dumps({"id": self.id, "status": self.status,
                           "lines": self.lines, "version": self.version})

    @classmethod
    def from_json(cls, text):
        d = json.loads(text)
        o = cls()
        o.id, o.status, o.version = d["id"], d["status"], d["version"]
        o.lines = {k: tuple(v) for k, v in d["lines"].items()}
        return o


def build(con, n, interval):
    con.executescript("""
        DROP TABLE IF EXISTS events; DROP TABLE IF EXISTS snapshots;
        CREATE TABLE events(stream_id TEXT, version INTEGER, type TEXT, payload TEXT,
                            PRIMARY KEY (stream_id, version));
        CREATE TABLE snapshots(stream_id TEXT, version INTEGER, state TEXT,
                               PRIMARY KEY (stream_id, version));
    """)
    o = Order()
    con.execute("BEGIN")
    for v in range(1, n + 1):
        kind, e = event_at(v)
        con.execute("INSERT INTO events VALUES ('order-1', ?, ?, ?)", (v, kind, json.dumps(e)))
        o.apply(kind, e)
        if interval and v % interval == 0:
            con.execute("INSERT INTO snapshots VALUES ('order-1', ?, ?)", (v, o.to_json()))
    con.execute("COMMIT")
    return o


def restore(con, use_snapshot):
    o, after = Order(), 0
    if use_snapshot:
        row = con.execute("SELECT version, state FROM snapshots WHERE stream_id='order-1' "
                          "ORDER BY version DESC LIMIT 1").fetchone()
        if row:
            after, o = row[0], Order.from_json(row[1])
    replayed = 0
    for kind, payload in con.execute(
            "SELECT type, payload FROM events WHERE stream_id='order-1' AND version > ? "
            "ORDER BY version", (after,)):
        o.apply(kind, json.loads(payload))
        replayed += 1
    return o, replayed


def main():
    tmp = tempfile.mkdtemp()
    cases = [(n, i) for n in range(0, MAX_EVENTS + 1, STEP) for i in INTERVALS]
    expected, best, replayed = {}, {}, {}
    for n, interval in cases:  # one DB file per stream, written by one connection
        con = sqlite3.connect(os.path.join(tmp, f"{n}-{interval}.db"), isolation_level=None)
        expected[n, interval] = build(con, n, interval)
        con.close()
    for _ in range(SWEEPS):
        for n, interval in cases:
            # restore through a new connection, as a new process would
            con = sqlite3.connect(os.path.join(tmp, f"{n}-{interval}.db"), isolation_level=None)
            gc.collect()
            gc.disable()  # as timeit does: keep the collector out of the timing
            for _ in range(REPEATS):
                t0 = time.perf_counter()
                o, count = restore(con, interval is not None)
                t = time.perf_counter() - t0
                best[n, interval] = min(t, best.get((n, interval), t))
            gc.enable()
            con.close()
            e = expected[n, interval]
            assert (o.version, o.lines) == (e.version, e.lines)
            replayed[n, interval] = count
    shutil.rmtree(tmp)

    print(f"SQLite {sqlite3.sqlite_version}, fastest of {SWEEPS} x {REPEATS} restores")
    print(f"{'events':>6} | " + " | ".join(
        f"{('every ' + str(i)) if i else 'no snapshot':>18}" for i in INTERVALS))
    print(f"{'':>6} | " + " | ".join(f"{'ms':>9} {'replayed':>8}" for _ in INTERVALS))
    for n in range(0, MAX_EVENTS + 1, STEP):
        print(f"{n:>6} | " + " | ".join(
            f"{best[n, i] * 1000:>9.3f} {replayed[n, i]:>8}" for i in INTERVALS))


if __name__ == "__main__":
    main()
