"""KV キャッシュのノートの図を作る（lab/*.json から）。

- kv-cache_concept.webp        : 前から埋まる KV キャッシュの枠と、新しいトークンが全部を読む様子（手書きの SVG）
- kv-cache_qkv.webp            : 今のトークンの Q と過去の K から比率を求め、その比率で V を混ぜる（手書きの SVG）
- kv-cache_steps.webp          : キャッシュ無し・有りで、各ステップに K・V を計算するトークン（手書きの SVG）
- kv-cache_gqa.webp            : 通常・GQA・MQA の Q ヘッドと K・V の組の対応（手書きの SVG）
- kv-cache_memory.webp         : num_ctx と読み込んだモデルの size（matplotlib）
- kv-cache_prefill.webp        : 入力の長さと、プロンプトの処理の時間・生成の速さ（matplotlib）
- kv-cache_read_per_token.webp : 生成の 1 トークンごとに読む量と実測の速さ（手書きの SVG）
- kv-cache_prefix.webp         : 5 通りの送り方で使い回せた範囲と処理の時間（手書きの SVG）

手書きの SVG は Chrome の headless で PNG にしてから WebP にする。images/ に SVG は残さない。

使い方:
    uv run --with matplotlib==3.11.2 --with pillow python figures.py
"""

import json
import statistics
import subprocess
import tempfile
from html import escape
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker  # noqa: E402
from PIL import Image  # noqa: E402

HERE = Path(__file__).resolve().parent
LAB = HERE / "lab"
IMAGES = HERE / "images"

INK, SUB, ACCENT = "#1f1f1f", "#666666", "#7aa6c2"
OCHRE, GREEN = "#d4a24c", "#8fae86"
PALE, OCHRE_PALE = "#eaf1f5", "#f8eed8"
plt.rcParams.update({
    "font.family": "Noto Sans CJK JP", "font.size": 12, "axes.edgecolor": SUB,
    "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK, "text.color": INK,
    "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
})
# Qwen3-1.7B（config.json）の 1 トークンあたりの K と V のバイト数: 2 x 28 層 x KV ヘッド 8 x 128 x 2 バイト
PER_TOKEN = 2 * 28 * 8 * 128 * 2
FONT = "'Noto Sans CJK JP','Hiragino Sans','Yu Gothic',sans-serif"


def save_plot(fig, name):
    """PNG（dpi 200）に描いてから WebP にする。"""
    IMAGES.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        png = Path(tmp) / "fig.png"
        fig.savefig(png, dpi=200, facecolor="#ffffff", bbox_inches="tight")
        Image.open(png).convert("RGB").save(IMAGES / name, "WEBP", quality=90, method=6)
    plt.close(fig)


def save_svg(svg_text, w, h, name):
    """SVG を Chrome の headless で 2 倍の PNG にしてから WebP にする。"""
    IMAGES.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        svg, png = Path(tmp) / "fig.svg", Path(tmp) / "fig.png"
        svg.write_text(svg_text, encoding="utf-8")
        subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--hide-scrollbars",
                        "--force-device-scale-factor=2", f"--window-size={w},{h}",
                        f"--screenshot={png}", svg.as_uri()], check=True, capture_output=True)
        Image.open(png).convert("RGB").save(IMAGES / name, "WEBP", quality=90, method=6)


