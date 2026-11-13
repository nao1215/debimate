"""The probability that an attacker with share q of the hash rate replaces a
transaction after z confirmations, by the formula in section 11 of the Bitcoin
white paper. The paper approximates the attacker's progress with a Poisson
distribution; Rosenfeld (arXiv:1402.2009) gives the exact values.
"""
import math


def whitepaper(q, z):
    p = 1 - q
    if q >= p:
        return 1.0                        # the attacker catches up with certainty
    lam = z * q / p
    s = 1.0
    for k in range(z + 1):
        poisson = math.exp(-lam) * lam ** k / math.factorial(k)
        s -= poisson * (1 - (q / p) ** (z - k))
    return s


if __name__ == "__main__":
    print("q     z=1        z=3        z=6        z=10")
    for q in (0.1, 0.2, 0.3, 0.4, 0.45, 0.5):
        print(f"{q:.2f}  " + "  ".join(f"{whitepaper(q, z):.7f}" for z in (1, 3, 6, 10)))
