"""Generate the cover diagram of the heartbeat note as a hand-written SVG.

concept_figure() lays the signals the Monitor receives on a time axis, one
row per node. Nodes send every 1 s and the Monitor gives up after 5 s of
silence (the example in the note). Node 3 really stops, Node 2 only pauses
for 8 s in a GC, and both are judged failed in the same way.

tradeoff_figure() plots lab/sim.py: for fixed timeouts of 2 to 10 times the
interval, the mean detection delay against false suspicions per day.

Run: python3 content/notes/distributed-systems/heartbeat/figures.py
"""

import sys
from html import escape
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "lab"))
import sim  # noqa: E402
INK, SUB, ACCENT, RED = "#1f1f1f", "#666666", "#7aa6c2", "#e15759"
FILL, PALE = "#f2f2f2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
GREEN, GREEN_PALE = "#8fae86", "#e9f1e6"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"

X0, X1, T_MAX = 250, 920, 12  # time axis: 0..12 s
TIMEOUT = 5


def tx(t):
    return X0 + (X1 - X0) * t / T_MAX


def concept_figure():
    w, h = 960, 540
    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img"><title>'
        f'{escape("Monitor が受け取るハートビートと、5 秒の途絶で故障とみなす時点")}</title>',
        f'<style>text{{font-family:{FONT};fill:{INK}}} .sub{{fill:{SUB}}} '
        f'.red{{fill:{RED}}}</style>',
        f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
    ]

    def text(x, y, s, size=24, anchor="middle", weight="normal", cls=""):
        c = f' class="{cls}"' if cls else ""
        p.append(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
                 f'text-anchor="{anchor}"{c}>{escape(s)}</text>')

    text(480, 50, "Monitor が受け取る信号（1 秒ごとに送信）", 28, weight="normal")

    rows = [
        # name, sub label, received times, last tick before silence, resumed
        ("Node 1", "", list(range(0, 13)), None, False),
        ("Node 2", "GC で 8 秒停止", [0, 1, 2, 10, 11, 12], 2, True),
        ("Node 3", "停止", [0, 1, 2, 3], 3, False),
    ]
    for i, (name, sub, ticks, last, resumed) in enumerate(rows):
        y = 140 + i * 112  # centre line of the row
        text(40, y + (-4 if sub else 9), name, 28, "start", "normal")
        if sub:
            text(40, y + 32, sub, 24, "start", cls="sub")
        p.append(f'<line x1="{X0}" y1="{y}" x2="{X1}" y2="{y}" stroke="{SUB}" '
                 'stroke-width="1.5"/>')
        if last is not None:
            # Silence counted by the Monitor, until it gives up.
            x, xe = tx(last), tx(last + TIMEOUT)
            p.append(f'<rect x="{x}" y="{y - 34}" width="{xe - x}" height="68" '
                     f'fill="{OCHRE_PALE}" stroke="none"/>')
            text((x + xe) / 2, y + 9, "5 秒 受信なし", 24, cls="sub")
            # Moment the node is regarded as failed.
            p.append(f'<line x1="{xe}" y1="{y - 42}" x2="{xe}" y2="{y + 42}" '
                     f'stroke="{RED}" stroke-width="7" stroke-linecap="round"/>')
            cx = (xe + tx(10)) / 2 if resumed else (xe + X1) / 2
            half = 40 if resumed else 64
            p.append(f'<rect x="{cx - half}" y="{y - 20}" width="{2 * half}" height="40" '
                     'fill="#ffffff"/>')
            if resumed:
                text((xe + tx(10)) / 2, y + 9, "誤検知", 24, cls="red", weight="normal")
            else:
                text((xe + X1) / 2, y + 9, "本当に停止", 24, weight="normal")
        for t in ticks:
            p.append(f'<line x1="{tx(t)}" y1="{y - 24}" x2="{tx(t)}" y2="{y + 24}" '
                     f'stroke="{ACCENT}" stroke-width="7" stroke-linecap="round"/>')

    # Time axis.
    ya = 470
    p.append(f'<line x1="{X0}" y1="{ya}" x2="{X1}" y2="{ya}" stroke="{SUB}" '
             'stroke-width="2"/>')
    for t in range(0, T_MAX + 1, 2):
        p.append(f'<line x1="{tx(t)}" y1="{ya}" x2="{tx(t)}" y2="{ya + 10}" '
                 f'stroke="{SUB}" stroke-width="2"/>')
        text(tx(t), ya + 38, str(t), 24, cls="sub")
    text(40, ya + 38, "経過（秒）", 24, "start", cls="sub")

    (HERE / "images").mkdir(exist_ok=True)
    (HERE / "images" / "heartbeat_concept.svg").write_text(
        "\n".join(p + ["</svg>"]) + "\n", encoding="utf-8")


