"""Generate the FLP note's explanatory figures.

Run: python3 content/notes/distributed-systems/flp-impossibility/figures.py  -> images/*.webp
Needs google-chrome (headless, to render the SVG) and Pillow (to write WebP).
"""

import subprocess
import tempfile
from html import escape
from pathlib import Path

from PIL import Image

OUT = Path(__file__).resolve().parent / "images"
# Approved palette for the figures added on 2026-11-10.
BLUE, BLUE_PALE = "#7aa6c2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
BLACK, GRAY, NEUTRAL = "#1f1f1f", "#666666", "#f2f2f2"
EDGE = "#9cabb5"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"
MONO = "'DejaVu Sans Mono','Menlo','Consolas',monospace"


class Svg:
    def __init__(self, width, height, title):
        self.width, self.height = width, height
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img"><title>{escape(title)}</title>',
            '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
            f'markerHeight="7" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" fill="{GRAY}"/></marker>'
            '<marker id="arrow-ink" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
            f'markerHeight="7" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" fill="{BLACK}"/></marker></defs>',
            f'<style>text{{font-family:{FONT};fill:{BLACK}}} .mono{{font-family:{MONO}}}</style>',
            f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        ]

    def add(self, s):
        self.parts.append(s)

    def text(self, x, y, s, size=24, anchor="start", fill=BLACK, cls=""):
        c = f' class="{cls}"' if cls else ""
        self.add(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" '
                 f'style="fill:{fill}"{c}>{escape(s)}</text>')

    def line(self, x1, y1, x2, y2, color=GRAY, width=2, dash=None, arrow=False, ink=False):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        a = f' marker-end="url(#{"arrow-ink" if ink else "arrow"})"' if arrow else ""
        self.add(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
                 f'stroke-width="{width}"{d}{a}/>')

    def rect(self, x, y, w, h, fill=BLUE_PALE, stroke=EDGE, rx=8, width=2):
        self.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" '
                 f'stroke="{stroke}" stroke-width="{width}"/>')

    def save(self, name):
        OUT.mkdir(exist_ok=True)
        svg_text = "\n".join(self.parts + ["</svg>"]) + "\n"
        with tempfile.TemporaryDirectory() as tmp:
            svg, png = Path(tmp) / "fig.svg", Path(tmp) / "fig.png"
            svg.write_text(svg_text, encoding="utf-8")
            subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--hide-scrollbars",
                            "--force-device-scale-factor=2", f"--window-size={self.width},{self.height}",
                            f"--screenshot={png}", svg.as_uri()], check=True, capture_output=True)
            Image.open(png).convert("RGB").save(OUT / name, "WEBP", quality=90, method=6)


def slow_or_crashed():
    s = Svg(960, 440, "p0 から見ると、止まった p2 と遅い p2 は timeout まで同じに見える")
    x0, x1 = 250, 920           # time axis: t = 0 .. 200 ms
    tx = lambda t: x0 + (x1 - x0) * t / 200
    timeout = tx(100)
    # p0's view before the timeout is identical in both worlds
    s.rect(x0, 60, timeout - x0, 360, fill=OCHRE_PALE, stroke=OCHRE, rx=4)
    s.text((x0 + timeout) / 2, 44, "p0 の観測は同じ", 22, "middle")
    s.text((x0 + timeout) / 2, 92, "p2 から何も届かない", 20, "middle", GRAY)
    s.line(timeout, 54, timeout, 422, BLACK, 2, "6 4")
    s.text(timeout + 10, 44, "timeout（100 ms）", 22)

    worlds = [
        (70, ("世界 A：", "p2 が止まった"), False),
        (245, ("世界 B：", "p2 が遅いだけ"), True),
    ]
    for top, label, slow in worlds:
        y_p0, y_p2 = top + 50, top + 120
        s.text(20, top + 80, label[0], 24)
        s.text(20, top + 112, label[1], 24)
        for y, name in ((y_p0, "p0"), (y_p2, "p2")):
            s.text(x0 - 16, y + 8, name, 24, "end")
            s.line(x0, y, x1, y, EDGE, 2.5)
        if slow:
            s.line(tx(10), y_p2, tx(150), y_p0 + 4, GRAY, 2.5, arrow=True)
            s.text(tx(150) + 10, y_p0 + 34, "150 ms で値が届く", 22, fill=GRAY)
        else:
            cx, cy = tx(10), y_p2
            s.line(tx(10), cy, x1, cy, "#ffffff", 4)
            s.line(tx(10), cy, x1, cy, EDGE, 2.5, "3 6")
            s.line(cx - 9, cy - 9, cx + 9, cy + 9, BLACK, 3)
            s.line(cx - 9, cy + 9, cx + 9, cy - 9, BLACK, 3)
            s.text(cx + 18, cy + 36, "10 ms で停止", 22, fill=GRAY)
    s.save("slow-or-crashed.webp")


