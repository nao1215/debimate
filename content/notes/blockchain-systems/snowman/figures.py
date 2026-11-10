"""Generate the figures of the Snowman note.

The concept figure is hand-written SVG (standard library only). The two graphs
use matplotlib and the simulation in lab/snow_sim.py (fixed seeds).
"""

import random
import sys

sys.dont_write_bytecode = True  # keep the Page Bundle free of __pycache__
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
IMAGES = HERE / "images"
INK, SUB, FILL = "#1f1f1f", "#666666", "#f2f2f2"
BLUE, BLUE_PALE = "#7aa6c2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
GREEN, GREEN_PALE = "#8fae86", "#e9f1e6"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"


def concept_figure():
    """Left: every node talks to every node. Right: one node asks a few, again and again."""
    import math

    w, h = 960, 540
    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img"><title>'
        f'{escape("全員と通信する BFT と、少数への問い合わせを繰り返す Snowman")}</title>',
        f'<style>text{{font-family:{FONT};fill:{INK}}} .sub{{fill:{SUB}}}</style>',
        f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
    ]

    def text(x, y, s, size=26, anchor="middle", cls=""):
        c = f' class="{cls}"' if cls else ""
        p.append(f'<text x="{x}" y="{y}" font-size="{size}" '
                 f'text-anchor="{anchor}"{c}>{escape(s)}</text>')

    def line(x1, y1, x2, y2, color=SUB, width=1.5):
        p.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                 f'stroke="{color}" stroke-width="{width}"/>')

    def node(x, y, r, fill, stroke, width=2):
        p.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{fill}" '
                 f'stroke="{stroke}" stroke-width="{width}"/>')

    # Left: classical BFT, all-to-all among 8 voters.
    text(210, 52, "PBFT・CometBFT", 28)
    text(210, 90, "全員が全員に送る", 24, cls="sub")
    cx, cy, r = 210, 290, 150
    pts = [(cx + r * math.cos(2 * math.pi * i / 8 - math.pi / 2),
            cy + r * math.sin(2 * math.pi * i / 8 - math.pi / 2)) for i in range(8)]
    for i in range(8):
        for j in range(i + 1, 8):
            line(*pts[i], *pts[j])
    for x, y in pts:
        node(x, y, 22, OCHRE_PALE, OCHRE, 2.5)
    text(210, 500, "1 段階で約 n² 通", 24, cls="sub")

    p.append(f'<line x1="425" y1="30" x2="425" y2="510" stroke="{SUB}" '
             'stroke-width="1" stroke-dasharray="4 4"/>')

    # Right: Snowman, one querier samples k of many nodes.
    text(690, 52, "Snowman", 28)
    text(690, 90, "無作為に選んだ k 個に聞き、繰り返す", 24, cls="sub")
    rng = random.Random(7)
    field = []
    for row in range(5):
        for col in range(9):
            x = 470 + col * 55 + rng.uniform(-10, 10)
            y = 135 + row * 62 + rng.uniform(-10, 10)
            if abs(x - 690) < 60 and abs(y - 260) < 50:
                continue  # leave room for the querier
            field.append((x, y))
    sampled = [3, 9, 15, 24, 30, 36]
    qx, qy = 690, 260
    for i in sampled:
        line(qx, qy, *field[i], INK, 2.5)
    for i, (x, y) in enumerate(field):
        if i in sampled:
            fill, stroke = (OCHRE_PALE, OCHRE) if i == 30 else (BLUE_PALE, BLUE)
            node(x, y, 14, fill, stroke, 3)
        else:
            node(x, y, 11, FILL, SUB, 1.5)
    node(qx, qy, 28, BLUE_PALE, BLUE, 4)

    # Consecutive successful polls, then accept.
    text(470, 478, "α 以上が連続", 24, "start")
    for i in range(6):
        p.append(f'<rect x="{620 + i * 40}" y="452" width="32" height="34" rx="4" '
                 f'fill="{GREEN_PALE}" stroke="{GREEN}" stroke-width="2.5"/>')
    p.append(f'<line x1="862" y1="469" x2="880" y2="469" stroke="{INK}" stroke-width="3"/>')
    p.append(f'<polygon points="892,469 878,461 878,477" fill="{INK}"/>')
    text(922, 478, "確定", 24)
    text(740, 520, "β 回", 24, cls="sub")
    IMAGES.mkdir(exist_ok=True)
    (IMAGES / "snowman_concept.svg").write_text("\n".join(p + ["</svg>"]) + "\n")


def setup_matplotlib():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({
        "font.size": 10, "axes.edgecolor": SUB, "axes.labelcolor": INK,
        "xtick.color": INK, "ytick.color": INK, "text.color": INK,
        "svg.fonttype": "path", "svg.hashsalt": "snowman",
        "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
    })
    return plt


def slush_figure(plt):
    sys.path.insert(0, str(HERE / "lab"))
    from snow_sim import slush

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.4), sharey=True)
    panels = [(0.0, "No Byzantine nodes", BLUE), (0.2, "20% Byzantine (keep balance)", OCHRE)]
    for ax, (byz, title, color) in zip(axes, panels):
        for seed in range(1, 6):
            trace = slush(500, 20, 15, 60, byz=byz, seed=seed)
            ax.plot(range(len(trace)), trace, color=color, lw=1.6)
        ax.set_title(title, fontsize=10)
        ax.set_xlabel("Round")
        ax.set_ylim(-0.03, 1.03)
        ax.axhline(0.5, color=SUB, lw=0.8, ls=":")
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].set_ylabel("Share of correct nodes\npreferring blue")
    fig.tight_layout()
    fig.savefig(IMAGES / "snowman_slush.svg", metadata={"Date": None})


