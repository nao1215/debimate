"""Prompt Weighting のノートの図を作る。

concept_figure() は Python 標準ライブラリだけで SVG を手書きする（冒頭の図）。
result_figures() は lab/ の集計 JSON から matplotlib でグラフを描く。

使い方:
    uv run --with matplotlib python figures.py
"""
import json
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
IMAGES = HERE / "images"

INK, SUB = "#1f1f1f", "#666666"
BLUE, BLUE_PALE = "#7aa6c2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
RED = "#e15759"
NEUTRAL = "#f2f2f2"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"


def concept_figure():
    """左: 重みは空のプロンプトからの距離を伸ばす。右: 75 トークンずつ別々に読む。"""
    w, h = 960, 540
    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img"><title>'
        f'{escape("重みは空のプロンプトの埋め込みから語の埋め込みまでの差を伸ばす。長いプロンプトは 75 トークンずつ別々に読まれる")}'
        f'</title>',
        f'<style>text{{font-family:{FONT};fill:{INK}}} .sub{{fill:{SUB}}}</style>',
        f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
        '<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
        f'markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{INK}"/></marker>'
        '<marker id="ahs" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
        f'markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{SUB}"/></marker>'
        '</defs>',
    ]

    def text(x, y, s, size=26, anchor="middle", cls=""):
        c = f' class="{cls}"' if cls else ""
        p.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}"{c}>'
                 f'{escape(s)}</text>')

    # --- 左: 重み ---
    text(230, 52, "(word:w)", 30)
    # 重みが 1 を超える側（語の埋め込みを通り越す側。黄土）
    p.append('<clipPath id="lp"><rect x="20" y="75" width="450" height="420"/></clipPath>')
    p.append(f'<path d="M -10 20 L 470 580 L 890 220 L 410 -340 z" clip-path="url(#lp)" '
             f'fill="{OCHRE_PALE}" stroke="none"/>')
    p.append(f'<line x1="-10" y1="20" x2="470" y2="580" clip-path="url(#lp)" stroke="{OCHRE}" '
             f'stroke-width="2" stroke-dasharray="7 5"/>')
    text(395, 130, "w > 1", 26)
    ex, ey = 90, 420      # 空のプロンプト
    tx, ty = 230, 300     # 重み 1.0 の語
    p.append(f'<circle cx="{ex}" cy="{ey}" r="12" fill="{NEUTRAL}" stroke="{SUB}" stroke-width="2"/>')
    text(40, ey + 50, "empty prompt (w = 0)", 24, anchor="start", cls="sub")
    p.append(f'<line x1="{ex}" y1="{ey}" x2="{tx - 12}" y2="{ty + 10}" stroke="{INK}" '
             f'stroke-width="3" marker-end="url(#ah)"/>')
    for k, (lab, r) in enumerate([("1.3", 1.3), ("1.6", 1.6)]):
        x = ex + (tx - ex) * r
        y = ey + (ty - ey) * r
        p.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="11" fill="#ffffff" stroke="{OCHRE}" '
                 f'stroke-width="3"/>')
        text(x + 20, y + 8, lab, 26, anchor="start")
    x16, y16 = ex + (tx - ex) * 1.6, ey + (ty - ey) * 1.6
    p.append(f'<line x1="{tx}" y1="{ty}" x2="{x16:.0f}" y2="{y16:.0f}" stroke="{OCHRE}" '
             f'stroke-width="3" stroke-dasharray="8 6"/>')
    p.append(f'<circle cx="{tx}" cy="{ty}" r="13" fill="{BLUE_PALE}" stroke="{BLUE}" stroke-width="3"/>')
    text(tx - 22, ty + 8, "1.0", 26, anchor="end")

    # 区切り線
    p.append(f'<line x1="485" y1="40" x2="485" y2="500" stroke="#dddddd" stroke-width="2"/>')

    # --- 右: 77 トークンの区切り ---
    text(725, 52, "77 tokens per chunk", 30)

    def chunk(y, label, fill, stroke):
        p.append(f'<rect x="520" y="{y}" width="34" height="64" fill="{NEUTRAL}" stroke="{SUB}"/>')
        p.append(f'<rect x="554" y="{y}" width="300" height="64" fill="{fill}" stroke="{stroke}" '
                 f'stroke-width="2.5"/>')
        p.append(f'<rect x="854" y="{y}" width="34" height="64" fill="{NEUTRAL}" stroke="{SUB}"/>')
        for i in range(1, 15):
            x = 554 + i * 20
            p.append(f'<line x1="{x}" y1="{y + 8}" x2="{x}" y2="{y + 56}" stroke="{stroke}" '
                     f'stroke-width="1" opacity="0.6"/>')
        text(704, y + 42, label, 26)

    chunk(110, "tokens 1-75", BLUE_PALE, BLUE)
    chunk(250, "tokens 76-150", OCHRE_PALE, OCHRE)
    text(537, 100, "S", 24, cls="sub")
    text(871, 100, "E", 24, cls="sub")
    text(704, 218, "encoded separately", 24, cls="sub")
    # 2 つを横に連結して UNet へ
    p.append(f'<path d="M 704 174 L 704 196" stroke="{SUB}" stroke-width="2"/>')
    p.append(f'<rect x="560" y="380" width="290" height="64" rx="8" fill="#ffffff" '
             f'stroke="{INK}" stroke-width="2.5"/>')
    text(705, 422, "UNet (154 tokens)", 26)
    p.append(f'<line x1="704" y1="314" x2="704" y2="374" stroke="{INK}" stroke-width="3" '
             f'marker-end="url(#ah)"/>')
    p.append(f'<path d="M 530 174 C 470 260 480 360 554 405" fill="none" stroke="{INK}" '
             f'stroke-width="3" marker-end="url(#ah)"/>')
    text(705, 490, "pooled vector: chunk 1 only", 24, cls="sub")

    p.append("</svg>")
    (IMAGES / "prompt-weighting_concept.svg").write_text("\n".join(p) + "\n")


