"""Transactional Outbox の実験（PostgreSQL 18、psycopg 3）。

使い方は lab/README.md。各サブコマンドは表を作り直してから走り、
結果を標準出力と output/<名前>.json に書く。
"""
import json
import multiprocessing as mp
import os
import random
import signal
import sys
import threading
import time
from pathlib import Path

import psycopg

DSN = os.environ.get("OUTBOX_DSN", "host=localhost port=55432 user=postgres password=pg")
OUT = Path(__file__).parent / "output"


def conn(dbname="postgres", autocommit=False):
    return psycopg.connect(DSN + f" dbname={dbname}", autocommit=autocommit)


def save(name, data):
    OUT.mkdir(exist_ok=True)
    (OUT / f"{name}.json").write_text(json.dumps(data, ensure_ascii=False, indent=1))


def reset_outbox():
    with conn(autocommit=True) as c:
        c.execute("DROP TABLE IF EXISTS orders, outbox")
        c.execute("CREATE TABLE orders (id bigserial PRIMARY KEY, item text, created_at timestamptz DEFAULT clock_timestamp())")
        c.execute("""
            CREATE TABLE outbox (
              id         bigserial PRIMARY KEY,
              order_id   bigint NOT NULL,
              type       text   NOT NULL,
              payload    jsonb  NOT NULL,
              tx         xid8   NOT NULL DEFAULT pg_current_xact_id(),
              published  boolean NOT NULL DEFAULT false
            )""")


def reset_broker():
    """ブローカーの代わり。別の DB の表に、届いた順に積む。"""
    with conn(autocommit=True) as c:
        if not c.execute("SELECT 1 FROM pg_database WHERE datname='broker'").fetchone():
            c.execute("CREATE DATABASE broker")
    with conn("broker", autocommit=True) as b:
        b.execute("DROP TABLE IF EXISTS events")
        b.execute("CREATE TABLE events (seq bigserial PRIMARY KEY, outbox_id bigint, order_id bigint, type text)")


# ---------------------------------------------------------------- 1. 追い越し
def overtake():
    """id 1 を先に取ったトランザクションが、id 2 より後にコミットする。id のカーソルで読む relay は 1 を飛ばす。"""
    reset_outbox()
    t0 = time.monotonic()
    log = []

    def at():
        return round(time.monotonic() - t0, 2)

    def tx_a():  # 注文 A: 行を入れた後、在庫の確認などで 1.5 秒かかってからコミット
        with conn() as c:
            oid = c.execute("INSERT INTO outbox (order_id, type, payload) VALUES (1, 'OrderPlaced', '{}') RETURNING id").fetchone()[0]
            log.append({"t": at(), "who": "A", "what": "insert", "id": oid})
            time.sleep(1.5)
            c.commit()
            log.append({"t": at(), "who": "A", "what": "commit", "id": oid})

    def tx_b():  # 注文 B: 0.3 秒後に始まり、すぐコミット
        time.sleep(0.3)
        with conn() as c:
            oid = c.execute("INSERT INTO outbox (order_id, type, payload) VALUES (2, 'OrderPlaced', '{}') RETURNING id").fetchone()[0]
            log.append({"t": at(), "who": "B", "what": "insert", "id": oid})
            c.commit()
            log.append({"t": at(), "who": "B", "what": "commit", "id": oid})

    def relay():  # 0.5 秒ごとに「前回の最大の id より大きい行」を読む
        cursor = 0
        with conn(autocommit=True) as c:
            for _ in range(6):
                time.sleep(0.5)
                ids = [r[0] for r in c.execute("SELECT id FROM outbox WHERE id > %s ORDER BY id", (cursor,))]
                log.append({"t": at(), "who": "relay", "what": "poll", "cursor": cursor, "ids": ids})
                if ids:
                    cursor = ids[-1]

    ths = [threading.Thread(target=f) for f in (tx_a, tx_b, relay)]
    for th in ths:
        th.start()
    for th in ths:
        th.join()
    with conn(autocommit=True) as c:
        in_table = [r[0] for r in c.execute("SELECT id FROM outbox ORDER BY id")]
    sent = sorted({i for e in log if e["what"] == "poll" for i in e["ids"]})
    log.sort(key=lambda e: e["t"])
    for e in log:
        print(e)
    print("outbox にある id:", in_table, " relay が送った id:", sent)
    save("overtake", {"log": log, "in_table": in_table, "sent": sent})


