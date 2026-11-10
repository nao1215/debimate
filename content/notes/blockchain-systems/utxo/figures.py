"""Generate the cover diagram of the UTXO note as a hand-written SVG.

Coins are circles whose area is proportional to the amount. A transaction
consumes Alice's 1.0 BTC output whole (gray = spent) and creates Bob's
0.3 BTC output and Alice's 0.69 BTC change (filled = unspent). The 0.01 BTC
left over is the fee (ochre). The amounts are the change example in the note body.

Run: python3 content/notes/blockchain-systems/utxo/figures.py
"""

import math
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
INK, SUB, ACCENT, RED = "#1f1f1f", "#666666", "#7aa6c2", "#e15759"
FILL, PALE = "#f2f2f2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
GREEN, GREEN_PALE = "#8fae86", "#e9f1e6"
RED_PALE = "#fbe3e3"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"


class Svg:
    def __init__(self, width, height, title):
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img"><title>{escape(title)}</title>',
            f'<style>text{{font-family:{FONT};fill:{INK}}}</style>',
            '<defs><marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" '
            'markerWidth="4" markerHeight="4" orient="auto">'
            f'<path d="M0,0 L10,5 L0,10 z" fill="{SUB}"/></marker>'
            '<marker id="arrowred" viewBox="0 0 10 10" refX="8" refY="5" '
            'markerWidth="4" markerHeight="4" orient="auto">'
            f'<path d="M0,0 L10,5 L0,10 z" fill="{RED}"/></marker></defs>',
            f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        ]

    def text(self, x, y, s, size=24, color=INK, weight="normal", anchor="middle"):
        self.parts.append(
            f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
            f'text-anchor="{anchor}" style="fill:{color}">{escape(s)}</text>')

    def circle(self, cx, cy, r, fill, stroke, sw=3, dash=""):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r:.1f}" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def box(self, x, y, w, h, fill, stroke, sw=3, rx=14):
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')

    def arrow(self, x1, y1, x2, y2, color=SUB, sw=4):
        m = "arrowred" if color == RED else "arrow"
        self.parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{color}" '
            f'stroke-width="{sw}" stroke-linecap="round" marker-end="url(#{m})"/>')

    def save(self, path):
        path.parent.mkdir(exist_ok=True)
        path.write_text("\n".join(self.parts + ["</svg>"]) + "\n", encoding="utf-8")


def radius(btc):
    """Circle area is proportional to the amount: 1.0 BTC -> r = 110."""
    return 110 * math.sqrt(btc)


def concept_figure():
    f = Svg(960, 540, "取引が UTXO を丸ごと消費し、宛先とお釣りの出力を作る")

    # Left: the output Alice owned, now spent by the transaction.
    lx, cy_in = 145, 280
    f.text(lx, 60, "取引 1 の出力", 28, weight="normal")
    f.text(lx, 96, "使用済み", 26, SUB)
    r_in = radius(1.0)
    f.circle(lx, cy_in, r_in, FILL, SUB, dash="10 7")
    f.text(lx, cy_in - 8, "Alice", 28)
    f.text(lx, cy_in + 28, "1.0 BTC", 26)

    # Middle: the transaction that consumes it whole.
    f.box(325, 165, 150, 230, PALE, ACCENT)
    f.text(400, cy_in - 6, "取引 2", 28, weight="normal")
    f.text(400, cy_in + 30, "丸ごと消費", 24, SUB)
    f.arrow(lx + r_in + 8, cy_in, 315, cy_in)

    # Right: new outputs, unspent until another transaction consumes them.
    rx = 640
    f.text(rx + 60, 60, "取引 2 の出力", 28, weight="normal")
    f.text(rx + 60, 96, "未使用（UTXO）", 26, SUB)
    outs = [("Bob", 0.3, 180), ("Alice のお釣り", 0.69, 345)]
    for name, btc, cy in outs:
        r = radius(btc)
        f.circle(rx, cy, r, ACCENT, ACCENT)
        f.arrow(483, cy_in + (cy - cy_in) * 0.3, rx - r - 10, cy - (cy - cy_in) * 0.1)
        f.text(rx + r + 16, cy - 6, name, 26, anchor="start")
        f.text(rx + r + 16, cy + 26, f"{btc} BTC", 26, anchor="start")

    # The fee is what is left: no output, it goes to the block's miner.
    r_fee = radius(0.01)
    f.circle(rx, 488, r_fee, OCHRE, OCHRE)
    f.arrow(460, 403, rx - r_fee - 10, 484, OCHRE, sw=3)
    f.text(rx + r_fee + 16, 497, "差額 0.01 BTC は手数料", 26, INK, anchor="start")

    f.text(lx, 488, "円の面積 = 金額", 24, SUB)

    f.save(HERE / "images" / "utxo_concept.svg")


if __name__ == "__main__":
    concept_figure()
