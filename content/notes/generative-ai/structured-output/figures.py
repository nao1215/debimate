"""Generate the figures of the structured output note.

concept_figure() は lab/logprobs.json（lab/probe.py の出力）から、
results_figure() と timing_figure() は lab/summary.json（lab/evaluate.py の出力）から描く。
"""

import json
from html import escape
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
INK, SUB, ACCENT, RED = "#1f1f1f", "#666666", "#7aa6c2", "#e15759"
OCHRE, GREEN = "#d4a24c", "#8fae86"
plt.rcParams.update({
    "font.size": 10, "axes.edgecolor": SUB, "axes.labelcolor": INK,
    "xtick.color": INK, "ytick.color": INK, "text.color": INK,
    "svg.fonttype": "path", "svg.hashsalt": "structured-output",
    "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
})

MODELS = [("qwen3:1.7b-q4_K_M", "qwen3:1.7b"), ("qwen3:4b", "qwen3:4b"), ("qwen3:8b", "qwen3:8b")]
METHODS = [("prompt", "prompt\nonly"), ("json", 'format:\n"json"'), ("schema", "format:\nschema")]
BARE = ("schema_bare", "schema,\nno keys in\nprompt")


def load_summary():
    return json.loads((HERE / "lab" / "summary.json").read_text())


def results_figure():
    s = load_summary()
    fig, axes = plt.subplots(3, 1, figsize=(8.4, 9.0), sharey=True)
    stages = [("parse", "parses as JSON", ACCENT), ("schema", "matches schema", OCHRE),
              ("value", "all 3 values correct", GREEN)]
    for ax, (key, label) in zip(axes, MODELS):
        methods = METHODS + ([BARE] if BARE[0] in s[key] else [])
        for j, (m, _) in enumerate(methods):
            d = s[key][m]
            for k, (st, _, color) in enumerate(stages):
                v = 100 * d[st] / d["n"]
                x = j + (k - 1) * 0.27
                ax.bar(x, v, width=0.25, color=color, edgecolor=INK, linewidth=0.6)
                ax.text(x, v + 1.5, f"{v:.0f}", ha="center", fontsize=10, color=INK)
        ax.set_xticks(range(len(methods)), [m[1] for m in methods], fontsize=10)
        ax.set_title(f"{label} ({s[key]['prompt']['n']} inputs)", fontsize=11)
        ax.set_ylim(0, 112)
        ax.spines[["top", "right"]].set_visible(False)
    fig.supylabel("Share of inputs (%)", fontsize=11)
    handles = [plt.Rectangle((0, 0), 1, 1, color=c, ec=INK, lw=0.6) for _, _, c in stages]
    fig.legend(handles, [lb for _, lb, _ in stages], loc="upper center", ncol=3,
               frameon=False, fontsize=11, bbox_to_anchor=(0.5, 1.0))
    fig.tight_layout(rect=(0, 0, 1, 0.965))
    fig.savefig(HERE / "images" / "structured-output_results.svg", metadata={"Date": None})


def timing_figure():
    s = load_summary()
    key = MODELS[0][0]
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.0))
    names = [m[1] for m in METHODS]
    n_timed = s[key]["prompt"]["n_timed"]
    med = [s[key][m]["sec_median"] for m, _ in METHODS]
    lo = [med[i] - min(s[key][m]["sec_reps"]) for i, (m, _) in enumerate(METHODS)]
    hi = [max(s[key][m]["sec_reps"]) - med[i] for i, (m, _) in enumerate(METHODS)]
    axes[0].bar(range(3), med, color=ACCENT, edgecolor=INK, linewidth=0.6,
                yerr=[lo, hi], capsize=4, ecolor=SUB)
    axes[0].set_ylabel("Prompt + generation time\nper call, median (s)")
    tps = [s[key][m]["tok_per_s"] for m, _ in METHODS]
    axes[1].bar(range(3), tps, color=OCHRE, edgecolor=INK, linewidth=0.6)
    axes[1].set_ylabel("Generated tokens / s (median)")
    tops = (max(m + h for m, h in zip(med, hi)), max(tps))
    for ax, vals, fmt, top in ((axes[0], med, "{:.2f}", tops[0]), (axes[1], tps, "{:.1f}", tops[1])):
        ax.set_xticks(range(3), names, fontsize=10)
        for i, v in enumerate(vals):
            ax.text(i + 0.08, v + top * 0.02, fmt.format(v), ha="left", fontsize=10)
        ax.set_ylim(0, top * 1.15)
        ax.spines[["top", "right"]].set_visible(False)
    fig.suptitle(f"qwen3:1.7b, 3 runs x {n_timed} inputs "
                 "(lines on the left: min-max of the 3 run medians)", fontsize=10, color=SUB)
    fig.tight_layout()
    fig.savefig(HERE / "images" / "structured-output_timing.svg", metadata={"Date": None})


FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"
MONO = "'DejaVu Sans Mono','Menlo','Consolas',monospace"
FILL, PALE = "#f2f2f2", "#eaf1f5"


def concept_figure():
    """Candidate tokens: those the grammar rejects drop out, the rest stay where they were."""
    data = json.loads((HERE / "lab" / "logprobs.json").read_text())
    cands = data["candidates"][:7]   # 確率の高い順
    w, h = 960, 540
    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img"><title>'
        f'{escape("次のトークンの候補から、スキーマの文法に合わない候補が外され、残りから選ばれる")}'
        '</title>',
        f'<style>text{{font-family:{FONT};fill:{INK}}} .mono{{font-family:{MONO}}}</style>',
        f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
    ]

    def text(x, y, s, size=24, anchor="middle", color=INK, cls=""):
        c = f' class="{cls}"' if cls else ""
        p.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}"{c} '
                 f'style="fill:{color}">{escape(s)}</text>')

    # 1 行目: 応答の 1 トークン目の枠。選ばれた候補がここに入る
    text(40, 66, data["prefix_shown"], 24, "start", SUB)
    cursor_x = 300
    p.append(f'<rect x="{cursor_x}" y="34" width="80" height="44" rx="6" fill="{PALE}" '
             f'stroke="{INK}" stroke-width="2.5"/>')

    # 候補の帯: 左から確率の高い順。棒の高さが確率
    x0, slot, base, tall = 150, 112, 330, 200
    text(40, 160, "候補", 24, "start", SUB)
    text(40, 192, "(確率)", 24, "start", SUB)
    p.append(f'<line x1="{x0 - 20}" y1="{base}" x2="{x0 + slot * len(cands)}" y2="{base}" '
             f'stroke="{SUB}" stroke-width="1.5"/>')
    best = max((c for c in cands if c["allowed"]), key=lambda c: c["p"])
    for i, c in enumerate(cands):
        cx = x0 + slot * i + slot / 2
        bh = max(6, tall * c["p"] / cands[0]["p"])
        if c["allowed"]:
            chosen = c is best
            p.append(f'<rect x="{cx - 34}" y="{base - bh}" width="68" height="{bh}" '
                     f'fill="{ACCENT if chosen else PALE}" stroke="{INK if chosen else ACCENT}" '
                     f'stroke-width="{3 if chosen else 2}"/>')
            text(cx, base + 40, c["shown"], 26, cls="mono")
        else:
            # 外される候補: 帯から下へ落とし、枠だけの点線にする
            p.append(f'<rect x="{cx - 34}" y="{base - bh}" width="68" height="{bh}" '
                     f'fill="#ffffff" stroke="{SUB}" stroke-width="1.5" stroke-dasharray="6 4"/>')
            p.append(f'<rect x="{cx - 34}" y="{base + 92}" width="68" height="46" rx="6" '
                     f'fill="{FILL}" stroke="{SUB}" stroke-width="1.5"/>')
            text(cx, base + 124, c["shown"], 26, color=SUB, cls="mono")
            p.append(f'<line x1="{cx}" y1="{base + 8}" x2="{cx}" y2="{base + 84}" '
                     f'stroke="{SUB}" stroke-width="1.5" stroke-dasharray="4 4"/>')
            text(cx, base + 40, "", 26)
        text(cx, base - bh - 10, f'{100 * c["p"]:.0f}%' if c["p"] >= 0.005 else "<1%", 24,
             color=INK if c["allowed"] else SUB)
    text(40, base + 124, "外す", 24, "start", SUB)
    text(40, base + 40, "残す", 24, "start", SUB)

    # 選ばれた候補を 1 行目の枠へ
    bi = cands.index(best)
    bx = x0 + slot * bi + slot / 2
    text(cursor_x + 40, 66, best["shown"], 26, cls="mono")
    kept = sum(c["p"] for c in cands if c["allowed"])
    p.append(f'<path d="M{bx} {base - tall * best["p"] / cands[0]["p"] - 40} '
             f'C {bx} 150, {cursor_x + 40} 150, {cursor_x + 40} 96" fill="none" '
             f'stroke="{INK}" stroke-width="3"/>')
    p.append(f'<polygon points="{cursor_x + 40},82 {cursor_x + 30},100 {cursor_x + 50},100" '
             f'fill="{INK}"/>')
    text(cursor_x + 110, 66, f"残りの中では {100 * best['p'] / kept:.0f}%", 24, "start", SUB)
    text(w - 30, h - 24, data["caption"], 24, "end", SUB)
    (HERE / "images" / "structured-output_concept.svg").write_text("\n".join(p + ["</svg>"]) + "\n")


if __name__ == "__main__":
    results_figure()
    timing_figure()
    concept_figure()
