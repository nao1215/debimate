"""Generate the figures of the Lending note.

The concept figures build SVG text here, render it with headless Chrome at 2x
and save WebP (Pillow). rate_figure() and liquidation_figure() need matplotlib;
liquidation_figure() reads lab/lending_sim_output.txt. matplotlib figures are
saved as PNG (dpi 200) and converted to WebP. Only WebP files are kept in images/.

Run: python3 content/notes/blockchain-systems/lending/figures.py
"""

import re
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
    """10 ETH of collateral, 12,000 USDC of debt, and the ETH price falling."""
    f = Svg("担保 10 ETH と借入 12,000 USDC。ETH の価格が下がり、担保の 80% の線が借入を下回ると清算される")
    base, scale = 400, 300 / 20000  # px per USDC
    debt = 12000
    for i, (price, hf) in enumerate(((2000, "1.33"), (1600, "1.07"), (1400, "0.93"))):
        cx = 170 + i * 310
        value = 10 * price
        h, lim = value * scale, value * 0.8 * scale
        f.text(cx, 56, f"1 ETH = {price:,} ドル", 26)
        f.box(cx - 115, base - h, 105, h, PALE, ACCENT, sw=3, rx=4)
        f.box(cx + 10, base - debt * scale, 105, debt * scale, OCHRE_PALE, OCHRE, sw=3, rx=4)
        f.line(cx - 135, base - lim, cx + 135, base - lim, SUB, sw=3, dash="10 7")
        f.line(cx - 140, base, cx + 140, base, SUB, sw=2)
        if i == 2:
            f.circle(cx + 62, base - debt * scale - 2, 18, RED)
            f.text(cx + 62, base - debt * scale + 7, "×", 26, "#ffffff")
        f.text(cx, base + 44, f"HF {hf}", 26, RED if i == 2 else INK)
    f.box(150, 478, 28, 22, PALE, ACCENT, sw=2.5, rx=3)
    f.text(186, 498, "担保の価値", 22, SUB, anchor="start")
    f.box(370, 478, 28, 22, OCHRE_PALE, OCHRE, sw=2.5, rx=3)
    f.text(406, 498, "借入", 22, SUB, anchor="start")
    f.line(520, 489, 570, 489, SUB, sw=3, dash="10 7")
    f.text(582, 498, "清算の線（担保の 80%）", 22, SUB, anchor="start")
    f.save("lending_concept.webp")


def liquidation_call_figure():
    """One liquidation call on Alice: before / after, and who pays whom."""
    price, repay, bonus, lt = 1455, 6000, 1.05, 0.8
    eth0, debt0 = 10.0, 12000.0
    seize = repay * bonus / price
    eth1, debt1 = eth0 - seize, debt0 - repay
    hf0, hf1 = eth0 * price * lt / debt0, eth1 * price * lt / debt1
    f = Svg("1 ETH = 1,455 ドルで HF 0.97 の Alice を清算する。清算者が 6,000 USDC を返済し、"
            "6,300 ドル分の ETH を受け取る。清算の後の HF は 1.10", 960, 500)
    base, scale = 400, 300 / 15000

    def position(cx, eth, debt, hf, title):
        value = eth * price
        f.text(cx, 50, title, 24)
        f.box(cx - 115, base - value * scale, 105, value * scale, PALE, ACCENT, sw=3, rx=4)
        f.box(cx + 10, base - debt * scale, 105, debt * scale, OCHRE_PALE, OCHRE, sw=3, rx=4)
        lim = value * lt * scale
        f.line(cx - 135, base - lim, cx + 135, base - lim, SUB, sw=3, dash="10 7")
        f.line(cx - 140, base, cx + 140, base, SUB, sw=2)
        f.text(cx - 62, base - 46, f"{eth:.2f}", 20)
        f.text(cx - 62, base - 20, "ETH", 18, SUB)
        f.text(cx + 62, base - 46, f"{debt:,.0f}", 20)
        f.text(cx + 62, base - 20, "USDC", 18, SUB)
        f.text(cx, base + 40, f"HF {hf:.2f}", 24)

    position(185, eth0, debt0, hf0, "清算の前")
    position(775, eth1, debt1, hf1, "清算の後")
    # the liquidator in the middle
    f.text(470, 176, f"← {repay:,} USDC を返済", 20)
    f.line(400, 212, 322, 212, OCHRE, sw=4, arrow="ochre")
    f.box(405, 190, 150, 84, FILL, SUB, sw=2.5)
    f.text(480, 228, "清算者", 24)
    f.text(480, 258, "（誰でもよい）", 18, SUB)
    f.line(322, 254, 398, 254, ACCENT, sw=4, arrow="accent")
    f.text(470, 302, f"→ {seize:.2f} ETH（{repay * bonus:,.0f} ドル分）", 20)
    f.text(470, 332, "を受け取る。差の 300 ドル分がボーナス", 17, SUB)
    f.box(150, 452, 28, 22, PALE, ACCENT, sw=2.5, rx=3)
    f.text(186, 470, "担保の価値", 20, SUB, anchor="start")
    f.box(350, 452, 28, 22, OCHRE_PALE, OCHRE, sw=2.5, rx=3)
    f.text(386, 470, "借入", 20, SUB, anchor="start")
    f.line(480, 463, 530, 463, SUB, sw=3, dash="10 7")
    f.text(542, 470, "清算の線（担保の 80%）", 20, SUB, anchor="start")
    f.save("lending_liquidation_call.webp")


