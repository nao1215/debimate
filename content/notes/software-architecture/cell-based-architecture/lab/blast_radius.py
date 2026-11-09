"""1 人の毒入り顧客が、他の顧客をどれだけ巻き込むかを数える。

ワーカー 8 台と顧客 1 万人で、通常の cell（2 台ずつ 4 組）と
shuffle sharding（顧客ごとにランダムな 2 台の組）の割り当てを比べる。
毒入り顧客の要求は、届いたワーカーを全て止めるものとする。
標準ライブラリだけを使う。Python 3.14.4 で実行を確認した。
"""

import random
from math import comb

WORKERS = 8
K = 2  # 1 人の顧客が使うワーカーの数
CUSTOMERS = 10_000
rng = random.Random(1)


def classify(shards, poison):
    """毒入り顧客の組と比べて、全滅・一部停止・無傷の人数を返す。"""
    dead = set(shards[poison])
    full = part = 0
    for c, shard in enumerate(shards):
        if c == poison:
            continue
        hit = len(dead & set(shard))
        if hit == K:
            full += 1  # 使えるワーカーが残らない
        elif hit > 0:
            part += 1  # 残りのワーカーへ再試行すれば動く
    return full, part


def show(label, full, part, others=CUSTOMERS - 1):
    print(f"  {label}  全滅 {full / others:6.2%}  "
          f"一部停止 {part / others:6.2%}  無傷 {1 - (full + part) / others:6.2%}")


# 通常の cell: ワーカー 0-1, 2-3, 4-5, 6-7 を 1 つの cell にして顧客を振り分ける
cells = [tuple(range(i, i + K)) for i in range(0, WORKERS, K)]
cell_shards = [cells[rng.randrange(len(cells))] for _ in range(CUSTOMERS)]
# shuffle sharding: 顧客ごとに 8 台から 2 台をランダムに選ぶ
shuffle_shards = [tuple(rng.sample(range(WORKERS), K)) for _ in range(CUSTOMERS)]

print(f"[1] ワーカー {WORKERS} 台、顧客 {CUSTOMERS:,} 人、1 人あたり {K} 台")
show("通常の cell", *classify(cell_shards, poison=0))
show("shuffle    ", *classify(shuffle_shards, poison=0))

print("[2] 理論値")
total = comb(WORKERS, K)
no_overlap = comb(WORKERS - K, K)
print(f"  組み合わせの数 C({WORKERS},{K}) = {total}")
print(f"  通常の cell  全滅 {1 / len(cells):6.2%}")
print(f"  shuffle      全滅 {1 / total:6.2%}  "
      f"一部停止 {(total - no_overlap - 1) / total:6.2%}")

print("[3] 台数と組の大きさを変えた時、毒入り顧客と組が完全に重なる確率")
for n, k in [(8, 2), (16, 4), (100, 5), (2048, 4)]:
    print(f"  {n:>5} 台から {k} 台: 組み合わせ {comb(n, k):>17,} 通り  "
          f"確率 {1 / comb(n, k):.2e}  （通常の cell なら {k / n:.2%}）")
