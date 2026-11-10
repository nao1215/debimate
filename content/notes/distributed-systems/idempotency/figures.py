"""Generate the cover diagram of the idempotency note (stdlib only).

Two worlds after a POST /charges: the request never reached the API, or the
API recorded the charge and only the response was lost. The client sees the
same 504 in both (one frame around both clients); only the server side differs.

Run: python3 content/notes/distributed-systems/idempotency/figures.py
"""

from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"
INK, SUB, ACCENT, RED = "#1f1f1f", "#666666", "#7aa6c2", "#e15759"
FILL, PALE = "#f2f2f2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"


class Svg:
    def __init__(self, width, height, title, defs=""):
        markers = "".join(
            f'<marker id="arrow-{name}" viewBox="0 0 10 10" refX="8" refY="5" '
            'markerWidth="4" markerHeight="4" orient="auto-start-reverse">'
            f'<path d="M0,0 L10,5 L0,10 z" fill="{color}"/></marker>'
            for name, color in (("sub", SUB), ("accent", ACCENT), ("red", RED)))
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img"><title>{escape(title)}</title>',
            f'<style>text{{font-family:{FONT};fill:{INK}}}</style>',
            f'<defs>{markers}{defs}</defs>',
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

    def line(self, x1, y1, x2, y2, color, sw=4, arrow=None, dash=""):
        m = f' marker-end="url(#arrow-{arrow})"' if arrow else ""
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
            f'stroke-width="{sw}" stroke-linecap="round"{d}{m}/>')

    def cross(self, cx, cy, r, color, sw=5):
        self.line(cx - r, cy - r, cx + r, cy + r, color, sw)
        self.line(cx - r, cy + r, cx + r, cy - r, color, sw)

    def raw(self, s):
        self.parts.append(s)

    def save(self, path):
        path.parent.mkdir(exist_ok=True)
        path.write_text("\n".join(self.parts + ["</svg>"]) + "\n", encoding="utf-8")


def concept_figure():
    f = Svg(960, 540, "要求が届かなかった場合と応答だけ失われた場合")
    f.text(162, 44, "クライアント", 26, weight="normal")
    f.text(788, 44, "決済 API", 26, weight="normal")
    f.box(24, 66, 276, 408, "none", ACCENT, sw=3, dash="10 7", rx=14)
    rows = [(178, "要求が届かなかった", False), (378, "応答だけ失われた", True)]
    for cy, label, charged in rows:
        f.box(50, cy - 55, 224, 110, PALE, ACCENT)
        f.text(162, cy + 9, "504 が返る", 28)
        f.text(470, cy - 62, label, 26, weight="normal")
        if charged:
            f.line(304, cy - 18, 632, cy - 18, SUB, arrow="sub")
            f.line(640, cy + 26, 516, cy + 26, SUB, dash="10 8")
            f.cross(494, cy + 26, 12, RED)
        else:
            f.line(304, cy - 18, 456, cy - 18, SUB)
            f.cross(480, cy - 18, 12, RED)
        f.box(640, cy - 78, 296, 156, FILL, SUB)
        if charged:
            f.box(672, cy - 36, 232, 84, OCHRE_PALE, OCHRE, sw=3, rx=8)
            f.text(788, cy + 16, "課金 1 件", 28, weight="normal")
        else:
            f.box(672, cy - 36, 232, 84, "#ffffff", SUB, dash="8 6", rx=8)
            f.text(788, cy + 16, "課金なし", 28, SUB)
    f.text(162, 516, "見えるものは同じ", 26, INK, weight="normal")
    f.text(788, 516, "違いはサーバー側だけ", 26, INK, weight="normal")
    f.save(HERE / "images" / "idempotency_concept.svg")


if __name__ == "__main__":
    concept_figure()
