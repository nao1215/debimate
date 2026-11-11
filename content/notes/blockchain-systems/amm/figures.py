"""Generate the figures of the AMM note.

concept_figure() builds SVG text here, renders it with headless Chrome at 2x
and saves WebP (Pillow). The other figures need matplotlib and read
lab/amm_sim_output.txt; they are saved as PNG (dpi 200) and converted to WebP.
Only the WebP files are kept in images/.

Run: python3 content/notes/blockchain-systems/amm/figures.py
"""

import re
import subprocess
import tempfile
from html import escape
from math import sqrt
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
INK, SUB, ACCENT, RED = "#1f1f1f", "#666666", "#7aa6c2", "#e15759"
FILL, PALE = "#f2f2f2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"
OUTPUT = (HERE / "lab" / "amm_sim_output.txt").read_text()


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


def save_matplotlib(fig, name):
    with tempfile.TemporaryDirectory() as tmp:
        png = Path(tmp) / "fig.png"
        fig.savefig(png, dpi=200, facecolor="#ffffff")
        to_webp(png, name)


class Svg:
    """A tiny hand-written SVG builder (960x540, white background)."""

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
                for name, color in (("sub", SUB), ("ink", INK), ("ochre", OCHRE)))
            + '</defs>',
            f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        ]

    def text(self, x, y, s, size=24, color=INK, anchor="middle"):
        self.parts.append(
            f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" '
            f'text-anchor="{anchor}" style="fill:{color}">{escape(s)}</text>')

    def rect(self, x, y, w, h, fill, stroke="none", sw=2.5, dash=""):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def circle(self, cx, cy, r, fill, stroke="none", sw=2.5):
        self.parts.append(
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r}" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="{sw}"/>')

    def line(self, x1, y1, x2, y2, color, sw=3, arrow=None, dash=""):
        m = f' marker-end="url(#arrow-{arrow})"' if arrow else ""
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{color}" '
            f'stroke-width="{sw}" stroke-linecap="round"{d}{m}/>')

    def path(self, d, stroke, sw=4, arrow=None):
        m = f' marker-end="url(#arrow-{arrow})"' if arrow else ""
        self.parts.append(
            f'<path d="{d}" fill="none" stroke="{stroke}" stroke-width="{sw}" '
            f'stroke-linecap="round" stroke-linejoin="round"{m}/>')

    def save(self, name):
        render("\n".join(self.parts + ["</svg>"]) + "\n", self.w, self.h, name)


def concept_figure():
    """x*y=k as a hyperbola; two reserve states are rectangles of the same area."""
    f = Svg("手数料を除くと、プールの残高 x と y は双曲線 x × y = k の上を動く。交換の前後で長方形の面積 k は変わらない")
    ox, oy, sx, sy = 110, 470, 70, 40  # origin and pixels per unit
    k = 12.0
    ax_, ay = 3.0, 4.0  # before: x=3, y=4
    bx, by = 6.0, 2.0  # after: x=6, y=2

    def px(x):
        return ox + x * sx

    def py(y):
        return oy - y * sy

    # The part only the "before" rectangle covers (blue) and the part only the
    # "after" rectangle covers (ochre). Both have the same area.
    f.rect(px(0), py(ay), ax_ * sx, (ay - by) * sy, PALE)
    f.rect(px(0), py(by), ax_ * sx, by * sy, FILL)
    f.rect(px(ax_), py(by), (bx - ax_) * sx, by * sy, OCHRE_PALE)
    f.rect(px(0), py(ay), ax_ * sx, ay * sy, "none", ACCENT, sw=3)
    f.rect(px(0), py(by), bx * sx, by * sy, "none", OCHRE, sw=3, dash="8 6")

    # Axes.
    f.line(ox, oy, ox + 11.6 * sx, oy, SUB, sw=2.5, arrow="sub")
    f.line(ox, oy, ox, oy - 10.6 * sy, SUB, sw=2.5, arrow="sub")
    f.text(ox + 11.6 * sx, oy + 40, "x（USDC の残高）", 22, SUB, anchor="end")
    f.text(ox + 14, oy - 10.6 * sy + 6, "y（ETH の残高）", 22, SUB, anchor="start")

    # Hyperbola x*y = k.
    pts = []
    x = 1.25
    while x <= 11.2:
        pts.append(f"{px(x):.1f},{py(k / x):.1f}")
        x += 0.05
    f.path("M" + " L".join(pts), INK, sw=3.5)
    f.text(px(9.6), py(k / 9.6) - 22, "x × y = k", 28)

    # The trade moves the point along the curve.
    f.path(f"M{px(3.35):.1f},{py(k / 3.35) - 22:.1f} Q{px(4.6):.1f},{py(3.35):.1f} "
           f"{px(5.6):.1f},{py(k / 5.6) - 24:.1f}", INK, sw=3, arrow="ink")
    f.circle(px(ax_), py(ay), 9, ACCENT)
    f.circle(px(bx), py(by), 9, OCHRE)
    f.text(px(ax_) + 18, py(ay) - 14, "交換の前", 24, anchor="start")
    f.text(px(bx) + 18, py(by) - 16, "交換の後", 24, anchor="start")

    # Side notes: what goes in and out.
    f.text(px(4.5), oy + 40, "USDC を入れる", 22, SUB)
    f.text(ox - 18, py(3.0) + 8, "ETH が", 22, SUB, anchor="end")
    f.text(ox - 18, py(3.0) + 36, "出る", 22, SUB, anchor="end")
    f.save("amm_concept.webp")


