"""Generate the cover figure of the Bitcoin Transaction Lifecycle note.

concept_figure() draws, as a hand-written SVG (Python stdlib only), the places
one transaction (solid blue; other transactions are white) passes through from left to right: Alice's wallet, the
mempool of each node (one node does not have it), and a block followed by two
more blocks (3 confirmations). Waiting places (mempool, the unconfirmed
span) are ochre; the confirmed blocks and span are gray-green.

Run: python3 content/notes/blockchain-systems/bitcoin-transaction-lifecycle/figures.py
"""

from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
INK, SUB, FILL, PALE = "#1f1f1f", "#666666", "#f2f2f2", "#eaf1f5"
ACCENT, RED = "#7aa6c2", "#e15759"
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
            '<defs>'
            + "".join(
                f'<marker id="arrow-{n}" viewBox="0 0 10 10" refX="9" refY="5" '
                f'markerWidth="4" markerHeight="4" orient="auto">'
                f'<path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>'
                for n, c in (("sub", SUB), ("red", RED), ("accent", ACCENT)))
            + '</defs>',
            f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        ]

    def text(self, x, y, s, size=24, color=INK, weight="normal", anchor="middle"):
        self.parts.append(
            f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
            f'text-anchor="{anchor}" style="fill:{color}">{escape(s)}</text>')

    def box(self, x, y, w, h, fill, stroke="none", sw=2.5, dash="", rx=8):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def line(self, x1, y1, x2, y2, color, sw=3, arrow="", dash=""):
        m = f' marker-end="url(#arrow-{arrow})"' if arrow else ""
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
            f'stroke-width="{sw}" stroke-linecap="round"{d}{m}/>')

    def raw(self, s):
        self.parts.append(s)

    def save(self, name):
        (HERE / "images").mkdir(exist_ok=True)
        (HERE / "images" / name).write_text(
            "\n".join(self.parts + ["</svg>"]) + "\n", encoding="utf-8")

def token(f, x, y, ours, w=44, h=28):
    if ours:
        f.box(x, y, w, h, ACCENT, rx=5, sw=0)
    else:
        f.box(x, y, w, h, "#ffffff", SUB, sw=2, rx=5)


def concept_figure():
    f = Svg(960, 540, "同じ取引がウォレットから mempool を経てブロックへ移る")
    top, bottom = 110, 420

    # Wallet: Alice builds and signs the transaction.
    f.text(110, 70, "ウォレット", 28, weight="normal")
    f.box(30, top, 160, bottom - top, FILL, rx=14)
    token(f, 76, 222, True, 68, 42)
    f.text(110, 310, "作成・署名", 24, SUB)

    f.line(200, 265, 252, 265, SUB, sw=4, arrow="sub")
    f.text(226, 244, "送信", 24, SUB)

    # Each node keeps its own mempool; node 3 has not received it.
    f.text(390, 70, "各ノードの mempool", 28, weight="normal")
    rows = [(0, 1, 0, 0, 0), (0, 0, 0, 1, 0), (0, 0, 0, 0, 0)]
    for r, ours in enumerate(rows):
        y = top + r * 106
        f.box(262, y, 256, 90, OCHRE_PALE, OCHRE, sw=2, rx=12)
        for c, o in enumerate(ours):
            token(f, 276 + c * 47, y + 31, o, 38, 28)
    for y in (top + 90, top + 196):
        f.line(390, y + 2, 390, y + 14, SUB, sw=3, dash="3 5")

    f.line(528, 265, 606, 265, SUB, sw=4, arrow="sub")
    f.text(567, 244, "取り込み", 24, SUB)

    # Blocks: the transaction sits in block 1, two more follow.
    f.text(775, 70, "ブロック", 28, weight="normal")
    for b in range(3):
        x = 620 + b * 110
        if b:
            f.line(x - 20, 265, x, 265, GREEN, sw=4)
        f.box(x, 170, 90, 190, GREEN_PALE, GREEN, rx=10)
        for i in range(8):
            ours = b == 0 and i == 3
            token(f, x + 9 + (i % 2) * 38, 182 + (i // 2) * 43, ours, 34, 30)
    f.line(620, 384, 930, 384, INK, sw=2.5)
    f.line(620, 376, 620, 392, INK, sw=2.5)
    f.line(930, 376, 930, 392, INK, sw=2.5)
    f.text(775, 420, "確認数 3", 26)

    # Status shown by the wallet.
    f.line(30, 470, 518, 470, OCHRE, sw=6)
    f.text(274, 512, "未確認", 28, SUB)
    f.line(620, 470, 930, 470, GREEN, sw=6)
    f.text(775, 512, "確認済み", 28)
    f.save("bitcoin-transaction-lifecycle_concept.svg")


if __name__ == "__main__":
    concept_figure()