class Svg:
    """手書きの SVG（文字は 24px 以上、太字なし、背景は白）。"""

    def __init__(self, w, h, title):
        self.w, self.h = w, h
        self.p = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}" role="img"><title>{escape(title)}</title>',
            f'<style>text{{font-family:{FONT};fill:{INK}}} .sub{{fill:{SUB}}}</style>',
            f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
        ]

    def text(self, x, y, s, size=24, anchor="middle", cls=""):
        c = f' class="{cls}"' if cls else ""
        self.p.append(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" '
                      f'text-anchor="{anchor}"{c}>{escape(s)}</text>')

    def rect(self, x, y, w, h, fill, stroke, sw=2, rx=4, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.p.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" '
                      f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def line(self, x1, y1, x2, y2, color=SUB, sw=2, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.p.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                      f'stroke="{color}" stroke-width="{sw}"{d}/>')

    def raw(self, s):
        self.p.append(s)

    def save(self, name):
        save_svg("\n".join(self.p + ["</svg>"]) + "\n", self.w, self.h, name)


def concept_figure():
    """コンテキスト長の数だけ枠があり、プロンプトと生成で前から埋まる。

    奥に重ねた帯は層ごとに別の K と V を持つことを表す。新しいトークンは、
    埋まった枠の K と V を全部読む。
    """
    s = Svg(960, 540, "KV キャッシュの枠は前から埋まり、次のトークンは埋まった枠を全部読む")
    slots, x0, sw, gap, y0, sh = 22, 60, 34, 4, 170, 150
    n_prompt, n_gen = 9, 3

    def slot(i, dx, dy, front):
        x, y = x0 + i * (sw + gap) + dx, y0 + dy
        if i < n_prompt:
            fill, stroke, dash = PALE, ACCENT, None
        elif i < n_prompt + n_gen:
            fill, stroke, dash = OCHRE_PALE, OCHRE, None
        else:
            fill, stroke, dash = "#ffffff", SUB, "5 4"
        if not front and i >= n_prompt + n_gen:
            stroke = SUB
        s.rect(x, y, sw, sh, fill, stroke, 2.5 if front else 1.5, 4, dash)
        if front and i < n_prompt + n_gen:
            # 上半分が K、下半分が V
            s.line(x + 4, y + sh / 2, x + sw - 4, y + sh / 2, stroke, 1.5)

    for depth in (2, 1, 0):
        for i in range(slots):
            slot(i, depth * 14, -depth * 14, depth == 0)
    s.text(30, y0 + 50, "K", 26)
    s.text(30, y0 + 125, "V", 26)
    s.text(x0 + slots * (sw + gap) + 20, y0 + sh + 50, "奥の帯: 層ごとの K と V（28 層）", 24, "end", "sub")

    xp1 = x0 + n_prompt * (sw + gap) - gap
    xg1 = x0 + (n_prompt + n_gen) * (sw + gap) - gap
    for xa, xb, label, color in ((x0, xp1, "プロンプト（まとめて計算）", ACCENT),
                                 (xp1 + gap, xg1, "生成", OCHRE)):
        s.raw(f'<path d="M{xa},{y0 - 40} V{y0 - 52} H{xb} V{y0 - 40}" fill="none" '
              f'stroke="{color}" stroke-width="3"/>')
        s.text((xa + xb) / 2, y0 - 64, label, 26)
    s.text(x0 + 13 * (sw + gap) + 150, y0 - 64, "空き", 24, "middle", "sub")

    xn = xg1 + gap + sw / 2
    s.rect(xg1 + gap, y0, sw, sh, "#ffffff", INK, 3)
    ya = y0 + sh + 20
    s.raw(f'<path d="M{xn},{ya} C{xn - 40},{ya + 70} {x0 + 60},{ya + 70} {x0 + 17},{ya + 6}" '
          f'fill="none" stroke="{INK}" stroke-width="3"/>')
    s.raw(f'<polygon points="{x0 + 17},{ya} {x0 + 7},{ya + 20} {x0 + 29},{ya + 16}" fill="{INK}"/>')
    s.text((x0 + xn) / 2, ya + 90, "次のトークンは、埋まった枠の K と V を全部読む", 24)

    xe = x0 + slots * (sw + gap) - gap
    yb = 470
    s.raw(f'<path d="M{x0},{yb - 12} V{yb} H{xe} V{yb - 12}" fill="none" '
          f'stroke="{SUB}" stroke-width="2"/>')
    s.text((x0 + xe) / 2, yb + 34, "枠の数 = コンテキスト長（Ollama では num_ctx）", 24, "middle", "sub")
    s.save("kv-cache_concept.webp")


def qkv_figure():
    """注意機構の 1 回分。今のトークンの Q を各トークンの K と比べて比率を出し、その比率で V を混ぜる。"""
    s = Svg(960, 600, "今のトークンの Q と各トークンの K から比率を求め、その比率で V を混ぜる")
    toks = ("今日", "は", "雨", "なので", "傘", "を")
    weights = (0.05, 0.03, 0.30, 0.07, 0.45, 0.10)  # 説明用の例。合計 1
    assert abs(sum(weights) - 1) < 1e-9
    cw, gap, x0 = 76, 10, 270
    xs = [x0 + i * (cw + gap) for i in range(len(toks))]
    yk, ybr, yw, yv, bh = 70, 160, 222, 262, 46
    yo = 410
    xo = (xs[0] + xs[-1] + cw) / 2
    for i, (x, t) in enumerate(zip(xs, toks)):
        now = i == len(toks) - 1
        s.text(x + cw / 2, 52, t, 24)
        s.rect(x, yk, cw, bh, PALE, INK if now else ACCENT, 3 if now else 2.5)
        s.text(x + cw / 2, yk + 32, "K", 24)
        s.line(x + cw / 2, yk + bh + 6, x + cw / 2, ybr, OCHRE, 2.5)
        s.text(x + cw / 2, yw - 8, f"{weights[i]:.2f}", 24)
        s.rect(x, yv, cw, bh, PALE, INK if now else ACCENT, 3 if now else 2.5)
        s.text(x + cw / 2, yv + 32, "V", 24)
        s.line(x + cw / 2, yv + bh, xo, yo, SUB, 1.5)
    # 今のトークン「を」の Q。下の線で全ての K とつながる
    xq = xs[-1] + cw + 50
    s.text(xq + 40, 52, "今の「を」", 22, "middle", "sub")
    s.rect(xq, yk, 80, bh, OCHRE_PALE, OCHRE, 2.5)
    s.text(xq + 40, yk + 32, "Q", 24)
    s.line(xq + 40, yk + bh + 6, xq + 40, ybr, OCHRE, 2.5)
    s.line(xs[0] + cw / 2, ybr, xq + 40, ybr, OCHRE, 2.5)
    for y, label in ((yk + 32, "K"), (ybr + 8, "① Q と各 K の内積"), (yw - 8, "② 比率（合計 1）"),
                     (yv + 32, "V"), (yv + 110, "③ 比率で V を混ぜる")):
        s.text(240, y, label, 22, "end", "sub")
    s.rect(xo - 150, yo, 300, 56, OCHRE_PALE, OCHRE, 2.5)
    s.text(xo, yo + 36, "「を」の注意機構の出力", 24)
    s.text(480, 528, "比率は説明用の例。今のトークン「を」自身の K と V も計算に入る", 22, "middle", "sub")
    s.text(480, 564, "K と V は後のトークンでも同じ値を使うので、キャッシュに取っておける", 22, "middle", "sub")
    s.save("kv-cache_qkv.webp")


def steps_figure():
    """5 トークン目までを読む時に、各ステップで K・V を計算するトークン。"""
    s = Svg(960, 520, "キャッシュ無しと有りで、各ステップに K・V を計算するトークンを比べる")
    s.rect(250, 26, 28, 28, OCHRE_PALE, OCHRE, 2.5)
    s.text(288, 48, "K・V を計算する", 24, "start")
    s.rect(520, 26, 28, 28, PALE, ACCENT, 2.5)
    s.text(558, 48, "キャッシュから読む", 24, "start")
    n, cell, gap = 5, 46, 6
    for p, (title, cached, x0) in enumerate((("キャッシュ無し", False, 170),
                                              ("キャッシュ有り", True, 640))):
        y0 = 150
        s.text(x0 + (n * (cell + gap) - gap) / 2, 104, title, 26)
        for j in range(n):
            s.text(x0 + j * (cell + gap) + cell / 2, y0 - 10, f"{j + 1}", 22, "middle", "sub")
        if p == 0:
            s.text(x0 - 20, y0 - 10, "トークン", 22, "end", "sub")
        count = 0
        for t in range(n):
            y = y0 + t * (cell + gap)
            if p == 0:
                s.text(x0 - 20, y + 32, f"ステップ {t + 1}", 24, "end")
            for j in range(n):
                x = x0 + j * (cell + gap)
                if j > t:
                    continue
                if cached and j < t:
                    s.rect(x, y, cell, cell, PALE, ACCENT, 2)
                else:
                    s.rect(x, y, cell, cell, OCHRE_PALE, OCHRE, 2.5)
                    count += 1
        expr = "1 + 2 + 3 + 4 + 5 = 15 回" if not cached else "1 + 1 + 1 + 1 + 1 = 5 回"
        s.text(x0 + (n * (cell + gap) - gap) / 2, 450, f"K・V の計算 {expr}", 24)
        assert count == (15 if not cached else 5)
    s.text(480, 500, "ステップ t では、1〜t トークン目を参照して次を選ぶ", 24, "middle", "sub")
    s.save("kv-cache_steps.webp")


def gqa_figure():
    """16 個の Q ヘッドが K・V の組をいくつ共有するか。組の数がキャッシュの大きさになる。"""
    s = Svg(960, 540, "通常の注意機構・GQA・MQA で、Q ヘッドと K・V の組の対応を比べる")
    s.text(451, 52, "上の小さい枠: Q ヘッド 16 個　下の枠: K・V の組", 24, "middle", "sub")
    qw, qg, x0 = 22, 6, 230
    rows = (("通常", 16), ("GQA（Qwen3）", 8), ("MQA", 1))
    for r, (label, kv) in enumerate(rows):
        y = 88 + r * 135
        per_token = 2 * 28 * kv * 128 * 2
        s.text(30, y + 62, label, 26, "start")
        group = 16 // kv
        for i in range(16):
            x = x0 + i * (qw + qg)
            s.rect(x, y, qw, qw, PALE, ACCENT, 2, 3)
            s.line(x + qw / 2, y + qw, x + qw / 2, y + 70, SUB, 1.5)
        for k in range(kv):
            xa = x0 + k * group * (qw + qg)
            s.rect(xa, y + 70, group * (qw + qg) - qg, 34, OCHRE_PALE, OCHRE, 2.5, 4)
        s.text(700, y + 62, f"{per_token // 1024} KiB / トークン", 26, "start")
    s.text(480, 522, "KV ヘッドの数にキャッシュの大きさが比例する（28 層、head_dim 128、f16）",
           24, "middle", "sub")
    s.save("kv-cache_gqa.webp")


def memory_figure():
    rows = json.loads((LAB / "memory.json").read_text())
    # num_ctx を指定しない行は 40,960 で読み込まれ、40,960 を指定した行と同じ値なので除く
    q8 = sorted((r for r in rows if r["model"] == "qwen3:1.7b-q8_0" and r["ps"]
                 and r["num_ctx"] is not None),
                key=lambda r: r["ps"]["context_length"])
    ctx = [r["ps"]["context_length"] for r in q8]
    size = [r["ps"]["size"] / 1e9 for r in q8]
    base = q8[0]
    pred = [(base["ps"]["size"] + PER_TOKEN * (c - base["ps"]["context_length"])) / 1e9
            for c in ctx]
    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    ax.plot(ctx, pred, color=SUB, lw=1.2, ls="--",
            label=f"{ctx[0]:,} の値から 1 トークンあたり {PER_TOKEN:,} バイトずつ増やした線")
    ax.plot(ctx, size, color=ACCENT, lw=0, marker="o", ms=7, label="qwen3:1.7b-q8_0")
    for name, color, marker in (("qwen3:1.7b-fp16", OCHRE, "s"),
                                ("qwen3:1.7b-q4_K_M", GREEN, "^")):
        pts = sorted((r["ps"]["context_length"], r["ps"]["size"] / 1e9)
                     for r in rows if r["model"] == name and r["ps"])
        ax.plot([p[0] for p in pts], [p[1] for p in pts], color=color, lw=1.2,
                marker=marker, ms=7, label=name)
    for i, (c, sz) in enumerate(zip(ctx, size)):
        # 左端の 2 点は近いので、4,096 の値は書かず、2,048 の値を真上に書く
        if c == 4096:
            continue
        xy, ha = ((0, 10), "center") if i == 0 else ((-6, 8), "right")
        ax.annotate(f"{sz:.2f}", (c, sz), textcoords="offset points", xytext=xy,
                    ha=ha, fontsize=10)
    ax.annotate("num_ctx 未指定は\n40,960 で読み込み", (40960, 6.21), textcoords="offset points",
                xytext=(-10, -46), ha="center", fontsize=10, color=SUB)
    ax.set_xlabel("num_ctx（トークン）")
    ax.set_ylabel("読み込んだモデルの size（GB）")
    ax.set_xlim(0, 43000)
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))
    ax.set_ylim(0, 9)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(loc="upper left", frameon=False, fontsize=10)
    save_plot(fig, "kv-cache_memory.webp")