# ---------------------------------------------------------------- 2. 負荷をかけた取りこぼし
def writer(n, work_ms, seed):
    rnd = random.Random(seed)
    with conn() as c:
        for _ in range(n):
            oid = c.execute("INSERT INTO orders (item) VALUES ('book') RETURNING id").fetchone()[0]
            c.execute("INSERT INTO outbox (order_id, type, payload) VALUES (%s, 'OrderPlaced', '{}')", (oid,))
            if work_ms:
                time.sleep(rnd.uniform(0, work_ms) / 1000)
            c.commit()


def relay_by_id(stop, sent):
    cursor = 0
    with conn(autocommit=True) as c:
        while True:
            done = stop.is_set()
            rows = c.execute("SELECT id FROM outbox WHERE id > %s ORDER BY id LIMIT 500", (cursor,)).fetchall()
            for (i,) in rows:
                sent.append(i)
            if rows:
                cursor = rows[-1][0]
            elif done:
                return
            time.sleep(0.05)


def relay_by_xmin(stop, sent):
    """書いたトランザクション ID（xid8）で読み、まだ終わっていないトランザクションより前のトランザクションだけを送る。"""
    last = ("0", 0)
    with conn(autocommit=True) as c:
        while True:
            done = stop.is_set()
            rows = c.execute(
                """SELECT tx::text, id FROM outbox
                   WHERE (tx, id) > (%s::xid8, %s)
                     AND tx < pg_snapshot_xmin(pg_current_snapshot())
                   ORDER BY tx, id LIMIT 500""", last).fetchall()
            for tx, i in rows:
                sent.append(i)
            if rows:
                last = rows[-1]
            elif done:
                return
            time.sleep(0.05)


def relay_by_flag(stop, sent):
    """未送信の印（published = false）の行を読み、送ったら印を変える。"""
    with conn() as c:
        while True:
            done = stop.is_set()
            rows = c.execute("SELECT id FROM outbox WHERE NOT published ORDER BY id LIMIT 500 FOR UPDATE SKIP LOCKED").fetchall()
            for (i,) in rows:
                sent.append(i)
            if rows:
                c.execute("UPDATE outbox SET published = true WHERE id = ANY(%s)", ([r[0] for r in rows],))
            c.commit()
            if not rows and done:
                return
            time.sleep(0.05)


RELAYS = {"id": relay_by_id, "xmin": relay_by_xmin, "flag": relay_by_flag}


def load(writers=8, per_writer=500, work_ms=20):
    result = {}
    for name, relay in RELAYS.items():
        reset_outbox()
        stop, sent = threading.Event(), []
        r = threading.Thread(target=relay, args=(stop, sent))
        r.start()
        ws = [threading.Thread(target=writer, args=(per_writer, work_ms, k)) for k in range(writers)]
        t0 = time.monotonic()
        for w in ws:
            w.start()
        for w in ws:
            w.join()
        elapsed = time.monotonic() - t0
        time.sleep(0.5)
        stop.set()
        r.join()
        with conn(autocommit=True) as c:
            total = c.execute("SELECT count(*) FROM outbox").fetchone()[0]
        missed = total - len(set(sent))
        result[name] = {"total": total, "sent": len(sent), "unique": len(set(sent)), "missed": missed,
                        "writers": writers, "work_ms": work_ms, "seconds": round(elapsed, 1)}
        print(name, result[name])
    return result


def load_all(reps=5):
    """INSERT からコミットまでの処理時間を 0・5・20 ms の 3 段に変え、それぞれ reps 回ずつ繰り返す。"""
    out = {}
    for work_ms in (0, 5, 20):
        out[str(work_ms)] = []
        for k in range(reps):
            print(f"--- INSERT からコミットまでの処理 0〜{work_ms} ms（{k + 1} 回目）")
            out[str(work_ms)].append(load(work_ms=work_ms))
    save("load", out)