def setup_matplotlib(salt):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "font.family": "Noto Sans CJK JP", "font.size": 11,
        "axes.edgecolor": SUB, "axes.labelcolor": INK,
        "xtick.color": INK, "ytick.color": INK, "text.color": INK,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.color": "#dddddd", "grid.linewidth": 0.6,
        "svg.fonttype": "path", "svg.hashsalt": salt,
        "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
        "savefig.facecolor": "#ffffff",
    })
    return plt


def price_impact_figure():
    """Average price paid vs trade size relative to the USDC reserve."""
    plt = setup_matplotlib("amm-impact")
    g = 0.997
    shares = [i / 1000 for i in range(1, 301)]
    # Buying ETH with share*x USDC from a pool at price p: average = p*(1 + g*s)/g
    avg = [((1 + g * s) / g - 1) * 100 for s in shares]
    spot = [((1 + s) ** 2 - 1) * 100 for s in shares]
    rows = re.findall(r"^\s*([\d,]+) USDC ->.*avg\s+[\d,]+ \(\+\s*([\d.]+)%\)", OUTPUT, re.M)
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    ax.plot([s * 100 for s in shares], spot, color=OCHRE, linewidth=2, linestyle="--",
            label="交換の後のプールの価格")
    ax.plot([s * 100 for s in shares], avg, color=ACCENT, linewidth=2.4,
            label="買った人の平均の価格")
    for usdc, pct in rows:
        s = int(usdc.replace(",", "")) / 3_000_000 * 100
        if s <= 30:
            ax.plot(s, float(pct), "o", color=ACCENT, markersize=5)
    ax.annotate("残高の 10% を入れると +10.3%", xy=(10, 10.3), xytext=(15, 3),
                color=SUB, arrowprops={"arrowstyle": "-", "color": SUB})
    ax.set_xlim(0, 30.5)
    ax.set_ylim(0, 72)
    ax.set_xlabel("入れる USDC の量（プールの USDC 残高に対する %）")
    ax.set_ylabel("交換前の価格からの上昇（%）")
    ax.legend(frameon=False, loc="upper left")
    fig.tight_layout()
    save_matplotlib(fig, "amm_price_impact.webp")
    plt.close(fig)


def impermanent_loss_figure():
    """LP value vs HODL as a function of the price ratio, with the lab results."""
    plt = setup_matplotlib("amm-il")
    ratios = [0.1 * 1.02 ** i for i in range(0, 233)]  # 0.1 .. ~10
    il = [(2 * sqrt(r) / (1 + r) - 1) * 100 for r in ratios]
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    ax.plot(ratios, il, color=ACCENT, linewidth=2.4, label="手数料を除いた式 2√r / (1 + r) − 1")
    lab = re.findall(r"^(up to 2x|down to 1/2)\s+price\s+([\d,]+).*LP vs HODL\s+([-+\d.]+)%",
                     OUTPUT, re.M)
    for i, (_, price, pct) in enumerate(lab):
        ax.plot(int(price.replace(",", "")) / 3000, float(pct), "o", color=OCHRE, markersize=7,
                label="実験（手数料あり）" if i == 0 else None)
    for r, text, tx in ((2, "2 倍で −5.7%", 4.2), (0.5, "半分でも −5.7%", 0.24)):
        ax.annotate(text, xy=(r, (2 * sqrt(r) / (1 + r) - 1) * 100),
                    xytext=(tx, -4), color=SUB, ha="center", va="center",
                    arrowprops={"arrowstyle": "-", "color": SUB})
    ax.set_xscale("log")
    ax.set_xticks([0.1, 0.25, 0.5, 1, 2, 4, 10], ["1/10", "1/4", "1/2", "1", "2", "4", "10"])
    ax.set_xlim(0.1, 10)
    ax.set_ylim(-45, 2)
    ax.set_xlabel("預けた時からの価格の比 r（対数軸）")
    ax.set_ylabel("持ち続けた場合との差（%）")
    ax.legend(frameon=False, loc="lower center")
    fig.tight_layout()
    save_matplotlib(fig, "amm_impermanent_loss.webp")
    plt.close(fig)