def prefill_figure():
    rows = json.loads((LAB / "prefill.json").read_text())
    by = {}
    for r in rows:
        by.setdefault(r["lines"], []).append(r)
    n = sorted(by)
    tok = [statistics.median(x["prompt_eval_count"] for x in by[k]) for k in n]
    pre = [[x["prompt_eval_s"] for x in by[k]] for k in n]
    gen = [[x["eval_count"] / x["eval_s"] for x in by[k]] for k in n]
    fig, axes = plt.subplots(1, 2, figsize=(8.4, 3.8))
    for ax, vals, label, color in (
            (axes[0], pre, "プロンプトの処理の時間（秒）", ACCENT),
            (axes[1], gen, "生成の速さ（トークン / 秒）", OCHRE)):
        med = [statistics.median(v) for v in vals]
        lo = [m - min(v) for m, v in zip(med, vals)]
        hi = [max(v) - m for m, v in zip(med, vals)]
        ax.errorbar(tok, med, yerr=[lo, hi], color=color, lw=1.8, marker="o", ms=5, capsize=3)
        ax.set_xlabel("入力の長さ（トークン）")
        ax.set_title(label, fontsize=12)
        ax.set_ylim(bottom=0)
        ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))
        ax.spines[["top", "right"]].set_visible(False)
    axes[1].text(0.5, 0.06, "どの回も num_ctx = 32,768", transform=axes[1].transAxes,
                 ha="center", color=SUB, fontsize=10)
    fig.tight_layout()
    save_plot(fig, "kv-cache_prefill.webp")