def result_figures():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({
        "font.size": 10, "axes.edgecolor": SUB, "axes.labelcolor": INK,
        "xtick.color": INK, "ytick.color": INK, "text.color": INK,
        "svg.fonttype": "path", "svg.hashsalt": "prompt-weighting",
        "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
    })
    lab = HERE / "lab"

    # 打ち消しの重みと個数ごとの、彩度の平均と赤い画素の割合
    neg = {r["name"]: r for r in json.loads((lab / "result_negative.json").read_text())}
    weights = [1.0, 1.2, 1.3, 1.5, 1.8]
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 4.2))
    # 線: (条件名の接頭辞, 凡例, 色, 線種, 印)
    lines = [("k1", "lowres only", SUB, ":", "s"),
             ("k12", "all 12 words", OCHRE, "-", "^")]
    if "mono_w1.3" in neg:
        lines += [("mono", "monochrome + greyscale only", INK, "-.", "D"),
                  ("k10", "the other 10 words", BLUE, "--", "o")]
    for key, ax, ylabel, scale in [("sat", axes[0], "Mean saturation (0-1)", 1),
                                   ("red", axes[1], "Red pixels (%)", 100)]:
        for prefix, label, color, ls, mk in lines:
            xs = [wt for wt in weights if wt == 1.0 or f"{prefix}_w{wt:.1f}" in neg]
            ys = [neg["w1.0" if wt == 1.0 else f"{prefix}_w{wt:.1f}"][key] * scale for wt in xs]
            ax.plot(xs, ys, color=color, ls=ls, marker=mk, lw=2, label=label)
        ax.set_xlabel("Weight of the negative words")
        ax.set_ylabel(ylabel)
        ax.set_xticks(weights)
        ax.spines[["top", "right"]].set_visible(False)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, frameon=False, fontsize=10, loc="lower center", ncol=2)
    fig.tight_layout(rect=(0, 0.13, 1, 1))
    fig.savefig(IMAGES / "prompt-weighting_negative.svg", metadata={"Date": None})
    plt.close(fig)


