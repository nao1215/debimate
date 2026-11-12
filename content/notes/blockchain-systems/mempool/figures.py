"""Generate the cover diagram of the Mempool note (Python stdlib only).

concept_figure() draws the mempools of two nodes as overlapping sets. The node
settings follow the experiment in lab/compare_policy.py: Node A accepts from
1 sat/vB and Node B from 10 sat/vB, so the 2 sat/vB transaction b (red) is
held only by Node A. Transaction c is held only by Node B.

Run: python3 content/notes/blockchain-systems/mempool/figures.py
"""

from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
INK, SUB, ACCENT, RED = "#1f1f1f", "#666666", "#7aa6c2", "#e15759"
FILL, PALE = "#f2f2f2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"


class Svg:
    """A tiny hand-written SVG builder (960x540, white background)."""

    def __init__(self, title, width=960, height=540):
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img"><title>{escape(title)}</title>',
            f'<style>text{{font-family:{FONT};fill:{INK}}}</style>',
            '<defs>'
            + "".join(
                f'<marker id="arrow-{name}" viewBox="0 0 10 10" refX="9" refY="5" '
                f'markerWidth="4" markerHeight="4" orient="auto">'
                f'<path d="M0,0 L10,5 L0,10 z" fill="{color}"/></marker>'
                for name, color in (("sub", SUB), ("accent", ACCENT), ("red", RED)))
            + '</defs>',
            f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        ]

    def text(self, x, y, s, size=24, color=INK, weight="normal", anchor="middle"):
        self.parts.append(
            f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
            f'text-anchor="{anchor}" style="fill:{color}">{escape(s)}</text>')

    def box(self, x, y, w, h, fill, stroke="none", sw=2.5, dash="", rx=10, opacity=1):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        o = f' fill-opacity="{opacity}"' if opacity != 1 else ""
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
            f'fill="{fill}"{o} stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def circle(self, cx, cy, r, fill, stroke="none", sw=2.5, dash="", opacity=1):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        o = f' fill-opacity="{opacity}"' if opacity != 1 else ""
        self.parts.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}"{o} '
            f'stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def line(self, x1, y1, x2, y2, color, sw=4, arrow=None, dash=""):
        m = f' marker-end="url(#arrow-{arrow})"' if arrow else ""
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
            f'stroke-width="{sw}" stroke-linecap="round"{d}{m}/>')

    def path(self, d, stroke, sw=4, fill="none"):
        self.parts.append(
            f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" '
            'stroke-linecap="round" stroke-linejoin="round"/>')

    def save(self, path):
        path.parent.mkdir(exist_ok=True)
        path.write_text("\n".join(self.parts + ["</svg>"]) + "\n", encoding="utf-8")


def tx(f, cx, cy, label, color, text_color=INK):
    f.circle(cx, cy, 26, color)
    f.text(cx, cy + 10, label, 28, text_color, weight="normal")


def concept_figure():
    f = Svg("2 台のノードの mempool が重なりつつ中身が異なる様子")
    cy, r = 280, 186
    ax, bx = 360, 600
    # Node A is blue and Node B is ochre; the shared part is a neutral face,
    # drawn by clipping B's circle with A's, so no translucency is needed.
    f.circle(ax, cy, r, PALE)
    f.circle(bx, cy, r, OCHRE_PALE)
    f.parts.append(f'<clipPath id="node-a"><circle cx="{ax}" cy="{cy}" r="{r}"/></clipPath>'
                   f'<circle cx="{bx}" cy="{cy}" r="{r}" fill="{FILL}" clip-path="url(#node-a)"/>')
    f.circle(ax, cy, r, "none", ACCENT, sw=3)
    f.circle(bx, cy, r, "none", OCHRE, sw=3)
    f.text(250, 60, "Node A：最低 1 sat/vB", 26, weight="normal")
    f.text(710, 60, "Node B：最低 10 sat/vB", 26, weight="normal")

    # Other transactions without labels, to read as a pool.
    for x, y in ((236, 190), (300, 380), (468, 200), (492, 372), (720, 196), (690, 380)):
        f.circle(x, y, 12, "#ffffff", SUB, sw=2.5)
    tx(f, 480, 286, "a", SUB, "#ffffff")
    tx(f, 262, 286, "b", RED, "#ffffff")
    f.text(262, 344, "2 sat/vB", 24, INK)
    tx(f, 700, 286, "c", SUB, "#ffffff")
    f.text(480, 516, "b は B の最低手数料率に届かず、A だけが持つ", 24, INK)
    f.save(HERE / "images" / "mempool_concept.svg")


