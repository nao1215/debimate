"""Generate the cover diagram of the Reproducible Builds note.

concept_figure() draws a hand-written SVG (stdlib only). The columns are the
stages 0-5 of lab/build.sh, the rows are the differences between builder A and
B that lab/output.txt shows for stage 0. An ochre cell is a difference that is
still left at that stage. The bottom row is the sha256 comparison of
lab/output.txt: DIFFERENT for stages 0-4, same for stage 5.

Run: python3 content/notes/security/reproducible-builds/figures.py
"""

import re
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
INK, SUB, ACCENT, RED = "#1f1f1f", "#666666", "#7aa6c2", "#e15759"
FILL = "#f2f2f2"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
GREEN, GREEN_PALE = "#8fae86", "#e9f1e6"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"

# (label, the stage that fixes it) in the order build.sh fixes them.
FACTORS = [
    ("gzip の時刻", 1),   # gzip -n
    ("更新時刻", 2),      # --mtime=@SOURCE_DATE_EPOCH
    ("並び順", 3),        # --sort=name
    ("所有者", 4),        # --owner=0 --group=0 --numeric-owner
    ("権限", 5),          # --mode=a=rX,u+w
]


class Svg:
    def __init__(self, width, height, title):
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img"><title>{escape(title)}</title>',
            f'<style>text{{font-family:{FONT};fill:{INK}}}</style>',
            f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        ]

    def text(self, x, y, s, size=24, color=INK, weight="normal", anchor="middle"):
        self.parts.append(
            f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
            f'text-anchor="{anchor}" style="fill:{color}">{escape(s)}</text>')

    def box(self, x, y, w, h, fill, stroke="none", sw=2.5, rx=8):
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')

    def save(self, path):
        path.write_text("\n".join(self.parts + ["</svg>"]) + "\n", encoding="utf-8")


def load_results():
    """Return {stage: True if A and B gave the same sha256} from lab/output.txt."""
    text = (HERE / "lab" / "output.txt").read_text(encoding="utf-8")
    rows = re.findall(r"^stage (\d)\s+A=(\w+)\s+B=(\w+)\s+(\w+)$", text, re.M)
    assert len(rows) == 6, rows
    return {int(s): a == b for s, a, b, _ in rows}


def concept_figure():
    same = load_results()
    f = Svg(960, 540, "段階ごとに残る差の要因と、A と B のハッシュ")
    left, cw, gap = 190, 116, 8          # first column x, column width, gap
    top, rh = 110, 56                    # first factor row y, row height
    cx = [left + i * (cw + gap) + cw / 2 for i in range(6)]

    f.text(left + 3 * (cw + gap) - gap / 2, 44, "固定する項目を 1 つずつ増やす", 26, SUB)
    for i, x in enumerate(cx):
        f.text(x, 92, f"段階 {i}", 24, SUB)

    for r, (label, fixed_at) in enumerate(FACTORS):
        y = top + r * rh
        f.text(left - 18, y + rh / 2 + 8, label, 24, anchor="end")
        for i, x in enumerate(cx):
            left_over = i < fixed_at
            if left_over:
                f.box(x - cw / 2 + 1.5, y + 5.5, cw - 3, rh - 11, OCHRE_PALE, OCHRE, sw=3)
            else:
                f.box(x - cw / 2, y + 4, cw, rh - 8, FILL)

    # Bottom row: does the sha256 of A equal that of B?
    y = top + len(FACTORS) * rh + 22
    f.text(left - 18, y + 44, "ハッシュ", 24, anchor="end")
    for i, x in enumerate(cx):
        ok = same[i]
        f.box(x - cw / 2, y, cw, 68, GREEN_PALE if ok else "#ffffff",
              GREEN if ok else SUB, sw=4 if ok else 2)
        f.text(x, y + 46, "一致" if ok else "不一致", 26 if ok else 24,
               INK if ok else SUB, weight="normal")

    # Legend
    ly = 524
    f.box(191.5, ly - 20.5, 27, 23, OCHRE_PALE, OCHRE, sw=3)
    f.text(230, ly, "残っている差", 24, SUB, anchor="start")
    f.box(420, ly - 22, 30, 26, FILL)
    f.text(460, ly, "固定した", 24, SUB, anchor="start")

    (HERE / "images").mkdir(exist_ok=True)
    f.save(HERE / "images" / "reproducible-builds_concept.svg")


if __name__ == "__main__":
    concept_figure()
