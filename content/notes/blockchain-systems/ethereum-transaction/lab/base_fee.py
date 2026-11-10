"""Base fee per block under EIP-1559 (calculation only, no network access).

The update rule is copied from https://eips.ethereum.org/EIPS/eip-1559
(BASE_FEE_MAX_CHANGE_DENOMINATOR = 8, ELASTICITY_MULTIPLIER = 2).
Assumptions: the gas limit stays at 36,000,000 (the ratio used/target is what
matters), the first base fee is 10 gwei, and every block has the same usage.
Run: python3 base_fee.py
"""

GWEI = 10**9
BASE_FEE_MAX_CHANGE_DENOMINATOR = 8
ELASTICITY_MULTIPLIER = 2
GAS_LIMIT = 36_000_000
START = 10 * GWEI
MAX_FEE = 30 * GWEI  # maxFeePerGas of the example in the note
USAGES = (1.00, 0.75, 0.50, 0.25, 0.00)
BLOCKS = 24


def next_base_fee(base_fee, gas_used, gas_limit=GAS_LIMIT):
    target = gas_limit // ELASTICITY_MULTIPLIER
    if gas_used == target:
        return base_fee
    if gas_used > target:
        delta = max(base_fee * (gas_used - target) // target
                    // BASE_FEE_MAX_CHANGE_DENOMINATOR, 1)
        return base_fee + delta
    delta = base_fee * (target - gas_used) // target // BASE_FEE_MAX_CHANGE_DENOMINATOR
    return base_fee - delta


def series(usage, blocks=BLOCKS):
    fees = [START]
    for _ in range(blocks):
        fees.append(next_base_fee(fees[-1], int(GAS_LIMIT * usage)))
    return fees


def main():
    print("block " + " ".join(f"{int(u * 100):>6}%" for u in USAGES))
    table = {u: series(u) for u in USAGES}
    for n in range(0, BLOCKS + 1, 2):
        print(f"{n:>5} " + " ".join(f"{table[u][n] / GWEI:7.2f}" for u in USAGES))
    for u in (1.00, 0.75):
        over = next(n for n, f in enumerate(series(u, 100)) if f > MAX_FEE)
        print(f"{int(u * 100)}% full: base fee exceeds 30 gwei at block {over} "
              f"({over * 12} s with 12 s slots)")
    print(f"one full block: x{table[1.00][1] / START:.3f}, one empty block: "
          f"x{table[0.00][1] / START:.3f}")


if __name__ == "__main__":
    main()
