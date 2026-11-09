"""Generate the figures of the circuit breaker note from lab/sim.py."""

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "lab"))
from sim import OUTAGE, POOL, run  # noqa: E402

INK, SUB, ACCENT, RED = "#1f1f1f", "#666666", "#7aa6c2", "#e15759"
plt.rcParams.update({
    "font.size": 10, "axes.edgecolor": SUB, "axes.labelcolor": INK,
    "xtick.color": INK, "ytick.color": INK, "text.color": INK,
    "svg.fonttype": "path", "svg.hashsalt": "circuit-breaker",
    "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
})


def outage_figure():
    none, cb = run(), run(use_breaker=True)
    for st in (none, cb):
        st["b_rate"] = [100 * ok / max(ok + ng, 1)
                        for ok, ng in zip(st["b_ok"], st["b_rejected"])]
    fig, axes = plt.subplots(3, 1, figsize=(7.2, 6.4), sharex=True)
    t_busy = [i / 10 for i in range(len(none["busy"]))]
    t_sec = [i + 0.5 for i in range(60)]
    panels = [
        (t_busy, "busy", f"Busy threads (pool = {POOL})", (0, POOL * 1.15)),
        (t_sec, "b_rate", "Local requests B\nserved (%)", (0, 105)),
        (t_sec, "down_calls", "Calls reaching\ndownstream / s", (0, 70)),
    ]
    for ax, (t, key, label, ylim) in zip(axes, panels):
        ax.axvspan(OUTAGE[0] / 1000, OUTAGE[1] / 1000, color="#f2f2f2", zorder=0)
        ax.step(t, none[key], where="mid", color=RED, lw=1.6, label="no breaker")
        ax.step(t, cb[key], where="mid", color=ACCENT, lw=1.6, ls="--",
                label="with breaker")
        ax.set_ylabel(label)
        ax.set_ylim(*ylim)
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].text(25, POOL * 0.5, "downstream silent (10 s - 40 s)", ha="center",
                 color=SUB, fontsize=9)
    axes[0].legend(loc="upper right", frameon=False, fontsize=9,
                   bbox_to_anchor=(1.0, 0.92))
    axes[-1].set_xlabel("Time (s)")
    axes[-1].set_xlim(0, 60)
    fig.tight_layout()
    fig.savefig(HERE / "images" / "outage_simulation.svg")


if __name__ == "__main__":
    outage_figure()
