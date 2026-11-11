"""Generate the figures of the MVCC and VACUUM note.

python3 figures.py で images/ の WebP を作り直す。
数値は lab/sizes.csv と lab/output.txt（PostgreSQL 17.11、手元の 1 回の実行）から取った。
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


def size_figure():
    """10 万件の全件を 10 回更新した時の表の大きさ（条件ごと）。"""
    rows = [r.split(",") for r in (HERE / "lab" / "sizes.csv").read_text().split()[1:]]
    data = {}
    for c, r, mb, _ in rows:
        data.setdefault(c, []).append((int(r), float(mb)))
    plt.rcParams.update({
        "font.family": "Noto Sans CJK JP", "font.size": 10, "axes.edgecolor": SUB,
        "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK, "text.color": INK,
        "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
    })
    fig, ax = plt.subplots(figsize=(7.2, 3.7))
    style = {"none": ("VACUUM しない", OCHRE, "o-", 2.4),
             "hold": ("毎回 VACUUM、古いスナップショットあり", RED, "s--", 1.6),
             "vacuum": ("毎回 VACUUM", BLUE, "o-", 2.4)}
    for c in ("none", "hold", "vacuum"):
        label, color, fmt, lw = style[c]
        xs, ys = zip(*data[c])
        ax.plot(xs, ys, fmt, color=color, lw=lw, ms=4, label=label)
    ax.annotate(f"{data['none'][-1][1]:.0f} MB", (10, data["none"][-1][1]), xytext=(-6, 8),
                textcoords="offset points", ha="right", fontsize=9)
    ax.annotate(f"{data['vacuum'][-1][1]:.0f} MB", (10, data["vacuum"][-1][1]), xytext=(-6, 8),
                textcoords="offset points", ha="right", fontsize=9)
    ax.annotate("この 2 本は重なっている", (6, data["none"][6][1]), xytext=(6.4, 60),
                fontsize=9, color=SUB, arrowprops=dict(arrowstyle="-", color=SUB, lw=0.8))
    ax.set_xlabel("全件を更新した回数")
    ax.set_ylabel("表の大きさ（MB）")
    ax.set_xticks(range(0, 11))
    ax.set_ylim(0, 170)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(loc="upper left", frameon=False)
    fig.tight_layout()
    with tempfile.TemporaryDirectory() as tmp:
        png = Path(tmp) / "fig.png"
        fig.savefig(png, dpi=200)
        png_to_webp(png, "mvcc-vacuum_size.webp")


def versions_figure():
    """UPDATE で古い版が残り、新しい版が足される。xmin と xmax で、どの読み手に見えるかが決まる。"""
    s = Svg(1000, 400, "ブロックの中に、残高 100 の古い版（xmin 741、xmax 742）と、残高 200 の新しい版"
                       "（xmin 742、xmax 0）が並ぶ。742 の確定より前のスナップショットは古い版を、後のスナップショットは新しい版を読む")
    s.box(40, 40, 600, 300, GRAY_PALE, LINE, rx=6)
    s.text(60, 76, "表のブロック 0", 19, anchor="start", cls="sub")

    def ver(y, title, xmin, xmax, fill, stroke):
        s.box(70, y, 540, 90, fill, stroke)
        s.text(90, y + 38, title, 21, anchor="start")
        s.text(90, y + 72, f"xmin {xmin}（作った）・xmax {xmax}", 17, anchor="start", cls="sub")

    ver(100, "1 番: id 1、残高 100（古い版）", 741, "742（消した）", "#ffffff", LINE)
    ver(220, "3 番: id 1、残高 200（新しい版）", 742, "0（まだ消されていない）", BLUE_PALE, BLUE)
    s.arrow(600, 160, 600, 214)
    s.text(800, 120, "742 の確定より前の", 18)
    s.text(800, 146, "スナップショット", 18)
    s.arrow(712, 140, 618, 140)
    s.text(800, 250, "742 の確定より後の", 18)
    s.text(800, 276, "スナップショット", 18)
    s.arrow(712, 262, 618, 262)
    s.text(500, 380, "UPDATE（トランザクション 742）は 1 番の中身を書き換えず、xmax だけを付けて 3 番を足す", 18, cls="sub")
    s.save("mvcc-vacuum_versions.webp")


def horizon_figure():
    """古いスナップショットより後に消された版は、VACUUM が消せない。"""
    s = Svg(1000, 360, "トランザクション ID の軸の上に、古いスナップショットの境目 797 と、今の ID 817 がある。"
                       "797 より前に消された版は VACUUM で消せる。797 から 817 の間の 10 回の UPDATE で消された 100 万の版は消せない")
    s.line(60, 170, 950, 170, SUB, 3)
    s.text(60, 200, "トランザクション ID →", 16, anchor="start", cls="sub")
    s.box(60, 110, 340, 50, GRAY_PALE, LINE, rx=4)
    s.text(230, 142, "ここで消された版は消せる", 18)
    s.box(420, 110, 400, 50, OCHRE_PALE, OCHRE, rx=4)
    s.text(620, 142, "ここで消された版は消せない", 18)
    for k in range(10):
        x = 440 + k * 38
        s.p.append(f'<circle cx="{x}" cy="170" r="5" fill="{OCHRE}"/>')
    s.text(620, 228, "10 回の UPDATE（消された版は合わせて 100 万）", 16, cls="sub")
    s.line(410, 70, 410, 250, RED, 4)
    s.text(410, 40, "797：古いスナップショットの境目", 18, fill=RED)
    s.text(410, 64, "（backend_xmin = removable cutoff）", 15, fill=RED)
    s.line(840, 90, 840, 190, INK, 3)
    s.text(840, 80, "今（817 前後）", 17)
    s.text(500, 300, "境目を持つトランザクションは、797 以降に確定した変更を見ないので、", 17, cls="sub")
    s.text(500, 328, "797 以降の更新で消された古い版を、まだ読むかもしれない", 17, cls="sub")
    s.save("mvcc-vacuum_horizon.webp")


def wrap_figure():
    """32 ビットのトランザクション ID の円。今の ID から見て、前の半周が過去、後の半周が未来。"""
    import math
    s = Svg(1000, 470, "トランザクション ID を約 40 億で一周する円で描く。今の ID から見て、反時計回りの半周（約 20 億）が過去、"
                       "時計回りの半周が未来。凍結していない古い版の xmin は、今の ID が進むと過去の半周から外れ、未来の側に入って見えなくなる")
    cx, cy, r = 300, 240, 170
    s.p.append(f'<path d="M{cx},{cy - r} A{r},{r} 0 0,0 {cx},{cy + r}" fill="none" stroke="{BLUE}" stroke-width="22"/>')
    s.p.append(f'<path d="M{cx},{cy + r} A{r},{r} 0 0,0 {cx},{cy - r}" fill="none" stroke="{OCHRE}" stroke-width="22"/>')
    s.text(cx - r - 30, cy - 40, "過去", 22, anchor="end")
    s.text(cx - r - 30, cy - 12, "約 20 億", 16, anchor="end", cls="sub")
    s.text(cx + r + 30, cy + 60, "未来", 22, anchor="start")
    s.text(cx + r + 30, cy + 88, "約 20 億", 16, anchor="start", cls="sub")
    s.p.append(f'<circle cx="{cx}" cy="{cy - r}" r="11" fill="{INK}"/>')
    s.text(cx, cy - r - 24, "今の ID", 19)
    a = math.radians(115)
    px, py = cx + r * math.cos(a), cy + r * math.sin(a)
    s.p.append(f'<circle cx="{px:.0f}" cy="{py:.0f}" r="9" fill="#ffffff" stroke="{RED}" stroke-width="4"/>')
    s.text(px + 10, py + 44, "古い版の xmin（過去の端の近く）", 16, anchor="middle", fill=RED)
    s.text(cx, cy + 6, "32 ビット", 18, cls="sub")
    s.text(cx, cy + 30, "約 40 億で一周", 18, cls="sub")
    s.text(600, 140, "今の ID が進むと、円の上の「今」も回る。", 18, anchor="start")
    s.text(600, 175, "今がさらに進むと、古い版の xmin は", 18, anchor="start")
    s.text(600, 205, "未来の側に入り、その版は見えなくなる。", 18, anchor="start")
    s.text(600, 265, "VACUUM が古い版に凍結の印を付けると、", 18, anchor="start")
    s.text(600, 295, "xmin を比べずに常に過去として扱う。", 18, anchor="start")
    s.save("mvcc-vacuum_wrap.webp")


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    size_figure()
    versions_figure()
    horizon_figure()
    wrap_figure()
