"""Timelock Encryption - 将来の条件が成立するまで復号できなくする の図を生成する。

再生成:
    uv run --with matplotlib --with numpy python content/notes/security/timelock-encryption/figures.py

図2 は lab/squaring_time_output.txt を読むだけで、計測はしない（計測は lab/README.txt）。
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


# --- 図1: 2 乗の回数 t に到達する時刻が、速度と開始時刻で動く（概念図） ---
#
# 目盛りは持たせない。横軸は「作成者が想定した秒数 T」を 1、縦軸は「puzzle が
# 要求する 2 乗の回数 t」を 1 とした相対量で、傾きの比も実測値ではない。
fig, ax = plt.subplots(figsize=(7, 4))

series = [
    (0.00, 1.00, COLOR_BLUE, "Assumed speed, starts at publication"),
    (0.00, 1.85, COLOR_RED, "Faster hardware"),
    (0.42, 1.00, COLOR_GREEN, "Later start, assumed speed"),
]
for start, speed, color, label in series:
    finish = start + 1.0 / speed
    x = np.linspace(start, finish, 200)
    ax.plot(x, (x - start) * speed, color=color, linewidth=1.8, label=label)
    ax.plot([finish], [1.0], marker="o", markersize=6, color=color)
    ax.plot([finish, finish], [0, 1.0], color=color, linestyle=":", linewidth=1)

ax.axhline(1.0, color=COLOR_GRAY, linestyle="--", linewidth=1)
ax.text(1.72, 1.03, "t squarings done", color=COLOR_GRAY, fontsize=9)
ax.text(0.58, 0.14, "unlocks\nearlier", color=COLOR_RED, fontsize=9, ha="left")
ax.text(1.46, 0.14, "unlocks\nlater", color=COLOR_GREEN, fontsize=9, ha="left")
ax.text(1.20, 0.62, "Conceptual figure: the axes carry no absolute scale",
        color=COLOR_GRAY, fontsize=9)

ax.set_xlim(0, 2.0)
ax.set_ylim(0, 1.25)
ax.set_xticks([0, 1.0])
ax.set_xticklabels(["publication", "T"])
ax.set_yticks([0, 1.0])
ax.set_yticklabels(["0", "t"])
ax.set_xlabel("Elapsed time (T = the duration assumed when the puzzle was made)")
ax.set_ylabel("Squarings done\n(t = the count required)")
ax.legend(loc="upper left", frameon=False, fontsize=9)
save("timelock_puzzle_unlock_time.svg")


# --- 図2: 2 乗の回数と時間の実測、ワーカー数を増やした時の比較 ---
#
# lab/squaring_time_output.txt（lab/squaring_time.py の実測結果）を読んで描く。
def measured_figure() -> None:
    import re

    ink, sub, accent, red = "#1f1f1f", "#666666", "#7aa6c2", "#e15759"
    text = (pathlib.Path(__file__).parent / "lab" / "squaring_time_output.txt").read_text()
    sweep = [(int(t.replace(",", "")), float(s)) for t, s in
             re.findall(r"t=\s*([\d,]+)\s+([\d.]+) s", text)]
    par = [(int(w), float(c), float(i)) for w, c, i in re.findall(
        r"workers=\s*(\d+)\s+chain: first done\s+([\d.]+) s.*independent squarings:\s+([\d.]+) s",
        text)]
    rc = {
        "font.size": 11, "axes.edgecolor": sub, "axes.labelcolor": ink,
        "xtick.color": ink, "ytick.color": ink, "text.color": ink,
        "axes.grid": True, "grid.alpha": 0.3, "grid.linewidth": 0.6,
        "svg.fonttype": "path", "svg.hashsalt": "timelock-measured",
        "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
    }
    with plt.rc_context(rc):
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.2, 4.0))
        ts = np.array([t for t, _ in sweep], dtype=float)
        secs = np.array([s for _, s in sweep])
        slope = (ts @ secs) / (ts @ ts)  # 原点を通る直線の傾き
        ax1.plot([0, ts.max() / 1e3], [0, ts.max() * slope], color=sub, lw=1.4, ls="--",
                 label=f"fit: {1 / slope / 1e3:.0f}k squarings/s")
        ax1.plot(ts / 1e3, secs, "o", color=accent, ms=8, label="measured")
        ax1.set_xlabel("Squarings t (thousands)")
        ax1.set_ylabel("Time on one core (s)")
        ax1.set_xlim(0, ts.max() / 1e3 * 1.05)
        ax1.set_ylim(0, secs.max() * 1.15)
        ax1.legend(loc="upper left", frameon=False, fontsize=10)

        ws = [w for w, _, _ in par]
        ax2.plot(ws, [c for _, c, _ in par], "o-", color=red, lw=2.4, ms=7,
                 label="one chain of\n200k squarings")
        ax2.plot(ws, [i for _, _, i in par], "s--", color=accent, lw=2.4, ms=7,
                 label="200k independent\nsquarings split")
        ax2.set_xscale("log", base=2)
        ax2.set_xticks(ws, [str(w) for w in ws])
        ax2.minorticks_off()
        ax2.set_xlabel("Worker processes (cores)")
        ax2.set_ylabel("Wall time (s)")
        ax2.set_ylim(0, max(c for _, c, i in par) * 1.4)
        ax2.legend(loc="upper right", frameon=False, fontsize=10)
        for ax in (ax1, ax2):
            ax.spines[["top", "right"]].set_visible(False)
        fig.tight_layout()
        fig.savefig(OUT / "timelock_squaring_measured.svg", metadata={"Date": None})
        plt.close(fig)
        print(f"wrote {OUT / 'timelock_squaring_measured.svg'}")


measured_figure()
