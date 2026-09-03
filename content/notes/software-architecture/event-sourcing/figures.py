"""Event Sourcing - 出来事の並びを一次記録にする の図を生成する。

再生成:
    uv run --with matplotlib --with numpy python content/notes/software-architecture/event-sourcing/figures.py
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


# --- 図1: ストリームの長さと、現在の状態を復元するために再生するイベント数 ---
#
# 間隔 i ごとにスナップショットを取ると、直近のスナップショットは version
# floor(n / i) * i の時点にある。そこから読むイベント数は n mod i で、
# 長さ n がいくら伸びても i を超えない。スナップショットが無ければ n 件全部。
n = np.arange(0, 2001)
fig, ax = plt.subplots(figsize=(7, 4))

ax.plot(n, n, color=COLOR_RED, linewidth=1.8, label="No snapshot")
ax.plot(n, n % 500, color=COLOR_GREEN, linewidth=1.2,
        label="Snapshot every 500 events")
ax.plot(n, n % 100, color=COLOR_BLUE, linewidth=1.2,
        label="Snapshot every 100 events")

ax.text(2010, 500, "at most 500", color=COLOR_GREEN, fontsize=9, va="center")
ax.text(2010, 100, "at most 100", color=COLOR_BLUE, fontsize=9, va="center")

ax.set_xlim(0, 2000)
ax.set_ylim(0, 2100)
ax.set_xlabel("Events in the stream")
ax.set_ylabel("Events replayed\nto restore the current state")
ax.legend(loc="upper left", frameon=False, fontsize=9)
save("event-sourcing_replay_cost.svg")
