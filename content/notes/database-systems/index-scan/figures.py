"""Index Scan ノートの図を生成する。

再生成:
    uv run --with matplotlib --with numpy python content/notes/database-systems/index-scan/figures.py
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


# --- 図1: 選択性と、読むページ枚数の逆転 ---
# 本文は具体的な枚数を持たないので、目盛りを置かない概念図にする。
#   全走査          : 選択性によらず表の全ページ (水平)
#   Index Scan      : 索引のページ + 一致した行が載る表のページ (右上がり)
#                     散らばっているほど 1 行あたりのページが増えるので傾きが立つ
# 縦軸の 1.0 が「表の全ページ」に当たる任意単位である。
s = np.linspace(0.0, 1.0, 200)
seq = np.ones_like(s)
index_pages = 0.05  # 木を降りる分。選択性によらずほぼ一定
scattered = index_pages + 3.0 * s   # 一致した行がページに散っている場合
clustered = index_pages + 1.05 * s   # 表の並びとキーの順序が揃っている場合

fig, ax = plt.subplots()
ax.plot(s, seq, color=COLOR_RED, linewidth=1.8, label="Sequential scan (whole table)")
ax.plot(s, scattered, color=COLOR_BLUE, linewidth=1.8, label="Index scan (rows scattered)")
ax.plot(s, clustered, color=COLOR_GREEN, linewidth=1.8, label="Index scan (rows clustered)")

for line, color, dx in ((scattered, COLOR_BLUE, 0.04), (clustered, COLOR_GREEN, -0.30)):
    i = int(np.argmin(np.abs(line - seq)))
    ax.plot([s[i]], [seq[i]], marker="o", markersize=7, color=color, zorder=3)
    ax.annotate(
        "crossover",
        xy=(s[i], seq[i]),
        xytext=(s[i] + dx, 1.45),
        color=color,
        fontsize=9,
        arrowprops={"arrowstyle": "-", "color": color, "linewidth": 0.8},
    )

ax.set_xlim(0, 1)
ax.set_ylim(0, 2.2)
ax.set_xticks([])
ax.set_yticks([])
ax.grid(False)
ax.set_xlabel("Selectivity: fraction of rows matched  →")
ax.set_ylabel("Pages read  →")
ax.text(
    0.99, 0.02, "Conceptual: axes have no scale",
    transform=ax.transAxes, ha="right", va="bottom", color=COLOR_GRAY, fontsize=9,
)
ax.legend(loc="upper left", fontsize=9)
save("index_scan_crossover.svg")