def lighting_figure():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rows = {r["name"]: r for r in json.loads((HERE / "lab" / "result_lighting.json").read_text())}
    weights = [1.0, 1.2, 1.3]
    lights = [("none", "no lighting word", SUB, ":", "s"),
              ("night", "night", INK, "-", "o"),
              ("neon_light", "neon light", BLUE, "-", "^"),
              ("sunset", "sunset", OCHRE, "-", "D"),
              ("dramatic_lighting", "dramatic lighting", BLUE, "--", "v")]
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 4.2))
    for key, ax, ylabel, scale in [("white", axes[0], "White pixels (%)", 100),
                                   ("sat", axes[1], "Mean saturation (0-1)", 1)]:
        for name, label, color, ls, mk in lights:
            ys = [rows[f"{name}_neg{w:.1f}"][key] * scale for w in weights]
            ax.plot(weights, ys, color=color, ls=ls, marker=mk, lw=2, label=label)
        ax.set_xlabel("Weight of all 12 negative words")
        ax.set_ylabel(ylabel)
        ax.set_xticks(weights)
        ax.spines[["top", "right"]].set_visible(False)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, frameon=False, fontsize=10, loc="lower center", ncol=3)
    fig.tight_layout(rect=(0, 0.13, 1, 1))
    fig.savefig(IMAGES / "prompt-weighting_lighting.svg", metadata={"Date": None})
    plt.close(fig)


def _plt():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "font.size": 11, "axes.edgecolor": SUB, "axes.labelcolor": INK,
        "xtick.color": INK, "ytick.color": INK, "text.color": INK,
        "svg.fonttype": "path", "svg.hashsalt": "prompt-weighting",
        "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
    })
    return plt


def positive_figure():
    """実験 1: 青いポットの重みと、青い画素・黄色い画素の割合（3 seed の平均）。"""
    plt = _plt()
    rows = json.loads((HERE / "lab" / "result_positive.json").read_text())
    xs = [float(r["name"][1:]) for r in rows]
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    ax.plot(xs, [r["blue"] * 100 for r in rows], color=BLUE, lw=2.2, marker="o",
            label="blue pixels (teapot, weighted)")
    ax.plot(xs, [r["yellow"] * 100 for r in rows], color=OCHRE, lw=2.2, marker="D",
            ls="--", label="yellow pixels (lemons, not weighted)")
    ax.set_xticks(xs)
    ax.set_xlabel("Weight of blue ceramic teapot")
    ax.set_ylabel("Pixels (%)")
    ax.set_ylim(0, 20)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, fontsize=10, loc="center right")
    fig.tight_layout()
    fig.savefig(IMAGES / "prompt-weighting_positive.svg", metadata={"Date": None})
    plt.close(fig)


def ablation_figure():
    """実験 4: 語を 1 つずつ外した時の、画素の差と赤・黄色の画素（2 seed の平均）。"""
    plt = _plt()
    rows = json.loads((HERE / "lab" / "result_ablation.json").read_text())
    names = [r["name"].replace("no_", "- ").replace("_", " ") for r in rows]
    ys = list(range(len(rows)))[::-1]
    panels = [("diff", "Pixel diff from full (0-255)", 1, None),
              ("red", "Red pixels (%)", 100, "no_red_apple"),
              ("yellow", "Yellow pixels (%)", 100, "no_lemons")]
    fig, axes = plt.subplots(1, 3, figsize=(7.6, 3.8), sharey=True)
    for ax, (key, label, scale, hit) in zip(axes, panels):
        colors = [OCHRE if r["name"] == hit else "#c8c8c8" for r in rows]
        ax.barh(ys, [r[key] * scale for r in rows], color=colors, height=0.66)
        ax.set_xlabel(label)
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].set_yticks(ys, names)
    fig.tight_layout()
    fig.savefig(IMAGES / "prompt-weighting_ablation.svg", metadata={"Date": None})
    plt.close(fig)


if __name__ == "__main__":
    concept_figure()
    if (HERE / "lab" / "result_negative.json").exists():
        result_figures()
    if (HERE / "lab" / "result_lighting.json").exists():
        lighting_figure()
    if (HERE / "lab" / "result_positive.json").exists():
        positive_figure()
    if (HERE / "lab" / "result_ablation.json").exists():
        ablation_figure()
