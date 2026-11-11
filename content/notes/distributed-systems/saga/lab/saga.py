"""注文・在庫・決済・配送の 4 つのサービスで Saga を動かす実験。

Python 標準ライブラリ（sqlite3・heapq）だけで動く。乱数は使わない。
各サービスは自分専用の SQLite（:memory:）を持ち、他のサービスの DB には触らない。
メッセージは仮想の時計を持つバスで届け、サービスごとに処理の遅さ（latency）を変えている。

    python3 saga.py            # 全ての場面を実行し、ログを表示して stock_timeline.json を書く
"""

import heapq
import itertools
import json
import sqlite3
from pathlib import Path

PRICE = 1000  # 商品 1 個の値段（円）


class Bus:
    """仮想の時計で、宛先ごとの遅れを足してメッセージを届ける。"""

    def __init__(self, latency):
        self.t = 0
        self.latency = latency
        self.q = []
        self.seq = itertools.count()
        self.nodes = {}
        self.lines = []

    def log(self, who, text):
        self.lines.append(f"t={self.t:>2}  {who:<12} {text}")

    def send(self, to, msg):
        heapq.heappush(self.q, (self.t + self.latency.get(to, 1), next(self.seq), to, msg))

    def at(self, t, fn):
        """時刻 t に fn() を呼ぶ（商品ページの表示や、別の客の注文を割り込ませる）。"""
        heapq.heappush(self.q, (t, next(self.seq), None, fn))

    def run(self):
        for node in self.nodes.values():
            node.relay()
        while self.q:
            t, _, to, item = heapq.heappop(self.q)
            self.t = t
            if to is None:
                item()
            else:
                self.nodes[to].handle(item)
            for node in self.nodes.values():
                node.relay()


class Node:
    """自分の DB と outbox を持つサービス。返信は業務の更新と同じトランザクションで outbox に書く。"""

    name = ""

    def __init__(self, bus):
        self.bus = bus
        bus.nodes[self.name] = self
        self.db = sqlite3.connect(":memory:")
        self.db.execute("CREATE TABLE outbox (id INTEGER PRIMARY KEY, dest TEXT, body TEXT,"
                        " sent INTEGER DEFAULT 0)")
        self.crash_after_send = set()  # この種類のメッセージを送った直後に relay を止める

    def emit(self, dest, **msg):
        msg["msg_id"] = f"{self.name}-{self.db.execute('SELECT COUNT(*) FROM outbox').fetchone()[0] + 1}"
        self.db.execute("INSERT INTO outbox (dest, body) VALUES (?, ?)", (dest, json.dumps(msg)))

    def relay(self):
        rows = self.db.execute("SELECT id, dest, body FROM outbox WHERE sent = 0 ORDER BY id").fetchall()
        for oid, dest, body in rows:
            msg = json.loads(body)
            self.bus.send(dest, msg)
            if msg["type"] in self.crash_after_send:
                # 送信は済んだが sent = 1 を書く前に止まった。再起動後の relay が同じ行をもう一度送る
                self.crash_after_send.discard(msg["type"])
                self.bus.log(self.name, f"relay が {msg['type']} を送った直後に停止、再起動")
                return self.relay()
            with self.db:
                self.db.execute("UPDATE outbox SET sent = 1 WHERE id = ?", (oid,))


class OrderService(Node):
    name = "order"

    def __init__(self, bus):
        super().__init__(bus)
        self.db.execute("CREATE TABLE orders (id TEXT PRIMARY KEY, item TEXT, qty INT, status TEXT)")

    def handle(self, m):
        with self.db:
            if m["type"] == "CreateOrder":
                self.db.execute("INSERT INTO orders VALUES (?, ?, ?, 'PENDING')",
                                (m["saga"], m["item"], m["qty"]))
            elif m["type"] == "CancelOrder":
                self.db.execute("UPDATE orders SET status = 'CANCELLED' WHERE id = ?", (m["saga"],))
            elif m["type"] == "ConfirmOrder":
                self.db.execute("UPDATE orders SET status = 'CONFIRMED' WHERE id = ?", (m["saga"],))
            self.emit("orchestrator", type=m["type"] + "Done", saga=m["saga"], ok=True)
        self.bus.log(self.name, f"{m['type']:<15} {m['saga']}")

    def status(self, saga):
        return self.db.execute("SELECT status FROM orders WHERE id = ?", (saga,)).fetchone()[0]


