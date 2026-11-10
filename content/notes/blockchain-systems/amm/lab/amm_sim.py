"""Uniswap v2 style constant product pool (calculation only, no network access).

Python 3.10+ standard library only. Amounts are floats for readability; the
contract uses integers and rounds the output down.
Run: python3 amm_sim.py
"""
from math import sqrt

FEE = 0.003  # 0.3% of the input stays in the pool


class Pool:
    def __init__(self, usdc, eth):
        self.usdc = usdc  # reserve x
        self.eth = eth  # reserve y

    def price(self):
        """Spot price in USDC per ETH (x / y, fee excluded)."""
        return self.usdc / self.eth

    def k(self):
        return self.usdc * self.eth

    @staticmethod
    def amount_out(amount_in, reserve_in, reserve_out):
        """UniswapV2Library.getAmountOut: in*997*out / (rIn*1000 + in*997)."""
        in_with_fee = amount_in * (1 - FEE)
        return in_with_fee * reserve_out / (reserve_in + in_with_fee)

    def buy_eth(self, usdc_in):
        out = self.amount_out(usdc_in, self.usdc, self.eth)
        self.usdc += usdc_in
        self.eth -= out
        return out

    def sell_eth(self, eth_in):
        out = self.amount_out(eth_in, self.eth, self.usdc)
        self.eth += eth_in
        self.usdc -= out
        return out


# 1. Price impact: the larger the trade relative to the reserve, the worse the price.
print("== 1. price impact (pool 3,000,000 USDC / 1,000 ETH) ==")
for share in (0.001, 0.01, 0.05, 0.10, 0.30, 1.00):
    pool = Pool(3_000_000, 1_000)
    k_before = pool.k()
    usdc_in = pool.usdc * share
    eth_out = pool.buy_eth(usdc_in)
    avg = usdc_in / eth_out
    print(f"{usdc_in:>9,.0f} USDC -> {eth_out:8.3f} ETH  avg {avg:6,.0f} (+{(avg / 3000 - 1) * 100:6.2f}%)"
          f"  spot after {pool.price():6,.0f}  k +{(pool.k() / k_before - 1) * 100:.3f}%")


# 2. Arbitrage moves the pool to the outside price. The LP (owner of the whole
#    pool here) is compared with HODL (keeping the deposited tokens as they are).
def arbitrage(pool, market):
    """Trade toward the market price if it pays after the fee. Returns profit in USDC."""
    g = 1 - FEE
    x, y = pool.usdc, pool.eth
    if market * g > pool.price():  # ETH is cheap in the pool: buy ETH
        a = (sqrt(g * x * y * market) - x) / g  # input that maximizes the profit
        return pool.buy_eth(a) * market - a
    if market < pool.price() * g:  # ETH is expensive in the pool: sell ETH
        b = (sqrt(g * x * y / market) - y) / g
        return pool.sell_eth(b) - b * market
    return 0.0


def run(label, path):
    pool = Pool(3_000_000, 1_000)
    hold_usdc, hold_eth = pool.usdc, pool.eth
    arb = sum(arbitrage(pool, p) for p in path)
    p = path[-1]
    lp = pool.usdc + pool.eth * p
    hodl = hold_usdc + hold_eth * p
    r = p / 3000
    il = 2 * sqrt(r) / (1 + r) - 1  # impermanent loss without fees
    print(f"{label:<15} price {p:5,.0f}  pool ETH {pool.eth:7.1f}"
          f"  LP vs HODL {(lp / hodl - 1) * 100:+6.2f}% (no fee {il * 100:+6.2f}%)"
          f"  arb {arb:6,.0f}")


print()
print("== 2. arbitrage, LP vs HODL ==")
up = [3000 * 1.01 ** i for i in range(1, 71)]  # 1% per step, about 2x
run("up to 2x", up)
run("2x and back", up + up[-2::-1] + [3000])
run("chop +-2% x100", [3060, 3000] * 100)
run("down to 1/2", [3000 * 0.99 ** i for i in range(1, 70)])

# 3. TWAP: the pair adds (price x seconds) to a cumulative value at the start of
#    each block. The attacker pushes the price to 4x at the end of the last
#    `held` blocks; arbitrage restores it at the start of the next block.
BLOCK = 12  # seconds per slot


def manipulate(held, target=4.0, blocks=150):
    pool = Pool(3_000_000, 1_000)
    market = pool.price()
    acc, cost = [0.0], 0.0
    for n in range(blocks):
        arbitrage(pool, market)  # first trade of block n
        if n >= blocks - held:  # attacker's trade at the end of block n
            usdc_in = pool.usdc * (sqrt(target) - 1) / (1 - FEE)
            cost += usdc_in - pool.buy_eth(usdc_in) * market
        acc.append(acc[-1] + pool.price() * BLOCK)  # this price holds for one block

    def twap(seconds):
        return (acc[-1] - acc[-1 - seconds // BLOCK]) / seconds

    print(f"held {held:>3} blocks  spot {pool.price():6,.0f}  TWAP 24s {twap(24):6,.0f}"
          f"  TWAP 30min {twap(1800):6,.0f}  attacker cost {cost / 1e6:6.1f}M USDC")


print()
print("== 3. pushing the price to 4x: spot vs TWAP (block 12 s) ==")
for held in (0, 1, 10, 150):
    manipulate(held)
