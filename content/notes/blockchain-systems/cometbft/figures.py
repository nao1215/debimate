"""Generate the figures of the CometBFT note.

python3 figures.py           # concept figure, halt threshold + timeline from lab/timeline.csv
"""

import csv
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
IMAGES = HERE / "images"

INK, SUB, NEUTRAL = "#1f1f1f", "#666666", "#f2f2f2"
BLUE, BLUE_PALE = "#7aa6c2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
RED = "#e15759"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"


class Svg:
    def __init__(self, w, h, title):
        self.w, self.h = w, h
        self.p = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}" role="img"><title>{escape(title)}</title>',
            f'<style>text{{font-family:{FONT};fill:{INK}}} .sub{{fill:{SUB}}}</style>',
            f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
        ]

    def text(self, x, y, s, size=26, anchor="middle", cls="", weight="normal"):
        c = f' class="{cls}"' if cls else ""
        self.p.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" '
                      f'font-weight="{weight}"{c}>{escape(s)}</text>')

    def rect(self, x, y, w, h, fill, stroke, sw=2.5, dash=None, rx=8):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.p.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
                      f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def line(self, x1, y1, x2, y2, stroke=SUB, sw=2.5, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.p.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" '
                      f'stroke-width="{sw}"{d}/>')

    def save(self, name):
        self.p.append("</svg>")
        (IMAGES / name).write_text("\n".join(self.p) + "\n", encoding="utf-8")


def concept_figure():
    """PoW branches and reorganizes; CometBFT commits with > 2/3 or waits at the next height."""
    s = Svg(960, 540, "PoW は分岐して長い方に揃うが、CometBFT は 2/3 を超える票で確定し、"
                      "届かなければ分岐せずに次の高さで待つ")
    s.line(480, 40, 480, 500, stroke="#d9d9d9", sw=2)

    # Left: PoW. A branch grows, the shorter tip is abandoned.
    s.text(240, 70, "PoW", 32, weight="normal")
    s.text(240, 108, "branches, longest wins", 24, cls="sub")
    y, size = 300, 64
    xs = [40, 130, 220, 310]
    for i, x in enumerate(xs):
        s.rect(x, y, size, size, BLUE_PALE, BLUE)
        if i:
            s.line(xs[i - 1] + size, y + size / 2, x, y + size / 2)
    # abandoned branch from the 2nd block
    s.line(130 + size, y + 10, 220, 200 + size / 2, stroke=OCHRE, dash="7 6")
    s.rect(220, 200, size, size, OCHRE_PALE, OCHRE, dash="7 6")
    s.line(310 + size, y + size / 2, 400, y + size / 2)
    s.rect(400, y, size, size, BLUE_PALE, BLUE)
    s.text(252, 186, "dropped", 24, cls="sub")
    s.text(240, 430, "reorg can undo blocks", 24)

    # Right: CometBFT. Committed blocks in one line, then rounds retry at the next height.
    s.text(720, 70, "CometBFT", 32, weight="normal")
    s.text(720, 108, "> 2/3 commits, else waits", 24, cls="sub")
    xs = [510, 600, 690]
    for i, x in enumerate(xs):
        s.rect(x, y, size, size, BLUE_PALE, BLUE, sw=3.5)
        if i:
            s.line(xs[i - 1] + size, y + size / 2, x, y + size / 2)
    # next height: proposed but not committed, the network waits instead of branching
    nx = 800
    s.line(690 + size, y + size / 2, nx, y + size / 2, dash="7 6")
    s.rect(nx, y, size, size, OCHRE_PALE, OCHRE, dash="7 6")
    s.text(nx + size / 2, y - 18, "next", 24, cls="sub")
    # vote gauge: 2 of 4 equal validators online, threshold > 2/3
    gx, gy, gw, gh = 530, 410, 380, 34
    s.rect(gx, gy, gw, gh, NEUTRAL, SUB, sw=2, rx=4)
    s.rect(gx, gy, gw * 0.5, gh, OCHRE_PALE, OCHRE, sw=2, rx=4)
    tx = gx + gw * 2 / 3
    s.line(tx, gy - 12, tx, gy + gh + 12, stroke=INK, sw=3)
    s.text(tx, gy - 20, "2/3", 24)
    s.text(gx + gw * 0.25, gy + 26, "2 of 4 up", 24)
    s.text(720, 500, "halt, no fork", 26, weight="normal")
    s.line(nx + 84, y + 20, nx + 108, y + 44, stroke=RED, sw=4)
    s.line(nx + 108, y + 20, nx + 84, y + 44, stroke=RED, sw=4)
    s.save("cometbft_concept.svg")


