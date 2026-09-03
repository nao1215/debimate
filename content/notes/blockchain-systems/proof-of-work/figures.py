"""Proof of Work ノートの図を生成する。

再生成:
    uv run --with matplotlib --with numpy python content/notes/blockchain-systems/proof-of-work/figures.py
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


# --- 図1: target の厳しさ k と、合格までの平均試行回数 ---
# target = 2^256 / 2^k とした時、1 回の試行が合格する確率は 2^-k、
# 合格までの平均試行回数は 2^k になる。本文の表の 3 行は k = 1, 32, 76 に当たる。
k = np.arange(0, 81)
trials = 2.0 ** k

fig, ax = plt.subplots()
ax.plot(k, trials, color=COLOR_BLUE, linewidth=1.8)
ax.set_yscale("log", base=2)

# nonce は 4 バイトなので、試せるのは 2^32 通りまで
ax.axhline(2.0 ** 32, color=COLOR_GRAY, linestyle="--", linewidth=1)
ax.text(1, 2.0 ** 33.5, "4-byte nonce space = 2^32", color=COLOR_GRAY, fontsize=9)

# 本文の表の 3 行を、そのまま曲線の上の点として置く
marks = [
    (1, "2 trials (pass rate ~50%)", 14, 2.0 ** 6, "left"),
    (32, "4.3 billion trials", 42, 2.0 ** 38, "left"),
    (76, "2^76 trials", 45, 2.0 ** 76, "right"),
]
for kk, label, tx, ty, ha in marks:
    ax.plot([kk], [2.0 ** kk], marker="o", markersize=6, color=COLOR_RED)
    ax.annotate(
        label,
        xy=(kk, 2.0 ** kk),
        xytext=(tx, ty),
        color=COLOR_RED,
        fontsize=9,
        ha=ha,
        va="center",
        arrowprops={"arrowstyle": "-", "color": COLOR_RED, "linewidth": 0.8},
    )

ticks = [2.0 ** e for e in (0, 16, 32, 48, 64, 80)]
ax.set_yticks(ticks)
ax.set_yticklabels([f"2^{e}" for e in (0, 16, 32, 48, 64, 80)])
ax.set_ylim(2.0 ** -2, 2.0 ** 84)
ax.set_xlim(0, 80)
ax.set_xlabel("How strict the target is (k, where target = 2^256 / 2^k)")
ax.set_ylabel("Average trials until a hash passes")

ax2 = ax.twinx()
ax2.set_yscale("log", base=2)
ax2.set_ylim(ax.get_ylim())
ax2.set_yticks(ticks)
ax2.set_yticklabels(["1"] + [f"2^-{e}" for e in (16, 32, 48, 64, 80)])
ax2.set_ylabel("Probability that one trial passes")
ax2.grid(False)
ax2.spines["top"].set_visible(False)
ax2.spines["right"].set_visible(True)

save("proof_of_work_target_trials.svg")
