"""Generate the cover diagram of the Adapter note as a hand-written SVG.

concept_figure() uses the same execution-unit frame as the Sidecar note,
three times. Each application emits metrics in its own shape (circle,
triangle, square); the adapter on the edge of each unit turns them into one
shape, so the monitoring system receives a single format.

Run: python3 content/notes/software-architecture/adapter/figures.py
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


def shape(f, kind, cx, cy, fill, stroke, r=22):
    if kind == "circle":
        f.parts.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}" '
                       f'stroke="{stroke}" stroke-width="3"/>')
    elif kind == "triangle":
        pts = f"{cx},{cy - r} {cx + r * 1.1},{cy + r * 0.8} {cx - r * 1.1},{cy + r * 0.8}"
        f.parts.append(f'<polygon points="{pts}" fill="{fill}" stroke="{stroke}" '
                       'stroke-width="3" stroke-linejoin="round"/>')
    elif kind == "square":
        f.parts.append(f'<rect x="{cx - r * 0.85}" y="{cy - r * 0.85}" width="{r * 1.7}" '
                       f'height="{r * 1.7}" fill="{fill}" stroke="{stroke}" stroke-width="3"/>')
    else:  # diamond: the one format the monitoring system reads
        pts = f"{cx},{cy - r} {cx + r},{cy} {cx},{cy + r} {cx - r},{cy}"
        f.parts.append(f'<polygon points="{pts}" fill="{fill}" stroke="{stroke}" '
                       'stroke-width="3" stroke-linejoin="round"/>')


APPS = [("アプリ A", "JMX", "circle"), ("アプリ B", "StatsD", "triangle"),
        ("アプリ C", "独自の形式", "square")]


def concept_figure():
    f = Svg(960, 540, "各アプリの形の違う出力が adapter を通って同じ形になり監視基盤に届く")
    f.text(30, 38, "実行単位", 26, SUB, "normal", "start")

    mon_x, mon_y, mon_w, mon_h = 790, 150, 150, 260
    for i, (name, fmt, kind) in enumerate(APPS):
        top = 54 + i * 160
        cy = top + 70
        # The execution unit (same frame as the Sidecar note).
        f.box(20, top, 560, 140, FILL, SUB, sw=2.5, dash="10 7", rx=20)
        f.box(40, top + 18, 220, 104, "#ffffff", INK, sw=3, rx=14)
        f.text(150, cy - 6, name, 26, weight="normal")
        f.text(150, cy + 30, fmt, 24, SUB)
        # Application output in its own shape.
        f.line(262, cy, 470, cy, SUB, 3)
        shape(f, kind, 360, cy, OCHRE_PALE, OCHRE)
        # The adapter sits on the edge of the unit.
        f.box(470, top + 22, 180, 96, PALE, ACCENT, sw=3, rx=14)
        f.text(560, cy + 9, "adapter", 26, weight="normal")
        # Same shape after the adapter.
        ty = mon_y + 60 + i * 70
        f.line(652, cy, mon_x - 8, ty, ACCENT, 4, arrow=True)
        shape(f, "diamond", 712, cy + (ty - cy) * (712 - 652) / (mon_x - 8 - 652), ACCENT, ACCENT)

    f.box(mon_x, mon_y, mon_w, mon_h, "#ffffff", INK, sw=3, rx=14)
    f.text(mon_x + mon_w / 2, mon_y + 44, "監視基盤", 26, weight="normal")
    for i in range(3):
        shape(f, "diamond", mon_x + mon_w / 2, mon_y + 100 + i * 52, ACCENT, ACCENT, r=18)
    f.text(mon_x + mon_w / 2, mon_y + mon_h + 40, "形式は 1 つ", 24, SUB)

    f.save(HERE / "images" / "adapter_concept.svg")


if __name__ == "__main__":
    concept_figure()
