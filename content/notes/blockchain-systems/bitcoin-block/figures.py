"""Generate the cover figure of the Bitcoin Block note (Python stdlib only).

concept_figure() draws four blocks in a row. Each large body (the list of
transactions) is summarized into the root row of a small 80-byte header, and
each header points to the previous one by its previous-hash row. One
transaction in block N+1 is rewritten (red, the one failure point), so its
root changes and the previous-hash rows of every later block turn ochre.

Run: python3 content/notes/blockchain-systems/bitcoin-block/figures.py
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
                for n, c in (("sub", SUB), ("red", RED), ("accent", ACCENT), ("ochre", OCHRE)))
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

def concept_figure():
    f = Svg(960, 540, "ヘッダが本体を要約し、直前のハッシュでブロックが繋がる")
    w, gap, x0 = 180, 60, 30
    hw, ht, rh = 130, 84, 40  # header width, header top, row height
    btop, bbot = 206, 410
    tampered = 1
    names = ["N", "N+1", "N+2", "N+3"]
    for i, name in enumerate(names):
        x = x0 + i * (w + gap)
        hx = x + (w - hw) / 2
        f.text(x + w / 2, 62, f"ブロック {name}", 24, SUB)
        after = i > tampered
        here = i == tampered
        # Body (large) is summarized into the root row of the header (small).
        f.raw(f'<polygon points="{x},{btop} {x + w},{btop} {hx + hw},{ht + 2 * rh} '
              f'{hx},{ht + 2 * rh}" fill="{PALE}"/>')
        f.box(x, btop, w, bbot - btop, FILL, SUB, sw=2, rx=8)
        for k in range(8):
            bad = here and k == 4
            f.box(x + 16, btop + 16 + k * 23, w - 32, 13,
                  RED if bad else "#dddddd", rx=3, sw=0)
        # Header rows: previous hash and Merkle root.
        for r, label in enumerate(("直前", "root")):
            red = (r == 0 and after) or (r == 1 and here)
            f.box(hx, ht + r * rh, hw, rh, OCHRE_PALE if red else PALE,
                  OCHRE if red else ACCENT, sw=2.5, rx=4)
            f.text(hx + hw / 2, ht + r * rh + 29, label, 24, INK)
        if i:
            px = x0 + (i - 1) * (w + gap) + (w + hw) / 2
            f.line(hx - 4, ht + rh / 2, px + 10, ht + rh / 2,
                   OCHRE if after else ACCENT, sw=4,
                   arrow="ochre" if after else "accent")
    f.text(30, 462, "小さい箱: ヘッダ 80 バイト　大きい箱: 本体（取引の並び）",
           24, SUB, anchor="start")
    f.text(30, 512, "1 か所の書き換えが、後ろの全ブロックの「直前」に伝わる", 26, INK,
           anchor="start")
    f.save("bitcoin-block_concept.svg")


if __name__ == "__main__":
    concept_figure()
