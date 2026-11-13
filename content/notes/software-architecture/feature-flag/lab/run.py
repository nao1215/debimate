"""Ask the same flag question many times and count users whose answer changes.

Run from this directory (needs gunicorn and uvicorn):
  python run.py > output.txt
"""

import collections
import json
import os
import signal
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
USERS = [f"u-{i:05d}" for i in range(3000)]
REPEAT = 6


def start(cmd, rule, port):
    env = dict(os.environ, FLAG_RULE=rule)
    env.pop("PYTHONHASHSEED", None)
    p = subprocess.Popen(cmd, cwd=HERE, env=env, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=True)
    for _ in range(100):
        try:
            ask(port, "u-ready")
            return p
        except OSError:
            time.sleep(0.1)
    raise RuntimeError("server did not start")


def stop(p):
    os.killpg(p.pid, signal.SIGTERM)
    p.wait()


def ask(port, user):
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/?user={user}") as r:
        return json.loads(r.read())


def gunicorn(port):
    return [sys.executable, "-m", "gunicorn", "-w", "3", "-b", f"127.0.0.1:{port}", "app:wsgi"]


def uvicorn(port, workers=3):
    return [sys.executable, "-m", "uvicorn", "--workers", str(workers),
            "--port", str(port), "--log-level", "error", "app:asgi"]


def report(name, answers):
    """answers: user -> list of (pid, on)."""
    by_pid = collections.defaultdict(list)
    mixed = 0
    for user, rows in answers.items():
        for pid, on in rows:
            by_pid[pid].append(on)
        if len({on for _, on in rows}) > 1:
            mixed += 1
    print(f"== {name}")
    for i, (pid, ons) in enumerate(sorted(by_pid.items())):
        print(f"  process {i + 1}: {len(ons)} requests, on {sum(ons) / len(ons):.1%}")
    seen = sum(len({pid for pid, _ in rows}) for rows in answers.values()) / len(answers)
    print(f"  users {len(answers)}, processes seen per user {seen:.2f}")
    print(f"  users whose answer changed: {mixed} ({mixed / len(answers):.1%})")
    return mixed / len(answers)


def same_port(name, cmd, rule):
    p = start(cmd, rule, 18080)
    answers = {u: [] for u in USERS}
    for _ in range(REPEAT):
        for u in USERS:
            a = ask(18080, u)
            answers[u].append((a["pid"], a["on"]))
    stop(p)
    return report(name, answers)


def three_pods(rule):
    """Three independent servers behind a round-robin balancer."""
    ports = [18081, 18082, 18083]
    procs = [start(uvicorn(port, 1), rule, port) for port in ports]
    answers = {u: [] for u in USERS}
    for r in range(REPEAT):
        for i, u in enumerate(USERS):
            a = ask(ports[(i + r) % 3], u)
            answers[u].append((a["pid"], a["on"]))
    for p in procs:
        stop(p)
    return report(f"3 pods (uvicorn x3, round robin), {rule}", answers)


def restart(rule):
    """Who is in the 10% before and after restarting gunicorn."""
    sets = []
    for _ in range(2):
        p = start(gunicorn(18080), rule, 18080)
        sets.append({u for u in USERS if ask(18080, u)["on"]})
        stop(p)
    before, after = sets
    print(f"== restart gunicorn, {rule}")
    print(f"  on before {len(before)}, on after {len(after)}, on both {len(before & after)}"
          f" ({len(before & after) / len(before):.1%} of before)")


def timeline():
    """One user asks every 0.5 s; record when and which worker answered."""
    p = start(uvicorn(18080), "builtin", 18080)
    user = None
    for u in USERS:  # pick the first user whose answer differs between workers
        if len({ask(18080, u)["on"] for _ in range(REPEAT)}) > 1:
            user = u
            break
    pids = {}
    print(f"== timeline: uvicorn --workers 3, builtin, user {user}, every 0.5 s")
    t0 = time.monotonic()
    for i in range(16):
        a = ask(18080, user)
        t = time.monotonic() - t0
        w = pids.setdefault(a["pid"], len(pids) + 1)
        print(f"  t={t:.3f} worker={w} on={a['on']}")
        time.sleep(0.5)
    stop(p)


if __name__ == "__main__":
    print(f"python {sys.version.split()[0]}, users {len(USERS)}, requests per user {REPEAT}")
    same_port("gunicorn -w 3 (fork), builtin", gunicorn(18080), "builtin")
    same_port("uvicorn --workers 3 (spawn), builtin", uvicorn(18080), "builtin")
    same_port("uvicorn --workers 3 (spawn), crc32", uvicorn(18080), "crc32")
    three_pods("builtin")
    three_pods("crc32")
    restart("builtin")
    restart("crc32")
    timeline()
