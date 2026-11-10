"""Stored price vs market price of a push-style price feed (simulation).

No network access. The market price is a seeded random walk, not real data.
Update rule (Chainlink docs, architecture-decentralized-model): a round starts
when the off-chain value deviates from the on-chain value by more than the
deviation threshold, or when the heartbeat time has passed since the last update.
Settings for this experiment (not taken from any real feed):
  deviation threshold 0.5 %, heartbeat 3600 s,
  a round reaches the chain LAG seconds after it starts (12 s or 60 s),
  the application accepts an answer up to 300 s old (as in price_feed.py).
Market: 3 hours, 1 s steps, 2,000 USD start, 0.01 % noise per second,
a crash of -15 % between 5,400 s and 5,700 s.
Run: python3 deviation_heartbeat.py
"""
import random

SEED = 20261110
DURATION = 3 * 3600
DEVIATION = 0.005
HEARTBEAT = 3600
MAX_AGE = 300
CRASH = (5400, 5700, -0.15)


def market(seed=SEED):
    rng = random.Random(seed)
    start, end, drop = CRASH
    per_sec = (1 + drop) ** (1 / (end - start))
    price, out = 2000.0, []
    for t in range(DURATION):
        price *= 1 + rng.gauss(0, 0.0001)
        if start <= t < end:
            price *= per_sec
        out.append(price)
    return out


def feed(prices, lag):
    """Return stored price, age of the stored answer, and update times."""
    stored, updated_at = prices[0], 0
    pending = None  # (arrival time, observed price)
    stored_s, age_s, updates = [], [], []
    for t, p in enumerate(prices):
        if pending and t >= pending[0]:
            stored, updated_at = pending[1], t
            updates.append(t)
            pending = None
        if pending is None and (abs(p / stored - 1) > DEVIATION
                                or t - updated_at >= HEARTBEAT):
            pending = (t + lag, p)
        stored_s.append(stored)
        age_s.append(t - updated_at)
    return stored_s, age_s, updates


def gap(prices, stored):
    return [100 * abs(s / p - 1) for p, s in zip(prices, stored)]


def main():
    prices = market()
    start, end, _ = CRASH
    print(f"market: {prices[0]:.2f} -> min {min(prices):.2f} USD")
    for lag in (12, 60):
        stored, age, updates = feed(prices, lag)
        g = gap(prices, stored)
        calm = max(g[:start])
        crash = max(g[start:end + 600])
        stale = sum(a > MAX_AGE for a in age[:start]) / start
        print(f"lag {lag:>2} s: updates {len(updates):>3} "
              f"(crash window {sum(start <= u < end + 600 for u in updates)}), "
              f"max gap before crash {calm:.2f} %, during crash {crash:.2f} %, "
              f"answer older than {MAX_AGE} s before crash {100 * stale:.0f} % of time")


if __name__ == "__main__":
    main()
