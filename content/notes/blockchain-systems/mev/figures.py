"""MEV ノートの図を生成する。

python3 figures.py  ->  images/mev_concept.webp     （冒頭。同じ指示の 3 件を 2 通りの順で実行した時のプールの ETH 価格）
                        images/mev_conditions.webp  （並び順が価値になる 2 つの条件）
                        images/mev_slippage.webp    （matplotlib。slippage tolerance ごとの損失と利益）

lab/sandwich.py と同じ計算を使う。手書きの図は標準ライブラリで SVG を組み立て、
Chrome の headless で 2 倍の解像度に描いてから WebP にする。matplotlib の図は dpi 200 の
PNG にしてから WebP にする。images/ には WebP だけを置く。

再生成:
    uv run --with matplotlib --with pillow python content/notes/blockchain-systems/mev/figures.py
"""

import pathlib
import subprocess
import sys
import tempfile
from html import escape

from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "lab"))
from sandwich import ETH, USDC, Pool, largest_front, min_out, sweep_point  # noqa: E402

INK, SUB = "#1f1f1f", "#666666"
BLUE, PALE = "#7aa6c2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
RED = "#e15759"
FILL = "#f2f2f2"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"


def to_webp(png, name):
    (HERE / "images").mkdir(exist_ok=True)
    Image.open(png).convert("RGB").save(HERE / "images" / name, "WEBP", quality=90, method=6)


class Svg:
    def __init__(self, width, height, title):
        self.w, self.h = width, height
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img"><title>{escape(title)}</title>',
            f'<style>text{{font-family:{FONT};fill:{INK}}}</style>',
            '<defs><marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" '
            'markerWidth="5" markerHeight="5" orient="auto">'
            f'<path d="M0,0 L10,5 L0,10 z" fill="{SUB}"/></marker></defs>',
            f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        ]

    def text(self, x, y, s, size=24, color=INK, anchor="middle"):
        self.parts.append(
            f'<text x="{x}" y="{y}" font-size="{size}" '
            f'text-anchor="{anchor}" style="fill:{color}">{escape(s)}</text>')

    def box(self, x, y, w, h, fill, stroke, sw=3, rx=10, dash=False):
        d = ' stroke-dasharray="8 6"' if dash else ""
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def arrow(self, x1, y1, x2, y2, color=SUB, sw=3):
        self.parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{color}" '
            f'stroke-width="{sw}" stroke-linecap="round" marker-end="url(#arrow)"/>')

    def save(self, name):
        svg_text = "\n".join(self.parts + ["</svg>"]) + "\n"
        with tempfile.TemporaryDirectory() as tmp:
            svg, png = pathlib.Path(tmp) / "fig.svg", pathlib.Path(tmp) / "fig.png"
            svg.write_text(svg_text, encoding="utf-8")
            subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--hide-scrollbars",
                            "--force-device-scale-factor=2", f"--window-size={self.w},{self.h}",
                            f"--screenshot={png}", svg.as_uri()], check=True, capture_output=True)
            to_webp(png, name)


# --- 冒頭の図: トランザクションの並びと、プールの ETH 価格 ---

def price(pool):
    """プールの ETH 価格 (USDC/ETH)。残高の比で、手数料と価格インパクトは含まない。"""
    return pool.usdc / USDC / (pool.eth / ETH)


