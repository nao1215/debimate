"""Generate the figures of the quantization note from the JSON files in lab/."""

import json
from html import escape
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
LAB = HERE / "lab"

INK, SUB, ACCENT, RED = "#1f1f1f", "#666666", "#7aa6c2", "#e15759"
ACCENT_PALE, OCHRE, OCHRE_PALE, FILL = "#eaf1f5", "#d4a24c", "#f8eed8", "#f2f2f2"
GREEN = "#8fae86"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"
plt.rcParams.update({
    "font.size": 14, "axes.edgecolor": SUB, "axes.labelcolor": INK,
    "xtick.color": INK, "ytick.color": INK, "text.color": INK,
    "svg.fonttype": "path", "svg.hashsalt": "quantization",
    "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
})
MODELS = ["qwen3:1.7b-q4_K_M", "qwen3:1.7b-q8_0", "qwen3:1.7b-fp16"]
SHORT = ["q4_K_M", "q8_0", "fp16"]


def load(name):
    return json.loads((LAB / name).read_text())


def concept_figure():
    """The same 8 weights stored in 16, 8 and 4 bits: the box narrows, the dots drift."""
    blk = load("block_error.json")["block"]
    w = blk["w"][24:]
    rows = [("FP16", 16, w, None, ACCENT, ACCENT_PALE),
            ("8 bit", 8, blk["q8"][24:], 0.000708, ACCENT, ACCENT_PALE),
            ("4 bit", 4, blk["q4"][24:], 0.011230, OCHRE, OCHRE_PALE)]
    width, height = 960, 540
    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img"><title>'
        f'{escape("同じ 8 個の重みを 16・8・4 bit で持つと、1 個の箱が細くなり、丸めた値が元の値からずれる")}'
        f'</title>',
        f'<style>text{{font-family:{FONT};fill:{INK}}} .sub{{fill:{SUB}}}</style>',
        f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
    ]

    def text(x, y, s, size=26, anchor="middle", weight="normal", cls=""):
        c = f' class="{cls}"' if cls else ""
        p.append(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
                 f'text-anchor="{anchor}"{c}>{escape(s)}</text>')

    # Value axis shared by the three rows (x in pixels).
    lo, hi, x0, x1 = -0.095, 0.050, 400, 930

    def vx(v):
        return x0 + (v - lo) / (hi - lo) * (x1 - x0)

    # Legend.
    p.append(f'<circle cx="390" cy="38" r="9" fill="#ffffff" stroke="{INK}" stroke-width="2.5"/>')
    text(408, 47, "元の値", 24, "start")
    p.append(f'<circle cx="516" cy="38" r="9" fill="{ACCENT}" stroke="{INK}" stroke-width="2"/>')
    text(534, 47, "丸めて戻した値", 24, "start")
    p.append(f'<line x1="736" y1="30" x2="736" y2="46" stroke="{OCHRE}" stroke-width="2"/>')
    text(750, 47, "表せる値", 24, "start")
    text(40, 47, "1 個の重みの幅", 24, "start", cls="sub")

    for i, (label, bits, rounded, step, color, pale) in enumerate(rows):
        top = 90 + i * 150
        mid = top + 60
        # Left: one weight as `bits` cells; the box narrows with the bit width.
        text(40, top + 34, label, 30, "start", weight="normal")
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
    text(vx(0), 528, "0", 24, cls="sub")
    p.append(f'<line x1="{vx(0):.1f}" y1="500" x2="{vx(0):.1f}" y2="508" stroke="{SUB}" '
             'stroke-width="1.5"/>')
    (HERE / "images" / "quantization_concept.svg").write_text("\n".join(p + ["</svg>"]) + "\n")


