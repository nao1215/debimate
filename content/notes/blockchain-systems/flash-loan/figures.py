"""Generate the figures of the Flash Loan note.

The figures build SVG text here, render it with headless Chrome at 2x and
save WebP (Pillow). Only WebP files are kept in images/.

Run: python3 content/notes/blockchain-systems/flash-loan/figures.py
"""

import subprocess
import tempfile
from html import escape
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
INK, SUB, ACCENT, RED = "#1f1f1f", "#666666", "#7aa6c2", "#e15759"
FILL, PALE = "#f2f2f2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
GREEN, GREEN_PALE = "#8fae86", "#e9f1e6"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"


def to_webp(png, name):
    (HERE / "images").mkdir(exist_ok=True)
    Image.open(png).convert("RGB").save(HERE / "images" / name, "WEBP", quality=90, method=6)


def render(svg_text, w, h, name):
    """SVG text -> PNG (headless Chrome, 2x) -> images/<name> (WebP)."""
    with tempfile.TemporaryDirectory() as tmp:
        svg, png = Path(tmp) / "fig.svg", Path(tmp) / "fig.png"
        svg.write_text(svg_text, encoding="utf-8")
        subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--hide-scrollbars",
                        "--force-device-scale-factor=2", f"--window-size={w},{h}",
                        f"--screenshot={png}", svg.as_uri()], check=True, capture_output=True)
        to_webp(png, name)


class Svg:
    """A tiny hand-written SVG builder (white background)."""

    def __init__(self, title, width=960, height=540):
        self.w, self.h = width, height
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img"><title>{escape(title)}</title>',
            f'<style>text{{font-family:{FONT};fill:{INK}}}</style>',
            '<defs>'
            + "".join(
                f'<marker id="arrow-{name}" viewBox="0 0 10 10" refX="9" refY="5" '
                f'markerWidth="4" markerHeight="4" orient="auto">'
                f'<path d="M0,0 L10,5 L0,10 z" fill="{color}"/></marker>'
                for name, color in (("sub", SUB), ("accent", ACCENT), ("ochre", OCHRE)))
            + '</defs>',
            f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        ]

    def text(self, x, y, s, size=24, color=INK, anchor="middle"):
        self.parts.append(
            f'<text x="{x}" y="{y}" font-size="{size}" '
            f'text-anchor="{anchor}" style="fill:{color}">{escape(s)}</text>')

    def box(self, x, y, w, h, fill, stroke="none", sw=2.5, dash="", rx=10):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def circle(self, cx, cy, r, fill, stroke="none", sw=2.5):
        self.parts.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="{sw}"/>')

    def line(self, x1, y1, x2, y2, color, sw=4, arrow=None, dash=""):
        m = f' marker-end="url(#arrow-{arrow})"' if arrow else ""
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
            f'stroke-width="{sw}" stroke-linecap="round"{d}{m}/>')

    def save(self, name):
        render("\n".join(self.parts + ["</svg>"]) + "\n", self.w, self.h, name)


