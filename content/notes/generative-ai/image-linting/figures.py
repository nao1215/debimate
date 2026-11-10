"""Generate the figures of the Image Linting note.

The cover and the color-check figures are hand-written SVG (standard library only).
The result charts read lab/result.json (lab/evaluate.py), so neither the
models nor ComfyUI are needed to redraw them.

    python3 figures.py            # cover and the color-check figure only
    python3 figures.py --results  # cover and the result charts (needs matplotlib)
"""

import json
import sys
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "images"
INK, SUB = "#1f1f1f", "#666666"
BLUE, BLUE_BG = "#7aa6c2", "#eaf1f5"
OCHRE, OCHRE_BG = "#d4a24c", "#f8eed8"
RED, RED_BG = "#e15759", "#fbe3e3"
GREY_BG = "#f2f2f2"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"


def cover_figure():
    """Good images shrink by 5% at each of five checks in series: 100% -> 77%."""
    w, h = 960, 540
    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img"><title>'
        f'{escape("正しい絵を 5% ずつ落とす検査を 5 段重ねると、正しい絵の 77% しか残らない")}'
        f'</title>',
        f'<style>text{{font-family:{FONT};fill:{INK}}} .sub{{fill:{SUB}}}</style>',
        f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
    ]

    def text(x, y, s, size=26, anchor="middle", weight="normal", cls=""):
        c = f' class="{cls}"' if cls else ""
        p.append(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
                 f'text-anchor="{anchor}"{c}>{escape(s)}</text>')

    text(480, 52, "検査ごとに正しい絵を 5% 落とすと", 30, weight="normal")

    base, full = 410, 300            # bottom of the bars, height of 100%
    bw, gap = 86, 66
    x0 = 70
    for i in range(6):
        rate = 0.95 ** i
        x = x0 + i * (bw + gap)
        hh = full * rate
        lost = full - hh
        # remaining good images (blue) and the good images thrown away so far (ochre)
        if lost > 0:
            p.append(f'<rect x="{x}" y="{base - full}" width="{bw}" height="{lost}" '
                     f'fill="{OCHRE_BG}" stroke="{OCHRE}" stroke-width="2" '
                     f'stroke-dasharray="6 4"/>')
        p.append(f'<rect x="{x}" y="{base - hh}" width="{bw}" height="{hh}" '
                 f'fill="{BLUE_BG}" stroke="{BLUE}" stroke-width="3"/>')
        last = i == 5
        text(x + bw / 2, base - hh + 40,
             f"{rate * 100:.0f}%", 34 if last else 26, weight="normal")
        text(x + bw / 2, base + 40, "生成" if i == 0 else f"検査 {i}", 24,
             cls="" if i == 0 else "sub")
        if i < 5:                    # the gate between two bars
            gx = x + bw + gap / 2
            p.append(f'<line x1="{gx}" y1="{base - full - 10}" x2="{gx}" y2="{base + 6}" '
                     f'stroke="{SUB}" stroke-width="3"/>')
            p.append(f'<path d="M{gx - 14},{base - 150} L{gx + 10},{base - 150}" '
                     f'stroke="{INK}" stroke-width="2.5"/>')
            p.append(f'<path d="M{gx + 2},{base - 158} L{gx + 12},{base - 150} '
                     f'L{gx + 2},{base - 142}" fill="none" stroke="{INK}" stroke-width="2.5"/>')

    # legend
    ly = 512
    p.append(f'<rect x="150" y="{ly - 20}" width="26" height="26" fill="{BLUE_BG}" '
             f'stroke="{BLUE}" stroke-width="3"/>')
    text(186, ly + 2, "残った正しい絵", 24, "start")
    p.append(f'<rect x="470" y="{ly - 20}" width="26" height="26" fill="{OCHRE_BG}" '
             f'stroke="{OCHRE}" stroke-width="2" stroke-dasharray="6 4"/>')
    text(506, ly + 2, "誤って落とした正しい絵", 24, "start")
    p.append("</svg>")
    (OUT / "image_linting_cover.svg").write_text("\n".join(p) + "\n")


