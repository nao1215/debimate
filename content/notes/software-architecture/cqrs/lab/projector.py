"""価格の変更イベントを読み取りモデルに反映し、古い値のまま残る商品を数える。

実行: python3 projector.py <SQLite のファイル> [繰り返す回数]
"""
import queue
import random
import sqlite3
import sys
import threading
import time

DB = sys.argv[1]
PRODUCTS, UPDATES = 200, 10  # 200 商品の価格を 10 回ずつ変える


def setup(seed):
    con = sqlite3.connect(DB, isolation_level=None)
    con.executescript("""
        PRAGMA journal_mode=WAL; PRAGMA synchronous=OFF;
        DROP TABLE IF EXISTS events; DROP TABLE IF EXISTS price_view;
        CREATE TABLE events(seq INTEGER PRIMARY KEY, product_id INT, version INT, price INT);
        CREATE TABLE price_view(product_id INT PRIMARY KEY, version INT, price INT);
    """)
    rng = random.Random(seed)
    version = [0] * PRODUCTS
    for _ in range(PRODUCTS * UPDATES):  # 書き込み側: 商品ごとにバージョンを 1 つずつ進めて追記する
        p = rng.choice([i for i in range(PRODUCTS) if version[i] < UPDATES])
        version[p] += 1
        con.execute("INSERT INTO events(product_id, version, price) VALUES (?, ?, ?)",
                    (p, version[p], rng.randint(100, 9999)))
    con.executemany("INSERT INTO price_view VALUES (?, 0, 0)", [(p,) for p in range(PRODUCTS)])
    return con


lock, applied = threading.Lock(), [0]  # 処理したイベントの数
trace = []  # (商品, バージョン, worker, 受け取った時刻, 書いた時刻)


def apply(q, guard, seed, worker, t0):
    con = sqlite3.connect(DB, isolation_level=None, timeout=30)
    con.execute("PRAGMA synchronous=OFF")  # 実験を速くするため、ディスクへの同期を省く
    rng = random.Random(seed)
    sql = "UPDATE price_view SET version = ?, price = ? WHERE product_id = ?"
    if guard:
        sql += " AND version < ?"  # 自分より新しいバージョンが入っていれば書かない
    while (ev := q.get()) is not None:
        p, v, price = ev
        got = time.monotonic() - t0
        time.sleep(rng.uniform(0, 0.002))  # 画面用の整形などに掛かる時間
        con.execute(sql, (v, price, p, v) if guard else (v, price, p))
        with lock:
            applied[0] += 1
            trace.append((p, v, worker, got, time.monotonic() - t0))


def project(con, workers, route, guard, seed):
    events = con.execute("SELECT product_id, version, price FROM events ORDER BY seq").fetchall()
    shared = queue.Queue()
    qs = [shared] * workers if route == "shared" else [queue.Queue() for _ in range(workers)]
    start = time.monotonic()
    threads = [threading.Thread(target=apply, args=(qs[i], guard, seed * 100 + i, i, start))
               for i in range(workers)]
    for t in threads:
        t.start()
    for p, v, price in events:  # イベントは seq の順に配る
        qs[0 if route == "shared" else p % workers].put((p, v, price))
    for q in qs[:1] if route == "shared" else qs:
        for _ in range(workers if route == "shared" else 1):
            q.put(None)
    for t in threads:
        t.join()
    elapsed = time.monotonic() - start
    assert applied[0] == len(events)  # 取りこぼしたイベントは無い
    applied[0] = 0
    stale = con.execute("""
        SELECT count(*) FROM price_view v JOIN events e
          ON e.product_id = v.product_id AND e.version = ?
         WHERE v.price <> e.price""", (UPDATES,)).fetchone()[0]
    return elapsed, stale


def inversions():
    """書いた時刻の順に並べ、既に書いたものより古いバージョンを後から書いた回数。"""
    newest, count = {}, 0
    for p, v, _, _, wrote in sorted(trace, key=lambda r: r[4]):
        count += v < newest.get(p, 0)
        newest[p] = max(v, newest.get(p, 0))
    return count


VARIANTS = [("1 つ", 1, "shared", False), ("4 つで 1 つのキュー", 4, "shared", False),
            ("4 つで商品ごとに振り分け", 4, "partition", False),
            ("4 つで 1 つのキュー + バージョンの比較", 4, "shared", True)]

if __name__ == "__main__":
    runs = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    for name, workers, route, guard in VARIANTS:
        for seed in range(runs):
            con = setup(seed)
            elapsed, stale = project(con, workers, route, guard, seed)
            print(f"{name}\tseed={seed}\t{elapsed:.2f} 秒\t古い値の商品 {stale}/{PRODUCTS}"
                  f"\t順番の逆転 {inversions()} 回")
            if workers == 4 and route == "shared" and not guard and seed == 0:
                with open("trace.tsv", "w") as f:  # 図に使う、各イベントを書いた時刻
                    for row in trace:
                        f.write("\t".join(f"{x:.4f}" if isinstance(x, float) else str(x)
                                           for x in row) + "\n")
            trace.clear()
            con.close()
