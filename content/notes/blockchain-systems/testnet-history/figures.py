"""Generate the figures of the testnet-history note.

lifespans(): years in which each Ethereum testnet ran (year resolution).
holesky_split(): the Holesky split of 2025-02-24 (SVG rendered by headless Chrome).
reward(): block subsidy by height, halving every 210,000 blocks (mainnet and testnet3).
activation(): the days Pectra and Fusaka went live on each network (UTC),
from the tables of EIP-7600 and EIP-7607.

Needs matplotlib and Pillow.
Run: python3 content/notes/blockchain-systems/testnet-history/figures.py
"""

import io
import subprocess
import tempfile
from datetime import date, timedelta
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from html import escape

from PIL import Image

HERE = Path(__file__).resolve().parent
INK, SUB, GRID = "#1f1f1f", "#666666", "#dddddd"
BLUE, OCHRE, GRAY = "#7aa6c2", "#d4a24c", "#9a9a9a"
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 13, "text.color": INK, "axes.labelcolor": INK,
                     "xtick.color": INK, "ytick.color": INK, "axes.edgecolor": SUB})


def save(fig, name):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, facecolor="#ffffff", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    Image.open(buf).convert("RGB").save(HERE / "images" / name, "WEBP", quality=90, method=6)


def lifespans():
    # (name, first year, last year or None = running in Nov 2026, how blocks were made)
    nets = [
        ("Ropsten", 2016, 2022, "PoW, later PoS"),
        ("Rinkeby", 2017, 2023, "PoA"),
        ("Goerli", 2019, 2024, "PoA, later PoS"),
        ("Sepolia", 2021, None, "apps and contracts"),
        ("Holesky", 2023, 2025, "validators"),
        ("Hoodi", 2025, None, "validators and infra"),
    ]
    fig, ax = plt.subplots(figsize=(9, 3.9))
    end_axis = 2026 + 10.5 / 12  # mid-November 2026
    for i, (name, start, end, note) in enumerate(nets):
        y = len(nets) - 1 - i
        running = end is None
        right = end_axis if running else end + 0.5  # ended rows stop mid-year
        ax.barh(y, right - start, left=start, height=0.56,
                color=BLUE if running else "#ececec", edgecolor=BLUE if running else GRAY, linewidth=1.2)
        label = f"{start}–" if running else f"{start}–{end}"
        ax.text(start + 0.15, y, label, va="center", ha="left", fontsize=12,
                color="#ffffff" if running else INK)
    ax.set_yticks(range(len(nets)), [n[0] for n in reversed(nets)])
    ax.set_xlim(2016, 2027.2)
    ax.set_xticks(range(2016, 2028))
    ax.set_xticklabels([str(y) if y % 2 == 0 else "" for y in range(2016, 2028)])
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.axvline(end_axis, color=SUB, linewidth=1, linestyle=(0, (4, 3)))
    ax.text(end_axis, len(nets) - 0.35, "2026 年 11 月", ha="center", va="bottom", fontsize=11, color=SUB)
    save(fig, "testnet-history_lifespans.webp")


def activation():
    rows = ["Holesky", "Sepolia", "Hoodi", "メインネット"]
    upgrades = {
        "Pectra": [date(2025, 2, 24), date(2025, 3, 5), date(2025, 3, 26), date(2025, 5, 7)],
        "Fusaka": [date(2025, 10, 1), date(2025, 10, 14), date(2025, 10, 28), date(2025, 12, 3)],
    }
    fig, ax = plt.subplots(figsize=(9, 3.2))
    for (name, days), color in zip(upgrades.items(), (OCHRE, BLUE)):
        ys = [len(rows) - 1 - i for i in range(len(rows))]
        ax.plot(days, ys, color=color, linewidth=1.5, zorder=1)
        ax.scatter(days, ys, s=70, color=color, zorder=2)
        for d, y in zip(days, ys):
            ax.text(d, y + 0.28, d.strftime("%m-%d"), ha="center", fontsize=11, color=INK)
        ax.text(days[-1] + timedelta(days=12), ys[-1], name, va="center", fontsize=13, color=color)
    ax.set_yticks(range(len(rows)), list(reversed(rows)))
    ax.set_ylim(-0.6, len(rows) - 0.3)
    ax.set_xlim(date(2025, 1, 15), date(2026, 1, 20))
    ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 3, 5, 7, 9, 11]))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.tick_params(axis="y", length=0)
    save(fig, "testnet-history_activation.webp")


FONT = "'Noto Sans CJK JP','Hiragino Sans',sans-serif"
RED, RED_PALE, BLUE_PALE, GRAY_PALE, OCHRE_PALE = "#c0504d", "#f6dcdb", "#eaf1f5", "#f2f2f2", "#f8eed8"


def save_svg(parts, w, h, name):
    with tempfile.TemporaryDirectory() as tmp:
        svg, png = Path(tmp) / "fig.svg", Path(tmp) / "fig.png"
        svg.write_text("\n".join(parts + ["</svg>"]) + "\n", encoding="utf-8")
        subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--hide-scrollbars",
                        "--force-device-scale-factor=2", f"--window-size={w},{h}",
                        f"--screenshot={png}", svg.as_uri()], check=True, capture_output=True)
        Image.open(png).convert("RGB").save(HERE / "images" / name, "WEBP", quality=90, method=6)


