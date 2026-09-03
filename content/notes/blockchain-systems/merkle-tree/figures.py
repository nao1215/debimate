"""Merkle Tree - ハッシュ木で包含を証明する の図を生成する。

再生成:
    uv run --with matplotlib --with numpy python content/notes/blockchain-systems/merkle-tree/figures.py
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


def proof_size(n):
    """葉が n 件の時の証明のハッシュの個数 ceil(log2 n)。"""
    ratio = np.log2(np.asarray(n, dtype=float))
    return np.ceil(np.round(ratio, 9))


# --- 図1: 葉の数に対する証明のハッシュの個数 ---
n = np.logspace(np.log10(2), np.log10(4e6), 6000)
plt.plot(n, proof_size(n), color=COLOR_BLUE, linewidth=1.8)

marks = [(4, "4"), (8, "8"), (1024, "1,024"), (1_000_000, "1,000,000")]
for leaves, _ in marks:
    y = float(proof_size(leaves))
    plt.plot([leaves], [y], marker="o", markersize=5, color=COLOR_BLUE)
    plt.annotate(
        f"{y:.0f}",
        xy=(leaves, y),
        xytext=(0, 9),
        textcoords="offset points",
        color=COLOR_GRAY,
        fontsize=10,
        ha="center",
    )

plt.xscale("log")
plt.xlim(2, 1.2e7)
plt.ylim(0, 24)
plt.xticks([leaves for leaves, _ in marks], [label for _, label in marks])
plt.minorticks_off()
plt.xlabel("Number of data items (leaves)")
plt.ylabel("Hashes in the inclusion proof")
save("merkle-tree_proof_size.svg")
