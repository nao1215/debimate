"""Generate the cover diagram of the 2PC note (stdlib only).

Each participant is a band along a time axis. The hatched part runs from the
yes vote to the arrival of the decision: the participant holds its locks and
can neither commit nor abort on its own. Top: the decision arrives (A first,
then B). Bottom: the coordinator stops before deciding, so the hatched part
never ends.

Run: python3 content/notes/distributed-systems/two-phase-commit/figures.py
"""

from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
HATCH = (
    '<pattern id="hatch" patternUnits="userSpaceOnUse" width="14" height="14" '
    'patternTransform="rotate(45)"><rect width="14" height="14" fill="#f8eed8"/>'
    '<rect width="5" height="14" fill="#d4a24c"/></pattern>')
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"
INK, SUB, ACCENT, RED = "#1f1f1f", "#666666", "#7aa6c2", "#e15759"
FILL, PALE = "#f2f2f2", "#eaf1f5"
GREEN, GREEN_PALE = "#7aa6c2", "#e9f1e6"


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


X0, X1 = 210, 936  # time axis
YES = {"A": 330, "B": 360}
DECIDE = 560
ARRIVE = {"A": 600, "B": 660}


def band(f, y, x0, x1, kind, label=""):
    h = 40
    if kind == "work":
        f.box(x0, y, x1 - x0, h, FILL, SUB, sw=2, rx=4)
    elif kind == "doubt":
        f.box(x0, y, x1 - x0, h, "url(#hatch)", "#d4a24c", sw=2.5, rx=4)
    else:
        f.box(x0, y, x1 - x0, h, GREEN, GREEN, sw=2, rx=4)
    if label:
        f.text((x0 + x1) / 2, y + 29, label, 24, INK)


def panel(f, top, title, stopped):
    f.text(24, top + 26, title, 26, weight="normal", anchor="start")
    cy = top + 76
    f.text(196, cy + 8, "コーディネータ", 24, anchor="end")
    f.text(196, cy + 58, "参加者 A", 24, anchor="end")
    f.text(196, cy + 116, "参加者 B", 24, anchor="end")
    end = 470 if stopped else X1
    f.line(X0, cy, end, cy, SUB, sw=6)
    f.raw(f'<circle cx="290" cy="{cy}" r="8" fill="{SUB}"/>')
    f.text(290, cy - 16, "prepare", 24, SUB)
    if stopped:
        f.cross(end + 18, cy, 14, RED, sw=6)
        f.text(end + 46, cy + 8, "停止", 24, RED, weight="normal", anchor="start")
    else:
        f.raw(f'<circle cx="{DECIDE}" cy="{cy}" r="8" fill="{GREEN}"/>')
        f.text(DECIDE, cy - 16, "決定", 24, SUB)
    for name, dy in (("A", 38), ("B", 96)):
        y = cy + dy
        band(f, y, X0, YES[name], "work")
        if stopped:
            band(f, y, YES[name], X1, "doubt")
        else:
            band(f, y, YES[name], ARRIVE[name], "doubt")
            band(f, y, ARRIVE[name], X1, "done", "確定")
    if stopped:
        f.text(X1, cy + 8, "参加者は待ち続ける →", 24, INK, weight="normal", anchor="end")


def concept_figure():
    f = Svg(960, 540, "2PC で yes の後に決定を待つ区間", HATCH)
    panel(f, 6, "決定が届く場合", stopped=False)
    panel(f, 252, "決定の前にコーディネータが停止した場合", stopped=True)
    f.box(24, 504, 60, 26, "url(#hatch)", "#d4a24c", sw=2.5, rx=4)
    f.text(96, 526, "yes を返してから決定が届くまで（ロックを保持）", 24, anchor="start")
    f.save(HERE / "images" / "two-phase-commit_concept.svg")


if __name__ == "__main__":
    concept_figure()