def holesky_split():
    """One block with deposits splits Holesky; most nodes follow the invalid side; finality stops ~2 weeks."""
    w, h = 960, 410
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img">'
         f'<title>{escape("2025-02-24 に Holesky の列が 2 本に分かれ、確定が 3 月 10 日まで止まった")}</title>',
         f"<style>text{{font-family:{FONT};fill:{INK}}} .sub{{fill:{SUB}}}</style>",
         f'<rect width="{w}" height="{h}" fill="#ffffff"/>']

    def t(x, y, s, size=20, anchor="middle", cls=""):
        c = f' class="{cls}"' if cls else ""
        p.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}"{c}>{escape(s)}</text>')

    def blk(x, y, fill, stroke, dash=False):
        d = ' stroke-dasharray="5 3"' if dash else ""
        p.append(f'<rect x="{x}" y="{y}" width="34" height="34" rx="4" fill="{fill}" stroke="{stroke}" stroke-width="2"{d}/>')

    def link(x1, y1, x2, y2, color):
        p.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="2"/>')

    mid = 225
    # Common part, before the split.
    for i in range(4):
        x = 40 + i * 50
        blk(x, mid - 17, GRAY_PALE, GRAY)
        if i:
            link(x - 16, mid, x, mid, GRAY)
    t(130, mid + 52, "共通の列", 19, cls="sub")
    t(130, mid + 78, "（確定済み）", 17, cls="sub")
    # The block with deposits.
    bx = 250
    link(224, mid, bx, mid, GRAY)
    p.append(f'<line x1="{bx - 8}" y1="70" x2="{bx - 8}" y2="390" stroke="{INK}" stroke-width="1.5" stroke-dasharray="6 4"/>')
    t(bx - 8, 52, "2/24 Pectra が有効", 19)
    # Invalid side (top), valid side (bottom).
    top, bot = 130, 320
    for side, y, fill, stroke, n in (("bad", top, RED_PALE, RED, 6), ("good", bot, BLUE_PALE, BLUE, 12)):
        p.append(f'<path d="M{bx - 4} {mid} C {bx + 20} {mid}, {bx + 10} {y}, {bx + 34} {y}" fill="none" stroke="{stroke}" stroke-width="2"/>')
        for i in range(n):
            x = bx + 34 + i * 50
            blk(x, y - 17, fill, stroke, dash=side == "good" and i < 6)
            if i:
                link(x - 16, y, x, y, stroke)
    t(bx + 34, top - 36, "誤った列: Geth・Nethermind・Besu が受け入れ、ノードの多くが従った", 17, anchor="start")
    t(bx + 34, bot + 52, "正しい列: Erigon・Reth は預け入れを含むブロックを拒否", 19, anchor="start")
    # Finality stall.
    sx, ex = bx + 34, bx + 34 + 6 * 50 - 8
    p.append(f'<line x1="{sx}" y1="{mid}" x2="{ex}" y2="{mid}" stroke="{SUB}" stroke-width="2"/>')
    p.append(f'<polygon points="{ex},{mid - 6} {ex + 10},{mid} {ex},{mid + 6}" fill="{SUB}"/>')
    t((sx + ex) / 2, mid - 10, "確定が止まる（約 2 週間）", 19)
    t((sx + ex) / 2, bot - 26, "点線の枠: 正しい列に票が集まらない期間", 15, cls="sub")
    rx = ex + 18
    p.append(f'<line x1="{rx}" y1="170" x2="{rx}" y2="282" stroke="{INK}" stroke-width="1.5" stroke-dasharray="6 4"/>')
    t(rx + 12, mid + 6, "3/10 正しい列で確定が戻る", 19, anchor="start")
    save_svg(p, w, h, "testnet-history_holesky.webp")


def reward():
    """Block subsidy by height: 50 BTC halved every 210,000 blocks, for both mainnet and testnet3."""
    heights = range(0, 5_400_000, 1000)
    sub = [50 / 2 ** (hh // 210_000) for hh in heights]
    fig, ax = plt.subplots(figsize=(9, 3.6))
    ax.step([hh / 1e6 for hh in heights], sub, where="post", color=GRAY, linewidth=1.6)
    ax.set_yscale("log")
    for hh, label, color, off in ((966_143, "メインネット（高さ 966,143）\n3.125 BTC", BLUE, (40, 30)),
                                  (5_128_859, "testnet3（高さ 5,128,859）\n約 0.000003 BTC", OCHRE, (-24, -30))):
        r = 50 / 2 ** (hh // 210_000)
        ax.scatter([hh / 1e6], [r], s=70, color=color, zorder=3)
        ax.annotate(label, (hh / 1e6, r), textcoords="offset points", xytext=off,
                    ha="left" if hh < 2e6 else "right", va="center", fontsize=12, color=INK)
    ax.set_xlabel("ブロックの高さ（百万）")
    ax.set_ylabel("1 ブロックの報酬（BTC）")
    ax.set_xlim(0, 5.4)
    ax.set_ylim(1e-8, 200)
    ax.grid(color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for s_ in ("top", "right"):
        ax.spines[s_].set_visible(False)
    save(fig, "testnet-history_reward.webp")


if __name__ == "__main__":
    lifespans()
    activation()
    holesky_split()
    reward()
