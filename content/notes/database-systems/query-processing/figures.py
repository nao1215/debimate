"""Query Processing ノートの図を生成する。

再生成:
    uv run --with matplotlib --with numpy python content/notes/database-systems/query-processing/figures.py
"""

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


# --- 図1: 候補ごとの見積もりコスト ---
# 本文が挙げている 3 候補の値をそのまま並べる。安い順に下から積む。
plans = [
    ("Plan 3: sort both, merge join", 51000, COLOR_GRAY),
    ("Plan 1: seq scan orders, hash join", 12300, COLOR_GRAY),
    ("Plan 2: filter users, index lookup", 480, COLOR_BLUE),
]
labels = [name for name, _, _ in plans]
costs = [cost for _, cost, _ in plans]
colors = [color for _, _, color in plans]

fig, ax = plt.subplots(figsize=(6.5, 3.2))
for i, (label, cost, color) in enumerate(plans):
    chosen = color == COLOR_BLUE
    ax.barh(i, cost, color=color, height=0.6, alpha=1.0 if chosen else 0.5)
    text = f"{cost:,} (chosen)" if chosen else f"{cost:,}"
    ax.text(cost + 900, i, text, va="center", fontsize=10,
            color=COLOR_BLUE if chosen else COLOR_GRAY)
ax.set_yticks(range(len(plans)))
ax.set_yticklabels(labels)
ax.set_xlim(0, 60000)
ax.set_xlabel("Estimated cost")
ax.xaxis.grid(True)
ax.yaxis.grid(False)
save("query_processing_plan_cost.svg")

# --- 図2: 独立と見なした選択性の掛け合わせ ---
# 本文の例をそのまま置く。country も city も 1% を通し、独立とみなした
# 見積もりは 0.01%、実際は 1% に近い。桁で外すので対数軸にする。
cases = [
    ("country\n(single column)", 0.01, COLOR_GRAY),
    ("city\n(single column)", 0.01, COLOR_GRAY),
    ("country AND city\n(estimated)", 0.0001, COLOR_BLUE),
    ("country AND city\n(actual)", 0.01, COLOR_RED),
]

fig, ax = plt.subplots(figsize=(7.0, 4))
for i, (label, value, color) in enumerate(cases):
    ax.bar(i, value, color=color, width=0.55, alpha=0.5 if color == COLOR_GRAY else 1.0)
    ax.text(i, value * 1.3, f"{value * 100:g}%", ha="center", fontsize=10, color=COLOR_GRAY)
ax.set_yscale("log")
ax.set_ylim(3e-5, 0.1)
ax.set_xlim(-0.6, 3.6)
ax.set_xticks(range(len(cases)))
ax.set_xticklabels([label for label, _, _ in cases], fontsize=9)
ax.set_yticks([1e-4, 1e-3, 1e-2, 1e-1])
ax.set_yticklabels(["0.01%", "0.1%", "1%", "10%"])
ax.set_ylabel("Selectivity: rows passing the condition")
ax.annotate("", xy=(2.5, 0.01), xytext=(2.5, 0.0001),
            arrowprops={"arrowstyle": "<->", "color": COLOR_GRAY, "linewidth": 1})
ax.text(2.55, 0.0009, "2 orders", ha="left", fontsize=9, color=COLOR_GRAY)
ax.xaxis.grid(False)
save("query_processing_selectivity.svg")
