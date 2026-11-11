"""Generate the figures of the long context note.

python3 figures.py
  - Lost in the Middle の論文（arXiv 2307.03172）の付録 Table 6 の値
  - Anthropic のシステムカード（Opus 4.6 / 4.7 / 4.8、Mythos 5）に載った値
  - lab/results_needle.jsonl と lab/results_twohop.jsonl（手元の実験）
  - MRCR と GraphWalks の課題の形（データセットの説明を縮めて描いた概念図。SVG を Chrome で WebP にする）
"""
import json
import subprocess
import tempfile
from collections import defaultdict
from html import escape
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from PIL import Image  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE / "images"
INK, SUB = "#1f1f1f", "#666666"
BLUE, OCHRE, GREEN, RED = "#7aa6c2", "#d4a24c", "#8fae86", "#e15759"

plt.rcParams.update({
    "font.family": "Noto Sans CJK JP", "font.size": 10, "axes.edgecolor": SUB,
    "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK, "text.color": INK,
    "svg.fonttype": "path", "svg.hashsalt": "long-context",
    "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
})


def save(fig, name):
    """PNG に描いてから WebP にして images/ に置く（ページを軽くするため）。"""
    fig.tight_layout()
    with tempfile.TemporaryDirectory() as tmp:
        png = Path(tmp) / "fig.png"
        fig.savefig(png, dpi=200)
        Image.open(png).convert("RGB").save(OUT / name, "WEBP", quality=90, method=6)
    plt.close(fig)


FONT = "'Noto Sans CJK JP','Hiragino Sans',sans-serif"
PALE_BLUE, PALE_OCHRE, PALE_GRAY, LINE = "#eaf1f5", "#f8eed8", "#f2f2f2", "#999999"


class Svg:
    """白い背景の手書き SVG を組み、Chrome で 2 倍の解像度に描いて WebP にする。"""

    def __init__(self, w, h, title):
        self.w, self.h = w, h
        self.p = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}" role="img"><title>{escape(title)}</title>',
            f'<style>text{{font-family:{FONT};fill:{INK}}} .sub{{fill:{SUB}}}</style>',
            f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
            '<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
            f'markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{SUB}"/></marker></defs>',
        ]

    def text(self, x, y, s, size=20, anchor="middle", cls="", fill=None):
        c = f' class="{cls}"' if cls else ""
        f = f' style="fill:{fill}"' if fill else ""
        self.p.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}"{c}{f}>'
                      f'{escape(s)}</text>')

    def box(self, x, y, w, h, fill, stroke, rx=6, sw=2, dash=False):
        d = ' stroke-dasharray="6 4"' if dash else ""
        self.p.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
                      f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def path(self, d, color=SUB, dash=False, arrow=True, sw=2):
        da = ' stroke-dasharray="6 4"' if dash else ""
        m = ' marker-end="url(#a)"' if arrow else ""
        self.p.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{sw}"{da}{m}/>')

    def circle(self, x, y, r, fill, stroke):
        self.p.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="2"/>')

    def save(self, name):
        self.p.append("</svg>")
        with tempfile.TemporaryDirectory() as tmp:
            svg, png = Path(tmp) / "fig.svg", Path(tmp) / "fig.png"
            svg.write_text("\n".join(self.p) + "\n", encoding="utf-8")
            subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--hide-scrollbars",
                            "--force-device-scale-factor=2", f"--window-size={self.w},{self.h}",
                            f"--screenshot={png}", svg.as_uri()], check=True, capture_output=True)
            Image.open(png).convert("RGB").save(OUT / name, "WEBP", quality=90, method=6)


