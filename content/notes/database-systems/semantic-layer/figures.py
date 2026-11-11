"""Generate the figures of the semantic layer note.

python3 figures.py で images/ の WebP を作り直す。
数値は lab/seeds の CSV と、dbt Labs のベンチマーク記事（2026-04-07）の表から取った。
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


def fanout_figure():
    """注文 101 の明細 3 件と支払い 2 件を JOIN すると 6 レコードになり、支払いが 3 回数えられる。"""
    s = Svg(960, 540, "注文 101 の明細 3 件と支払い 2 件を注文番号で JOIN すると 6 レコードになり、"
                      "支払い 2420 円が 3 回数えられて 7260 円になる")
    s.text(40, 52, "注文 101", 28, anchor="start")
    # 明細
    s.text(140, 104, "明細 3 件", 24, cls="sub")
    items = ["本 1500", "文具 200×2", "文具 300"]
    for k, label in enumerate(items):
        y = 124 + k * 74
        s.box(40, y, 200, 56, BLUE_PALE, BLUE)
        s.text(140, y + 37, label, 24)
    # 支払い
    s.text(380, 104, "支払い 2 件", 24, cls="sub")
    pays = ["card 2000", "points 420"]
    for k, label in enumerate(pays):
        y = 124 + k * 74
        s.box(290, y, 180, 56, OCHRE_PALE, OCHRE)
        s.text(380, y + 37, label, 24)
    s.text(380, 312, "計 2420", 24, cls="sub")
    s.arrow(490, 230, 548, 230)
    s.text(519, 212, "JOIN", 20, cls="sub")
    # JOIN 結果: 3 x 2
    s.text(745, 104, "JOIN の結果 3 × 2 = 6 レコード", 24, cls="sub")
    for r in range(3):
        for c in range(2):
            x, y = 570 + c * 180, 124 + r * 74
            s.box(x, y, 168, 56, OCHRE_PALE, OCHRE)
            s.text(x + 84, y + 37, ["2000", "420"][c], 24)
    # 合計
    s.box(40, 380, 430, 110, GRAY_PALE, LINE)
    s.text(255, 425, "実際の支払い", 24, cls="sub")
    s.text(255, 466, "2420 円", 32)
    s.box(570, 380, 348, 110, "#fbe3e3", RED)
    s.text(744, 425, "SUM(amount)", 24, cls="sub")
    s.text(744, 466, "7260 円（3 倍）", 32)
    s.save("semantic-layer_fanout.webp")


def layer_figure():
    """利用者は指標名と切り口で問い合わせ、セマンティックレイヤーが SQL を組み立てる。"""
    s = Svg(960, 540, "ダッシュボード・表計算・LLM のエージェントが指標名と切り口で問い合わせ、"
                      "セマンティックレイヤーが定義から SQL を組み立てて DB に送る")
    users = ["ダッシュボード", "表計算", "LLM エージェント"]
    for k, u in enumerate(users):
        y = 110 + k * 130
        s.box(30, y, 230, 70, GRAY_PALE, LINE)
        s.text(145, y + 44, u, 24)
        s.arrow(262, y + 35, 356, y + 35)
    s.text(30, 80, "指標 × 切り口で問い合わせる", 22, anchor="start", cls="sub")
    s.box(360, 60, 330, 420, BLUE_PALE, BLUE, rx=12)
    s.text(525, 108, "セマンティックレイヤー", 26)
    rows = [("指標", "revenue / paid_amount"), ("エンティティ", "order / customer"),
            ("切り口（次元）", "region / category")]
    for k, (h, v) in enumerate(rows):
        y = 140 + k * 106
        s.box(385, y, 280, 86, "#ffffff", BLUE)
        s.text(525, y + 34, h, 22, cls="sub")
        s.text(525, y + 68, v, 22)
    s.arrow(692, 270, 778, 270)
    s.text(735, 252, "SQL", 22, cls="sub")
    s.box(786, 200, 150, 140, OCHRE_PALE, OCHRE, rx=12)
    s.text(861, 262, "DB", 28)
    s.text(861, 300, "テーブル", 22, cls="sub")
    s.save("semantic-layer_position.webp")


def entity_figure():
    """4 つのモデルのエンティティと、許される JOIN の向き（foreign → primary）と許されない向き。"""
    s = Svg(960, 520, "支払いと明細は order が foreign で、注文の order（primary）へつながる。注文は customer が foreign で、"
                      "顧客の customer（primary）へつながる。注文から明細・支払いへの向きと、明細と支払いの間は許されない")
    def model(x, y, title, rows, w=250):
        s.box(x, y, w, 44, GRAY_PALE, LINE, rx=4)
        s.text(x + w / 2, y + 30, title, 21)
        for k, (a, b) in enumerate(rows):
            yy = y + 44 + k * 38
            s.box(x, yy, w, 38, "#ffffff", LINE, rx=0, sw=1.5)
            s.text(x + 14, yy + 26, a, 18, anchor="start")
            s.text(x + w - 14, yy + 26, b, 16, anchor="end", cls="sub")
    model(40, 40, "明細（order_items）", [("order_item", "primary"), ("order", "foreign"), ("category", "次元")])
    model(40, 330, "支払い（payments）", [("payment", "primary"), ("order", "foreign")])
    model(380, 185, "注文（orders）", [("order", "primary"), ("customer", "foreign"), ("status", "次元")])
    model(690, 185, "顧客（customers）", [("customer", "primary"), ("region", "次元")], w=240)
    # 許される向き（foreign → primary）
    s.arrow(292, 145, 376, 250)
    s.arrow(292, 410, 376, 270)
    s.arrow(632, 290, 686, 250)
    s.text(810, 350, "矢印: foreign → primary", 15, cls="sub")
    s.text(810, 372, "（JOIN してよい向き）", 15, cls="sub")
    # 許されない向き
    s.p.append(f'<line x1="140" y1="200" x2="140" y2="324" stroke="{RED}" stroke-width="2" stroke-dasharray="7 5"/>')
    s.text(152, 258, "明細 ↔ 支払い（foreign 同士）", 15, anchor="start", fill=RED)
    s.text(152, 280, "は許されない", 15, anchor="start", fill=RED)
    s.text(480, 495, "注文から明細・支払いへの向き（primary → foreign）も、fan-out になるので組み立てない", 17,
           cls="sub")
    s.save("semantic-layer_entities.webp")


def split_figure():
    """MetricFlow は指標ごとに地域まで集計してから、地域をキーに横に並べる。"""
    s = Svg(960, 470, "支払い 6 件を地域ごとに合計した表と、明細 7 件を地域ごとに合計した表を別々に作り、"
                      "地域をキーに横に並べる。東京は 4400 円・5 点、大阪は 3850 円・5 点")
    def table(x, y, head, rows, fill, stroke, w=250):
        s.box(x, y, w, 46, fill, stroke, rx=4)
        s.text(x + w / 2, y + 31, head, 20)
        for k, (a, b) in enumerate(rows):
            yy = y + 46 + k * 42
            s.box(x, yy, w, 42, "#ffffff", stroke, rx=0, sw=1.5)
            s.text(x + 20, yy + 28, a, 20, anchor="start")
            s.text(x + w - 20, yy + 28, b, 20, anchor="end")
    s.box(30, 40, 200, 70, OCHRE_PALE, OCHRE)
    s.text(130, 70, "支払い 6 件", 22)
    s.text(130, 98, "→ 注文 → 顧客", 18, cls="sub")
    s.box(30, 250, 200, 70, BLUE_PALE, BLUE)
    s.text(130, 280, "明細 7 件", 22)
    s.text(130, 308, "→ 注文 → 顧客", 18, cls="sub")
    s.arrow(232, 75, 300, 75)
    s.arrow(232, 285, 300, 285)
    s.text(266, 60, "SUM", 16, cls="sub")
    s.text(266, 270, "SUM", 16, cls="sub")
    table(305, 30, "地域ごとの支払い額", [("東京", "4400"), ("大阪", "3850")], OCHRE_PALE, OCHRE)
    table(305, 240, "地域ごとの販売点数", [("東京", "5"), ("大阪", "5")], BLUE_PALE, BLUE)
    s.arrow(558, 100, 640, 160)
    s.arrow(558, 310, 640, 230)
    s.text(600, 200, "地域で", 16, cls="sub", anchor="middle")
    s.text(600, 220, "並べる", 16, cls="sub", anchor="middle")
    x, y, w = 650, 130, 290
    s.box(x, y, w, 46, GRAY_PALE, LINE, rx=4)
    s.text(x + 60, y + 31, "地域", 20)
    s.text(x + 160, y + 31, "支払い", 20)
    s.text(x + 245, y + 31, "点数", 20)
    for k, (r, a, b) in enumerate([("東京", "4400", "5"), ("大阪", "3850", "5")]):
        yy = y + 46 + k * 42
        s.box(x, yy, w, 42, "#ffffff", LINE, rx=0, sw=1.5)
        s.text(x + 60, yy + 28, r, 20)
        s.text(x + 185, yy + 28, a, 20, anchor="end")
        s.text(x + 265, yy + 28, b, 20, anchor="end")
    s.text(480, 420, "支払いと明細を同じ JOIN に入れないので、どちらも複製されない", 20, cls="sub")
    s.save("semantic-layer_split.webp")


def benchmark_figure():
    """dbt Labs の ACME Insurance ベンチマーク（2026-04-07）の正答率。"""
    plt.rcParams.update({
        "font.family": "Noto Sans CJK JP", "font.size": 10, "axes.edgecolor": SUB,
        "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK, "text.color": INK,
        "svg.fonttype": "path", "svg.hashsalt": "semantic-layer",
        "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
    })
    models = ["GPT-4\n(2023)", "Sonnet 4.6\n(2026)", "GPT-5.3 Codex\n(2026)"]
    panels = [
        ("レイヤーの範囲内の問い（8 問）", [26.9, 62.5, 51.2], [83.1, 100.0, 100.0]),
        ("JOIN の段数が多すぎる問い（3 問）", [48.3, 70.0, 100.0], [0.0, 0.0, 0.0]),
    ]
    fig, axes = plt.subplots(1, 2, figsize=(7.6, 3.6), sharey=True)
    x = range(len(models))
    for ax, (title, t2s, sl) in zip(axes, panels):
        b1 = ax.bar([i - 0.2 for i in x], t2s, 0.38, color=OCHRE, label="Text-to-SQL")
        b2 = ax.bar([i + 0.2 for i in x], sl, 0.38, color=BLUE, label="セマンティックレイヤー")
        for bars in (b1, b2):
            for b in bars:
                v = b.get_height()
                ax.text(b.get_x() + b.get_width() / 2, v + 2, f"{v:.1f}", ha="center",
                        fontsize=8, color=INK)
        ax.set_title(title, fontsize=10)
        ax.set_xticks(list(x), models, fontsize=8.5)
        ax.set_ylim(0, 126)
        ax.set_yticks(range(0, 101, 20))
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].set_ylabel("正答率（%）")
    axes[0].legend(loc="upper left", frameon=False, fontsize=8.5, ncol=2)
    axes[1].text(0.5, 86, "セマンティックレイヤーは\n答えずにエラーを返す（0%）", ha="center",
                 fontsize=8.5, color=SUB)
    fig.tight_layout()
    with tempfile.TemporaryDirectory() as tmp:
        png = Path(tmp) / "fig.png"
        fig.savefig(png, dpi=200)
        png_to_webp(png, "semantic-layer_benchmark.webp")


def modeled_figure():
    """全 11 問の正答率。dbt のモデルを 3 つ足す前と後（dbt Labs の記事の表）。"""
    models = ["Sonnet 4.6", "GPT-5.3 Codex"]
    before_t2s, before_sl = [64.5, 64.5], [72.7, 72.7]
    after_t2s, after_sl = [90.0, 84.1], [98.2, 100.0]
    fig, axes = plt.subplots(1, 2, figsize=(7.6, 3.4), sharey=True)
    for ax, title, t2s, sl in [(axes[0], "dbt のモデルを足す前（全 11 問）", before_t2s, before_sl),
                               (axes[1], "dbt のモデルを 3 つ足した後（全 11 問）", after_t2s, after_sl)]:
        x = range(len(models))
        b1 = ax.bar([i - 0.2 for i in x], t2s, 0.38, color=OCHRE, label="Text-to-SQL")
        b2 = ax.bar([i + 0.2 for i in x], sl, 0.38, color=BLUE, label="セマンティックレイヤー")
        for bars in (b1, b2):
            for b in bars:
                v = b.get_height()
                ax.text(b.get_x() + b.get_width() / 2, v + 2, f"{v:.1f}", ha="center",
                        fontsize=8, color=INK)
        ax.set_title(title, fontsize=10)
        ax.set_xticks(list(x), models, fontsize=9)
        ax.set_ylim(0, 126)
        ax.set_yticks(range(0, 101, 20))
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].set_ylabel("正答率（%）")
    axes[0].legend(loc="upper left", frameon=False, fontsize=8.5, ncol=2)
    fig.tight_layout()
    with tempfile.TemporaryDirectory() as tmp:
        png = Path(tmp) / "fig.png"
        fig.savefig(png, dpi=200)
        png_to_webp(png, "semantic-layer_modeled.webp")


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    fanout_figure()
    layer_figure()
    entity_figure()
    split_figure()
    benchmark_figure()
    modeled_figure()
