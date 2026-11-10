"""Generate the cover diagram of the soft delete note (stdlib only).

concept_figure() lays the life of one record on a horizontal time axis and,
for each of the five ways in the note (physical delete, delete flag, state
transition, archive, anonymization), shows by colored bands what is left
where after the record stops being used.

Run: python3 content/notes/database-systems/soft-delete/figures.py
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


X0, CUT, X1 = 210, 420, 940
GONE = ("#ffffff", SUB, "9 6", SUB)      # nothing is left
KEPT = (FILL, SUB, "", INK)              # left in the same table
MOVED = (OCHRE_PALE, OCHRE, "9 6", INK)  # left in another place
# (name, [(start x, end x, style, text)]) for the part after CUT
ROWS = [
    ("物理削除", [(CUT, X1, GONE, "何も残らない")]),
    ("削除フラグ", [(CUT, X1, KEPT, "deleted_at を付けて残る")]),
    ("状態の遷移", [(CUT, X1, KEPT, "「退会済み」として残る")]),
    ("アーカイブ", [(CUT, 600, KEPT, "保持期間"), (612, X1, MOVED, "別の表に移る")]),
    ("匿名化", [(CUT, X1, KEPT, "個人データだけ消して残る")]),
]


def concept_figure():
    f = Svg(960, 540, "使わなくなったレコードの扱いごとに、どこに何が残るか")
    f.text((X0 + CUT) / 2, 58, "使っている間", 24, SUB)
    f.text((CUT + X1) / 2, 58, "使わなくなった後", 24, SUB)
    for i, (name, segs) in enumerate(ROWS):
        y = 88 + i * 72
        f.text(30, y + 33, name, 24, anchor="start")
        f.box(X0, y, CUT - X0 - 6, 48, PALE, ACCENT, sw=2.5)
        for x1, x2, (fill, stroke, dash, color), label in segs:
            f.box(x1 + 6, y, x2 - x1 - 6, 48, fill, stroke, sw=2.5, dash=dash)
            f.text((x1 + 6 + x2) / 2, y + 33, label, 24, color)
    f.line(CUT, 76, CUT, 448, INK, sw=3, dash="2 7")

    legend = [((PALE, ACCENT, ""), "使っている"), ((FILL, SUB, ""), "同じ表に残る"),
              ((OCHRE_PALE, OCHRE, "9 6"), "別の表に残る"), (("#ffffff", SUB, "9 6"), "残らない")]
    x = 64
    for (fill, stroke, dash), label in legend:
        f.box(x, 476, 40, 28, fill, stroke, sw=2.5, dash=dash, rx=5)
        f.text(x + 52, 499, label, 24, SUB, anchor="start")
        x += 52 + len(label) * 24 + 30
    f.save(HERE / "images" / "soft-delete_concept.svg")


def race_figure():
    """The lost update of the note: A (withdraw) and B (suspend) on member 42."""
    f = Svg(960, 540, "退会と一時停止を同時に走らせた時の順序")
    xs = (330, 500, 670, 840)   # steps 1..4
    f.text(40, 60, "会員 42 の status を 2 つのトランザクションで書き換える", 24, SUB, anchor="start")
    lanes = (("処理 A", "（退会）", 120, ACCENT, PALE),
             ("処理 B", "（一時停止）", 290, OCHRE, OCHRE_PALE))
    for name, sub, y, stroke, fill in lanes:
        f.text(40, y + 52, name, 26, anchor="start")
        f.text(40, y + 86, sub, 24, SUB, anchor="start")
        f.line(220, y + 64, 930, y + 64, stroke, sw=2, dash="3 8")
    steps = ((0, 0, "SELECT で", "有効 を読む"),
             (1, 1, "SELECT で", "有効 を読む"),
             (2, 0, "退会済み に", "更新・追記"),
             (3, 1, "一時停止 に", "更新・追記"))
    for i, lane, l1, l2 in steps:
        _, _, y, stroke, fill = lanes[lane]
        x = xs[i]
        f.box(x - 80, y + 14, 160, 100, fill, stroke)
        f.text(x, y + 56, l1, 24)
        f.text(x, y + 92, l2, 24)
    # A's result after step 4: overwritten by B.
    _, _, ya, _, _ = lanes[0]
    f.box(xs[3] - 80, ya + 14, 160, 100, "#ffffff", SUB, dash="9 6")
    f.text(xs[3], ya + 56, "退会済み", 24, SUB)
    f.text(xs[3], ya + 92, "が消える", 24, SUB)
    f.line(xs[3], 290 + 14, xs[3], ya + 120, RED, sw=3, arrow="red")
    f.line(220, 470, 930, 470, SUB, sw=2, arrow="sub")
    for i, x in enumerate(xs):
        f.line(x, 462, x, 478, SUB, sw=2)
        f.text(x, 512, f"手順 {i + 1}", 24, SUB)
    f.text(40, 478, "時間", 24, SUB, anchor="start")
    f.save(HERE / "images" / "soft-delete_lost_update.svg")


if __name__ == "__main__":
    concept_figure()
    race_figure()
