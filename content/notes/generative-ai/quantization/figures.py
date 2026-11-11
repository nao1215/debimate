"""Generate the figures of the quantization note from the JSON files in lab/.

Needs matplotlib, NumPy, Pillow (to write WebP) and google-chrome (headless, to render
the hand-written SVG figures). Run: python3 figures.py
"""

import json
import subprocess
import tempfile
from html import escape
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

HERE = Path(__file__).resolve().parent
LAB = HERE / "lab"
IMG = HERE / "images"

INK, SUB, ACCENT, RED = "#1f1f1f", "#666666", "#7aa6c2", "#e15759"
ACCENT_PALE, OCHRE, OCHRE_PALE, FILL = "#eaf1f5", "#d4a24c", "#f8eed8", "#f2f2f2"
GREEN = "#8fae86"
FONT = "'Noto Sans CJK JP','Hiragino Sans','Yu Gothic',sans-serif"
plt.rcParams.update({
    "font.family": "Noto Sans CJK JP", "font.size": 13, "axes.edgecolor": SUB,
    "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK, "text.color": INK,
    "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
})
MODELS = ["qwen3:1.7b-q4_K_M", "qwen3:1.7b-q8_0", "qwen3:1.7b-fp16"]
SHORT = ["q4_K_M", "q8_0", "fp16"]


def load(name):
    return json.loads((LAB / name).read_text())


def save_fig(fig, name):
    """matplotlib -> PNG (dpi 200, white background) -> WebP."""
    IMG.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        png = Path(tmp) / "fig.png"
        fig.savefig(png, dpi=200, facecolor="#ffffff", bbox_inches="tight")
        Image.open(png).convert("RGB").save(IMG / name, "WEBP", quality=90, method=6)
    plt.close(fig)


def save_svg(parts, name, width, height):
    """Hand-written SVG -> headless Chrome at 2x -> WebP. The SVG itself is not kept."""
    IMG.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        svg, png = Path(tmp) / "fig.svg", Path(tmp) / "fig.png"
        svg.write_text("\n".join(parts + ["</svg>"]) + "\n", encoding="utf-8")
        subprocess.run(
            ["google-chrome", "--headless=new", "--disable-gpu", "--hide-scrollbars",
             "--force-device-scale-factor=2", f"--window-size={width},{height}",
             f"--screenshot={png}", svg.as_uri()], check=True, capture_output=True)
        Image.open(png).convert("RGB").save(IMG / name, "WEBP", quality=90, method=6)


def svg_start(title, width=960, height=540):
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img"><title>{escape(title)}</title>',
        f'<style>text{{font-family:{FONT};fill:{INK}}} .sub{{fill:{SUB}}}</style>',
        f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
    ]


def svg_text(p, x, y, s, size=26, anchor="middle", cls=""):
    c = f' class="{cls}"' if cls else ""
    p.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}"{c}>'
             f'{escape(s)}</text>')