def price_path(order, victim, front):
    """順番どおりに 3 件を実行し、開始時と各トランザクションの後の価格、A の受取量を返す。"""
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
    front = largest_front(victim, min_out(victim, 100))  # 許容幅 1% の時の B の大きさ
    f = Svg(960, 540, "トランザクションの並び順と、取引所の ETH 価格の上下")
    f.text(540, 40, "線: 取引所の ETH 価格（USDC/ETH）　箱: トランザクションの並び", 20, SUB)

    xs = [300, 490, 680]  # 箱の中心
    bw, bh, scale = 150, 52, 2.0  # 1 USDC/ETH を 2px で描く
    rows = [("A→B→C", "ABC", 215), ("B→A→C", "BAC", 448)]
    for title, order, base in rows:
        prices, got = price_path(order, victim, front)
        y = [base - (p - 3000) * scale for p in prices]
        top = base + 14
        mid = (base - 100 + top + bh) / 2
        f.text(40, base - 95, title, 28, anchor="start")
        # 3,000 USDC/ETH の基準線
        f.parts.append(
            f'<line x1="205" y1="{base}" x2="765" y2="{base}" stroke="#cccccc" '
            f'stroke-width="2" stroke-dasharray="6 6"/>')
        f.text(196, base + 8, "3,000", 24, SUB, anchor="end")
        # 箱の上は、そのトランザクションが動かした区間。トランザクションと同じ色で描く
        pts = [(205, y[0])]
        for i, x in enumerate(xs):
            pts += [(x - bw / 2, y[i]), (x + bw / 2, y[i + 1])]
        pts.append((765, y[-1]))
        for k in range(len(pts) - 1):
            (x1, y1), (x2, y2) = pts[k], pts[k + 1]
            color = INK
            if k % 2 == 1:
                color = BLUE if order[k // 2] == "A" else OCHRE
            f.parts.append(
                f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                f'stroke="{color}" stroke-width="{6 if k % 2 else 3}" stroke-linecap="round"/>')
        for x, tx in zip(xs, order):
            fill, stroke = (PALE, BLUE) if tx == "A" else (OCHRE_PALE, OCHRE)
            name = {"A": "A 利用者", "B": "B 買い", "C": "C 売り"}[tx]
            f.box(x - bw / 2, top, bw, bh, fill, stroke, rx=8)
            f.text(x, top + bh / 2 + 9, name, 26)
        f.parts.append(
            f'<line x1="778" y1="{base - 100}" x2="778" y2="{top + bh}" stroke="#cccccc" stroke-width="2"/>')
        f.text(790, mid - 14, "A の受取量", 24, SUB, anchor="start")
        f.text(790, mid + 22, f"{got / ETH:.3f} ETH", 28,
               INK if order == "ABC" else RED, anchor="start")
    f.save("mev_concept.webp")


# --- 並び順が価値になる 2 つの条件 ---

def conditions_figure():
    f = Svg(960, 470, "トランザクションが実行前に読めることと、ブロックを作る者が並び順を選べること")
    # 条件 1: 公開の置き場
    f.text(230, 44, "条件 1: 実行前に誰でも読める", 24)
    f.box(30, 66, 400, 250, FILL, "#cccccc", 2)
    f.text(230, 104, "公開 mempool（トランザクションを置く場所）", 17, SUB)
    f.box(60, 126, 340, 70, PALE, BLUE)
    f.text(230, 170, "A 利用者: ETH を買う", 24)
    f.arrow(230, 200, 230, 236)
    f.text(244, 226, "読む", 20, SUB, anchor="start")
    f.box(60, 240, 340, 60, OCHRE_PALE, OCHRE)
    f.text(230, 279, "searcher が B と C を作る", 22)
    # 渡す
    f.arrow(404, 270, 520, 270)
    f.text(470, 256, "渡す", 20, SUB)
    # 条件 2: 並べる
    f.text(735, 44, "条件 2: 並び順を選べる", 24)
    f.box(530, 66, 410, 250, "#ffffff", INK, 2)
    f.text(735, 104, "ブロックを作る者", 22, SUB)
    for i, (label, fill, stroke) in enumerate([("1 番目: B 買い", OCHRE_PALE, OCHRE),
                                               ("2 番目: A 利用者", PALE, BLUE),
                                               ("3 番目: C 売り", OCHRE_PALE, OCHRE)]):
        y = 124 + i * 62
        f.box(570, y, 330, 50, fill, stroke)
        f.text(735, y + 34, label, 22)
    f.text(480, 372, "プロトコルが決めるのは、同じ送り主のトランザクションを nonce の順に並べることだけ", 19, SUB)
    f.text(480, 420, "2 つが揃うと、他人のトランザクションを挟むように前後に自分のトランザクションを差し込める", 20)
    f.save("mev_conditions.webp")


# --- slippage tolerance ごとの損失と利益 ---

def slippage_figure():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({
        "font.family": "Noto Sans CJK JP",
        "figure.figsize": (6.4, 3.8),
        "font.size": 11,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.alpha": 0.3,
        "grid.linewidth": 0.5,
    })
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
    ax.plot(x, loss, color=RED, linestyle="--", linewidth=2,
            label="利用者の損失（1 ETH = 3,000 USDC で換算）")
    ax.plot(x, profit, color=BLUE, linewidth=2.2,
            label="攻撃者の利益（gas 代を引く前）")
    ax.fill_between(x, profit, loss, color=FILL)
    ax.text(3.6, 130, "差の大半は、攻撃者の 2 回の\n交換で払うプールの手数料", color=SUB,
            fontsize=10, ha="center")
    ax.set_xlabel("slippage tolerance（受取量の許容幅、%）")
    ax.set_ylabel("USDC")
    ax.set_xlim(0, 5.1)
    ax.set_ylim(0, None)
    ax.legend(loc="upper left", frameon=False)
    with tempfile.TemporaryDirectory() as tmp:
        png = pathlib.Path(tmp) / "fig.png"
        fig.savefig(png, dpi=200, bbox_inches="tight", facecolor="#ffffff")
        to_webp(png, "mev_slippage.webp")
    plt.close(fig)


if __name__ == "__main__":
    concept_figure()
    conditions_figure()
    slippage_figure()