def tradeoff_figure():
    plt.rcParams.update({
        "font.size": 11, "axes.edgecolor": SUB, "axes.labelcolor": INK,
        "xtick.color": INK, "ytick.color": INK, "text.color": INK,
        "svg.fonttype": "path", "svg.hashsalt": "heartbeat",
        "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
    })
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    styles = {"stable": (ACCENT, "o", "stable (same DC)"),
              "jittery": (RED, "s", "jittery (cross-region)")}
    for name, (color, marker, label) in styles.items():
        rows = [r for r in sim.run(name) if r[1] > 0]  # log axis: drop zeros
        xs, ys = [r[2] for r in rows], [r[1] for r in rows]
        ax.plot(xs, ys, color=color, marker=marker, lw=2.2, ms=7, label=label)
        for k, fp, mean, _ in rows:
            ax.annotate(f"{k}T", (mean, fp), textcoords="offset points",
                        xytext=(6, 6), fontsize=10, color=SUB)
    ax.set_yscale("log")
    ax.set_xlabel("Mean detection delay after a crash (s)")
    ax.set_ylabel("False suspicions per day")
    ax.set_xlim(0, 11)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, loc="upper right")
    fig.tight_layout()
    fig.savefig(HERE / "images" / "heartbeat_timeout_tradeoff.svg",
                metadata={"Date": None})


class Svg:
    """A tiny hand-written SVG canvas for the explanatory figures."""

    def __init__(self, title, w=960, h=540):
        self.p = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}" role="img"><title>{escape(title)}</title>',
            f'<style>text{{font-family:{FONT};fill:{INK}}} .sub{{fill:{SUB}}}</style>',
            '<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" '
            f'markerHeight="6" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{SUB}"/>'
            '</marker></defs>',
            f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
        ]

    def text(self, x, y, s, size=24, anchor="middle", cls=""):
        c = f' class="{cls}"' if cls else ""
        self.p.append(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" '
                      f'text-anchor="{anchor}"{c}>{escape(s)}</text>')

    def raw(self, s):
        self.p.append(s)

    def line(self, x1, y1, x2, y2, color=SUB, sw=2.5, start=False, end=False, dash=""):
        m = (' marker-start="url(#a)"' if start else "") + (' marker-end="url(#a)"' if end else "")
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.p.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                      f'stroke="{color}" stroke-width="{sw}"{d}{m}/>')

    def circle(self, cx, cy, r, fill, stroke, sw=3):
        self.p.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r}" fill="{fill}" '
                      f'stroke="{stroke}" stroke-width="{sw}"/>')

    def save(self, name):
        (HERE / "images").mkdir(exist_ok=True)
        (HERE / "images" / name).write_text("\n".join(self.p + ["</svg>"]) + "\n",
                                            encoding="utf-8")


