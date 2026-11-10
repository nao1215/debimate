"""Measure repeated squaring mod a 2048-bit n on this machine.

Part 1: wall time of t sequential squarings for several t (one core).
Part 2: the same chain with P worker processes. The chain cannot be split,
so each worker solves its own puzzle; we record the wall time until ONE
puzzle is solved. As a contrast, t independent squarings (x_i^2 mod n for
different x_i) are split evenly over P workers.

Run: uv run --with sympy python lab/squaring_time.py
Timings depend on the machine and its load; the chain results are checked
against the phi(n) shortcut so the computation itself is deterministic.
"""

import os
import random
import time
from multiprocessing import Pool

from sympy import nextprime

# Deterministic 1024-bit primes (top two bits set, so n has exactly 2048 bits)
rng = random.Random(20261110)
p = nextprime(rng.getrandbits(1024) | (3 << 1022))
q = nextprime(rng.getrandbits(1024) | (3 << 1022))
n, phi = p * q, (p - 1) * (q - 1)

T_SWEEP = [50_000, 100_000, 200_000, 400_000, 800_000]
T_PAR = 200_000
WORKERS = [1, 2, 4, 8, 16]
REPEAT = 5  # keep the fastest of 5 runs; other processes on the machine only add time
# Worker i runs on logical CPU i (0-15). CPUs 16-31 are the SMT siblings of 0-15,
# so 16 workers occupy 16 distinct physical cores.


def chain(args):
    """t sequential squarings of a; returns the result and its own time."""
    a, t, cpu = args
    os.sched_setaffinity(0, {cpu})
    start = time.perf_counter()
    x = a
    for _ in range(t):
        x = x * x % n
    return x, time.perf_counter() - start


def independent(args):
    """Square `count` different values once each (no dependency)."""
    seed, count, cpu = args
    os.sched_setaffinity(0, {cpu})
    x = pow(seed, 65537, n)  # a 2048-bit starting value
    for i in range(count):
        _ = (x + i) * (x + i) % n
    return count


def main():
    print(f"n: {n.bit_length()} bits, logical CPUs: {os.cpu_count()}, repeat: {REPEAT} (fastest kept)")
    print("part 1: one chain, one core")
    chain((2, T_SWEEP[0], 0))  # warm-up
    for t in T_SWEEP:
        runs = [chain((2, t, 0)) for _ in range(REPEAT)]
        x = runs[0][0]
        sec = min(s for _, s in runs)
        ok = x == pow(2, pow(2, t, phi), n)
        print(f"  t={t:>7,}  {sec:6.2f} s  {t / sec:8,.0f} squarings/s  match={ok}")

    print(f"part 2: t={T_PAR:,}, wall time until one result")
    for w in WORKERS:
        firsts, chain_walls, indep_walls = [], [], []
        with Pool(w) as pool:
            for _ in range(REPEAT):
                start = time.perf_counter()
                res = pool.map(chain, [(2 + i, T_PAR, i) for i in range(w)])
                chain_walls.append(time.perf_counter() - start)
                ok = all(x == pow(2 + i, pow(2, T_PAR, phi), n)
                         for i, (x, _) in enumerate(res))
                firsts.append(min(sec for _, sec in res))

                start = time.perf_counter()
                pool.map(independent, [(3 + i, T_PAR // w, i) for i in range(w)])
                indep_walls.append(time.perf_counter() - start)
        first = min(firsts)
        chain_wall = min(chain_walls)
        indep_wall = min(indep_walls)
        print(f"  workers={w:>2}  chain: first done {first:5.2f} s "
              f"(all {chain_wall:5.2f} s, match={ok})  "
              f"independent squarings: {indep_wall:5.2f} s")


if __name__ == "__main__":
    main()