def concept_figure():
    """The same 8 weights stored in 16, 8 and 4 bits: the box narrows, the dots drift."""
    blk = load("block_error.json")["block"]
    w = blk["w"][24:]
    rows = [("FP16", 16, w, None, ACCENT, ACCENT_PALE),
            ("8 bit", 8, blk["q8"][24:], 0.000708, ACCENT, ACCENT_PALE),
            ("4 bit", 4, blk["q4"][24:], 0.011230, OCHRE, OCHRE_PALE)]
    width, height = 960, 540
    p = svg_start("同じ 8 個の重みを 16・8・4 bit で持つと、1 個の箱が細くなり、"
                  "丸めた値が元の値からずれる", width, height)

    # Value axis shared by the three rows (x in pixels).
    lo, hi, x0, x1 = -0.095, 0.050, 400, 930

    def vx(v):
        return x0 + (v - lo) / (hi - lo) * (x1 - x0)

    # Legend.
    p.append(f'<circle cx="390" cy="38" r="9" fill="#ffffff" stroke="{INK}" stroke-width="2.5"/>')
    svg_text(p, 408, 47, "元の値", 24, "start")
    p.append(f'<circle cx="516" cy="38" r="9" fill="{ACCENT}" stroke="{INK}" stroke-width="2"/>')
    svg_text(p, 534, 47, "丸めて戻した値", 24, "start")
    p.append(f'<line x1="736" y1="30" x2="736" y2="46" stroke="{OCHRE}" stroke-width="2"/>')
    svg_text(p, 750, 47, "表せる値", 24, "start")
    svg_text(p, 40, 47, "重み 1 個の幅", 24, "start", cls="sub")

    for i, (label, bits, rounded, step, color, pale) in enumerate(rows):
        top = 90 + i * 150
        mid = top + 60
        # Left: one weight as `bits` cells; the box narrows with the bit width.
        svg_text(p, 40, top + 34, label, 30, "start")
        cell = 18
        for b in range(bits):
            p.append(f'<rect x="{40 + b * cell}" y="{top + 56}" width="{cell}" height="34" '
                     f'fill="{pale}" stroke="{color}" stroke-width="2"/>')
        # Right: the grid of values this format can hold, as ticks on the axis.
        p.append(f'<line x1="{x0}" y1="{mid + 40}" x2="{x1}" y2="{mid + 40}" '
                 f'stroke="{SUB}" stroke-width="1.5"/>')
        if step:
            k = int(lo / step) - 1
            while k * step <= hi:
                x = vx(k * step)
                if x0 <= x <= x1:
                    tall = 14 if step > 0.005 else 7
                    p.append(f'<line x1="{x:.1f}" y1="{mid + 40 - tall}" x2="{x:.1f}" '
                             f'y2="{mid + 40}" stroke="{color}" stroke-width="1.5"/>')
                k += 1
        for v, r in zip(w, rounded):
            # Original value above, rounded value on the axis, joined by a line.
            p.append(f'<line x1="{vx(v):.1f}" y1="{mid - 28}" x2="{vx(r):.1f}" y2="{mid + 30}" '
                     f'stroke="{SUB}" stroke-width="1.5"/>')
            p.append(f'<circle cx="{vx(v):.1f}" cy="{mid - 30}" r="9" fill="#ffffff" '
                     f'stroke="{INK}" stroke-width="2.5"/>')
            p.append(f'<circle cx="{vx(r):.1f}" cy="{mid + 30}" r="9" fill="{color}" '
                     f'stroke="{INK}" stroke-width="2"/>')
    svg_text(p, vx(0), 528, "0", 24, cls="sub")
    p.append(f'<line x1="{vx(0):.1f}" y1="500" x2="{vx(0):.1f}" y2="508" stroke="{SUB}" '
             'stroke-width="1.5"/>')
    save_svg(p, "quantization_concept.webp", width, height)


