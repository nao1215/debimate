"""Availability of quorum reads and writes under independent node failures.

Assumption: each of the N replicas is down with probability p, independently
of the others (no correlated failures, no partitions). An operation that needs
k responses succeeds when at least k replicas are up:

    P(at least k of N up) = sum_{i=k..N} C(N, i) (1 - p)^i p^(N - i)

The configurations are the N = 3 table in the note, plus N = 5 majority.

Run: python3 availability.py > availability_output.txt
"""

from math import comb

CONFIGS = [  # (label, N, W, R)
    ("N=3 W=1 R=3", 3, 1, 3),
    ("N=3 W=2 R=2", 3, 2, 2),
    ("N=3 W=3 R=1", 3, 3, 1),
    ("N=5 W=3 R=3", 5, 3, 3),
]
PS = [0.001, 0.01, 0.05, 0.1, 0.2]


def available(n, k, p):
    """Probability that at least k of n replicas are up."""
    return sum(comb(n, i) * (1 - p) ** i * p ** (n - i) for i in range(k, n + 1))


def main():
    print("unavailability = 1 - P(at least k replicas up), independent failures")
    for p in PS:
        print(f"\np = {p:g}")
        print(f"{'config':<13} {'write unavail':>14} {'read unavail':>13}")
        for label, n, w, r in CONFIGS:
            print(f"{label:<13} {1 - available(n, w, p):>14.3e} "
                  f"{1 - available(n, r, p):>13.3e}")


if __name__ == "__main__":
    main()