def topology_figure():
    """Messages per period with n = 5: central monitoring vs mutual monitoring."""
    import math
    f = Svg("中央集約型と相互監視型で 1 周期に流れる信号の本数")
    n, r_ring, r_node = 5, 150, 30

    def ring(cx, cy):
        return [(cx + r_ring * math.sin(2 * math.pi * i / n),
                 cy - r_ring * math.cos(2 * math.pi * i / n)) for i in range(n)]

    def arrow(a, b, both=False):
        (x1, y1), (x2, y2) = a, b
        d = math.hypot(x2 - x1, y2 - y1)
        ux, uy = (x2 - x1) / d, (y2 - y1) / d
        f.line(x1 + ux * (r_node + 4), y1 + uy * (r_node + 4),
               x2 - ux * (r_node + 6), y2 - uy * (r_node + 6), start=both, end=True)

    # Central: every node sends to the monitor.
    cx, cy = 240, 270
    f.text(cx, 52, "中央集約型", 28)
    for pt in ring(cx, cy):
        arrow(pt, (cx, cy))
    f.circle(cx, cy, 40, OCHRE_PALE, OCHRE)
    f.text(cx, cy + 9, "監視", 24)
    for x, y in ring(cx, cy):
        f.circle(x, y, r_node, PALE, ACCENT)
    f.text(cx, 500, "1 周期に n = 5 本", 26, cls="sub")

    # Mutual: every pair watches each other.
    cx = 720
    f.text(cx, 52, "相互監視型", 28)
    pts = ring(cx, cy)
    for i in range(n):
        for j in range(i + 1, n):
            arrow(pts[i], pts[j], both=True)
    for x, y in pts:
        f.circle(x, y, r_node, PALE, ACCENT)
    f.text(cx, 500, "1 周期に n × (n−1) = 20 本", 26, cls="sub")
    f.line(480, 90, 480, 470, FILL, sw=2)
    f.save("heartbeat_topology.svg")


def phi_figure():
    """phi = -log10(P): the tail of a normal model of arrival intervals."""
    import math
    from statistics import NormalDist
    f = Svg("到着間隔の分布の裾の面積 P と phi")
    dist = NormalDist(1.0, 0.2)             # arrival interval [s], illustrative
    x0, x1, lo, hi = 110, 900, 0.3, 1.8     # plot range in px and seconds
    yb, top = 420, 110

    def px(t):
        return x0 + (x1 - x0) * (t - lo) / (hi - lo)

    peak = dist.pdf(1.0)

    def py(t):
        return yb - (yb - top) * dist.pdf(t) / peak

    ts = [lo + (hi - lo) * i / 400 for i in range(401)]
    t2 = dist.inv_cdf(0.9)                  # phi = 1: shade P = 10%
    tail = [t for t in ts if t >= t2]
    d = f"M{px(t2):.1f},{yb} " + " ".join(f"L{px(t):.1f},{py(t):.1f}" for t in [t2] + tail)
    f.raw(f'<path d="{d} L{px(hi):.1f},{yb} Z" fill="{OCHRE_PALE}" stroke="none"/>')
    d = "M" + " L".join(f"{px(t):.1f},{py(t):.1f}" for t in ts)
    f.raw(f'<path d="{d}" fill="none" stroke="{ACCENT}" stroke-width="4"/>')
    f.line(x0, yb, x1 + 10, yb, SUB, sw=2, end=True)
    for phi in (1, 2, 3):
        t = dist.inv_cdf(1 - 10 ** -phi)
        ylab = 140 + (phi - 1) * 80
        f.line(px(t), yb, px(t), ylab + 44, SUB, sw=2, dash="6 6")
        f.text(px(t) + 10, ylab, f"φ = {phi}", 24, "start")
        f.text(px(t) + 10, ylab + 30, f"P = {10 ** (2 - phi):g}%", 24, "start", cls="sub")
    f.text(px(t2) + 28, yb - 16, "P", 24)
    f.text(px(1.0), 92, "これまでの到着間隔の分布", 24, cls="sub")
    f.text(x0, 470, "最後の受信からの経過 t", 24, "start", cls="sub")
    f.text(x1, 470, "長い →", 24, "end", cls="sub")
    f.save("heartbeat_phi.svg")


if __name__ == "__main__":
    concept_figure()
    tradeoff_figure()
    topology_figure()
    phi_figure()
