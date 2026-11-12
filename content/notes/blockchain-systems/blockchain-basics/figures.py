"""Generate the figures of the Blockchain Basics note.

concept_figure() draws five participants on a ring, each holding its own copy
of the same block chain (the newest block in the accent color). Participant C
rewrote block 2 in its copy, so that block shifts out of line (pale red with a
red edge, the one failure point) and its link to block 3 turns into a red
dashed line.

chain_figure() draws three blocks, each a header (previous hash, Merkle root,
nonce) over a body of transactions, linked by the previous-hash field. One
transaction in the first block is rewritten (red), so its summary and header
hash change and the link to the next block no longer matches.

fork_figure() draws a chain whose tip split into two blocks found at almost
the same time. The branch that grew longer (more accumulated work) is adopted
and the other block drops out.

Run: python3 content/notes/blockchain-systems/blockchain-basics/figures.py
Needs google-chrome (headless, to render the SVG) and Pillow (to write WebP).
"""

import math
import subprocess
import tempfile
from html import escape
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
INK, SUB, FILL, PALE = "#1f1f1f", "#666666", "#f2f2f2", "#eaf1f5"
ACCENT, RED = "#7aa6c2", "#e15759"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
GREEN, GREEN_PALE = "#8fae86", "#e9f1e6"
RED_PALE = "#fbe3e3"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"


class Svg:
    def __init__(self, width, height, title):
        self.w, self.h = width, height
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
        """Render the SVG with headless Chrome at 2x and store it as WebP."""
        (HERE / "images").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory() as tmp:
            svg, png = Path(tmp) / "fig.svg", Path(tmp) / "fig.png"
            svg.write_text("\n".join(self.parts + ["</svg>"]) + "\n", encoding="utf-8")
            subprocess.run(
                ["google-chrome", "--headless=new", "--disable-gpu", "--hide-scrollbars",
                 "--force-device-scale-factor=2", f"--window-size={self.w},{self.h}",
                 f"--screenshot={png}", svg.as_uri()], check=True, capture_output=True)
            Image.open(png).convert("RGB").save(
                HERE / "images" / name, "WEBP", quality=90, method=6)


def concept_figure():
    f = Svg(960, 540, "参加者がそれぞれ同じブロックの列を複製して持つ")
    cx, cy, rx, ry = 480, 272, 300, 190
    f.raw(f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="none" '
          f'stroke="#dddddd" stroke-width="3"/>')
    f.text(cx, cy - 8, "同じ履歴を", 30, SUB)
    f.text(cx, cy + 32, "各自が複製", 30, SUB)
    names = "12345"
    tampered = 2  # participant 3 rewrote block 2 in its own copy
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
    f.save("blockchain-basics_concept.webp")


def chain_figure():
    f = Svg(1060, 430, "直前のブロックのハッシュ値で繋がるブロック")
    bw, gap, x0, top = 290, 80, 15, 60
    rows = ["前のブロックのハッシュ値", "要約（Merkle root）", "nonce"]
    for k in range(3):
        x = x0 + k * (bw + gap)
        f.text(x + bw / 2, top - 18, f"ブロック {100 + k}", 24, INK)
        # header
        f.box(x, top, bw, 150, PALE, ACCENT, rx=8)
        f.text(x + 14, top + 30, "ブロックヘッダ", 18, SUB, anchor="start")
        for j, r in enumerate(rows):
            bad = k == 0 and j == 1
            y = top + 44 + j * 34
            f.box(x + 12, y, bw - 58, 28, RED_PALE if bad else "#ffffff",
                  RED if bad else "#c3d3dd", sw=2, rx=5)
            f.text(x + 20, y + 20, r, 16, INK, anchor="start")
        # body
        f.box(x, top + 166, bw, 150, FILL, "#cccccc", rx=8)
        f.text(x + 14, top + 196, "トランザクションの並び", 18, SUB, anchor="start")
        for j in range(3):
            bad = k == 0 and j == 1
            y = top + 210 + j * 32
            f.box(x + 12, y, bw - 58, 26, RED_PALE if bad else "#ffffff",
                  RED if bad else "#cccccc", sw=2, rx=5)
            f.text(x + 20, y + 19, "トランザクション " + str(j + 1) + ("（書き換え）" if bad else ""),
                   16, INK, anchor="start")
        # Merkle root arrow: from the body up along the right margin to row 2
        c = RED if k == 0 else SUB
        mx = x + bw - 24
        f.raw(f'<polyline points="{mx},{top + 166} {mx},{top + 92} {x + bw - 42},{top + 92}" '
              f'fill="none" stroke="{c}" stroke-width="2.5" '
              f'marker-end="url(#arrow-{"red" if k == 0 else "sub"})"/>')
        if k:
            # previous-hash link: this block's row 1 points at the previous header
            px = x - gap
            broken = k == 1
            col = RED if broken else ACCENT
            f.line(x + 10, top + 58, px + 4, top + 58, col, sw=3.5,
                   arrow="red" if broken else "accent", dash="6 6" if broken else "")
            f.text(x - gap / 2, top + 22, "ヘッダの", 14, col)
            f.text(x - gap / 2, top + 40, "ハッシュ値", 14, col)
            if broken:
                f.text(x - gap / 2, top + 86, "合わない", 15, RED)
    f.text(530, 410, "トランザクションを書き換えると要約とヘッダのハッシュ値が変わり、"
           "ブロック 101 が持つ値と合わなくなる", 18, RED)
    f.save("blockchain-basics_chain.webp")


