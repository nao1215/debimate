"""Generate the cover diagram of the Sidecar note as a hand-written SVG.

concept_figure() draws one execution unit (Pod / Task). The main container
and the sidecar overlap: what they share (volume and network) sits in the
overlap, and what each keeps for itself (image and resource limit) appears
once on each side. The Ambassador and Adapter notes use the same frame.

Run: python3 content/notes/software-architecture/sidecar/figures.py
"""

from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
INK, SUB, ACCENT, RED = "#1f1f1f", "#666666", "#7aa6c2", "#e15759"
FILL, PALE = "#f2f2f2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"


class Svg:
    def __init__(self, width, height, title):
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img"><title>{escape(title)}</title>',
            f'<style>text{{font-family:{FONT};fill:{INK}}}</style>',
            '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" '
            'markerWidth="4" markerHeight="4" orient="auto">'
            f'<path d="M0,0 L10,5 L0,10 z" fill="{INK}"/></marker></defs>',
            f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
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

    def line(self, x1, y1, x2, y2, color=INK, sw=4, arrow=False):
        m = ' marker-end="url(#arrow)"' if arrow else ""
        self.parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
            f'stroke-width="{sw}" stroke-linecap="round"{m}/>')

    def db(self, cx, top, w, h, fill, stroke):
        rx, ry = w / 2, 10
        x = cx - rx
        self.parts.append(
            f'<path d="M{x},{top} v{h} a{rx},{ry} 0 0 0 {w},0 v{-h}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="2.5"/>')
        self.parts.append(
            f'<ellipse cx="{cx}" cy="{top}" rx="{rx}" ry="{ry}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="2.5"/>')

    def save(self, path):
        path.parent.mkdir(exist_ok=True)
        path.write_text("\n".join(self.parts + ["</svg>"]) + "\n", encoding="utf-8")


def concept_figure():
    f = Svg(960, 540, "同じ実行単位の main と sidecar が共有するものと分けるもの")

    # The execution unit (Pod / Task).
    f.box(180, 40, 560, 470, FILL, SUB, sw=2.5, dash="10 7", rx=24)
    f.text(204, 82, "実行単位", 26, SUB, "normal", "start")

    # Two containers overlapping in the middle, shifted vertically so the
    # overlap reads as the intersection of two boxes, not a third box.
    w, h = 340, 360
    main_x, main_y, side_x, side_y = 200, 100, 380, 140  # overlap: 380..540
    for x, y, fill in ((main_x, main_y, PALE), (side_x, side_y, OCHRE_PALE)):
        f.box(x, y, w, h, fill, INK, sw=0, rx=18)
    # Shared area: the intersection of the two containers.
    f.box(side_x, side_y, main_x + w - side_x, main_y + h - side_y, "#ffffff", ACCENT, sw=0, rx=0)
    for x, y, stroke in ((main_x, main_y, ACCENT), (side_x, side_y, OCHRE)):
        f.box(x, y, w, h, "none", stroke, sw=3, rx=18)

    f.text(290, 142, "main", 28, weight="normal")
    f.text(290, 178, "Web サーバー", 24, SUB)
    f.text(630, 190, "sidecar", 28, weight="normal")
    f.text(630, 226, "logsaver", 24, SUB)

    # Shared: volume and network.
    f.text(460, 186, "共有", 26, INK, "normal")
    f.db(460, 230, 110, 60, FILL, INK)
    f.text(460, 276, "volume", 24)
    f.box(400, 326, 120, 56, FILL, INK, rx=8)
    f.text(460, 363, "network", 24)
    f.text(460, 438, "1 つ", 24, INK, "normal")

    # Kept per container: image and resource limit.
    for cx, y in ((290, 240), (630, 280)):
        f.box(cx - 75, y, 150, 52, "#ffffff", SUB, sw=2)
        f.text(cx, y + 35, "イメージ", 24, SUB)
        f.box(cx - 75, y + 68, 150, 52, "#ffffff", SUB, sw=2)
        f.text(cx, y + 103, "資源の上限", 24, SUB)
        f.text(cx, y + 168, "別々", 24, SUB, "normal")

    # Outside: the client calls main, the sidecar sends logs out.
    f.box(6, 175, 160, 70, "#ffffff", INK, sw=2.5)
    f.text(86, 219, "クライアント", 24)
    f.line(168, 210, 214, 210, INK, 4, arrow=True)
    f.db(860, 230, 150, 80, "#ffffff", INK)
    f.text(860, 290, "ストレージ", 24)
    f.line(706, 265, 768, 265, INK, 4, arrow=True)

    f.save(HERE / "images" / "sidecar_concept.svg")


if __name__ == "__main__":
    concept_figure()
