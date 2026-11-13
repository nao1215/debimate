"""コメントを保存した直後に一覧を読み、自分のコメントが載っていない割合を数える。

プロジェクションは 0.5 秒ごとに新しいイベントをまとめて読み取りモデルに反映する。
実行: python3 read_after_write.py <SQLite のファイル> [試行の回数]
"""
import random
import sqlite3
import sys
import threading
import time

DB = sys.argv[1]
POLL = 0.5  # プロジェクションがイベントを読みに行く間隔（秒）


def connect():
    con = sqlite3.connect(DB, isolation_level=None, timeout=30, check_same_thread=False)
    con.execute("PRAGMA synchronous=OFF")
    return con


def setup():
    con = connect()
    con.executescript("""
        PRAGMA journal_mode=WAL;
        DROP TABLE IF EXISTS events; DROP TABLE IF EXISTS comment_list; DROP TABLE IF EXISTS checkpoint;
        CREATE TABLE events(seq INTEGER PRIMARY KEY, body TEXT);
        CREATE TABLE comment_list(seq INTEGER PRIMARY KEY, body TEXT);
        CREATE TABLE checkpoint(pos INTEGER);
        INSERT INTO checkpoint VALUES (0);
    """)
    return con


def projector(stop):
    con = connect()
    while not stop.is_set():
        pos = con.execute("SELECT pos FROM checkpoint").fetchone()[0]
        rows = con.execute("SELECT seq, body FROM events WHERE seq > ?", (pos,)).fetchall()
        if rows:
            con.execute("BEGIN")
            con.executemany("INSERT INTO comment_list VALUES (?, ?)", rows)
            con.execute("UPDATE checkpoint SET pos = ?", (rows[-1][0],))
            con.execute("COMMIT")
        time.sleep(POLL)


def post(con, body):  # 書き込み側: イベントを追記し、その位置（seq）を返す
    return con.execute("INSERT INTO events(body) VALUES (?)", (body,)).lastrowid


def list_comments(con, wait_for=None, timeout=2.0):  # 参照側
    start = time.monotonic()
    while wait_for is not None and time.monotonic() - start < timeout:
        if con.execute("SELECT pos FROM checkpoint").fetchone()[0] >= wait_for:
            break
        time.sleep(0.005)
    rows = con.execute("SELECT seq FROM comment_list").fetchall()
    return {r[0] for r in rows}, time.monotonic() - start


if __name__ == "__main__":
    trials = int(sys.argv[2]) if len(sys.argv) > 2 else 100
    setup()
    stop = threading.Event()
    threading.Thread(target=projector, args=(stop,), daemon=True).start()
    con, rng = connect(), random.Random(0)
    for delay in (0.0, 0.1, 0.25, 0.5):  # 保存から一覧を読むまでの間
        missing = 0
        for i in range(trials):
            time.sleep(rng.uniform(0, POLL))  # プロジェクションの周期と無関係な時刻に保存する
            seq = post(con, f"comment {i}")
            time.sleep(delay)
            seen, _ = list_comments(con)
            missing += seq not in seen
        print(f"保存の {delay * 1000:.0f}ms 後に読む\t載っていない {missing}/{trials}")
    waits = []
    for i in range(trials):  # 直し方: 保存で返した seq までプロジェクションが進むのを待ってから読む
        time.sleep(rng.uniform(0, POLL))
        seq = post(con, f"wait {i}")
        seen, waited = list_comments(con, wait_for=seq)
        assert seq in seen
        waits.append(waited)
    waits.sort()
    print(f"seq まで待って読む\t載っていない 0/{trials}\t待ち時間 中央値 {waits[trials // 2] * 1000:.0f}ms"
          f" 最大 {waits[-1] * 1000:.0f}ms")
    stop.set()