def size_figure():
    """File size of the three GGUF files, stacked by tensor type."""
    g = load("gguf.json")
    types = [("F32", "#cccccc"), ("F16", ACCENT), ("Q8_0", GREEN),
             ("Q6_K", OCHRE), ("Q4_K", "#b9d0de")]
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
                    label=None if t in seen else t)
            seen.add(t)
            left += s["bytes"]
        bpp = g[name]["weight_bytes"] * 8 / g[name]["params"]
        ax.text(left / 1e9 + 0.05, y, f"{g[name]['file_size'] / 1e9:.2f} GB\n"
                f"({bpp:.2f} bits/param)", va="center", fontsize=13)
    ax.set_yticks(range(3), SHORT)
    ax.invert_yaxis()
    ax.set_xlim(0, 6.0)
    ax.set_xlabel("File size (GB)")
    handles, labels = ax.get_legend_handles_labels()
    order = sorted(range(len(labels)), key=lambda i: [t for t, _ in types].index(labels[i]))
    ax.legend([handles[i] for i in order], [labels[i] for i in order], ncol=5,
              loc="lower left", frameon=False, fontsize=13, bbox_to_anchor=(0.0, 1.0),
              handlelength=1.2, columnspacing=1.0)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(HERE / "images" / "quantization_size.svg", metadata={"Date": None})


def speed_figure():
    """Median tokens/s with the min-max range, for prompt processing and generation."""
    data = load("speed.json")
    s, runs = data["summary"], data["runs"]
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 4.0))
    panels = [("eval", "Generation (tokens/s)"), ("prompt", "Prompt processing (tokens/s)")]
    colors = [OCHRE, GREEN, ACCENT]
    for ax, (key, label) in zip(axes, panels):
        med = [s[m][f"{key}_median"] for m in MODELS]
        lo = [med[i] - s[m][f"{key}_min"] for i, m in enumerate(MODELS)]
        hi = [s[m][f"{key}_max"] - med[i] for i, m in enumerate(MODELS)]
        ax.bar(range(3), med, color=colors, edgecolor=INK, lw=0.8, width=0.6)
        ax.errorbar([i + 0.22 for i in range(3)], med, yerr=[lo, hi], fmt="none", ecolor=INK,
                    capsize=4, lw=1)
        for i, m in enumerate(MODELS):                      # each of the 9 runs
            vals = [r[f"{key}_tps"] for r in runs if r["model"] == m]
            ax.scatter([i + 0.22] * len(vals), vals, s=10, color=INK, zorder=3)
        for i, v in enumerate(med):
            ax.text(i, v * 0.5, f"{v:.0f}", ha="center", va="center", fontsize=14)
        ax.set_xticks(range(3), SHORT)
        ax.set_ylabel(label)
        ax.spines[["top", "right"]].set_visible(False)
    fig.text(0.5, 0.01, "bar: median of 9 runs, line: min-max, dots: each run", ha="center", color=SUB, fontsize=13)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.savefig(HERE / "images" / "quantization_speed.svg", metadata={"Date": None})


def accuracy_figure():
    """Correct answers out of 100, split into arithmetic and knowledge."""
    a = load("accuracy.json")["models"]
    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    for y, (m, name) in enumerate(zip(MODELS, SHORT)):
        rows = a[m]
        math = sum(r["correct"] for r in rows if r["kind"] == "math")
        know = sum(r["correct"] for r in rows if r["kind"] == "knowledge")
        ax.barh(y, math, color=ACCENT, edgecolor=INK, lw=0.6,
                label="arithmetic (40)" if y == 0 else None)
        ax.barh(y, know, left=math, color=OCHRE_PALE, edgecolor=INK, lw=0.6,
                label="knowledge (60)" if y == 0 else None)
        ax.text(math / 2, y, str(math), ha="center", va="center", fontsize=14)
        ax.text(math + know / 2, y, str(know), ha="center", va="center", fontsize=14)
        ax.text(math + know + 1, y, f"{math + know} / 100", va="center", fontsize=14)
    ax.set_yticks(range(3), SHORT)
    ax.invert_yaxis()
    ax.set_xlim(0, 120)
    ax.set_xlabel("Correct answers (thinking off, temperature 0)")
    ax.legend(ncol=2, loc="lower left", frameon=False, fontsize=13, bbox_to_anchor=(0.0, 1.0))
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(HERE / "images" / "quantization_accuracy.svg", metadata={"Date": None})


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


