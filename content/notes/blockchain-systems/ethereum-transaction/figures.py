"""Generate the cover diagram of the Ethereum transaction note.

concept_figure() draws the fee of a type 2 transaction as areas, as a
hand-written SVG (stdlib only). The width is gas (used gas inside gasLimit),
the height is the price per gas (base fee and priority fee under
maxFeePerGas). The outer frame is the maximum fee a wallet shows, and the
painted part is what is actually paid. The proportions are schematic.

Run: python3 content/notes/blockchain-systems/ethereum-transaction/figures.py
"""

from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"
INK, SUB, ACCENT, RED = "#1f1f1f", "#666666", "#7aa6c2", "#e15759"
FILL, PALE = "#f2f2f2", "#eaf1f5"
OCHRE = "#d4a24c"


class Svg:
    def __init__(self, width, height, title):
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img"><title>{escape(title)}</title>',
            f'<style>text{{font-family:{FONT};fill:{INK}}}</style>',
            '<defs>'
            + "".join(
                f'<marker id="arrow-{n}" viewBox="0 0 10 10" refX="9" refY="5" '
                'markerWidth="4" markerHeight="4" orient="auto">'
                f'<path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>'
                for n, c in (("ink", INK), ("sub", SUB), ("accent", ACCENT), ("red", RED)))
            + '</defs>',
            f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        ]

    def text(self, x, y, s, size=24, color=INK, weight="normal", anchor="middle",
             rotate=None):
        r = f' transform="rotate({rotate} {x} {y})"' if rotate is not None else ""
        self.parts.append(
            f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
            f'text-anchor="{anchor}" style="fill:{color}"{r}>{escape(s)}</text>')

    def box(self, x, y, w, h, fill, stroke="none", sw=2.5, dash="", rx=10):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def line(self, x1, y1, x2, y2, color, sw=4, arrow=None, dash=""):
        m = f' marker-end="url(#arrow-{arrow})"' if arrow else ""
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
            f'stroke-width="{sw}" stroke-linecap="round"{d}{m}/>')

    def save(self, path):
        path.parent.mkdir(exist_ok=True)
        path.write_text("\n".join(self.parts + ["</svg>"]) + "\n", encoding="utf-8")


def concept_figure():
    f = Svg(960, 540, "取引の手数料を gas の量と 1 gas あたりの額の面積で表した図")
    x0, x_used, x_lim = 200, 560, 760   # gas axis
    y0, y_base, y_prio, y_max = 430, 270, 205, 100   # price axis (top is larger)

    # Outer frame: gasLimit x maxFeePerGas, the maximum fee.
    f.box(x0, y_max, x_lim - x0, y0 - y_max, FILL, SUB, sw=2.5, dash="10 7", rx=0)
    # Painted part: used gas x (base fee + priority fee), the actual fee.
    f.box(x0, y_base, x_used - x0, y0 - y_base, OCHRE, "none", rx=0)
    f.box(x0, y_prio, x_used - x0, y_base - y_prio, ACCENT, "none", rx=0)
    cx = (x0 + x_used) / 2
    f.text(cx, (y0 + y_base) / 2 + 9, "base fee の分 → 焼却", 26, INK, "normal")
    f.text(cx, (y_base + y_prio) / 2 + 9, "priority fee の分 → 参加者", 24, INK, "normal")
    f.text(cx, (y_prio + y_max) / 2 + 9, "単価の上限までの余り", 24, SUB)
    rx = (x_used + x_lim) / 2
    f.text(rx, 250, "使わずに", 24, SUB)
    f.text(rx, 284, "済んだ gas", 24, SUB)

    # Axes.
    f.line(x0, y0, x0, y_max - 30, INK, sw=3, arrow="ink")
    f.line(x0, y0, x_lim + 50, y0, INK, sw=3, arrow="ink")
    f.text(70, 265, "1 gas あたりの額", 24, INK, rotate=-90)
    f.text(x_lim + 60, y0 + 8, "gas", 24, INK, anchor="start")
    for y, label in ((y_max, "maxFeePerGas"), (y_base, "base fee")):
        f.line(x0 - 10, y, x0, y, INK, sw=2)
        f.text(x0 - 16, y + 8, label, 24, INK, anchor="end")
    for x, label in ((x_used, "使った gas"), (x_lim, "gasLimit")):
        f.line(x, y0, x, y0 + 10, INK, sw=2)
        f.text(x, y0 + 40, label, 24, INK)
    f.text(480, 60, "外枠：最大手数料（gasLimit × maxFeePerGas）", 24, SUB)
    f.text(480, 515, "塗った面積が実際に払う手数料", 26, INK, "normal")
    f.save(HERE / "images" / "ethereum-transaction_concept.svg")


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


def base_fee_figure():
    plt = _plt("ethereum-transaction-base-fee")
    from base_fee import BLOCKS, GWEI, MAX_FEE, series
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    x = list(range(BLOCKS + 1))
    for usage, color, ls, label in ((1.00, RED, "-", "100 % full"),
                                    (0.75, ACCENT, "-", "75 % full"),
                                    (0.50, SUB, "-", "50 % (target)"),
                                    (0.00, INK, ":", "empty")):
        ax.plot(x, [f / GWEI for f in series(usage)], color=color, ls=ls, lw=2.4,
                label=label)
    ax.axhline(MAX_FEE / GWEI, color=SUB, ls="--", lw=1.4)
    ax.text(0.3, MAX_FEE / GWEI + 3, "maxFeePerGas = 30 gwei", color=SUB)
    ax.set_xlabel("Blocks after the start (12 s each)")
    ax.set_ylabel("Base fee (gwei)")
    ax.set_xlim(0, BLOCKS)
    ax.set_ylim(0, 100)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, loc="upper left", bbox_to_anchor=(0.0, 0.85))
    _save(fig, "ethereum-transaction_base_fee.svg")


if __name__ == "__main__":
    concept_figure()
    base_fee_figure()
