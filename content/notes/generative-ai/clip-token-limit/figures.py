"""CLIP Token Limit のノートの図を作る（images/ に WebP で書き出す）。

concept_figure() は SVG を手書きし、Chrome の headless で PNG にしてから WebP にする（冒頭の図）。
他の図は ../prompt-weighting/lab/ の集計 JSON から
matplotlib でグラフを描く（実験のファイルは Prompt Weighting のノートと共有している）。

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
LAB = HERE.parent / "prompt-weighting" / "lab"

INK, SUB = "#1f1f1f", "#666666"
BLUE, BLUE_PALE = "#7aa6c2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
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
RED = "#e15759"


def _svg(w, h, title):
    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img"><title>{escape(title)}</title>',
        f'<style>text{{font-family:{FONT};fill:{INK}}} .sub{{fill:{SUB}}}</style>',
        f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
        '<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
        f'markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{INK}"/></marker>'
        '<marker id="ahs" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
        f'markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{SUB}"/></marker></defs>',
    ]

    def text(x, y, s, size=22, anchor="middle", cls=""):
        c = f' class="{cls}"' if cls else ""
        p.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}"{c}>{escape(s)}</text>')

    def box(x, y, bw, bh, fill, stroke, sw=2, rx=6, dash=""):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        p.append(f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" rx="{rx}" fill="{fill}" '
                 f'stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def arrow(d, color=INK, sw=3, dash=""):
        m = "ah" if color == INK else "ahs"
        ds = f' stroke-dasharray="{dash}"' if dash else ""
        p.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{sw}"{ds} marker-end="url(#{m})"/>')

    return p, text, box, arrow


def pipeline_figure():
    """前提: text encoder の出力が UNet に届く 2 つの経路。"""
    w, h = 980, 330
    p, text, box, arrow = _svg(w, h, "プロンプトがトークンの列と pooled の 2 つの経路で UNet に届く")
    box(20, 125, 130, 70, NEUTRAL, SUB)
    text(85, 168, "プロンプト", 22)
    arrow("M 150 160 L 192 160")
    box(198, 115, 170, 90, NEUTRAL, SUB)
    text(283, 152, "tokenizer", 22)
    text(283, 182, "トークンの列", 18, cls="sub")
    arrow("M 368 160 L 410 160")
    box(416, 115, 170, 90, NEUTRAL, SUB)
    text(501, 152, "text encoder", 22)
    text(501, 182, "ベクトルにする", 18, cls="sub")
    # 経路 1: トークンごとの埋め込みの列
    arrow("M 586 140 C 620 140 620 70 652 70")
    box(658, 30, 300, 80, BLUE_PALE, BLUE)
    text(808, 64, "トークンごとの埋め込みの列", 21)
    text(808, 92, "UNet の画像の各位置が参照", 18, cls="sub")
    # 経路 2: pooled
    arrow("M 586 180 C 620 180 620 250 652 250", SUB, 2.5, "7 5")
    box(658, 210, 300, 80, OCHRE_PALE, OCHRE)
    text(808, 244, "pooled（全体のまとめ 1 本）", 21)
    text(808, 272, "UNet 全体に足される", 18, cls="sub")
    text(808, 320, "どちらも UNet に渡る", 16, cls="sub")
    p.append("</svg>")
    svg_to_webp("\n".join(p) + "\n", w, h, "clip-token-limit_pipeline.webp")


def concept_figure():
    """長いプロンプトは 75 トークンずつ別々に読まれ、連結されて UNet に渡る。"""
    w, h = 800, 570
    p, text, box, arrow = _svg(w, h, "長いプロンプトは 75 トークンずつ別々に読まれ、連結されて UNet に渡る")
    x0 = 140

    def chunk(y, label, fill, stroke):
        p.append(f'<rect x="{x0}" y="{y}" width="34" height="64" fill="{NEUTRAL}" stroke="{SUB}"/>')
        p.append(f'<rect x="{x0 + 34}" y="{y}" width="300" height="64" fill="{fill}" '
                 f'stroke="{stroke}" stroke-width="2.5"/>')
        p.append(f'<rect x="{x0 + 334}" y="{y}" width="34" height="64" fill="{NEUTRAL}" stroke="{SUB}"/>')
        for i in range(1, 15):
            x = x0 + 34 + i * 20
            p.append(f'<line x1="{x}" y1="{y + 8}" x2="{x}" y2="{y + 56}" stroke="{stroke}" '
                     f'stroke-width="1" opacity="0.6"/>')
        text(x0 + 184, y + 42, label, 24)

    cx = x0 + 184
    text(cx, 44, "1 つの枠 = S + 75 トークン + E = 77 トークン", 26)
    text(cx, 78, "枠ごとに別々に text encoder を通る", 20, cls="sub")
    chunk(116, "枠 1（chunk 1）: 1〜75", BLUE_PALE, BLUE)
    chunk(236, "枠 2（chunk 2）: 76〜150", OCHRE_PALE, OCHRE)
    for y in (108, 228):
        text(x0 + 17, y, "S", 20, cls="sub")
        text(x0 + 351, y, "E", 20, cls="sub")
    bar_y = 380
    for bx, fill, stroke, lab in [(x0, BLUE_PALE, BLUE, "枠 1"), (x0 + 184, OCHRE_PALE, OCHRE, "枠 2")]:
        p.append(f'<rect x="{bx}" y="{bar_y}" width="20" height="40" fill="{NEUTRAL}" stroke="{SUB}"/>')
        p.append(f'<rect x="{bx + 20}" y="{bar_y}" width="144" height="40" fill="{fill}" stroke="{stroke}" stroke-width="2"/>')
        p.append(f'<rect x="{bx + 164}" y="{bar_y}" width="20" height="40" fill="{NEUTRAL}" stroke="{SUB}"/>')
        text(bx + 92, bar_y + 28, lab, 20)
        text(bx + 10, bar_y - 6, "S", 14, cls="sub")
        text(bx + 174, bar_y - 6, "E", 14, cls="sub")
    arrow(f"M {x0} 148 C {x0 - 80} 160 {x0 - 60} 330 {x0 + 80} 372")
    arrow(f"M {x0 + 276} 300 L {x0 + 276} 372")
    arrow(f"M {cx} 420 L {cx} 476")
    text(cx + 14, 446, "連結した 154 トークン", 18, anchor="start", cls="sub")
    text(cx + 14, 468, "画像の各位置から参照", 18, anchor="start", cls="sub")
    box(cx - 150, 482, 300, 56, "#ffffff", INK, 2.5, 8)
    text(cx, 519, "UNet", 26)
    px = x0 + 480
    arrow(f"M {x0 + 368} 148 C {px} 148 {px} 200 {px} 296", SUB, 2.5, "7 5")
    box(px - 72, 302, 144, 64, NEUTRAL, SUB)
    text(px, 330, "pooled", 22)
    text(px, 354, "枠 1 の E の位置", 16, cls="sub")
    arrow(f"M {px} 366 C {px} 480 {px - 40} 510 {cx + 156} 510", SUB, 2.5, "7 5")
    text(px + 8, 430, "絵全体に効く", 18, anchor="start", cls="sub")
    p.append("</svg>")
    svg_to_webp("\n".join(p) + "\n", w, h, "clip-token-limit_concept.webp")


def causal_figure():
    """枠 2 の語は、枠 1 の語を参照できない（枠ごとに別々に読むため）。"""
    w, h = 980, 300
    p, text, box, arrow = _svg(w, h, "枠 2 の語は枠 1 の語を参照できない")
    toks1 = ["S", "masterpiece", "…", "quiet mood", "E"]
    toks2 = ["S", "red background", "…", "still", "E"]
    xs = []
    x = 20
    for i, t in enumerate(toks1 + toks2):
        tw = 44 if t in ("S", "E", "…") else 150
        if i == 5:
            x += 40
        fill, stroke = (BLUE_PALE, BLUE) if i < 5 else (OCHRE_PALE, OCHRE)
        if t in ("S", "E"):
            fill, stroke = NEUTRAL, SUB
        box(x, 180, tw, 50, fill, stroke, 2, 4)
        text(x + tw / 2, 212, t, 17 if tw > 44 else 18)
        xs.append(x + tw / 2)
        x += tw + 6
    text((xs[0] + xs[4]) / 2, 268, "枠 1", 20, cls="sub")
    text((xs[5] + xs[9]) / 2, 268, "枠 2", 20, cls="sub")
    # 枠 1 の中: quiet mood -> masterpiece は参照できる
    arrow(f"M {xs[3]} 176 C {xs[3]} 120 {xs[1]} 120 {xs[1]} 172", INK, 2.5)
    text((xs[1] + xs[3]) / 2, 112, "枠の中では前の語を見られる", 18)
    # 枠 2 の red background -> 枠 1 は参照できない
    arrow(f"M {xs[6]} 176 C {xs[6]} 40 {xs[3]} 40 {xs[3]} 172", SUB, 2.5, "7 5")
    mx, my = (xs[6] + xs[3]) / 2, 74
    p.append(f'<line x1="{mx - 14}" y1="{my - 14}" x2="{mx + 14}" y2="{my + 14}" stroke="{RED}" stroke-width="4"/>')
    p.append(f'<line x1="{mx - 14}" y1="{my + 14}" x2="{mx + 14}" y2="{my - 14}" stroke="{RED}" stroke-width="4"/>')
    text(mx, 36, "枠をまたいでは見られない", 18)
    p.append("</svg>")
    svg_to_webp("\n".join(p) + "\n", w, h, "clip-token-limit_causal.webp")


def position_map_figure():
    """実験 1: red background を入れた 4 か所（149 トークンが 2 つの枠に分かれる）。"""
    w, h = 980, 230
    p, text, box, arrow = _svg(w, h, "red background を入れた 4 か所")
    x0, cw = 40, 440
    box(x0, 110, cw, 50, BLUE_PALE, BLUE, 2, 4)
    box(x0 + cw + 20, 110, cw, 50, OCHRE_PALE, OCHRE, 2, 4)
    text(x0 + cw / 2, 142, "枠 1: 75 トークン", 20)
    text(x0 + cw + 20 + cw / 2, 142, "枠 2: 74 トークン", 20)
    marks = [("front", x0 + 60), ("chunk1_end", x0 + cw - 20),
             ("chunk2_start", x0 + cw + 40), ("chunk2_end", x0 + 2 * cw)]
    for i, (lab, mx) in enumerate(marks):
        p.append(f'<rect x="{mx - 10}" y="104" width="20" height="62" fill="{RED}" opacity="0.85"/>')
        y = 70 if i % 2 == 0 else 40
        p.append(f'<line x1="{mx}" y1="{y + 6}" x2="{mx}" y2="102" stroke="{SUB}" stroke-width="1.5"/>')
        anchor = "end" if lab == "chunk1_end" else ("start" if lab == "chunk2_start" else "middle")
        dx = 6 if anchor == "end" else (-6 if anchor == "start" else 0)
        text(mx + dx, y, lab, 18, anchor=anchor)
    text(w / 2, 200, "赤い印が red background（3 トークン）を入れた場所。front は先頭の 4 語の後", 17, cls="sub")
    p.append("</svg>")
    svg_to_webp("\n".join(p) + "\n", w, h, "clip-token-limit_position_map.webp")


def procedure_figure():
    """実験 2: 1 語ずつ外して原因の語を探す手順。"""
    w, h = 1000, 180
    p, text, box, arrow = _svg(w, h, "1 語ずつ外して原因の語を探す手順")
    steps = [("全部の語で生成", "seed を固定"),
             ("1 語ずつ外して生成", "同じ seed"),
             ("症状の指標を比べる", "例: 赤い画素の割合"),
             ("指標が下がった語", "原因の候補")]
    bw, gap = 210, 44
    for i, (a, b) in enumerate(steps):
        x = 20 + i * (bw + gap)
        fill, stroke = (OCHRE_PALE, OCHRE) if i == 3 else (NEUTRAL, SUB)
        box(x, 50, bw, 90, fill, stroke)
        text(x + bw / 2, 88, a, 21)
        text(x + bw / 2, 118, b, 17, cls="sub")
        if i < 3:
            arrow(f"M {x + bw + 4} 95 L {x + bw + gap - 6} 95")
    p.append("</svg>")
    svg_to_webp("\n".join(p) + "\n", w, h, "clip-token-limit_procedure.webp")


def _plt():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "font.size": 11, "axes.edgecolor": SUB, "axes.labelcolor": INK,
        "xtick.color": INK, "ytick.color": INK, "text.color": INK,
        "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
        "font.family": "Noto Sans CJK JP",
    })
    return plt


def position_figure():
    """実験 1: red background を置いた場所ごとの赤い画素（seed ごとの点と 4 seed の平均）。"""
    plt = _plt()
    rows = json.loads((LAB / "result_position.json").read_text())
    order = ["none", "front", "chunk1_end", "chunk2_start", "chunk2_end"]
    rows = sorted(rows, key=lambda r: order.index(r["name"]))
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    for i, r in enumerate(rows):
        color = SUB if r["name"] == "none" else (BLUE if "chunk2" not in r["name"] else OCHRE)
        ys = [s["red"] * 100 for s in r["per_seed"]]
        ax.scatter([i] * len(ys), ys, color=color, s=28, alpha=0.7, zorder=2)
        ax.hlines(r["red"] * 100, i - 0.25, i + 0.25, color=INK, lw=2.4, zorder=3)
    ax.set_xticks(range(len(rows)), [r["name"] for r in rows])
    ax.set_ylabel("赤い画素（%）")
    ax.set_ylim(0, 50)
    ax.axvline(2.5, color="#cccccc", lw=1, ls="--")
    ax.text(1.5, 47, "枠 1（chunk 1）", ha="center", color=SUB, fontsize=10)
    ax.text(3.5, 47, "枠 2（chunk 2）", ha="center", color=SUB, fontsize=10)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    save_webp(fig, "clip-token-limit_position.webp")
    plt.close(fig)


def ablation_figure():
    """実験 2: 語を 1 つずつ外した時の、画素の差と赤・黄色の画素（2 seed の平均）。"""
    plt = _plt()
    rows = json.loads((LAB / "result_ablation.json").read_text())
    names = ["全部" if r["name"] == "full" else "− " + r["name"][3:].replace("_", " ") for r in rows]
    ys = list(range(len(rows)))[::-1]
    panels = [("diff", "外す前との画素の差（0〜255）", 1, None),
              ("red", "赤い画素（%）", 100, "no_red_apple"),
              ("yellow", "黄色い画素（%）", 100, "no_lemons")]
    fig, axes = plt.subplots(1, 3, figsize=(7.6, 3.8), sharey=True)
    for ax, (key, label, scale, hit) in zip(axes, panels):
        colors = [OCHRE if r["name"] == hit else "#c8c8c8" for r in rows]  # 橙: 症状が下がった語
        ax.barh(ys, [r[key] * scale for r in rows], color=colors, height=0.66)
        ax.set_xlabel(label)
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].set_yticks(ys, names)
    fig.tight_layout()
    save_webp(fig, "clip-token-limit_ablation.webp")
    plt.close(fig)


def diff_figure():
    """実験 1: 基準の絵との画素の差（seed ごとの点と 4 seed の平均）。"""
    plt = _plt()
    rows = json.loads((LAB / "result_position.json").read_text())
    order = ["front", "chunk1_end", "chunk2_start", "chunk2_end"]
    rows = sorted([r for r in rows if r["name"] in order], key=lambda r: order.index(r["name"]))
    fig, ax = plt.subplots(figsize=(6.4, 3.0))
    for i, r in enumerate(rows):
        color = BLUE if "chunk2" not in r["name"] else OCHRE
        ax.bar(i, r["diff"], color=color, width=0.55, alpha=0.85)
        ax.scatter([i] * len(r["per_seed"]), [s["diff"] for s in r["per_seed"]], color=INK, s=14, zorder=3)
        ax.text(i, 4, f"平均 {r['diff']:.1f}", ha="center", fontsize=10, color=INK)
    ax.set_xticks(range(len(rows)), [r["name"] for r in rows])
    ax.set_ylabel("基準との画素の差（0〜255）")
    ax.set_ylim(0, 70)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    save_webp(fig, "clip-token-limit_diff.webp")
    plt.close(fig)


if __name__ == "__main__":
    pipeline_figure()
    concept_figure()
    causal_figure()
    position_map_figure()
    procedure_figure()
    position_figure()
    diff_figure()
    ablation_figure()
