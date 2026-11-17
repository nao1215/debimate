"""QUORUM の書き込みが失敗と返った後、その値がどこに残り、いつ広がるかを見る。

cluster.sh up で作った Cassandra 3 台（複製の数 3）に対して、次を順に行う。
  1. k=order-1 に v1 を ALL で書く（3 台とも v1）
  2. q2 と q3 を docker pause で止め、すぐ v2 を QUORUM で書く
  3. 止めたまま待ち、q1 が 2 台を落ちたと見なした後に v3 を QUORUM で書く
  4. q2 と q3 を戻し、0.5 秒ごとに各台が持つ値を 1 台ずつ読む（ONE）。
     同時に q2 を調整役にして QUORUM でも読む
  5. q1 のログから、2 台を UP と見なした時刻と hint を送り終えた時刻を拾う

各台の値は、その台を調整役にした ONE の読み取りのトレースで、その台が自分で読んだ時だけ数える。
読み取りで値を直す read repair と、別の台へ投機的に読みに行く speculative retry は切ってある。

使い方: python timeout_write.py   出力は out_timeout_write.txt、図に使う時刻は out_timeout_write.json
"""
import datetime as dt
import json
import subprocess
import time

from cassandra import ConsistencyLevel as CL
from cassandra.cluster import Cluster, ExecutionProfile, EXEC_PROFILE_DEFAULT
from cassandra.policies import WhiteListRoundRobinPolicy, FallthroughRetryPolicy
from cassandra.query import SimpleStatement

NODES = ["q1", "q2", "q3"]
T0 = time.monotonic()
WALL0 = time.time()
NAME_OF = {}
EVENTS = []      # 図に使う出来事
SAMPLES = []     # 0.5 秒ごとの各台の値


def now():
    return round(time.monotonic() - T0, 2)


def log(msg, kind=None, **kw):
    t = now()
    print(f"{t:6.2f}s  {msg}", flush=True)
    if kind:
        EVENTS.append({"t": t, "kind": kind, "msg": msg, **kw})


def ip(name):
    return subprocess.check_output(
        ["docker", "inspect", "-f", "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}", name],
        text=True).strip()


def session_for(name):
    # 調整役（coordinator）を 1 台に固定し、ドライバーの再試行も切る
    prof = ExecutionProfile(load_balancing_policy=WhiteListRoundRobinPolicy([ip(name)]),
                            retry_policy=FallthroughRetryPolicy(), request_timeout=20)
    c = Cluster([ip(name)], execution_profiles={EXEC_PROFILE_DEFAULT: prof}, protocol_version=5)
    return c.connect("lab")


def write(s, v, cl):
    st = SimpleStatement("UPDATE kv SET v = %s WHERE k = 'order-1'", consistency_level=cl)
    start = now()
    try:
        s.execute(st, (v,))
        log(f"write {v} {CL.value_to_name[cl]}: OK", "write", v=v, ok=True, start=start)
    except Exception as e:
        log(f"write {v} {CL.value_to_name[cl]}: {type(e).__name__}: {e}", "write",
            v=v, ok=False, error=type(e).__name__, start=start)


def read_local(s, name):
    """name を調整役にした ONE の読み取り。name 自身が読んだ時だけ値を返す"""
    st = SimpleStatement("SELECT v FROM kv WHERE k = 'order-1'", consistency_level=CL.ONE)
    r = s.execute(st, trace=True)
    row = r.one()
    srcs = {NAME_OF.get(str(ev.source), str(ev.source))
            for ev in r.get_query_trace(max_wait_sec=5).events if "live rows" in ev.description}
    return (row.v if row else None) if srcs == {name} else None


def read(s, cl):
    st = SimpleStatement("SELECT v FROM kv WHERE k = 'order-1'", consistency_level=cl)
    try:
        row = s.execute(st).one()
        return row.v if row else None
    except Exception as e:
        return type(e).__name__


def nodetool_status():
    return subprocess.run(["docker", "exec", "q1", "nodetool", "status"],
                          capture_output=True, text=True).stdout


def q1_log_events():
    """q1 のログから、2 台を DOWN・UP と見なした最初の時刻と、hint を送り終えた時刻を拾う"""
    since = dt.datetime.fromtimestamp(WALL0, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    out = subprocess.run(["docker", "logs", "-t", "--since", since, "q1"],
                         capture_output=True, text=True)
    first = {}
    for line in (out.stdout + out.stderr).splitlines():
        stamp = line.split(" ", 1)[0]
        try:
            t = dt.datetime.fromisoformat(stamp[:26] + "+00:00").timestamp() - WALL0
        except ValueError:
            continue
        for n in NODES[1:]:
            addr = f"/{ip(n)}:7000"
            if f"{addr} is now UP" in line:
                first.setdefault(("up", n), t)
            elif f"{addr} is now DOWN" in line:
                first.setdefault(("down", n), t)
            elif "Finished hinted handoff" in line and addr in line:
                # 途中で打ち切った送信も同じ文で記録されるので、最後の 1 行（送り終えた時）を使う
                first[("hint", n)] = t
    return sorted(((k, n, round(t, 2)) for (k, n), t in first.items()), key=lambda x: x[2])


def docker(*args):
    subprocess.run(["docker", *args], check=True, stdout=subprocess.DEVNULL)


def main():
    for n in NODES:
        NAME_OF[ip(n)] = n
    s1 = session_for("q1")
    s1.execute("ALTER TABLE kv WITH read_repair = 'NONE' AND speculative_retry = 'NONE'")
    write(s1, "v1", CL.ALL)

    docker("pause", "q2", "q3")
    log("pause q2 q3", "pause")
    write(s1, "v2", CL.QUORUM)
    log(f"read via q1 ONE: {read(s1, CL.ONE)}", "read", node="q1", cl="ONE")

    # q1 が 2 台とも落ちたと見なす（nodetool status が DN を 2 行出す）まで待ってから書く
    while nodetool_status().count("\nDN") < 2 and now() < 60:
        time.sleep(1)
    write(s1, "v3", CL.QUORUM)

    docker("unpause", "q2", "q3")
    log("unpause q2 q3", "unpause")
    sessions = {n: session_for(n) for n in NODES}
    end = now() + 20
    while now() < end:
        t = now()
        vals = {n: read_local(sessions[n], n) for n in NODES}
        quorum_via_q2 = read(sessions["q2"], CL.QUORUM)
        SAMPLES.append({"t": t, **vals, "quorum_via_q2": quorum_via_q2})
        print(f"{t:6.2f}s  ONE q1={vals['q1']} q2={vals['q2']} q3={vals['q3']}  "
              f"QUORUM via q2={quorum_via_q2}", flush=True)
        time.sleep(max(0, 0.5 - (now() - t)))

    for kind, n, t in q1_log_events():
        print(f"{t:6.2f}s  q1 log: {kind} {n}")
        EVENTS.append({"t": t, "kind": kind, "node": n})
    with open("out_timeout_write.json", "w") as f:
        json.dump({"events": sorted(EVENTS, key=lambda e: e["t"]), "samples": SAMPLES}, f, indent=1)


if __name__ == "__main__":
    main()
