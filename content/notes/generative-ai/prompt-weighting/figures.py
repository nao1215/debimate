"""Prompt Weighting のノートの図を作る（images/ に WebP で書き出す）。

concept_figure() は SVG を手書きし、Chrome の headless で PNG にしてから WebP にする（冒頭の図）。
result_figures() などは lab/ の集計 JSON から matplotlib でグラフを描く。
77 トークンの区切りと、語を 1 つずつ外す実験の図は ../clip-token-limit/figures.py にある。

使い方:
    uv run --with matplotlib --with pillow python figures.py
"""
import json
import subprocess
import tempfile
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
IMAGES = HERE / "images"

INK, SUB = "#1f1f1f", "#666666"
BLUE, BLUE_PALE = "#7aa6c2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
RED = "#e15759"
NEUTRAL = "#f2f2f2"
FONT = "'Noto Sans CJK JP','Hiragino Sans','Yu Gothic',sans-serif"


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
    """重みは、空のプロンプトの埋め込みから語の埋め込みまでの差を w 倍に伸ばす。"""
    w, h = 500, 520
    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img"><title>'
        f'{escape("重みは空のプロンプトの埋め込みから語の埋め込みまでの差を伸ばす")}'
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
    text(380, 120, "w > 1", 26)
    text(380, 152, "語を通り越した先", 22, cls="sub")
    ex, ey = 90, 420      # 空のプロンプト
    tx, ty = 230, 300     # 重み 1.0 の語
    p.append(f'<circle cx="{ex}" cy="{ey}" r="12" fill="{NEUTRAL}" stroke="{SUB}" stroke-width="2"/>')
    text(40, ey + 50, "空のプロンプト（w = 0）", 24, anchor="start", cls="sub")
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
    text(tx - 22, ty + 8, "語（w = 1.0）", 24, anchor="end")

    p.append("</svg>")
    svg_to_webp("\n".join(p) + "\n", w, h, "prompt-weighting_concept.webp")


def result_figures():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({
        "font.size": 10, "axes.edgecolor": SUB, "axes.labelcolor": INK,
        "xtick.color": INK, "ytick.color": INK, "text.color": INK,
        "svg.fonttype": "path", "svg.hashsalt": "prompt-weighting",
        "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
        "font.family": "Noto Sans CJK JP",
    })
    lab = HERE / "lab"

    # ネガティブプロンプトの重みと個数ごとの、彩度の平均と赤い画素の割合
    neg = {r["name"]: r for r in json.loads((lab / "result_negative.json").read_text())}
    weights = [1.0, 1.2, 1.3, 1.5, 1.8]
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 4.2))
    # 線: (条件名の接頭辞, 凡例, 色, 線種, 印)
    lines = [("k1", "lowres の 1 語だけ", SUB, ":", "s"),
             ("k12", "12 語すべて", OCHRE, "-", "^")]
    if "mono_w1.3" in neg:
        lines += [("mono", "monochrome + greyscale だけ", INK, "-.", "D"),
                  ("k10", "残りの 10 語", BLUE, "--", "o")]
    for key, ax, ylabel, scale in [("sat", axes[0], "彩度の平均（0〜1）", 1),
                                   ("red", axes[1], "赤い画素（%）", 100)]:
        for prefix, label, color, ls, mk in lines:
            xs = [wt for wt in weights if wt == 1.0 or f"{prefix}_w{wt:.1f}" in neg]
            ys = [neg["w1.0" if wt == 1.0 else f"{prefix}_w{wt:.1f}"][key] * scale for wt in xs]
            ax.plot(xs, ys, color=color, ls=ls, marker=mk, lw=2, label=label)
        ax.set_xlabel("ネガティブプロンプトの語の重み")
        ax.set_ylabel(ylabel)
        ax.set_xticks(weights)
        ax.spines[["top", "right"]].set_visible(False)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, frameon=False, fontsize=10, loc="lower center", ncol=2)
    fig.tight_layout(rect=(0, 0.13, 1, 1))
    save_webp(fig, "prompt-weighting_negative.webp")
    plt.close(fig)


def lighting_figure():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rows = {r["name"]: r for r in json.loads((HERE / "lab" / "result_lighting.json").read_text())}
    weights = [1.0, 1.2, 1.3]
    lights = [("none", "照明の語なし", SUB, ":", "s"),
              ("night", "night", INK, "-", "o"),
              ("neon_light", "neon light", BLUE, "-", "^"),
              ("sunset", "sunset", OCHRE, "-", "D"),
              ("dramatic_lighting", "dramatic lighting", BLUE, "--", "v")]
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 4.2))
    for key, ax, ylabel, scale in [("white", axes[0], "白い画素（%）", 100),
                                   ("sat", axes[1], "彩度の平均（0〜1）", 1)]:
        for name, label, color, ls, mk in lights:
            ys = [rows[f"{name}_neg{w:.1f}"][key] * scale for w in weights]
            ax.plot(weights, ys, color=color, ls=ls, marker=mk, lw=2, label=label)
        ax.set_xlabel("ネガティブプロンプト 12 語の重み")
        ax.set_ylabel(ylabel)
        ax.set_xticks(weights)
        ax.spines[["top", "right"]].set_visible(False)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, frameon=False, fontsize=10, loc="lower center", ncol=3)
    fig.tight_layout(rect=(0, 0.13, 1, 1))
    save_webp(fig, "prompt-weighting_lighting.webp")
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
        "font.family": "Noto Sans CJK JP",
    })
    return plt


