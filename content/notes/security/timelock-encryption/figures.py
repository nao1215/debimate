"""Timelock Encryption - 将来の条件が成立するまで復号できなくする の図を生成する。

再生成:
    uv run --with matplotlib --with numpy python content/notes/security/timelock-encryption/figures.py
"""

import pathlib

import matplotlib
matplotlib.use("Agg")  # 表示せずファイルへ書く
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
    "grid.linestyle": "-",
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


# --- 図1: 2 乗の回数 t に到達する時刻が、速度と開始時刻で動く（概念図） ---
#
# 目盛りは持たせない。横軸は「作成者が想定した秒数 T」を 1、縦軸は「puzzle が
# 要求する 2 乗の回数 t」を 1 とした相対量で、傾きの比も実測値ではない。
fig, ax = plt.subplots(figsize=(7, 4))

series = [
    (0.00, 1.00, COLOR_BLUE, "Assumed speed, starts at publication"),
    (0.00, 1.85, COLOR_RED, "Faster hardware"),
    (0.42, 1.00, COLOR_GREEN, "Later start, assumed speed"),
]
for start, speed, color, label in series:
    finish = start + 1.0 / speed
    x = np.linspace(start, finish, 200)
    ax.plot(x, (x - start) * speed, color=color, linewidth=1.8, label=label)
    ax.plot([finish], [1.0], marker="o", markersize=6, color=color)
    ax.plot([finish, finish], [0, 1.0], color=color, linestyle=":", linewidth=1)

ax.axhline(1.0, color=COLOR_GRAY, linestyle="--", linewidth=1)
ax.text(1.72, 1.03, "t squarings done", color=COLOR_GRAY, fontsize=9)
ax.text(0.58, 0.14, "unlocks\nearlier", color=COLOR_RED, fontsize=9, ha="left")
ax.text(1.46, 0.14, "unlocks\nlater", color=COLOR_GREEN, fontsize=9, ha="left")
ax.text(1.20, 0.62, "Conceptual figure: the axes carry no absolute scale",
        color=COLOR_GRAY, fontsize=9)

ax.set_xlim(0, 2.0)
ax.set_ylim(0, 1.25)
ax.set_xticks([0, 1.0])
ax.set_xticklabels(["publication", "T"])
ax.set_yticks([0, 1.0])
ax.set_yticklabels(["0", "t"])
ax.set_xlabel("Elapsed time (T = the duration assumed when the puzzle was made)")
ax.set_ylabel("Squarings done\n(t = the count required)")
ax.legend(loc="upper left", frameon=False, fontsize=9)
save("timelock_puzzle_unlock_time.svg")
