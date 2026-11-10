"""Chance that one user ever builds a circuit whose Guard and Exit both belong
to the attacker, with a fixed Guard vs. a Guard re-picked for every circuit.

Model (simulation, not a measurement of the live Tor network):
- The attacker holds a fraction c of the guard bandwidth and of the exit
  bandwidth; relays are picked in proportion to bandwidth, so each pick lands
  on the attacker with probability c, independently.
- "rotate": every circuit picks a new Guard and a new Exit.
- "fixed": the user picks one Guard before the first circuit and keeps it for
  the whole horizon (no guard rotation inside the horizon); Exits are re-picked.
A circuit is compromised when both its Guard and its Exit are the attacker's.

Run: python3 lab/guard_exposure.py
"""

import random

USERS = 20_000
CIRCUITS = 1_000
C_VALUES = [0.05, 0.10]
CHECKPOINTS = [1, 10, 100, 1_000]
SEED = 20261110


def simulate(c, fixed_guard, rng):
    """Return, per checkpoint, the fraction of users compromised at least once."""
    first_hit = []  # circuit index of the first compromised circuit, or None
    for _ in range(USERS):
        guard_bad = rng.random() < c if fixed_guard else None
        hit = None
        for i in range(1, CIRCUITS + 1):
            g = guard_bad if fixed_guard else rng.random() < c
            if g and rng.random() < c:
                hit = i
                break
            if fixed_guard and not g:
                break  # an honest fixed Guard is never compromised in the horizon
        first_hit.append(hit)
    return {k: sum(1 for h in first_hit if h is not None and h <= k) / USERS
            for k in CHECKPOINTS}


def main():
    rng = random.Random(SEED)
    print(f"users={USERS:,}  circuits per user={CIRCUITS:,}  seed={SEED}")
    for c in C_VALUES:
        for fixed in (False, True):
            name = "fixed guard " if fixed else "rotate guard"
            sim = simulate(c, fixed, rng)
            cells = []
            for k in CHECKPOINTS:
                exact = c * (1 - (1 - c) ** k) if fixed else 1 - (1 - c * c) ** k
                cells.append(f"C={k:>5,}: {sim[k]:6.2%} (exact {exact:6.2%})")
            print(f"c={c:.2f} {name}  " + "  ".join(cells))


if __name__ == "__main__":
    main()
