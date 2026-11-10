"""Generate the cover figure of the Bounded Context note (Python stdlib only).

concept_figure() puts one shared order model on the left and three bounded
contexts on the right. The attributes are the same nine on both sides. A
change requested by shipping (adding a state) reaches all three businesses
when they share one model, and only the shipping context when they are
separated and matched by the order ID.

Run: python3 content/notes/software-architecture/bounded-context/figures.py
"""

from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
INK, SUB, ACCENT, RED = "#1f1f1f", "#666666", "#7aa6c2", "#e15759"
FILL, PALE, WHITE = "#f2f2f2", "#eaf1f5", "#ffffff"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"
MARKERS = {"ink": SUB, "accent": ACCENT, "red": RED}


class Svg:
    def __init__(self, width, height, title):
        defs = "".join(
            f'<marker id="arrow-{name}" viewBox="0 0 10 10" refX="8" refY="5" '
            f'markerWidth="4" markerHeight="4" orient="auto">'
            f'<path d="M0,0 L10,5 L0,10 z" fill="{color}"/></marker>'
            for name, color in MARKERS.items())
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img"><title>{escape(title)}</title>',
            f'<style>text{{font-family:{FONT};fill:{INK}}}</style>',
            f'<defs>{defs}</defs>',
            f'<rect width="{width}" height="{height}" fill="{WHITE}"/>',
        ]

    def text(self, x, y, s, size=24, color=INK, weight="normal", anchor="middle"):
        self.parts.append(
            f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
            f'text-anchor="{anchor}" style="fill:{color}">{escape(s)}</text>')

    def box(self, x, y, w, h, fill, stroke, sw=2.5, dash="", rx=10):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def ellipse(self, cx, cy, rx, ry, fill, stroke, sw=2.5):
        self.parts.append(
            f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="{sw}"/>')

    def line(self, x1, y1, x2, y2, color, sw=4, arrow="", dash=""):
        m = f' marker-end="url(#arrow-{arrow})"' if arrow else ""
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
            f'stroke-width="{sw}" stroke-linecap="round"{d}{m}/>')

    def path(self, d, color, sw=4, arrow="", dash="", fill="none"):
        m = f' marker-end="url(#arrow-{arrow})"' if arrow else ""
        da = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<path d="{d}" fill="{fill}" stroke="{color}" stroke-width="{sw}" '
            f'stroke-linecap="round" stroke-linejoin="round"{da}{m}/>')

    def cross(self, cx, cy, r, color, sw=6):
        self.line(cx - r, cy - r, cx + r, cy + r, color, sw)
        self.line(cx - r, cy + r, cx + r, cy - r, color, sw)

    def db(self, cx, top, w, h, label):
        rx, ry = w / 2, 14
        x = cx - rx
        self.parts.append(
            f'<path d="M{x},{top} v{h} a{rx},{ry} 0 0 0 {w},0 v{-h}" '
            f'fill="{FILL}" stroke="{SUB}" stroke-width="2.5"/>')
        self.ellipse(cx, top, rx, ry, FILL, SUB)
        self.text(cx, top + h / 2 + 18, label)

    def save(self, name):
        out = HERE / "images"
        out.mkdir(exist_ok=True)
        (out / name).write_text("\n".join(self.parts + ["</svg>"]) + "\n",
                                encoding="utf-8")


CONTEXTS = [
    ("販売", "注文", ["見積もり", "値引き", "成立"]),
    ("請求", "請求", ["支払方法", "入金", "督促"]),
    ("配送", "出荷", ["宛先", "箱", "追跡番号"]),
]


def change_tag(f, cx, y):
    f.box(cx - 80, y, 160, 40, OCHRE, OCHRE, rx=20)
    f.text(cx, y + 29, "状態を追加", 24, INK, weight="normal")


def concept_figure():
    f = Svg(960, 540, "共通の注文モデルと、境界で分けたモデルの違い")
    cols = (90, 230, 370)

    # Left: one shared model holds every attribute; all three businesses read it.
    f.text(230, 52, "共通モデル 1 つ", 30, weight="normal")
    change_tag(f, 230, 74)
    f.box(26, 128, 408, 236, OCHRE_PALE, OCHRE, sw=4)
    f.text(230, 170, "注文", 28, weight="normal")
    for cx, (_, _, attrs) in zip(cols, CONTEXTS):
        for i, a in enumerate(attrs):
            f.text(cx, 222 + 46 * i, a, 24)
    for cx, (team, _, _) in zip(cols, CONTEXTS):
        f.line(cx, 366, cx, 404, OCHRE, 4)
        f.box(cx - 56, 406, 112, 48, WHITE, OCHRE, sw=4)
        f.text(cx, 439, team, 26)
    f.text(230, 510, "変更が 3 つ全部に及ぶ", 26)

    f.line(480, 30, 480, 510, "#dddddd", sw=2)

    # Right: three contexts, each with its own word and attributes.
    rcols = (594, 730, 866)
    f.text(730, 52, "境界で分ける", 30, weight="normal")
    change_tag(f, 866, 74)
    for cx, (team, word, attrs), last in zip(rcols, CONTEXTS, (0, 0, 1)):
        f.line(cx, 402, cx, 432, SUB, 3)
        f.box(cx - 62, 128, 124, 274, OCHRE_PALE if last else PALE, OCHRE if last else ACCENT,
              sw=4 if last else 2.5, dash="" if last else "10 7")
        f.text(cx, 166, team, 24, SUB)
        f.text(cx, 206, word, 28, weight="normal")
        for i, a in enumerate(attrs):
            f.text(cx, 262 + 46 * i, a, 24)
    f.line(594, 432, 866, 432, SUB, 3)
    f.text(730, 466, "注文 ID で対応付ける", 24, SUB)
    f.text(730, 510, "変更は配送だけ", 26)

    f.save("bounded-context_concept.svg")


if __name__ == "__main__":
    concept_figure()
