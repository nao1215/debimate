"""Hash Function ノートの図を生成する。

再生成:
    uv run --with matplotlib --with numpy python content/notes/blockchain-systems/hash-function/figures.py
"""

import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

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


# --- 図1: 出力のビット数 n と、総当たりに必要な試行回数 ---
# 原像・第二原像は 2^n 回、衝突は 2^(n/2) 回。本文の表と同じ式である。
n = np.arange(64, 513)

fig, ax = plt.subplots()
ax.plot(n, 2.0 ** n, color=COLOR_BLUE, linewidth=1.8, label="Preimage / second preimage: 2^n")
ax.plot(n, 2.0 ** (n / 2), color=COLOR_RED, linewidth=1.8, label="Collision: 2^(n/2)")
ax.set_yscale("log", base=2)

# SHA-256 (n = 256) の 2 点。本文の表の右列に当たる
ax.axvline(256, color=COLOR_GRAY, linestyle="--", linewidth=1)
ax.text(262, 2.0 ** 430, "SHA-256 (n = 256)", color=COLOR_GRAY, fontsize=9, ha="left", va="top")
for exp, color in ((256, COLOR_BLUE), (128, COLOR_RED)):
    ax.plot([256], [2.0 ** exp], marker="o", markersize=6, color=color)
    ax.annotate(
        f"2^{exp}",
        xy=(256, 2.0 ** exp),
        xytext=(268, 2.0 ** (exp - 40)),
        color=color,
        fontsize=9,
        va="center",
        arrowprops={"arrowstyle": "-", "color": color, "linewidth": 0.8},
    )

# SHA-1 (n = 160) の衝突は、総当たりの 2^80 回より少ない計算で見付かった
ax.plot([160], [2.0 ** 80], marker="o", markersize=6, color=COLOR_GREEN)
ax.annotate(
    "SHA-1 (n = 160): 2^80 by brute force,\nbut a collision was found\nwith far fewer trials",
    xy=(160, 2.0 ** 76),
    xytext=(278, 2.0 ** 40),
    color=COLOR_GREEN,
    fontsize=9,
    ha="left",
    va="center",
    arrowprops={"arrowstyle": "->", "color": COLOR_GREEN, "linewidth": 1.0},
)

exps = (0, 128, 256, 384, 512)
ax.set_yticks([2.0 ** e for e in exps])
ax.set_yticklabels([f"2^{e}" for e in exps])
ax.set_ylim(2.0 ** 0, 2.0 ** 600)
ax.set_xlim(64, 512)
ax.set_xticks([64, 128, 160, 256, 384, 512])
ax.set_xlabel("Output length n (bits)")
ax.set_ylabel("Trials needed by brute force")
ax.legend(loc="upper left", fontsize=9)

save("hash_function_attack_cost.svg")
