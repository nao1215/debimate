"""サブエージェントのノートの図を作る。

python3 figures.py
  images/subagent_concept.webp  親と子のコンテキストの中身の量（手書きの SVG を Chrome で描いて WebP に）
  images/subagent_handoff.webp  子に任せる形（agents as tools）と引き継ぐ形（handoff）の違い
  images/subagent_results.webp  lab/results.jsonl の合計の正答と親のコンテキストの長さ
"""
import json
import subprocess
import tempfile
from collections import defaultdict
from html import escape
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from PIL import Image  # noqa: E402

HERE = Path(__file__).resolve().parent
INK, SUB = "#1f1f1f", "#666666"
BLUE, BLUE_PALE = "#7aa6c2", "#eaf1f5"
OCHRE, OCHRE_PALE = "#d4a24c", "#f8eed8"
GREEN, GREEN_PALE = "#8fae86", "#e9f1e6"
GRAY_PALE = "#f2f2f2"
FONT = "'Noto Sans CJK JP','Hiragino Sans','Yu Gothic',sans-serif"
OUT = HERE / "images"


def png_to_webp(png, name):
    """PNG を WebP にして images/ に置く。"""
    Image.open(png).convert("RGB").save(OUT / name, "WEBP", quality=90, method=6)


def svg_to_webp(svg_text, w, h, name):
    """手書きの SVG を Chrome で 2 倍の解像度に描き、WebP にする。"""
    with tempfile.TemporaryDirectory() as tmp:
        svg, png = Path(tmp) / "fig.svg", Path(tmp) / "fig.png"
        svg.write_text(svg_text, encoding="utf-8")
        subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--hide-scrollbars",
                        "--force-device-scale-factor=2", f"--window-size={w},{h}",
                        f"--screenshot={png}", svg.as_uri()], check=True, capture_output=True)
        png_to_webp(png, name)


def concept_figure():
    """左は 1 つのコンテキストに全部を積む形、右は子が読んで親には要約だけが戻る形。"""
    w, h = 960, 540
    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img"><title>'
        f'{escape("1 つのコンテキストに全部を積む形と、子が読んで親には要約だけが戻る形")}</title>',
        f'<style>text{{font-family:{FONT};fill:{INK}}} .sub{{fill:{SUB}}}</style>',
        f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
    ]

    def text(x, y, s, size=24, anchor="middle", cls=""):
        c = f' class="{cls}"' if cls else ""
        p.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}"{c}>{escape(s)}</text>')

    def rect(x, y, rw, rh, fill, stroke, sw=2, rx=4, dash=""):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        p.append(f'<rect x="{x}" y="{y}" width="{rw}" height="{rh}" rx="{rx}" fill="{fill}" '
                 f'stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def stack(x, y, cw, n_reads, block=26):
        """質問 1 つの下に、読んだファイル・ツールの出力を n_reads 個積む。戻り値は下端。"""
        rect(x + 6, y + 6, cw - 12, 22, BLUE, BLUE, 1.5)
        y += 34
        for i in range(n_reads):
            rect(x + 6, y, cw - 12, block, OCHRE_PALE, OCHRE, 1.5)
            y += block + 4
        return y

    # 左: 1 つのコンテキスト
    text(150, 50, "1 つのコンテキスト")
    rect(70, 70, 160, 412, "#ffffff", INK, 2.5, 10)
    stack(70, 70, 160, 12)
    text(150, 522, "読んだもの全部", 24, cls="sub")

    # 区切り
    p.append(f'<line x1="300" y1="30" x2="300" y2="520" stroke="{SUB}" stroke-width="1" '
             'stroke-dasharray="4 4"/>')

    # 右: 親と子
    text(420, 50, "親")
    rect(360, 70, 120, 150, "#ffffff", INK, 2.5, 10)
    rect(366, 76, 108, 22, BLUE, BLUE, 1.5)
    for i in range(3):
        rect(366, 108 + i * 30, 108, 22, GREEN_PALE, GREEN, 1.5)
    text(420, 250, "要約だけ", 24, cls="sub")

    for j in range(3):
        cx = 560 + j * 130
        text(cx + 78, 308, f"子 {j + 1}")
        rect(cx, 320, 110, 162, "#ffffff", SUB, 2, 10)
        y = 326
        rect(cx + 6, y, 98, 18, BLUE_PALE, BLUE, 1.5)   # 親から渡された指示
        y += 24
        for i in range(4):
            rect(cx + 6, y, 98, 22, OCHRE_PALE, OCHRE, 1.5)
            y += 26
        rect(cx + 6, y + 2, 98, 22, GREEN_PALE, GREEN, 1.5)  # 子が返す要約
        # 子の要約から親へ戻る線
        sx, sy = cx + 22, 318
        ty = 119 + (2 - j) * 30   # 遠い子ほど上の欄へ戻し、線を交差させない
        p.append(f'<path d="M {sx} {sy} C {sx} {sy - 90}, 560 {ty}, 486 {ty}" fill="none" '
                 f'stroke="{GREEN}" stroke-width="3"/>')
        p.append(f'<polygon points="480,{ty} 494,{ty - 8} 494,{ty + 8}" fill="{GREEN}"/>')
    text(760, 140, "子が読んだものは", 24, "start", cls="sub")
    text(760, 172, "親に入らない", 24, "start", cls="sub")
    text(560, 522, "子ごとに別のコンテキスト", 24, "start", cls="sub")
    svg_to_webp("\n".join(p + ["</svg>"]) + "\n", w, h, "subagent_concept.webp")


def handoff_figure():
    """左は親が子に指示だけを渡して要約を受け取る形、右は会話の履歴ごと別のエージェントに引き継ぐ形。"""
    w, h = 960, 440
    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img"><title>'
        f'{escape("子に任せる形と、会話の履歴ごと引き継ぐ形")}</title>',
        f'<style>text{{font-family:{FONT};fill:{INK}}} .sub{{fill:{SUB}}}</style>',
        f'<defs><marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" '
        f'orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{SUB}"/></marker></defs>',
        f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
    ]

    def text(x, y, s, size=22, anchor="middle", cls=""):
        c = f' class="{cls}"' if cls else ""
        p.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}"{c}>{escape(s)}</text>')

    def rect(x, y, rw, rh, fill, stroke, sw=1.5, rx=4, dash=""):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        p.append(f'<rect x="{x}" y="{y}" width="{rw}" height="{rh}" rx="{rx}" fill="{fill}" '
                 f'stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def arrow(x1, y1, x2, y2):
        p.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{SUB}" stroke-width="2.5" '
                 'marker-end="url(#ar)"/>')

    def context(x, label, bars, top=100, cw=150):
        """見出しと、中身の帯（(面, 線) の並び）を持つコンテキストの枠。"""
        text(x + cw / 2, top - 14, label, 24)
        rect(x, top, cw, 230, "#ffffff", INK, 2.5, 10)
        y = top + 10
        for fill, stroke in bars:
            rect(x + 8, y, cw - 16, 26, fill, stroke)
            y += 34

    # 左: 子に任せる（agents as tools）
    text(240, 40, "子に任せる（agents as tools）", 26)
    context(40, "親", [(BLUE, BLUE), (GREEN_PALE, GREEN)])
    context(290, "子", [(BLUE_PALE, BLUE), (OCHRE_PALE, OCHRE), (OCHRE_PALE, OCHRE),
                        (OCHRE_PALE, OCHRE), (GREEN_PALE, GREEN)])
    arrow(192, 123, 286, 123)
    text(240, 112, "指示だけ", 20, cls="sub")
    arrow(286, 290, 192, 290)
    text(240, 280, "要約だけ", 20, cls="sub")
    text(240, 375, "答えを書くのは親のまま", 22)
    text(240, 408, "子のコンテキストは捨てる", 20, cls="sub")

    p.append(f'<line x1="480" y1="20" x2="480" y2="420" stroke="{SUB}" stroke-width="1" stroke-dasharray="4 4"/>')

    # 右: 引き継ぐ（handoff）
    hist = [(BLUE, BLUE), (OCHRE_PALE, OCHRE), (OCHRE_PALE, OCHRE), (OCHRE_PALE, OCHRE)]
    text(720, 40, "引き継ぐ（handoff）", 26)
    context(520, "エージェント A", hist)
    context(770, "エージェント B", hist)
    text(719, 170, "履歴を", 20, cls="sub")
    text(719, 194, "全部渡す", 20, cls="sub")
    arrow(672, 206, 766, 206)
    text(719, 236, "（既定）", 20, cls="sub")
    text(720, 375, "以後はエージェント B が答える", 22)
    text(720, 408, "input_filter で渡す履歴を絞ることもできる", 20, cls="sub")
    svg_to_webp("\n".join(p + ["</svg>"]) + "\n", w, h, "subagent_handoff.webp")