class InventoryService(Node):
    """在庫。semantic_lock・idempotent・snapshot で、異常と対策の有無を切り替える。"""

    name = "inventory"

    def __init__(self, bus, stock, semantic_lock=False, idempotent=True, snapshot=False):
        super().__init__(bus)
        self.semantic_lock, self.idempotent, self.snapshot = semantic_lock, idempotent, snapshot
        self.db.execute("CREATE TABLE stock (item TEXT PRIMARY KEY, available INT)")
        self.db.execute("CREATE TABLE reservations (saga TEXT PRIMARY KEY, item TEXT, qty INT,"
                        " state TEXT, before INT)")
        self.db.execute("INSERT INTO stock VALUES ('book', ?)", (stock,))
        self.timeline = [(0, stock, 0)]

    def available(self):
        return self.db.execute("SELECT available FROM stock WHERE item = 'book'").fetchone()[0]

    def pending(self):
        return self.db.execute("SELECT COALESCE(SUM(qty), 0) FROM reservations"
                               " WHERE state = 'PENDING'").fetchone()[0]

    def handle(self, m):
        with self.db:
            reply = getattr(self, m["type"])(m)
            self.emit("orchestrator", type=m["type"] + "Done", saga=m["saga"], **reply)
        self.timeline.append((self.bus.t, self.available(), self.pending()))
        extra = reply.get("note", "") if reply.get("ok") else reply["reason"]
        self.bus.log(self.name, f"{m['type']:<15} {m['saga']}  -> available={self.available()}"
                     f"{'  ' + extra if extra else ''}")

    def ReserveStock(self, m):
        avail = self.available()
        if avail < m["qty"]:
            if self.semantic_lock and self.pending() > 0:
                return {"ok": False, "reason": "busy"}   # 仮押さえ中。後で取れるかもしれない
            return {"ok": False, "reason": "out_of_stock"}
        state = "PENDING" if self.semantic_lock else "RESERVED"
        self.db.execute("UPDATE stock SET available = available - ? WHERE item = ?", (m["qty"], m["item"]))
        self.db.execute("INSERT INTO reservations VALUES (?, ?, ?, ?, ?)",
                        (m["saga"], m["item"], m["qty"], state, avail))
        return {"ok": True}

    def ReleaseStock(self, m):
        """補償。予約で減らした在庫を戻す。"""
        if self.idempotent:
            # 予約の状態が「戻す前」の時だけ戻す。2 通目は rowcount が 0 になり、在庫に触らない
            cur = self.db.execute("UPDATE reservations SET state = 'RELEASED'"
                                  " WHERE saga = ? AND state IN ('RESERVED', 'PENDING')", (m["saga"],))
            if cur.rowcount == 0:
                return {"ok": True, "note": "already released"}
        else:
            self.db.execute("UPDATE reservations SET state = 'RELEASED' WHERE saga = ?", (m["saga"],))
        qty, before = self.db.execute("SELECT qty, before FROM reservations WHERE saga = ?",
                                      (m["saga"],)).fetchone()
        if self.snapshot:
            # 予約の前の値を書き戻す。間に入った別の Saga の更新を消してしまう
            self.db.execute("UPDATE stock SET available = ? WHERE item = 'book'", (before,))
        else:
            # 差分で戻す。他の Saga の増減と順序を入れ替えても結果が同じ（可換）
            self.db.execute("UPDATE stock SET available = available + ? WHERE item = 'book'", (qty,))
        return {"ok": True}

    def ConfirmReservation(self, m):
        """決済が通った後に仮押さえを外す（semantic lock の解除）。"""
        self.db.execute("UPDATE reservations SET state = 'CONFIRMED'"
                        " WHERE saga = ? AND state IN ('RESERVED', 'PENDING')", (m["saga"],))
        return {"ok": True}


class PaymentService(Node):
    name = "payment"

    def __init__(self, bus, limits):
        super().__init__(bus)
        self.limits = limits
        self.db.execute("CREATE TABLE payments (saga TEXT PRIMARY KEY, amount INT)")

    def handle(self, m):
        with self.db:
            amount = m["qty"] * PRICE
            ok = amount <= self.limits[m["customer"]]
            if ok:
                self.db.execute("INSERT INTO payments VALUES (?, ?)", (m["saga"], amount))
            self.emit("orchestrator", type="ChargeCardDone", saga=m["saga"], ok=ok,
                      reason="" if ok else "card_declined")
        self.bus.log(self.name, f"ChargeCard      {m['saga']}  {amount} 円 -> "
                     f"{'charged' if ok else 'card_declined'}")