# ---------------------------------------------------------------- 3. WAL のコミット順
def wal_order(writers=8, per_writer=500, work_ms=20):
    """論理デコーディング（test_decoding）で、outbox の INSERT をコミットの順に読む。"""
    reset_outbox()
    with conn(autocommit=True) as c:
        c.execute("SELECT pg_drop_replication_slot(slot_name) FROM pg_replication_slots WHERE slot_name='outbox_slot'")
        c.execute("SELECT pg_create_logical_replication_slot('outbox_slot', 'test_decoding')")
    ws = [threading.Thread(target=writer, args=(per_writer, work_ms, k)) for k in range(writers)]
    for w in ws:
        w.start()
    for w in ws:
        w.join()
    ids = []
    with conn(autocommit=True) as c:
        for (data,) in c.execute("SELECT data FROM pg_logical_slot_get_changes('outbox_slot', NULL, NULL)"):
            if data.startswith("table public.outbox: INSERT:"):
                ids.append(int(data.split("id[bigint]:")[1].split()[0]))
        c.execute("SELECT pg_drop_replication_slot('outbox_slot')")
        total = c.execute("SELECT count(*) FROM outbox").fetchone()[0]
    inversions = sum(1 for a, b in zip(ids, ids[1:]) if b < a)
    print(f"WAL から読んだ行 {len(ids)} / outbox の行 {total}、id が前の行より小さくなった箇所 {inversions}")
    print("先頭 20 行の id（コミット順）:", ids[:20])
    save("wal_order", {"read": len(ids), "total": total, "inversions": inversions, "head": ids[:40], "ids": ids})


def wal_stall():
    """書き込み中の長いトランザクションがあっても、論理デコーディングは先にコミットした行を返すか。"""
    reset_outbox()
    with conn(autocommit=True) as c:
        c.execute("DROP TABLE IF EXISTS report")
        c.execute("CREATE TABLE report (n int)")
        c.execute("SELECT pg_drop_replication_slot(slot_name) FROM pg_replication_slots WHERE slot_name='outbox_slot'")
        c.execute("SELECT pg_create_logical_replication_slot('outbox_slot', 'test_decoding')")
    batch = conn()
    batch.execute("INSERT INTO report VALUES (1)")  # 集計のトランザクション: 書き込みを始めたまま開いておく
    with conn() as c:
        for _ in range(5):
            c.execute("INSERT INTO outbox (order_id, type, payload) VALUES (1, 'OrderPlaced', '{}')")
            c.commit()

    def changes():
        with conn(autocommit=True) as c:
            rows = c.execute("SELECT data FROM pg_logical_slot_get_changes('outbox_slot', NULL, NULL)").fetchall()
        return [int(d.split("id[bigint]:")[1].split()[0]) for (d,) in rows if d.startswith("table public.outbox: INSERT:")]

    while_open = changes()
    with conn(autocommit=True) as c:
        snap = c.execute("SELECT pg_snapshot_xmin(pg_current_snapshot())::text").fetchone()[0]
        xmin_rows = c.execute("SELECT count(*) FROM outbox WHERE tx < pg_snapshot_xmin(pg_current_snapshot())").fetchone()[0]
    batch.commit(); batch.close()
    with conn(autocommit=True) as c:
        c.execute("SELECT pg_drop_replication_slot('outbox_slot')")

    # 比べる対象: SELECT だけのトランザクションを開いたまま、outbox に 5 行をコミットする
    reader = conn()
    reader.execute("SELECT count(*) FROM report")  # 読むだけで、書き込みはしない
    with conn() as c:
        new_ids = []
        for _ in range(5):
            new_ids.append(c.execute("INSERT INTO outbox (order_id, type, payload) VALUES (2, 'OrderPlaced', '{}') RETURNING id").fetchone()[0])
            c.commit()
    with conn(autocommit=True) as c:
        reader_xid = c.execute("SELECT backend_xid::text FROM pg_stat_activity WHERE pid = %s", (reader.info.backend_pid,)).fetchone()[0]
        select_rows = c.execute("SELECT count(*) FROM outbox WHERE id = ANY(%s) AND tx < pg_snapshot_xmin(pg_current_snapshot())",
                                (new_ids,)).fetchone()[0]
    reader.rollback(); reader.close()
    print(f"集計のトランザクションが開いている間に、WAL から読めた outbox の行: {while_open}")
    print(f"同じ時点で、tx < pg_snapshot_xmin の条件で読める行: {xmin_rows} 行")
    print(f"SELECT だけのトランザクションが開いている間にコミットした 5 行のうち、同じ条件で読める行: {select_rows} 行"
          f"（そのトランザクションの ID: {reader_xid or '割り当て無し'}）")
    save("wal_stall", {"wal_rows_while_open": while_open, "xmin_rows_while_open": xmin_rows, "xmin_while_open": snap,
                       "select_only_xid": reader_xid, "xmin_rows_while_select_only": select_rows})


