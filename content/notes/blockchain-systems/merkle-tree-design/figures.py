"""Generate the cover figure of the Merkle Tree Design note (Python stdlib only).

concept_figure() puts two trees side by side. Under Bitcoin's rule of
duplicating the last node of an odd level, the leaves [A, B, C] (left, the
copied C drawn as an ochre dashed box) and [A, B, C, C] (right) build the same
tree and therefore the same root hash; the red = between the roots is the
one failure point.

Run: python3 content/notes/blockchain-systems/merkle-tree-design/figures.py
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

def tree(f, cx, leaves, dup):
    """Draw a 4-leaf tree centered at cx; leaf index `dup` is a copy."""
    ys = (410, 300, 190)
    lx = [cx - 135 + i * 90 for i in range(4)]
    mx = [(lx[0] + lx[1]) / 2, (lx[2] + lx[3]) / 2]
    for i, x in enumerate(lx):
        f.line(x, ys[0] - 24, mx[i // 2], ys[1] + 24, SUB, sw=3)
    for x in mx:
        f.line(x, ys[1] - 24, cx, ys[2] + 24, SUB, sw=3)
    for i, (x, name) in enumerate(zip(lx, leaves)):
        copy = i == dup
        f.box(x - 34, ys[0] - 24, 68, 48, "#ffffff" if copy else PALE,
              OCHRE if copy else ACCENT, sw=3.5 if copy else 2.5,
              dash="8 6" if copy else "", rx=6)
        f.text(x, ys[0] + 9, name, 26, INK)
    for x, name in zip(mx, ("AB", "CC")):
        f.box(x - 40, ys[1] - 24, 80, 48, PALE, ACCENT, rx=6)
        f.text(x, ys[1] + 9, name, 26)
    f.box(cx - 60, ys[2] - 26, 120, 52, ACCENT, rx=8, sw=0)
    f.text(cx, ys[2] + 9, "root", 26)


def concept_figure():
    f = Svg(960, 540, "末尾を複製する規則では [A, B, C] と [A, B, C, C] が同じ木になる")
    f.text(480, 56, "Bitcoin の規則: 奇数なら末尾を複製する", 28, weight="normal")
    f.text(240, 118, "葉 [A, B, C]", 26, SUB)
    f.text(720, 118, "葉 [A, B, C, C]", 26, SUB)
    tree(f, 240, "ABCC", 3)
    tree(f, 720, "ABCC", None)
    f.text(480, 206, "=", 56, RED, weight="normal")
    f.line(480, 100, 480, 150, "#dddddd", sw=2)
    f.line(480, 230, 480, 440, "#dddddd", sw=2)
    f.text(480, 500, "黄土色の破線の葉は複製。どちらも同じルートハッシュになる", 26, INK)
    f.save("merkle-tree-design_concept.svg")


if __name__ == "__main__":
    concept_figure()
