"""LSM-Tree - 追記だけで書く索引 の図を生成する。

再生成（実験の結果 lab/results.json を先に作る）:
    python3 content/notes/database-systems/lsm-tree/lab/lsm.py
    uv run --with matplotlib python content/notes/database-systems/lsm-tree/figures.py
"""

import json
import pathlib

import matplotlib
matplotlib.use("Agg")  # 表示せずファイルへ書く
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

COLOR_BLUE = "#7aa6c2"
COLOR_RED = "#e15759"
COLOR_GRAY = "#666666"
COLOR_TEXT = "#1f1f1f"
COLOR_FILL = "#f2f2f2"

plt.rcParams.update({
    "figure.figsize": (6.5, 4),
    "font.size": 11,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "grid.linewidth": 0.5,
    "savefig.bbox": "tight",
    "savefig.dpi": 144,
    "svg.hashsalt": "lsm-tree",
})

HERE = pathlib.Path(__file__).parent
OUT = HERE / "images"
OUT.mkdir(exist_ok=True)
RESULTS = {r["style"]: r for r in json.loads((HERE / "lab" / "results.json").read_text())}


def save(name: str) -> None:
    path = OUT / name
    plt.savefig(path, metadata={"Date": None})
    plt.close()
    print(f"wrote {path}")


# --- 図1: size-tiered と leveled の並び方 ---
def draw_runs(ax, title, rows):
    """rows: (label, [(x0, x1), ...], note). 1 行が 1 つの sorted run かファイル群。"""
    ax.set_title(title, fontsize=12, color=COLOR_TEXT)
    y = len(rows) - 1
    for label, boxes, note in rows:
        for x0, x1 in boxes:
            ax.add_patch(Rectangle((x0, y + 0.15), x1 - x0, 0.7,
                                   facecolor=COLOR_FILL, edgecolor=COLOR_TEXT, linewidth=1))
        ax.text(-0.03, y + 0.5, label, ha="right", va="center", fontsize=10, color=COLOR_TEXT)
        ax.text(1.03, y + 0.5, note, ha="left", va="center", fontsize=9, color=COLOR_GRAY)
        y -= 1
    ax.set_xlim(0, 1)
    ax.set_ylim(-0.2, len(rows))
    ax.set_xticks([0, 1], ["key a", "key z"])
    ax.set_yticks([])
    ax.grid(False)
    for side in ("left", "top", "right"):
        ax.spines[side].set_visible(False)


full = [(0.0, 1.0)]
tiered = [
    ("tier 0", full, "1 MB"), ("tier 0", full, "1 MB"), ("tier 0", full, "1 MB"),
    ("tier 1", full, "4 MB"), ("tier 1", full, "4 MB"),
    ("tier 2", full, "16 MB"),
]
leveled = [
    ("L0", [(0.05, 0.9)], "1 MB"), ("L0", [(0.0, 0.8)], "1 MB"), ("L0", [(0.2, 1.0)], "1 MB"),
    ("L1", [(i / 4, (i + 1) / 4) for i in range(4)], "10 MB total"),
    ("L2", [(i / 10, (i + 1) / 10) for i in range(10)], "100 MB total"),
]
fig, axes = plt.subplots(1, 2, figsize=(7, 3.4))
draw_runs(axes[0], "Size-tiered: 6 sorted runs", tiered)
draw_runs(axes[1], "Leveled: 5 sorted runs", leveled)
fig.subplots_adjust(wspace=0.75)
save("lsm-tree_compaction_shapes.svg")


# --- 図2: 削除を始めた後も、保存している件数が増える ---
fig, ax = plt.subplots()
for style, color, label in (("leveled", COLOR_BLUE, "Leveled"),
                            ("tiered", COLOR_RED, "Size-tiered")):
    t = RESULTS[style]["timeline"]
    ax.plot([e[0] for e in t], [e[1] for e in t], color=color, linewidth=1.8,
            label=f"{label}: entries on disk")
t = RESULTS["leveled"]["timeline"]
ax.plot([e[0] for e in t], [e[3] for e in t], color=COLOR_GRAY, linestyle="--",
        linewidth=1.5, label="Live keys")
ax.axvline(100_000, color=COLOR_GRAY, linestyle=":", linewidth=1)
ax.text(101_500, 56_000, "deletes\nstart", color=COLOR_GRAY, fontsize=9, va="top")
ax.set_xlabel("Operations (put, then delete)")
ax.set_ylabel("Entries")
ax.set_ylim(0, 58_000)
ax.legend(loc="upper left", fontsize=9, frameon=False)
save("lsm-tree_space_timeline.svg")


# --- 図3: compaction を止めると sorted run が増え続ける ---
fig, ax = plt.subplots()
for style, color, ls, label in (("none", COLOR_RED, "-", "No compaction"),
                                ("tiered", COLOR_GRAY, "--", "Size-tiered"),
                                ("leveled", COLOR_BLUE, "-", "Leveled")):
    t = RESULTS[style]["timeline"]
    ax.plot([e[0] for e in t], [e[2] for e in t], color=color, linestyle=ls,
            linewidth=1.8, label=label)
ax.set_xlabel("Operations")
ax.set_ylabel("SSTables on disk")
ax.legend(loc="upper left", fontsize=9, frameon=False)
save("lsm-tree_runs_timeline.svg")
