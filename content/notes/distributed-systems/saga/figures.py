"""Saga のノートの図を作る。

python3 figures.py で images/ の WebP を作り直す。
在庫の推移は lab/saga.py が書いた lab/stock_timeline.json から取る（先に python3 lab/saga.py を実行する）。
"""

import json
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
GREEN, GREEN_PALE = "#8fae86", "#e9f1e6"
RED, RED_PALE = "#e15759", "#fbe3e3"
GRAY_PALE = "#f2f2f2"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"


def png_to_webp(png, name):
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
            '<defs>'
            '<marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
            f'markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{SUB}"/></marker>'
            '<marker id="o" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
            f'markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{OCHRE}"/></marker>'
            '</defs>',
        ]

    def text(self, x, y, s, size=24, anchor="middle", cls=""):
        c = f' class="{cls}"' if cls else ""
        self.p.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}"{c}>'
                      f'{escape(s)}</text>')

    def box(self, x, y, w, h, fill, stroke, rx=10, sw=2.5, dash=""):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.p.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
                      f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def circle(self, cx, cy, r, fill, stroke):
        self.p.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}" stroke="{stroke}" '
                      'stroke-width="2.5"/>')

    def line(self, x1, y1, x2, y2, color=SUB, width=2.5, marker="a", dash=""):
        m = f' marker-end="url(#{marker})"' if marker else ""
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.p.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
                      f'stroke-width="{width}"{d}{m}/>')

    def path(self, d, color=SUB, width=2.5, marker="a"):
        self.p.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}" '
                      f'marker-end="url(#{marker})"/>')

    def cross(self, cx, cy, r=16):
        for dx in (-r, r):
            self.p.append(f'<line x1="{cx - dx}" y1="{cy - r}" x2="{cx + dx}" y2="{cy + r}" '
                          f'stroke="{RED}" stroke-width="6" stroke-linecap="round"/>')

    def save(self, name):
        self.p.append("</svg>")
        svg_to_webp("\n".join(self.p) + "\n", self.w, self.h, name)


def concept_figure():
    """4 つのローカルトランザクションの列。決済で失敗し、前の 2 段を後ろから補償する。"""
    s = Svg(960, 540, "注文・在庫・決済・配送の 4 段が左から右へ並ぶ。決済で失敗すると、"
                      "在庫を戻す補償と注文を取り消す補償が右から左へ走る。決済が pivot で、"
                      "配送は補償せず再試行で進める")
    xs = [30, 260, 490, 720]
    names = [("T1", "注文を作る"), ("T2", "在庫を確保"), ("T3  pivot", "決済"), ("T4", "配送を手配")]
    # 補償できる区間と、再試行で進める区間
    s.box(14, 70, 446, 400, GRAY_PALE, GRAY_PALE, rx=16, sw=0)
    s.box(704, 70, 242, 400, GREEN_PALE, GREEN_PALE, rx=16, sw=0)
    s.text(237, 52, "補償できる段", 24, cls="sub")
    s.text(825, 52, "再試行で進める段", 24, cls="sub")
    for k, (x, (t, label)) in enumerate(zip(xs, names)):
        fill, stroke = (GREEN_PALE, GREEN) if k == 3 else (BLUE_PALE, BLUE)
        dash = "8 6" if k == 3 else ""
        s.box(x, 110, 210, 120, "#ffffff" if k == 3 else fill, stroke, dash=dash)
        s.text(x + 105, 158, t, 24, cls="sub")
        s.text(x + 105, 200, label, 26)
        if k < 3:
            s.line(x + 212, 170, x + 228, 170, marker="a")
    s.cross(595, 110, 18)
    # pivot の線
    s.line(705, 84, 705, 456, color=SUB, width=2, marker="", dash="6 6")
    s.text(705, 500, "決済が通ったら、ここから先は戻さない", 22, cls="sub")
    # 補償
    comps = [(260, "C2", "在庫を戻す"), (30, "C1", "注文を取り消す")]
    for x, c, label in comps:
        s.box(x, 320, 210, 120, OCHRE_PALE, OCHRE)
        s.text(x + 105, 368, c, 24, cls="sub")
        s.text(x + 105, 410, label, 26)
    s.path("M595,232 C595,300 520,380 474,380", color=OCHRE, width=3, marker="o")
    s.line(258, 380, 244, 380, color=OCHRE, width=3, marker="o")
    s.save("saga_concept.webp")


