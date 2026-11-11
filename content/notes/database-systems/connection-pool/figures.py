"""Generate the figures of the connection pool note.

python3 figures.py で images/ の WebP を作り直す。
数値は lab/bench.csv・rate.csv・connect.csv（PostgreSQL 17.11、手元の実行）から取った。
"""

import subprocess
import tempfile
from html import escape
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from PIL import Image  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE / "images"

INK, SUB, LINE = "#1f1f1f", "#666666", "#999999"
BLUE, BLUE_PALE = "#7aa6c2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
RED, GRAY_PALE = "#e15759", "#f2f2f2"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"


def png_to_webp(png, name):
    """PNG を WebP にして images/ に置く（ページを軽くし、画像検索にも載せやすくするため）。"""
    Image.open(png).convert("RGB").save(OUT / name, "WEBP", quality=90, method=6)


def svg_to_webp(svg_text, w, h, name):
    """手書きの SVG を Chrome で 2 倍の解像度に描き、WebP にする。"""
    with tempfile.TemporaryDirectory() as tmp:
        svg, png = Path(tmp) / "fig.svg", Path(tmp) / "fig.png"
        svg.write_text(svg_text, encoding="utf-8")
        subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--hide-scrollbars",
                        "--force-device-scale-factor=2", f"--window-size={w},{h}",
                        f"--screenshot={png}", svg.as_uri()], check=True, capture_output=True)
        png_to_webp(png, name)


class Svg:
    def __init__(self, w, h, title):
        self.w, self.h = w, h
        self.p = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}" role="img"><title>{escape(title)}</title>',
            f'<style>text{{font-family:{FONT};fill:{INK}}} .sub{{fill:{SUB}}}</style>',
            f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
            '<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" '
            f'markerHeight="8" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{SUB}"/></marker></defs>',
        ]

    def text(self, x, y, s, size=24, anchor="middle", cls="", fill=None):
        c = f' class="{cls}"' if cls else ""
        f = f' style="fill:{fill}"' if fill else ""
        self.p.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}"{c}{f}>'
                      f'{escape(s)}</text>')

    def box(self, x, y, w, h, fill, stroke, rx=8, sw=2):
        self.p.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
                      f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')

    def arrow(self, x1, y1, x2, y2):
        self.p.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{SUB}" '
                      'stroke-width="2" marker-end="url(#a)"/>')

    def save(self, name):
        self.p.append("</svg>")
        svg_to_webp("\n".join(self.p) + "\n", self.w, self.h, name)

    def line(self, x1, y1, x2, y2, color=LINE, sw=2, dash=""):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.p.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
                      f'stroke-width="{sw}"{d}/>')


import csv  # noqa: E402
from statistics import median  # noqa: E402


def load(name):
    with open(HERE / "lab" / name) as f:
        return list(csv.DictReader(f))


def style():
    plt.rcParams.update({
        "font.family": "Noto Sans CJK JP", "font.size": 10, "axes.edgecolor": SUB,
        "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK, "text.color": INK,
        "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
    })


def save(fig, name):
    fig.tight_layout()
    with tempfile.TemporaryDirectory() as tmp:
        png = Path(tmp) / "fig.png"
        fig.savefig(png, dpi=200)
        png_to_webp(png, name)