def _plt(salt):
    """matplotlib with the site's monochrome settings (imported lazily)."""
    import sys
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    sys.path.insert(0, str(HERE / "lab"))
    plt.rcParams.update({
        "font.size": 11, "axes.edgecolor": SUB, "axes.labelcolor": INK,
        "xtick.color": INK, "ytick.color": INK, "text.color": INK,
        "svg.fonttype": "path", "svg.hashsalt": salt,
        "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
    })
    return plt


def _save(fig, name):
    fig.tight_layout()
    fig.savefig(HERE / "images" / name, metadata={"Date": None})


def rolling_min_fee_figure():
    plt = _plt("mempool-rolling-min-fee")
    from rolling_min_fee import BUSY_HOURS, HOURS, LIMIT, run
    samples, _ = run()
    hours = [s[0] for s in samples]
    fig, (top, bottom) = plt.subplots(2, 1, figsize=(7.2, 5.0), sharex=True)
    top.plot(hours, [s[1] / 1e6 for s in samples], color=ACCENT, lw=2.4)
    top.axhline(LIMIT / 1e6, color=SUB, ls="--", lw=1.2)
    top.text(HOURS - 0.5, LIMIT / 1e6 + 0.12, "limit", color=SUB, ha="right")
    top.set_ylabel("Mempool (million vB)")
    top.set_ylim(0, 3.6)
    bottom.plot(hours, [s[2] for s in samples], color=RED, lw=2.4)
    bottom.set_ylabel("Minimum fee rate\n(sat/vB)")
    bottom.set_xlabel("Hours")
    bottom.set_xlim(0, HOURS)
    bottom.set_ylim(0, 2.2)
    for ax in (top, bottom):
        ax.axvspan(0, BUSY_HOURS, color="#f2f2f2", zorder=0)
        ax.spines[["top", "right"]].set_visible(False)
    top.text(BUSY_HOURS / 2, 1.2, "arrivals\n1.5 blocks\n/ 10 min", ha="center",
             color=SUB, fontsize=10)
    top.text(BUSY_HOURS + 1, 1.4, "arrivals 0.6 blocks / 10 min", color=SUB,
             fontsize=10)
    _save(fig, "mempool_rolling_min_fee.svg")


def eviction_figure():
    """A full mempool sorted by fee rate: a new high-rate tx pushes out the tail."""
    f = Svg("上限に達した mempool に手数料率の高いトランザクションが入ると、末尾のトランザクションが取り除かれる")
    f.text(480, 42, "上限に達した mempool（手数料率の高い順）", 26)
    base, limit_x = 380, 744
    f.box(60, 110, limit_x - 60, 290, "#ffffff", SUB, sw=2, rx=8)
    heights = [240 * 0.9 ** i for i in range(12)]
    heights.insert(2, (heights[1] + heights[2]) / 2)  # the new transaction
    for i, h in enumerate(heights):
        x = 80 + i * 56 + (20 if i == len(heights) - 1 else 0)
        if i == 2:
            fill, stroke = PALE, ACCENT
        elif i == len(heights) - 1:
            fill, stroke = OCHRE_PALE, OCHRE
        else:
            fill, stroke = FILL, SUB
        f.box(x, base - h, 44, h, fill, stroke, sw=2, rx=3)
    nx = 80 + 2 * 56 + 22
    f.text(nx, 92, "新しいトランザクション", 24)
    f.line(nx, 100, nx, base - heights[2] - 10, ACCENT, sw=3, arrow="accent")
    f.line(limit_x, 100, limit_x, 410, INK, sw=2.5, dash="8 6")
    f.text(limit_x, 92, "上限", 24)
    ex = 80 + 12 * 56 + 20 + 22
    f.text(ex + 20, base - heights[-1] - 24, "取り除く", 24, anchor="middle")
    f.text(400, 440, "高い　←　手数料率　→　低い", 24, SUB)
    f.text(480, 500, "最低の手数料率は、取り除いたトランザクションの率 + 0.1 sat/vB まで上がる", 24)
    f.save(HERE / "images" / "mempool_eviction.svg")


if __name__ == "__main__":
    concept_figure()
    rolling_min_fee_figure()
    eviction_figure()
