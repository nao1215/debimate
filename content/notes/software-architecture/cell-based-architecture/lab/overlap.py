"""Shuffle Sharding で組の大きさ k と台数 n を変えた時、ポイズンピルを送る顧客の組と
他の顧客の組がどれだけ重なるかを、組み合わせの数から求める。

- 全て重なる : 他の顧客の組が、ポイズンピルを送る顧客の組と同じ（全ての台を失う）
- 一部重なる : 1 台以上 k 台未満を共有する（再試行で残りの台に届けば動く）
- 通常のセル : k 台ずつの固定のセルなら、同じセルの顧客は k/n の割合で全ての台を失う

標準ライブラリだけを使う。
Run: python3 overlap.py
"""

from math import comb


def overlap(n, k):
    total = comb(n, k)
    full = 1 / total
    part = (total - comb(n - k, k) - 1) / total
    return total, full, part


print("[1] 台数と組の大きさを変えた時、組が全て重なる確率")
for n, k in [(8, 2), (16, 4), (100, 5), (2048, 4)]:
    total, full, _ = overlap(n, k)
    print(f"  {n:>5} 台から {k} 台: 組み合わせ {total:>17,} 通り  "
          f"全て重なる {full:.2e}  通常のセルなら {k / n:.2%}")

print("[2] 100 台で k を変えた時")
for k in range(1, 11):
    _, full, part = overlap(100, k)
    print(f"  k={k:>2}  全て重なる {full:.2e}  一部重なる {part:6.2%}  通常のセルなら {k / 100:.0%}")