def structure_figure():
    """Which weight matrices Qwen3-1.7B has: embedding, 28 layers of attention + FFN, output."""
    width, height = 960, 420
    p = svg_start("Qwen3-1.7B の重み行列: 入力の埋め込み、注意機構と FFN を持つ層を 28 段、出力の層",
                  width, height)

    def box(x, y, w, h, fill, stroke, sw=2):
        p.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{fill}" '
                 f'stroke="{stroke}" stroke-width="{sw}"/>')

    def arrow(x1, x2, y):
        p.append(f'<line x1="{x1}" y1="{y}" x2="{x2 - 10}" y2="{y}" stroke="{SUB}" stroke-width="2.5"/>')
        p.append(f'<polygon points="{x2},{y} {x2 - 12},{y - 7} {x2 - 12},{y + 7}" fill="{SUB}"/>')

    mid = 215
    # Input embedding.
    box(16, mid - 60, 176, 120, FILL, SUB)
    svg_text(p, 104, mid - 12, "入力の埋め込み", 21)
    svg_text(p, 104, mid + 22, "token_embd", 20, cls="sub")
    arrow(192, 222, mid)
    # One layer, repeated 28 times (drawn as a stack).
    for k in (2, 1):
        box(222 + k * 10, 50 - k * 10, 520, 330, "#ffffff", "#bbbbbb", 1.5)
    box(222, 50, 520, 330, "#ffffff", INK, 2.5)
    svg_text(p, 482, 86, "層（同じ形を 28 段重ねる）", 24)
    # Attention.
    box(242, 108, 230, 252, ACCENT_PALE, ACCENT)
    svg_text(p, 357, 140, "注意機構", 24)
    for i, name in enumerate(["attn_q", "attn_k", "attn_v", "attn_output"]):
        box(267, 158 + i * 48, 180, 38, "#ffffff", ACCENT, 1.5)
        svg_text(p, 357, 184 + i * 48, name, 20)
    arrow(472, 512, 234)
    # FFN.
    box(512, 108, 210, 252, OCHRE_PALE, OCHRE)
    svg_text(p, 617, 140, "FFN", 24)
    for i, name in enumerate(["ffn_gate", "ffn_up", "ffn_down"]):
        box(537, 158 + i * 48, 160, 38, "#ffffff", OCHRE, 1.5)
        svg_text(p, 617, 184 + i * 48, name, 20)
    svg_text(p, 617, 336, "全結合のネットワーク", 18, cls="sub")
    arrow(762, 800, mid)
    # Output layer.
    box(800, mid - 60, 140, 120, FILL, SUB)
    svg_text(p, 870, mid - 12, "出力の層", 22)
    svg_text(p, 870, mid + 22, "output", 20, cls="sub")
    save_svg(p, "quantization_structure.webp", width, height)


def block_figure():
    """Why the scale is kept per 32 weights: one large value coarsens its whole group."""
    w = np.array(load("block_error.json")["block"]["w"], dtype=np.float32)
    # 32 個ごとのスケール（このブロックの最大は 0.0898）と、
    # 仮に 10 倍の 0.9 を含む大きな組と同じスケールを使った場合（説明用の仮の値）
    cases = [("32 個ごとにスケールを持つ（d = 0.0112）", float(np.abs(w).max()) / 8, OCHRE),
             ("0.9 の重みと同じスケールを使う（d = 0.1125）", 0.9 / 8, OCHRE)]
    fig, axes = plt.subplots(2, 1, figsize=(7.6, 4.6), sharex=True)
    idx = np.arange(1, 33)
    for ax, (title, d, color) in zip(axes, cases):
        q = np.clip(np.round(w / d), -8, 7)
        r = q * d
        for i in range(32):
            ax.plot([idx[i], idx[i]], [w[i], r[i]], color=SUB, lw=1)
        ax.scatter(idx, w, s=28, facecolor="#ffffff", edgecolor=INK, lw=1.2, zorder=3,
                   label="元の値")
        ax.scatter(idx, r, s=28, color=color, edgecolor=INK, lw=0.8, zorder=4,
                   label="丸めて戻した値")
        ax.axhline(0, color=SUB, lw=0.8)
        zeros = int((q == 0).sum())
        ax.set_title(f"{title}: 0 に潰れた重み {zeros} / 32", fontsize=13, loc="left")
        ax.set_ylim(-0.13, 0.13)
        ax.set_yticks([-0.1, 0, 0.1])
        ax.spines[["top", "right"]].set_visible(False)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, frameon=False, fontsize=12, ncol=2, loc="upper right",
               bbox_to_anchor=(1.0, 1.07))
    axes[1].set_xticks([1, 8, 16, 24, 32])
    axes[1].set_xlabel("ブロックの中の位置（1〜32 番目の重み）")
    fig.supylabel("重みの値", fontsize=13)
    fig.tight_layout()
    save_fig(fig, "quantization_block.webp")


