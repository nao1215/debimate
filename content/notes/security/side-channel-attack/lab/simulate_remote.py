"""Simulation: find a 1 us gap in response times buried in network jitter."""

import numpy as np

GAP_US = 1.0  # the slower candidate does 1 us more work on the server
TRIALS = 1000  # repeat each attack to estimate the success rate
COUNTS = [10, 30, 100, 300, 1000, 3000, 10000]


def jitter(rng, shape):
    """Network delay in us: a fixed floor plus a long right tail."""
    return 500.0 + rng.exponential(20.0, shape) + rng.lognormal(2.0, 1.0, shape)


def success_rate(stat, n, rng, random_delay_us=0.0):
    fast = jitter(rng, (TRIALS, n))
    slow = jitter(rng, (TRIALS, n)) + GAP_US
    if random_delay_us:
        fast += rng.uniform(0, random_delay_us, fast.shape)
        slow += rng.uniform(0, random_delay_us, slow.shape)
    return float(np.mean(stat(slow) > stat(fast)))  # attacker picks the slower one


STATS = {
    "mean": lambda x: x.mean(axis=1),
    "median": lambda x: np.median(x, axis=1),
    "p10": lambda x: np.percentile(x, 10, axis=1),
}


def run():
    rng = np.random.default_rng(1)
    rows = []
    for n in COUNTS:
        row = {name: success_rate(f, n, rng) for name, f in STATS.items()}
        row["p10+delay"] = success_rate(STATS["p10"], n, rng, random_delay_us=100.0)
        rows.append((n, row))
    return rows


if __name__ == "__main__":
    print("samples  mean  median  p10   p10+random_delay(0-100us)")
    for n, row in run():
        print(f"{n:7d}  {row['mean']:.2f}  {row['median']:.2f}    {row['p10']:.2f}  {row['p10+delay']:.2f}")