def concept_figure():
    """One transaction: borrow, use, repay. If repayment fails, everything is undone."""
    f = Svg("1 つのトランザクションの中で、借りる・使う・手数料を付けて返す。返せなければトランザクション全体が失敗し、"
            "借りる前の状態に戻る", 960, 430)
    f.box(30, 60, 900, 190, "#ffffff", SUB, sw=2.5, dash="10 7", rx=14)
    f.text(56, 96, "1 つのトランザクション", 22, SUB, anchor="start")
    steps = (("① 借りる", "担保は預けない"), ("② 使う", "交換・清算など"),
             ("③ 返す", "借りた額 + 手数料"))
    for i, (title, note) in enumerate(steps):
        x = 70 + i * 290
        f.box(x, 120, 230, 100, PALE, ACCENT, sw=3)
        f.text(x + 115, 162, title, 26)
        f.text(x + 115, 196, note, 18, SUB)
        if i < 2:
            f.line(x + 236, 170, x + 282, 170, SUB, sw=3, arrow="sub")
    # success: straight down from step 3
    f.line(870, 226, 870, 300, GREEN, sw=3, arrow="sub")
    f.box(730, 306, 200, 64, GREEN_PALE, GREEN, sw=2.5)
    f.text(830, 346, "返せた：成立", 22)
    f.text(830, 400, "貸し手は手数料を得る", 18, SUB)
    # failure: down and to the left
    f.line(680, 226, 680, 338, OCHRE, sw=3)
    f.line(680, 338, 600, 338, OCHRE, sw=3, arrow="ochre")
    f.circle(640, 338, 15, RED)
    f.text(640, 346, "×", 20, "#ffffff")
    f.box(30, 306, 560, 64, OCHRE_PALE, OCHRE, sw=2.5)
    f.text(310, 344, "返せない：トランザクション全体が失敗し、①② も取り消される", 17)
    f.text(310, 400, "借りる前の状態に戻る（トランザクションの gas 代だけは払う）", 18, SUB)
    f.save("flash_loan_concept.webp")


def bzx_figure():
    """bZx, 2020-02-18: the sUSD price seen on the DEXes and the loan against it."""
    f = Svg("左は 1 つのトランザクションの中の攻撃者の ETH の出入りで、最後に 2,381 ETH が残る。"
            "右は担保の本来の価値約 4,100 ETH と、借りた 6,799 ETH", 960, 440)
    # left panel: the attacker's ETH within the transaction (waterfall)
    f.text(230, 44, "攻撃者の ETH の出入り", 22)
    base = 360
    scale = 280 / 11000
    steps = (("借りる", 7500), ("DEX", -900), ("Synthetix", -3517.86),
             ("bZx から", 6799.27), ("返済", -7500))
    level, x = 0.0, 24
    for label, delta in steps:
        top, bottom = level + max(delta, 0), level + min(delta, 0)
        fill, stroke = (PALE, ACCENT) if delta > 0 else (OCHRE_PALE, OCHRE)
        f.box(x, base - top * scale, 56, (top - bottom) * scale, fill, stroke, sw=2.5, rx=3)
        f.text(x + 28, base - top * scale - 8, f"{delta:+,.0f}", 15)
        f.text(x + 28, base + 26, label, 14, SUB)
        level += delta
        x += 72
    f.box(x, base - level * scale, 56, level * scale, GREEN_PALE, GREEN, sw=2.5, rx=3)
    f.text(x + 28, base - level * scale - 8, f"{level:,.0f}", 15)
    f.text(x + 28, base + 26, "残り", 15, SUB)
    f.line(16, base, 460, base, SUB, sw=2)
    f.text(230, base + 64, "単位は ETH。+ が受け取り、− が支払い", 16, SUB)
    # right panel: collateral vs loan (in ETH)
    f.text(720, 44, "担保と借入（ETH 換算）", 22)
    scale2 = 260 / 7000
    for x, value, label, fill, stroke in (
            (590, 4100, "約 4,100", PALE, ACCENT),
            (740, 6799.27, "6,799", OCHRE_PALE, OCHRE)):
        f.box(x, base - value * scale2, 110, value * scale2, fill, stroke, sw=3, rx=4)
        f.text(x + 55, base - value * scale2 - 12, label, 22)
    f.line(560, base, 880, base, SUB, sw=2)
    f.text(645, base + 32, "担保の本来の価値", 18, SUB)
    f.text(795, base + 32, "借りた ETH", 18, SUB)
    f.text(720, base + 64, "約 110 万 sUSD ÷ 268.30 で換算", 18, SUB)
    f.line(480, 70, 480, 400, FILL, sw=2)
    f.save("flash_loan_bzx.webp")


if __name__ == "__main__":
    concept_figure()
    bzx_figure()