def neon_figure():
    """Color check: the bright yellow raincoat (outfit D) goes over the 2% limit.

    The values are the ones in the note (reference 0.0004, the 12 images of
    outfit D 0.051-0.105, one image of outfit A 0.025); per-image values are
    not kept in lab/result.json.
    """
    w, h = 960, 540
    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img"><title>'
        f'{escape("色の検査は、明るい黄色の服を蛍光色とみなして正しい絵を捨てた")}'
        f'</title>',
        f'<style>text{{font-family:{FONT};fill:{INK}}} .sub{{fill:{SUB}}}</style>',
        f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
    ]

    def text(x, y, s, size=24, anchor="middle", cls=""):
        c = f' class="{cls}"' if cls else ""
        p.append(f'<text x="{x}" y="{y}" font-size="{size}" '
                 f'text-anchor="{anchor}"{c}>{escape(s)}</text>')

    def x(v):
        return 80 + v / 0.11 * 820

    top, axis = 70, 400
    # the rejected side of the threshold (grey) and the threshold itself
    p.append(f'<rect x="{x(0.02):.0f}" y="{top}" width="{x(0.11) - x(0.02):.0f}" '
             f'height="{axis - top}" fill="{GREY_BG}"/>')
    text((x(0.02) + x(0.11)) / 2, top + 36, "不合格にする側（2% を超える）", 24, cls="sub")
    p.append(f'<line x1="{x(0.02):.0f}" y1="{top}" x2="{x(0.02):.0f}" y2="{axis}" '
             f'stroke="{SUB}" stroke-width="2" stroke-dasharray="7 5"/>')
    # axis
    p.append(f'<line x1="{x(0):.0f}" y1="{axis}" x2="{x(0.11):.0f}" y2="{axis}" '
             f'stroke="{INK}" stroke-width="2"/>')
    for v, s in [(0, "0"), (0.02, "0.02"), (0.05, "0.05"), (0.10, "0.10")]:
        p.append(f'<line x1="{x(v):.0f}" y1="{axis}" x2="{x(v):.0f}" y2="{axis + 10}" '
                 f'stroke="{INK}" stroke-width="2"/>')
        text(x(v), axis + 40, s, 24)
    text(480, axis + 92, "彩度と明るさがともに 0.85 を超える画素の割合", 24, cls="sub")

    # reference image of outfit D: passes
    y = 160
    p.append(f'<circle cx="{x(0.0004):.0f}" cy="{y}" r="11" fill="{BLUE_BG}" '
             f'stroke="{BLUE}" stroke-width="3"/>')
    text(x(0.0004) + 26, y + 9, "服装 D の基準の絵  0.0004", 24, "start")
    # 12 images of outfit D (seed changed): all thrown away
    y = 250
    p.append(f'<rect x="{x(0.051):.0f}" y="{y - 14}" width="{x(0.105) - x(0.051):.0f}" '
             f'height="28" fill="{OCHRE_BG}" stroke="{OCHRE}" stroke-width="3"/>')
    text(x(0.051) - 18, y + 9, "seed を変えた服装 D の 12 枚", 24, "end")
    text((x(0.051) + x(0.105)) / 2, y + 56, "0.051〜0.105", 24)
    # one image of outfit A
    y = 345
    p.append(f'<circle cx="{x(0.025):.0f}" cy="{y}" r="11" fill="{OCHRE_BG}" '
             f'stroke="{OCHRE}" stroke-width="3"/>')
    text(x(0.025) + 26, y + 9, "服装 A の 1 枚  0.025", 24, "start")
    p.append("</svg>")
    (OUT / "image_linting_neon.svg").write_text("\n".join(p) + "\n")


def _plt():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "font.family": ["Noto Sans CJK JP", "sans-serif"],
        "font.size": 11, "axes.edgecolor": SUB, "axes.labelcolor": INK,
        "xtick.color": INK, "ytick.color": INK, "text.color": INK,
        "svg.fonttype": "path", "svg.hashsalt": "image-linting",
        "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
        "axes.spines.top": False, "axes.spines.right": False,
    })
    return plt


