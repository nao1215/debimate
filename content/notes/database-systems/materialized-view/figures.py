"""Materialized View ノートの図を生成する。

再生成:
    uv run --with matplotlib python content/notes/database-systems/materialized-view/figures.py

数値は lab/output.txt の (c-1)・(c-2) の実測値（psql の \\timing）。
読み手の開始時刻は、lab/run.sh が出力した「refresh の開始から約 N ms 後」の値
（docker exec の起動時間を含む概算）。
"""

import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

COLOR_BLUE = "#7aa6c2"
COLOR_RED = "#e15759"
COLOR_GRAY = "#666666"
COLOR_TEXT = "#1f1f1f"

plt.rcParams.update({
    "font.size": 11,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "svg.hashsalt": "materialized-view",
    "savefig.bbox": "tight",
    "savefig.dpi": 144,
})

OUT = pathlib.Path(__file__).parent / "images"
OUT.mkdir(exist_ok=True)

# (label, refresh duration [s], reader start [s], reader duration [s])
RUNS = [
    ("REFRESH", 2.961600, 0.154, 2.824188),
    ("REFRESH CONCURRENTLY", 2.663952, 0.154, 0.001077),
]


def refresh_timeline() -> None:
    fig, axes = plt.subplots(2, 1, figsize=(6.5, 3.6), sharex=True)
    for ax, (label, refresh, start, reader) in zip(axes, RUNS):
        ax.barh(1, refresh, left=0, height=0.5, color=COLOR_GRAY, alpha=0.35,
                edgecolor=COLOR_GRAY)
        ax.text(0.03, 1, f"{label}  {refresh * 1000:.0f} ms", va="center",
                fontsize=10, color=COLOR_TEXT)
        if reader > 0.01:
            ax.barh(0, reader, left=start, height=0.5, color=COLOR_RED,
                    alpha=0.8, edgecolor=COLOR_RED, hatch="//")
            ax.text(start + reader + 0.04, 0,
                    f"SELECT waits {reader * 1000:.0f} ms", va="center",
                    fontsize=10, color=COLOR_TEXT)
        else:
            ax.plot([start], [0], marker="o", color=COLOR_BLUE,
                    markersize=8)
            ax.text(start + 0.06, 0,
                    f"SELECT returns in {reader * 1000:.1f} ms (old rows)",
                    va="center", fontsize=10, color=COLOR_TEXT)
        ax.set_yticks([0, 1], ["reader", "refresher"])
        ax.set_ylim(-0.6, 1.6)
        ax.set_xlim(0, 4.2)
        ax.grid(axis="x", alpha=0.3, linewidth=0.5)
    axes[-1].set_xlabel("seconds since refresh started")
    fig.tight_layout()
    path = OUT / "refresh_timeline.svg"
    fig.savefig(path)
    plt.close(fig)
    print(f"wrote {path}")


if __name__ == "__main__":
    refresh_timeline()
