"""Generate the figures of the keyset pagination note.

python3 figures.py で images/ の WebP を作り直す。
数値は lab/bench.csv（PostgreSQL 17.11、手元の 1 回の実行）から取った。
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


def speed_figure():
    """同じ 20 件を読む時間を、読む位置（先頭から何件目か）ごとに並べる。"""
    rows = [r.split(",") for r in (HERE / "lab" / "bench.csv").read_text().split()[1:]]
    pos = [int(r[0]) / 10000 for r in rows]
    off = [float(r[1]) for r in rows]
    key = [float(r[2]) for r in rows]
    plt.rcParams.update({
        "font.family": "Noto Sans CJK JP", "font.size": 10, "axes.edgecolor": SUB,
        "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK, "text.color": INK,
        "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
    })
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    ax.plot(pos, off, "o-", color=OCHRE, lw=2, ms=4, label="OFFSET")
    ax.plot(pos, key, "o-", color=BLUE, lw=2, ms=4, label="キーセット")
    ax.annotate(f"{off[-1]:.1f} ms", (pos[-1], off[-1]), xytext=(-8, 6),
                textcoords="offset points", ha="right", fontsize=9, color=INK)
    ax.annotate(f"{key[-1]:.3f} ms", (pos[-1], key[-1]), xytext=(-8, 6),
                textcoords="offset points", ha="right", fontsize=9, color=INK)
    ax.set_xlabel("読み始める位置（先頭から何万件目か）")
    ax.set_ylabel("20 件を読む時間（ms）")
    ax.set_xlim(0, 104)
    ax.set_ylim(0, max(off) * 1.15)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(loc="upper left", frameon=False)
    fig.tight_layout()
    with tempfile.TemporaryDirectory() as tmp:
        png = Path(tmp) / "fig.png"
        fig.savefig(png, dpi=200)
        png_to_webp(png, "keyset-pagination_speed.webp")


def scan_figure():
    """索引の葉に並んだ行を、OFFSET は先頭から数えて捨て、キーセットは木を下りて途中から読む。"""
    s = Svg(1000, 470, "OFFSET は索引の先頭から 999,980 件を数えて捨て、残りの 20 件を返す。"
                       "キーセットは前のページの最後の値で索引の木を下り、その次から 20 件を読む")
    # 索引の木（キーセットが通る道を青で描く）
    s.line(500, 68, 240, 110)
    s.line(500, 68, 500, 110)
    s.line(500, 68, 760, 110, BLUE, 5)
    s.line(760, 154, 726, 226, BLUE, 5)
    s.box(440, 24, 120, 44, GRAY_PALE, LINE)
    s.text(500, 54, "根", 22)
    for x in (180, 440, 700):
        s.box(x, 110, 120, 44, GRAY_PALE, BLUE if x == 700 else LINE)
    s.text(500, 140, "中間", 22)
    # 葉（新しい順）
    s.text(40, 214, "葉に並ぶキー（新しい順。数字は先頭から何件目か）", 19, anchor="start", cls="sub")
    xs = [40 + k * 92 for k in range(10)]
    labels = ["1", "2", "3", "…", "…", "…", "999,980", "999,981", "…", "100 万"]
    for x, lab in zip(xs, labels):
        s.box(x, 226, 84, 44, BLUE_PALE if lab == "999,981" else "#ffffff",
              BLUE if lab == "999,981" else LINE)
        s.text(x + 42, 255, lab, 17)
    # OFFSET
    s.box(40, 300, 636, 30, OCHRE_PALE, OCHRE, rx=4)
    s.text(358, 322, "OFFSET 999980：先頭から数えて捨てる（表のレコードも読む）", 19)
    s.box(684, 300, 276, 30, OCHRE, OCHRE, rx=4)
    s.text(822, 322, "返す 20 件", 19, fill="#ffffff")
    # キーセット
    s.box(684, 360, 276, 30, BLUE, BLUE, rx=4)
    s.text(822, 382, "返す 20 件", 19, fill="#ffffff")
    s.text(660, 382, "キーセット：前のページの最後の値で木を下りる（青の道）", 19, anchor="end")
    s.text(500, 440, "どちらも返すのは同じ 20 件。違うのは、そこに着くまでに触るレコードの数", 20, cls="sub")
    s.save("keyset-pagination_scan.webp")


def shift_figure():
    """1 ページ目を読んだ後に 3 件増えると、OFFSET の 2 ページ目は 1 ページ目の 3 件と重なる。"""
    s = Svg(1000, 400, "1 ページ目に 20〜16 を読んだ後、21〜23 が先頭に入る。OFFSET 5 は 18〜14 を返し、"
                       "18・17・16 が重なる。キーセットは 16 の次から 15〜11 を返す")
    w, g, x0 = 52, 6, 230

    def cx(k):
        return x0 + k * (w + g)

    def row(y, ids, colors, label):
        s.text(40, y + 30, label, 19, anchor="start", cls="sub")
        for k, (i, (fill, stroke)) in enumerate(zip(ids, colors)):
            s.box(cx(k), y, w, 44, fill, stroke)
            s.text(cx(k) + w / 2, y + 30, str(i), 19)

    white, new, p1 = ("#ffffff", LINE), (GRAY_PALE, SUB), (BLUE_PALE, BLUE)
    row(40, list(range(20, 10, -1)), [p1] * 5 + [white] * 5, "1 ページ目を読んだ時")
    s.text((cx(0) + cx(5) - g) / 2, 110, "1 ページ目（20〜16）", 17, cls="sub")
    row(160, [23, 22, 21] + list(range(20, 10, -1)), [new] * 3 + [p1] * 5 + [white] * 5, "3 件増えた後")
    s.text((cx(0) + cx(3) - g) / 2, 230, "新しい 3 件", 17, cls="sub")
    # OFFSET 5 は 6〜10 件目、キーセットは 16 の次から
    s.box(cx(5), 214, cx(10) - cx(5) - g, 12, OCHRE, OCHRE, rx=3)
    s.text(cx(10), 225, "OFFSET", 15, anchor="start", fill=OCHRE)
    s.text(40, 300, "OFFSET 5 の 2 ページ目", 19, anchor="start", fill=OCHRE)
    s.text(300, 300, "18 17 16 15 14（18〜16 は 1 ページ目でも見た）", 19, anchor="start")
    s.box(cx(8), 234, cx(13) - cx(8) - g, 12, BLUE, BLUE, rx=3)
    s.text(cx(8) - 8, 245, "キーセット", 15, anchor="end", fill=BLUE)
    s.text(40, 350, "キーセットの 2 ページ目", 19, anchor="start", fill=BLUE)
    s.text(300, 350, "15 14 13 12 11（16 の次から）", 19, anchor="start")
    s.save("keyset-pagination_shift.webp")


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    speed_figure()
    scan_figure()
    shift_figure()
