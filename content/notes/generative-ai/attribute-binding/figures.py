"""Generate the figures of the attribute binding note.

The concept figure is hand-written SVG, rendered to PNG by headless Chrome and
saved as WebP (Pillow). The charts read
lab/clip_mix.json (lab/clip_mix.py) and lab/measure.json (lab/measure.py), so
neither the model files nor ComfyUI are needed to redraw them.

    python3 figures.py            # needs matplotlib for the charts
"""

import json
import subprocess
import sys
import tempfile
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
INK, SUB, BLUE, RED = "#1f1f1f", "#666666", "#7aa6c2", "#e15759"
BLUE_PALE, OCHRE, OCHRE_PALE, FILL = "#eaf1f5", "#d4a24c", "#f8eed8", "#f2f2f2"
FONT = "'Noto Sans CJK JP','Hiragino Sans','Yu Gothic',sans-serif"
IMAGES = HERE / "images"


def png_to_webp(png, name):
    """PNG を WebP にして images/ に置く。"""
    from PIL import Image
    Image.open(png).convert("RGB").save(IMAGES / name, "WEBP", quality=90, method=6)


def svg_to_webp(svg_text, w, h, name):
    """手書きの SVG を Chrome で 2 倍の解像度に描き、WebP にする。"""
    with tempfile.TemporaryDirectory() as tmp:
        svg, png = Path(tmp) / "fig.svg", Path(tmp) / "fig.png"
        svg.write_text(svg_text, encoding="utf-8")
        subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--hide-scrollbars",
                        "--force-device-scale-factor=2", f"--window-size={w},{h}",
                        f"--screenshot={png}", svg.as_uri()], check=True, capture_output=True)
        png_to_webp(png, name)


def save_webp(fig, name):
    """matplotlib の図を 200 dpi の PNG にしてから WebP にする。"""
    with tempfile.TemporaryDirectory() as tmp:
        png = Path(tmp) / "fig.png"
        fig.savefig(png, dpi=200, facecolor="#ffffff")
        png_to_webp(png, name)


