"""Generate the figures of the bulkhead note.

python3 figures.py で images/ の WebP を作り直す。
数値は lab/sim.py が書く lab/result.json から取る（python3 lab/sim.py --json で作り直す）。
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


import json  # noqa: E402

RESULT = json.loads((HERE / "lab" / "result.json").read_text())


def concept_figure():
    """共有のスレッドでは、止まった呼び出し先を待つ A が全体を埋める。A に上限を置くと、A は 10 本までで止まる。"""
    s = Svg(1000, 410, "左は仕切りの無いスレッド 40 本で、止まった呼び出し先を待つ要求 A が 40 本全てを埋め、要求 B は入れない。"
                       "右は A が同時に使える数を 10 本までにした場合で、A は 10 本だけを使い、残りの 30 本で B を処理できる")

    def hull(x0, title, n_a, limit):
        s.text(x0 + 210, 40, title, 21)
        s.p.append(f'<path d="M{x0},80 L{x0 + 420},80 L{x0 + 390},300 L{x0 + 30},300 Z" '
                   f'fill="#ffffff" stroke="{SUB}" stroke-width="3"/>')
        for k in range(40):
            col, row = k % 10, k // 10
            x, y = x0 + 50 + col * 32, 100 + row * 48
            fill, stroke = (OCHRE_PALE, OCHRE) if k < n_a else (BLUE_PALE, BLUE)
            s.box(x, y, 26, 38, fill, stroke, rx=3, sw=1.5)
        if limit:
            s.p.append(f'<rect x="{x0 + 42}" y="92" width="{10 * 32 + 2}" height="54" rx="6" fill="none" '
                       f'stroke="{INK}" stroke-width="3" stroke-dasharray="8 5"/>')
            s.text(x0 + 210, 330, "破線の枠：A は同時に 10 本まで（数を数えるだけで、場所は決めない）", 15, cls="sub")

    hull(40, "仕切りなし（スレッド 40 本を共有）", 40, False)
    hull(540, "Bulkhead（A は 10 本まで）", 10, True)
    s.box(150, 352, 26, 26, OCHRE_PALE, OCHRE, rx=3, sw=1.5)
    s.text(186, 372, "止まった呼び出し先を待つ要求 A", 18, anchor="start")
    s.box(560, 352, 26, 26, BLUE_PALE, BLUE, rx=3, sw=1.5)
    s.text(596, 372, "要求 B が使えるスレッド", 18, anchor="start")
    s.text(500, 402, "呼び出し先が止まって 15 秒後（25 秒の時点）のスレッドの使われ方", 16, cls="sub")
    s.save("bulkhead_concept.webp")


def timeline_figure():
    """B を処理できた割合と、A が掴んでいるスレッドの数（1 秒ごと）。"""
    plt.rcParams.update({
        "font.family": "Noto Sans CJK JP", "font.size": 10, "axes.edgecolor": SUB,
        "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK, "text.color": INK,
        "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
    })
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(7.4, 5.0), sharex=True)
    t = list(range(60))
    for name, label, color, fmt in (("shared 40", "仕切りなし", OCHRE, "-"),
                                    ("bulkhead A<=10", "Bulkhead（A は 10 本まで）", BLUE, "--")):
        r = RESULT["timeline"][name]
        rate = [100 * ok / (ok + rej) if ok + rej else 100 for ok, rej in zip(r["b_ok"], r["b_rejected"])]
        ax1.plot(t, rate, fmt, color=color, lw=2, label=label)
        ax2.plot(t, r["busy_a"], fmt, color=color, lw=2, label=label)
    for ax in (ax1, ax2):
        ax.axvspan(10, 40, color=GRAY_PALE, zorder=0)
        ax.spines[["top", "right"]].set_visible(False)
    ax1.set_ylabel("B を処理できた割合（%）")
    ax1.set_ylim(0, 110)
    ax1.text(25, 104, "呼び出し先が応答しない 30 秒", ha="center", fontsize=9, color=SUB)
    ax1.legend(loc="lower right", frameon=False, fontsize=9)
    ax2.set_ylabel("A が使うスレッド（本）")
    ax2.axhline(40, color=LINE, lw=1, ls=":")
    ax2.text(59, 41, "スレッドは全部で 40 本", ha="right", fontsize=8.5, color=SUB)
    ax2.set_ylim(0, 45)
    ax2.set_xlabel("経過時間（秒）")
    fig.tight_layout()
    with tempfile.TemporaryDirectory() as tmp:
        png = Path(tmp) / "fig.png"
        fig.savefig(png, dpi=200)
        png_to_webp(png, "bulkhead_timeline.webp")


def sweep_figure():
    """A の上限を変えた時の、平常時に断られる A の割合。"""
    sw = [r for r in RESULT["sweep"] if r["limit"] <= 20]
    plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10,
                         "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff"})
    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    xs = [r["limit"] for r in sw]
    ys = [100 * r["a_rejected_normal"] for r in sw]
    ax.plot(xs, ys, "o-", color=OCHRE, lw=2, ms=5)
    for x, y in zip(xs, ys):
        if y > 0:
            ax.annotate(f"{y:.1f}%", (x, y), xytext=(4, 6), textcoords="offset points", fontsize=8.5)
    ax.axvline(2.5, color=BLUE, lw=1.2, ls="--")
    ax.text(2.7, 62, "平常時に同時に使う本数の平均\n（毎秒 50 件 × 0.05 秒 = 2.5 本）", fontsize=8.5, color=BLUE)
    ax.set_xlabel("A に許すスレッドの上限（本）")
    ax.set_ylabel("平常時に断られた A（%）")
    ax.set_xticks([1, 2, 3, 4, 5, 6, 8, 10, 15, 20])
    ax.set_ylim(0, 80)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    with tempfile.TemporaryDirectory() as tmp:
        png = Path(tmp) / "fig.png"
        fig.savefig(png, dpi=200)
        png_to_webp(png, "bulkhead_sweep.webp")


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    concept_figure()
    timeline_figure()
    sweep_figure()