def layout_figure():
    """Bytes for 256 weights in Q8_0, Q4_0 and Q4_K, drawn to scale."""
    p = svg_start("256 個の重みを Q8_0・Q4_0・Q4_K で持った時のバイトの並び。"
                  "Q4_0 と Q4_K はどちらも 144 バイト")
    px = 2.3                                   # pixels per byte
    x0 = 150
    rows = [  # name, [(bytes, kind)]
        ("Q8_0", [(2, "s"), (32, "q")] * 8),
        ("Q4_0", [(2, "s"), (16, "q")] * 8),
        ("Q4_K", [(4, "s"), (12, "s2")] + [(16, "q")] * 8),
    ]
    svg_text(p, 40, 52, "256 個の重みのバイト数（長さはバイト数に比例）", 26, "start", cls="sub")
    for i, (name, parts) in enumerate(rows):
        y = 100 + i * 115
        svg_text(p, 40, y + 38, name, 30, "start")
        x = x0
        for nbytes, kind in parts:
            fill, stroke = (ACCENT_PALE, ACCENT) if kind == "q" else (OCHRE, OCHRE)
            if kind == "s2":
                fill = OCHRE_PALE
            p.append(f'<rect x="{x:.1f}" y="{y}" width="{nbytes * px:.1f}" height="56" '
                     f'fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>')
            x += nbytes * px
        total = sum(n for n, _ in parts)
        svg_text(p, x + 16, y + 26, f"{total} バイト", 26, "start")
        svg_text(p, x + 16, y + 58, f"1 個 {total * 8 / 256:g} bit", 24, "start", cls="sub")
    lx, ly = 40, 500
    for dx, fill, stroke, label in ((0, ACCENT_PALE, ACCENT, "整数"),
                                    (120, OCHRE, OCHRE, "FP16 の d（Q4_K は d と dmin）"),
                                    (500, OCHRE_PALE, OCHRE, "小ブロックの 6 bit の値（12 バイト）")):
        p.append(f'<rect x="{lx + dx}" y="{ly - 20}" width="28" height="24" fill="{fill}" '
                 f'stroke="{stroke}" stroke-width="1.5"/>')
        svg_text(p, lx + dx + 38, ly, label, 22, "start")
    save_svg(p, "quantization_layout.webp", 960, 540)


def size_figure():
    """File size of the three GGUF files, stacked by tensor type."""
    g = load("gguf.json")
    types = [("F32", "#cccccc"), ("F16", ACCENT), ("Q8_0", GREEN),
             ("Q6_K", "#b7a3c9"), ("Q4_K", OCHRE)]
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    seen = set()
    for y, name in enumerate(SHORT):
        left = g[name]["file_size"] - g[name]["weight_bytes"]          # header (tokenizer etc.)
        ax.barh(y, left / 1e9, color="#ffffff", edgecolor=SUB, lw=0.8)
        for t, c in types[::-1]:
            s = g[name]["by_type"].get(t)
            if not s:
                continue
            ax.barh(y, s["bytes"] / 1e9, left=left / 1e9, color=c, edgecolor=INK, lw=0.6,
                    label=None if t in seen or t == "F32" else t)
            seen.add(t)
            left += s["bytes"]
        bpp = g[name]["weight_bytes"] * 8 / g[name]["params"]
        ax.text(left / 1e9 + 0.05, y, f"{g[name]['file_size'] / 1e9:.2f} GB\n"
                f"（重み 1 個 {bpp:.2f} bit）", va="center", fontsize=12)
    ax.set_yticks(range(3), SHORT)
    ax.invert_yaxis()
    ax.set_xlim(0, 6.2)
    ax.set_xlabel("ファイルの大きさ（GB）")
    handles, labels = ax.get_legend_handles_labels()
    order = sorted(range(len(labels)), key=lambda i: [t for t, _ in types].index(labels[i]))
    ax.legend([handles[i] for i in order], [labels[i] for i in order], ncol=5,
              loc="lower left", frameon=False, fontsize=12, bbox_to_anchor=(0.0, 1.0),
              handlelength=1.2, columnspacing=1.0)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    save_fig(fig, "quantization_size.webp")