# ---------------------------------------------------------------- 4. 落ちる時の比較
def dual_write_child(seed):
    """注文をコミットしてから、ブローカーに送る（outbox を使わない）。"""
    rnd = random.Random(seed)
    with conn() as c, conn("broker", autocommit=True) as b:
        while True:
            oid = c.execute("INSERT INTO orders (item) VALUES ('book') RETURNING id").fetchone()[0]
            c.commit()
            time.sleep(rnd.uniform(0, 0.004))  # コミットと送信の間の処理（ログ出力・変換など）
            b.execute("INSERT INTO events (order_id, type) VALUES (%s, 'OrderPlaced')", (oid,))


def send_first_child(seed):
    """ブローカーに送ってから、注文をコミットする（outbox を使わない、逆の順）。"""
    rnd = random.Random(seed)
    with conn() as c, conn("broker", autocommit=True) as b:
        while True:
            oid = c.execute("INSERT INTO orders (item) VALUES ('book') RETURNING id").fetchone()[0]
            b.execute("INSERT INTO events (order_id, type) VALUES (%s, 'OrderPlaced')", (oid,))
            time.sleep(rnd.uniform(0, 0.004))
            c.commit()


def outbox_app_child(seed):
    with conn() as c:
        while True:
            oid = c.execute("INSERT INTO orders (item) VALUES ('book') RETURNING id").fetchone()[0]
            c.execute("INSERT INTO outbox (order_id, type, payload) VALUES (%s, 'OrderPlaced', '{}')", (oid,))
            c.commit()


def outbox_relay_child(seed):
    """未送信の行を 1 件ずつ送り、送った後に印を付ける。"""
    rnd = random.Random(seed)
    with conn() as c, conn("broker", autocommit=True) as b:
        while True:
            row = c.execute("SELECT id, order_id FROM outbox WHERE NOT published ORDER BY id LIMIT 1 FOR UPDATE SKIP LOCKED").fetchone()
            if not row:
                c.commit()
                time.sleep(0.01)
                continue
            b.execute("INSERT INTO events (outbox_id, order_id, type) VALUES (%s, %s, 'OrderPlaced')", row)
            time.sleep(rnd.uniform(0, 0.004))
            c.execute("UPDATE outbox SET published = true WHERE id = %s", (row[0],))
            c.commit()


def kill_loop(target, rounds, seed):
    rnd = random.Random(seed)
    for k in range(rounds):
        p = mp.Process(target=target, args=(seed * 1000 + k,))
        p.start()
        time.sleep(rnd.uniform(0.1, 0.3))
        os.kill(p.pid, signal.SIGKILL)  # 電源断や OOM Killer の代わり
        p.join()