def matvec_figure():
    """Generation multiplies the weights by 1 vector; prompt processing by hundreds."""
    p = svg_start("生成では読んだ重みを 1 本のベクトルにしか掛けず、プロンプト処理では数百本に掛ける")
    panels = [(40, "生成（1 トークンずつ）", 1, "読んだ重み 1 個で計算 1 回",
               "読み出しの速さで決まる"),
              (500, "プロンプト処理（まとめて）", 10, "読んだ重み 1 個で計算 数百回",
               "計算の速さで決まる")]
    for x, title, cols, line1, line2 in panels:
        svg_text(p, x + 210, 60, title, 28)
        # The weight matrix: the same size on both sides.
        mx, my, mw, mh = x + 20, 110, 220, 220
        p.append(f'<rect x="{mx}" y="{my}" width="{mw}" height="{mh}" fill="{ACCENT_PALE}" '
                 f'stroke="{ACCENT}" stroke-width="2.5"/>')
        for k in range(1, 8):
            off = k * mw / 8
            p.append(f'<line x1="{mx + off:.1f}" y1="{my}" x2="{mx + off:.1f}" y2="{my + mh}" '
                     f'stroke="{ACCENT}" stroke-width="1"/>')
            p.append(f'<line x1="{mx}" y1="{my + off:.1f}" x2="{mx + mw}" y2="{my + off:.1f}" '
                     f'stroke="{ACCENT}" stroke-width="1"/>')
        svg_text(p, mx + mw / 2, my + mh + 36, "重み行列", 24)
        svg_text(p, mx + mw + 26, my + mh / 2 + 10, "×", 34)
        # The input vectors: 1 column, or a block of many columns.
        vx, vw = mx + mw + 52, 14
        for c in range(cols):
            p.append(f'<rect x="{vx + c * vw}" y="{my}" width="{vw}" height="{mh}" '
                     f'fill="{OCHRE_PALE}" stroke="{OCHRE}" stroke-width="2"/>')
        label = "ベクトル 1 本" if cols == 1 else "数百本"
        svg_text(p, vx + cols * vw / 2, my + mh + 36, label, 24)
        svg_text(p, x + 210, 440, line1, 26)
        svg_text(p, x + 210, 484, line2, 26, cls="sub")
    p.append(f'<line x1="480" y1="40" x2="480" y2="500" stroke="{FILL}" stroke-width="3"/>')
    (HERE / "images" / "quantization_matvec.svg").write_text("\n".join(p + ["</svg>"]) + "\n")


