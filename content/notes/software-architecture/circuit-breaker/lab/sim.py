"""Simulate a caller whose downstream service stops answering for 30 seconds."""

import heapq
import random

from breaker import CircuitBreaker

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


def run(use_breaker=False, attempts=1, retry_outside=True, timeout=TIMEOUT):
    """Requests A call the downstream; requests B finish locally in 5 ms."""
    cb = CircuitBreaker() if use_breaker else None
    events, seq, busy, arriving = [], 0, 0, arrivals()
    st = {"a_ok": 0, "a_failed": 0, "a_fast_fail": 0, "a_rejected": 0,
          "down_calls": [0] * 60, "b_ok": [0] * 60, "b_rejected": [0] * 60,
          "busy": [], "transitions": []}

    def push(at, kind, job, ok):
        nonlocal seq
        seq += 1
        heapq.heappush(events, (at, seq, kind, job, ok))

    def attempt(now, job):
        if cb and retry_outside:  # Retry(CircuitBreaker(call)): every attempt asks
            job["gen"] = cb.allow(now / 1000)
            if job["gen"] is None:
                return False  # rejected attempts are not retried
        st["down_calls"][now // 1000] += 1
        ok = not OUTAGE[0] <= now < OUTAGE[1]  # the outage never answers
        push(now + (LATENCY if ok else timeout), "A", job, ok)
        return True

    def finish(outcome):
        nonlocal busy
        busy -= 1
        st[outcome] += 1

    for now in range(END):
        before = cb.state if cb else None
        while events and events[0][0] == now:
            _, _, kind, job, ok = heapq.heappop(events)
            if kind == "B":
                busy -= 1
                st["b_ok"][now // 1000] += 1
                continue
            job["left"] -= 1
            if cb and retry_outside:
                cb.record(now / 1000, ok, job["gen"])
            if ok or job["left"] == 0:
                if cb and not retry_outside:
                    cb.record(now / 1000, ok, job["gen"])  # CircuitBreaker(Retry(call))
                finish("a_ok" if ok else "a_failed")
            elif not attempt(now, job):
                finish("a_fast_fail")
        for kind in arriving.get(now, []):
            if busy >= POOL:  # no thread left: reject at once (e.g. 503)
                if kind == "A":
                    st["a_rejected"] += 1
                else:
                    st["b_rejected"][now // 1000] += 1
            elif kind == "B":
                busy += 1
                push(now + LOCAL, "B", None, True)
            else:
                gen = cb.allow(now / 1000) if cb and not retry_outside else None
                if cb and not retry_outside and gen is None:
                    st["a_fast_fail"] += 1
                    continue
                busy += 1  # retries follow at once, with no backoff
                if not attempt(now, {"left": attempts, "gen": gen}):
                    finish("a_fast_fail")
        if cb and cb.state != before:
            st["transitions"].append((now / 1000, cb.state))
        if now % 100 == 0:
            st["busy"].append(busy)
    return st


SCENARIOS = {
    "no breaker": dict(),
    "breaker": dict(use_breaker=True),
    "breaker, timeout 30 s": dict(use_breaker=True, timeout=30_000),
    "3 attempts, no breaker": dict(attempts=3),
    "Retry(CircuitBreaker), 3 attempts": dict(use_breaker=True, attempts=3),
    "CircuitBreaker(Retry), 3 attempts": dict(use_breaker=True, attempts=3,
                                              retry_outside=False),
}


def main():
    for name, kw in SCENARIOS.items():
        st = run(**kw)
        out = slice(OUTAGE[0] // 1000, OUTAGE[1] // 1000)
        b_total = sum(st["b_ok"][out]) + sum(st["b_rejected"][out])
        print(f"== {name}")
        print(f"  downstream calls during outage: {sum(st['down_calls'][out])}")
        print(f"  B (local) served during outage: {sum(st['b_ok'][out])}/{b_total}")
        print(f"  A: ok={st['a_ok']} failed={st['a_failed']} "
              f"fast_fail={st['a_fast_fail']} rejected={st['a_rejected']}")
        if st["transitions"]:
            first = st["transitions"][:2]
            last = [t for t in st["transitions"] if t[1] == "CLOSED"][-1:]
            print("  transitions:", ", ".join(f"{t:.2f}s {s}" for t, s in first + last),
                  f"({len(st['transitions'])} total)")


if __name__ == "__main__":
    main()