def concept_figure():
    """The two places where a colour word can reach another object.

    Left: prompt tokens. Middle: the text encoder, where each output is built from
    the token itself and the tokens before it. Right: cross-attention, where each
    image position chooses which outputs to use; the hair position also uses 'aqua'.
    """
    w, h = 1100, 540
    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img"><title>'
        f'{escape("色の語が別の物に届く 2 か所")}</title>',
        f'<style>text{{font-family:{FONT};fill:{INK}}} .sub{{fill:{SUB}}}</style>',
        '<defs>'
        f'<marker id="ab" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
        f'markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{BLUE}"/></marker>'
        f'<marker id="ao" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
        f'markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{OCHRE}"/></marker>'
        '</defs>',
        f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
    ]

    def text(x, y, s, size=20, anchor="middle", cls=""):
        c = f' class="{cls}"' if cls else ""
        p.append(f'<text x="{x}" y="{y}" font-size="{size}" '
                 f'text-anchor="{anchor}"{c}>{escape(s)}</text>')

    words = ["black", "hair", "aqua", "eyes"]
    ys = [130 + i * 82 for i in range(4)]          # top of each box
    bh = 54

    # Column A: prompt tokens.
    text(120, 40, "プロンプトの", 20, cls="sub")
    text(120, 66, "トークン", 20, cls="sub")
    for wd, y in zip(words, ys):
        hl = wd == "aqua"
        p.append(f'<rect x="50" y="{y}" width="140" height="{bh}" rx="8" '
                 f'fill="{BLUE_PALE if hl else FILL}" stroke="{BLUE if hl else SUB}" '
                 f'stroke-width="{3 if hl else 1.5}"/>')
        text(120, y + 35, wd, 24)

    # Column B: text encoder outputs. Lines from token i to output j (j >= i).
    bx = 330
    p.append(f'<rect x="{bx - 30}" y="80" width="260" height="{ys[-1] + bh + 30 - 80}" rx="12" '
             f'fill="none" stroke="{SUB}" stroke-width="1.5" stroke-dasharray="6 5"/>')
    text(bx + 100, 40, "① プロンプトを読む", 20)
    text(bx + 100, 66, "（text encoder）", 18, cls="sub")
    for i, yi in enumerate(ys):
        for j, yj in enumerate(ys):
            if j < i:
                continue
            col, sw = (BLUE, 3) if (words[i] == "aqua" and j >= i) else ("#bdbdbd", 1.5)
            p.append(f'<path d="M190,{yi + bh / 2} C250,{yi + bh / 2} 260,{yj + bh / 2} '
                     f'{bx},{yj + bh / 2}" fill="none" stroke="{col}" stroke-width="{sw}"/>')
    for wd, y in zip(words, ys):
        p.append(f'<rect x="{bx}" y="{y}" width="200" height="{bh}" rx="8" fill="{FILL}" '
                 f'stroke="{SUB}" stroke-width="1.5"/>')
        text(bx + 100, y + 35, f"{wd} の出力", 20)
    text(bx + 100, ys[-1] + bh + 58, "前の語だけが後ろの出力に混ざる", 18, cls="sub")

    # Column C: the image. Hair, face, eyes.
    cx, cy = 880, 280
    text(cx, 40, "② 画像の各位置が出力を選ぶ", 20)
    text(cx, 66, "（cross-attention）", 18, cls="sub")
    p.append(f'<path d="M{cx-120},{cy+150} C{cx-150},{cy-30} {cx-120},{cy-160} {cx},{cy-165} '
             f'C{cx+120},{cy-160} {cx+150},{cy-30} {cx+120},{cy+150} Z" '
             f'fill="{FILL}" stroke="{SUB}" stroke-width="2"/>')
    p.append(f'<path d="M{cx+90},{cy-50} C{cx+112},{cy+15} {cx+116},{cy+90} {cx+110},{cy+148} '
             f'L{cx+80},{cy+148} C{cx+86},{cy+90} {cx+80},{cy+15} {cx+68},{cy-32} Z" '
             f'fill="{OCHRE_PALE}" stroke="{OCHRE}" stroke-width="3"/>')
    p.append(f'<ellipse cx="{cx}" cy="{cy+8}" rx="74" ry="95" fill="#ffffff" '
             f'stroke="{SUB}" stroke-width="2"/>')
    for ex in (cx - 30, cx + 30):
        p.append(f'<ellipse cx="{ex}" cy="{cy+4}" rx="16" ry="21" fill="{BLUE_PALE}" '
                 f'stroke="{BLUE}" stroke-width="3"/>')
    p.append(f'<path d="M{cx-76},{cy-24} C{cx-64},{cy-112} {cx+64},{cy-112} {cx+76},{cy-24} '
             f'C{cx+32},{cy-56} {cx-32},{cy-56} {cx-76},{cy-24} Z" fill="{FILL}" '
             f'stroke="{SUB}" stroke-width="2"/>')

    # From the 'aqua' output: to the eyes, and (wrongly) to the hair streak.
    oy = ys[2] + bh / 2
    p.append(f'<path d="M{bx + 200},{oy} C640,{oy} 700,{cy+4} {cx-48},{cy+4}" '
             f'fill="none" stroke="{BLUE}" stroke-width="4" marker-end="url(#ab)"/>')
    p.append(f'<path d="M{bx + 200},{oy + 12} C640,{oy + 170} 900,{h - 30} {cx+95},{cy+152}" '
             f'fill="none" stroke="{OCHRE}" stroke-width="4" stroke-dasharray="10 7" '
             f'marker-end="url(#ao)"/>')
    text(cx + 170, h - 24, "髪の位置も aqua の出力を使う（色移り）", 18, anchor="end")

    p.append("</svg>")
    svg_to_webp("\n".join(p) + "\n", w, h, "attribute-binding_concept.webp")


def charts():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "font.size": 10, "axes.edgecolor": SUB, "axes.labelcolor": INK,
        "xtick.color": INK, "ytick.color": INK, "text.color": INK,
        "font.family": "Noto Sans CJK JP",
        "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
    })
    token_chart(plt)
    hair_chart(plt)
    people_chart(plt)


