# Lightning Network の支払い成功率を単純化したモデルで比べる（標準ライブラリのみ）
import json
import pathlib
import random
from collections import deque

N_NODES, LINKS_PER_NODE = 200, 2
AMOUNTS = [10_000, 30_000, 100_000, 300_000, 1_000_000, 3_000_000]  # sat
PARTS = [1, 2, 4, 8]
TRIALS, MAX_ATTEMPTS = 1000, 10

rng = random.Random(42)

# チャネルのグラフ: 後から来たノードは、繋がりの多いノードと開設しやすい
capacity, ends = {}, [0, 1]
capacity[(0, 1)] = capacity[(1, 0)] = 1_000_000
for new in range(2, N_NODES):
    peers = set()
    while len(peers) < min(LINKS_PER_NODE, new):
        peers.add(rng.choice(ends))
    for p in peers:
        c = int(10 ** rng.uniform(5, 7))  # 10 万〜1,000 万 sat
        capacity[(new, p)] = capacity[(p, new)] = c
        ends += [new, p]
neighbors = {}
for u, v in capacity:
    neighbors.setdefault(u, []).append(v)


def find_path(src, dst, amount, excluded):
    """容量だけを見て、ホップ数が最小の経路を探す（残高は送る側に見えない）"""
    prev, queue = {src: None}, deque([src])
    while queue:
        u = queue.popleft()
        if u == dst:
            path = []
            while prev[u] is not None:
                path.append((prev[u], u))
                u = prev[u]
            return path[::-1]
        for v in neighbors[u]:
            if v not in prev and (u, v) not in excluded and capacity[(u, v)] >= amount:
                prev[v] = u
                queue.append(v)
    return None


def pay(src, dst, amount, parts, balance):
    """amount を parts 個に分けて送る。1 つでも届かなければ支払い全体が失敗"""
    excluded = set()
    for _ in range(parts):
        part = amount // parts
        for _ in range(MAX_ATTEMPTS):
            path = find_path(src, dst, part, excluded)
            if path is None:
                return False
            short = next((hop for hop in path if balance[hop] < part), None)
            if short is None:
                for hop in path:  # HTLC が経路上の残高を押さえる
                    balance[hop] -= part
                break
            excluded.add(short)  # 失敗した区間を次の試行から外す
        else:
            return False
    return True


results, bound = {k: [] for k in PARTS}, []
for amount in AMOUNTS:
    ok, possible = {k: 0 for k in PARTS}, 0
    for _ in range(TRIALS):
        balance = {}
        for (u, v), c in capacity.items():
            if u < v:  # 容量の内訳は一様分布で割り当てる
                balance[(u, v)] = rng.randint(0, c)
                balance[(v, u)] = c - balance[(u, v)]
        src, dst = rng.sample(range(N_NODES), 2)
        # 送り手の手元の残高と、受取人の受け取りの余地の小さい方が上限
        out_sum = sum(balance[(src, v)] for v in neighbors[src])
        in_sum = sum(balance[(v, dst)] for v in neighbors[dst])
        possible += min(out_sum, in_sum) >= amount
        for k in PARTS:
            ok[k] += pay(src, dst, amount, k, dict(balance))
    for k in PARTS:
        results[k].append(ok[k] / TRIALS)
    bound.append(possible / TRIALS)

print("amount_sat  " + "  ".join(f"parts={k}" for k in PARTS) + "  endpoint_bound")
for i, amount in enumerate(AMOUNTS):
    row = "  ".join(f"{results[k][i]:>7.1%}" for k in PARTS)
    print(f"{amount:>10,}  {row}  {bound[i]:>14.1%}")

out = pathlib.Path(__file__).with_name("result.json")
out.write_text(json.dumps({"amounts": AMOUNTS, "success": results, "bound": bound}, indent=1))