def mrcr_figure():
    """MRCR: 長い会話に同じ依頼が何回も隠れていて、何番目かを区別させる（4 回の例に縮めた）。"""
    s = Svg(1040, 400, "長い会話の中に「バクの詩を書いて」という同じ依頼が 4 回あり、"
                       "最後の質問は 2 番目の詩を返させる。4 つは同じ文面なので、単語の一致では区別できない")
    s.text(20, 40, "入力（長い会話。左から右へ時間が進む）", 20, anchor="start", cls="sub")
    seq = ["g", 1, "g", 2, "g", "g", 3, "g", 4, "g"]
    x, w, gap = 20, 92, 8
    centers = {}
    for item in seq:
        if item == "g":
            s.box(x, 70, w, 110, PALE_GRAY, LINE)
            s.text(x + w / 2, 120, "別の", 18, cls="sub")
            s.text(x + w / 2, 144, "話題", 18, cls="sub")
        else:
            s.box(x, 70, w, 110, PALE_OCHRE, OCHRE)
            s.text(x + w / 2, 108, "バクの詩", 18)
            s.text(x + w / 2, 132, "を書いて", 18)
            s.text(x + w / 2, 162, f"→ 詩 {item}", 18, cls="sub")
            s.text(x + w / 2, 208, f"{item} 回目", 18, cls="sub")
            centers[item] = x + w / 2
        x += w + gap
    s.box(20, 290, 420, 70, PALE_BLUE, BLUE)
    s.text(230, 333, "質問: 2 番目のバクの詩を返して", 20)
    s.path(f"M 300 290 C 300 250, {centers[2]} 260, {centers[2]} 222", color=INK)
    s.text(centers[2] + 14, 262, "正解は詩 2", 18, anchor="start")
    s.text(480, 318, "4 つの依頼は同じ文面なので、単語の一致では選べない。", 18, anchor="start", cls="sub")
    s.text(480, 346, "何回目かを数えながら会話の全体を読む必要がある。", 18, anchor="start", cls="sub")
    s.save("long-context_mrcr.webp")


def graphwalks_figure():
    """GraphWalks: 辺の一覧が入力のあちこちに散らばり、幅優先探索で深さ 2 の節点を挙げさせる。"""
    s = Svg(1040, 460, "入力には有向グラフの辺が並び、必要な辺は先頭・中ほど・末尾に散らばる。"
                       "節点 a3f から深さ 2 にある節点を全て挙げさせる")
    s.text(20, 40, "入力（辺の一覧。実際は長い 16 進数のハッシュ）", 20, anchor="start", cls="sub")
    rows = [("7e2 → c41", False), ("a3f → 5b0", True), ("d19 → 7e2", False), ("…", None),
            ("5b0 → e86", True), ("c41 → 0fa", False), ("…", None), ("a3f → 9c1", True),
            ("2d7 → b33", False), ("…", None), ("9c1 → 4ad", True), ("0fa → d19", False)]
    y = 62
    for label, hit in rows:
        if hit is None:
            s.text(130, y + 22, "…（数十万トークン分の辺）", 16, cls="sub")
        else:
            s.box(30, y, 200, 30, PALE_OCHRE if hit else PALE_GRAY, OCHRE if hit else LINE, rx=4)
            s.text(130, y + 22, label, 18, fill=INK if hit else SUB)
        y += 32
    # 右: たどる木
    s.text(560, 40, "たどった結果（幅優先探索）", 20, anchor="start", cls="sub")
    nodes = {"a3f": (520, 150), "5b0": (700, 90), "9c1": (700, 220), "e86": (880, 90), "4ad": (880, 220)}
    for a, b in [("a3f", "5b0"), ("a3f", "9c1"), ("5b0", "e86"), ("9c1", "4ad")]:
        (x1, y1), (x2, y2) = nodes[a], nodes[b]
        s.path(f"M {x1 + 36} {y1} L {x2 - 38} {y2}", color=SUB)
    for name, (cx, cy) in nodes.items():
        fill, stroke = (PALE_BLUE, BLUE) if name in ("e86", "4ad") else (PALE_GRAY, LINE)
        s.circle(cx, cy, 34, fill, stroke)
        s.text(cx, cy + 7, name, 20)
    s.text(520, 292, "出発点", 18, cls="sub")
    s.text(700, 292, "深さ 1", 18, cls="sub")
    s.text(880, 292, "深さ 2（答え）", 18, cls="sub")
    s.box(330, 340, 690, 92, PALE_BLUE, BLUE)
    s.text(675, 376, "質問: a3f から深さ 2 にある節点を全て挙げて", 20)
    s.text(675, 410, "色の付いた 4 本の辺は入力のあちこちに散らばっている。全てをつなげて読む", 18, cls="sub")
    s.save("long-context_graphwalks.webp")


