"""Generate the figures of the metamorphic-contract note.

Run: python3 figures.py  -> images/*.webp
Needs google-chrome (headless, to render the SVG) and Pillow (to write WebP).
The addresses come from ../ethereum-address/lab/output/summary.txt.
"""

import subprocess
import tempfile
from html import escape
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
INK, SUB, FILL = "#1f1f1f", "#666666", "#f2f2f2"
BLUE, BLUE_PALE = "#7aa6c2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
RED = "#e15759"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"
MONO = "'DejaVu Sans Mono','Menlo','Consolas',monospace"


class Svg:
    def __init__(self, title, w=960, h=540):
        self.w, self.h = w, h
        self.p = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}" role="img"><title>{escape(title)}</title>',
            f'<style>text{{font-family:{FONT};fill:{INK}}} .sub{{fill:{SUB}}} .mono{{font-family:{MONO}}}</style>',
            f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
            '<defs>'
            f'<marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" '
            f'orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{INK}"/></marker>'
            f'<marker id="arrs" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
            f'orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{SUB}"/></marker>'
            '</defs>',
        ]

    def text(self, x, y, s, size=22, anchor="middle", cls=""):
        c = f' class="{cls}"' if cls else ""
        self.p.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}"{c}>{escape(s)}</text>')

    def lines(self, x, cy, rows, size=22, anchor="middle", cls="", gap=1.35):
        """Several lines centred vertically on cy."""
        top = cy - (len(rows) - 1) * size * gap / 2 + size * 0.36
        for i, s in enumerate(rows):
            self.text(x, top + i * size * gap, s, size, anchor, cls)

    def box(self, x, y, bw, bh, stroke, fill, rx=8, dash=False, sw=2):
        d = ' stroke-dasharray="8 6"' if dash else ""
        self.p.append(f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" rx="{rx}" fill="{fill}" '
                      f'stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def line(self, x1, y1, x2, y2, color=INK, width=2.5, arrow="arr", dash=False):
        m = f' marker-end="url(#{arrow})"' if arrow else ""
        d = ' stroke-dasharray="7 6"' if dash else ""
        self.p.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
                      f'stroke-width="{width}"{m}{d}/>')

    def cross(self, cx, cy, r=13):
        for a, b in ((-r, r), (r, -r)):
            self.p.append(f'<line x1="{cx - r}" y1="{cy + a}" x2="{cx + r}" y2="{cy + b}" '
                          f'stroke="{RED}" stroke-width="5"/>')

    def save(self, name):
        svg_text = "\n".join(self.p + ["</svg>"]) + "\n"
        with tempfile.TemporaryDirectory() as tmp:
            svg, png = Path(tmp) / "fig.svg", Path(tmp) / "fig.png"
            svg.write_text(svg_text, encoding="utf-8")
            subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--hide-scrollbars",
                            "--force-device-scale-factor=2", f"--window-size={self.w},{self.h}",
                            f"--screenshot={png}", svg.as_uri()], check=True, capture_output=True)
            Image.open(png).convert("RGB").save(HERE / "images" / name, "WEBP", quality=90, method=6)


