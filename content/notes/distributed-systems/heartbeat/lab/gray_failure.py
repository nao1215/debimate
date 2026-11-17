"""ハートビートは届き続けるのに、要求には答えなくなるノードの実験。

node は要求を処理するループと、100 ms ごとにハートビートを送る処理を持つ。
開始から 2 秒後に、要求を処理するループがロックの取り合いで止まる
（2 つのロックを逆の順に取るデッドロック）。

ハートビートを送る場所を 2 通りに変えて、同じ 5 秒の間に
  - monitor がハートビートを受け取った時刻と、落ちたと判定した時刻
  - client が 100 ms ごとに送った要求が、300 ms 以内に返ったか
を記録する。

  thread : ハートビートを別のスレッドから送る
  inloop : ハートビートを、要求を処理するループの中から送る

実行: python3 gray_failure.py
"""

import json
import os
import socket
import subprocess
import sys
import threading
import time

INTERVAL, TIMEOUT = 0.100, 0.500
REQ_EVERY, REQ_TIMEOUT = 0.100, 0.300
STUCK_AT, RUN_LEN = 2.0, 5.0


def node(mode, hb_port, req_port, t0):
    hb = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    srv = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    srv.bind(("127.0.0.1", req_port))
    srv.settimeout(INTERVAL)
    lock_a, lock_b = threading.Lock(), threading.Lock()

    def send_heartbeat():
        hb.sendto(b"node", ("127.0.0.1", hb_port))

    def other_job():
        # 2 秒後に lock_b を取ってから lock_a を待つ。処理のループとは逆の順
        time.sleep(max(0, t0 + STUCK_AT - time.monotonic()))
        with lock_b:
            time.sleep(0.2)
            with lock_a:
                pass

    threading.Thread(target=other_job, daemon=True).start()
    if mode == "thread":
        def beat():
            while True:
                send_heartbeat()
                time.sleep(INTERVAL)
        threading.Thread(target=beat, daemon=True).start()

    last_beat = 0.0
    while time.monotonic() - t0 < RUN_LEN:
        if mode == "inloop" and time.monotonic() - last_beat >= INTERVAL:
            send_heartbeat()
            last_beat = time.monotonic()
        try:
            data, addr = srv.recvfrom(64)
        except socket.timeout:
            continue
        with lock_a:          # 要求の処理は lock_a → lock_b の順に取る
            time.sleep(0.02)
            with lock_b:
                srv.sendto(b"ok " + data, addr)


def run(mode, hb_port, req_port):
    t0 = time.monotonic() + 0.3
    proc = subprocess.Popen([sys.executable, __file__, "--node", mode, str(hb_port),
                             str(req_port), repr(t0)])
    events = []
    lock = threading.Lock()

    def log(ev, **kw):
        with lock:
            events.append({"t": round(time.monotonic() - t0, 3), "ev": ev, **kw})

    def monitor():
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.bind(("127.0.0.1", hb_port))
        s.settimeout(0.05)
        last, dead = time.monotonic(), False
        while time.monotonic() - t0 < RUN_LEN:
            try:
                s.recvfrom(64)
                last = time.monotonic()
                log("hb")
                if dead:
                    dead = False
                    log("revive")
            except socket.timeout:
                pass
            if not dead and time.monotonic() - last > TIMEOUT:
                dead = True
                log("dead")

    def client():
        c = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        c.settimeout(REQ_TIMEOUT)
        time.sleep(max(0, t0 + 0.2 - time.monotonic()))
        i = 0
        while time.monotonic() - t0 < RUN_LEN:
            sent = time.monotonic()
            c.sendto(str(i).encode(), ("127.0.0.1", req_port))
            try:
                while c.recv(64).split()[1] != str(i).encode():
                    pass
                log("ok", ms=round((time.monotonic() - sent) * 1000))
            except socket.timeout:
                log("timeout", sent=round(sent - t0, 3))
            i += 1
            time.sleep(max(0, sent + REQ_EVERY - time.monotonic()))

    threads = [threading.Thread(target=f) for f in (monitor, client)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    proc.kill()
    proc.wait()
    return events


def main():
    out = {}
    for mode, port in (("thread", 41000), ("inloop", 41100)):
        ev = run(mode, port, port + 1)
        out[mode] = ev
        hb_after = sum(1 for e in ev if e["ev"] == "hb" and e["t"] > STUCK_AT + 0.1)
        ok_after = sum(1 for e in ev if e["ev"] == "ok" and e["t"] > STUCK_AT + 0.5)
        to = sum(1 for e in ev if e["ev"] == "timeout")
        dead = [e["t"] for e in ev if e["ev"] == "dead"]
        print(f"{mode:6s}  2.1 秒以降のハートビート {hb_after:3d}  2.5 秒以降の成功 {ok_after}"
              f"  タイムアウト {to:2d}  落ちたと判定した時刻 {dead}")
    with open(os.path.join(os.path.dirname(__file__), "gray_failure.json"), "w") as f:
        json.dump(out, f)


if __name__ == "__main__":
    if sys.argv[1:2] == ["--node"]:
        node(sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), float(sys.argv[5]))
    else:
        main()
