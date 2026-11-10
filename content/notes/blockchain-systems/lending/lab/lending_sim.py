"""Liquidations in an over-collateralized lending market (no network access).

Three borrowers deposit 10 ETH each and borrow USDC. The ETH price falls
from 2,000 to 1,200 USDC. Liquidators repay part of the debt of any position
whose health factor is below 1 and take ETH with a bonus.
"smooth": the price falls 10 USDC per step.
"gap":    the price jumps from 1,950 to 1,300 in one step.
"""

LT = 0.80  # liquidation threshold
BONUS = 1.05  # liquidator receives 105% of the repaid debt in collateral
CLOSE_FACTOR = 0.5  # share of the debt repayable per call while HF > 0.95


def health_factor(p, price):
    if p["debt"] == 0:
        return float("inf")
    return p["eth"] * price * LT / p["debt"]


def liquidate(p, price):
    """One liquidation call. Returns the debt left without collateral."""
    hf = health_factor(p, price)
    repay = p["debt"] * (CLOSE_FACTOR if hf > 0.95 else 1.0)
    seize = repay * BONUS / price  # ETH sent to the liquidator
    if seize > p["eth"]:  # not enough collateral: take all of it
        seize = p["eth"]
        repay = seize * price / BONUS
    p["eth"] -= seize
    p["debt"] -= repay
    if p["eth"] == 0 and p["debt"] > 0:
        bad, p["debt"] = p["debt"], 0.0
        return bad
    return 0.0


def run(prices):
    positions = {name: {"eth": 10.0, "debt": debt}
                 for name, debt in (("A", 8000.0), ("B", 12000.0), ("C", 15000.0))}
    bad_debt, calls, history = 0.0, 0, []
    for price in prices:
        for p in positions.values():
            if health_factor(p, price) < 1:
                bad_debt += liquidate(p, price)
                calls += 1
        history.append((price, [health_factor(p, price) for p in positions.values()]))
    return positions, bad_debt, calls, history


smooth = [2000 - 10 * i for i in range(81)]
gap = smooth[:6] + [p for p in smooth if p <= 1300]

for label, prices in (("smooth", smooth), ("gap", gap)):
    positions, bad_debt, calls, history = run(prices)
    print(f"[{label}] {prices[0]} -> {prices[-1]} USDC, {calls} liquidation calls")
    for name, p in positions.items():
        print(f"  {name}: eth={p['eth']:6.3f} debt={p['debt']:9.2f}")
    print(f"  bad debt: {bad_debt:.2f} USDC")
    for price, hfs in history:  # health factors after the liquidations
        print(f"  hf {label} {price} " + " ".join(f"{h:.3f}" for h in hfs))