def lp_vs_hodl_figure():
    """Value after the price doubled: deposit, LP and HODL, split into USDC and ETH."""
    plt = setup_matplotlib("amm-lp-hodl")
    m = re.search(r"^up to 2x\s+price\s+([\d,]+)\s+pool ETH\s+([\d.]+)\s+LP vs HODL\s+([-+\d.]+)%",
                  OUTPUT, re.M)
    price, pool_eth, pct = int(m[1].replace(",", "")), float(m[2]), float(m[3])
    hodl = 3_000_000 + 1_000 * price
    lp = hodl * (1 + pct / 100)
    rows = [  # label, USDC part, ETH part (valued in USDC)
        ("預けた時（1 ETH = 3,000）", 3_000_000, 1_000 * 3000),
        ("2 倍の後: LP", lp - pool_eth * price, pool_eth * price),
        ("2 倍の後: 持ち続けた場合", 3_000_000, 1_000 * price),
    ]
    fig, ax = plt.subplots(figsize=(7.2, 3.1))
    for i, (label, usdc, eth) in enumerate(reversed(rows)):
        ax.barh(i, usdc / 1e6, color=PALE, edgecolor=ACCENT, height=0.55,
                label="USDC の分" if i == 0 else None)
        ax.barh(i, eth / 1e6, left=usdc / 1e6, color=OCHRE_PALE, edgecolor=OCHRE, height=0.55,
                label="ETH の分" if i == 0 else None)
        ax.text((usdc + eth) / 1e6 + 0.12, i, f"{(usdc + eth) / 1e6:,.2f} 百万 USDC",
                va="center", ha="left", color=INK)
    ax.set_yticks(range(3), [r[0] for r in reversed(rows)])
    ax.set_xlim(0, 11.5)
    ax.set_ylim(-0.5, 3.0)
    ax.set_xlabel("価値（百万 USDC。ETH はその時点の価格で換算）")
    ax.grid(axis="y", visible=False)
    ax.legend(frameon=False, loc="upper center", ncol=2, fontsize=10)
    fig.tight_layout()
    save_matplotlib(fig, "amm_lp_vs_hodl.webp")
    plt.close(fig)


def twap_cumulative_figure():
    """The cumulative price is the area under the price; TWAP = area / seconds."""
    plt = setup_matplotlib("amm-twap-cum")
    prices = [3000, 3030, 2990, 3010, 3060, 3040, 3000, 2980, 3020, 3050, 3030, 3000]
    secs = [12 * i for i in range(len(prices) + 1)]
    t1, t2 = 36, 120
    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    for i, pr in enumerate(prices):
        inside = t1 <= secs[i] < t2
        ax.fill_between([secs[i], secs[i + 1]], 2900, pr, color=PALE if inside else FILL,
                        edgecolor="none")
    ax.step(secs, prices + [prices[-1]], where="post", color=INK, linewidth=1.6,
            label="各ブロックの最初の交換の前の価格")
    area = sum(prices[i] * 12 for i in range(len(prices)) if t1 <= secs[i] < t2)
    twap = area / (t2 - t1)
    ax.hlines(twap, t1, t2, color=ACCENT, linewidth=2.6, label=f"t1〜t2 の TWAP: {twap:,.0f}")
    for t, name in ((t1, "t1"), (t2, "t2")):
        ax.axvline(t, color=SUB, linewidth=1, linestyle="--")
        ax.text(t + 2, 2908, name, ha="left", color=SUB)
    ax.text((t1 + t2) / 2, 2940, "累積値の差 = この区間の（価格 × 秒）の合計", ha="center", color=INK)
    ax.set_xlim(0, secs[-1])
    ax.set_ylim(2900, 3100)
    ax.set_xticks(secs)
    ax.set_xlabel("時間（秒、1 ブロック 12 秒）")
    ax.set_ylabel("USDC / ETH")
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:,.0f}"))
    ax.legend(frameon=False, loc="upper left", fontsize=10)
    fig.tight_layout()
    save_matplotlib(fig, "amm_twap_cumulative.webp")
    plt.close(fig)


