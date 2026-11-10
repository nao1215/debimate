"""Generate the figures of the LoRA note.

The charts read lab/params.json (lab/count_params.py) and
lab/pixel_change_*.json (lab/to_webp.py) and lab/seed_baseline.json
(lab/seed_baseline.py), so neither the model files nor
ComfyUI are needed to redraw the figures.

    python3 figures.py
"""

import json
from html import escape
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
INK, SUB, ACCENT, RED = "#1f1f1f", "#666666", "#7aa6c2", "#e15759"
FILL, PALE = "#f2f2f2", "#eaf1f5"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"
plt.rcParams.update({
    "font.size": 10, "axes.edgecolor": SUB, "axes.labelcolor": INK,
    "xtick.color": INK, "ytick.color": INK, "text.color": INK,
    "svg.fonttype": "path", "svg.hashsalt": "lora",
    "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
})


def concept_figure():
    """W (d x d) next to B (d x r) and A (r x d) drawn at true scale (d=1280, r=32)."""
    w, h = 960, 540
    d, r = 1280, 32
    side = 320                      # pixels for d
    thin = max(side * r / d, 8)     # 8 px; true scale would be 8 px as well
    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img"><title>'
        f'{escape("凍結した W と同じ大きさの差分を細長い B と A の積で作る")}</title>',
        f'<style>text{{font-family:{FONT};fill:{INK}}} .sub{{fill:{SUB}}}</style>',
        f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
    ]

    def text(x, y, s, size=26, anchor="middle", weight="normal", cls=""):
        c = f' class="{cls}"' if cls else ""
        p.append(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
                 f'text-anchor="{anchor}"{c}>{escape(s)}</text>')

    top = 100
    text(480, 56, "W' = W + (α/r)·BA", 34, weight="normal")

    # Frozen base weight W.
    wx = 70
    p.append(f'<rect x="{wx}" y="{top}" width="{side}" height="{side}" fill="{FILL}" '
             f'stroke="{SUB}" stroke-width="2"/>')
    text(wx + side / 2, top + side / 2 - 6, "W", 64, weight="normal")
    text(wx + side / 2, top + side / 2 + 40, f"{d} × {d}", 26, cls="sub")
    text(wx + side / 2, top + side + 50, "凍結（学習しない）", 26)
    text(wx + side / 2, top + side + 86, f"{d * d:,} 個", 26, cls="sub")

    text(445, top + side / 2 + 14, "+", 56)

    # B (d x r) on the left edge, A (r x d) on the top edge, BA fills the square.
    bx = 520
    ax0 = bx + thin + 6
    ay = top - thin - 6
    p.append(f'<rect x="{ax0}" y="{top}" width="{side}" height="{side}" fill="{PALE}" '
             f'stroke="{ACCENT}" stroke-width="2" stroke-dasharray="8 6"/>')
    text(ax0 + side / 2, top + side / 2 - 6, "ΔW = BA", 40, weight="normal")
    text(ax0 + side / 2, top + side / 2 + 40, f"{d} × {d}（保存しない）", 24, cls="sub")
    p.append(f'<rect x="{bx}" y="{top}" width="{thin}" height="{side}" fill="{ACCENT}" '
             f'stroke="{INK}" stroke-width="1.5"/>')
    p.append(f'<rect x="{ax0}" y="{ay}" width="{side}" height="{thin}" fill="{ACCENT}" '
             f'stroke="{INK}" stroke-width="1.5"/>')
    text(bx - 14, top + side / 2 + 10, "B", 32, "end", weight="normal")
    text(ax0 + side + 14, ay + 12, "A", 32, "start", weight="normal")
    text(ax0 + side / 2, top + side + 50, f"学習するのは B と A（r = {r}）", 26)
    lora = r * (d + d)
    text(ax0 + side / 2, top + side + 86,
         f"{lora:,} 個（W の {100 * lora / (d * d):.0f}%）", 26, cls="sub")
    (HERE / "images" / "lora_concept.svg").write_text("\n".join(p + ["</svg>"]) + "\n")


def params_figure():
    s = json.loads((HERE / "lab" / "params.json").read_text())
    g = s["base_groups"]
    te = g["Text encoder 1 (CLIP ViT-L)"] + g["Text encoder 2 (OpenCLIP ViT-bigG)"]
    rows = [
        ("Base: UNet", g["UNet"], FILL),
        ("Base: text encoders (2)", te, FILL),
        (f"Base: W of the {s['target_layers']} target layers", s["target_full_params"],
         FILL),
        (f"LoRA: B and A (r = {s['rank'][0]})", s["lora_params"], ACCENT),
    ]
    fig, ax = plt.subplots(figsize=(7.2, 2.9))
    y = list(range(len(rows)))[::-1]
    vals = [v / 1e6 for _, v, _ in rows]
    ax.barh(y, vals, color=[c for _, _, c in rows], edgecolor=SUB, height=0.6)
    ratio = s["lora_params"] / g["UNet"]
    for i, (yi, v) in enumerate(zip(y, vals)):
        note = f"  ({ratio:.2%} of UNet)" if i == len(rows) - 1 else ""
        ax.text(v + 30, yi, f"{v:,.1f} M{note}", va="center", fontsize=9)
    ax.set_yticks(y, [n for n, _, _ in rows])
    ax.set_xlim(0, 3100)
    ax.set_xlabel("Parameters (millions)")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(HERE / "images" / "lora_params.svg", metadata={"Date": None})


def change_figure():
    """Mean pixel difference from the weight-0 image, per sampler.

    The grey band is the range of the same metric between unrelated images
    (weight 0, different seeds), i.e. what "a different picture" scores.
    """
    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    base = json.loads((HERE / "lab" / "seed_baseline.json").read_text())
    ax.axhspan(base["min"], base["max"], color=FILL, zorder=0)
    ax.text(0.02, base["max"] + 1.5,
            f"unrelated images (other seeds): {base['min']:.1f}-{base['max']:.1f}",
            fontsize=10, color=SUB, va="bottom")
    # (tag, label, color, line style, label offset): ancestral labels above left, euler below right
    series = [("ancestral", "euler_ancestral", RED, "-", 2.5),
              ("euler", "euler", ACCENT, "--", -4.0)]
    top = 0
    for tag, label, color, ls, dy in series:
        rows = json.loads((HERE / "lab" / f"pixel_change_{tag}.json").read_text())
        x = [r["weight"] for r in rows]
        y = [r["mad_vs_0"] for r in rows]
        top = max(top, *y)
        ax.plot(x, y, color=color, lw=2.0, ls=ls, marker="o", label=label)
        for xi, yi in zip(x[1:], y[1:]):
            ax.text(xi + (0.03 if dy < 0 else -0.03), yi + dy, f"{yi:.1f}",
                    ha="left" if dy < 0 else "right", fontsize=10, color=color,
                    va="bottom" if dy > 0 else "top")
    ax.set_xticks(x)
    ax.set_xlabel("LoRA strength (weight)")
    ax.set_ylabel("Mean abs. pixel diff\nfrom weight 0 (0-255)")
    ax.set_xlim(-0.05, 1.08)
    ax.set_ylim(0, max(top, base["max"]) * 1.2)
    ax.legend(loc="lower right", frameon=False, fontsize=10)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(HERE / "images" / "lora_pixel_change.svg", metadata={"Date": None})


if __name__ == "__main__":
    concept_figure()
    params_figure()
    change_figure()