def messages_figure(plt):
    sys.path.insert(0, str(HERE / "lab"))
    from snow_sim import pbft_messages, sweep

    ns = [50, 100, 200, 500, 1000, 2000, 5000]
    snow = [sweep(n, 0.0, 20, 15, 20, "agree", trials=20)["msgs_per_node"] * n for n in ns]
    split = [sweep(n, 0.0, 20, 15, 20, "split", trials=20)["msgs_per_node"] * n for n in ns]
    pbft = [pbft_messages(n) for n in ns]
    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    ax.plot(ns, pbft, color=OCHRE, lw=2.0, marker="o", ls="--",
            label="PBFT normal case (all-to-all)")
    ax.plot(ns, snow, color=BLUE, lw=2.0, marker="o",
            label="Snowball, all prefer one value")
    ax.plot(ns, split, color=BLUE, lw=1.5, marker="s", ls=":",
            label="Snowball, start split 50/50")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Number of nodes n")
    ax.set_ylabel("Messages for one decision")
    ax.legend(frameon=False, loc="upper left")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(IMAGES / "snowman_messages.svg", metadata={"Date": None})


def poll_probability_figure(plt):
    """Chance that one poll succeeds, and that beta polls succeed in a row.

    Exact binomial values for k=20, alpha=15, beta=20, when Byzantine nodes
    always answer the other color (section 1 of lab/output.txt).
    """
    from math import comb

    k, alpha, beta = 20, 15, 20
    shares = [i / 200 for i in range(0, 71)]

    def one(f):
        q = 1 - f
        return sum(comb(k, i) * q**i * f ** (k - i) for i in range(alpha, k + 1))

    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    ax.plot([100 * f for f in shares], [one(f) for f in shares], color=BLUE, lw=2.0,
            label="one poll succeeds (15 of 20 agree)")
    ax.plot([100 * f for f in shares], [one(f) ** beta for f in shares], color=OCHRE,
            lw=2.0, ls="--", label="20 polls succeed in a row")
    for f in (0.2, 0.25):
        ax.plot([100 * f], [one(f)], "o", color=BLUE)
        ax.annotate(f"{one(f):.2f}", (100 * f, one(f)), textcoords="offset points",
                    xytext=(6, 4), fontsize=9)
    ax.axvline(25, color=SUB, lw=0.8, ls=":")
    ax.set_yscale("log")
    ax.set_ylim(1e-9, 2)
    ax.set_xlabel("Byzantine share of nodes (%)")
    ax.set_ylabel("Probability")
    ax.legend(frameon=False, loc="lower left")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(IMAGES / "snowman_poll_probability.svg", metadata={"Date": None})


def beta_sweep_figure(plt):
    """Splits and unfinished runs out of 100, from section 2 of lab/output.txt."""
    rows = {}
    section = None
    for line in (HERE / "lab" / "output.txt").read_text().splitlines():
        if line.startswith("=="):
            section = line.split(".")[0].strip("= ")
            continue
        parts = line.split()
        if section == "2" and parts and parts[0][0].isdigit():
            byz, beta = float(parts[0]), int(parts[1])
            rows.setdefault(byz, []).append((beta, int(parts[3]), int(parts[4])))

    styles = {0.0: (BLUE, "-", "o"), 0.05: (BLUE, ":", "s"),
              0.1: (OCHRE, "-", "o"), 0.2: (OCHRE, "--", "s")}
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.4), sharey=True)
    for byz, pts in rows.items():
        color, ls, marker = styles[byz]
        betas = [b for b, _, _ in pts]
        label = f"{int(byz * 100)}% Byzantine"
        axes[0].plot(betas, [s for _, s, _ in pts], color=color, ls=ls, marker=marker,
                     lw=1.6, label=label)
        axes[1].plot(betas, [u for _, _, u in pts], color=color, ls=ls, marker=marker,
                     lw=1.6, label=label)
    axes[0].set_title("Runs where correct nodes decided both colors", fontsize=10)
    axes[1].set_title("Runs where some node never decided", fontsize=10)
    axes[0].set_ylabel("Runs out of 100")
    for ax in axes:
        ax.set_xscale("log")
        ax.set_xticks([1, 2, 4, 8, 20], ["1", "2", "4", "8", "20"])
        ax.set_xlabel("beta")
        ax.set_ylim(-4, 104)
        ax.spines[["top", "right"]].set_visible(False)
    axes[1].legend(frameon=False, loc="center right", fontsize=9)
    fig.tight_layout()
    fig.savefig(IMAGES / "snowman_beta_sweep.svg", metadata={"Date": None})


if __name__ == "__main__":
    concept_figure()
    plt = setup_matplotlib()
    slush_figure(plt)
    messages_figure(plt)
    poll_probability_figure(plt)
    beta_sweep_figure(plt)