def crash(rounds=100):
    result = {}
    # outbox を使わない場合
    reset_outbox(); reset_broker()
    kill_loop(dual_write_child, rounds, 1)
    with conn(autocommit=True) as c, conn("broker", autocommit=True) as b:
        orders = c.execute("SELECT count(*) FROM orders").fetchone()[0]
        got = {r[0] for r in b.execute("SELECT order_id FROM events")}
        lost = orders - len(got)
    result["dual_write"] = {"rounds": rounds, "orders": orders, "events": len(got), "lost": lost, "duplicated": 0}
    print("dual_write", result["dual_write"])

    # 送ってからコミットする場合
    reset_outbox(); reset_broker()
    kill_loop(send_first_child, rounds, 2)
    with conn(autocommit=True) as c, conn("broker", autocommit=True) as b:
        orders = {r[0] for r in c.execute("SELECT id FROM orders")}
        got = {r[0] for r in b.execute("SELECT order_id FROM events")}
    result["send_first"] = {"rounds": rounds, "orders": len(orders), "events": len(got),
                            "lost": len(orders - got), "ghost": len(got - orders), "duplicated": 0}
    print("send_first", result["send_first"])

    # outbox を使う場合: アプリと relay の両方を何度も落とす
    reset_outbox(); reset_broker()
    for k in range(rounds):
        app = mp.Process(target=outbox_app_child, args=(k,))
        rel = mp.Process(target=outbox_relay_child, args=(k,))
        app.start(); rel.start()
        time.sleep(random.Random(k).uniform(0.1, 0.3))
        os.kill(app.pid, signal.SIGKILL); os.kill(rel.pid, signal.SIGKILL)
        app.join(); rel.join()
    rel = mp.Process(target=outbox_relay_child, args=(9999,))  # 最後に relay だけ動かして残りを送り切る
    rel.start()
    with conn(autocommit=True) as c:
        while c.execute("SELECT count(*) FROM outbox WHERE NOT published").fetchone()[0]:
            time.sleep(0.2)
    os.kill(rel.pid, signal.SIGKILL); rel.join()
    with conn(autocommit=True) as c, conn("broker", autocommit=True) as b:
        orders = c.execute("SELECT count(*) FROM orders").fetchone()[0]
        rows = b.execute("SELECT order_id, count(*) FROM events GROUP BY order_id").fetchall()
        dup = sum(n - 1 for _, n in rows)
    result["outbox"] = {"rounds": rounds, "orders": orders, "events": len(rows), "lost": orders - len(rows), "duplicated": dup}
    print("outbox", result["outbox"])
    save("crash", result)


# ---------------------------------------------------------------- 4b. 長いトランザクションで止まる
def stall():
    """outbox と無関係な表を更新する長いトランザクションが 3 秒開いている間、xid8 で読む relay は何も送らない。"""
    reset_outbox()
    with conn(autocommit=True) as c:
        c.execute("DROP TABLE IF EXISTS report")
        c.execute("CREATE TABLE report (n int)")
    t0 = time.monotonic()
    log = []

    def at():
        return round(time.monotonic() - t0, 2)

    def batch():  # 集計のバッチ: 0.2 秒に始まり、3 秒後にコミット
        time.sleep(0.2)
        with conn() as c:
            c.execute("INSERT INTO report VALUES (1)")
            log.append({"t": at(), "who": "batch", "what": "begin"})
            time.sleep(3)
            c.commit()
            log.append({"t": at(), "who": "batch", "what": "commit"})

    def orders():  # 注文: 0.5 秒ごとに 1 件、すぐコミット
        with conn() as c:
            for _ in range(8):
                time.sleep(0.5)
                oid = c.execute("INSERT INTO outbox (order_id, type, payload) VALUES (1, 'OrderPlaced', '{}') RETURNING id").fetchone()[0]
                c.commit()
                log.append({"t": at(), "who": "app", "what": "commit", "id": oid})

    stop, sent = threading.Event(), []

    def relay():
        last = ("0", 0)
        with conn(autocommit=True) as c:
            while not stop.is_set():
                rows = c.execute(
                    """SELECT tx::text, id FROM outbox
                       WHERE (tx, id) > (%s::xid8, %s)
                         AND tx < pg_snapshot_xmin(pg_current_snapshot())
                       ORDER BY tx, id""", last).fetchall()
                for tx, i in rows:
                    log.append({"t": at(), "who": "relay", "what": "send", "id": i})
                if rows:
                    last = rows[-1]
                time.sleep(0.1)

    ths = [threading.Thread(target=f) for f in (batch, orders, relay)]
    for th in ths:
        th.start()
    ths[0].join(); ths[1].join()
    time.sleep(0.5)
    stop.set(); ths[2].join()
    log.sort(key=lambda e: e["t"])
    for e in log:
        print(e)
    save("stall", {"log": log})


# ---------------------------------------------------------------- 5. relay を増やした時の順番
def order_relay(stop, seed, part=None):
    """part=(k, n) なら、order_id を n で割った余りが k の行だけを受け持つ。"""
    rnd = random.Random(seed)
    where = f" AND order_id % {part[1]} = {part[0]}" if part else ""
    with conn() as c, conn("broker", autocommit=True) as b:
        while True:
            rows = c.execute("SELECT id, order_id, type FROM outbox WHERE NOT published" + where +
                             " ORDER BY id LIMIT 10 FOR UPDATE SKIP LOCKED").fetchall()
            for row in rows:
                time.sleep(rnd.uniform(0, 0.002))  # 送信にかかる時間
                b.execute("INSERT INTO events (outbox_id, order_id, type) VALUES (%s, %s, %s)", row)
            if rows:
                c.execute("UPDATE outbox SET published = true WHERE id = ANY(%s)", ([r[0] for r in rows],))
            c.commit()
            if not rows:
                if stop.is_set():
                    return
                time.sleep(0.01)


