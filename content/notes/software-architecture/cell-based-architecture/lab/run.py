"""毒の要求（poison pill）で、何台のサーバーと何人の顧客が巻き込まれるかを測る。

8 台の worker.py を立て、前段に nginx を置く。nginx の振り分けだけを 4 通りに変える。

- shared       : 8 台を 1 つの upstream にまとめる（どの顧客もどの台にも行く）
- shared_post  : shared と同じで、毒の要求だけ POST にする
- cells        : 2 台ずつ 4 つのセルに分け、顧客 ID からセルを引く表（map）で振り分ける
- shuffle      : 顧客ごとに 8 台から 2 台の組を割り当てる（28 通り）

どの方式も nginx の upstream と proxy の設定は既定のまま。
280 人の顧客が 14 秒間 GET を送り、顧客 c007 だけが 2 秒目に毒の要求を 1 回送る。
落ちた worker は 2 秒後に起動し直す（プロセスの再起動に掛かる時間の代わり）。

Run: python3 run.py [mode ...]   （docker と nginx:alpine のイメージが要る）
結果は results/<mode>.json と output.txt に書く。
"""

import hashlib
import itertools
import json
import os
import random
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
PORTS = list(range(9001, 9009))
ROUTER = 18080
CUSTOMERS = [f"c{i:03d}" for i in range(280)]
POISONER = "c007"
POISON_AT = [2.0]
DURATION = 14.0
RESTART = 2.0
THREADS = 24
INTERVAL = 0.15  # 1 スレッドが要求を送る間隔（全体で約 150 件/秒）


def h(s):
    return int(hashlib.sha256(s.encode()).hexdigest(), 16)


def cell_of(c):
    """セルの割り当て表を作る時の規則。表を作った後は、表だけを引く。"""
    return h(c) % 4


COMBOS = list(itertools.combinations(range(8), 2))  # 28 通り


def shuffle_of(c):
    return COMBOS[h(c) % len(COMBOS)]


def server(i):
    return f"        server 127.0.0.1:{PORTS[i]};"


def nginx_conf(mode):
    if mode in ("shared", "shared_post"):
        upstreams = "    upstream app {\n" + "\n".join(server(i) for i in range(8)) + "\n    }\n"
        route = "proxy_pass http://app;"
        maps = ""
    elif mode == "cells":
        upstreams = "".join(
            f"    upstream cell{k} {{\n{server(2 * k)}\n{server(2 * k + 1)}\n    }}\n" for k in range(4))
        rows = "\n".join(f"        {c} cell{cell_of(c)};" for c in CUSTOMERS)
        maps = f"    map $arg_c $cell {{\n        default cell0;\n{rows}\n    }}\n"
        route = "proxy_pass http://$cell;"
    elif mode == "shuffle":
        upstreams = "".join(
            f"    upstream s{a}{b} {{\n{server(a)}\n{server(b)}\n    }}\n" for a, b in COMBOS)
        rows = "\n".join(f"        {c} s{shuffle_of(c)[0]}{shuffle_of(c)[1]};" for c in CUSTOMERS)
        maps = f"    map $arg_c $shard {{\n        default s01;\n{rows}\n    }}\n"
        route = "proxy_pass http://$shard;"
    else:
        raise SystemExit(f"unknown mode {mode}")
    return f"""worker_processes 2;
events {{ worker_connections 4096; }}
http {{
    log_format t '$msec $arg_c $request_method $arg_q $status "$upstream_addr"';
    access_log /log/access.log t;
    error_log /log/error.log warn;
{maps}{upstreams}    server {{
        listen 127.0.0.1:{ROUTER};
        location / {{ {route} }}
    }}
}}
"""


def wait_port(port, timeout=10):
    end = time.time() + timeout
    while time.time() < end:
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", port)) == 0:
                return True
        time.sleep(0.01)
    return False


class Fleet:
    """8 台の worker を動かし、落ちたら RESTART 秒後に起動し直す。"""

    def __init__(self, t0):
        self.t0 = t0
        self.events = []  # (秒, 台の番号, "down" | "up")
        self.procs = [self._start(i) for i in range(8)]
        self.stop = False
        self.thread = threading.Thread(target=self._watch, daemon=True)

    def _start(self, i):
        p = subprocess.Popen([sys.executable, str(HERE / "worker.py"), str(PORTS[i])])
        wait_port(PORTS[i])
        return p

    def _watch(self):
        pending = {}
        while not self.stop:
            now = time.time()
            for i, p in enumerate(self.procs):
                if p is not None and p.poll() is not None:
                    self.events.append((round(now - self.t0, 3), i, "down"))
                    self.procs[i] = None
                    pending[i] = now + RESTART
            for i, at in list(pending.items()):
                if now >= at:
                    self.procs[i] = self._start(i)
                    self.events.append((round(time.time() - self.t0, 3), i, "up"))
                    del pending[i]
            time.sleep(0.005)

    def close(self):
        self.stop = True
        self.thread.join()
        for p in self.procs:
            if p is not None:
                p.kill()