def people_chart(plt):
    """Images with two or more people per resolution (eye labels, seeds 1000-1005 of each prompt)."""
    labels = json.loads((HERE / "lab" / "labels.json").read_text())
    sets = [("768 × 1344", "s_eye_none", "s_rep_none"),
            ("832 × 1216", "s_ar_832x1216", "s_rep_ar_832x1216"),
            ("1024 × 1024", "s_ar_1024x1024", "s_rep_ar_1024x1024")]

    def count(cond):
        return sum(labels[f"{cond}/{s}"].get("multi", False) for s in range(1000, 1006))

    fig, ax = plt.subplots(figsize=(6.0, 3.2))
    x = list(range(len(sets)))
    a = [count(c1) for _, c1, _ in sets]
    b = [count(c2) for _, _, c2 in sets]
    ax.bar([i - 0.18 for i in x], a, 0.36, color=BLUE, label="立ち絵のプロンプト")
    ax.bar([i + 0.18 for i in x], b, 0.36, color=OCHRE, label="髪を抑えたプロンプト")
    for i in x:
        ax.text(i - 0.18, a[i] + 0.08, str(a[i]), ha="center", fontsize=10)
        ax.text(i + 0.18, b[i] + 0.08, str(b[i]), ha="center", fontsize=10)
    ax.set_xticks(x, [n for n, _, _ in sets])
    ax.set_ylabel("2 人以上が描かれた枚数\n（6 枚中）")
    ax.set_ylim(0, 6)
    ax.legend(frameon=False, fontsize=10, loc="upper right")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    save_webp(fig, "attribute-binding_people.webp")


def hair_chart(plt):
    """Share of aqua pixels in the hair region, one dot per image (base model, 12 seeds each)."""
    rows = json.loads((HERE / "lab" / "measure.json").read_text())
    conds = [("eye_none", "black hair\n（対照）"), ("eye_aqua", "black hair,\naqua eyes"),
             ("eye_aqua_rev", "aqua eyes,\nblack hair"), ("eye_aqua_concat", "2 つに分けて\n通す")]
    fig, ax = plt.subplots(figsize=(6.4, 3.2))
    for i, (c, label) in enumerate(conds):
        v = sorted(100 * r["hair_aqua"] for r in rows if r["cond"] == c)
        xs = [i + (j - (len(v) - 1) / 2) * 0.03 for j in range(len(v))]
        ax.scatter(xs, v, s=22, color=SUB if c == "eye_none" else BLUE, zorder=3)
        ax.hlines(sum(v) / len(v), i - 0.25, i + 0.25, color=INK, lw=1.5, zorder=4)
    ax.axhline(0.5, color=OCHRE, lw=1.2, ls="--")
    ax.text(0.3, 0.9, "判定の線 0.5%", color=SUB, fontsize=10, ha="left")
    ax.set_xticks(range(len(conds)), [l for _, l in conds], fontsize=10)
    ax.set_ylabel("髪に占める青緑の画素（%）")
    ax.set_xlim(-0.5, 3.5)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    save_webp(fig, "attribute-binding_hair_share.webp")


def token_chart(plt):
    """Per-token change when only the eye colour word changes, in two word orders."""
    data = json.loads((HERE / "lab" / "clip_mix.json").read_text())
    fig, axes = plt.subplots(1, 3, figsize=(8.5, 4.1), sharey=True)
    titles = {"eyes_last": "black hair, aqua eyes\n（目の aqua → brown）",
              "eyes_first": "aqua eyes, black hair\n（目の aqua → brown）",
              "hair_self": "brown eyes, aqua hair\n（基準: 髪の aqua → black）"}
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
    axes[0].set_ylabel("トークンの出力の差\n（1 − コサイン類似度）")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, frameon=False, fontsize=10, loc="upper center", ncol=2)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    save_webp(fig, "attribute-binding_tokens.webp")


if __name__ == "__main__":
    concept_figure()
    if "--concept-only" not in sys.argv:
        charts()