def maker_auction_figure():
    """MakerDAO's collateral auction: a normal day vs. 2020-03-12 (schematic)."""
    f = Svg("通常の清算では keeper が競って入札し、落札額で借入の DAI を回収できる。"
            "2020 年 3 月 12 日は入札者が少なく、ほぼ 0 DAI で落札され、借入が埋まらなかった", 960, 450)
    rows = (("通常の日", 0.8, "複数の keeper が競って入札"),
            ("2020 年 3 月 12〜13 日", 0.03, "入札者が少なく、ほぼ 0 DAI で落札"))
    x0, width = 290, 560
    for i, (title, bid, note) in enumerate(rows):
        y = 30 + i * 190
        f.text(40, y + 20, title, 24, anchor="start")
        f.text(40, y + 52, note, 18, SUB, anchor="start")
        f.text(x0 - 12, y + 108, "借入（DAI）", 20, SUB, anchor="end")
        f.box(x0, y + 86, width * 0.8, 34, OCHRE_PALE, OCHRE, sw=2.5, rx=4)
        f.text(x0 - 12, y + 154, "落札額（DAI）", 20, SUB, anchor="end")
        paid = width * bid
        f.box(x0, y + 132, max(paid, 6), 34, GREEN_PALE if bid > 0.5 else PALE,
              GREEN if bid > 0.5 else ACCENT, sw=2.5, rx=4)
        if bid > 0.5:
            f.text(x0 + paid + 12, y + 156, "借入を回収できる", 20, anchor="start")
        else:
            f.box(x0 + paid + 4, y + 132, width * 0.8 - paid - 4, 34, "#ffffff", RED,
                  sw=2.5, dash="8 6", rx=4)
            f.text(x0 + width * 0.4, y + 156, "埋まらない借入", 20)
    f.text(480, 432, "1 つの Vault の清算を表した模式図（長さは目安）", 16, SUB)
    f.save("lending_maker_auction.webp")


def _plt(salt):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "font.family": "Noto Sans CJK JP", "font.size": 11,
        "axes.edgecolor": SUB, "axes.labelcolor": INK,
        "xtick.color": INK, "ytick.color": INK, "text.color": INK,
        "svg.hashsalt": salt,
        "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
        "savefig.facecolor": "#ffffff",
    })
    return plt


def save_matplotlib(fig, name):
    with tempfile.TemporaryDirectory() as tmp:
        png = Path(tmp) / "fig.png"
        fig.savefig(png, dpi=200, facecolor="#ffffff")
        to_webp(png, name)


