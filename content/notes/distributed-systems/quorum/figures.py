"""Generate the cover diagram of the quorum note as a hand-written SVG.

concept_figure() places five nodes on a ring twice. On the left, the write
set (W = 3) and the read set (R = 3) are drawn as bands along the ring;
W + R = 6 > 5, so they always share a node (Node 3, in green). On the right,
W = 2 and R = 2 give W + R = 4 <= 5, and the two sets can miss each other.

availability_figure() plots lab/availability.py: the probability that an
operation needing k of N replicas cannot proceed, against the per-node
failure probability p.

Run: python3 content/notes/distributed-systems/quorum/figures.py
"""

import math
import sys
from html import escape
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "lab"))
from availability import available  # noqa: E402
INK, SUB, ACCENT, RED = "#1f1f1f", "#666666", "#7aa6c2", "#e15759"
FILL, PALE = "#f2f2f2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
GREEN, GREEN_PALE = "#8fae86", "#e9f1e6"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"

RING = 118  # radius of the node ring
STEP = 72  # degrees between nodes


def angle(i):
    """Node i (1..5) clockwise from the top."""
    return math.radians(-90 + (i - 1) * STEP)


def pos(cx, cy, i, r=RING):
    a = angle(i)
    return cx + r * math.cos(a), cy + r * math.sin(a)


def band(cx, cy, first, last, r, width):
    """Closed path of a thick arc with round ends from node first to last."""
    a0, a1 = angle(first), angle(last)
    ro, ri, cap = r + width / 2, r - width / 2, width / 2

    def pt(rad, a):
        return cx + rad * math.cos(a), cy + rad * math.sin(a)

    large = 1 if (a1 - a0) > math.pi else 0
    (ox0, oy0), (ox1, oy1) = pt(ro, a0), pt(ro, a1)
    (ix0, iy0), (ix1, iy1) = pt(ri, a0), pt(ri, a1)
    return (f"M{ox0:.1f},{oy0:.1f} A{ro},{ro} 0 {large} 1 {ox1:.1f},{oy1:.1f} "
            f"A{cap},{cap} 0 0 1 {ix1:.1f},{iy1:.1f} "
            f"A{ri},{ri} 0 {large} 0 {ix0:.1f},{iy0:.1f} "
            f"A{cap},{cap} 0 0 1 {ox0:.1f},{oy0:.1f} Z")


def concept_figure():
    w, h = 960, 540
    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img"><title>'
        f'{escape("W + R が N を超えると書き込みと読み取りの集合が必ず重なる")}</title>',
        f'<style>text{{font-family:{FONT};fill:{INK}}} .sub{{fill:{SUB}}} '
        f'.red{{fill:{RED}}}</style>',
        f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
    ]

    def text(x, y, s, size=24, anchor="middle", weight="normal", cls=""):
        c = f' class="{cls}"' if cls else ""
        p.append(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
                 f'text-anchor="{anchor}"{c}>{escape(s)}</text>')

    panels = [
        # centre x, W range, R range, heading, verdict, verdict is red
        (240, (1, 3), (3, 5), "W = 3、R = 3", "W + R = 6 > 5　必ず重なる", True),
        (720, (1, 2), (3, 4), "W = 2、R = 2", "W + R = 4 ≤ 5　重ならない場合がある", False),
    ]
    cy = 268
    for cx, wr, rr, head, verdict, overlap in panels:
        text(cx, 52, head, 30, weight="normal")
        # Write set on the outer side, read set on the inner side of the ring.
        p.append(f'<path d="{band(cx, cy, *wr, RING + 16, 92)}" fill="{PALE}" '
                 f'stroke="{ACCENT}" stroke-width="4"/>')
        p.append(f'<path d="{band(cx, cy, *rr, RING - 16, 92)}" fill="{OCHRE_PALE}" '
                 f'stroke="{OCHRE}" stroke-width="3" stroke-dasharray="9 6"/>')
        for i in range(1, 6):
            x, y = pos(cx, cy, i)
            both = wr[0] <= i <= wr[1] and rr[0] <= i <= rr[1]
            # The shared node holds the latest value: success colour.
            fill = GREEN if both else "#ffffff"
            p.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="27" fill="{fill}" '
                     f'stroke="{INK}" stroke-width="2.5"/>')
            p.append(f'<text x="{x:.1f}" y="{y + 9:.1f}" font-size="26" text-anchor="middle" '
                     f'font-weight="normal" style="fill:{INK}">{i}</text>')
        # Labels next to the bands.
        wx, wy = pos(cx, cy, 1.5, RING + 92)
        text(wx + 6, wy, "W", 28, "start", "normal")
        rx_, ry_ = pos(cx, cy, 4, RING + 68)
        text(rx_ - 4, ry_ + 10, "R", 28, "end", "normal")
        # Red only for the counterexample that can miss the latest value.
        text(cx, 476, verdict, 26, weight="normal", cls="" if overlap else "red")

    p.append(f'<line x1="480" y1="30" x2="480" y2="500" stroke="{SUB}" '
             'stroke-width="1" stroke-dasharray="4 4"/>')
    (HERE / "images").mkdir(exist_ok=True)
    (HERE / "images" / "quorum_concept.svg").write_text(
        "\n".join(p + ["</svg>"]) + "\n", encoding="utf-8")


def availability_figure():
    plt.rcParams.update({
        "font.size": 11, "axes.edgecolor": SUB, "axes.labelcolor": INK,
        "xtick.color": INK, "ytick.color": INK, "text.color": INK,
        "svg.fonttype": "path", "svg.hashsalt": "quorum",
        "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
    })
    ps = [10 ** (-3 + i * 0.025) for i in range(0, 77)]  # 0.001 .. ~0.08
    ps = [p for p in ps if p <= 0.2] + [0.2]
    lines = [  # (n, k, label, color, style)
        (3, 3, "3 of 3  (W=3 write, R=3 read)", RED, "-"),
        (3, 2, "2 of 3  (N=3 majority)", ACCENT, "-"),
        (5, 3, "3 of 5  (N=5 majority)", INK, "--"),
        (3, 1, "1 of 3  (W=1 write, R=1 read)", SUB, ":"),
    ]
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    for n, k, label, color, ls in lines:
        ax.plot(ps, [1 - available(n, k, p) for p in ps], color=color, ls=ls,
                lw=2.4, label=label)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(0.001, 0.2)
    ax.set_ylim(1e-10, 1)
    ax.set_xlabel("Probability that one node is down (p)")
    ax.set_ylabel("Probability the operation\ncannot reach its quorum")
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, loc="lower right", fontsize=10)
    fig.tight_layout()
    fig.savefig(HERE / "images" / "quorum_availability.svg",
                metadata={"Date": None})


if __name__ == "__main__":
    concept_figure()
    availability_figure()