def ordering_once(n, keyed, orders):
    reset_outbox(); reset_broker()
    stop = threading.Event()
    rs = [threading.Thread(target=order_relay, args=(stop, k, (k, n) if keyed else None)) for k in range(n)]
    for r in rs:
        r.start()
    with conn() as c:  # 1 件の注文について 3 つのイベントを、別々のトランザクションで順に書く
        for o in range(1, orders + 1):
            for t in ("OrderPlaced", "OrderPaid", "OrderShipped"):
                c.execute("INSERT INTO outbox (order_id, type, payload) VALUES (%s, %s, '{}')", (o, t))
                c.commit()
    stop.set()
    for r in rs:
        r.join()
    with conn("broker", autocommit=True) as b:
        seen = {}
        for oid, t in b.execute("SELECT order_id, type FROM events ORDER BY seq"):
            seen.setdefault(oid, []).append(t)
    return sum(1 for v in seen.values() if v != ["OrderPlaced", "OrderPaid", "OrderShipped"])


def ordering(orders=500, reps=5):
    result = {}
    for n, keyed in ((1, False), (2, False), (4, False), (2, True), (4, True)):
        runs = [ordering_once(n, keyed, orders) for _ in range(reps)]
        key = f"{n}_by_order" if keyed else str(n)
        result[key] = {"orders": orders, "runs": runs, "out_of_order": sorted(runs)[reps // 2]}
        print(f"relay {n} 個{'（注文ごとに受け持つ）' if keyed else ''}: 順番が入れ替わった注文 {runs} / {orders}")
    save("ordering", result)


def ordering_trace(rows_per_send=0.2):
    """relay 2 個が 10 行ずつ取った時に、注文 4 の支払いが確定より先に届く様子を時刻付きで記録する。
    図で追えるように、1 行の送信を 0.2 秒にしている（ordering() は 0〜2 ms）。"""
    reset_outbox(); reset_broker()
    with conn() as c:
        for o in range(1, 7):
            for t in ("OrderPlaced", "OrderPaid", "OrderShipped"):
                c.execute("INSERT INTO outbox (order_id, type, payload) VALUES (%s, %s, '{}')", (o, t))
                c.commit()
    t0 = time.monotonic()
    log = []

    def at():
        return round(time.monotonic() - t0, 3)

    def relay(name, delay):
        time.sleep(delay)
        with conn() as c, conn("broker", autocommit=True) as b:
            rows = c.execute("SELECT id, order_id, type FROM outbox WHERE NOT published"
                             " ORDER BY id LIMIT 10 FOR UPDATE SKIP LOCKED").fetchall()
            log.append({"t": at(), "who": name, "what": "take", "ids": [r[0] for r in rows]})
            for row in rows:
                time.sleep(rows_per_send)
                b.execute("INSERT INTO events (outbox_id, order_id, type) VALUES (%s, %s, %s)", row)
                log.append({"t": at(), "who": name, "what": "send", "id": row[0], "order": row[1], "type": row[2]})
            c.execute("UPDATE outbox SET published = true WHERE id = ANY(%s)", ([r[0] for r in rows],))
            c.commit()

    ths = [threading.Thread(target=relay, args=("A", 0.0)), threading.Thread(target=relay, args=("B", 0.1))]
    for th in ths:
        th.start()
    for th in ths:
        th.join()
    with conn("broker", autocommit=True) as b:
        arrived = [list(r) for r in b.execute("SELECT outbox_id, order_id, type FROM events ORDER BY seq")]
    log.sort(key=lambda e: e["t"])
    for e in log:
        print(e)
    save("ordering_trace", {"send_sec": rows_per_send, "log": log, "arrived": arrived})


if __name__ == "__main__":
    {"overtake": overtake, "load": load_all, "wal": wal_order, "crash": crash, "ordering": ordering, "ordering_trace": ordering_trace, "stall": stall,
     "wal_stall": wal_stall}[sys.argv[1]]()
