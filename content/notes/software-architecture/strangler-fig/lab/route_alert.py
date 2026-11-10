"""Simulation: does an error-rate alert on the total notice one migrated route?

Assumptions (simulation, not a measurement):
- 20 routes. Traffic per route follows Zipf (s = 1); 1,000 requests/min in total.
- The route of rank 10 (about 2.8% of traffic) moves to the new system at
  minute 30. Every other route stays on the legacy system.
- Legacy error rate is 0.5% on every route. The new system's error rate on the
  migrated route is NEW_ERR (8% in the time series, swept in the second part).
- Errors are drawn per minute from a binomial distribution (random.seed fixed).
- After the switch, alerts are evaluated every minute over the last 5 minutes:
    total: errors / requests of all routes > 1%
    route: errors / requests of the migrated route on the new system > 3%,
           only when the window has at least 50 such requests
"""

import random

ROUTES, TOTAL_RPM, RANK = 20, 1000, 10
BASE_ERR, SWITCH, MINUTES, WINDOW = 0.005, 30, 90, 5
TOTAL_LIMIT, ROUTE_LIMIT, MIN_REQ = 0.01, 0.03, 50

H = sum(1 / k for k in range(1, ROUTES + 1))
SHARE = [(1 / k) / H for k in range(1, ROUTES + 1)]
RPM = [round(TOTAL_RPM * s) for s in SHARE]


def binom(rng, n, p):
    return sum(rng.random() < p for _ in range(n))


def run(new_err, seed):
    """Return per-minute windowed rates and the first alert minute of each kind."""
    rng = random.Random(seed)
    tot_req, tot_err, rt_req, rt_err = [], [], [], []
    for t in range(MINUTES):
        req = err = 0
        r_req = r_err = 0
        for i, n in enumerate(RPM):
            migrated = i == RANK - 1 and t >= SWITCH
            e = binom(rng, n, new_err if migrated else BASE_ERR)
            req, err = req + n, err + e
            if migrated:
                r_req, r_err = n, e
        tot_req.append(req); tot_err.append(err)
        rt_req.append(r_req); rt_err.append(r_err)
    total_rate, route_rate = [], []
    first = {"total": None, "route": None}
    for t in range(MINUTES):
        lo = max(0, t - WINDOW + 1)
        tr = sum(tot_err[lo:t + 1]) / sum(tot_req[lo:t + 1])
        n = sum(rt_req[lo:t + 1])
        rr = sum(rt_err[lo:t + 1]) / n if n else None
        total_rate.append(tr); route_rate.append(rr)
        if t < SWITCH:
            continue
        if tr > TOTAL_LIMIT and first["total"] is None:
            first["total"] = t
        if n >= MIN_REQ and rr > ROUTE_LIMIT and first["route"] is None:
            first["route"] = t
    failed = {k: (None if v is None else sum(rt_err[SWITCH:v + 1]))
              for k, v in first.items()}
    return total_rate, route_rate, first, failed


SWEEP = [0.005, 0.01, 0.02, 0.03, 0.05, 0.08, 0.12, 0.16, 0.20, 0.25, 0.30]
SEEDS = 200


def sweep():
    rows = []
    for e in SWEEP:
        hit = {"total": 0, "route": 0}
        for s in range(SEEDS):
            first = run(e, s)[2]
            for k in hit:
                hit[k] += first[k] is not None
        rows.append((e, hit["total"] / SEEDS, hit["route"] / SEEDS))
    return rows


def main():
    print(f"routes={ROUTES} total={TOTAL_RPM} req/min migrated=rank {RANK} "
          f"({SHARE[RANK - 1]:.1%} of traffic, {RPM[RANK - 1]} req/min)")
    total_rate, route_rate, first, failed = run(0.08, 0)
    print("time series (new error 8%, seed 0):")
    print(f"  total error rate after switch: max {max(total_rate[SWITCH:]):.2%}")
    for k in ("total", "route"):
        when = "never" if first[k] is None else f"minute {first[k] - SWITCH + 1} after switch"
        print(f"  {k:5} alert: {when}, failed requests until then: {failed[k]}")
    print(f"sweep: alert within {MINUTES - SWITCH} min after switch, {SEEDS} seeds")
    print("  new_err  total_alert  route_alert")
    for e, pt, pr in sweep():
        print(f"  {e:6.1%}  {pt:10.1%}  {pr:10.1%}")


if __name__ == "__main__":
    main()