def error_figure():
    """Relative RMSE of one matrix, and the spread of the errors of the two Ollama files."""
    b = load("block_error.json")
    fig, axes = plt.subplots(1, 2, figsize=(7.6, 4.0), gridspec_kw={"width_ratios": [1.25, 1]})
    ax = axes[0]
    rows = [("Q8_0 (mine)", "Q8_0 自作", GREEN),
            ("Q8_0 (Ollama q8_0 file)", "Q8_0 Ollama", GREEN),
            ("Q4_0 (mine)", "Q4_0 自作", OCHRE),
            ("Q4 scale+min (mine)", "4 bit 最小値付き 自作", OCHRE),
            ("Q4_K (Ollama q4_K_M file)", "Q4_K Ollama", OCHRE)]
    vals = [b["rel_rmse"][k] * 100 for k, _, _ in rows]
    ax.barh(range(5), vals, color=[c for _, _, c in rows], edgecolor=INK, lw=0.6)
    for y, v in enumerate(vals):
        ax.text(v + 0.2, y, f"{v:.2f}%", va="center", fontsize=12)
    ax.set_yticks(range(5), [s for _, s, _ in rows])
    ax.invert_yaxis()
    ax.set_xlim(0, 12.5)
    ax.set_xlabel("誤差の相対値（relative RMSE, %）")
    ax.spines[["top", "right"]].set_visible(False)
    ax = axes[1]
    edges = b["hist_edges"]
    centers = [(a + c) / 2 for a, c in zip(edges, edges[1:])]
    for k, name, c in (("Q8_0 (Ollama q8_0 file)", "Q8_0 Ollama", GREEN),
                       ("Q4_K (Ollama q4_K_M file)", "Q4_K Ollama", OCHRE)):
        h = b["hist"][k]
        share = [v / sum(h) * 100 for v in h]
        ax.plot(centers, share, color=c, lw=2.2, label=name)
    ax.set_xlabel("戻した値 − 元の値")
    ax.set_ylabel("重みの割合（%、幅 0.0005 ごと）")
    ax.set_xlim(-0.012, 0.012)
    ax.set_xticks([-0.01, 0, 0.01], ["-0.01", "0", "0.01"])
    ax.legend(frameon=False, fontsize=12, loc="upper left", handlelength=1.2)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    save_fig(fig, "quantization_error.webp")


def accuracy_figure():
    """Correct answers out of 100, split into arithmetic and knowledge."""
    a = load("accuracy.json")["models"]
    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    for y, (m, name) in enumerate(zip(MODELS, SHORT)):
        rows = a[m]
        math = sum(r["correct"] for r in rows if r["kind"] == "math")
        know = sum(r["correct"] for r in rows if r["kind"] == "knowledge")
        ax.barh(y, math, color=ACCENT, edgecolor=INK, lw=0.6,
                label="算数（40 問）" if y == 0 else None)
        ax.barh(y, know, left=math, color=OCHRE_PALE, edgecolor=INK, lw=0.6,
                label="常識（60 問）" if y == 0 else None)
        ax.text(math / 2, y, str(math), ha="center", va="center", fontsize=13)
        ax.text(math + know / 2, y, str(know), ha="center", va="center", fontsize=13)
        ax.text(math + know + 1, y, f"{math + know} / 100", va="center", fontsize=13)
    ax.set_yticks(range(3), SHORT)
    ax.invert_yaxis()
    ax.set_xlim(0, 120)
    ax.set_xlabel("正答の数（思考モードなし、温度 0）")
    ax.legend(ncol=2, loc="lower left", frameon=False, fontsize=12, bbox_to_anchor=(0.0, 1.0))
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    save_fig(fig, "quantization_accuracy.webp")


# Qwen3-1.7B: 28 layers, 8 KV heads of 128 dims, K and V in FP16 (config.json on Hugging Face).
KV_BYTES_PER_TOKEN = 28 * 2 * 8 * 128 * 2
PROMPT_TOKENS = 950
EMBD_PARAMS = 151936 * 2048            # token_embd: only one row is read per token


