"""Generate the cover figure of the Value Object / Entity / Aggregate note
(Python stdlib only).

concept_figure() draws the Order and Customer aggregates as frames. The only
door into a frame is its aggregate root, which sits on the frame edge. Entities
carry an ID tag, Value Objects are small tags without an ID. Outside code that
tries to reach an OrderLine directly is stopped at the frame (red), and Order
refers to the Customer aggregate only by CustomerID.

Run: python3 content/notes/software-architecture/value-object-entity-aggregate/figures.py
"""

from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
INK, SUB, ACCENT, RED = "#1f1f1f", "#666666", "#7aa6c2", "#e15759"
FILL, PALE, WHITE = "#f2f2f2", "#eaf1f5", "#ffffff"
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


def id_tag(f, x, y):
    f.box(x, y, 48, 36, SUB, SUB, sw=0, rx=6)
    f.text(x + 24, y + 27, "ID", 22, WHITE, weight="normal")


def entity(f, x, y, w, h, name, root=False):
    f.box(x, y, w, h, WHITE, SUB, sw=3)
    id_tag(f, x + 12, y + (h - 36) / 2)
    cx = x + 60 + (w - 60) / 2
    if root:
        f.text(cx, y + h / 2 - 6, name, 26, weight="normal")
        f.text(cx, y + h / 2 + 26, "集約ルート", 24, SUB)
    else:
        f.text(cx, y + h / 2 + 9, name, 24)


def value(f, x, y, name):
    f.box(x, y, 118, 44, FILL, SUB, sw=2, rx=22)
    f.text(x + 59, y + 31, name, 24)


def concept_figure():
    f = Svg(960, 540, "集約の境界と、Value Object・Entity・集約ルートの関係")

    # Outside code: one door through the root, one blocked direct path.
    f.box(14, 110, 112, 200, FILL, SUB)
    f.text(70, 200, "外の", 24)
    f.text(70, 232, "コード", 24)
    f.line(126, 155, 166, 155, ACCENT, 5, arrow="accent")
    f.line(126, 275, 180, 275, RED, 5, arrow="red")

    # Order aggregate.
    f.box(200, 70, 410, 400, PALE, ACCENT, sw=4, rx=16)
    f.text(405, 452, "Order 集約", 24, SUB)
    f.path("M222,200 V375 M222,275 H240 M222,375 H240", SUB, 3)
    for y in (240, 340):
        entity(f, 240, y, 220, 70, "OrderLine")
        f.line(460, y + 35, 478, y + 35, SUB, 3)
        value(f, 478, y + 13, "Money")
    entity(f, 176, 110, 234, 90, "Order", root=True)
    f.cross(200, 275, 14, RED)

    # Customer aggregate, referred to only by its ID.
    f.box(680, 70, 262, 400, PALE, ACCENT, sw=4, rx=16)
    f.text(811, 452, "Customer 集約", 24, SUB)
    f.line(780, 200, 780, 260, SUB, 3)
    value(f, 721, 260, "Address")
    entity(f, 656, 110, 262, 90, "Customer", root=True)
    f.line(412, 155, 646, 155, SUB, 3, arrow="ink", dash="8 7")
    f.text(529, 140, "CustomerID", 24, SUB)

    # Legend.
    id_tag(f, 140, 490)
    f.text(198, 517, "Entity", 24, anchor="start")
    f.box(300, 486, 60, 44, FILL, SUB, sw=2, rx=22)
    f.text(372, 517, "Value Object", 24, anchor="start")
    f.cross(560, 508, 12, RED)
    f.text(588, 517, "外から直接は触れない", 24, anchor="start")

    f.save("value-object-entity-aggregate_concept.svg")


OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"


def units_figure():
    """A number that loses its unit between writer and reader.

    Top: the Mars Climate Orbiter hand-off. The writer (blue) knows the value
    is in pound-seconds, the file carries only the number, and the reader
    (ochre) takes it as newton-seconds. Bottom: a Money value that keeps the
    amount and the currency together, so the pair cannot be split.
    """
    f = Svg(960, 540, "数値から単位が落ちる受け渡しと、単位を組で持つ値")
    f.text(40, 50, "Mars Climate Orbiter の受け渡し（数値は例）", 24, SUB, anchor="start")
    f.box(40, 86, 260, 150, PALE, ACCENT)
    f.text(170, 132, "地上のソフトウェア", 24)
    f.text(170, 172, "ポンド秒で", 24, SUB)
    f.text(170, 208, "書き出す", 24, SUB)
    f.line(306, 161, 372, 161, SUB, sw=4, arrow="ink")
    f.box(380, 106, 200, 110, FILL, SUB)
    f.text(480, 146, "ファイル", 24, SUB)
    f.text(480, 196, "100", 34)
    f.line(586, 161, 652, 161, SUB, sw=4, arrow="ink")
    f.box(660, 86, 260, 150, OCHRE_PALE, OCHRE)
    f.text(790, 132, "軌道の計算", 24)
    f.text(790, 172, "ニュートン秒", 24, SUB)
    f.text(790, 208, "として読む", 24, SUB)
    f.text(480, 280, "100 ポンド秒は約 445 ニュートン秒。ファイルに単位は無い", 24, SUB)
    f.line(40, 322, 920, 322, "#dddddd", sw=2)
    f.text(40, 376, "Value Object にした金額", 24, SUB, anchor="start")
    f.box(250, 404, 460, 92, PALE, ACCENT, rx=12)
    f.text(282, 436, "Money", 24, SUB, anchor="start")
    f.box(282, 446, 190, 40, WHITE, ACCENT, sw=2, rx=6)
    f.text(377, 474, "amount 1999", 24)
    f.box(488, 446, 190, 40, WHITE, ACCENT, sw=2, rx=6)
    f.text(583, 474, "currency JPY", 24)
    f.text(760, 460, "組のまま渡る", 24, SUB, anchor="start")
    f.save("value-object-entity-aggregate_units.svg")


if __name__ == "__main__":
    concept_figure()
    units_figure()