def halt_figure():
    """Share of voting power that cannot vote, against the 1/3 line (run 1 of lab/run.py)."""
    s = Svg(960, 540, "票を出さない重みが 1/3 未満なら確定が進み、1/3 以上なら全体が止まる")
    x0, x1 = 40, 920

    def X(v):
        return x0 + (x1 - x0) * v

    s.text(x0 - 20, 60, "票を出さない重みの割合", 26, anchor="start", cls="sub")
    s.rect(X(0), 110, X(1 / 3) - X(0), 120, BLUE_PALE, BLUE, rx=0)
    s.rect(X(1 / 3), 110, X(1) - X(1 / 3), 120, OCHRE_PALE, OCHRE, rx=0)
    s.text((X(0) + X(1 / 3)) / 2, 182, "確定が進む", 28)
    s.text((X(1 / 3) + X(1)) / 2, 182, "全体が止まり、分岐しない", 28)
    s.line(X(1 / 3), 96, X(1 / 3), 290, stroke=INK, sw=3)
    s.text(X(1 / 3), 86, "1/3", 26)
    s.line(X(0), 270, X(1), 270, stroke=SUB, sw=2.5)
    for v, lab in [(1, "1")]:
        s.text(X(v), 305, lab, 24, cls="sub")
    # phases of run 1: (share not voting, label, blocks committed / phase length)
    points = [(0, "4 台", "15 個 / 20 秒", "start"),
              (1 / 4, "node3 停止", "11 個 / 30 秒", "middle"),
              (1 / 2, "2 台停止", "0 個 / 45 秒", "middle"),
              (1 / 2, "2|2 に分断", "0 個 / 45 秒", "middle")]
    for i, (v, lab, blocks, anchor) in enumerate(points):
        x = X(v)
        if i < 3:
            s.p.append(f'<circle cx="{x}" cy="270" r="11" fill="#ffffff" stroke="{INK}" stroke-width="3"/>')
        tx = x - 10 if anchor == "start" else x
        if i == 3:
            tx = X(0.75)
        s.text(tx if anchor == "middle" else x0 - 20, 350, lab, 26, anchor=anchor)
        s.text(tx if anchor == "middle" else x0 - 20, 390, blocks, 24, anchor=anchor, cls="sub")
    s.line(X(0.5) + 14, 278, X(0.75) - 70, 322, stroke=SUB, sw=2, dash="6 5")
    s.text(480, 470, "確定したブロックの数は、実験 1 回目の各区間", 24, cls="sub")
    s.save("cometbft_halt.svg")


def timeline_figure():
    """Committed height of the 4 nodes over time (run 1 of lab/run.py)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({
        "font.size": 10, "axes.edgecolor": SUB, "axes.labelcolor": INK,
        "xtick.color": INK, "ytick.color": INK, "text.color": INK,
        "svg.fonttype": "path", "svg.hashsalt": "cometbft",
        "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
    })
    with open(HERE / "lab" / "timeline.csv") as f:
        rows = list(csv.DictReader(f))
    t = [float(r["t"]) for r in rows]
    fig, ax = plt.subplots(figsize=(7.6, 3.6))
    styles = [(BLUE, "-"), (BLUE, "--"), (OCHRE, "-"), (OCHRE, "--")]
    for k, (color, ls) in enumerate(styles):
        # a stopped node has no sample: NaN breaks the line instead of bridging the gap
        ys = [int(r[f"h{k}"]) if r[f"h{k}"] else float("nan") for r in rows]
        ax.plot(t, ys, color=color, ls=ls, lw=1.8, label=f"node{k}")
    # phase boundaries
    bounds, names = [], []
    for ti, r in zip(t, rows):
        if not names or names[-1] != r["phase"]:
            bounds.append(ti)
            names.append(r["phase"])
    bounds.append(t[-1])
    short = {"all 4 up": "4 up", "node3 stopped": "3 up", "node2,3 stopped": "2 up",
             "node2,3 restarted": "4 up", "partition 0,1 | 2,3": "split 2|2",
             "partition healed": "healed"}
    top = max(int(r["h0"]) for r in rows if r["h0"])
    for i, name in enumerate(names):
        if name in ("node2,3 stopped", "partition 0,1 | 2,3"):
            ax.axvspan(bounds[i], bounds[i + 1], color=OCHRE_PALE, lw=0)
        ax.axvline(bounds[i], color="#d9d9d9", lw=1)
        ax.text((bounds[i] + bounds[i + 1]) / 2, top * 1.04, short.get(name, name),
                ha="center", fontsize=9, color=SUB)
    ax.set_xlabel("Elapsed time (s)")
    ax.set_ylabel("Committed height")
    ax.set_ylim(0, top * 1.12)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(loc="lower right", frameon=False, fontsize=9, ncol=2)
    fig.tight_layout()
    fig.savefig(IMAGES / "cometbft_timeline.svg", metadata={"Date": None})


if __name__ == "__main__":
    IMAGES.mkdir(exist_ok=True)
    concept_figure()
    halt_figure()
    if (HERE / "lab" / "timeline.csv").exists():
        timeline_figure()
