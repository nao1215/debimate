"""Generate the cover figure of the Anticorruption Layer note (Python stdlib only).

concept_figure() draws the upstream inventory system on the left and the
downstream sales context on the right. The ACL is the membrane on the edge of
the downstream area: the upstream terms (red) exist only outside it, and the
sales model inside uses only its own terms.

Run: python3 content/notes/software-architecture/anti-corruption-layer/figures.py
"""

from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
INK, SUB, ACCENT, RED = "#1f1f1f", "#666666", "#7aa6c2", "#e15759"
FILL, PALE, WHITE = "#f2f2f2", "#eaf1f5", "#ffffff"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"
MARKERS = {"ink": SUB, "accent": ACCENT, "red": RED, "ochre": OCHRE}


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


def concept_figure():
    f = Svg(960, 540, "Anticorruption Layer の位置と語の切り替わり")
    # Upstream: the inventory system speaks its own terms (ochre).
    f.box(24, 120, 270, 300, OCHRE_PALE, OCHRE)
    f.text(159, 172, "在庫システム", 28, weight="normal")
    f.text(159, 206, "上流", 24, SUB)
    for y, word in ((276, "QTY_ON_HAND"), (330, "QTY_ALLOC"), (384, "STS")):
        f.text(159, y, word, 26, INK, weight="normal")
    f.text(159, 468, "相手の語", 26)

    # Downstream: the sales context, with the ACL as a membrane on its edge.
    f.box(396, 56, 540, 428, PALE, ACCENT, rx=16)
    f.box(396, 56, 66, 428, ACCENT, ACCENT, rx=0)
    f.text(429, 280, "ACL", 26, INK, weight="normal")
    f.text(699, 104, "下流：販売コンテキスト", 28, weight="normal")
    f.box(520, 150, 380, 240, WHITE, SUB)
    f.text(710, 200, "注文の成立を判断するモデル", 24)
    f.text(710, 280, "販売できる数", 28, weight="normal")
    f.text(710, 340, "販売停止", 28, weight="normal")
    f.text(710, 448, "自分の語", 26)

    # Outside the membrane the exchange is in upstream terms (ochre arrows),
    # inside it is in sales terms.
    f.line(390, 230, 304, 230, OCHRE, 5, arrow="ochre")
    f.line(300, 330, 384, 330, OCHRE, 5, arrow="ochre")
    f.line(514, 230, 472, 230, SUB, 4, arrow="ink")
    f.line(470, 330, 512, 330, SUB, 4, arrow="ink")

    f.save("anti-corruption-layer_concept.svg")


def unknown_status_figure():
    """A new STS value from the upstream: stopped at the ACL, or read in every place."""
    f = Svg(960, 540, "上流が足した新しい状態コードを、ACL の 1 箇所で止めるか、各所で読むか")

    # With the ACL.
    f.text(40, 44, "ACL がある", 26, anchor="start")
    f.box(40, 76, 220, 76, OCHRE_PALE, OCHRE)
    f.text(150, 123, "STS = \"7\"", 26)
    f.line(266, 114, 330, 114, OCHRE, sw=4, arrow="ochre")
    f.box(340, 66, 240, 96, PALE, ACCENT)
    f.text(460, 106, "ACL", 26)
    f.text(460, 140, "未知の値でエラー", 24, SUB)
    f.cross(606, 114, 13, RED)
    f.box(640, 76, 290, 76, WHITE, SUB, dash="8 6")
    f.text(785, 123, "販売のモデルに届かない", 24, SUB)

    # Without the ACL.
    f.text(40, 244, "ACL が無い", 26, anchor="start")
    f.box(40, 342, 220, 76, OCHRE_PALE, OCHRE)
    f.text(150, 389, "STS = \"7\"", 26)
    for k, label in enumerate(["注文の受付", "商品の一覧", "再入荷の通知"]):
        y = 270 + k * 92
        f.path(f"M266,380 C300,380 300,{y + 32} 344,{y + 32}", OCHRE, sw=4, arrow="ochre")
        f.box(352, y, 220, 64, WHITE, OCHRE)
        f.text(462, y + 41, label, 24)
        f.text(596, y + 41, "7 の意味を各所で判断", 24, SUB, anchor="start")
    f.save("anti-corruption-layer_unknown_status.svg")


if __name__ == "__main__":
    concept_figure()
    unknown_status_figure()
