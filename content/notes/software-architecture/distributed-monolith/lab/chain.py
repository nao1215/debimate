"""注文サービスが在庫・決済・配送を同期で呼ぶ時の待ち時間と失敗を測る。

127.0.0.1 に 3 つの HTTP サーバーを立てるだけで、外部には通信しない。
標準ライブラリだけを使う。Python 3.14.4 で実行を確認した。
"""

import random
import statistics
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# サービスごとの処理時間（秒）と状態。mode は ok / hang / flaky。
SERVICES = {
    "inventory": {"delay": 0.05, "mode": "ok"},
    "payment": {"delay": 0.08, "mode": "ok"},
    "shipping": {"delay": 0.03, "mode": "ok"},
}
FLAKY_RATE = 0.01  # flaky の時に 500 を返す割合
TIMEOUT = 0.5  # 注文サービスが 1 回の呼び出しを待つ上限（秒）
rng = random.Random(42)
ports = {}


def make_handler(name):
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            conf = SERVICES[name]
            if conf["mode"] == "hang":
                time.sleep(2)  # 応答しないサービスの代わり
            time.sleep(conf["delay"])
            failed = conf["mode"] == "flaky" and rng.random() < FLAKY_RATE
            self.send_response(500 if failed else 200)
            self.end_headers()

        def log_message(self, *args):
            pass

    return Handler


def start_services():
    for name in SERVICES:
        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(name))
        ports[name] = server.server_address[1]
        threading.Thread(target=server.serve_forever, daemon=True).start()


def call(name):
    req = urllib.request.Request(f"http://127.0.0.1:{ports[name]}/", method="POST")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT):
            return True
    except Exception:  # タイムアウト、HTTP 500 など
        return False


def order_serial(names=("inventory", "payment", "shipping")):
    """順に呼び、1 つでも失敗したら注文を失敗にする。"""
    return all(call(n) for n in names)


def order_parallel():
    """3 つを同時に呼び、全ての応答を待つ。"""
    with ThreadPoolExecutor(3) as pool:
        return all(pool.map(call, SERVICES))


shipping_queue = []  # 後から配送サービスに渡す依頼（実際は outbox テーブルなど）


def order_with_queue():
    """在庫と決済だけ同期で呼び、配送依頼は記録して先に成功を返す。"""
    ok = order_serial(("inventory", "payment"))
    if ok:
        shipping_queue.append("配送依頼")
    return ok


def measure(label, order, n=20):
    results, elapsed = [], []
    for _ in range(n):
        start = time.perf_counter()
        results.append(order())
        elapsed.append((time.perf_counter() - start) * 1000)
    print(f"  成功 {sum(results):>2}/{n}  "
          f"中央値 {statistics.median(elapsed):5.1f} ms  {label}")


start_services()
order_serial()  # 接続の初回コストを測定から外す

print("[1] 全サービスが正常")
measure("順に呼ぶ", order_serial)
measure("同時に呼ぶ", order_parallel)

print("[2] 決済サービスが応答しない")
SERVICES["payment"]["mode"] = "hang"
measure("順に呼ぶ", order_serial)
SERVICES["payment"]["mode"] = "ok"

print("[3] 配送サービスが応答しない")
SERVICES["shipping"]["mode"] = "hang"
measure("順に呼ぶ", order_serial)
measure("配送だけ後から渡す", order_with_queue)
print(f"  未送信の配送依頼 {len(shipping_queue)} 件")
SERVICES["shipping"]["mode"] = "ok"

print(f"[4] 各サービスが {FLAKY_RATE:.0%} の確率で失敗")
for conf in SERVICES.values():
    conf.update(delay=0, mode="flaky")
n = 10000
ok = sum(order_serial() for _ in range(n))
print(f"  注文の成功率 {ok / n:.2%}（理論値 {(1 - FLAKY_RATE) ** 3:.2%}）")
