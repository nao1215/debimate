"""Generate the figures of the attribute binding note.

The concept figure is hand-written SVG (standard library only). The charts read
lab/clip_mix.json (lab/clip_mix.py) and lab/measure.json (lab/measure.py), so
neither the model files nor ComfyUI are needed to redraw them.

    python3 figures.py            # needs matplotlib for the charts
"""

import json
import sys
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
INK, SUB, BLUE, RED = "#1f1f1f", "#666666", "#7aa6c2", "#e15759"
BLUE_PALE, OCHRE, OCHRE_PALE, FILL = "#eaf1f5", "#d4a24c", "#f8eed8", "#f2f2f2"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"


def concept_figure():
    """Tokens on the left, a portrait on the right; 'aqua' paints the eyes and leaks into the hair."""
    w, h = 960, 540
    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img"><title>'
        f'{escape("aqua の語が目だけでなく髪の一部にも色を付ける")}</title>',
        f'<style>text{{font-family:{FONT};fill:{INK}}} .sub{{fill:{SUB}}}</style>',
        '<defs>'
        f'<marker id="ab" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" '
        f'markerHeight="8" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{BLUE}"/></marker>'
        f'<marker id="ao" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" '
        f'markerHeight="8" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{OCHRE}"/></marker>'
        f'<marker id="ag" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" '
        f'markerHeight="8" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{SUB}"/></marker>'
        '</defs>',
        f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
    ]

    def text(x, y, s, size=26, anchor="middle", weight="normal", cls=""):
        c = f' class="{cls}"' if cls else ""
        p.append(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
                 f'text-anchor="{anchor}"{c}>{escape(s)}</text>')

    # Prompt tokens, top to bottom in prompt order.
    text(170, 62, "prompt", 28, cls="sub")
    tokens = [("black", FILL, SUB), ("hair", FILL, SUB),
              ("aqua", BLUE_PALE, BLUE), ("eyes", FILL, SUB)]
    ys = {}
    for i, (t, fill, stroke) in enumerate(tokens):
        y = 100 + i * 100
        ys[t] = y + 34
        sw = 3 if t == "aqua" else 2
        p.append(f'<rect x="70" y="{y}" width="200" height="68" rx="10" fill="{fill}" '
                 f'stroke="{stroke}" stroke-width="{sw}"/>')
        text(170, y + 45, t, 32 if len(t) < 8 else 28)

    # Portrait: hair behind, face, eyes. Coordinates of the right half.
    cx, cy = 700, 290
    text(cx, 62, "image", 28, cls="sub")
    p.append(f'<path d="M{cx-150},{cy+190} C{cx-190},{cy-40} {cx-150},{cy-200} {cx},{cy-205} '
             f'C{cx+150},{cy-200} {cx+190},{cy-40} {cx+150},{cy+190} Z" '
             f'fill="{FILL}" stroke="{SUB}" stroke-width="2"/>')
    # Leaked streak in the hair (ochre = the area that should not have the colour).
    p.append(f'<path d="M{cx+112},{cy-60} C{cx+140},{cy+20} {cx+145},{cy+110} {cx+138},{cy+185} '
             f'L{cx+100},{cy+185} C{cx+108},{cy+110} {cx+100},{cy+20} {cx+86},{cy-40} Z" '
             f'fill="{OCHRE_PALE}" stroke="{OCHRE}" stroke-width="3"/>')
    p.append(f'<ellipse cx="{cx}" cy="{cy+10}" rx="92" ry="118" fill="#ffffff" '
             f'stroke="{SUB}" stroke-width="2"/>')
    for ex in (cx - 38, cx + 38):
        p.append(f'<ellipse cx="{ex}" cy="{cy+5}" rx="20" ry="26" fill="{BLUE_PALE}" '
                 f'stroke="{BLUE}" stroke-width="3"/>')
    # Bangs over the forehead.
    p.append(f'<path d="M{cx-95},{cy-30} C{cx-80},{cy-140} {cx+80},{cy-140} {cx+95},{cy-30} '
             f'C{cx+40},{cy-70} {cx-40},{cy-70} {cx-95},{cy-30} Z" fill="{FILL}" '
             f'stroke="{SUB}" stroke-width="2"/>')

    # Arrows: black/hair -> hair (gray), aqua -> eyes (blue), aqua -> hair streak (ochre, dashed).
    p.append(f'<path d="M272,{ys["hair"]} C380,{ys["hair"]} 470,140 {cx-120},170" fill="none" '
             f'stroke="{SUB}" stroke-width="2.5" marker-end="url(#ag)"/>')
    p.append(f'<path d="M272,{ys["aqua"]} C400,{ys["aqua"]} 520,{cy+5} {cx-62},{cy+5}" '
             f'fill="none" stroke="{BLUE}" stroke-width="4" marker-end="url(#ab)"/>')
    p.append(f'<path d="M272,{ys["aqua"]+8} C420,{ys["aqua"]+150} 640,470 {cx+110},{cy+160}" '
             f'fill="none" stroke="{OCHRE}" stroke-width="4" stroke-dasharray="10 7" '
             f'marker-end="url(#ao)"/>')
    # The single failure mark.
    mx, my = 520, 452
    p.append(f'<circle cx="{mx}" cy="{my}" r="22" fill="#fbe3e3" stroke="{RED}" stroke-width="3"/>')
    p.append(f'<path d="M{mx-10},{my-10} L{mx+10},{my+10} M{mx+10},{my-10} L{mx-10},{my+10}" '
             f'stroke="{RED}" stroke-width="4"/>')
    text(cx + 175, cy + 225, "aqua が髪にも", 26, anchor="end")

    p.append("</svg>")
    (HERE / "images" / "attribute-binding_concept.svg").write_text("\n".join(p) + "\n")