def fork_figure():
    f = Svg(960, 310, "末尾が分岐した時に採用される列")
    size, step, y0 = 70, 120, 130
    def blk(x, y, label, fill=PALE, stroke=ACCENT, dash=""):
        f.box(x, y, size, size, fill, stroke, dash=dash, rx=8)
        f.text(x + size / 2, y + size / 2 + 9, label, 24)
    xs = [40 + i * step for i in range(4)]
    for i, x in enumerate(xs[:3]):
        blk(x, y0, str(i + 1))
        if i:
            f.line(x - step + size + 2, y0 + size / 2, x - 4, y0 + size / 2, ACCENT, 3.5)
    # branch
    up, dn = 40, 220
    bx = xs[3]
    f.line(xs[2] + size + 2, y0 + size / 2, bx - 4, up + size / 2, ACCENT, 3.5)
    f.line(xs[2] + size + 2, y0 + size / 2, bx - 4, dn + size / 2, "#bbbbbb", 3.5, dash="6 6")
    blk(bx, up, "4", ACCENT)
    blk(bx + step, up, "5", ACCENT)
    f.line(bx + size + 2, up + size / 2, bx + step - 4, up + size / 2, ACCENT, 3.5)
    blk(bx, dn, "4'", "#f7f7f7", "#bbbbbb", dash="6 5")
    f.text(bx + 2 * step + 10, up + 32, "計算量が大きい列を採用する", 22, INK, anchor="start")
    f.text(bx + 2 * step + 10, up + 62, "（普通は長く伸びた列）", 20, SUB, anchor="start")
    f.text(bx + size + 24, dn + 32, "外れたブロック", 22, SUB, anchor="start")
    f.text(bx + size + 24, dn + 62, "ほぼ同時に見付かった別の候補", 20, SUB, anchor="start")
    f.text(xs[1] + size / 2, y0 - 30, "全員が持つ共通の列", 20, SUB)
    f.save("blockchain-basics_fork.webp")


def split_figure():
    f = Svg(960, 300, "規則を変えた参加者と変えなかった参加者で履歴が分かれる")
    size, step, y0 = 64, 110, 118
    def blk(x, y, label, fill=PALE, stroke=ACCENT):
        f.box(x, y, size, size, fill, stroke, rx=8)
        f.text(x + size / 2, y + size / 2 + 9, label, 22)
    xs = [40 + i * step for i in range(3)]
    for i, x in enumerate(xs):
        blk(x, y0, str(i + 1))
        if i:
            f.line(x - step + size + 2, y0 + size / 2, x - 4, y0 + size / 2, ACCENT, 3.5)
    up, dn = 30, 206
    bx = xs[2] + step
    f.line(xs[2] + size + 2, y0 + size / 2, bx - 4, up + size / 2, ACCENT, 3.5)
    f.line(xs[2] + size + 2, y0 + size / 2, bx - 4, dn + size / 2, OCHRE, 3.5)
    for k in range(3):
        x = bx + k * step
        blk(x, up, "", ACCENT)
        blk(x, dn, "", OCHRE_PALE, OCHRE)
        if k:
            f.line(x - step + size + 2, up + size / 2, x - 4, up + size / 2, ACCENT, 3.5)
            f.line(x - step + size + 2, dn + size / 2, x - 4, dn + size / 2, OCHRE, 3.5)
    tx = bx + 3 * step - 20
    f.text(tx, up + 28, "規則を変えたソフトウェア", 21, INK, anchor="start")
    f.text(tx, up + 56, "を動かす参加者の列", 21, INK, anchor="start")
    f.text(tx, dn + 28, "元の規則のソフトウェア", 21, INK, anchor="start")
    f.text(tx, dn + 56, "を動かす参加者の列", 21, INK, anchor="start")
    f.text(xs[1] + size / 2, y0 - 22, "切り替える前は共通の列", 19, SUB)
    f.text(bx + step + size / 2, y0 + size / 2 + 8, "規則が違うので合流しない", 19, SUB)
    f.save("blockchain-basics_split.webp")


if __name__ == "__main__":
    split_figure()
    concept_figure()
    chain_figure()
    fork_figure()
