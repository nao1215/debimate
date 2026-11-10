"""Generate the figures of the KV cache note from lab/*.json."""

import json
import statistics
from html import escape
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
LAB = HERE / "lab"
IMAGES = HERE / "images"

INK, SUB, ACCENT, RED = "#1f1f1f", "#666666", "#7aa6c2", "#e15759"
OCHRE, GREEN = "#d4a24c", "#8fae86"
PALE, OCHRE_PALE, FILL = "#eaf1f5", "#f8eed8", "#f2f2f2"
plt.rcParams.update({
    "font.size": 10, "axes.edgecolor": SUB, "axes.labelcolor": INK,
    "xtick.color": INK, "ytick.color": INK, "text.color": INK,
    "svg.fonttype": "path", "svg.hashsalt": "kv-cache",
    "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
})
# Bytes of K and V for one token in Qwen3-1.7B (config.json): 2 x 28 layers x 8 KV heads x 128 x 2 bytes.
PER_TOKEN = 2 * 28 * 8 * 128 * 2


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
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    ax.plot(ctx, pred, color=SUB, lw=1.2, ls="--",
            label=f"{ctx[0]:,} tokens + {PER_TOKEN:,} bytes / token")
    ax.plot(ctx, size, color=ACCENT, lw=0, marker="o", ms=7,
            label="qwen3:1.7b-q8_0 (ollama ps SIZE)")
    for name, color, marker in (("qwen3:1.7b-fp16", OCHRE, "s"),
                                ("qwen3:1.7b-q4_K_M", GREEN, "^")):
        pts = sorted((r["ps"]["context_length"], r["ps"]["size"] / 1e9)
                     for r in rows if r["model"] == name and r["ps"])
        ax.plot([p[0] for p in pts], [p[1] for p in pts], color=color, lw=1.2,
                marker=marker, ms=7, label=name)
    for c, s in zip(ctx, size):
        ax.annotate(f"{s:.2f}", (c, s), textcoords="offset points", xytext=(-6, 8),
                    ha="right", fontsize=9)
    ax.annotate("num_ctx unset\n= 40,960", (40960, 6.21), textcoords="offset points",
                xytext=(-4, -40), ha="center", fontsize=9, color=SUB)
    ax.set_xlabel("num_ctx (tokens)")
    ax.set_ylabel("Memory of the loaded model (GB)")
    ax.set_xlim(0, 43000)
    ax.set_ylim(0, 9)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(loc="upper left", frameon=False, fontsize=9)
    fig.tight_layout()
    fig.savefig(IMAGES / "kv-cache_memory.svg", metadata={"Date": None})


def prefill_figure():
    rows = json.loads((LAB / "prefill.json").read_text())
    by = {}
    for r in rows:
        by.setdefault(r["lines"], []).append(r)
    n = sorted(by)
    tok = [statistics.median(x["prompt_eval_count"] for x in by[k]) for k in n]
    pre = [[x["prompt_eval_s"] for x in by[k]] for k in n]
    gen = [[x["eval_count"] / x["eval_s"] for x in by[k]] for k in n]
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.6))
    for ax, vals, label, color in (
            (axes[0], pre, "Time to read the prompt (s)", ACCENT),
            (axes[1], gen, "Generation speed (tokens / s)", OCHRE)):
        med = [statistics.median(v) for v in vals]
        lo = [m - min(v) for m, v in zip(med, vals)]
        hi = [max(v) - m for m, v in zip(med, vals)]
        ax.errorbar(tok, med, yerr=[lo, hi], color=color, lw=1.8, marker="o", ms=5,
                    capsize=3)
        ax.set_xlabel("Prompt length (tokens)")
        ax.set_ylabel(label)
        ax.set_ylim(bottom=0)
        ax.spines[["top", "right"]].set_visible(False)
    axes[1].text(0.5, 0.06, "num_ctx = 32,768 in all runs", transform=axes[1].transAxes,
                 ha="center", color=SUB, fontsize=9)
    fig.tight_layout()
    fig.savefig(IMAGES / "kv-cache_prefill.svg", metadata={"Date": None})


FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"


