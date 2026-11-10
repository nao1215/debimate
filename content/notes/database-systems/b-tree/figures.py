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


# --- 図2: 昇順とランダムな順で挿入した索引の葉ページ（本文の pgstatindex() の出力） ---
# (index, insert order, leaf_pages, avg_leaf_density)
FILL_RUNS = [
    ("seq_ins_k", "ascending", 2733, 90.06),
    ("rnd_ins_k", "random", 3701, 66.58),
]
with plt.rc_context({
    "font.size": 10, "axes.grid": False, "svg.fonttype": "path",
    "svg.hashsalt": "b-tree", "figure.facecolor": "#ffffff",
    "axes.facecolor": "#ffffff", "axes.edgecolor": COLOR_GRAY,
}):
    fig, (left, right) = plt.subplots(1, 2, figsize=(7.2, 3.2))
    labels = [f"{order}\n({name})" for name, order, _, _ in FILL_RUNS]
    colors = [COLOR_BLUE, COLOR_RED]
    for ax, col, title, fmt, top in [
        (left, 2, "Leaf pages", "{:,.0f}", 4300),
        (right, 3, "Average leaf density (%)", "{:.1f}%", 115),
    ]:
        values = [run[col] for run in FILL_RUNS]
        ax.bar([0, 1], values, color=colors, width=0.6)
        for x, v in enumerate(values):
            ax.text(x, v + top * 0.02, fmt.format(v), ha="center", va="bottom",
                    fontsize=10)
        ax.set_xticks([0, 1], labels, fontsize=9.5)
        ax.set_ylim(0, top)
        ax.set_title(title, fontsize=10.5)
    right.axhline(90, color=COLOR_GRAY, linestyle="--", linewidth=1)
    right.text(1.45, 92, "fillfactor 90", ha="right", va="bottom",
               color=COLOR_GRAY, fontsize=9)
    fig.tight_layout()
    path = OUT / "b-tree_insert_order_fill.svg"
    fig.savefig(path, metadata={"Date": None})
    plt.close(fig)
    print(f"wrote {path}")