def coordination_figure():
    """オーケストレーション（中央の指揮役から放射状）とコレオグラフィー（イベントで数珠つなぎ）。"""
    s = Svg(960, 540, "左のオーケストレーションでは中央の指揮役が 4 つのサービスに命令を送り返事を受ける。"
                      "右のコレオグラフィーでは各サービスが出したイベントを次のサービスが受けて連鎖する")
    s.text(230, 48, "オーケストレーション", 26)
    s.text(720, 48, "コレオグラフィー", 26)
    s.line(480, 70, 480, 500, color=LINE, width=1.5, marker="")
    # 左: 中央の指揮役
    cx, cy = 230, 290
    s.circle(cx, cy, 70, OCHRE_PALE, OCHRE)
    s.text(cx, cy - 4, "指揮役", 24)
    s.text(cx, cy + 26, "Saga の状態", 18, cls="sub")
    pos = [(70, 130, "注文"), (390, 130, "在庫"), (70, 450, "決済"), (390, 450, "配送")]
    for x, y, label in pos:
        s.box(x - 62, y - 34, 124, 68, BLUE_PALE, BLUE)
        s.text(x, y + 9, label, 24)
        # 命令と返事の往復を 2 本の線で
        dx, dy = x - cx, y - cy
        n = (dx * dx + dy * dy) ** 0.5
        ux, uy = dx / n, dy / n
        px, py = -uy * 9, ux * 9
        s.line(cx + ux * 74 + px, cy + uy * 74 + py, x - ux * 72 + px, y - uy * 50 + py)
        s.line(x - ux * 72 - px, y - uy * 50 - py, cx + ux * 74 - px, cy + uy * 74 - py)
    # 右: 数珠つなぎ
    chain = [(580, 150, "注文"), (840, 150, "在庫"), (840, 430, "決済"), (580, 430, "配送")]
    for x, y, label in chain:
        s.box(x - 58, y - 38, 116, 76, BLUE_PALE, BLUE)
        s.text(x, y + 9, label, 24)
    s.line(640, 150, 780, 150)
    s.line(840, 190, 840, 390)
    s.line(780, 430, 640, 430)
    s.text(710, 132, "注文を作った", 18, cls="sub")
    s.text(830, 292, "在庫を", 18, anchor="end", cls="sub")
    s.text(830, 316, "確保した", 18, anchor="end", cls="sub")
    s.text(710, 464, "決済した", 18, cls="sub")
    s.text(580, 296, "イベントを受けて", 18, cls="sub")
    s.text(580, 320, "次が動く", 18, cls="sub")
    s.save("saga_coordination.webp")


def dirty_read_figure():
    """在庫 1 個の時の推移。semantic lock の有無で、B の注文の結末が変わる。"""
    data = json.loads((HERE / "lab" / "stock_timeline.json").read_text())
    plt.rcParams.update({
        "font.family": "Noto Sans CJK JP", "font.size": 10, "axes.edgecolor": SUB,
        "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK, "text.color": INK,
        "svg.fonttype": "path", "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
    })
    fig, axes = plt.subplots(2, 1, figsize=(7.6, 4.4), sharex=True)
    end = 26
    for ax, key, title in zip(axes, ["naive", "lock"],
                              ["対策なし: 確保した分を在庫から引くだけ",
                               "semantic lock: 確保した分に「仮押さえ」の印を付ける"]):
        pts = data[key]
        ts = [p[0] for p in pts] + [end]
        av = [p[1] for p in pts] + [pts[-1][1]]
        ax.axvspan(3, 11, color=OCHRE_PALE, zorder=0)
        ax.step(ts, av, where="post", color=BLUE, lw=2.2, zorder=3)
        ax.set_ylim(-0.6, 1.9)
        ax.set_yticks([0, 1])
        ax.set_ylabel("在庫の数", fontsize=9)
        ax.set_title(title, fontsize=10, loc="left")
        ax.spines[["top", "right"]].set_visible(False)
        ax.text(7, 1.55, "A が在庫を確保してから補償で戻すまで（t=3〜11）", ha="center", fontsize=8.5, color=SUB)
        ax.text(3.2, 1.12, "A が確保", fontsize=8.5, color=SUB)
        ax.annotate("A を補償", (11, 1), (11.3, 1.12), fontsize=8.5, color=SUB)
    # 対策なし: ページは在庫切れ、B は在庫切れで断られる
    a0 = axes[0]
    a0.plot([4], [0], "o", color=SUB, zorder=4)
    a0.text(4.3, 0.18, "ページ: 在庫切れ", fontsize=8.5)
    a0.plot([7], [0], "x", color=RED, ms=11, mew=3, zorder=4)
    a0.text(7.3, -0.42, "B: 在庫切れで注文を取り消し", fontsize=8.5)
    a0.text(19, 0.55, "1 冊残ったのに、A も B も買えない", fontsize=9, ha="center")
    # semantic lock: ページは仮押さえ中、B は待って再試行
    a1 = axes[1]
    a1.plot([4], [0], "o", color=SUB, zorder=4)
    a1.text(4.3, 0.18, "ページ: 仮押さえ中", fontsize=8.5)
    a1.plot([7], [0], "o", color=OCHRE, ms=8, zorder=4)
    a1.text(7.3, -0.42, "B: 待つ", fontsize=8.5)
    a1.plot([15], [0], "o", color=GREEN, ms=8, zorder=4)
    a1.text(15.3, 0.18, "B: 再試行で確保、決済まで成功", fontsize=8.5)
    a1.set_xlabel("仮想の時刻 t（決済の処理は 5、他は 1 掛かる）", fontsize=9)
    a1.set_xlim(0, end)
    fig.tight_layout()
    with tempfile.TemporaryDirectory() as tmp:
        png = Path(tmp) / "fig.png"
        fig.savefig(png, dpi=200, facecolor="#ffffff")
        png_to_webp(png, "saga_dirty_read.webp")


