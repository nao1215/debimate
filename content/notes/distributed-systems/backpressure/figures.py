"""Backpressure ノートの図を生成する。

実行: uv run --with matplotlib python figures.py
lab/results.json（lab/queue_experiment.py の出力）を読み、images/ に SVG を書く。
"""
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).parent
TEXT = "#1f1f1f"
SUB = "#666666"
STYLE = {
    "unbounded": dict(color="#e15759", linestyle="-", label="unbounded"),
    "block": dict(color="#7aa6c2", linestyle="-", label="bounded: block"),
    "reject": dict(color=SUB, linestyle="--", label="bounded: reject"),
}

plt.rcParams.update({
    "font.size": 11, "axes.edgecolor": SUB, "axes.labelcolor": TEXT,
    "xtick.color": SUB, "ytick.color": SUB, "svg.fonttype": "path",
    "axes.spines.top": False, "axes.spines.right": False,
})


def queue_experiment():
    data = json.loads((ROOT / "lab" / "results.json").read_text())
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 3.8))
    for mode, st in STYLE.items():
        t, q = zip(*data[mode]["samples"])
        ax1.plot(t, q, linewidth=2, **st)
        t, w = zip(*data[mode]["waits"])
        ax2.plot(t, w, linewidth=2, **st)
    ax1.set_title("Queue length", color=TEXT, loc="left")
    ax1.set_xlabel("elapsed time (s)")
    ax1.set_ylabel("items in queue")
    ax2.set_title("Waiting time in queue", color=TEXT, loc="left")
    ax2.set_xlabel("elapsed time when dequeued (s)")
    ax2.set_ylabel("wait (s)")
    for ax in (ax1, ax2):
        ax.grid(axis="y", color="#eeeeee")
        ax.set_xlim(0, 4)
        ax.set_ylim(bottom=0)
    ax1.legend(frameon=False, loc="upper left", labelcolor=TEXT)
    fig.text(0.01, 0.01, "arrival 200/s, service 100/s, bounded queue maxsize=50",
             color=SUB, fontsize=9)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(ROOT / "images" / "queue_growth.svg", facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    queue_experiment()