def concept_figure():
    """アプリに同時に 256 件の問い合わせがある時、接続を増やすと待つ場所がアプリから DB の中に移る。"""
    s = Svg(1000, 470, "アプリに同時に 256 件の問い合わせがある時。左は接続 256 本で、2 件が CPU で動き、254 件が DB の中で CPU を待つ。"
                       "右は接続 8 本で、248 件はアプリの接続プールの前で待ち、DB の中では 2 件が動いて 6 件が CPU を待つ")

    def panel(x0, title, n_conn, app_wait):
        s.text(x0 + 225, 40, title, 21)
        s.text(x0 + 60, 84, "アプリ", 17, cls="sub")
        if app_wait:
            for k in range(36):
                s.box(x0 + 20 + (k % 6) * 14, 100 + (k // 6) * 22, 10, 16, OCHRE_PALE, OCHRE, rx=2, sw=1)
            s.text(x0 + 10, 360, f"アプリで待つ問い合わせ {app_wait} 件（箱 1 つで約 7 件）", 14, anchor="start", cls="sub")
        else:
            s.text(x0 + 60, 200, "待ちは無い", 15, cls="sub")
        s.text(x0 + 200, 84, f"接続 {n_conn} 本", 17, cls="sub")
        lines = min(n_conn, 32)
        for k in range(lines):
            y = 100 + k * (200 / lines)
            s.line(x0 + 120, y + 4, x0 + 300, 200, LINE, 1)
        s.box(x0 + 300, 110, 150, 180, GRAY_PALE, LINE)
        s.text(x0 + 375, 140, "DB", 19)
        for k in range(2):
            s.box(x0 + 320 + k * 60, 220, 50, 50, BLUE_PALE, BLUE, rx=4)
            s.text(x0 + 345 + k * 60, 242, "CPU", 13)
            s.p.append(f'<circle cx="{x0 + 345 + k * 60}" cy="257" r="5" fill="{OCHRE}"/>')
        waiting = n_conn - 2
        dots = waiting if waiting <= 64 else round(waiting / 4)
        for k in range(dots):
            s.p.append(f'<circle cx="{x0 + 318 + (k % 16) * 7.5:.1f}" cy="{160 + (k // 16) * 12}" r="2.6" fill="{OCHRE}"/>')
        s.text(x0 + 450, 316, f"CPU で動く 2 件、中で CPU を待つ {waiting} 件", 15, anchor="end", cls="sub")
        if waiting > 64:
            s.text(x0 + 450, 336, "（待つ点 1 つで約 4 件）", 14, anchor="end", cls="sub")

    panel(30, "接続を多く張る", 256, 0)
    panel(510, "接続を絞り、プールで待たせる", 8, 248)
    s.text(500, 414, "アプリに同時に 256 件の問い合わせがある時。どちらも DB の CPU は 2 コアで、違うのは順番を待つ場所", 17)
    s.text(500, 444, "（左は DB の中で CPU と内部の資源を奪い合い、右はアプリの中で待つ）", 16, cls="sub")
    s.save("connection-pool_concept.webp")


def servers_figure():
    """アプリのサーバーを増やすと DB への接続数が台数倍になる。PgBouncer で DB 側の接続をまとめる。"""
    s = Svg(1000, 400, "左はアプリのサーバー 10 台がそれぞれプール 20 本を持ち、DB に 200 本の接続が来て max_connections 100 を超える。"
                       "右は 10 台が PgBouncer に繋ぎ、PgBouncer が DB への接続を 8 本にまとめる")

    def apps(x0):
        for k in range(10):
            y = 70 + k * 26
            s.box(x0, y, 90, 20, "#ffffff", LINE, rx=3, sw=1.5)
            s.text(x0 + 45, y + 15, f"アプリ {k + 1}", 12)
        return [70 + k * 26 + 10 for k in range(10)]

    s.text(250, 40, "台数 × プールの大きさ", 20)
    ys = apps(40)
    for y in ys:
        for d in range(4):
            s.line(130, y, 330, 150 + d * 18 + (y - 190) * 0.15, LINE, 1)
    s.box(330, 120, 130, 120, GRAY_PALE, RED, sw=3)
    s.text(395, 165, "DB", 20)
    s.text(395, 195, "接続 200 本", 14, fill=RED)
    s.text(395, 215, "上限 100 を超える", 13, fill=RED)
    s.text(250, 362, "10 台 × 20 本 = 200 本（線 1 本で 5 本）", 15, cls="sub")

    s.text(750, 40, "間に PgBouncer を置く", 20)
    ys = apps(530)
    for y in ys:
        for d in range(2):
            s.line(620, y, 720, 170 + d * 20, LINE, 1)
    s.box(720, 140, 110, 80, OCHRE_PALE, OCHRE)
    s.text(775, 185, "PgBouncer", 15)
    for d in range(8):
        s.line(830, 160 + d * 6, 880, 160 + d * 6, BLUE, 2)
    s.box(880, 120, 90, 120, GRAY_PALE, BLUE, sw=3)
    s.text(925, 175, "DB", 20)
    s.text(925, 200, "8 本", 14)
    s.text(750, 362, "アプリの接続は多くても、DB への接続は 8 本（左の線は 1 本で 5 本）", 15, cls="sub")
    s.save("connection-pool_servers.webp")


def sweep_figure():
    """接続数ごとの、1 秒あたりの件数と平均の待ち時間（3 回の中央値）。"""
    rows = load("bench.csv")
    cs = sorted({int(r["clients"]) for r in rows})
    tps = [median(float(r["tps"]) for r in rows if int(r["clients"]) == c) / 1000 for c in cs]
    lat = [median(float(r["latency_ms"]) for r in rows if int(r["clients"]) == c) for c in cs]
    style()
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.6, 3.4))
    ax1.plot(cs, tps, "o-", color=BLUE, lw=2, ms=4)
    ax1.set_xscale("log", base=2)
    ax1.set_xticks(cs, [str(c) for c in cs], fontsize=8)
    ax1.set_xlabel("接続数（本）")
    ax1.set_ylabel("1 秒あたりの件数（千件）")
    ax1.set_ylim(0, max(tps) * 1.2)
    ax2.plot(cs, lat, "o-", color=OCHRE, lw=2, ms=4)
    ax2.set_xscale("log", base=2)
    ax2.set_yscale("log")
    ax2.set_xticks(cs, [str(c) for c in cs], fontsize=8)
    ax2.set_xlabel("接続数（本）")
    ax2.set_ylabel("平均の応答時間（ms、対数）")
    for ax in (ax1, ax2):
        ax.spines[["top", "right"]].set_visible(False)
    save(fig, "connection-pool_sweep.webp")