def concept_figure():
    """num_ctx 個の枠を読み込み時に全部確保し、プロンプトと生成で前から埋める。

    奥に重ねた帯は層ごとに別の K と V を持つことを表す。新しいトークンは、
    埋まった枠の K と V を全部読む。
    """
    w, h = 960, 540
    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img"><title>'
        f'{escape("KV キャッシュは num_ctx の枠を先に確保し、プロンプトと生成で前から埋める")}'
        '</title>',
        f'<style>text{{font-family:{FONT};fill:{INK}}} .sub{{fill:{SUB}}}</style>',
        f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
    ]

    def text(x, y, s, size=26, anchor="middle", cls=""):
        c = f' class="{cls}"' if cls else ""
        p.append(f'<text x="{x}" y="{y}" font-size="{size}" '
                 f'text-anchor="{anchor}"{c}>{escape(s)}</text>')

    slots, x0, sw, gap, y0, sh = 22, 60, 34, 4, 170, 150
    n_prompt, n_gen = 9, 3

    def slot(i, dx, dy, front):
        x, y = x0 + i * (sw + gap) + dx, y0 + dy
        if i < n_prompt:
            fill, stroke, dash = PALE, ACCENT, ""
        elif i < n_prompt + n_gen:
            fill, stroke, dash = OCHRE_PALE, OCHRE, ""
        else:
            fill, stroke, dash = "#ffffff", SUB, ' stroke-dasharray="5 4"'
        if not front:
            stroke = SUB if i >= n_prompt + n_gen else stroke
        p.append(f'<rect x="{x}" y="{y}" width="{sw}" height="{sh}" rx="4" fill="{fill}" '
                 f'stroke="{stroke}" stroke-width="{2.5 if front else 1.5}"{dash}/>')
        if front and i < n_prompt + n_gen:
            # K の上半分と V の下半分
            p.append(f'<line x1="{x + 4}" y1="{y + sh / 2}" x2="{x + sw - 4}" '
                     f'y2="{y + sh / 2}" stroke="{stroke}" stroke-width="1.5"/>')

    # 層ごとに K と V を持つので、奥に 2 枚重ねて描く
    for depth in (2, 1, 0):
        for i in range(slots):
            slot(i, depth * 14, -depth * 14, depth == 0)
    text(30, y0 + 50, "K", 26, "middle")
    text(30, y0 + 125, "V", 26, "middle")
    text(x0 + slots * (sw + gap) + 20, y0 + sh + 50, "奥の帯: 層ごとの K と V（28 層）", 24, "end", "sub")

    # 上の札: プロンプトと生成
    xp1 = x0 + n_prompt * (sw + gap) - gap
    xg1 = x0 + (n_prompt + n_gen) * (sw + gap) - gap
    for xa, xb, label, color in ((x0, xp1, "プロンプト（まとめて計算）", ACCENT),
                                 (xp1 + gap, xg1, "生成", OCHRE)):
        p.append(f'<path d="M{xa},{y0 - 40} V{y0 - 52} H{xb} V{y0 - 40}" fill="none" '
                 f'stroke="{color}" stroke-width="3"/>')
        text((xa + xb) / 2, y0 - 64, label, 26)
    text(x0 + 13 * (sw + gap) + 150, y0 - 64, "空き（確保済み）", 24, "middle", "sub")

    # 新しいトークンが過去の K・V を全部読む
    xn = xg1 + gap + sw / 2
    p.append(f'<rect x="{xg1 + gap}" y="{y0}" width="{sw}" height="{sh}" rx="4" '
             f'fill="#ffffff" stroke="{INK}" stroke-width="3"/>')
    ya = y0 + sh + 20
    p.append(f'<path d="M{xn},{ya} C{xn - 40},{ya + 70} {x0 + 60},{ya + 70} {x0 + 17},{ya + 6}" '
             f'fill="none" stroke="{INK}" stroke-width="3"/>')
    p.append(f'<polygon points="{x0 + 17},{ya} {x0 + 7},{ya + 20} {x0 + 29},{ya + 16}" '
             f'fill="{INK}"/>')
    text((x0 + xn) / 2, ya + 90, "次のトークンは、埋まった枠の K と V を全部読む", 24)

    # 下の札: num_ctx の分を読み込み時に確保
    xe = x0 + slots * (sw + gap) - gap
    yb = 470
    p.append(f'<path d="M{x0},{yb - 12} V{yb} H{xe} V{yb - 12}" fill="none" '
             f'stroke="{SUB}" stroke-width="2"/>')
    text((x0 + xe) / 2, yb + 34, "読み込んだ時に num_ctx 個の枠を全部確保する", 24, "middle", "sub")
    IMAGES.mkdir(exist_ok=True)
    (IMAGES / "kv-cache_concept.svg").write_text("\n".join(p + ["</svg>"]) + "\n",
                                                  encoding="utf-8")


class Svg:
    """Hand-drawn SVG with the approved palette (text >= 24px, no bold)."""

    def __init__(self, w, h, title):
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

    def save(self, name):
        IMAGES.mkdir(exist_ok=True)
        (IMAGES / name).write_text("\n".join(self.p + ["</svg>"]) + "\n", encoding="utf-8")


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
    s.text(480, 522, "KV ヘッドの数がキャッシュの大きさに比例する（28 層、head_dim 128、f16）",
           24, "middle", "sub")
    s.save("kv-cache_gqa.svg")


# The q4_K_M file size (1.36 GB) is quoted from the quantization note (ollama list).
Q4_FILE_GB = 1.36


