"""Generate the figures of the RAG note.

- images/rag_concept.svg : chunks become points; only the points near the question reach the LLM
- images/rag_recall.svg  : Recall@k by chunk size, from lab/output_recall.json
- images/rag_rank.svg    : rank of the first chunk holding the evidence, same file

Run: uv run --with matplotlib==3.10.7 python3 figures.py
"""

import json
import math
from html import escape
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
INK, SUB, FILL = "#1f1f1f", "#666666", "#f2f2f2"
BLUE, BLUE_PALE = "#7aa6c2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"

plt.rcParams.update({
    "font.size": 10, "axes.edgecolor": SUB, "axes.labelcolor": INK,
    "xtick.color": INK, "ytick.color": INK, "text.color": INK,
    "svg.fonttype": "path", "svg.hashsalt": "rag",
    "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
})


def concept_figure():
    """A note is cut into chunks, each chunk becomes a point, and the question picks its neighbours."""
    w, h = 960, 540
    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img"><title>'
        f'{escape("文書をチャンクに切ってベクトル空間の点にし、質問の点に近いチャンクだけを LLM に渡す")}'
        f'</title>',
        f'<style>text{{font-family:{FONT};fill:{INK}}} .sub{{fill:{SUB}}}</style>',
        f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
    ]

    def text(x, y, s, size=24, anchor="middle", cls=""):
        c = f' class="{cls}"' if cls else ""
        p.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}"{c}>'
                 f'{escape(s)}</text>')

    def arrow(x1, y1, x2, y2, color=INK, sw=3):
        ang = math.atan2(y2 - y1, x2 - x1)
        bx, by = x2 - 16 * math.cos(ang), y2 - 16 * math.sin(ang)
        p.append(f'<line x1="{x1}" y1="{y1}" x2="{bx:.1f}" y2="{by:.1f}" stroke="{color}" '
                 f'stroke-width="{sw}"/>')
        pts = [(x2, y2),
               (bx + 9 * math.sin(ang), by - 9 * math.cos(ang)),
               (bx - 9 * math.sin(ang), by + 9 * math.cos(ang))]
        p.append('<polygon points="' + " ".join(f"{a:.1f},{b:.1f}" for a, b in pts)
                 + f'" fill="{color}"/>')

    # Left: one note cut into four chunks (gaps are the cuts).
    text(125, 52, "文書", 26)
    for i in range(4):
        y = 76 + i * 104
        p.append(f'<rect x="45" y="{y}" width="160" height="88" rx="4" fill="#ffffff" '
                 f'stroke="{SUB}" stroke-width="2"/>')
        for j in range(4):
            lw = 120 if j < 3 else 70
            p.append(f'<line x1="62" y1="{y + 20 + j * 17}" x2="{62 + lw}" y2="{y + 20 + j * 17}" '
                     f'stroke="{SUB}" stroke-width="3"/>')
    text(125, 512, "チャンクに切る", 24, cls="sub")

    # Middle: embedding space. Each chunk of every note is one point.
    sx, sy, sw_, sh = 300, 40, 400, 400
    p.append(f'<rect x="{sx}" y="{sy}" width="{sw_}" height="{sh}" rx="10" fill="#ffffff" '
             f'stroke="{SUB}" stroke-width="1.5"/>')
    text(sx + sw_ / 2, 512, "埋め込みのベクトル空間", 24, cls="sub")
    arrow(214, 240, 290, 240)
    qx, qy, r = 520, 250, 78
    near = [(555, 195), (585, 262), (500, 310)]
    far = [(345, 110), (410, 170), (360, 215), (395, 330), (340, 400), (450, 395),
           (620, 120), (665, 185), (640, 380), (560, 410), (470, 125), (680, 300),
           (600, 345)]
    p.append(f'<circle cx="{qx}" cy="{qy}" r="{r + 14}" fill="{OCHRE_PALE}" stroke="{OCHRE}" '
             'stroke-width="2" stroke-dasharray="7 5"/>')
    for x, y in far:
        p.append(f'<circle cx="{x}" cy="{y}" r="11" fill="{FILL}" stroke="{SUB}" stroke-width="2"/>')
    for x, y in near:
        p.append(f'<circle cx="{x}" cy="{y}" r="13" fill="{BLUE}" stroke="{INK}" stroke-width="2"/>')
    # The question is a diamond so it never reads as a chunk.
    d = 16
    p.append(f'<polygon points="{qx},{qy - d} {qx + d},{qy} {qx},{qy + d} {qx - d},{qy}" '
             f'fill="{OCHRE}" stroke="{INK}" stroke-width="2"/>')
    text(qx, sy + 34, "質問の近く = 意味が近い", 24)
    text(qx - 26, qy + 9, "質問", 24, anchor="end")

    # Right: only the neighbours reach the LLM.
    lx, ly, lw, lh = 790, 190, 140, 110
    for x, y in near:
        arrow(x + 14, y, lx - 4, ly + lh / 2 + (y - qy) * 0.3, BLUE, 3)
    p.append(f'<rect x="{lx}" y="{ly}" width="{lw}" height="{lh}" rx="12" fill="{FILL}" '
             f'stroke="{INK}" stroke-width="2.5"/>')
    text(lx + lw / 2, ly + 66, "LLM", 32)
    arrow(lx + lw / 2, ly + lh + 6, lx + lw / 2, ly + lh + 80)
    text(lx + lw / 2, ly + lh + 112, "回答", 26)
    text(lx + lw / 2, ly - 34, "近い 3 個だけ", 24, cls="sub")
    (HERE / "images" / "rag_concept.svg").write_text("\n".join(p + ["</svg>"]) + "\n")