# q8_0 で生成の 1 トークンごとに読む重み。入力の埋め込みを除いた値（本文の約 1.88 GB）。
WEIGHTS_READ_GB = 1.885


def read_per_token_figure():
    """生成の 1 トークンごとに読む量（重み + K・V）と、実測の生成の速さ。"""
    rows = json.loads((LAB / "prefill.json").read_text())
    by = {}
    for r in rows:
        by.setdefault(r["lines"], []).append(r)
    ends = (min(by), max(by))
    s = Svg(960, 400, "生成の 1 トークンごとに読む量と、実測の生成の速さ")
    x0, scale = 250, 80
    s.text(30, 52, "入力の長さ", 24, "start", "sub")
    s.text(x0, 52, "1 トークンを出すたびに読む量", 24, "start", "sub")
    s.text(930, 52, "実測の速さ", 24, "end", "sub")
    for i, k in enumerate(ends):
        y = 84 + i * 130
        tok = statistics.median(x["prompt_eval_count"] for x in by[k])
        speed = statistics.median(x["eval_count"] / x["eval_s"] for x in by[k])
        kv = PER_TOKEN * tok / 1e9
        s.text(30, y + 44, f"{tok:,.0f} トークン", 26, "start")
        s.rect(x0, y, WEIGHTS_READ_GB * scale, 66, PALE, ACCENT, 2.5)
        s.rect(x0 + WEIGHTS_READ_GB * scale, y, kv * scale, 66, OCHRE_PALE, OCHRE, 2.5)
        s.text(x0 + WEIGHTS_READ_GB * scale / 2, y + 43, "重み 1.88 GB", 24)
        if kv * scale > 120:
            s.text(x0 + (WEIGHTS_READ_GB + kv / 2) * scale, y + 43, f"K・V {kv:.2f} GB", 24)
        else:
            s.text(x0 + (WEIGHTS_READ_GB + kv) * scale + 12, y + 43, f"+ K・V {kv:.2f} GB", 22, "start", "sub")
        s.text(x0 + (WEIGHTS_READ_GB + kv) * scale, y + 98,
               f"計 {WEIGHTS_READ_GB + kv:.2f} GB", 24, "end")
        s.text(930, y + 43, f"{speed:.1f} トークン/秒", 26, "end")
    s.text(480, 372, "読む量は約 2.8 倍、速さは約 2.4 分の 1（num_ctx 32,768、q8_0）",
           24, "middle", "sub")
    s.save("kv-cache_read_per_token.webp")


