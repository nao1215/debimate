"""Uniswap v2 型の定数積プールで、同じ 3 件の取引を並べ替えて結果を比べる。

ネットワークには接続せず、整数の計算だけを行う。gas 代は含めない。
"""

USDC = 10**6   # USDC は小数 6 桁
ETH = 10**18   # ETH は小数 18 桁（wei）


def amount_out(amount_in, reserve_in, reserve_out):
    """UniswapV2Library.getAmountOut と同じ式。入力の 0.3% が手数料になる。"""
    amount_in_with_fee = amount_in * 997
    return amount_in_with_fee * reserve_out // (reserve_in * 1000 + amount_in_with_fee)


class Pool:
    def __init__(self, usdc=3_000_000 * USDC, eth=1_000 * ETH):
        self.usdc = usdc
        self.eth = eth

    def buy_eth(self, usdc_in):
        out = amount_out(usdc_in, self.usdc, self.eth)
        self.usdc += usdc_in
        self.eth -= out
        return out

    def sell_eth(self, eth_in):
        out = amount_out(eth_in, self.eth, self.usdc)
        self.eth += eth_in
        self.usdc -= out
        return out


def run(order, victim_usdc, min_eth, front_usdc):
    """A: 利用者の買い、B: 攻撃者の買い、C: 攻撃者の売り（B で得た ETH を全て売る）。"""
    pool = Pool()
    result = {}
    attacker_eth = 0
    for tx in order:
        if tx == "A":
            # Router は受取量が amountOutMin を下回ると取引全体を取り消す
            if amount_out(victim_usdc, pool.usdc, pool.eth) < min_eth:
                result["A"] = None
                continue
            result["A"] = pool.buy_eth(victim_usdc)
        elif tx == "B":
            attacker_eth = pool.buy_eth(front_usdc)
        elif tx == "C":
            result["C"] = pool.sell_eth(attacker_eth)
    result["profit"] = result["C"] - front_usdc
    return result


def min_out(victim_usdc, tolerance_bps):
    """画面で見積もった受取量から、許容する下落分を引いた最低受取量。"""
    quote = amount_out(victim_usdc, Pool().usdc, Pool().eth)
    return quote * (10_000 - tolerance_bps) // 10_000


def largest_front(victim_usdc, min_eth):
    """利用者の取引が取り消されない範囲で、最も大きい先回りの買いを二分探索する。"""
    lo, hi = 0, 3_000_000 * USDC
    while lo < hi:
        mid = (lo + hi + 1) // 2
        pool = Pool()
        pool.buy_eth(mid)
        if amount_out(victim_usdc, pool.usdc, pool.eth) >= min_eth:
            lo = mid
        else:
            hi = mid - 1
    return lo


def sweep_point(victim_usdc, tolerance_bps):
    """許容幅ごとに、取り消されない最大の先回りで sandwich を組む。"""
    floor = min_out(victim_usdc, tolerance_bps)
    front = largest_front(victim_usdc, floor)
    r = run("BAC", victim_usdc, floor, front)
    r["front"] = front
    return r


def fmt_eth(v):
    return "revert" if v is None else f"{v / ETH:.6f} ETH"


def fmt_usdc(v):
    return f"{v / USDC:+,.2f} USDC"


if __name__ == "__main__":
    victim = 10_000 * USDC
    tol = 100  # 1.00%
    floor = min_out(victim, tol)
    front = largest_front(victim, floor)
    print("pool: 3,000,000 USDC / 1,000 ETH, victim buys with 10,000 USDC")
    print(f"quote {fmt_eth(min_out(victim, 0))}, amountOutMin (1%) {fmt_eth(floor)}")
    print(f"attacker front-run: {front / USDC:,.2f} USDC")
    print()
    for order in ("ABC", "BAC"):
        r = run(order, victim, floor, front)
        print(f"order {'->'.join(order)}: victim gets {fmt_eth(r['A'])}, "
              f"attacker {fmt_usdc(r['profit'])}")
    print()
    print("tolerance  front-run  victim loss        attacker profit")
    quote = min_out(victim, 0)
    for bps in (10, 50, 100, 200, 300, 500):
        r = sweep_point(victim, bps)
        loss = quote - r["A"]
        print(f"{bps / 100:>8.2f}%  {r['front'] / USDC:>9,.0f}  "
              f"{loss / ETH:.6f} ETH ({loss * 3_000 // ETH:>3} USDC)  "
              f"{r['profit'] / USDC:>8.2f} USDC")