def nolima_figure():
    """従来の針探しは質問と針に同じ単語があり、NoLiMa は共通の単語を消して知識でつながせる。"""
    s = Svg(1040, 330, "左の従来の針探しは、質問と針に同じ語 project Aurora があり、語の一致で見つかる。"
                       "右の NoLiMa は共通の語が無く、ゼンパー・オペラ座がドレスデンにあるという知識でつなぐ")
    for ox, title, q, needle, link, hit in [
        (20, "従来の針探し", "質問: project Aurora の暗証番号は？", "針: The secret code for project Aurora is 7341.",
         "同じ語「project Aurora」", True),
        (540, "NoLiMa", "質問: ドレスデンに行ったことがある登場人物は？", "針: 実はユキはゼンパー・オペラ座の隣に住んでいる",
         "共通の語は無い。「オペラ座はドレスデンにある」という知識でつなぐ", False)]:
        s.text(ox, 40, title, 22, anchor="start")
        s.box(ox, 64, 480, 60, PALE_BLUE, BLUE)
        s.text(ox + 240, 101, q, 17)
        s.box(ox, 214, 480, 60, PALE_OCHRE, OCHRE)
        s.text(ox + 240, 251, needle, 16 if hit else 17)
        s.path(f"M {ox + 240} 128 L {ox + 240} 208", color=INK if hit else OCHRE, dash=not hit)
        s.text(ox + 252, 166, link, 15, anchor="start", cls="sub") if hit else None
        if not hit:
            s.text(ox + 252, 160, "共通の語は無い", 15, anchor="start", cls="sub")
            s.text(ox + 252, 184, "知識でつなぐ", 15, anchor="start", cls="sub")
    s.text(520, 314, "長い干し草（無関係な文章）の中から、針の 1 文を探させる", 16, cls="sub")
    s.save("long-context_nolima.webp")


def twohop_figure():
    """2 文をつなげる問いの、離した条件での文の置き場所と、本物と偽物の連鎖。"""
    s = Svg(1040, 360, "干し草の 10% に文 A、90% に文 B を置き、30%・70%・95% に紛らわしい文を置く。"
                       "本物の連鎖は Aurora から部屋 214、7341。誤答は 95% の Aurelia の文から部屋 241、7314 とたどった")
    x0, x1, yb = 60, 900, 170
    s.box(x0, yb - 14, x1 - x0, 28, PALE_GRAY, LINE, rx=4)
    s.text(x0, yb + 48, "0%", 16, cls="sub")
    s.text(x1, yb + 48, "100%", 16, cls="sub")
    s.text((x0 + x1) / 2, yb + 48, "干し草（小説の本文）の中の位置", 16, cls="sub")
    X = lambda d: x0 + (x1 - x0) * d
    s.box(x1 + 14, yb - 34, 120, 68, PALE_BLUE, BLUE)
    s.text(x1 + 74, yb - 6, "質問", 18)
    s.text(x1 + 74, yb + 20, "Aurora の番号は？", 14, cls="sub")
    true = [(0.10, "文 A", "Aurora → 部屋 214"), (0.90, "文 B", "部屋 214 → 7341")]
    fake = [(0.30, "部屋 241 → 7314"), (0.70, "部屋 412 → 3417"), (0.95, "Aurelia → 部屋 241")]
    for d, name, label in true:
        s.box(X(d) - 6, yb - 20, 12, 40, BLUE, BLUE, rx=2)
        s.text(X(d), 64, name, 18)
        s.text(X(d), 88, label, 16)
    for d, label in fake:
        s.box(X(d) - 6, yb - 20, 12, 40, OCHRE, OCHRE, rx=2)
        s.text(X(d), 272, label, 16)
    s.path(f"M {X(0.10)} 100 C {X(0.10)} 120, {X(0.90)} 120, {X(0.90)} 100", color=BLUE, arrow=False, sw=2)
    s.text(X(0.5), 76, "本物の連鎖（正解 7341）", 16, fill=INK)
    s.path(f"M {X(0.95)} 252 C {X(0.95)} 230, {X(0.30)} 230, {X(0.30)} 252", color=OCHRE, dash=True,
           arrow=False, sw=2)
    s.text(X(0.62), 310, "誤答の連鎖（Aurelia を Aurora と取り違え、7314 と答えた）", 16, fill=INK)
    s.save("long-context_twohop.webp")