def lock_figure():
    """2PC と Saga で、各サービスが在庫などのロックを持つ時間を比べる模式図。"""
    plt.rcParams.update({
        "font.family": "Noto Sans CJK JP", "font.size": 10, "axes.edgecolor": SUB,
        "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK, "text.color": INK,
        "svg.fonttype": "path", "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
    })
    services = ["注文", "在庫", "決済", "配送"]
    fig, axes = plt.subplots(2, 1, figsize=(7.6, 4.6), sharex=True)
    end = 20
    # 2PC: 各参加者は準備の後、決定が届くまでロックを持って待つ
    a = axes[0]
    for i, name in enumerate(services):
        y = 3 - i
        start = 1 + i * 0.6
        a.broken_barh([(start, 1.0)], (y - 0.3, 0.6), fc=BLUE_PALE, ec=BLUE)
        a.broken_barh([(start + 1.0, 14 - start - 1.0)], (y - 0.3, 0.6), fc=OCHRE_PALE, ec=OCHRE)
        a.broken_barh([(14, 1.0)], (y - 0.3, 0.6), fc=GREEN_PALE, ec=GREEN)
    a.axvline(14, color=SUB, lw=1, ls=(0, (4, 3)))
    a.text(14.2, 3.55, "コーディネータの決定", fontsize=9, color=SUB)
    a.text(8.6, 3, "ロックを持って待つ", fontsize=10, ha="center", va="center")
    a.set_title("2PC: 全員の準備が揃い、決定が届くまで待つ", loc="left", fontsize=10.5)
    # Saga: 各段はすぐ確定し、ロックを手放す。確定した結果は他から見える
    b = axes[1]
    for i, name in enumerate(services):
        y = 3 - i
        start = 1 + i * 3
        b.broken_barh([(start, 1.0)], (y - 0.3, 0.6), fc=BLUE_PALE, ec=BLUE)
        b.broken_barh([(start + 1.0, end - start - 1.0)], (y - 0.12, 0.24), fc=GRAY_PALE, ec=LINE)
    b.text(5.2, 2.55, "灰: 確定してロックを手放した後。結果は他の処理から見える", fontsize=9, color=SUB)
    b.set_title("Saga: 各段がローカルトランザクションをすぐ確定させる", loc="left", fontsize=10.5)
    for ax in axes:
        ax.set_yticks([3, 2, 1, 0], services)
        ax.set_ylim(-0.6, 3.9)
        ax.spines[["top", "right"]].set_visible(False)
    b.set_xlim(0, end)
    b.set_xticks([])
    b.set_xlabel("時間 →（青: 各サービスの処理、黄土: ロックを持って待つ、緑: 確定。Saga は青の終わりで確定）")
    fig.tight_layout()
    with tempfile.TemporaryDirectory() as tmp:
        png = Path(tmp) / "fig.png"
        fig.savefig(png, dpi=200, facecolor="#ffffff")
        png_to_webp(png, "saga_lock.webp")


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    concept_figure()
    coordination_figure()
    dirty_read_figure()
    lock_figure()
