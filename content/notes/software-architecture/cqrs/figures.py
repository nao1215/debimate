"""Generate the figures of the CQRS note (WebP).

stale_figure() and read_after_write_figure() read the outputs in lab/.
reorder_figure() animates the measured times in lab/trace.tsv for the one
product whose read model ended on an older version.

Run: python3 content/notes/software-architecture/cqrs/figures.py
"""

import re
import statistics
import subprocess
import tempfile
from collections import defaultdict
from html import escape
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

HERE = Path(__file__).resolve().parent
INK, SUB, ACCENT, RED = "#1f1f1f", "#666666", "#7aa6c2", "#e15759"
FILL, PALE = "#f2f2f2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"
CJK = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"


class Svg:
    def __init__(self, width, height, title):
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img"><title>{escape(title)}</title>',
            f'<style>text{{font-family:{FONT};fill:{INK}}}</style>',
            '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" '
            'markerWidth="4" markerHeight="4" orient="auto">'
            f'<path d="M0,0 L10,5 L0,10 z" fill="{INK}"/></marker></defs>',
            f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        ]

    def text(self, x, y, s, size=20, color=INK, anchor="middle"):
        self.parts.append(
            f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" '
            f'style="fill:{color}">{escape(s)}</text>')

    def box(self, x, y, w, h, fill, stroke, sw=2.5, dash="", rx=10):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def path(self, d, color=INK, sw=3.5, dash=""):
        da = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{sw}" '
            f'stroke-linecap="round" marker-end="url(#arrow)"{da}/>')

    def db(self, cx, top, w, h, fill, stroke):
        rx, ry = w / 2, 8
        x = cx - rx
        self.parts.append(
            f'<path d="M{x},{top} v{h} a{rx},{ry} 0 0 0 {w},0 v{-h}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="2"/>')
        self.parts.append(
            f'<ellipse cx="{cx}" cy="{top}" rx="{rx}" ry="{ry}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="2"/>')

    def save_webp(self, name, width, height):
        """SVG を Chrome で 2 倍の解像度に描き、WebP にする。"""
        with tempfile.TemporaryDirectory(dir=HERE) as tmp:
            svg, png = Path(tmp) / "fig.svg", Path(tmp) / "fig.png"
            svg.write_text("\n".join(self.parts + ["</svg>"]) + "\n", encoding="utf-8")
            subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--hide-scrollbars",
                            "--force-device-scale-factor=2", f"--window-size={width},{height}",
                            f"--screenshot={png}", svg.as_uri()], check=True, capture_output=True)
            Image.open(png).convert("RGB").save(HERE / "images" / name, "WEBP", quality=90, method=6)


def concept_figure():
    """書き込み側と読み取り側の 2 つのモデルを、プロジェクションがつなぐ。利用者から見ると入口が 2 つある。"""
    W, H = 960, 430
    s = Svg(W, H, "CQRS の書き込み側と読み取り側")
    # 利用者
    s.box(20, 160, 130, 110, FILL, SUB)
    s.text(85, 222, "利用者", 22)
    # 書き込み側
    s.box(340, 30, 290, 150, OCHRE_PALE, OCHRE)
    s.text(485, 66, "書き込みモデル", 22)
    s.text(485, 96, "価格の規則を検査して保存", 16, SUB)
    s.db(485, 122, 170, 36, "#ffffff", OCHRE)
    s.text(485, 150, "商品の表・イベント", 15)
    # 読み取り側
    s.box(340, 250, 290, 150, PALE, ACCENT)
    s.text(485, 286, "読み取りモデル", 22)
    s.text(485, 316, "一覧の形に整えた表", 16, SUB)
    s.db(485, 342, 170, 36, "#ffffff", ACCENT)
    s.text(485, 370, "商品一覧の表", 15)
    # プロジェクション
    s.box(730, 160, 200, 110, FILL, INK)
    s.text(830, 208, "プロジェクション", 22)
    s.text(830, 238, "別のプロセスで後から", 15, SUB)
    # 矢印
    s.path("M150,190 H200 V105 H334")
    s.text(268, 92, "コマンド", 17)
    s.text(268, 132, "（価格を変える）", 14, SUB)
    s.path("M630,105 H830 V154")
    s.text(730, 70, "イベント", 17)
    s.text(730, 92, "（価格が変わった）", 14, SUB)
    s.path("M830,270 V325 H636", dash="9 7")
    s.text(730, 350, "一覧の行を書き換える", 15)
    s.text(730, 372, "（遅れて届く）", 14, RED)
    s.path("M340,325 H200 V250 H156")
    s.text(268, 312, "クエリ", 17)
    s.text(268, 352, "（一覧を見る）", 14, SUB)
    s.save_webp("cqrs_concept.webp", W, H)


def _style():
    plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10,
                         "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff"})


def _save(fig, name):
    fig.tight_layout()
    with tempfile.TemporaryDirectory(dir=HERE) as tmp:
        png = Path(tmp) / "fig.png"
        fig.savefig(png, dpi=200, facecolor="#ffffff")
        Image.open(png).convert("RGB").save(HERE / "images" / name, "WEBP", quality=90, method=6)
    plt.close(fig)


