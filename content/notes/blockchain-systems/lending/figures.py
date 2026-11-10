"""Generate the figures of the Lending note.

concept_figure() uses the Python standard library only.
rate_figure() and liquidation_figure() need matplotlib;
liquidation_figure() reads lab/lending_sim_output.txt.

Run: python3 content/notes/blockchain-systems/lending/figures.py
"""

import re
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
                for name, color in (("sub", SUB), ("accent", ACCENT), ("ochre", OCHRE)))
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


def concept_figure():
    """10 ETH of collateral, 12,000 USDC of debt, and the ETH price falling."""
    f = Svg("担保 10 ETH と借入 12,000 USDC。ETH の価格が下がり、担保の 80% の線が借入を下回ると清算される")
    base, scale = 400, 300 / 20000  # px per USDC
    debt = 12000
    for i, (price, hf) in enumerate(((2000, "1.33"), (1600, "1.07"), (1400, "0.93"))):
        cx = 170 + i * 310
        value = 10 * price
        h, lim = value * scale, value * 0.8 * scale
        f.text(cx, 56, f"1 ETH = {price:,} ドル", 26)
        f.box(cx - 115, base - h, 105, h, PALE, ACCENT, sw=3, rx=4)
        f.box(cx + 10, base - debt * scale, 105, debt * scale, OCHRE_PALE, OCHRE, sw=3, rx=4)
        f.line(cx - 135, base - lim, cx + 135, base - lim, SUB, sw=3, dash="10 7")
        f.line(cx - 140, base, cx + 140, base, SUB, sw=2)
        if i == 2:
            f.circle(cx + 62, base - debt * scale - 2, 18, RED)
            f.text(cx + 62, base - debt * scale + 7, "×", 26, "#ffffff")
        f.text(cx, base + 44, f"HF {hf}", 26, RED if i == 2 else INK)
    f.box(150, 478, 28, 22, PALE, ACCENT, sw=2.5, rx=3)
    f.text(186, 498, "担保の価値", 22, SUB, anchor="start")
    f.box(370, 478, 28, 22, OCHRE_PALE, OCHRE, sw=2.5, rx=3)
    f.text(406, 498, "借入", 22, SUB, anchor="start")
    f.line(520, 489, 570, 489, SUB, sw=3, dash="10 7")
    f.text(582, 498, "清算の線（担保の 80%）", 22, SUB, anchor="start")
    f.save(HERE / "images" / "lending_concept.svg")


def _plt(salt):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "font.size": 11, "axes.edgecolor": SUB, "axes.labelcolor": INK,
        "xtick.color": INK, "ytick.color": INK, "text.color": INK,
        "svg.fonttype": "path", "svg.hashsalt": salt,
        "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
    })
    return plt


def rate_figure():
    """A kinked borrow rate curve (illustrative parameters, not a real market)."""
    plt = _plt("lending-rate")
    optimal, base, slope1, slope2, reserve_factor = 0.80, 0.0, 0.04, 0.75, 0.15
    u = [i / 200 for i in range(201)]
    borrow = [base + slope1 * x / optimal if x <= optimal
              else base + slope1 + slope2 * (x - optimal) / (1 - optimal) for x in u]
    supply = [b * x * (1 - reserve_factor) for b, x in zip(borrow, u)]
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    ax.plot([x * 100 for x in u], [b * 100 for b in borrow], color=OCHRE, lw=2.4,
            label="borrow rate")
    ax.plot([x * 100 for x in u], [s * 100 for s in supply], color=ACCENT, lw=2.4,
            label="supply rate")
    ax.axvline(optimal * 100, color=SUB, lw=1, ls="--")
    ax.text(optimal * 100 - 1.5, 60, "optimal usage\n(kink) 80%", ha="right", color=SUB)
    ax.set_xlabel("utilization: borrowed / (borrowed + available)  [%]")
    ax.set_ylabel("annual rate [%]")
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 82)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, loc="upper left")
    fig.tight_layout()
    fig.savefig(HERE / "images" / "lending_rate.svg", metadata={"Date": None})


def liquidation_figure():
    plt = _plt("lending-liquidation")
    text = (HERE / "lab" / "lending_sim_output.txt").read_text()
    rows = re.findall(r"^  hf (\w+) (\d+) (\S+) (\S+) (\S+)$", text, re.M)
    bad = float(re.search(r"\[gap\].*?bad debt: ([\d.]+)", text, re.S).group(1))
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    smooth = [(int(p), float(b), float(c)) for s, p, _, b, c in rows if s == "smooth"]
    ax.plot([r[0] for r in smooth], [r[1] for r in smooth], color=SUB, lw=1.8,
            label="B (borrowed 60%), price falls 10 per step")
    ax.plot([r[0] for r in smooth], [r[2] for r in smooth], color=ACCENT, lw=2.4,
            label="C (borrowed 75%), price falls 10 per step")
    gap = [(int(p), float(c)) for s, p, _, _, c in rows if s == "gap" and c != "inf"]
    # HF of C at 1,300 just before it is liquidated: 10 ETH * 1300 * 0.8 / 15000
    hf_c = 10 * 1300 * 0.8 / 15000
    ax.plot([r[0] for r in gap] + [1300], [r[1] for r in gap] + [hf_c], color=OCHRE,
            lw=2.4, ls="--", label="C, price jumps 1,950 -> 1,300")
    ax.plot([1300], [hf_c], "x", color=RED, ms=11, mew=3)
    ax.annotate(f"collateral < debt\nbad debt {bad:,.0f} USDC", (1300, hf_c),
                (1640, 0.64), color=INK, arrowprops={"arrowstyle": "-", "color": SUB})
    ax.axhline(1.0, color=SUB, lw=1, ls=":")
    ax.text(1995, 0.97, "HF = 1", va="top", color=SUB)
    ax.set_xlim(2010, 1190)
    ax.set_ylim(0.55, 1.42)
    ax.set_xlabel("ETH price [USDC]  (falls to the right)")
    ax.set_ylabel("health factor after liquidations")
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, loc="upper right", fontsize=9.5)
    fig.tight_layout()
    fig.savefig(HERE / "images" / "lending_liquidation.svg", metadata={"Date": None})


if __name__ == "__main__":
    concept_figure()
    rate_figure()
    liquidation_figure()