def read_per_token():
    """Bytes read per generated token: weights minus the input embedding, plus the KV cache."""
    g = load("gguf.json")
    bits = {"Q4_K": 4.5, "Q8_0": 8.5, "F16": 16}
    out = {}
    for name in SHORT:
        embd = EMBD_PARAMS * bits[g[name]["tensor_types"]["token_embd.weight"]] / 8
        out[name] = g[name]["weight_bytes"] - embd + KV_BYTES_PER_TOKEN * PROMPT_TOKENS
    return out


def speedup_figure():
    """Speed-up over fp16 expected from the bytes read, next to the measured median."""
    read = read_per_token()
    s = load("speed.json")["summary"]
    names = ["q8_0", "q4_K_M"]
    expected = [read["fp16"] / read[n] for n in names]
    measured = [s[f"qwen3:1.7b-{n}"]["eval_median"] / s["qwen3:1.7b-fp16"]["eval_median"]
                for n in names]
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    w = 0.36
    for i in range(2):
        ax.bar(i - w / 2, expected[i], w, color="#ffffff", edgecolor=SUB, lw=1.2,
               label="読む量からの計算" if i == 0 else None)
        ax.bar(i + w / 2, measured[i], w, color=ACCENT, edgecolor=INK, lw=0.8,
               label="実測（9 回の中央値）" if i == 0 else None)
        ax.text(i - w / 2, expected[i] + 0.06, f"{expected[i]:.1f} 倍", ha="center", fontsize=13)
        ax.text(i + w / 2, measured[i] + 0.06, f"{measured[i]:.1f} 倍", ha="center", fontsize=13)
    ax.axhline(1, color=SUB, lw=1, ls="--")
    ax.text(1.62, 1.04, "fp16 と同じ", color=SUB, fontsize=12, ha="right", va="bottom")
    ax.set_xticks(range(2), names)
    ax.set_xlim(-0.6, 1.65)
    ax.set_ylim(0, 3.3)
    ax.set_ylabel("fp16 に対する生成の速さ")
    ax.legend(frameon=False, fontsize=12, loc="upper left")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    save_fig(fig, "quantization_speedup.webp")


def tradeoff_figure():
    """File size, generation speed and correct answers of the three models side by side."""
    g = load("gguf.json")
    s = load("speed.json")["summary"]
    a = load("accuracy.json")["models"]
    panels = [
        ("ファイルの大きさ（GB）", [g[n]["file_size"] / 1e9 for n in SHORT], "{:.2f}"),
        ("生成（トークン毎秒）", [s[m]["eval_median"] for m in MODELS], "{:.0f}"),
        ("正答（100 問中）", [sum(r["correct"] for r in a[m]) for m in MODELS], "{:d}"),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 3.6))
    colors = [OCHRE, GREEN, ACCENT]
    for ax, (title, vals, fmt) in zip(axes, panels):
        ax.bar(range(3), vals, color=colors, edgecolor=INK, lw=0.8, width=0.62)
        top = max(vals)
        for i, v in enumerate(vals):
            ax.text(i - 0.08 if title.startswith("生成") else i, v * 0.25 if title.startswith("生成") else v + top * 0.03,
                    fmt.format(v), ha="center", fontsize=12)
        ax.set_ylim(0, top * 1.22)
        ax.set_title(title, fontsize=13)
        if title.startswith("生成"):                 # 9 runs: min-max as a line
            lo = [v - s[m]["eval_min"] for v, m in zip(vals, MODELS)]
            hi = [s[m]["eval_max"] - v for v, m in zip(vals, MODELS)]
            ax.errorbar([i + 0.2 for i in range(3)], vals, yerr=[lo, hi], fmt="none", ecolor=INK, capsize=4, lw=1)
            ax.set_ylim(0, 70)
        ax.set_xticks(range(3), SHORT, rotation=30, ha="right", rotation_mode="anchor")
        ax.set_yticks([])
        ax.spines[["top", "right", "left"]].set_visible(False)
    fig.tight_layout()
    save_fig(fig, "quantization_tradeoff.webp")


if __name__ == "__main__":
    concept_figure()
    structure_figure()
    block_figure()
    layout_figure()
    size_figure()
    error_figure()
    accuracy_figure()
    speedup_figure()
    tradeoff_figure()
