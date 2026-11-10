"""A size-limited mempool and its rolling minimum fee rate (simulation).

No bitcoind, no network. The rule follows Bitcoin Core v30.0 src/txmempool.cpp:
  TrimToSize removes the lowest fee rate entry while the pool is over the limit,
  and raises the rolling minimum to (removed fee rate + incremental relay fee);
  GetMinFee decays the rolling minimum with a 12 h half-life (3 h below 1/4 of
  the limit, 6 h below 1/2) only after a block has arrived since the last bump,
  and drops it to 0 below half of the incremental relay fee.
  DEFAULT_INCREMENTAL_RELAY_FEE and DEFAULT_MIN_RELAY_TX_FEE are 0.1 sat/vB
  (src/policy/policy.h).
Simplifications (assumptions, not measurements):
  the limit counts vsize, not memory usage, and is scaled down to 3,000,000 vB;
  every transaction is 250 vB and has no parent or child;
  a block arrives every 600 s exactly and takes the best 1,000,000 vB;
  fee rates follow a log-normal distribution (median 3 sat/vB, sigma 1.0);
  arrivals are Poisson: 6,000 tx per 10 min for the first 6 h (1.5 blocks'
  worth), then 2,400 tx per 10 min (0.6 blocks' worth), 36 h in total.
Run: python3 rolling_min_fee.py
"""
import bisect
import math
import random

SEED = 20261110
LIMIT = 3_000_000
TX_VB = 250
BLOCK_VB = 1_000_000
INCREMENTAL = 0.1
MIN_RELAY = 0.1
HALFLIFE = 12 * 3600
HOURS = 36
BUSY_HOURS = 6
RATE_BUSY, RATE_CALM = 6000 / 600, 2400 / 600  # tx per second


class Mempool:
    def __init__(self):
        self.rates = []  # sorted fee rates, one entry per transaction
        self.rolling = 0.0
        self.block_since_bump = True
        self.last_update = 0.0

    def size(self):
        return len(self.rates) * TX_VB

    def min_fee(self, now):
        if not self.block_since_bump or self.rolling == 0:
            return self.rolling
        if now > self.last_update + 10:
            half = HALFLIFE
            if self.size() < LIMIT / 4:
                half /= 4
            elif self.size() < LIMIT / 2:
                half /= 2
            self.rolling /= 2 ** ((now - self.last_update) / half)
            self.last_update = now
            if self.rolling < INCREMENTAL / 2:
                self.rolling = 0.0
                return 0.0
        return max(self.rolling, INCREMENTAL)

    def accept(self, rate, now):
        if rate < MIN_RELAY or rate < self.min_fee(now):
            return False
        bisect.insort(self.rates, rate)
        while self.size() > LIMIT:
            removed = self.rates.pop(0) + INCREMENTAL
            if removed > self.rolling:
                self.rolling = removed
                self.block_since_bump = False
        return True

    def mine(self, now):
        take = BLOCK_VB // TX_VB
        del self.rates[-take:]
        self.block_since_bump = True
        self.last_update = now  # Core resets the decay clock on each block


def run(seed=SEED):
    rng = random.Random(seed)
    pool = Mempool()
    t, next_block, rejected, samples = 0.0, 600.0, 0, []
    while t < HOURS * 3600:
        rate = RATE_BUSY if t < BUSY_HOURS * 3600 else RATE_CALM
        t += rng.expovariate(rate)
        while next_block <= t:
            # sample just before each block takes its transactions
            samples.append((next_block / 3600, pool.size(),
                            max(pool.min_fee(next_block), MIN_RELAY)))
            pool.mine(next_block)
            next_block += 600
        fee = math.exp(rng.gauss(math.log(3), 1.0))
        if not pool.accept(fee, t):
            rejected += 1
    return samples, rejected


def main():
    samples, rejected = run()
    print("hour  mempool_vB  min_fee_sat/vB")
    for h, size, fee in samples:
        if abs(h - round(h)) < 1e-9 and round(h) % 3 == 0:
            print(f"{round(h):>4} {size:>11,} {fee:>15.2f}")
    peak = max(samples, key=lambda s: s[2])
    print(f"peak min fee {peak[2]:.2f} sat/vB at hour {peak[0]:.2f}")
    print(f"rejected arrivals below the minimum: {rejected:,}")


if __name__ == "__main__":
    main()
