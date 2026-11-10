"""Diffusion Model のノートの図を作る。

全体の流れの図は Python 標準ライブラリだけで SVG を書く。sigma の列のグラフは matplotlib。
どちらも lab/schedule.json（lab/schedule.py の出力）と lab/*_log.json を読むだけなので、
ComfyUI もモデルも無しで描き直せる。生成画像の WebP と冒頭の並べた図は lab/to_webp.py が作る。

    uv run --with matplotlib==3.10.7 python figures.py
"""

import json
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
LAB = HERE / "lab"
IMAGES = HERE / "images"
INK, SUB, BLUE, OCHRE = "#1f1f1f", "#666666", "#7aa6c2", "#d4a24c"
BLUE_F, OCHRE_F, NEUTRAL = "#eaf1f5", "#f8eed8", "#f2f2f2"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"


def pipeline_figure():
    """プロンプト → text encoder、ノイズ → UNet とサンプラーの繰り返し → VAE decoder → 画像。"""
    w, h = 960, 540
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img">'
         f'<title>{escape("SDXL で 1 枚を描く時の部品の流れ")}</title>',
         f'<style>text{{font-family:{FONT};fill:{INK}}} .sub{{fill:{SUB}}}</style>',
         f'<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" '
         f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 Z" fill="{SUB}"/></marker></defs>',
         f'<rect width="{w}" height="{h}" fill="#ffffff"/>']

    def box(x, y, bw, bh, fill, stroke, lines, size=24, dash=False):
        d = ' stroke-dasharray="6 5"' if dash else ""
        p.append(f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" rx="10" fill="{fill}" '
                 f'stroke="{stroke}" stroke-width="2.5"{d}/>')
        n = len(lines)
        for i, (s, cls) in enumerate(lines):
            ty = y + bh / 2 + (i - (n - 1) / 2) * (size + 8) + size * 0.35
            c = f' class="{cls}"' if cls else ""
            sz = size if not cls else size - 3
            p.append(f'<text x="{x + bw / 2}" y="{ty:.1f}" font-size="{sz}" text-anchor="middle"{c}>{escape(s)}</text>')

    def arrow(x1, y1, x2, y2):
        p.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{SUB}" stroke-width="2.5" marker-end="url(#a)"/>')

    # 上段: プロンプトから条件まで（黄土）
    box(30, 40, 230, 90, NEUTRAL, SUB, [("プロンプト", ""), ("lighthouse, ocean...", "sub")])
    arrow(262, 85, 318, 85)
    box(320, 40, 300, 90, OCHRE_F, OCHRE, [("text encoder", ""), ("CLIP ViT-L と bigG", "sub")])
    arrow(470, 132, 470, 218)
    p.append(f'<text x="484" y="182" font-size="21" class="sub">語ごとのベクトル</text>')

    # 中段: 潜在の上での繰り返し（青）
    p.append(f'<rect x="150" y="220" width="640" height="200" rx="14" fill="none" stroke="{BLUE}" stroke-width="2.5"/>')
    p.append(f'<text x="170" y="252" font-size="22" class="sub">潜在 128 × 128 × 4 の上で 28 回</text>')
    box(190, 275, 260, 110, BLUE_F, BLUE, [("UNet", ""), ("ノイズを予測", "sub")])
    box(500, 275, 260, 110, BLUE_F, BLUE, [("サンプラー", ""), ("次の sigma まで引く", "sub")])
    arrow(452, 315, 498, 315)
    arrow(498, 350, 452, 350)

    # 入口: seed のノイズ、出口: VAE decoder
    box(20, 445, 260, 75, NEUTRAL, SUB, [("seed のノイズ", ""), ("sigma 14.6 倍", "sub")], size=22)
    arrow(150, 443, 220, 389)
    box(560, 445, 200, 75, NEUTRAL, SUB, [("VAE decoder", "")], size=24)
    arrow(700, 389, 660, 443)
    arrow(762, 482, 808, 482)
    box(810, 425, 130, 95, NEUTRAL, SUB, [("画像", ""), ("1024²", "sub")], size=24)

    p.append("</svg>")
    (IMAGES / "diffusion_pipeline.svg").write_text("\n".join(p) + "\n")


def schedule_figure():
    """normal と karras の 28 ステップの sigma、右に画像の割合 1/sqrt(1+sigma^2)。"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    s = json.loads((LAB / "schedule.json").read_text())
    plt.rcParams.update({"font.family": ["Noto Sans CJK JP", "sans-serif"], "font.size": 13,
                         "axes.edgecolor": SUB, "axes.labelcolor": INK, "xtick.color": SUB,
                         "ytick.color": SUB, "svg.fonttype": "none"})
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.6, 4.0), facecolor="#ffffff")
    ks = list(range(s["steps"] + 1))
    for name, color, mark in (("normal", BLUE, "o"), ("karras", OCHRE, "s")):
        sig = s[name]
        a1.plot(ks, sig, color=color, marker=mark, ms=4, lw=2, label=name)
        a2.plot(ks, [1 / (1 + x * x) ** 0.5 for x in sig], color=color, marker=mark, ms=4, lw=2, label=name)
    a1.set_title("sigma（ノイズの大きさ）", color=INK, fontsize=14)
    a2.set_title("画像に掛かる係数 1/sqrt(1+σ²)", color=INK, fontsize=14)
    for a in (a1, a2):
        a.set_xlabel("ステップ k（28 ステップ）")
        a.grid(color="#dddddd", lw=0.8)
        a.spines[["top", "right"]].set_visible(False)
        a.legend(frameon=False)
    a2.set_ylim(0, 1.05)
    fig.tight_layout()
    fig.savefig(IMAGES / "diffusion_schedule.svg", facecolor="#ffffff")


def main():
    IMAGES.mkdir(exist_ok=True)
    pipeline_figure()
    schedule_figure()


if __name__ == "__main__":
    main()