def bivalent_initial():
    """Lemma 2: lining up initial values one process at a time puts a 0-valent next to a 1-valent."""
    s = Svg(960, 540, "初期値を 1 台ずつ変えて並べると、0-valent と 1-valent が隣り合う")
    s.text(40, 56, "仮定：bivalent な初期状態が無い", 26, fill=GRAY)
    states = ["(0, 0, 0)", "(1, 0, 0)", "(1, 1, 0)", "(1, 1, 1)"]
    xs = [40, 290, 540, 790]
    w, top, h = 130, 140, 90
    for i, (x, label) in enumerate(zip(xs, states)):
        zero = i < 2
        s.rect(x, top, w, h, fill=BLUE_PALE if zero else OCHRE_PALE,
               stroke=BLUE if zero else OCHRE)
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
    s.rect(130, 420, 700, 96, fill=NEUTRAL, stroke=GRAY)
    s.text(480, 458, "p1 が一切動かない実行では、残りの 2 台に", 24, "middle")
    s.text(480, 494, "2 つは区別できず、同じ値に決まる（仮定と矛盾）", 24, "middle")
    s.save("flp_bivalent_initial.webp")


def adversary_round():
    """One round chosen by the lab's adversary from x = (0, 1, 1); it comes back to (0, 1, 1).

    Matches flp_lab.adversary((0, 1, 1)): first1 = (1, 0, 1), first2 = (1, 2, 0).
    """
    s = Svg(960, 640, "adversary が選ぶ 1 ラウンド。p2 から p0 への提案 1 を遅らせると、推定値は (0, 1, 1) に戻る")
    ys = {0: 170, 1: 300, 2: 430}
    xa, xm, xb = 120, 480, 840        # columns: estimate / proposal / next estimate
    # Column headings
    s.text(xa, 60, "推定値", 24, "middle")
    s.text(xm, 60, "提案", 24, "middle")
    s.text(xb, 60, "次の推定値", 24, "middle")
    s.text(300, 104, "段階 1：推定値を送る", 20, "middle", GRAY)
    s.text(660, 104, "段階 2：提案を送る", 20, "middle", GRAY)
    est = {0: "0", 1: "1", 2: "1"}
    prop = {0: "?", 1: "?", 2: "1"}
    nxt = {0: "0", 1: "1", 2: "1"}
    for i, y in ys.items():
        for x, v in ((xa, est[i]), (xm, prop[i]), (xb, nxt[i])):
            one = v == "1"
            s.rect(x - 56, y - 34, 112, 68, fill=OCHRE_PALE if one else (BLUE_PALE if v == "0" else NEUTRAL),
                   stroke=OCHRE if one else (BLUE if v == "0" else GRAY))
            s.text(x - 46, y - 12, f"p{i}", 18, fill=GRAY)
            s.text(x + 8, y + 12, v, 30, "middle", cls="mono")
    # Messages delivered first (solid) and delayed past the round (dashed).
    def msg(src_x, src, dst_x, dst, delayed):
        y1, y2 = ys[src], ys[dst]
        if delayed:
            s.line(src_x + 60, y1, dst_x - 64, y2, "#b5b5b5", 2, "7 6", arrow=True)
        else:
            s.line(src_x + 60, y1, dst_x - 64, y2, BLACK, 2.5, arrow=True, ink=True)
    # Stage 1: first1 = (1, 0, 1) -> p0 hears p1, p1 hears p0, p2 hears p1.
    first1 = {0: 1, 1: 0, 2: 1}
    first2 = {0: 1, 1: 2, 2: 0}
    for dst in range(3):
        msg(xa, first1[dst], xm, dst, False)
        msg(xm, first2[dst], xb, dst, False)
    # The one message the adversary holds back: p2's proposal 1 to p0.
    msg(xm, 2, xb, 0, True)
    s.text(500, 528, "p2 から p0 への提案 1 は遅れて、ラウンドの後に届く（捨てられる）", 20, "middle", GRAY)
    s.line(200, 568, 250, 568, BLACK, 2.5, arrow=True, ink=True)
    s.text(260, 576, "先に届いたメッセージ（自分の値は省略）", 20)
    s.line(200, 608, 250, 608, "#b5b5b5", 2, "7 6", arrow=True)
    s.text(260, 616, "遅れた決め手の 1 通（他の遅れたメッセージは省略）", 20)
    s.save("flp_adversary_round.webp")


if __name__ == "__main__":
    slow_or_crashed()
    bivalent_initial()
    adversary_round()