def stale_figure():
    """プロジェクションの置き方 4 通りを 10 回ずつ動かし、古い価格のまま残った商品の数と、一覧への反映に掛かった時間を並べる。"""
    runs = defaultdict(list)
    for line in (HERE / "lab" / "output_projector.txt").read_text().splitlines():
        name, _, sec, stale, _ = line.split("\t")
        runs[name].append((float(sec.split()[0]), int(re.search(r"(\d+)/", stale).group(1))))
    names = list(runs)
    labels = ["worker 1 つ", "worker 4 つ\n1 つのキュー", "worker 4 つ\n商品ごとに振り分け", "worker 4 つ\n1 つのキュー + バージョンの比較"]
    _style()
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(8.4, 3.3), sharey=True,
                                 gridspec_kw={"width_ratios": [1.3, 1]})
    for i, n in enumerate(names):
        y = len(names) - 1 - i
        stale = [s for _, s in runs[n]]
        color = RED if max(stale) else ACCENT
        for k, v in enumerate(sorted(stale)):
            a1.plot(v, y + (k - 4.5) * 0.045, "o", color=color, ms=5, alpha=0.85)
        a1.text(max(stale) + 0.4, y, f"{min(stale)}〜{max(stale)} 商品" if max(stale) else "10 回とも 0",
                va="center", fontsize=9, color=color)
        med = statistics.median(t for t, _ in runs[n])
        a2.barh(y, med, height=0.5, color=SUB if i == 0 else ACCENT)
        a2.text(med + 0.05, y, f"{med:.2f} 秒", va="center", fontsize=9)
    a1.set_yticks(range(len(names))[::-1], labels)
    a1.set_xlim(-0.5, 10)
    a1.set_xlabel("古い価格のまま残った商品（200 商品中）")
    a1.set_title("10 回の実行ごとの数", fontsize=10, color=SUB)
    a2.set_xlim(0, 3)
    a2.set_xlabel("2,000 件を一覧へ反映した秒数")
    a2.set_title("10 回の中央値", fontsize=10, color=SUB)
    for a in (a1, a2):
        a.spines[["top", "right"]].set_visible(False)
    _save(fig, "cqrs_stale.webp")


def read_after_write_figure():
    """保存から一覧を読むまでの間と、自分のコメントが一覧に載っていなかった割合。"""
    out = (HERE / "lab" / "output_read_after_write.txt").read_text()
    pts = [(int(m.group(1)), int(m.group(2)) / int(m.group(3)) * 100)
           for m in re.finditer(r"保存の (\d+)ms 後に読む\s+載っていない (\d+)/(\d+)", out)]
    wait = re.search(r"中央値 (\d+)ms 最大 (\d+)ms", out)
    _style()
    fig, ax = plt.subplots(figsize=(7.2, 3.3))
    ax.plot([0, 500, 600], [100, 0, 0], ls="--", color=SUB, lw=1.5, label="間隔 0.5 秒から計算した割合")
    ax.plot([p[0] for p in pts], [p[1] for p in pts], "o-", color=RED, ms=7, lw=2, label="実測（各 200 回）")
    for x, y in pts:
        ax.text(x + 12, y + 4, f"{y:.0f}%", fontsize=9, color=RED)
    ax.plot([int(wait.group(1))], [0], marker="v", color=ACCENT, ms=10)
    ax.annotate(f"保存した位置まで待って読む: 0%\n待ち時間は中央値 {wait.group(1)} ms・最大 {wait.group(2)} ms",
                xy=(int(wait.group(1)), 3), xytext=(-10, 14), fontsize=9, color=INK, ha="left",
                arrowprops=dict(arrowstyle="->", color=ACCENT))
    ax.set_xlim(-20, 620)
    ax.set_ylim(-5, 112)
    ax.set_xlabel("保存してから一覧を読むまでの時間（ms）")
    ax.set_ylabel("自分のコメントが\n一覧に無かった割合（%）")
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(loc="upper right", frameon=False, fontsize=9)
    _save(fig, "cqrs_read_after_write.webp")


