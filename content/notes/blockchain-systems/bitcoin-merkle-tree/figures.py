"""Generate the cover figure of the Bitcoin Merkle Tree note.

Run: python3 figures.py  -> images/bitcoin-merkle-tree_concept.webp

The figure is built as SVG text here (stdlib only), rendered by headless
Chrome at 2x and saved as WebP (Pillow). Only the WebP file is kept in images/.

concept_figure() draws a phone that keeps only block headers on the left and
the Merkle tree of an 8-transaction block on the right. To show that Tx2 is in
the block, only the sibling hashes on the path (ochre) are sent; the phone
computes the path nodes (accent) up to the root in one of its headers, and the
other hashes (gray) are never sent.

The figures of the duplication and 64-byte weaknesses moved to
../bitcoin-merkle-tree-attacks/figures.py.
"""

from html import escape
from pathlib import Path
import subprocess
import tempfile

from PIL import Image

HERE = Path(__file__).resolve().parent
INK, SUB, FILL, PALE = "#1f1f1f", "#666666", "#f2f2f2", "#eaf1f5"
ACCENT, RED = "#7aa6c2", "#e15759"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
GREEN, GREEN_PALE = "#8fae86", "#e9f1e6"
RED_PALE = "#fbe3e3"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"


def render(svg_text, w, h, name):
    """SVG text -> PNG (headless Chrome, 2x) -> images/<name> (WebP)."""
    with tempfile.TemporaryDirectory() as tmp:
        svg, png = Path(tmp) / "fig.svg", Path(tmp) / "fig.png"
        svg.write_text(svg_text, encoding="utf-8")
        subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--hide-scrollbars",
                        "--force-device-scale-factor=2", f"--window-size={w},{h}",
                        f"--screenshot={png}", svg.as_uri()], check=True, capture_output=True)
        (HERE / "images").mkdir(exist_ok=True)
        Image.open(png).convert("RGB").save(HERE / "images" / name, "WEBP", quality=90, method=6)


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
        render("\n".join(self.parts + ["</svg>"]) + "\n", self.w, self.h, name)

GRAY = "#dddddd"


def concept_figure():
    f = Svg(960, 540, "ヘッダだけを持つ端末が、少数の兄弟ハッシュで包含を確かめる")

    # Left: the phone keeps only the chain of 80-byte headers.
    f.text(135, 62, "携帯端末", 26, weight="normal")
    f.box(50, 84, 170, 380, FILL, SUB, sw=2.5, rx=24)
    strip_top, sh, sg = 112, 36, 12
    mine = 3
    for k in range(6):
        y = strip_top + k * (sh + sg)
        hit = k == mine
        f.box(70, y, 130, sh, ACCENT if hit else PALE, ACCENT, sw=2, rx=4)
        if hit:
            f.text(135, y + 27, "ルート", 24)
    f.text(135, 440, "ヘッダだけ", 24, SUB)

    # Right: the full block on another participant, as a Merkle tree.
    f.text(615, 62, "ブロック全体を持つ参加者", 26, weight="normal")
    f.box(290, 84, 650, 380, "#ffffff", SUB, sw=2.5, rx=16)
    ys = [404, 316, 228, 140]
    xs = [[330 + i * 80 for i in range(8)]]
    while len(xs[-1]) > 1:
        prev = xs[-1]
        xs.append([(prev[i] + prev[i + 1]) / 2 for i in range(0, len(prev), 2)])
    target = 2
    path = [target >> lv for lv in range(4)]
    for lv in range(1, 4):
        for i, x in enumerate(xs[lv]):
            for c in (2 * i, 2 * i + 1):
                on = path[lv] == i and path[lv - 1] == c
                f.line(x, ys[lv] + 20, xs[lv - 1][c], ys[lv - 1] - 20,
                       ACCENT if on else "#c8c8c8", sw=5 if on else 3)
    for lv in range(4):
        for i, x in enumerate(xs[lv]):
            if path[lv] == i:
                fill = ACCENT
            elif lv < 3 and path[lv] ^ 1 == i:
                fill = OCHRE
            else:
                fill = GRAY
            w = 92 if lv == 3 else 56
            f.box(x - w / 2, ys[lv] - 20, w, 40, fill, rx=6, sw=0)
    f.text(xs[0][target], ys[0] + 9, "Tx2", 24)
    f.text(xs[3][0], ys[3] + 9, "ルート", 24)

    # The root of the tree is the root in one of the phone's headers.
    y = strip_top + mine * (sh + sg) + sh / 2
    f.raw(f'<path d="M{xs[3][0] - 50},{ys[3]} C 420,{ys[3]} 330,{y} 206,{y}" '
          f'fill="none" stroke="{ACCENT}" stroke-width="4" '
          f'stroke-dasharray="8 7" marker-end="url(#arrow-accent)"/>')

    legend = [(OCHRE, "証明として渡る"), (ACCENT, "端末が計算"), (GRAY, "渡らない")]
    x = 56
    for color, label in legend:
        f.box(x, 494, 30, 30, color, rx=4, sw=0)
        f.text(x + 42, 518, label, 24, anchor="start")
        x += 60 + 26 * len(label) + 40
    f.save("bitcoin-merkle-tree_concept.webp")


if __name__ == "__main__":
    concept_figure()
