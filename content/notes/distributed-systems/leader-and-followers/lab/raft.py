"""etcd（Raft）の 3 台で、Leader をネットワークから外した時の書き込みを見る。

1. 3 台を作り、Leader を見つけて k=v1 を書く
2. Leader をネットワークから外し、外した Leader と残りの 2 台の両方に書く。外した Leader から 2 通りに読む。
   外した Leader が自分を Leader と見なさなくなった時刻も記録する（etcd の CheckQuorum）
3. 外した Leader を戻し、全員の役割・term・k の値を見る。外した Leader のログから役割の変化を抜き出す
"""
import json
import threading
import subprocess
import time

IMG = "gcr.io/etcd-development/etcd:v3.5.17"
NET = "lf-raft"
NODES = ["e1", "e2", "e3"]
T0 = time.perf_counter()


def log(msg):
    print(f"{time.perf_counter() - T0:6.1f}s  {msg}", flush=True)


def run(*args, check=True):
    return subprocess.run(args, check=check, capture_output=True, text=True)


def ctl(node, *args, timeout="3s"):
    r = run("docker", "exec", node, "etcdctl", "--endpoints=127.0.0.1:2379",
            f"--command-timeout={timeout}", *args, check=False)
    return (r.stdout + r.stderr).strip().splitlines()[-1] if (r.stdout + r.stderr).strip() else ""


def status(node):
    r = run("docker", "exec", node, "etcdctl", "--endpoints=127.0.0.1:2379",
            "endpoint", "status", "-w", "json", check=False)
    try:
        s = json.loads(r.stdout)[0]["Status"]
        return s["header"]["member_id"] == s.get("leader", 0), s["raftTerm"], s.get("leader", 0)
    except (ValueError, IndexError, KeyError):
        return None, None, None


run("docker", "rm", "-f", *NODES, check=False)
run("docker", "network", "rm", NET, check=False)
run("docker", "network", "create", NET)
cluster = ",".join(f"{n}=http://{n}:2380" for n in NODES)
for n in NODES:
    run("docker", "run", "-d", "--name", n, "--network", NET, IMG, "etcd", "--name", n,
        "--listen-client-urls", "http://0.0.0.0:2379", "--advertise-client-urls", f"http://{n}:2379",
        "--listen-peer-urls", "http://0.0.0.0:2380", "--initial-advertise-peer-urls", f"http://{n}:2380",
        "--initial-cluster", cluster, "--initial-cluster-state", "new")
while True:
    leaders = [n for n in NODES if status(n)[0]]
    if leaders:
        break
    time.sleep(0.2)
L = leaders[0]
others = [n for n in NODES if n != L]
T0 = time.perf_counter()
log(f"Leader は {L}（term {status(L)[1]}）。put k=v1 -> {ctl(L, 'put', 'k', 'v1')}")

run("docker", "network", "disconnect", NET, L)
log(f"{L} をネットワークから外した")
th = threading.Thread(target=lambda: log(f"外した {L} に put k=v-old -> {ctl(L, 'put', 'k', 'v-old', timeout='5s')}"))
th.start()


def watch_step_down():
    while status(L)[0] is not False:
        time.sleep(0.1)
    log(f"外した {L} が自分から Leader を降りた（Leader=False term={status(L)[1]}）")


wd = threading.Thread(target=watch_step_down)
wd.start()
while not any(status(n)[0] for n in others):
    time.sleep(0.1)
nl = [n for n in others if status(n)[0]][0]
log(f"残りの 2 台で新しい Leader {nl}（term {status(nl)[1]}）")
log(f"{nl} に put k=v-new -> {ctl(nl, 'put', 'k', 'v-new')}")
log(f"外した {L} に get k（linearizable） -> {ctl(L, 'get', 'k', '--print-value-only')}")
log(f"外した {L} に get k（serializable） -> {ctl(L, 'get', 'k', '--print-value-only', '--consistency=s')}")
th.join()
wd.join()

run("docker", "network", "connect", NET, L)
log(f"{L} を戻した")
time.sleep(3)
for n in NODES:
    is_leader, term, _ = status(n)
    log(f"{n}: Leader={is_leader} term={term} get k -> {ctl(n, 'get', 'k', '--print-value-only')}")
KEYS = ("stepped down", "became follower", "found conflict")
started = False  # 起動時の became follower at term 0/1 は飛ばし、降りた所から出す
for line in run("docker", "logs", L, check=False).stderr.splitlines():
    try:
        msg = json.loads(line).get("msg", "")
    except ValueError:
        continue
    started = started or "stepped down" in msg
    if started and any(k in msg for k in KEYS):
        print(f"        {L} のログ: {msg}")
run("docker", "rm", "-f", *NODES, check=False)
run("docker", "network", "rm", NET, check=False)