def layout_figure():
    """Bytes for 256 weights in Q8_0, Q4_0 and Q4_K, drawn to scale."""
    p = svg_start("256 個の重みを Q8_0・Q4_0・Q4_K で持った時のバイトの並び。"
                  "Q4_0 と Q4_K はどちらも 144 バイト")
    px = 2.3                                   # pixels per byte
    x0 = 150
    rows = [  # name, [(bytes, kind)], total bytes
        ("Q8_0", [(2, "s"), (32, "q")] * 8),
        ("Q4_0", [(2, "s"), (16, "q")] * 8),
        ("Q4_K", [(4, "s"), (12, "s2"), (128, "q")]),
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
    # Legend.
    lx, ly = 150, 500
    for dx, fill, stroke, label in ((0, ACCENT_PALE, ACCENT, "整数"),
                                    (130, OCHRE, OCHRE, "スケール（FP16）"),
                                    (370, OCHRE_PALE, OCHRE, "小ブロックの 6 bit の値")):
        p.append(f'<rect x="{lx + dx}" y="{ly - 20}" width="28" height="24" fill="{fill}" '
                 f'stroke="{stroke}" stroke-width="1.5"/>')
        svg_text(p, lx + dx + 38, ly, label, 24, "start")
    (HERE / "images" / "quantization_layout.svg").write_text("\n".join(p + ["</svg>"]) + "\n")


def error_figure():
    """Relative RMSE of one matrix, and the spread of the errors of the two Ollama files."""
    b = load("block_error.json")
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 4.0), gridspec_kw={"width_ratios": [1.15, 1]})
    ax = axes[0]
    rows = [("Q8_0 (mine)", "Q8_0 mine", GREEN), ("Q8_0 (Ollama q8_0 file)", "Q8_0 Ollama", GREEN),
            ("Q4_0 (mine)", "Q4_0 mine", OCHRE), ("Q4 scale+min (mine)", "Q4 min mine", OCHRE),
            ("Q4_K (Ollama q4_K_M file)", "Q4_K Ollama", OCHRE)]
    vals = [b["rel_rmse"][k] * 100 for k, _, _ in rows]
    ax.barh(range(5), vals, color=[c for _, _, c in rows], edgecolor=INK, lw=0.6)
    for y, v in enumerate(vals):
        ax.text(v + 0.2, y, f"{v:.2f}%", va="center", fontsize=13)
    ax.set_yticks(range(5), [s for _, s, _ in rows])
    ax.invert_yaxis()
    ax.set_xlim(0, 12.5)
    ax.set_xlabel("Relative RMSE (%)")
    ax.spines[["top", "right"]].set_visible(False)
    ax = axes[1]
    edges = b["hist_edges"]
    centers = [(a + c) / 2 for a, c in zip(edges, edges[1:])]
    for k, name, c in (("Q8_0 (Ollama q8_0 file)", "Q8_0", GREEN),
                       ("Q4_K (Ollama q4_K_M file)", "Q4_K", OCHRE)):
        h = b["hist"][k]
        share = [v / sum(h) * 100 for v in h]
        ax.plot(centers, share, color=c, lw=2.2, label=name)
    ax.set_xlabel("Restored - original")
    ax.set_ylabel("Share of weights (%)")
    ax.set_xlim(-0.012, 0.012)
    ax.set_xticks([-0.01, 0, 0.01], ["-0.01", "0", "0.01"])
    ax.legend(frameon=False, fontsize=13, loc="upper left", handlelength=1.2)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(HERE / "images" / "quantization_error.svg", metadata={"Date": None})


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
        ax.bar(i - w / 2, expected[i], w, color="#ffffff", edgecolor=SUB, lw=1.2, hatch=None,
               label="expected from bytes read" if i == 0 else None)
        ax.bar(i + w / 2, measured[i], w, color=ACCENT, edgecolor=INK, lw=0.8,
               label="measured (median of 9)" if i == 0 else None)
        ax.text(i - w / 2, expected[i] + 0.06, f"{expected[i]:.1f}x", ha="center", fontsize=14)
        ax.text(i + w / 2, measured[i] + 0.06, f"{measured[i]:.1f}x", ha="center", fontsize=14)
    ax.axhline(1, color=SUB, lw=1, ls="--")
    ax.text(1.62, 1.04, "fp16", color=SUB, fontsize=13, ha="right", va="bottom")
    ax.set_xticks(range(2), names)
    ax.set_xlim(-0.6, 1.65)
    ax.set_ylim(0, 3.3)
    ax.set_ylabel("Generation speed vs fp16")
    ax.legend(frameon=False, fontsize=13, loc="upper left")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(HERE / "images" / "quantization_speedup.svg", metadata={"Date": None})


def tradeoff_figure():
    """File size, generation speed and correct answers of the three models side by side."""
    g = load("gguf.json")
    s = load("speed.json")["summary"]
    a = load("accuracy.json")["models"]
    panels = [
        ("File size (GB)", [g[n]["file_size"] / 1e9 for n in SHORT], "{:.2f}"),
        ("Generation (tokens/s)", [s[m]["eval_median"] for m in MODELS], "{:.0f}"),
        ("Correct (of 100)", [sum(r["correct"] for r in a[m]) for m in MODELS], "{:d}"),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 3.6))
    colors = [OCHRE, GREEN, ACCENT]
    for ax, (title, vals, fmt) in zip(axes, panels):
        ax.bar(range(3), vals, color=colors, edgecolor=INK, lw=0.8, width=0.62)
        top = max(vals)
        for i, v in enumerate(vals):
            ax.text(i, v + top * 0.03, fmt.format(v), ha="center", fontsize=13)
        ax.set_ylim(0, top * 1.22)
        ax.set_title(title, fontsize=14)
        ax.set_xticks(range(3), SHORT, rotation=30, ha="right", rotation_mode="anchor")
        ax.set_yticks([])
        ax.spines[["top", "right", "left"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(HERE / "images" / "quantization_tradeoff.svg", metadata={"Date": None})


if __name__ == "__main__":
    concept_figure()
    matvec_figure()
    layout_figure()
    size_figure()
    error_figure()
    accuracy_figure()
    if (LAB / "speed.json").exists():
        speed_figure()
        speedup_figure()
        tradeoff_figure()
