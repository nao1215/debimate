"""Generate the figures of the UUIDv7 primary key note.

python3 figures.py で images/ の WebP を作り直す。
数値は lab/dirty_blocks.csv と lab/output.txt（PostgreSQL 18.6、手元の 1 回の実行）から取った。
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


def dirty_figure():
    """CHECKPOINT の直後に 1 万件を足した時、書き換わった索引のブロックの位置を主キーの型ごとに並べる。"""
    pages = {"t_bigint": 2772, "t_v4": 4923, "t_v7": 3891}  # lab/output.txt の index_pages
    blocks = {k: [] for k in pages}
    for line in (HERE / "lab" / "dirty_blocks.csv").read_text().split()[1:]:
        k, b = line.split(",")
        blocks[k].append(int(b))
    plt.rcParams.update({
        "font.family": "Noto Sans CJK JP", "font.size": 10, "axes.edgecolor": SUB,
        "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK, "text.color": INK,
        "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
    })
    rows = [("t_v7", "UUIDv7", BLUE), ("t_v4", "UUIDv4", OCHRE), ("t_bigint", "bigint の連番", SUB)]
    fig, ax = plt.subplots(figsize=(7.4, 2.9))
    for y, (k, label, color) in enumerate(rows):
        ax.barh(y, pages[k], height=0.62, color=GRAY_PALE, edgecolor=LINE, linewidth=0.8)
        ax.vlines(blocks[k], y - 0.31, y + 0.31, color=color, linewidth=0.6)
        ax.text(pages[k] + 60, y, f"{len(blocks[k]):,} / {pages[k]:,}", va="center", fontsize=9)
    ax.set_yticks(range(len(rows)), [r[1] for r in rows])
    ax.set_xlim(0, 5700)
    ax.set_xlabel("索引のファイルの中のブロックの番号（灰色の帯が索引の全体）")
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="y", length=0)
    fig.tight_layout()
    with tempfile.TemporaryDirectory() as tmp:
        png = Path(tmp) / "fig.png"
        fig.savefig(png, dpi=200)
        png_to_webp(png, "uuidv7-primary-key_dirty.webp")


def layout_figure():
    """UUIDv4 と UUIDv7 の 128 ビットの使い道を並べる。"""
    s = Svg(1000, 330, "UUIDv4 はバージョンと変種の 6 ビットを除く 122 ビットが乱数。UUIDv7 は先頭 48 ビットが "
                       "ミリ秒の Unix 時刻で、続くバージョンの 4 ビット、12 ビット、変種の 2 ビット、62 ビットの乱数が並ぶ")
    x0, w = 150, 820
    scale = w / 128

    def seg(y, start, bits, label, fill, stroke):
        x = x0 + start * scale
        s.box(x, y, bits * scale, 56, fill, stroke, rx=2)
        if label:
            s.text(x + bits * scale / 2, y + 35, label, 19 if bits > 20 else 14)

    s.text(40, 98, "UUIDv4", 22, anchor="start")
    seg(64, 0, 48, "乱数", OCHRE_PALE, OCHRE)
    seg(64, 48, 4, "4", GRAY_PALE, LINE)
    seg(64, 52, 12, "乱数", OCHRE_PALE, OCHRE)
    seg(64, 64, 2, "", GRAY_PALE, LINE)
    seg(64, 66, 62, "乱数", OCHRE_PALE, OCHRE)
    s.text(40, 208, "UUIDv7", 22, anchor="start")
    seg(174, 0, 48, "Unix 時刻（ミリ秒、48 ビット）", BLUE_PALE, BLUE)
    seg(174, 48, 4, "7", GRAY_PALE, LINE)
    seg(174, 52, 12, "12 ビット", GRAY_PALE, LINE)
    seg(174, 64, 2, "", GRAY_PALE, LINE)
    seg(174, 66, 62, "乱数（62 ビット）", OCHRE_PALE, OCHRE)
    for b in (0, 48, 64, 128):
        s.text(x0 + b * scale, 40, str(b), 16, cls="sub")
    s.text(x0, 270, "4・7 の箱はバージョン（version）、細い灰色は変種（variant）の 2 ビット", 17,
           anchor="start", cls="sub")
    s.text(x0, 300, "12 ビットは乱数でもよく、PostgreSQL 18 はミリ秒未満の時刻に使う", 17,
           anchor="start", cls="sub")
    s.save("uuidv7-primary-key_layout.webp")


def fpw_figure():
    """チェックポイントの後、各ブロックを最初に書き換える時だけ 8 KB を丸ごと WAL に書く。"""
    s = Svg(1000, 360, "時間の流れに沿って、チェックポイントの後にブロック A を書き換えると 8 KB 丸ごと、"
                       "2 回目は差分だけ。ブロック B も最初は丸ごと。次のチェックポイントの後は、A も再び丸ごとになる")
    s.line(60, 120, 960, 120, SUB, 2)
    s.text(960, 150, "時間", 17, anchor="end", cls="sub")
    for x, lab in ((90, "チェックポイント"), (690, "次のチェックポイント")):
        s.line(x, 70, x, 300, INK, 3)
        s.text(x + 8, 58, lab, 18, anchor="start")
    events = [(190, "A", True), (300, "A", False), (410, "B", True), (520, "A", False),
              (790, "A", True)]
    for x, blk, full in events:
        s.p.append(f'<circle cx="{x}" cy="120" r="7" fill="{INK}"/>')
        s.text(x, 100, f"{blk} を書き換え", 16)
        h = 120 if full else 22
        fill, stroke = (OCHRE_PALE, OCHRE) if full else (BLUE_PALE, BLUE)
        s.box(x - 50, 170, 100, h, fill, stroke, rx=3)
        s.text(x, 170 + h / 2 + 7 if full else 210, "8 KB 丸ごと" if full else "差分", 15)
    s.text(90 + 8, 330, "WAL に書く量（四角の高さ）", 16, anchor="start", cls="sub")
    s.save("uuidv7-primary-key_fpw.webp")


def insert_figure():
    """葉はキーの順に並ぶ。UUIDv7 の新しい値は右端の葉に、UUIDv4 の新しい値はあちこちの葉に入る。"""
    s = Svg(1000, 330, "葉のブロックがキーの小さい順に左から並ぶ。UUIDv7 の新しい値 3 つは全て右端の葉に入る。"
                       "UUIDv4 の新しい値 3 つは、左・中ほど・右寄りの別々の葉に入る")
    x0, w, n = 170, 70, 10

    def leaves(y, hits, color, pale):
        for k in range(n):
            hit = k in hits
            s.box(x0 + k * (w + 8), y, w, 50, pale if hit else "#ffffff", color if hit else LINE)
        s.text(x0 - 20, y + 32, "", 18)

    s.text(x0, 40, "葉のブロック（左ほどキーが小さい）", 17, anchor="start", cls="sub")
    s.text(40, 112, "UUIDv7", 22, anchor="start")
    leaves(80, {9}, BLUE, BLUE_PALE)
    s.text(40, 252, "UUIDv4", 22, anchor="start")
    leaves(220, {1, 5, 7}, OCHRE, OCHRE_PALE)
    for k, y, color in ((9, 80, BLUE), (1, 220, OCHRE), (5, 220, OCHRE), (7, 220, OCHRE)):
        cx = x0 + k * (w + 8) + w / 2
        s.line(cx, y - 28, cx, y - 4, color, 4)
        s.p.append(f'<path d="M{cx-7},{y-12} L{cx},{y-2} L{cx+7},{y-12} z" fill="{color}"/>')
    s.text(x0 + 9 * (w + 8) + w / 2, 160, "新しい値は全てここ", 16, cls="sub")
    s.text(x0 + 4 * (w + 8), 310, "新しい値ごとに別の葉（1 万件で索引のブロックの 86%）", 16, cls="sub")
    s.save("uuidv7-primary-key_insert.webp")


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    dirty_figure()
    layout_figure()
    fpw_figure()
    insert_figure()
