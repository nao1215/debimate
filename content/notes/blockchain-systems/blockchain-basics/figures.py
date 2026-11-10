"""Generate the cover figure of the Blockchain Basics note (Python stdlib only).

concept_figure() draws five participants on a ring, each holding its own copy
of the same block chain (the newest block in the accent color). Participant C
rewrote block 2 in its copy, so that block shifts out of line (pale red with a
red edge, the one failure point) and its link to block 3 turns into a red
dashed line.

Run: python3 content/notes/blockchain-systems/blockchain-basics/figures.py
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

import math


def concept_figure():
    f = Svg(960, 540, "参加者がそれぞれ同じブロックの列を複製して持つ")
    cx, cy, rx, ry = 480, 272, 300, 190
    f.raw(f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="none" '
          f'stroke="#dddddd" stroke-width="3"/>')
    f.text(cx, cy - 8, "同じ履歴を", 30, SUB)
    f.text(cx, cy + 32, "各自が複製", 30, SUB)
    names = "ABCDE"
    tampered = 2  # participant C rewrote block 2 in its own copy
    size, step, r = 56, 88, 32
    for i, name in enumerate(names):
        ang = math.radians(-90 + 72 * i)
        px, py = cx + rx * math.cos(ang), cy + ry * math.sin(ang)
        x0 = px - 147
        f.box(x0 - 8, py - 40, 326, 80, "#ffffff", rx=12)
        f.raw(f'<circle cx="{x0 + r}" cy="{py}" r="{r}" fill="{FILL}" '
              f'stroke="{SUB}" stroke-width="2.5"/>')
        f.text(x0 + r, py + 10, name, 28)
        bx = x0 + 2 * r + 14
        for k in range(3):
            x = bx + k * step
            bad = i == tampered and k == 1
            dy = 16 if bad else 0
            if k:
                broken = i == tampered and k == 2
                f.line(x - step + size + 2, py, x - 2, py,
                       RED if broken else ACCENT, sw=4,
                       dash="5 6" if broken else "")
            fill = RED_PALE if bad else (ACCENT if k == 2 else PALE)
            f.box(x, py - size / 2 + dy, size, size, fill,
                  RED if bad else ACCENT, rx=6)
        if i == tampered:
            f.text(px + 20, py + 80, "書き換えた複製だけ食い違う", 26, INK)
    f.save("blockchain-basics_concept.svg")


if __name__ == "__main__":
    concept_figure()