def positive_figure():
    """実験 1: 青いポットの重みと、青い画素・黄色い画素の割合（3 seed の平均）。"""
    plt = _plt()
    rows = json.loads((HERE / "lab" / "result_positive.json").read_text())
    xs = [float(r["name"][1:]) for r in rows]
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    ax.plot(xs, [r["blue"] * 100 for r in rows], color=BLUE, lw=2.2, marker="o",
            label="青い画素（ポット、重みあり）")
    ax.plot(xs, [r["yellow"] * 100 for r in rows], color=OCHRE, lw=2.2, marker="D",
            ls="--", label="黄色い画素（主にレモン、重みなし）")
    ax.set_xticks(xs)
    ax.set_xlabel("blue ceramic teapot の重み")
    ax.set_ylabel("画素の割合（%）")
    ax.set_ylim(0, 20)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, fontsize=10, loc="center right")
    fig.tight_layout()
    save_webp(fig, "prompt-weighting_positive.webp")
    plt.close(fig)


def cfg_figure():
    """CFG: ネガティブプロンプトでの予測からプロンプトでの予測への差を cfg 倍に伸ばす。"""
    w, h = 960, 260
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img">'
         f'<title>{escape("CFG はネガティブプロンプトでの予測からプロンプトでの予測への差を cfg 倍に伸ばす")}</title>',
         f'<style>text{{font-family:{FONT};fill:{INK}}} .sub{{fill:{SUB}}}</style>',
         f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
         '<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
         f'markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{INK}"/></marker></defs>']

    def text(x, y, t, size=20, anchor="middle", cls=""):
        c = f' class="{cls}"' if cls else ""
        p.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}"{c}>{escape(t)}</text>')

    nx, py_, y = 150, 260, 150
    mx = nx + (py_ - nx) * 5.5
    p.append(f'<line x1="{py_}" y1="{y}" x2="{mx - 14}" y2="{y}" stroke="{OCHRE}" stroke-width="3" '
             f'stroke-dasharray="9 6"/>')
    p.append(f'<line x1="{nx + 14}" y1="{y}" x2="{py_ - 14}" y2="{y}" stroke="{INK}" stroke-width="3" marker-end="url(#ah)"/>')
    p.append(f'<circle cx="{nx}" cy="{y}" r="12" fill="{NEUTRAL}" stroke="{SUB}" stroke-width="2.5"/>')
    p.append(f'<circle cx="{py_}" cy="{y}" r="12" fill="{BLUE_PALE}" stroke="{BLUE}" stroke-width="2.5"/>')
    p.append(f'<circle cx="{mx}" cy="{y}" r="13" fill="#ffffff" stroke="{OCHRE}" stroke-width="3"/>')
    text(nx, y + 50, "ネガティブプロンプトでの予測", 19)
    text(py_, y - 30, "プロンプトでの予測", 19)
    text(mx, y + 50, "混ぜた予測", 19)
    text(mx, y + 76, "（差の 5.5 倍の位置）", 17, cls="sub")
    text((nx + py_) / 2, y + 26, "差", 18, cls="sub")
    text(470, y + 30, "ネガティブプロンプトから遠ざかる向きに伸ばす", 19, cls="sub")
    text(w / 2, 50, "予測 = ネガティブプロンプトでの予測 + 5.5 ×（プロンプトでの予測 − ネガティブプロンプトでの予測）", 17)
    p.append("</svg>")
    svg_to_webp("\n".join(p) + "\n", w, h, "prompt-weighting_cfg.webp")


def share_figure():
    """説明用: 画像のある位置が、参照する割合を 3 つの語で分け合う（数値は仮）。"""
    w, h = 900, 260
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img">'
         f'<title>{escape("参照する割合は合計 100% を語で分け合う")}</title>',
         f'<style>text{{font-family:{FONT};fill:{INK}}} .sub{{fill:{SUB}}}</style>',
         f'<rect width="{w}" height="{h}" fill="#ffffff"/>']

    def text(x, y, t, size=20, anchor="middle", cls=""):
        c = f' class="{cls}"' if cls else ""
        p.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}"{c}>{escape(t)}</text>')

    x0, bw = 230, 620
    rows = [("重みなし", [("teapot", 0.4), ("lemons", 0.3), ("glass bottle", 0.3)], 70),
            ("teapot に重み", [("teapot", 0.7), ("lemons", 0.15), ("glass bottle", 0.15)], 160)]
    colors = {"teapot": (BLUE_PALE, BLUE), "lemons": (OCHRE_PALE, OCHRE), "glass bottle": (NEUTRAL, SUB)}
    for label, parts, y in rows:
        text(x0 - 20, y + 34, label, 20, anchor="end")
        x = x0
        for name, r in parts:
            fill, stroke = colors[name]
            p.append(f'<rect x="{x}" y="{y}" width="{bw * r}" height="52" fill="{fill}" stroke="{stroke}" stroke-width="2"/>')
            text(x + bw * r / 2, y + 33, name if r > 0.2 else name.split()[0], 18 if r > 0.2 else 15)
            x += bw * r
    text(x0 + bw / 2, 40, "画像のある位置が、各語を参照する割合（合計 100%）", 20)
    text(x0 + bw / 2, 245, "説明用の例で、数値は測った値ではない", 16, cls="sub")
    p.append("</svg>")
    svg_to_webp("\n".join(p) + "\n", w, h, "prompt-weighting_share.webp")


if __name__ == "__main__":
    concept_figure()
    cfg_figure()
    share_figure()
    if (HERE / "lab" / "result_negative.json").exists():
        result_figures()
    if (HERE / "lab" / "result_lighting.json").exists():
        lighting_figure()
    if (HERE / "lab" / "result_positive.json").exists():
        positive_figure()