def concept_figure():
    """The Deployer address is fixed by CREATE2 and its nonce restarts, so the CREATE target repeats."""
    s = Svg("CREATE2 で Deployer のアドレスが固定され、消して作り直すと nonce が 1 に戻るので、CREATE の作成先も同じになる")
    s.box(30, 90, 170, 100, SUB, FILL)
    s.text(115, 148, "ファクトリ", 22)
    s.line(204, 140, 356, 140)
    s.text(280, 118, "1. CREATE2", 18, cls="sub")
    s.text(280, 172, "salt・initcode 固定", 16, cls="sub")
    s.box(360, 90, 220, 100, BLUE, BLUE_PALE)
    s.text(470, 132, "Deployer", 24)
    s.text(470, 166, "アドレスは毎回同じ", 18, cls="sub")
    s.line(584, 140, 736, 140)
    s.text(660, 118, "2・5. CREATE", 18, cls="sub")
    s.text(660, 172, "Deployer・nonce 1", 16, cls="sub")
    s.box(740, 90, 190, 100, INK, "#ffffff", sw=2.5)
    s.text(835, 132, "0xCB8956e6…", 20, cls="mono")
    s.text(835, 166, "置き場所", 18, cls="sub")
    # destroy and recreate loop under the Deployer
    s.box(290, 290, 170, 100, RED, "#fbe3e3")
    s.lines(375, 340, ["3. Deployer を消す", "nonce も消える"], 18)
    s.box(480, 290, 170, 100, BLUE, BLUE_PALE)
    s.lines(565, 340, ["4. 作り直す", "nonce は 1 から"], 19)
    s.line(420, 194, 380, 284, SUB, 2, arrow="arrs")
    s.line(462, 340, 476, 340, SUB, 2, arrow="arrs")
    s.line(560, 286, 520, 196, SUB, 2, arrow="arrs")
    # what lands at the target, first and second time
    s.line(835, 194, 835, 226, SUB, 2, arrow="arrs")
    s.box(740, 230, 190, 60, BLUE, BLUE_PALE)
    s.text(835, 268, "2. V1 を置く", 20)
    s.line(835, 294, 835, 316, SUB, 2, arrow="arrs")
    s.box(740, 320, 190, 50, RED, "#fbe3e3")
    s.text(835, 353, "3. V1 を消す", 19)
    s.line(835, 374, 835, 396, SUB, 2, arrow="arrs")
    s.box(740, 400, 190, 60, OCHRE, OCHRE_PALE)
    s.text(835, 438, "5. V2 を置く", 20)
    s.text(30, 510, "2024 年 3 月の Cancun 以降は、手順 3 でアカウントが消えず、手順 4 が失敗する", 18, "start", "sub")
    s.save("metamorphic-contract_concept.webp")


def redeploy_figure():
    """What sits at the first target address after each step, Shanghai vs Cancun."""
    s = Svg("Shanghai では同じアドレスに V2 が置かれ、Cancun 以降は V1 が残る")
    cols = [(230, "1〜2 作る"), (480, "3 消す"), (730, "4〜5 作り直す")]
    cw, ch = 200, 110
    for x, label in cols:
        s.text(x + cw / 2, 50, label, 22, cls="sub")
    s.text(30, 92, "0xCB8956e6… にあるコード", 22, "start", "sub")
    rows = [
        (120, "Shanghai", [("V1", "version() = 1", BLUE_PALE, BLUE, False),
                            ("空", "0 バイト", "#ffffff", SUB, True),
                            ("V2", "version() = 2", OCHRE_PALE, OCHRE, False)]),
        (300, "Cancun 以降", [("V1", "version() = 1", BLUE_PALE, BLUE, False),
                              ("V1 のまま", "218 バイト", BLUE_PALE, BLUE, False),
                              ("V1 のまま", "version() = 1", BLUE_PALE, BLUE, False)]),
    ]
    for top, name, cells in rows:
        s.text(30, top + ch / 2 + 9, name, 24, "start")
        for i, ((x, _), (main, sub, fill, stroke, dash)) in enumerate(zip(cols, cells)):
            s.box(x, top, cw, ch, stroke, fill, dash=dash)
            s.text(x + cw / 2, top + 48, main, 24)
            s.text(x + cw / 2, top + 84, sub, 20, cls="sub")
            if i < 2:
                s.line(x + cw + 6, top + ch / 2, cols[i + 1][0] - 8, top + ch / 2)
    s.cross(632, 452, 12)
    s.text(930, 461, "Deployer を作り直せない", 22, "end", "sub")
    s.text(930, 500, "V2 は 0x673a327D… へ", 22, "end", "sub")
    s.save("metamorphic-contract_redeploy.webp")


if __name__ == "__main__":
    (HERE / "images").mkdir(exist_ok=True)
    concept_figure()
    redeploy_figure()
