"""Heartbeat ノートの図を生成する。

再生成:
    uv run --with matplotlib --with numpy python content/notes/distributed-systems/heartbeat/figures.py
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


# --- 図1: ノード数とメッセージの本数 ---
# 本文の表と同じ 3 つのオーダーを、係数を置かずにそのまま描く。
#   中央集約 : 1 周期あたり O(n)。Lease の更新も同じ
#   相互監視 : 1 周期あたり O(n^2)
#   gossip   : 情報 1 件がクラスタ全体へ届くまでで O(n log n) 程度
# n と n log n は線形軸だと n^2 に潰れるので両対数にする。
n = np.arange(2, 1001)

fig, ax = plt.subplots()
ax.loglog(n, n * n, color=COLOR_RED, linewidth=1.8,
          label="Mutual monitoring: O(n^2) per round")
ax.loglog(n, n * np.log2(n), color=COLOR_GREEN, linewidth=1.8,
          label="Gossip: O(n log n) to spread one update")
ax.loglog(n, n, color=COLOR_BLUE, linewidth=1.8,
          label="Central monitoring / lease: O(n) per round")

ax.set_xlabel("Number of nodes (n)")
ax.set_ylabel("Messages")
# 係数を置いていないので、読むのは傾きであって目盛りの値ではない
ax.text(0.99, 0.02, "Coefficients omitted: compare the slopes",
        transform=ax.transAxes, ha="right", va="bottom", color=COLOR_GRAY, fontsize=9)
ax.legend(loc="upper left", fontsize=9)
save("heartbeat_message_scaling.svg")