class ShippingService(Node):
    name = "shipping"

    def __init__(self, bus, fail_first=0):
        super().__init__(bus)
        self.fail_left = fail_first
        self.db.execute("CREATE TABLE shipments (saga TEXT PRIMARY KEY)")

    def handle(self, m):
        with self.db:
            ok = self.fail_left == 0
            if ok:
                self.db.execute("INSERT OR IGNORE INTO shipments VALUES (?)", (m["saga"],))
            else:
                self.fail_left -= 1  # 配送業者の API が一時的に応答しない
            self.emit("orchestrator", type="ArrangeShippingDone", saga=m["saga"], ok=ok,
                      reason="" if ok else "timeout")
        self.bus.log(self.name, f"ArrangeShipping {m['saga']}  -> {'ok' if ok else 'timeout'}")


# 進める命令と、それを打ち消す補償の命令。決済が pivot で、それより後は補償せずに再試行で進める
STEPS = [
    ("order", "CreateOrder", "CancelOrder"),
    ("inventory", "ReserveStock", "ReleaseStock"),
    ("payment", "ChargeCard", None),         # pivot
    ("shipping", "ArrangeShipping", None),   # retryable
]
PIVOT = 2


class Orchestrator(Node):
    """Saga の進み具合を自分の DB に記録し、次の命令か補償の命令を outbox に書く。"""

    name = "orchestrator"

    def __init__(self, bus, retry_delay=6):
        super().__init__(bus)
        self.retry_delay = retry_delay
        self.db.execute("CREATE TABLE sagas (id TEXT PRIMARY KEY, body TEXT, step INT, status TEXT)")

    def start(self, saga, customer, qty):
        body = {"saga": saga, "customer": customer, "item": "book", "qty": qty}
        with self.db:
            self.db.execute("INSERT INTO sagas VALUES (?, ?, 0, 'RUNNING')", (saga, json.dumps(body)))
            self.emit("order", type="CreateOrder", **body)
        self.bus.log(self.name, f"start           {saga}  ({customer}, {qty} 個)")

    def handle(self, m):
        body, step, status = self.db.execute("SELECT body, step, status FROM sagas WHERE id = ?",
                                             (m["saga"],)).fetchone()
        body = json.loads(body)
        with self.db:
            if status == "COMPENSATING" or m["type"] in ("ConfirmOrderDone", "ConfirmReservationDone"):
                return  # 補償と仕上げの返信は記録だけ
            if m["ok"]:
                self.forward(m["saga"], body, step + 1)
            elif step >= PIVOT + 1:
                # pivot を過ぎた段は補償せず、同じ命令を後でもう一度送る
                self.bus.log(self.name, f"retry           {m['saga']}  {STEPS[step][1]}")
                self.bus.at(self.bus.t + self.retry_delay, lambda: self.resend(m["saga"], body, step))
            elif m.get("reason") == "busy":
                self.bus.log(self.name, f"wait            {m['saga']}  在庫が仮押さえ中、{self.retry_delay} 後に再試行")
                self.bus.at(self.bus.t + self.retry_delay, lambda: self.resend(m["saga"], body, step))
            else:
                self.compensate(m["saga"], body, step, m.get("reason", ""))

    def forward(self, saga, body, step):
        if step == len(STEPS):
            self.db.execute("UPDATE sagas SET step = ?, status = 'DONE' WHERE id = ?", (step, saga))
            self.emit("inventory", type="ConfirmReservation", **body)
            self.emit("order", type="ConfirmOrder", **body)
            self.bus.log(self.name, f"done            {saga}")
            return
        self.db.execute("UPDATE sagas SET step = ? WHERE id = ?", (step, saga))
        dest, command, _ = STEPS[step]
        self.emit(dest, type=command, **body)

    def resend(self, saga, body, step):
        with self.db:
            dest, command, _ = STEPS[step]
            self.emit(dest, type=command, **body)

    def compensate(self, saga, body, failed, reason):
        """失敗した段より前の段について、後ろから順に補償の命令を出す。"""
        self.db.execute("UPDATE sagas SET status = 'COMPENSATING' WHERE id = ?", (saga,))
        self.bus.log(self.name, f"compensate      {saga}  {STEPS[failed][1]} が {reason}")
        for dest, _, undo in reversed(STEPS[:failed]):
            if undo:
                self.emit(dest, type=undo, **body)


