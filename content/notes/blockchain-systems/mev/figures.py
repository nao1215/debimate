"""MEV ノートの図を生成する。

lab/sandwich.py と同じ計算で、slippage tolerance ごとの被害額と攻撃者の利益を描く。
concept_figure() は冒頭の概念図で、同じ 3 件を 2 通りの順で実行した時のプールの
ETH 価格（USDC 残高 / ETH 残高）を、標準ライブラリだけで手書きした SVG に描く。

再生成:
    uv run --with matplotlib python content/notes/blockchain-systems/mev/figures.py
"""

import pathlib
import sys
from html import escape

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "lab"))
from sandwich import ETH, USDC, Pool, largest_front, min_out, sweep_point  # noqa: E402

COLOR_BLUE = "#7aa6c2"
COLOR_RED = "#e15759"
COLOR_GRAY = "#666666"

plt.rcParams.update({
    "figure.figsize": (6.4, 3.8),
    "font.size": 11,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "grid.linestyle": "-",
    "grid.linewidth": 0.5,
    "savefig.bbox": "tight",
    "savefig.dpi": 144,
    "svg.hashsalt": "mev",
})


def slippage_figure():
    victim = 10_000 * USDC
    quote = min_out(victim, 0)
    bps_list = list(range(10, 501, 10))
    loss, profit = [], []
    for bps in bps_list:
        r = sweep_point(victim, bps)
        loss.append((quote - r["A"]) * 3_000 / ETH)  # 3,000 USDC/ETH で換算
        profit.append(r["profit"] / USDC)
    x = [b / 100 for b in bps_list]

    fig, ax = plt.subplots()
    ax.plot(x, loss, color=COLOR_RED, linestyle="--", linewidth=2,
            label="Victim loss (USDC at 3,000/ETH)")
    ax.plot(x, profit, color=COLOR_BLUE, linewidth=2.2,
            label="Attacker profit (USDC, before gas)")
    ax.fill_between(x, profit, loss, color="#f2f2f2")
    ax.text(3.3, 215, "gap ≈ pool fees on\nthe attacker's 2 swaps", color=COLOR_GRAY,
            fontsize=10, ha="center")
    ax.set_xlabel("Slippage tolerance (%)")
    ax.set_ylabel("USDC")
    ax.set_xlim(0, 5.1)
    ax.set_ylim(0, None)
    ax.legend(loc="upper left", frameon=False)
    fig.savefig(HERE / "images" / "mev_slippage.svg", metadata={"Date": None})
    plt.close(fig)


# --- 概念図: 取引の並びと、プールの ETH 価格 ---

INK, SUB, ACCENT, RED = "#1f1f1f", COLOR_GRAY, COLOR_BLUE, COLOR_RED
FILL, PALE = "#f2f2f2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
GREEN, GREEN_PALE = "#8fae86", "#e9f1e6"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"


class Svg:
    def __init__(self, width, height, title):
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img"><title>{escape(title)}</title>',
            f'<style>text{{font-family:{FONT};fill:{INK}}}</style>',
            '<defs><marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" '
            'markerWidth="4" markerHeight="4" orient="auto">'
            f'<path d="M0,0 L10,5 L0,10 z" fill="{SUB}"/></marker>'
            '<marker id="arrowred" viewBox="0 0 10 10" refX="8" refY="5" '
            'markerWidth="4" markerHeight="4" orient="auto">'
            f'<path d="M0,0 L10,5 L0,10 z" fill="{RED}"/></marker></defs>',
            f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        ]

    def text(self, x, y, s, size=24, color=INK, weight="normal", anchor="middle"):
        self.parts.append(
            f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
            f'text-anchor="{anchor}" style="fill:{color}">{escape(s)}</text>')

    def circle(self, cx, cy, r, fill, stroke, sw=3, dash=""):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r:.1f}" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def box(self, x, y, w, h, fill, stroke, sw=3, rx=14):
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')

    def arrow(self, x1, y1, x2, y2, color=SUB, sw=4):
        m = "arrowred" if color == RED else "arrow"
        self.parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{color}" '
            f'stroke-width="{sw}" stroke-linecap="round" marker-end="url(#{m})"/>')

    def save(self, path):
                path.write_text("\n".join(self.parts + ["</svg>"]) + "\n", encoding="utf-8")


def price(pool):
    """プールの ETH 価格 (USDC/ETH)。残高の比で、手数料と価格インパクトは含まない。"""
    return pool.usdc / USDC / (pool.eth / ETH)


def price_path(order, victim, front):
    """順番どおりに 3 件を実行し、開始時と各取引の後の価格、A の受取量を返す。"""
    pool = Pool()
    prices, got, attacker_eth = [price(pool)], None, 0
    for tx in order:
        if tx == "A":
            got = pool.buy_eth(victim)
        elif tx == "B":
            attacker_eth = pool.buy_eth(front)
        else:
            pool.sell_eth(attacker_eth)
        prices.append(price(pool))
    return prices, got


def concept_figure():
    victim = 10_000 * USDC
    front = largest_front(victim, min_out(victim, 100))  # 許容幅 1% の時の front-run
    f = Svg(960, 540, "取引の並び順と、プールの ETH 価格の上下")
    f.text(570, 40, "線: プールの ETH 価格　箱: ブロック内の取引の並び", 24, SUB)

    xs = [300, 490, 680]  # 箱の中心
    bw, bh, scale = 150, 52, 2.0  # 1 USDC/ETH を 2px で描く
    rows = [("A→B→C", "ABC", 215), ("B→A→C", "BAC", 448)]
    for title, order, base in rows:
        prices, got = price_path(order, victim, front)
        y = [base - (p - 3000) * scale for p in prices]
        top = base + 14
        mid = (base - 100 + top + bh) / 2
        f.text(40, base - 95, title, 28, weight="normal", anchor="start")
        # 3,000 USDC/ETH の基準線
        f.parts.append(
            f'<line x1="205" y1="{base}" x2="765" y2="{base}" stroke="#cccccc" '
            f'stroke-width="2" stroke-dasharray="6 6"/>')
        f.text(196, base + 8, "3,000", 24, SUB, anchor="end")
        # 箱の上は、その取引が動かした区間。取引と同じ色で描く
        pts = [(205, y[0])]
        for i, x in enumerate(xs):
            pts += [(x - bw / 2, y[i]), (x + bw / 2, y[i + 1])]
        pts.append((765, y[-1]))
        for k in range(len(pts) - 1):
            (x1, y1), (x2, y2) = pts[k], pts[k + 1]
            color = INK
            if k % 2 == 1:
                color = ACCENT if order[k // 2] == "A" else OCHRE
            f.parts.append(
                f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                f'stroke="{color}" stroke-width="{6 if k % 2 else 3}" stroke-linecap="round"/>')
        for x, tx in zip(xs, order):
            victim_tx = tx == "A"
            fill, stroke = (PALE, ACCENT) if victim_tx else (OCHRE_PALE, OCHRE)
            name = {"A": "A 利用者", "B": "B 買い", "C": "C 売り"}[tx]
            f.box(x - bw / 2, top, bw, bh, fill, stroke, rx=8)
            f.text(x, top + bh / 2 + 9, name, 26, INK, weight="normal")
        f.text(790, mid - 14, "A の受取", 24, SUB, anchor="start")
        f.text(790, mid + 22, f"{got / ETH:.3f} ETH", 28,
               INK if order == "ABC" else RED, weight="normal", anchor="start")

    f.save(HERE / "images" / "mev_concept.svg")


if __name__ == "__main__":
    slippage_figure()
    concept_figure()
