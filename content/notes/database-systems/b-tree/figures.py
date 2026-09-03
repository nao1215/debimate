"""B-Tree - ページ単位の入出力に合わせた索引の木 の図を生成する。

再生成:
    uv run --with matplotlib --with numpy python content/notes/database-systems/b-tree/figures.py
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


def levels(n, fanout: int):
    """根から葉まで通過するノードの個数 ceil(log(n) / log(f))。"""
    ratio = np.log(np.asarray(n, dtype=float)) / np.log(float(fanout))
    return np.ceil(np.round(ratio, 9))


# --- 図1: 件数に対する段数を、分岐数ごとに描く ---
n = np.logspace(3, 9, 4000)
series = [
    (2, COLOR_RED, "Fanout f = 2 (binary search tree)"),
    (100, COLOR_BLUE, "Fanout f = 100"),
    (500, COLOR_GREEN, "Fanout f = 500"),
]
for fanout, color, label in series:
    plt.plot(n, levels(n, fanout), color=color, linewidth=1.8, label=label)

plt.axvline(1e8, color=COLOR_GRAY, linestyle="--", linewidth=1)
plt.text(1.2e8, 31.5, "100 million keys", color=COLOR_GRAY, fontsize=9)
offsets = {2: 1.4, 100: 1.4, 500: -2.6}
for fanout, color, _ in series:
    y = float(levels(1e8, fanout))
    plt.plot([1e8], [y], marker="o", markersize=5, color=color)
    plt.text(8.0e7, y + offsets[fanout], f"{y:.0f}", color=color, fontsize=10, ha="right")

plt.xscale("log")
plt.ylim(0, 34)
plt.xlabel("Number of keys in the index (n)")
plt.ylabel("Levels from root to leaf")
plt.legend(loc="upper left", frameon=False, fontsize=9)
save("b-tree_levels_by_fanout.svg")


# --- 図2: 分岐数が大きい時、件数を 10 倍にすると段数がいくつ増えるか ---
n2 = np.logspace(5, 12, 4000)
decades = np.logspace(5, 12, 8)
for fanout, color, label in [(100, COLOR_BLUE, "Fanout f = 100"), (500, COLOR_GREEN, "Fanout f = 500")]:
    plt.plot(n2, levels(n2, fanout), color=color, linewidth=1.8, label=label)
    plt.plot(decades, levels(decades, fanout), linestyle="none", marker="o",
             markersize=5, color=color)

plt.xscale("log")
plt.ylim(0, 7)
plt.yticks(range(0, 8))
plt.xlabel("Number of keys in the index (n), one marker per 10x")
plt.ylabel("Levels from root to leaf")
plt.legend(loc="upper left", frameon=False, fontsize=9)
save("b-tree_levels_per_decade.svg")
