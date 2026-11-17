"""監視する側が止まった時に、動いているノードを落ちたと判定するかを数える実験。

node-a と node-b は 100 ms ごとに UDP でハートビートを送る。monitor は
最後に受け取ってから 500 ms 届かなければ「落ちた」と判定する。開始から
2 秒後に monitor だけを SIGSTOP で 1.5 秒止め、SIGCONT で再開させる。
node-a と node-b は一度も止めない。

monitor の作りを 4 通りに変えて、試行ごとに「落ちた」と判定した回数を数える。

  thread : 受信のスレッドと判定のスレッドを分ける（よくある形）
  guard  : thread に、判定の間隔が空いたら自分が止まっていたとみなして
           判定を見送る処理を足す（Cassandra の FailureDetector と同じ考え方）
  loop1  : 1 つのループで、届いた 1 通を読んでから判定する
  drain  : 1 つのループで、届いている分を全て読んでから判定する

実行: python3 monitor_pause.py [試行回数]   （Linux、Python 3.10 以降）
"""

import json
import os
import select
import signal
import socket
import subprocess
import sys
import threading
import time

INTERVAL = 0.100   # ハートビートの間隔
TIMEOUT = 0.500    # これだけ届かなければ落ちたと判定する
TICK = 0.050       # 判定の周期
PAUSE_AT, PAUSE_LEN, RUN_LEN = 2.0, 1.5, 4.5
GUARD_GAP = 4 * TICK  # 判定の間隔がこれより空いたら、自分が止まっていたとみなす


def sender(name, port, offset, t0):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    time.sleep(max(0, t0 + offset - time.monotonic()))
    seq = 0
    while time.monotonic() - t0 < RUN_LEN + 0.5:
        s.sendto(f"{name} {seq}".encode(), ("127.0.0.1", port))
        print(json.dumps({"t": time.monotonic() - t0, "ev": "send", "node": name}), flush=True)
        seq += 1
        time.sleep(max(0, t0 + offset + seq * INTERVAL - time.monotonic()))


def monitor(mode, port, t0):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", port))
    last = {"node-a": time.monotonic(), "node-b": time.monotonic()}
    dead = set()
    lock = threading.Lock()

    def log(ev, **kw):
        print(json.dumps({"t": time.monotonic() - t0, "ev": ev, **kw}), flush=True)

    def on_heartbeat(data):
        node = data.decode().split()[0]
        with lock:
            last[node] = time.monotonic()
            if node in dead:
                dead.discard(node)
                log("revive", node=node)
        log("recv", node=node)

    def judge():
        now = time.monotonic()
        with lock:
            for node, seen in last.items():
                if node not in dead and now - seen > TIMEOUT:
                    dead.add(node)
                    log("dead", node=node, silent_ms=round((now - seen) * 1000))

    if mode in ("thread", "guard"):
        def receiver():
            while True:
                data, _ = sock.recvfrom(64)
                on_heartbeat(data)

        threading.Thread(target=receiver, daemon=True).start()
        prev, hold_until = time.monotonic(), 0.0
        while time.monotonic() - t0 < RUN_LEN:
            time.sleep(TICK)
            now = time.monotonic()
            if mode == "guard":
                if now - prev > GUARD_GAP:
                    log("skip", gap_ms=round((now - prev) * 1000))
                    hold_until = now + TIMEOUT
                prev = now
                if now < hold_until:
                    continue
            judge()
    else:
        sock.setblocking(False)
        while time.monotonic() - t0 < RUN_LEN:
            ready, _, _ = select.select([sock], [], [], TICK)
            while ready:
                on_heartbeat(sock.recv(64))
                if mode == "loop1":
                    break
                ready, _, _ = select.select([sock], [], [], 0)
            judge()


def trial(mode, port):
    t0 = time.monotonic() + 0.3
    me = [sys.executable, __file__]
    mon = subprocess.Popen(me + ["--monitor", mode, str(port), repr(t0)],
                           stdout=subprocess.PIPE, text=True)
    nodes = [subprocess.Popen(me + ["--sender", n, str(port), str(off), repr(t0)],
                              stdout=subprocess.PIPE, text=True)
             for n, off in (("node-a", 0.0), ("node-b", INTERVAL / 2))]
    time.sleep(max(0, t0 + PAUSE_AT - time.monotonic()))
    os.kill(mon.pid, signal.SIGSTOP)
    stop_t = time.monotonic() - t0
    time.sleep(PAUSE_LEN)
    os.kill(mon.pid, signal.SIGCONT)
    cont_t = time.monotonic() - t0
    out = mon.communicate()[0]
    sends = [json.loads(line) for p in nodes for line in p.communicate()[0].splitlines()]
    events = [json.loads(line) for line in out.splitlines()]
    return {"mode": mode, "stop": stop_t, "cont": cont_t, "events": events, "sends": sends}


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    results = []
    for i, mode in enumerate(("thread", "guard", "loop1", "drain")):
        dead_trials, dead_total = 0, 0
        for k in range(n):
            r = trial(mode, 40000 + i * 100 + k)
            deaths = [e for e in r["events"] if e["ev"] == "dead"]
            dead_trials += bool(deaths)
            dead_total += len(deaths)
            results.append(r)
        print(f"{mode:6s}  落ちたと判定した試行 {dead_trials:2d}/{n}  判定の回数 {dead_total}")
    with open(os.path.join(os.path.dirname(__file__), "monitor_pause.json"), "w") as f:
        json.dump(results, f)


if __name__ == "__main__":
    if sys.argv[1:2] == ["--monitor"]:
        monitor(sys.argv[2], int(sys.argv[3]), float(sys.argv[4]))
    elif sys.argv[1:2] == ["--sender"]:
        sender(sys.argv[2], int(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5]))
    else:
        main()