def prefix_figure():
    """5 通りの送り方で、先頭からどこまでキャッシュを使えたかとプロンプトの処理の時間。"""
    rows = json.loads((LAB / "prefix.json").read_text())
    med = {}
    for r in rows:
        med.setdefault(r["case"], []).append(r["prompt_eval_s"])
    # (case, 表示名, 先頭から使い回せた割合)。割合は送った内容から読んだ模式で、測ったのは時間だけ。
    # Ollama 0.22.1 は入力が全部一致しても、応答を作るために末尾の 1 トークンを計算し直す
    # （runner/ollamarunner/cache.go の LoadCacheSlot）。2 と 3 の右端の黄土は幅を誇張している。
    cases = (("1 first send", "1 初回", 0.0),
             ("2 same prompt again", "2 同じ入力をもう一度", 0.985),
             ("3 same prefix, new question", "3 同じプレフィックス・別の質問", 0.96),
             ("4 one line edited in the middle", "4 真ん中の 1 行を変更", 0.5),
             ("5 one char added at the head", "5 先頭に 1 文字を追加", 0.0))
    s = Svg(960, 580, "同じプレフィックスを送り直した時に、キャッシュを使えた範囲と処理の時間")
    s.rect(420, 32, 28, 28, PALE, ACCENT, 2.5)
    s.text(458, 54, "キャッシュから使う", 24, "start")
    s.rect(680, 32, 28, 28, OCHRE_PALE, OCHRE, 2.5)
    s.text(718, 54, "計算し直す", 24, "start")
    x0, width = 420, 340
    for i, (case, label, frac) in enumerate(cases):
        y = 100 + i * 80
        s.text(30, y + 32, label, 22, "start")
        if frac > 0:
            s.rect(x0, y, width * frac, 44, PALE, ACCENT, 2.5)
        if frac < 1:
            s.rect(x0 + width * frac, y, width * (1 - frac), 44, OCHRE_PALE, OCHRE, 2.5)
        s.text(930, y + 32, f"{statistics.median(med[case]):.3f} 秒", 26, "end")
    s.text(480, 516, "2・3 の右端の黄土は幅を誇張（2 は応答を作るための末尾の 1 トークン）", 22, "middle", "sub")
    s.text(480, 552, "約 8,300 トークンのプレフィックス、3 巡の中央値。帯は送った内容から見た模式", 22, "middle", "sub")
    s.save("kv-cache_prefix.webp")


if __name__ == "__main__":
    concept_figure()
    qkv_figure()
    steps_figure()
    gqa_figure()
    if (LAB / "memory.json").exists():
        memory_figure()
    if (LAB / "prefill.json").exists():
        prefill_figure()
        read_per_token_figure()
    if (LAB / "prefix.json").exists():
        prefix_figure()