LATENCY = {"order": 1, "inventory": 1, "payment": 5, "shipping": 1, "orchestrator": 1}


def build(stock, limits, **inv):
    bus = Bus(LATENCY)
    nodes = {
        "orch": Orchestrator(bus),
        "order": OrderService(bus),
        "inv": InventoryService(bus, stock, **inv),
        "pay": PaymentService(bus, limits),
        "ship": ShippingService(bus),
    }
    return bus, nodes


def product_page(bus, inv):
    """商品ページの表示。在庫の DB を読むだけの、Saga の外の処理。"""
    a, p = inv.available(), inv.pending()
    if a > 0:
        label = f"在庫あり（{a}）"
    elif p > 0:
        label = "仮押さえ中（確定待ち）"
    else:
        label = "在庫切れ"
    bus.log("page", f"商品ページ: {label}")


def scenario_1():
    """途中の段（決済）で失敗し、注文と在庫を補償で戻す。"""
    bus, n = build(stock=3, limits={"alice": 500})
    n["orch"].start("saga-A", "alice", 1)
    bus.run()
    return bus, n


def scenario_1_retry():
    """pivot の後の段（配送）が一時的に失敗し、補償せずに再試行で進む。"""
    bus, n = build(stock=3, limits={"alice": 5000})
    n["ship"].fail_left = 1
    n["orch"].start("saga-A", "alice", 1)
    bus.run()
    return bus, n


def scenario_2(semantic_lock):
    """在庫 1 個。A の決済の返事を待つ間に、商品ページと B の注文が在庫を読む。"""
    bus, n = build(stock=1, limits={"alice": 500, "bob": 5000}, semantic_lock=semantic_lock)
    n["orch"].start("saga-A", "alice", 1)
    bus.at(4, lambda: product_page(bus, n["inv"]))
    bus.at(4, lambda: n["orch"].start("saga-B", "bob", 1))
    bus.at(14, lambda: product_page(bus, n["inv"]))
    bus.run()
    return bus, n


def scenario_2_snapshot(snapshot):
    """在庫 2 個。A と B が 1 個ずつ予約し、A だけ決済に失敗する。補償を値の書き戻しにすると B の分が消える。"""
    bus, n = build(stock=2, limits={"alice": 500, "bob": 5000}, snapshot=snapshot)
    n["orch"].start("saga-A", "alice", 1)
    bus.at(1, lambda: n["orch"].start("saga-B", "bob", 1))
    bus.run()
    return bus, n


def scenario_3(idempotent):
    """在庫 3 個。A が決済に失敗し、補償の ReleaseStock が relay の停止で 2 回届く。"""
    bus, n = build(stock=3, limits={"alice": 500}, idempotent=idempotent)
    n["orch"].crash_after_send.add("ReleaseStock")
    n["orch"].start("saga-A", "alice", 1)
    bus.run()
    return bus, n


def report(title, bus, n, sagas):
    print(f"== {title}")
    for line in bus.lines:
        print(line)
    states = ", ".join(f"{s}={n['order'].status(s)}" for s in sagas)
    print(f"-- 結果: available={n['inv'].available()}  {states}\n")


if __name__ == "__main__":
    timeline = {}
    bus, n = scenario_1()
    report("1. 決済で失敗して補償する", bus, n, ["saga-A"])
    bus, n = scenario_1_retry()
    report("1b. pivot の後の失敗は再試行で進める", bus, n, ["saga-A"])
    for lock in (False, True):
        bus, n = scenario_2(lock)
        report(f"2. 補償の前に途中の状態が読まれる（semantic lock {'あり' if lock else 'なし'}）",
               bus, n, ["saga-A", "saga-B"])
        timeline["lock" if lock else "naive"] = n["inv"].timeline
    for snap in (True, False):
        bus, n = scenario_2_snapshot(snap)
        report(f"2b. 補償を{'値の書き戻し' if snap else '差分'}で書く", bus, n, ["saga-A", "saga-B"])
    for idem in (False, True):
        bus, n = scenario_3(idem)
        report(f"3. 補償が 2 回届く（冪等{'' if idem else 'でない'}）", bus, n, ["saga-A"])
        timeline["dup_idem" if idem else "dup_naive"] = n["inv"].timeline
    Path(__file__).with_name("stock_timeline.json").write_text(json.dumps(timeline, indent=1) + "\n")