def rate_figure():
    """毎秒の件数を固定した時の、接続 8 本と 256 本の平均の待ち時間（3 回の中央値）。"""
    rows = load("rate.csv")
    rates = sorted({int(r["rate"]) for r in rows})
    style()
    fig, ax = plt.subplots(figsize=(7.2, 3.5))
    for c, color, fmt in ((8, BLUE, "o-"), (256, OCHRE, "s--")):
        ys = [median(float(r["latency_ms"]) for r in rows
                     if int(r["clients"]) == c and int(r["rate"]) == rate) for rate in rates]
        ax.plot([r / 1000 for r in rates], ys, fmt, color=color, lw=2, ms=5, label=f"接続 {c} 本")
        for x, y in zip(rates, ys):
            ax.annotate(f"{y:.2f} ms" if y < 10 else f"{y:,.0f} ms", (x / 1000, y), xytext=(4, 6),
                        textcoords="offset points", fontsize=8.5)
    for cap, c, color in ((60.3, 8, BLUE), (35.0, 256, OCHRE)):
        if cap <= 42:
            ax.axvline(cap, color=color, lw=1, ls=":")
            ax.text(cap + 0.4, 6, f"接続 {c} 本が送り続けた時の件数\n（約 {cap / 10:.1f} 万件、前の実験）", fontsize=8, color=color)
    ax.set_yscale("log")
    ax.set_xlabel("毎秒の件数の目標（千件）")
    ax.set_ylabel("空き待ちを含む平均の待ち時間（ms、対数）")
    ax.set_xticks([r / 1000 for r in rates])
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(loc="upper left", frameon=False)
    save(fig, "connection-pool_rate.webp")


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    concept_figure()
    sweep_figure()
    rate_figure()
    servers_figure()
