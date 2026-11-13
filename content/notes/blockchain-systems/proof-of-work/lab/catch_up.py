"""Exact probabilities for the double_spend.py race, without mining.

Each new block is honest with p = 0.6 and the attacker's with q = 0.4.
The shop hands over the goods when the honest chain has Z = 2 blocks.
After that, the attacker wins when its chain is longer (a > h), or, as in
the white paper's "catch up", when it is as long (a >= h). It may give up
when it is GIVE_UP = 5 blocks behind. Run: python3 catch_up.py
"""
from fractions import Fraction

P, Q, Z = Fraction(3, 5), Fraction(2, 5), 2


def reach(d, target, give_up):
    """Probability that d = h - a falls to target before it rises to give_up."""
    if d <= target:
        return Fraction(1)
    if give_up is None:
        return (Q / P) ** (d - target)
    if d >= give_up:
        return Fraction(0)
    r = Q / P                                  # gambler's ruin with ratio q/p
    n, k = give_up - target, d - target
    return (r ** n - r ** k) / (r ** n - 1)


def win(tie, give_up):
    """Sum over a, the attacker's blocks found before the honest chain has Z."""
    target = 0 if tie else -1
    total = Fraction(0)
    for a in range(400):                      # P(a) = C(a+Z-1, a) p^Z q^a
        pr = (a + 1) * P ** Z * Q ** a         # Z = 2
        total += pr * reach(Z - a, target, give_up)
    return float(total)


for tie in (True, False):
    for give_up in (None, 5):
        rule = "a >= h" if tie else "a >  h"
        print(f"win when {rule}, give_up={give_up}: {win(tie, give_up):.3f}")
