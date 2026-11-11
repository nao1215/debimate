"""Simulate a caller with 40 threads whose downstream stops answering for 30 seconds.

Same setting as the Circuit Breaker note: requests A call the downstream, requests B
finish locally. A bulkhead caps how many threads A may hold at the same time.
"""

import heapq
import json
import random
import sys

END, OUTAGE = 60_000, (10_000, 40_000)  # milliseconds
POOL, TIMEOUT, LATENCY, LOCAL = 40, 2_000, 50, 5


def arrivals(seed=1):
    """Poisson arrivals, 100 req/s in total: half A, half B (same for all runs)."""
    rng, t, out = random.Random(seed), 0.0, {}
    while True:
        t += rng.expovariate(100 / 1000)
        if t >= END:
            return out
        out.setdefault(int(t), []).append(rng.choice("AB"))


def run(a_limit=None, outage=OUTAGE):
    """a_limit: max threads A may hold at once (None = no bulkhead)."""
    events, seq = [], 0
    busy = {"A": 0, "B": 0}
    st = {"a_ok": 0, "a_timeout": 0, "a_rejected": 0,
          "a_rejected_normal": 0, "a_normal": 0,
          "b_ok": [0] * 60, "b_rejected": [0] * 60, "busy_a": [0] * 60, "busy_b": [0] * 60}
    for now in range(END):
        while events and events[0][0] == now:
            _, _, kind, ok = heapq.heappop(events)
            busy[kind] -= 1
            if kind == "B":
                st["b_ok"][now // 1000] += 1
            else:
                st["a_ok" if ok else "a_timeout"] += 1
        for kind in arrivals_cache.get(now, []):
            in_outage = outage[0] <= now < outage[1]
            # normal: before the outage, or after the last timed-out call has returned
            normal = now < outage[0] or now >= outage[1] + TIMEOUT
            if kind == "A" and normal:
                st["a_normal"] += 1
            full = busy["A"] + busy["B"] >= POOL
            if kind == "A":
                if full or (a_limit is not None and busy["A"] >= a_limit):
                    st["a_rejected"] += 1
                    if normal:
                        st["a_rejected_normal"] += 1
                    continue
                busy["A"] += 1
                ok = not in_outage  # the outage never answers
                seq += 1
                heapq.heappush(events, (now + (LATENCY if ok else TIMEOUT), seq, "A", ok))
            else:
                if full:
                    st["b_rejected"][now // 1000] += 1
                    continue
                busy["B"] += 1
                seq += 1
                heapq.heappush(events, (now + LOCAL, seq, "B", True))
        if now % 1000 == 999:
            st["busy_a"][now // 1000] = busy["A"]
            st["busy_b"][now // 1000] = busy["B"]
    return st


arrivals_cache = arrivals()  # the same arrivals for every run (Poisson, seed 1)


def b_rate(st, lo=10, hi=40):
    ok = sum(st["b_ok"][lo:hi])
    rej = sum(st["b_rejected"][lo:hi])
    return ok / (ok + rej) if ok + rej else 1.0


if __name__ == "__main__":
    runs = {
        "shared 40": run(),
        "bulkhead A<=10": run(a_limit=10),
    }
    for name, st in runs.items():
        print(f"{name:18} B ok during outage {b_rate(st):6.1%}  "
              f"B ok {sum(st['b_ok'])}  B rejected {sum(st['b_rejected'])}  "
              f"A ok {st['a_ok']}  A timeout {st['a_timeout']}  A rejected {st['a_rejected']}  "
              f"busy A at 20s {st['busy_a'][20]}")
    print()
    print("a_limit  A rejected in normal time  B ok during outage")
    sweep = []
    for lim in (1, 2, 3, 4, 5, 6, 8, 10, 15, 20, 30, 40):
        st = run(a_limit=lim)
        r = st["a_rejected_normal"] / st["a_normal"]
        sweep.append({"limit": lim, "a_rejected_normal": r, "b_ok_outage": b_rate(st)})
        print(f"{lim:7}  {r:25.2%}  {b_rate(st):18.1%}")
    if "--json" in sys.argv:
        json.dump({"timeline": {k: {"b_ok": v["b_ok"], "b_rejected": v["b_rejected"],
                                    "busy_a": v["busy_a"], "busy_b": v["busy_b"]}
                                for k, v in runs.items()},
                   "sweep": sweep}, open("result.json", "w"), indent=1)
