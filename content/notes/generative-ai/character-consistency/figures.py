"""Character Consistency ノートの図を作る。

  uv run --with matplotlib==3.11.2 --with numpy==2.5.4 --with pillow==13.0.0 python figures.py

lab/metrics.json（metrics.py の出力）を読む。ComfyUI は不要。概念図は SVG を組んで Chrome で描く。図は WebP で images/ に置く。
"""
import io
import json
import itertools
import subprocess
import tempfile
from html import escape
from pathlib import Path

import matplotlib
import numpy as np
from PIL import Image

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).parent
OUT = HERE / "images"
BLUE, OCHRE, GREEN, RED = "#7aa6c2", "#d4a24c", "#8fae86", "#e15759"
INK, SUB = "#1f1f1f", "#666666"
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "svg.fonttype": "path", "font.size": 12,
                     "text.color": INK, "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK,
                     "axes.edgecolor": SUB})

M = json.load(open(HERE / "lab" / "metrics.json"))

# 上から下へ: 物差しの目盛り → プロンプトだけ → 手段
GROUPS = [
    ("別人（金髪・青い目）", ["other_0", "other_1"], "#bdbdbd"),
    ("同じプロンプト・seed だけ変える", ["seed_0", "seed_1", "seed_2"], OCHRE),
    ("seed 固定・場面の語だけ変える", ["fixed_smile", "fixed_wave", "fixed_cafe"], OCHRE),
    ("場面の語と seed を変える", ["newseed_smile", "newseed_wave", "newseed_cafe"], OCHRE),
    ("基準の骨格で縛る（ControlNet）", ["pose_1", "pose_2"], GREEN),
    ("参照画像（IP-Adapter）", ["ipa35s0_smile", "ipa50_smile", "ipa50_wave", "ipa50_cafe", "ipa60s3_smile",
                          "ipa80_smile", "ipa80_wave", "ipa80_cafe", "redraw_wave", "redraw_cafe"], BLUE),
    ("基準から img2img（0.5・0.7）", ["i2i50_smile", "i2i50_wave", "i2i50_cafe", "i2i70_smile", "i2i70_wave",
                                 "i2i70_cafe"], BLUE),
    ("基準から img2img（0.85）", ["i2i85_wave", "i2i85_cafe"], BLUE),
]


def png_to_webp(fig, name):
    """matplotlib の図を PNG（dpi 200）に描き、WebP にして images/ に置く。"""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, facecolor="#ffffff", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    Image.open(buf).convert("RGB").save(OUT / name, "WEBP", quality=90, method=6)


def metrics_figure():
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.6), sharey=True)
    keys = [("face_clip", "顔の CLIP 埋め込みの近さ（cos）", (0.65, 1.0)),
            ("face_tags", "顔のタグの一致（Jaccard）", (0.0, 1.0))]
    ys = np.arange(len(GROUPS))[::-1]
    for ax, (key, label, lim) in zip(axes, keys):
        for y, (_, names, color) in zip(ys, GROUPS):
            vals = [M[n][key] for n in names]
            jitter = np.linspace(-0.18, 0.18, len(vals)) if len(vals) > 1 else [0]
            ax.scatter(vals, y + np.array(jitter), s=34, color=color, edgecolor=INK, linewidth=0.5, zorder=3)
            ax.plot([np.mean(vals)] * 2, [y - 0.3, y + 0.3], color=INK, linewidth=1.4, zorder=4)
        base = M["base"][key]
        ax.axvline(base, color=SUB, linestyle=":", linewidth=1)
        ax.set_xlim(*lim)
        ax.set_title(label, fontsize=12, color=INK)
        ax.grid(axis="x", color="#e6e6e6", linewidth=0.8)
        ax.set_axisbelow(True)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
    axes[0].set_yticks(ys, [g[0] for g in GROUPS])
    png_to_webp(fig, "metrics.webp")