def breakdown_figure():
    """q4_K_M を num_ctx 4,096 と 40,960 で読み込んだ時の size を、KV キャッシュとそれ以外に分ける。"""
    rows = json.loads((LAB / "memory.json").read_text())
    q4 = sorted((r for r in rows if r["model"] == "qwen3:1.7b-q4_K_M" and r["ps"]),
                key=lambda r: (r["num_ctx"] is None, r["num_ctx"] or 0))
    s = Svg(960, 440, "q4_K_M の読み込み時の size を、KV キャッシュとそれ以外に分ける")
    x0, scale = 290, 95  # px per GB
    xf = x0 + Q4_FILE_GB * scale
    s.line(xf, 78, xf, 330, SUB, 2, "6 5")
    s.text(xf, 64, f"ファイル {Q4_FILE_GB:.2f} GB", 24, "middle", "sub")
    for i, r in enumerate(q4):
        y = 110 + i * 130
        ctx = r["ps"]["context_length"]
        total = r["ps"]["size"] / 1e9
        kv = PER_TOKEN * ctx / 1e9
        rest = total - kv
        label = f"num_ctx {ctx:,}" if r["num_ctx"] else "num_ctx 未指定"
        s.text(30, y + 44, label, 26, "start")
        if r["num_ctx"] is None:
            s.text(30, y + 80, f"（{ctx:,} で読み込み）", 24, "start", "sub")
        s.rect(x0, y, rest * scale, 70, PALE, ACCENT, 2.5)
        s.rect(x0 + rest * scale, y, kv * scale, 70, OCHRE_PALE, OCHRE, 2.5)
        s.text(x0 + rest * scale / 2, y + 44, f"{rest:.2f} GB", 24)
        if kv * scale > 200:
            s.text(x0 + rest * scale + kv * scale / 2, y + 44, f"KV キャッシュ {kv:.2f} GB", 24)
            s.text(x0 + total * scale, y + 104, f"計 {total:.2f} GB", 24, "end")
        else:
            s.text(x0 + total * scale + 14, y + 44, f"計 {total:.2f} GB（うち KV {kv:.2f}）",
                   24, "start")
    s.rect(290, 392, 28, 28, PALE, ACCENT, 2.5)
    s.text(328, 414, "重み・作業領域", 24, "start")
    s.rect(540, 392, 28, 28, OCHRE_PALE, OCHRE, 2.5)
    s.text(578, 414, "KV キャッシュ（num_ctx 個の枠）", 24, "start")
    s.save("kv-cache_breakdown.svg")


# Weights read per generated token for q8_0, excluding the input embedding
# (the body text: about 1.88 GB; 1.885 reproduces the 1.95 / 5.41 GB in the text).
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
        s.text(x0 + WEIGHTS_READ_GB * scale / 2, y + 43, "重み", 24)
        if kv * scale > 120:
            s.text(x0 + (WEIGHTS_READ_GB + kv / 2) * scale, y + 43, f"K・V {kv:.2f}", 24)
        s.text(x0 + (WEIGHTS_READ_GB + kv) * scale, y + 98,
               f"計 {WEIGHTS_READ_GB + kv:.2f} GB", 24, "end")
        s.text(930, y + 43, f"{speed:.1f} トークン/秒", 26, "end")
    s.text(480, 372, "読む量は約 2.8 倍、速さは約 2.4 分の 1（num_ctx 32,768、q8_0）",
           24, "middle", "sub")
    s.save("kv-cache_read_per_token.svg")


def prefix_figure():
    """5 通りの送り方で、先頭からどこまでキャッシュを使えたかとプロンプトの処理の時間。"""
    rows = json.loads((LAB / "prefix.json").read_text())
    med = {}
    for r in rows:
        med.setdefault(r["case"], []).append(r["prompt_eval_s"])
    # (case, label, fraction reused from the head). The fractions are schematic, read from
    # what each case sends (case 4 edits the middle line); only the times are measured.
    cases = (("1 first send", "1 初回", 0.0),
             ("2 same prompt again", "2 同じ入力をもう一度", 1.0),
             ("3 same prefix, new question", "3 同じ前置き・別の質問", 0.985),
             ("4 one line edited in the middle", "4 真ん中の 1 行を変更", 0.5),
             ("5 one char added at the head", "5 先頭に 1 文字を追加", 0.0))
    s = Svg(960, 540, "同じ前置きを送り直した時に、キャッシュを使えた範囲と処理の時間")
    s.rect(330, 32, 28, 28, PALE, ACCENT, 2.5)
    s.text(368, 54, "キャッシュから使う", 24, "start")
    s.rect(600, 32, 28, 28, OCHRE_PALE, OCHRE, 2.5)
    s.text(638, 54, "計算し直す", 24, "start")
    x0, width = 330, 420
    for i, (case, label, frac) in enumerate(cases):
        y = 100 + i * 80
        s.text(30, y + 32, label, 24, "start")
        if frac > 0:
            s.rect(x0, y, width * frac, 44, PALE, ACCENT, 2.5)
        if frac < 1:
            s.rect(x0 + width * frac, y, width * (1 - frac), 44, OCHRE_PALE, OCHRE, 2.5)
        s.text(930, y + 32, f"{statistics.median(med[case]):.3f} 秒", 26, "end")
    s.text(x0 + width / 2, 520, "約 8,300 トークンの前置き、3 巡の中央値", 24, "middle", "sub")
    s.save("kv-cache_prefix.svg")


if __name__ == "__main__":
    concept_figure()
    gqa_figure()
    if (LAB / "memory.json").exists():
        memory_figure()
        breakdown_figure()
    if (LAB / "prefill.json").exists():
        prefill_figure()
        read_per_token_figure()
    if (LAB / "prefix.json").exists():
        prefix_figure()
