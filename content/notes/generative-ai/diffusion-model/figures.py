"""Diffusion Model のノートの図を作る。

全体の流れの図は Python 標準ライブラリだけで SVG を組み、Chrome の headless で PNG にしてから
WebP にする。σ と係数のグラフは matplotlib で PNG にしてから WebP にする。
どれも lab/schedule.json（lab/schedule.py の出力）と images/fwd_*.webp を読むだけなので、
ComfyUI もモデルも無しで描き直せる。生成画像の WebP と冒頭の並べた図は lab/to_webp.py が作る。
images/ には WebP だけを置く。

    uv run --with matplotlib==3.10.7 --with pillow==12.0.0 python figures.py
"""

import json
import subprocess
import tempfile
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
LAB = HERE / "lab"
IMAGES = HERE / "images"
INK, SUB, BLUE, OCHRE = "#1f1f1f", "#666666", "#7aa6c2", "#d4a24c"
BLUE_F, OCHRE_F, NEUTRAL = "#eaf1f5", "#f8eed8", "#f2f2f2"
FONT = "'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif"


def png_to_webp(png, name):
    from PIL import Image
    Image.open(png).convert("RGB").save(IMAGES / name, "WEBP", quality=90, method=6)


def svg_to_webp(svg, w, h, name):
    """SVG の文字列を Chrome の headless で 2 倍の PNG にし、WebP で保存する。"""
    with tempfile.TemporaryDirectory() as d:
        html = Path(d) / "fig.html"
        png = Path(d) / "fig.png"
        html.write_text(f'<!doctype html><html><body style="margin:0;background:#fff">{svg}</body></html>')
        subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--hide-scrollbars",
                        "--force-device-scale-factor=2", f"--window-size={w},{h}",
                        f"--screenshot={png}", html.as_uri()], check=True, capture_output=True)
        png_to_webp(png, name)


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
    box(320, 40, 300, 90, OCHRE_F, OCHRE, [("テキストエンコーダー", ""), ("CLIP ViT-L と bigG", "sub")])
    arrow(470, 132, 470, 218)
    p.append(f'<text x="484" y="182" font-size="21" class="sub">語ごとのベクトル</text>')

    # 中段: 潜在の上での繰り返し（青）
    p.append(f'<rect x="150" y="220" width="640" height="200" rx="14" fill="none" stroke="{BLUE}" stroke-width="2.5"/>')
    p.append(f'<text x="170" y="252" font-size="22" class="sub">潜在 128 × 128 × 4 の上で 28 回</text>')
    box(190, 275, 260, 110, BLUE_F, BLUE, [("UNet", ""), ("ノイズを予測", "sub")])
    box(500, 275, 260, 110, BLUE_F, BLUE, [("サンプラー", ""), ("次の σ まで引く", "sub")])
    arrow(452, 315, 498, 315)
    arrow(498, 350, 452, 350)

    # 入口: seed のノイズ、出口: VAE decoder
    box(20, 445, 260, 75, NEUTRAL, SUB, [("seed のノイズ", ""), ("最初の状態", "sub")], size=22)
    arrow(150, 443, 190, 423)
    box(560, 445, 200, 75, NEUTRAL, SUB, [("VAE の", ""), ("デコーダー", "")], size=22)
    arrow(700, 389, 660, 443)
    arrow(762, 482, 808, 482)
    box(810, 425, 130, 95, NEUTRAL, SUB, [("画像", ""), ("1024²", "sub")], size=24)

    p.append("</svg>")
    svg_to_webp("\n".join(p), w, h, "diffusion_pipeline.webp")


def schedule_figure():
    """normal と karras の 28 ステップの σ、右に画像に掛かる係数 1/sqrt(1+σ²)。"""
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
        a1.plot(ks[:-1], sig[:-1], color=color, marker=mark, ms=4, lw=2, label=name)
        a2.plot(ks, [1 / (1 + x * x) ** 0.5 for x in sig], color=color, marker=mark, ms=4, lw=2, label=name)
    a1.set_title("σ（ノイズの大きさ、対数目盛）", color=INK, fontsize=14)
    a1.set_yscale("log")
    a2.set_title("画像に掛かる係数 1/sqrt(1+σ²)", color=INK, fontsize=14)
    for a in (a1, a2):
        a.set_xlabel("ステップ k（28 ステップ）")
        a.grid(color="#dddddd", lw=0.8)
        a.spines[["top", "right"]].set_visible(False)
        a.legend(frameon=False)
    a2.set_ylim(0, 1.05)
    fig.tight_layout()
    with tempfile.TemporaryDirectory() as d:
        png = Path(d) / "schedule.png"
        fig.savefig(png, dpi=200, facecolor="#ffffff")
        png_to_webp(png, "diffusion_schedule.webp")
    plt.close(fig)


