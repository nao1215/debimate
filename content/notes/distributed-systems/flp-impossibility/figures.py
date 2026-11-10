"""Generate the FLP note's explanatory SVGs (Python stdlib only).

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
        s.text(20, top + 62, label[0], 14, weight="normal")
        s.text(20, top + 82, label[1], 14, weight="normal")
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


# Approved palette for the figures added on 2026-11-10.
BLUE, BLUE_PALE = "#7aa6c2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
BLACK, GRAY, NEUTRAL = "#1f1f1f", "#666666", "#f2f2f2"


def bivalent_initial():
    """Lemma 2: lining up initial values one process at a time puts a 0-valent next to a 1-valent."""
    s = Svg(960, 540, "初期値を 1 台ずつ変えて並べると、0-valent と 1-valent が隣り合う")
    s.parts[2] = (f"<style>text{{font-family:'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',"
                  f"sans-serif;fill:{BLACK}}}</style>")
    s.text(40, 56, "仮定：bivalent な初期状態が無い", 26, fill=GRAY)
    states = ["(0, 0, 0)", "(1, 0, 0)", "(1, 1, 0)", "(1, 1, 1)"]
    xs = [40, 290, 540, 790]
    w, top, h = 130, 140, 90
    for i, (x, label) in enumerate(zip(xs, states)):
        zero = i < 2
        s.rect(x, top, w, h, fill=BLUE_PALE if zero else OCHRE_PALE,
               stroke=BLUE if zero else OCHRE, rx=8)
        s.text(x + w / 2, top + 55, label, 26, "middle")
        s.text(x + w / 2, top + h + 40, "0-valent" if zero else "1-valent", 24, "middle", fill=GRAY)
        if i:
            x_prev = xs[i - 1] + w
            s.line(x_prev + 10, top + h / 2, x - 10, top + h / 2, GRAY, 2.5, arrow=True)
            s.text((x_prev + x) / 2, top + h / 2 - 16, f"p{i - 1} を 1 に", 24, "middle", fill=GRAY)
    # The adjacent pair that differs only in p1.
    a, b = xs[1], xs[2] + w
    s.line(a, 330, a, 345, BLACK, 2)
    s.line(a, 345, b, 345, BLACK, 2)
    s.line(b, 330, b, 345, BLACK, 2)
    s.text((a + b) / 2, 384, "隣り合う 2 つの違いは p1 の初期値だけ", 26, "middle")
    s.rect(130, 420, 700, 96, fill=NEUTRAL, stroke=GRAY, rx=8)
    s.text(480, 458, "p1 が一切動かない実行では、残りの 2 台に", 24, "middle")
    s.text(480, 494, "2 つは区別できず、同じ値に決まる（仮定と矛盾）", 24, "middle")
    s.save("flp_bivalent_initial.svg")


if __name__ == "__main__":
    slow_or_crashed()
    bivalent_initial()
