"""Fixed-timeout heartbeat: detection delay vs. false suspicions (simulation).

Assumptions (not measurements):
- The node sends a heartbeat every T = 1 s for 10,000,000 s (about 116 days).
- Each heartbeat is lost independently with probability LOSS, otherwise it
  arrives after a one-way delay of BASE + a log-normal jitter.
- Stalls (a GC pause on the node, a congested path) start as a Poisson
  process and last a log-normal time. A heartbeat due during a stall leaves
  when the stall ends, so stalls produce long silences, not only losses.
- The Monitor keeps the latest receive time. A false suspicion is a silence
  longer than the timeout while the node is alive.
- For detection delay, the node crashes at 100,000 uniform random instants.
  Heartbeats already in flight still arrive; the Monitor declares failure at
  (latest receive time) + timeout.

Run: python3 sim.py > sim_output.txt
"""

import numpy as np

T = 1.0
N = 10_000_000
CRASHES = 100_000
MULTIPLIERS = [2, 3, 4, 5, 6, 8, 10]
SCENARIOS = {
    # name: (loss probability, base delay s, jitter median s, jitter sigma,
    #        stalls per hour, stall median s, stall sigma)
    "stable": (0.001, 0.0005, 0.0005, 0.5, 1 / 6, 0.3, 0.8),
    "jittery": (0.01, 0.08, 0.05, 1.2, 1.0, 2.0, 0.8),
}
DAYS = N * T / 86400


def run(name, seed=1):
    loss, base, median, sigma, per_hour, s_median, s_sigma = SCENARIOS[name]
    rng = np.random.default_rng(seed)
    send = np.arange(N) * T
    n_stall = rng.poisson(per_hour * N * T / 3600)
    start = np.sort(rng.uniform(0, N * T, n_stall))
    end = start + rng.lognormal(np.log(s_median), s_sigma, n_stall)
    j = np.searchsorted(start, send, side="right") - 1
    inside = (j >= 0) & (send < end[np.maximum(j, 0)])
    send = np.where(inside, end[np.maximum(j, 0)], send)
    arrive = send + base + rng.lognormal(np.log(median), sigma, N)
    arrive[rng.random(N) < loss] = -np.inf  # lost
    received = np.sort(arrive[np.isfinite(arrive)])
    gaps = np.diff(received)
    # Latest receive time among heartbeats sent up to index i.
    last = np.maximum.accumulate(arrive)
    crash = rng.uniform(10 * T, (N - 20) * T, CRASHES)
    # Heartbeats that left before the crash (send is non-decreasing).
    last_before = last[np.searchsorted(send, crash, side="right") - 1]
    rows = []
    for k in MULTIPLIERS:
        timeout = k * T
        false_per_day = np.count_nonzero(gaps > timeout) / DAYS
        delay = last_before + timeout - crash
        # Crash after an already-expired silence: detection is immediate.
        delay = np.maximum(delay, 0.0)
        rows.append((k, false_per_day, delay.mean(), np.percentile(delay, 99)))
    return rows


def main():
    print(f"T={T:g}s heartbeats={N} (~{DAYS:.0f} days) crashes={CRASHES}")
    for name, (loss, base, median, sigma, ph, sm, ss) in SCENARIOS.items():
        print(f"\n[{name}] loss={loss:g} delay={base * 1000:g}ms+lognormal("
              f"median={median * 1000:g}ms, sigma={sigma:g}) stalls={ph:.3g}/h "
              f"lognormal(median={sm:g}s, sigma={ss:g})")
        print("timeout  false/day  mean_delay_s  p99_delay_s")
        for k, fp, mean, p99 in run(name):
            print(f"{k:>4g}xT  {fp:>9.3f}  {mean:>12.2f}  {p99:>11.2f}")


if __name__ == "__main__":
    main()
