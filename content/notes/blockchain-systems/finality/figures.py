"""Finality ノートの図を生成する。

再生成:
    uv run --with matplotlib --with numpy python content/notes/blockchain-systems/finality/figures.py
"""

import math
import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

COLOR_BLUE = "#7aa6c2"
COLOR_RED = "#e15759"
COLOR_GREEN = "#59a14f"
COLOR_GRAY = "#666666"

plt.rcParams.update({
    "figure.figsize": (6, 4),
    "font.size": 11,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "grid.linewidth": 0.5,
    "savefig.bbox": "tight",
    "savefig.dpi": 144,
})

OUT = pathlib.Path(__file__).parent / "images"
OUT.mkdir(exist_ok=True)


def save(name: str) -> None:
    path = OUT / name
    plt.savefig(path)
    plt.close()
    print(f"wrote {path}")


def attacker_success_probability(q: float, z: int) -> float:
    """Bitcoin 白書 (Nakamoto 2008) の AttackerSuccessProbability を写したもの。

    z ブロック遅れている攻撃者が、正直なマイナーの列に追い付く確率を返す。
    """
    p = 1.0 - q
    lam = z * (q / p)
    total = 1.0
    for k in range(z + 1):
        poisson = math.exp(-lam)
        for i in range(1, k + 1):
            poisson *= lam / i
        total -= poisson * (1 - (q / p) ** (z - k))
    return total


# --- 図1: 後ろに積むブロック数 z と、攻撃の成功確率 ---
z_values = list(range(0, 26))
series = [
    (0.10, COLOR_BLUE),
    (0.30, COLOR_GREEN),
    (0.45, COLOR_RED),
]
for q, color in series:
    probs = [attacker_success_probability(q, z) for z in z_values]
    plt.semilogy(z_values, probs, marker="o", markersize=3, color=color, label=f"q = {q:.2f}")

plt.axhline(0.001, color=COLOR_GRAY, linestyle="--", linewidth=1)
plt.text(0.3, 0.0013, "0.1%", color=COLOR_GRAY, fontsize=9)
plt.xlabel("Blocks stacked after the transaction (z)")
plt.ylabel("Attack success probability")
plt.ylim(1e-8, 2)
plt.legend()
save("finality_success_rate.svg")

# 本文と表の値が式と一致するかを、生成のたびに確かめる
if __name__ == "__main__":
    print("\n--- 本文で使っている値 ---")
    for z in (0, 5, 10):
        print(f"q=0.10 z={z}: {attacker_success_probability(0.10, z):.7f}")
    print("\n--- 表: 成功確率が 0.1% を下回る最小の z ---")
    for q in (0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45):
        z = 0
        while attacker_success_probability(q, z) >= 0.001:
            z += 1
        print(f"q={q:.2f}: z={z} (確認数 {z + 1})")
