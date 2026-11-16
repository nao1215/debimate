"""セルを 4 つから 5 つに増やした時、既存の顧客の何人がセルを移るかを数える。

- 剰余     : hash(顧客 ID) % セルの数
- 一貫性ハッシュ : セル 1 つにつき 100 個の仮想ノードを置いたリング
- 割り当て表 : 顧客ごとに決めたセルを表に書いておく。セルを足しても既存の行は変えない

Run: python3 remap.py
"""

import bisect
import hashlib

N = 10_000
CUSTOMERS = [f"cust-{i:05d}" for i in range(N)]


def h(s):
    return int(hashlib.sha256(s.encode()).hexdigest(), 16)


def modulo(c, cells):
    return h(c) % cells


def ring(cells, vnodes=100):
    points = sorted((h(f"cell{k}#{v}"), k) for k in range(cells) for v in range(vnodes))
    keys = [p for p, _ in points]

    def lookup(c):
        i = bisect.bisect(keys, h(c)) % len(keys)
        return points[i][1]
    return lookup


def moved(before, after):
    return sum(1 for c in CUSTOMERS if before(c) != after(c))


if __name__ == "__main__":
    r4, r5 = ring(4), ring(5)
    table = {c: modulo(c, 4) for c in CUSTOMERS}  # 最初に作った表
    rows = [
        ("modulo", moved(lambda c: modulo(c, 4), lambda c: modulo(c, 5))),
        ("consistent_hash", moved(r4, r5)),
        ("table", moved(table.get, table.get)),
    ]
    for name, m in rows:
        print(f"{name:16s} moved {m:5d} / {N} ({m / N:.1%})")
    new5 = sum(1 for c in CUSTOMERS if r5(c) == 4)
    print(f"consistent_hash: customers in the new cell = {new5}")