def checks_figure(res):
    """False rejects (of good images) and false accepts (of bad images) per check."""
    plt = _plt()
    rows = res["checks"][::-1]
    names = [r["check"] for r in rows]
    fr = [r["false_reject"] / res["n_good"] * 100 for r in rows]
    fa = [r["false_accept"] / res["n_bad"] * 100 for r in rows]
    fig, axes = plt.subplots(1, 2, figsize=(8.4, 3.6), sharey=True)
    for ax, vals, raw, color, edge, title, n in [
        (axes[0], fr, [r["false_reject"] for r in rows], BLUE_BG, BLUE,
         "誤った棄却（合格の絵を落とした割合）", res["n_good"]),
        (axes[1], fa, [r["false_accept"] for r in rows], OCHRE_BG, OCHRE,
         "誤った合格（不合格の絵を通した割合）", res["n_bad"]),
    ]:
        ax.barh(names, vals, color=color, edgecolor=edge, linewidth=1.5)
        for y, (v, k) in enumerate(zip(vals, raw)):
            ax.text(v + 1.5, y, f"{k}/{n}", va="center", fontsize=10)
        ax.set_xlim(0, 115)
        ax.set_xticks([0, 25, 50, 75, 100])
        ax.set_xticklabels(["0%", "25%", "50%", "75%", "100%"])
        ax.set_title(title, fontsize=11)
    fig.tight_layout()
    fig.savefig(OUT / "image_linting_checks.svg", metadata={"Date": None})
    plt.close(fig)


def stages_figure(res):
    """Share of good images passing the first k checks: measured vs. formulas."""
    plt = _plt()
    st = res["stages"]
    k = [s["n"] for s in st]
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    ax.plot([0] + k, [100] + [s["measured"] * 100 for s in st], "o-", color=BLUE,
            lw=2, label="実測（合格の絵が全段を通った割合）")
    ax.plot([0] + k, [100] + [s["product"] * 100 for s in st], "s--", color=OCHRE,
            lw=1.5, label="各段の通過率の積（独立を仮定）")
    ax.plot([0] + k, [100 * 0.95 ** i for i in [0] + k], ":", color=SUB, lw=1.5,
            label="0.95^n（5% の誤りを n 段）")
    ax.set_xlabel("重ねた検査の段数")
    ax.set_ylabel("通過した割合（%）")
    ax.set_ylim(0, 105)
    ax.set_xticks([0] + k)
    ax.legend(frameon=False, fontsize=10, loc="lower left")
    fig.tight_layout()
    fig.savefig(OUT / "image_linting_stages.svg", metadata={"Date": None})
    plt.close(fig)


def identity_figure(res):
    """Cosine of face crops: same outfit vs. different outfit, CLIP and tags."""
    import numpy as np
    plt = _plt()
    same, diff = res["identity"]["same"], res["identity"]["diff"]
    bins = np.arange(0, 1.0001, 0.02)
    fig, axes = plt.subplots(1, 2, figsize=(8.4, 3.2), sharey=True)
    for ax, key, title in [(axes[0], "clip", "CLIP の埋め込みの cos"),
                           (axes[1], "tag", "タグの確率の cos")]:
        for vals, color, edge, label in [(diff[key], OCHRE_BG, OCHRE, "別の服装"),
                                         (same[key], BLUE_BG, BLUE, "同じ服装")]:
            w = np.full(len(vals), 100 / len(vals))
            filled = label == "別の服装"      # 同じ服装は線だけにして重なりを見せる
            ax.hist(vals, bins=bins, weights=w, histtype="stepfilled" if filled else "step",
                    color=color if filled else edge, edgecolor=edge, linewidth=1.8,
                    label=f"{label}（{len(vals)} 組）")
        ax.set_xlim(0, 1)
        ax.set_title(title, fontsize=11)
        ax.set_xlabel("cos")
        ax.legend(frameon=False, fontsize=9, loc="upper left")
    axes[0].set_ylabel("組の割合（%）")
    fig.tight_layout()
    fig.savefig(OUT / "image_linting_identity.svg", metadata={"Date": None})
    plt.close(fig)


def main():
    OUT.mkdir(exist_ok=True)
    cover_figure()
    neon_figure()
    if "--results" in sys.argv:
        res = json.loads((HERE / "lab" / "result.json").read_text())
        checks_figure(res)
        stages_figure(res)
        identity_figure(res)


if __name__ == "__main__":
    main()
