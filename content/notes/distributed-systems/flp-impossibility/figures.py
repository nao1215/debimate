"""Generate the FLP note's explanatory SVG (Python stdlib only).

Run: python3 content/notes/distributed-systems/flp-impossibility/figures.py
"""

from html import escape
from pathlib import Path

OUT = Path(__file__).parent / "images"
INK, LINE, BOX, EDGE = "#28343b", "#596b76", "#eaf1f5", "#9cabb5"
NOTE, NOTE_EDGE, MUTED = "#f7f1e5", "#c5b99b", "#5f6b73"


class Svg:
    def __init__(self, width, height, title):
        self.width, self.height = width, height
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img"><title>{escape(title)}</title>',
            '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
            f'markerHeight="7" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" fill="{LINE}"/></marker></defs>',
            f'<style>text{{font-family:"Noto Sans CJK JP","Noto Sans JP",sans-serif;fill:{INK}}}</style>',
            f'<rect width="{width}" height="{height}" fill="white"/>',
        ]

    def add(self, s):
        self.parts.append(s)

    def text(self, x, y, s, size=14, anchor="start", fill=INK, weight="normal"):
        self.add(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" '
                 f'fill="{fill}" font-weight="{weight}">{escape(s)}</text>')

    def line(self, x1, y1, x2, y2, color=LINE, width=1.5, dash=None, arrow=False):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        a = ' marker-end="url(#arrow)"' if arrow else ""
        self.add(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
                 f'stroke-width="{width}"{d}{a}/>')

    def rect(self, x, y, w, h, fill=BOX, stroke=EDGE, rx=6):
        self.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}"/>')

    def save(self, name):
        OUT.mkdir(exist_ok=True)
        (OUT / name).write_text("\n".join(self.parts + ["</svg>"]) + "\n", encoding="utf-8")


def slow_or_crashed():
    s = Svg(800, 330, "From p0, a crashed p2 and a slow p2 look the same until the timeout")
    x0, x1 = 230, 760           # time axis: t = 0 .. 200 ms
    tx = lambda t: x0 + (x1 - x0) * t / 200
    timeout = tx(100)
    # p0's view before the timeout is identical in both worlds
    s.rect(x0, 40, timeout - x0, 270, fill=NOTE, stroke=NOTE_EDGE)
    s.text((x0 + timeout) / 2, 30, "p0 sees the same thing: nothing from p2", 13, "middle")
    s.line(timeout, 36, timeout, 312, INK, 1.5, "6 4")
    s.text(timeout + 6, 30, "timeout (100 ms)", 13)

    worlds = [
        (50, ("World A:", "p2 crashed"), False),
        (180, ("World B:", "p2 is only slow"), True),
    ]
    for top, label, slow in worlds:
        y_p0, y_p2 = top + 40, top + 90
        s.text(20, top + 62, label[0], 14, weight="bold")
        s.text(20, top + 82, label[1], 14, weight="bold")
        for y, name in ((y_p0, "p0"), (y_p2, "p2")):
            s.text(x0 - 14, y + 5, name, 14, "end")
            s.line(x0, y, x1, y, EDGE, 2)
        if slow:
            s.line(tx(10), y_p2, tx(150), y_p0 + 4, LINE, 1.8, arrow=True)
            s.text(tx(150) + 8, y_p0 + 20, "value arrives at 150 ms", 13, fill=MUTED)
        else:
            cx, cy = tx(10), y_p2
            s.line(cx - 7, cy - 7, cx + 7, cy + 7, INK, 2.5)
            s.line(cx - 7, cy + 7, cx + 7, cy - 7, INK, 2.5)
            s.text(cx + 14, cy + 22, "stops at 10 ms, sends nothing", 13, fill=MUTED)
            s.line(tx(10), cy + 0.1, x1, cy + 0.1, "white", 3)
            s.line(tx(10), cy, x1, cy, EDGE, 2, "3 5")
    s.save("slow-or-crashed.svg")


if __name__ == "__main__":
    slow_or_crashed()