def rate_figure():
    """A kinked borrow rate curve (illustrative parameters, not a real market)."""
    plt = _plt("lending-rate")
    optimal, base, slope1, slope2, reserve_factor = 0.80, 0.0, 0.04, 0.75, 0.15
    u = [i / 200 for i in range(201)]
    borrow = [base + slope1 * x / optimal if x <= optimal
              else base + slope1 + slope2 * (x - optimal) / (1 - optimal) for x in u]
    supply = [b * x * (1 - reserve_factor) for b, x in zip(borrow, u)]
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    ax.plot([x * 100 for x in u], [b * 100 for b in borrow], color=OCHRE, lw=2.4,
            label="借り手の金利（borrow rate）")
    ax.plot([x * 100 for x in u], [s * 100 for s in supply], color=ACCENT, lw=2.4,
            label="預け手の利率（supply rate）")
    ax.axvline(optimal * 100, color=SUB, lw=1, ls="--")
    ax.text(optimal * 100 - 1.5, 52, "最適利用率 80%\n（Compound の kink）", ha="right", color=SUB)
    ax.set_xlabel("利用率：プールの資産のうち貸し出されている割合 [%]")
    ax.set_ylabel("年利 [%]")
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 82)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, loc="upper left")
    fig.tight_layout()
    save_matplotlib(fig, "lending_rate.webp")


def liquidation_figure():
    plt = _plt("lending-liquidation")
    text = (HERE / "lab" / "lending_sim_output.txt").read_text()
    rows = re.findall(r"^  hf (\w+) (\d+) (\S+) (\S+) (\S+)$", text, re.M)
    bad = float(re.search(r"\[gap\].*?bad debt: ([\d.]+)", text, re.S).group(1))
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    smooth = [(int(p), float(b), float(c)) for s, p, _, b, c in rows if s == "smooth"]
    ax.plot([r[0] for r in smooth], [r[1] for r in smooth], color=SUB, lw=1.8,
            label="B（担保の 60% を借入）、10 ずつ下がる")
    ax.plot([r[0] for r in smooth], [r[2] for r in smooth], color=ACCENT, lw=2.4,
            label="C（担保の 75% を借入）、10 ずつ下がる")
    # gap: the price jumps 1,950 -> 1,300. Mark C's HF just before it is liquidated
    # (10 ETH * 1300 * 0.8 / 15000); after the call C has no debt left.
    hf_c = 10 * 1300 * 0.8 / 15000
    ax.plot([1300], [hf_c], "x", color=RED, ms=11, mew=3)
    ax.plot([1950], [1.04], "o", color=OCHRE, ms=6, label="C、価格が飛ぶ直前（1,950）")
    ax.annotate("", (1310, 0.585), (1950, 0.585),
                arrowprops={"arrowstyle": "->", "color": OCHRE, "lw": 1.8})
    ax.text(1625, 0.6, "価格が 1,950 から 1,300 に飛ぶ（間の価格では清算できない）",
            color=SUB, ha="center", fontsize=9.5)
    ax.text(1500, 0.7, "C の清算の直前の HF（×）\n"
            f"担保 < 借入で、不良債権 {bad:,.0f} USDC", color=INK, ha="center", fontsize=10)
    ax.axhline(1.0, color=SUB, lw=1, ls=":")
    ax.text(1995, 0.97, "HF = 1", va="top", color=SUB)
    ax.set_xlim(2010, 1190)
    ax.set_ylim(0.55, 1.42)  # noqa
    ax.set_xlabel("ETH の価格 [USDC]（右ほど安い）")
    ax.set_ylabel("清算の後の HF")
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, loc="upper right", fontsize=9.5)
    fig.tight_layout()
    save_matplotlib(fig, "lending_liquidation.webp")


if __name__ == "__main__":
    concept_figure()
    liquidation_call_figure()
    maker_auction_figure()
    rate_figure()
    liquidation_figure()