def results_figure():
    rows = [json.loads(l) for l in open(HERE / "lab" / "results.jsonl", encoding="utf-8")]
    tot, ctx = defaultdict(int), defaultdict(list)
    for r in rows:
        tot[(r["mode"], r["k"])] += r["total_ok"]
        ctx[(r["mode"], r["k"])].append(r["parent_prompt"])
    ks = sorted({r["k"] for r in rows})
    plt.rcParams.update({
        "font.family": "Noto Sans CJK JP", "font.size": 10, "axes.edgecolor": SUB,
        "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK, "text.color": INK,
        "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
    })
    fig, axes = plt.subplots(1, 2, figsize=(7.6, 3.6))
    styles = [("single", "1 つのコンテキストに積む", OCHRE, "-", "o"),
              ("sub_brief", "子に抽出させる（指示あり）", BLUE, "-", "s"),
              ("sub_vague", "子に要約させる（指示なし）", SUB, "--", "^")]
    for mode, label, color, ls, m in styles:
        axes[0].plot(ks, [tot[(mode, k)] for k in ks], color=color, ls=ls,
                     marker=m, lw=2, label=label)
        c = [sum(ctx[(mode, k)]) / len(ctx[(mode, k)]) / 1000 for k in ks]
        axes[1].plot(ks, c, color=color, ls=ls, marker=m, lw=2, label=label)
    axes[0].set_ylabel("合計まで正しかった組（4 組中）")
    axes[0].set_ylim(-0.3, 4.3)
    axes[0].set_yticks(range(5))
    axes[0].set_xticks(ks)
    axes[1].set_ylabel("親の最後の呼び出しの入力（K トークン）")
    axes[1].set_xticks(ks)
    for ax in axes:
        ax.set_xlabel("資料の数")
        ax.spines[["top", "right"]].set_visible(False)
    axes[1].legend(loc="upper left", frameon=False, fontsize=8.5)
    fig.tight_layout()
    with tempfile.TemporaryDirectory() as tmp:
        png = Path(tmp) / "fig.png"
        fig.savefig(png, dpi=200, facecolor="#ffffff")
        png_to_webp(png, "subagent_results.webp")


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    concept_figure()
    handoff_figure()
    if (HERE / "lab" / "results.jsonl").exists():
        results_figure()