def lost_in_the_middle():
    """20 文書の多文書 QA で、正解の文書の位置ごとの正答率（論文 Table 6）。"""
    pos = [1, 5, 10, 15, 20]
    gpt35 = [75.8, 57.2, 53.8, 55.4, 63.2]
    claude13 = [59.9, 55.9, 56.8, 57.2, 60.1]
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    ax.plot(pos, gpt35, color=BLUE, lw=2.4, marker="o", label="GPT-3.5-Turbo")
    ax.plot(pos, claude13, color=OCHRE, lw=2.4, marker="o", label="Claude-1.3")
    ax.axhline(56.1, color=RED, lw=1.2, ls="--")
    ax.text(20.6, 52.5, "文書を渡さない時の\nGPT-3.5-Turbo（56.1%）", va="center", fontsize=8.5, color=SUB)
    ax.set_xticks(pos, [f"{p} 番目" for p in pos])
    ax.set_xlabel("正解を含む文書の位置（20 文書中）")
    ax.set_ylabel("正答率（%）")
    ax.set_xlim(0, 27)
    ax.set_ylim(45, 80)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(loc="upper center", frameon=False, fontsize=9, ncol=2)
    save(fig, "long-context_lost-in-the-middle.webp")


def vendor_figure():
    """Anthropic のシステムカードに載った、同じ社のモデルの長い入力での成績。"""
    fig, axes = plt.subplots(1, 2, figsize=(7.8, 3.6))
    # 左: GraphWalks BFS（F1）。Opus 4.8 と Mythos 5 のカードの表から
    models = ["Opus 4.6\n(2026-02)", "Opus 4.7\n(2026-04)", "Opus 4.8\n(2026-05)", "Mythos 5\n(2026-06)"]
    k256 = [61.1, 76.9, 85.9, 91.1]
    k1m = [16.3, 40.3, 68.1, 79.4]
    ax = axes[0]
    x = range(len(models))
    ax.plot(x, k256, color=BLUE, lw=2.4, marker="o", label="入力 256K の問題")
    ax.plot(x, k1m, color=OCHRE, lw=2.4, marker="o", label="入力 1M の問題")
    for i, (a, b) in enumerate(zip(k256, k1m)):
        ax.text(i, a + 3, f"{a:.1f}", ha="center", fontsize=8)
        ax.text(i, b - 8, f"{b:.1f}", ha="center", fontsize=8)
    ax.set_title("GraphWalks BFS（F1）", fontsize=10)
    ax.set_xticks(list(x), models, fontsize=8)
    ax.set_ylim(0, 105)
    ax.legend(loc="lower right", frameon=False, fontsize=8.5)
    ax.spines[["top", "right"]].set_visible(False)
    # 右: MRCR v2 8-needle 1M。Opus 4.6 と 4.7 のカードから
    ax = axes[1]
    names = ["Sonnet 4.5", "Opus 4.6\n(思考 最大)", "Opus 4.7\n(思考 最大)"]
    vals = [18.5, 76.0, 32.2]
    bars = ax.bar(range(3), vals, 0.55, color=OCHRE)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 2, f"{v:g}", ha="center", fontsize=8.5)
    ax.set_title("MRCR v2（針 8 個）、524K〜1024K の区間（%）", fontsize=10)
    ax.set_xticks(range(3), names, fontsize=8.5)
    ax.set_ylim(0, 105)
    ax.spines[["top", "right"]].set_visible(False)
    save(fig, "long-context_vendor.webp")