def routes_figure():
    """生成の流れ（ノイズ → 28 ステップ → 絵）と、各手段が入る口。SVG を Chrome で WebP にする。"""
    w, h = 1040, 470
    pale = {"ochre": "#f8eed8", "blue": "#eaf1f5", "green": "#eef3ec", "gray": "#f2f2f2"}
    edge = {"ochre": OCHRE, "blue": BLUE, "green": GREEN, "gray": "#999999"}
    fnt = "'Noto Sans CJK JP','Hiragino Sans',sans-serif"
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img">'
         '<title>最初のノイズからステップを繰り返して絵を描く流れに、seed・img2img・プロンプト・IP-Adapter・'
         'ControlNet・LoRA がどこから入るか</title>',
         f'<style>text{{font-family:{fnt};fill:{INK}}} .sub{{fill:{SUB}}}</style>',
         f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
         f'<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
         f'orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{SUB}"/></marker></defs>']

    def text(x, y, t, size=18, anchor="middle", cls=""):
        c = f' class="{cls}"' if cls else ""
        p.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}"{c}>{escape(t)}</text>')

    def box(x, y, bw, bh, kind):
        p.append(f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" rx="8" fill="{pale[kind]}" '
                 f'stroke="{edge[kind]}" stroke-width="2"/>')

    def arrow(x1, y1, x2, y2):
        p.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{SUB}" stroke-width="2" '
                 'marker-end="url(#a)"/>')

    # 中央の流れ
    box(40, 190, 190, 90, "gray")
    text(135, 230, "最初のノイズ", 20)
    text(135, 258, "（乱数の画像）", 15, cls="sub")
    box(330, 175, 380, 120, "gray")
    text(520, 220, "モデルがノイズを少しずつ取り除く", 19)
    text(520, 252, "（ステップを 28 回くり返す）", 15, cls="sub")
    box(810, 190, 190, 90, "gray")
    text(905, 242, "絵", 22)
    arrow(232, 235, 326, 235)
    arrow(712, 235, 806, 235)
    # 上から入るもの
    box(40, 30, 190, 80, "ochre")
    text(135, 64, "seed", 19)
    text(135, 92, "ノイズのシード値", 15, cls="sub")
    arrow(135, 112, 135, 186)
    box(300, 30, 200, 80, "ochre")
    text(400, 64, "プロンプト", 19)
    text(400, 92, "各ステップの条件", 15, cls="sub")
    arrow(400, 112, 430, 171)
    box(540, 30, 200, 80, "blue")
    text(640, 64, "IP-Adapter", 19)
    text(640, 92, "参照画像の特徴を条件に", 15, cls="sub")
    arrow(640, 112, 610, 171)
    # 下から入るもの
    box(40, 360, 190, 80, "blue")
    text(135, 394, "img2img", 19)
    text(135, 422, "下絵＋ノイズから始める", 15, cls="sub")
    arrow(135, 358, 135, 284)
    box(300, 360, 200, 80, "gray")
    text(400, 394, "LoRA", 19)
    text(400, 422, "モデルの重みに足す", 15, cls="sub")
    arrow(400, 358, 430, 299)
    box(540, 360, 200, 80, "green")
    text(640, 394, "ControlNet", 19)
    text(640, 422, "骨格などの形の条件", 15, cls="sub")
    arrow(640, 358, 610, 299)
    p.append("</svg>")
    with tempfile.TemporaryDirectory() as tmp:
        svg, png = Path(tmp) / "fig.svg", Path(tmp) / "fig.png"
        svg.write_text("\n".join(p) + "\n", encoding="utf-8")
        subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--hide-scrollbars",
                        "--force-device-scale-factor=2", f"--window-size={w},{h}",
                        f"--screenshot={png}", svg.as_uri()], check=True, capture_output=True)
        Image.open(png).convert("RGB").save(OUT / "routes.webp", "WEBP", quality=90, method=6)


def pairwise(names, key):
    """組の中の総当たりの近さ（顔の埋め込みの cos と、顔のタグの Jaccard）。"""
    out = []
    for a, b in itertools.combinations(names, 2):
        if key == "face_clip":
            out.append(float(np.dot(M[a]["emb"], M[b]["emb"])))
        else:
            x, y = set(M[a]["face_tag_list"]), set(M[b]["face_tag_list"])
            out.append(len(x & y) / len(x | y))
    return out


def main():
    OUT.mkdir(exist_ok=True)
    metrics_figure()
    routes_figure()
    lora = ["seed_0", "seed_1", "seed_2", "base"]
    nolora = ["nolora_0", "nolora_1", "nolora_2", "nolora_3"]
    for label, names in (("画風 LoRA あり", lora), ("画風 LoRA なし", nolora)):
        c, t = pairwise(names, "face_clip"), pairwise(names, "face_tags")
        print(f"{label}: 顔の CLIP の近さ 平均 {np.mean(c):.3f}（{min(c):.3f}〜{max(c):.3f}）、"
              f"顔のタグの一致 平均 {np.mean(t):.3f}（{min(t):.3f}〜{max(t):.3f}）")
    for _, names, _ in GROUPS:
        print(", ".join(f"{n} clip={M[n]['face_clip']:.3f} tags={M[n]['face_tags']:.3f} sat={M[n]['saturation']:.3f}"
                        for n in names))
    print("base sat", M["base"]["saturation"])


if __name__ == "__main__":
    main()