def noise_mix_figure():
    """σ を横軸に、画像とノイズに掛かる係数。上に、その σ でノイズを足した画像を並べる。"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import ConnectionPatch
    from PIL import Image

    forward = json.loads((LAB / "forward_log.json").read_text())[0]
    shots = sorted(zip(forward["sigmas"], forward["js"]))          # σ の小さい順
    plt.rcParams.update({"font.family": ["Noto Sans CJK JP", "sans-serif"], "font.size": 13,
                         "axes.edgecolor": SUB, "axes.labelcolor": INK, "xtick.color": SUB,
                         "ytick.color": SUB})
    n = len(shots)
    fig = plt.figure(figsize=(10.0, 5.6), facecolor="#ffffff")
    gs = fig.add_gridspec(2, n, height_ratios=[1.0, 2.1], hspace=0.32, wspace=0.08,
                          left=0.08, right=0.98, top=0.93, bottom=0.11)
    ax = fig.add_subplot(gs[1, :])
    xs = [0.02 * (1000 ** (i / 400)) for i in range(401)]
    ax.plot(xs, [1 / (1 + x * x) ** 0.5 for x in xs], color=OCHRE, lw=2.5, label="画像に掛かる係数 1 / sqrt(1 + σ²)")
    ax.plot(xs, [x / (1 + x * x) ** 0.5 for x in xs], color=BLUE, lw=2.5, ls="--", label="ノイズに掛かる係数 σ / sqrt(1 + σ²)")
    ax.set_xscale("log")
    ax.set_xlim(0.02, 20)
    ax.set_ylim(0, 1.08)
    ax.set_xlabel("σ（ノイズの大きさ、対数目盛）")
    ax.grid(color="#dddddd", lw=0.8)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, loc="center left", fontsize=12)
    for i, (sig, j) in enumerate(shots):
        c = 1 / (1 + sig * sig) ** 0.5
        ax.plot([sig], [c], marker="o", color=INK, ms=6, zorder=5)
        im = fig.add_subplot(gs[0, i])
        im.imshow(Image.open(IMAGES / f"fwd_{j:02d}.webp"))
        im.set_xticks([]); im.set_yticks([])
        for sp in im.spines.values():
            sp.set_edgecolor("#cccccc")
        im.set_title(f"σ {sig:.2f}", fontsize=12, color=INK, pad=4)
        fig.add_artist(ConnectionPatch(xyA=(0.5, 0), coordsA=im.transAxes, xyB=(sig, c), coordsB=ax.transData,
                                       color="#aaaaaa", lw=1))
    with tempfile.TemporaryDirectory() as d:
        png = Path(d) / "mix.png"
        fig.savefig(png, dpi=200, facecolor="#ffffff")
        png_to_webp(png, "diffusion_noise_mix.webp")
    plt.close(fig)


def euler_step_figure():
    """euler の 1 ステップ: x から予測 x0_hat へ向かう直線の上を、次の σ まで進む。2 ステップ分。"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"font.family": ["Noto Sans CJK JP", "sans-serif"], "font.size": 13,
                         "axes.edgecolor": SUB, "axes.labelcolor": INK, "xtick.color": SUB,
                         "ytick.color": SUB})
    fig, ax = plt.subplots(figsize=(9.6, 4.4), facecolor="#ffffff")
    s0, s1, s2 = 6.0, 3.6, 1.8                      # 説明用の σ（実測値ではない）
    x0, p0, p1 = 5.0, 1.2, 2.4                      # 状態の位置と、1 回目・2 回目の予測 x0_hat
    x1 = p0 + (x0 - p0) * s1 / s0                   # x0_hat + σ1 × eps_hat
    x2 = p1 + (x1 - p1) * s2 / s1
    for (sa, xa, pr, sb, xb, col, lab) in ((s0, x0, p0, s1, x1, BLUE, "1"), (s1, x1, p1, s2, x2, OCHRE, "2")):
        ax.plot([sa, 0], [xa, pr], color=col, lw=1.6, ls=":")
        ax.annotate("", xy=(sb, xb), xytext=(sa, xa),
                    arrowprops=dict(arrowstyle="-|>", color=col, lw=2.8, mutation_scale=18))
        ax.plot([0], [pr], marker="s", color=col, ms=9, zorder=5)
        ax.text(0.25, pr - 0.3, f"{lab} 回目の予測 x0_hat", va="center", ha="right", fontsize=12, color=INK)
    ax.plot([s0, s1, s2], [x0, x1, x2], "o", color=INK, ms=7, zorder=6)
    ax.text(s0 + 0.1, x0 + 0.15, r"今の状態 x（$\sigma_i$）", fontsize=12, color=INK)
    ax.text(s1 + 0.1, x1 + 0.2, r"次の状態（$\sigma_{i+1}$）", fontsize=12, color=INK)
    ax.text(s2 + 0.1, x2 + 0.2, r"その次（$\sigma_{i+2}$）", fontsize=12, color=INK)
    ax.set_xlim(6.9, -0.2)                          # 生成は σ の大きい側から小さい側へ進むので左から右へ
    ax.set_ylim(0.6, 5.7)
    ax.set_xlabel("σ（ノイズの大きさ。生成は左から右へ進む）")
    ax.set_ylabel("状態（説明用の 1 次元）")
    ax.set_xticks([s0, s1, s2, 0], [r"$\sigma_i$", r"$\sigma_{i+1}$", r"$\sigma_{i+2}$", "0"])
    ax.text(6.6, 1.5, "点線：今の状態から予測 x0_hat へ向かう直線（傾きは予測したノイズ eps_hat）", fontsize=12, color=SUB)
    ax.set_yticks([])
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="x", color="#dddddd", lw=0.8)
    fig.tight_layout()
    with tempfile.TemporaryDirectory() as d:
        png = Path(d) / "euler.png"
        fig.savefig(png, dpi=200, facecolor="#ffffff")
        png_to_webp(png, "diffusion_euler_step.webp")
    plt.close(fig)


def main():
    IMAGES.mkdir(exist_ok=True)
    pipeline_figure()
    schedule_figure()
    noise_mix_figure()
    euler_step_figure()


if __name__ == "__main__":
    main()