def experiment_figure():
    """手元の qwen3:8b での正答数。左が 1 文を探す問い、右が 2 文をつなぐ問い。"""
    needle = [json.loads(line) for line in (HERE / "lab" / "results_needle.jsonl").open()]
    twohop = [json.loads(line) for line in (HERE / "lab" / "results_twohop.jsonl").open()]
    lengths = sorted({r["length_chars"] for r in needle})
    tok = defaultdict(list)
    for r in needle + twohop:
        tok[r["length_chars"]].append(r["tokens"])
    labels = [f"約 {sum(tok[n]) / len(tok[n]) / 1000:.1f}K" for n in lengths]

    fig, axes = plt.subplots(1, 2, figsize=(7.8, 3.6), sharey=True)
    ax = axes[0]
    for cond, label, color, mk, ms in [("needle_only", "紛らわしい文なし", BLUE, "s", 11),
                                       ("with_distractors", "紛らわしい文を 3 つ追加", OCHRE, "o", 6)]:
        acc = []
        for n in lengths:
            rs = [r["correct"] for r in needle if r["length_chars"] == n and r["cond"] == cond]
            acc.append(100 * sum(rs) / len(rs))
        ax.plot(range(len(lengths)), acc, color=color, lw=4.5 if ms > 8 else 2.2, marker=mk,
                markersize=ms, label=label)
    ax.set_title("1 文を探す（位置 5 通り × 4 問）", fontsize=10)
    ax.set_xticks(range(len(lengths)), labels)
    ax.set_xlabel("入力の長さ（トークン）")
    ax.set_ylabel("正答率（%）")
    ax.set_ylim(-5, 108)
    ax.legend(loc="lower left", frameon=False, fontsize=8.5)
    ax.spines[["top", "right"]].set_visible(False)

    ax = axes[1]
    styles = [("near_start", "2 文とも先頭付近", BLUE, "-", "s", 14),
              ("near_end", "2 文とも末尾付近", GREEN, "-", "^", 10),
              ("near_middle", "2 文とも真ん中", OCHRE, "-", "o", 6),
              ("far_apart", "10% と 90% に離す", SUB, "--", "o", 6)]
    for key, label, color, ls, mk, ms in styles:
        acc = []
        for n in lengths:
            rs = [r["correct"] for r in twohop if r["length_chars"] == n and r["placement"] == key]
            acc.append(100 * sum(rs) / len(rs))
        ax.plot(range(len(lengths)), acc, markersize=ms, color=color, lw=2.2, marker=mk, ls=ls,
                label=label)
    ax.set_title("2 文をつなげて答える（4 問）", fontsize=10)
    ax.set_xticks(range(len(lengths)), labels)
    ax.set_xlabel("入力の長さ（トークン）")
    ax.legend(loc="center left", bbox_to_anchor=(0.0, 0.62), frameon=False, fontsize=8)
    ax.spines[["top", "right"]].set_visible(False)
    save(fig, "long-context_experiment.webp")


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    lost_in_the_middle()
    vendor_figure()
    mrcr_figure()
    graphwalks_figure()
    twohop_figure()
    nolima_figure()
    if (HERE / "lab" / "results_twohop.jsonl").exists():
        experiment_figure()