def twap_figure():
    """One manipulated block at the end of a 30-minute window: spot vs TWAP."""
    plt = setup_matplotlib("amm-twap")
    row = re.search(r"held\s+1 blocks\s+spot\s+([\d,]+)\s+TWAP 24s\s+([\d,]+)\s+TWAP 30min\s+([\d,]+)",
                    OUTPUT)
    spot, t24, t30 = (int(v.replace(",", "")) for v in row.groups())
    fig, (left, right) = plt.subplots(1, 2, figsize=(7.6, 3.6), sharey=True,
                                      gridspec_kw={"width_ratios": [3, 2]})
    # Left: the whole 30 minutes. The manipulated block is only the last 12 s.
    left.fill_between([0, 30 - 0.2], 0, 3000, color=FILL, step="post")
    left.fill_between([30 - 0.2, 30], 0, spot, color=OCHRE_PALE)
    left.plot([0, 29.8, 29.8, 30], [3000, 3000, spot, spot], color=INK, linewidth=1.6,
              label="プールの価格")
    left.hlines(t30, 0, 30, color=ACCENT, linewidth=2.6, label=f"30 分の TWAP: {t30:,}")
    left.set_xlim(0, 30.5)
    left.set_xlabel("経過時間（分）")
    left.set_ylabel("USDC / ETH")
    left.legend(frameon=False, loc="upper left")
    # Right: zoom into the last 60 seconds (5 blocks of 12 s).
    right.fill_between([-60, -12], 0, 3000, color=FILL)
    right.fill_between([-12, 0], 0, spot, color=OCHRE_PALE)
    right.plot([-60, -12, -12, 0], [3000, 3000, spot, spot], color=INK, linewidth=1.6)
    right.hlines(t24, -24, 0, color=OCHRE, linewidth=2.6, label=f"24 秒の TWAP: {t24:,}")
    right.hlines(t30, -60, 0, color=ACCENT, linewidth=2.6)
    right.set_xlim(-60, 2)
    right.set_xticks([-60, -48, -36, -24, -12, 0])
    right.set_xlabel("最後の 60 秒の拡大（秒）")
    right.legend(frameon=False, loc="upper left")
    left.set_ylim(0, 13500)
    left.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:,.0f}"))
    fig.tight_layout()
    save_matplotlib(fig, "amm_twap.webp")
    plt.close(fig)


def keep3r_window_figure():
    """Keep3rV2Oracle averages from its last record to the pair's last update.

    A record is added only after more than 30 minutes, so right after a record
    the averaging window is short and one manipulated block dominates it.
    Schematic: the bar of the manipulated block is drawn wider than its seconds.
    The lower row uses the 15 s window that CertiK reports for the Inverse Finance attack.
    """
    f = Svg("Keep3r のオラクルは最後の記録から平均するので、記録の直後に吊り上げると平均の区間が短く、"
            "吊り上げた価格がほぼそのまま返る", 960, 500)
    x0, x1 = 70, 900  # 0 min .. 36 min

    def px(m):
        return x0 + (x1 - x0) * m / 36

    rows = (
        (40, 25, "記録から 25 分後に吊り上げた場合",
         "平均する区間が長く、吊り上げた 1 ブロックは薄まる", "平均する区間（25 分）"),
        (280, 0, "記録の直後に吊り上げた場合（Inverse Finance の事故）",
         "平均する区間が吊り上げた 1 ブロックだけになり、吊り上げた価格がそのまま平均になる",
         "平均する区間（15 秒）"),
    )
    for top, at, title, note, window in rows:
        f.text(x0, top + 22, title, 22, anchor="start")
        f.text(x0, top + 52, note, 20, SUB, anchor="start")
        base = top + 170  # time axis
        lo, hi = base - 20, base - 90  # normal price, manipulated price
        end = at + 0.4 if at else 10 / ((x1 - x0) / 36)  # the block bar is 10 px wide
        f.rect(px(0), hi - 10, px(end) - px(0), base - hi + 10, PALE)
        f.path(f"M{px(0):.1f},{lo:.1f} L{px(36):.1f},{lo:.1f}", INK, sw=3)
        f.text(px(36), lo - 14, "プールの価格", 20, SUB, anchor="end")
        f.rect(px(at), hi, 10, lo - hi, OCHRE_PALE, OCHRE, sw=2)
        f.text(px(at) + 22, hi + 24, "吊り上げた 1 ブロック", 20, anchor="start")
        f.line(px(0), base, px(36), base, SUB, sw=2, arrow="sub")
        f.circle(px(0), base, 8, INK, INK, sw=2.5)
        f.text(px(0), base + 32, "記録", 20, SUB)
        f.circle(px(31), base, 8, "#ffffff", INK, sw=2.5)
        f.text(px(31), base + 32, "次の記録（30 分より後）", 20, SUB)
        f.text(px(at) + 22 if at < 5 else (px(0) + px(end)) / 2, hi + 58 if at < 5 else hi + 24,
               window, 20, anchor="start" if at < 5 else "middle")
    f.save("amm_keep3r_window.webp")

if __name__ == "__main__":
    concept_figure()
    price_impact_figure()
    impermanent_loss_figure()
    lp_vs_hodl_figure()
    twap_cumulative_figure()
    twap_figure()
    keep3r_window_figure()