def recall_figure():
    data = json.load(open(HERE / "lab" / "output_recall.json"))
    order = ["200", "500", "1000", "2000", "section"]
    labels = {"200": "200 chars", "500": "500 chars", "1000": "1,000 chars",
              "2000": "2,000 chars", "section": "section (###)"}
    styles = {"200": (OCHRE, "-"), "500": (BLUE, "-"), "1000": (INK, "-"),
              "2000": (SUB, "--"), "section": (BLUE, ":")}
    fig, axes = plt.subplots(1, 2, figsize=(7.6, 3.8))
    ks = list(range(1, 21))
    for st in order:
        color, ls = styles[st]
        ev = [100 * v for v in data[st]["evidence"]]
        axes[0].plot(ks, ev, color=color, ls=ls, lw=2.0, label=labels[st])
        axes[1].plot(data[st]["chars"], ev, color=color, ls=ls, lw=2.0, label=labels[st])
    axes[0].set_xlabel("k (chunks passed to the LLM)")
    axes[0].set_ylabel("Recall@k: evidence in top k (%)")
    axes[0].set_xticks([1, 5, 10, 15, 20])
    axes[1].set_xlabel("Characters passed to the LLM (median)")
    axes[1].set_xscale("log")
    axes[1].set_xticks([200, 1000, 5000, 20000, 50000], ["200", "1k", "5k", "20k", "50k"])
    for ax in axes:
        ax.set_ylim(0, 103)
        ax.grid(axis="y", color="#e0e0e0", lw=0.8)
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].legend(loc="lower right", frameon=False, fontsize=10)
    fig.tight_layout()
    fig.savefig(HERE / "images" / "rag_recall.svg", metadata={"Date": None})


def rank_figure():
    """Rank of the first chunk holding the evidence, per question and chunking."""
    from matplotlib.patches import Patch, Rectangle

    data = json.load(open(HERE / "lab" / "output_recall.json"))
    order = ["200", "500", "1000", "2000", "section"]
    labels = {"200": "200", "500": "500", "1000": "1,000", "2000": "2,000",
              "section": "section"}
    n = len(data[order[0]]["first_evidence_rank"])
    bins = [(lambda r: r == 1, BLUE, "1st"), (lambda r: r <= 5, BLUE_PALE, "2nd-5th"),
            (lambda r: r <= 20, OCHRE_PALE, "6th-20th")]
    fig, ax = plt.subplots(figsize=(8.4, 3.1))
    for row, st in enumerate(order):
        for q, rank in enumerate(data[st]["first_evidence_rank"]):
            if rank is None:
                color, mark = "#ffffff", "-"
            else:
                color = next(c for test, c, _ in bins if test(rank))
                mark = str(rank)
            ax.add_patch(Rectangle((q, row), 1, 1, facecolor=color, edgecolor="#ffffff", lw=1.5))
            ax.text(q + 0.5, row + 0.52, mark, ha="center", va="center", fontsize=10,
                    color="#ffffff" if rank == 1 else INK)
    ax.set_xlim(0, n)
    ax.set_ylim(len(order), 0)
    ax.set_yticks([i + 0.5 for i in range(len(order))], [labels[s] for s in order])
    ax.set_xticks([i + 0.5 for i in range(0, n, 2)], [str(i + 1) for i in range(0, n, 2)],
                  fontsize=10)
    ax.set_xlabel("Question ID")
    ax.set_ylabel("Chunk")
    ax.tick_params(length=0)
    ax.spines[:].set_visible(False)
    handles = [Patch(facecolor=c, edgecolor=SUB, lw=0.5, label=l) for _, c, l in bins]
    handles.append(Patch(facecolor="#ffffff", edgecolor=SUB, lw=0.5, label="- not in top 20"))
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.26), ncol=4,
              frameon=False, fontsize=10)
    fig.tight_layout()
    fig.savefig(HERE / "images" / "rag_rank.svg", metadata={"Date": None})


if __name__ == "__main__":
    (HERE / "images").mkdir(exist_ok=True)
    concept_figure()
    if (HERE / "lab" / "output_recall.json").exists():
        recall_figure()
        rank_figure()