def charts():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "font.size": 10, "axes.edgecolor": SUB, "axes.labelcolor": INK,
        "xtick.color": INK, "ytick.color": INK, "text.color": INK,
        "svg.fonttype": "path", "svg.hashsalt": "attribute-binding",
        "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
    })
    token_chart(plt)
    hair_chart(plt)
    people_chart(plt)


def people_chart(plt):
    """Images with two or more people per resolution (eye labels, seeds 1000-1005 of each prompt)."""
    labels = json.loads((HERE / "lab" / "labels.json").read_text())
    sets = [("768 x 1344", "s_eye_none", "s_rep_none"),
            ("832 x 1216", "s_ar_832x1216", "s_rep_ar_832x1216"),
            ("1024 x 1024", "s_ar_1024x1024", "s_rep_ar_1024x1024")]

    def count(cond):
        return sum(labels[f"{cond}/{s}"].get("multi", False) for s in range(1000, 1006))

    fig, ax = plt.subplots(figsize=(6.0, 3.2))
    x = list(range(len(sets)))
    a = [count(c1) for _, c1, _ in sets]
    b = [count(c2) for _, _, c2 in sets]
    ax.bar([i - 0.18 for i in x], a, 0.36, color=BLUE, label="standing prompt")
    ax.bar([i + 0.18 for i in x], b, 0.36, color=OCHRE, label="+ eye / single-color hair words")
    for i in x:
        ax.text(i - 0.18, a[i] + 0.08, str(a[i]), ha="center", fontsize=10)
        ax.text(i + 0.18, b[i] + 0.08, str(b[i]), ha="center", fontsize=10)
    ax.set_xticks(x, [n for n, _, _ in sets])
    ax.set_ylabel("Images with 2+ people\n(out of 6)")
    ax.set_ylim(0, 6)
    ax.legend(frameon=False, fontsize=10, loc="upper right")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(HERE / "images" / "attribute-binding_people.svg", metadata={"Date": None})


def hair_chart(plt):
    """Share of aqua pixels in the hair region, one dot per image (base model, 12 seeds each)."""
    rows = json.loads((HERE / "lab" / "measure.json").read_text())
    conds = [("eye_none", "black hair\n(control)"), ("eye_aqua", "black hair,\naqua eyes"),
             ("eye_aqua_rev", "aqua eyes,\nblack hair"), ("eye_aqua_concat", "split +\nConcat")]
    fig, ax = plt.subplots(figsize=(6.4, 3.2))
    for i, (c, label) in enumerate(conds):
        v = sorted(100 * r["hair_aqua"] for r in rows if r["cond"] == c)
        xs = [i + (j - (len(v) - 1) / 2) * 0.03 for j in range(len(v))]
        ax.scatter(xs, v, s=22, color=SUB if c == "eye_none" else BLUE, zorder=3)
        ax.hlines(sum(v) / len(v), i - 0.25, i + 0.25, color=INK, lw=1.5, zorder=4)
    ax.axhline(0.5, color=OCHRE, lw=1.2, ls="--")
    ax.text(0.3, 0.9, "threshold 0.5%", color=SUB, fontsize=10, ha="left")
    ax.set_xticks(range(len(conds)), [l for _, l in conds], fontsize=10)
    ax.set_ylabel("Aqua pixels in hair (%)")
    ax.set_xlim(-0.5, 3.5)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(HERE / "images" / "attribute-binding_hair_share.svg", metadata={"Date": None})


def token_chart(plt):
    """Per-token change when only the eye colour word changes, in two word orders."""
    data = json.loads((HERE / "lab" / "clip_mix.json").read_text())
    fig, axes = plt.subplots(1, 3, figsize=(8.5, 4.1), sharey=True)
    titles = {"eyes_last": "black hair, aqua eyes\n(aqua -> brown)",
              "eyes_first": "aqua eyes, black hair\n(aqua -> brown)",
              "hair_self": "brown eyes, aqua hair\n(aqua -> black)"}
    for ax, key in zip(axes, ("eyes_last", "eyes_first", "hair_self")):
        d = data[key]
        toks = [t.replace("</w>", "").replace("<|startoftext|>", "BOS")
                .replace("<|endoftext|>", "EOS") for t in d["tokens"]]
        x = list(range(len(toks)))
        ax.bar([i - 0.2 for i in x], [max(v, 0) for v in d["clip_l"]], 0.4,
               color=BLUE, label="CLIP ViT-L")
        ax.bar([i + 0.2 for i in x], [max(v, 0) for v in d["bigg"]], 0.4,
               color=OCHRE, label="OpenCLIP ViT-bigG")
        ax.set_xticks(x, toks, rotation=60, fontsize=10)
        ax.set_title(f"1girl, {titles[key]}", fontsize=10)
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].set_ylabel("Change of the token output\n(1 - cosine similarity)")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, frameon=False, fontsize=10, loc="upper center", ncol=2)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(HERE / "images" / "attribute-binding_tokens.svg", metadata={"Date": None})


if __name__ == "__main__":
    concept_figure()
    if "--concept-only" not in sys.argv:
        charts()