def reorder_figure():
    """古いバージョンで止まった商品の最後の 4 つのイベントが、worker を通って読み取りモデルに書かれる順を、実測の時刻で動かす。"""
    rows = []
    for line in (HERE / "lab" / "trace.tsv").read_text().splitlines():
        p, v, w, got, wrote = line.split("\t")
        rows.append((int(p), int(v), int(w), float(got) * 1000, float(wrote) * 1000))
    by = defaultdict(list)
    for r in rows:
        by[r[0]].append(r)
    product, evs = next((p, rs) for p, rs in sorted(by.items())
                        if max(rs, key=lambda r: r[4])[1] != max(r[1] for r in rs))
    evs = sorted(evs, key=lambda r: r[1])[-4:]  # 最後の 4 つのバージョン
    t0 = min(r[3] for r in evs) - 0.2
    t1 = max(r[4] for r in evs) + 0.8
    STEP, SLOW = 0.1, 2500  # 0.1 ms ずつ、実時間の 2500 分の 1 の速さ
    S, W, H = 2, 960, 470
    font = lambda n: ImageFont.truetype(CJK, n * S)  # noqa: E731
    x0, x1 = 110, 840
    X = lambda ms: (x0 + (x1 - x0) * (ms - t0) / (t1 - t0)) * S  # noqa: E731
    lane_y = {w: 120 + i * 48 for i, w in enumerate(range(4))}
    color = {evs[0][1]: "#a8a8a8", evs[1][1]: SUB, evs[2][1]: OCHRE, evs[3][1]: ACCENT}
    frames = []
    n = int((t1 - t0) / STEP) + 1
    for k in range(n):
        now = t0 + k * STEP
        im = Image.new("RGB", (W * S, H * S), "#ffffff")
        d = ImageDraw.Draw(im)
        d.text((20 * S, 12 * S), f"商品 {product} の最後の価格の変更 4 つが、読み取りモデルに書かれる順",
               font=font(20), fill=INK)
        d.text((20 * S, 42 * S), f"経過 {now:7.2f} ms（実測した時刻を、実時間の {SLOW} 分の 1 の速さで再生）",
               font=font(15), fill=SUB)
        d.text((20 * S, 78 * S), "キューに入れたバージョンの順: " + " → ".join(str(r[1]) for r in evs),
               font=font(15), fill=INK)
        d.text((470 * S, 78 * S), "棒の数字: バージョン　枠だけ: 整形中　塗り: 書いた後", font=font(14), fill=SUB)
        for w, y in lane_y.items():
            d.text((20 * S, (y + 6) * S), f"worker {w}", font=font(14), fill=SUB)
            d.line([(x0 * S, (y + 34) * S), (x1 * S, (y + 34) * S)], fill="#e6e6e6", width=1 * S)
        for p, v, w, got, wrote in evs:
            if now < got:
                continue
            y = lane_y[w]
            end = min(now, wrote)
            d.rectangle([X(got), (y + 4) * S, max(X(end), X(got) + 3 * S), (y + 30) * S],
                        fill=color[v] if now >= wrote else "#ffffff", outline=color[v], width=2 * S)
            d.text((X(got) + 5 * S, (y + 5) * S), f"{v}", font=font(14),
                   fill="#ffffff" if now >= wrote and v in (evs[1][1], evs[3][1]) else INK)
            if now >= wrote:
                d.text((X(wrote) + 4 * S, (y + 7) * S), f"{wrote:.1f} ms に書いた", font=font(12), fill=SUB)
        # 読み取りモデルの今の値
        written = [r for r in evs if r[4] <= now]
        before = [r for r in by[product] if r[4] <= now]
        cur = max(before, key=lambda r: r[4])[1]
        y = 330
        d.rectangle([60 * S, y * S, 460 * S, (y + 60) * S], fill=PALE, outline=ACCENT, width=2 * S)
        d.text((76 * S, (y + 6) * S), "読み取りモデル（一覧）", font=font(14), fill=SUB)
        d.text((76 * S, (y + 28) * S), f"商品 {product}: バージョン {cur}", font=font(18),
               fill=RED if len(written) == len(evs) and cur != evs[-1][1] else INK)
        d.rectangle([500 * S, y * S, 900 * S, (y + 60) * S], fill=OCHRE_PALE, outline=OCHRE, width=2 * S)
        d.text((516 * S, (y + 6) * S), "書き込みモデル（商品ページ）", font=font(14), fill=SUB)
        d.text((516 * S, (y + 28) * S), f"商品 {product}: バージョン {evs[-1][1]}", font=font(18), fill=INK)
        if len(written) == len(evs) and cur != evs[-1][1]:
            d.text((60 * S, 400 * S), f"バージョン {evs[-1][1]} の後にバージョン {cur} が書かれ、一覧は古いまま止まった",
                   font=font(16), fill=RED)
        # 時間の帯
        d.line([(x0 * S, 432 * S), (x1 * S, 432 * S)], fill=SUB, width=2 * S)
        tick = int(t0 * 2 + 1) / 2
        while tick < t1:
            d.line([(X(tick), 427 * S), (X(tick), 437 * S)], fill=SUB, width=2 * S)
            d.text((X(tick) - 22 * S, 442 * S), f"{tick:.1f} ms", font=font(12), fill=SUB)
            tick += 0.5
        d.line([(X(now), 108 * S), (X(now), 312 * S)], fill=INK, width=2 * S)
        d.ellipse([X(now) - 5 * S, 427 * S, X(now) + 5 * S, 437 * S], fill=INK)
        frames.append(im.resize((W, H), Image.LANCZOS))
    dur = int(STEP / 1000 * SLOW * 1000)
    durations = [dur] * (len(frames) - 1) + [3500]
    frames[0].save(HERE / "images" / "cqrs_reorder.webp", "WEBP", save_all=True, append_images=frames[1:],
                   duration=durations, loop=0, quality=70, method=6)


if __name__ == "__main__":
    (HERE / "images").mkdir(exist_ok=True)
    concept_figure()
    stale_figure()
    read_after_write_figure()
    reorder_figure()