def request(c, q="", method="GET"):
    req = urllib.request.Request(f"http://127.0.0.1:{ROUTER}/work?c={c}&q={q}", method=method)
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return 0


def run(mode, work):
    work.mkdir(parents=True, exist_ok=True)
    (work / "access.log").unlink(missing_ok=True)
    conf = work / "nginx.conf"
    conf.write_text(nginx_conf(mode))
    cid = subprocess.check_output([
        "docker", "run", "-d", "--rm", "--network", "host",
        "-v", f"{conf}:/etc/nginx/nginx.conf:ro", "-v", f"{work}:/log",
        "nginx:alpine"]).decode().strip()
    try:
        assert wait_port(ROUTER), "nginx did not start"
        t0 = time.time() + 0.5
        fleet = Fleet(t0)
        fleet.thread.start()
        records, lock = [], threading.Lock()
        normal = [c for c in CUSTOMERS if c != POISONER]

        def load(seed):
            rnd = random.Random(seed)
            while time.time() < t0:
                time.sleep(0.001)
            while (t := time.time() - t0) < DURATION:
                c = rnd.choice(normal)
                status = request(c)
                with lock:
                    records.append((round(t, 3), c, status))
                time.sleep(INTERVAL)

        threads = [threading.Thread(target=load, args=(s,)) for s in range(THREADS)]
        for th in threads:
            th.start()
        poison = []
        for at in POISON_AT:
            while time.time() - t0 < at:
                time.sleep(0.001)
            method = "POST" if mode == "shared_post" else "GET"
            poison.append((at, request(POISONER, "poison", method)))
        for th in threads:
            th.join()
        fleet.close()
    finally:
        subprocess.run(["docker", "stop", "-t", "1", cid], capture_output=True)
    tried = []
    for line in (work / "access.log").read_text().splitlines():
        if " poison " in line:
            tried.append(line.split('"')[1])
    return {"mode": mode, "events": fleet.events, "records": records,
            "poison": poison, "poison_upstreams": tried}


def summary(res):
    rec = res["records"]
    fails = [r for r in rec if r[2] != 200]
    hit = sorted({r[1] for r in fails})
    down = {}
    for _, i, kind in res["events"]:
        if kind == "down":
            down[i] = down.get(i, 0) + 1
    lines = [f"== {res['mode']}",
             f"normal requests: {len(rec)}  failed: {len(fails)} ({len(fails) / len(rec):.1%})",
             f"customers with >=1 failure: {len(hit)} / {len(CUSTOMERS) - 1}",
             f"worker crashes: {sum(down.values())}  crashed ports: {[PORTS[i] for i in sorted(down)]}",
             f"poison responses: {res['poison']}"]
    for u in res["poison_upstreams"]:
        lines.append(f"  poison tried: {u}")
    return "\n".join(lines)


def resummarize():
    """results/*.json から output.txt を作り直す（実験は走らせない）。"""
    out = [summary(json.loads((HERE / "results" / f"{m}.json").read_text()))
           for m in ["shared", "shared_post", "cells", "shuffle"]]
    (HERE / "output.txt").write_text("\n\n".join(out) + "\n")


if __name__ == "__main__":
    if sys.argv[1:] == ["--summary"]:
        resummarize()
        sys.exit(0)
    modes = sys.argv[1:] or ["shared", "shared_post", "cells", "shuffle"]
    base = Path(os.environ.get("LAB_WORK", tempfile.gettempdir())) / "cell-lab"
    (HERE / "results").mkdir(exist_ok=True)
    out = []
    for m in modes:
        res = run(m, base / m)
        (HERE / "results" / f"{m}.json").write_text(json.dumps(res))
        s = summary(res)
        print(s, flush=True)
        out.append(s)
        time.sleep(1)
    print(f"cells of {POISONER}: cell{cell_of(POISONER)} = workers "
          f"{[2 * cell_of(POISONER), 2 * cell_of(POISONER) + 1]}; shuffle shard: {shuffle_of(POISONER)}")
    (HERE / "output.txt").write_text("\n\n".join(out) + "\n")
