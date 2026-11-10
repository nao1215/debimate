"""Generate the cover diagram of the SQL NULL note (stdlib only).

concept_figure() sorts the four users of the note's example table into the
three truth values TRUE / FALSE / UNKNOWN for two conditions:
email <> 'sato@example.com' and id NOT IN (2, NULL).
Only the TRUE column survives WHERE.

Run: python3 content/notes/database-systems/sql-null/figures.py
"""

from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
INK, SUB, ACCENT, RED = "#1f1f1f", "#666666", "#7aa6c2", "#e15759"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
FILL, PALE = "#f2f2f2", "#eaf1f5"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"


class Svg:
    """Minimal hand-written SVG canvas (stdlib only)."""

    def __init__(self, width, height, title):
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img"><title>{escape(title)}</title>',
            f'<style>text{{font-family:{FONT};fill:{INK}}}</style>',
            '<defs>'
            + "".join(
                f'<marker id="arrow-{n}" viewBox="0 0 10 10" refX="9" refY="5" '
                'markerWidth="4" markerHeight="4" orient="auto">'
                f'<path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>'
                for n, c in (("red", RED), ("sub", SUB), ("accent", ACCENT)))
            + '</defs>',
            f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        ]

    def text(self, x, y, s, size=24, color=INK, weight="normal", anchor="middle"):
        self.parts.append(
            f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
            f'text-anchor="{anchor}" style="fill:{color}">{escape(s)}</text>')

    def box(self, x, y, w, h, fill, stroke, sw=2.5, dash="", rx=8):
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

    def save(self, path):
        path.parent.mkdir(exist_ok=True)
        path.write_text("\n".join(self.parts + ["</svg>"]) + "\n", encoding="utf-8")


# (label, x, width, fill, stroke, dash, foot, foot color)
COLUMNS = {
    "TRUE": (210, 190, PALE, ACCENT, "", "結果に残る", INK),
    "FALSE": (414, 190, FILL, SUB, "", "落ちる", SUB),
    "UNKNOWN": (618, 312, OCHRE_PALE, OCHRE, "10 7", "落ちる", SUB),
}
# (condition lines, row center y, {column: names})
ROWS = [
    (["email <>", "'sato@…'"], 200,
     {"TRUE": ["鈴木"], "FALSE": ["佐藤"], "UNKNOWN": ["高橋", "田中"]}),
    (["id NOT IN", "(2, NULL)"], 360,
     {"TRUE": [], "FALSE": ["鈴木"], "UNKNOWN": ["佐藤", "高橋", "田中"]}),
]


def concept_figure():
    f = Svg(960, 540, "WHERE が残す TRUE と、落ちる FALSE・UNKNOWN")
    for name, (x, w, fill, stroke, dash, foot, fc) in COLUMNS.items():
        f.box(x, 100, w, 350, fill, stroke, sw=3, dash=dash, rx=14)
        f.text(x + w / 2, 80, name, 28, weight="normal")
        f.text(x + w / 2, 492, foot, 26, fc)
    f.line(30, 280, 930, 280, "#cccccc", sw=2, dash="6 6")
    for lines, cy, cells in ROWS:
        for i, s in enumerate(lines):
            f.text(30, cy - 6 + i * 32, s, 24, anchor="start")
        for col, names in cells.items():
            x, w = COLUMNS[col][:2]
            if not names:
                f.text(x + w / 2, cy + 10, "0 件", 26, SUB)
                continue
            cw, gap = 88, 12
            left = x + (w - len(names) * cw - (len(names) - 1) * gap) / 2
            for i, n in enumerate(names):
                bx = left + i * (cw + gap)
                stroke = ACCENT if col == "TRUE" else (OCHRE if col == "UNKNOWN" else SUB)
                f.box(bx, cy - 28, cw, 56, "#ffffff", stroke, sw=3, rx=28)
                f.text(bx + cw / 2, cy + 9, n, 26)
    f.save(HERE / "images" / "sql-null_concept.svg")


if __name__ == "__main__":
    concept_figure()
