"""Generate the figures of the video upscale note.

python3 figures.py <作業ディレクトリ>
  <作業ディレクトリ> は lab/prepare.py と lab/upscale.py が作ったフレームの置き場所
  （gt/ と out/<方式>_<入力>/）。数値のグラフは lab/metrics.json から描く。
"""
import json
import subprocess
from html import escape
import sys
import tempfile
from pathlib import Path

import matplotlib
import numpy as np
from PIL import Image, ImageDraw, ImageFont

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE / "images"
WORK = Path(sys.argv[1]) if len(sys.argv) > 1 else None
FONT_PATH = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
INK, SUB = "#1f1f1f", "#666666"
BLUE, OCHRE, GRAY = "#7aa6c2", "#d4a24c", "#bdbdbd"

# 比べる 2 フレームと、拡大して見せる範囲（640x360 の上の座標）
T0, T1 = "020.png", "021.png"
CROP = (384, 104, 784, 329)   # 400x225（1024x576 の上の座標）


def font(size):
    return ImageFont.truetype(FONT_PATH, size, index=0)


def load(d, name):
    return Image.open(WORK / d / name).convert("RGB")


def labeled_row(tiles, labels, scale=1, pad=12, label_h=40):
    """同じ大きさの画像を横に並べ、上にラベルを付けた 1 枚の画像を作る。"""
    w, h = tiles[0].width * scale, tiles[0].height * scale
    canvas = Image.new("RGB", (len(tiles) * w + (len(tiles) + 1) * pad, h + label_h + pad), "white")
    draw = ImageDraw.Draw(canvas)
    for k, (tile, label) in enumerate(zip(tiles, labels)):
        x = pad + k * (w + pad)
        canvas.paste(tile.resize((w, h), Image.Resampling.NEAREST), (x, label_h))
        draw.text((x + w / 2, label_h / 2), label, fill=INK, font=font(22), anchor="mm")
    return canvas


def diff_figure():
    """隣り合う 2 フレームの差の絶対値を 8 倍して白黒で見せる。正解は動いた所だけが光る。"""
    runs = [("gt", "正解"), ("out/bicubic_noisy", "bicubic"),
            ("out/gan_noisy", "Real-ESRGAN"), ("out/diffusion_noisy", "拡散モデルで描き直し")]
    tiles = []
    for d, _ in runs:
        a = np.asarray(load(d, T0).convert("L"), dtype=np.float64)
        b = np.asarray(load(d, T1).convert("L"), dtype=np.float64)
        diff = np.clip(np.abs(b - a) * 8, 0, 255).astype(np.uint8)
        tiles.append(Image.fromarray(diff).convert("RGB").crop(CROP))
    img = labeled_row(tiles, [label for _, label in runs])
    img.save(OUT / "video-upscale_diff.webp", quality=90)


def frame_figure():
    """同じフレームの同じ範囲を、正解と各方式で並べる。"""
    runs = [("gt", "正解"), ("out/bicubic_noisy", "bicubic"),
            ("out/gan_noisy", "Real-ESRGAN"), ("out/diffusion_noisy", "拡散モデルで描き直し")]
    tiles = [load(d, T0).crop(CROP) for d, _ in runs]
    img = labeled_row(tiles[:2], [label for _, label in runs[:2]])
    img2 = labeled_row(tiles[2:], [label for _, label in runs[2:]])
    both = Image.new("RGB", (img.width, img.height + img2.height), "white")
    both.paste(img, (0, 0))
    both.paste(img2, (0, img.height))
    both.save(OUT / "video-upscale_frames.webp", quality=90)


def input_figure():
    """拡大の前の入力（256x144）を 4 倍に並べて見せる。ノイズと圧縮の影響が見える。"""
    box = tuple(v // 4 for v in CROP)
    tiles = [load(d, T0).crop(box) for d in ["clean", "noisy"]]
    img = labeled_row(tiles, ["入力（ノイズ無し）", "入力（ノイズ有り）"], scale=4)
    img.save(OUT / "video-upscale_inputs.webp", quality=90)


def metrics_figure():
    m = json.loads((HERE / "lab" / "metrics.json").read_text())
    runs = m["runs"]
    plt.rcParams.update({
        "font.family": "Noto Sans CJK JP", "font.size": 10, "axes.edgecolor": SUB,
        "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK, "text.color": INK,
        "svg.fonttype": "path", "svg.hashsalt": "video-upscale",
        "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
    })
    methods = [("bicubic", "bicubic"), ("animevideo", "animevideov3"), ("gan", "x4plus\nanime_6B"),
               ("diffusion", "6B +\n描き直し")]
    inputs = [("clean", "ノイズ無し", GRAY), ("noisy", "ノイズ有り", OCHRE),
              ("denoised", "除去後", BLUE)]
    fig, axes = plt.subplots(1, 2, figsize=(7.6, 3.4))
    panels = [("flicker", "静止した画素の変化（輝度）", m["gt_flicker"]),
              ("excess", "動きで説明できない変化（輝度）", 0.0)]
    for ax, (key, title, ref) in zip(axes, panels):
        for j, (inp, label, color) in enumerate(inputs):
            xs = [i + (j - 1) * 0.26 for i in range(len(methods))]
            pairs = [(x, runs[f"{mt}_{inp}"][key]) for x, (mt, _) in zip(xs, methods)
                     if f"{mt}_{inp}" in runs]
            bars = ax.bar([x for x, _ in pairs], [v for _, v in pairs], 0.25, color=color,
                          label=label if key == "flicker" else None)
            for b, (_, v) in zip(bars, pairs):
                ax.text(b.get_x() + b.get_width() / 2, v + 0.05, f"{v:.1f}", ha="center", fontsize=7)
        if ref:
            ax.axhline(ref, color=SUB, lw=1, ls="--")
            ax.text(3.45, ref + 0.04, "正解", ha="right", fontsize=8, color=SUB)
        ax.set_title(title, fontsize=10)
        ax.set_xticks(range(len(methods)), [label for _, label in methods])
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].legend(loc="upper left", frameon=False, fontsize=8)
    top = max(v[k] for v in runs.values() for k in ("flicker", "excess")) * 1.25
    for ax in axes:
        ax.set_ylim(0, top)
    fig.tight_layout()
    with tempfile.TemporaryDirectory() as tmp:
        png = Path(tmp) / "fig.png"
        fig.savefig(png, dpi=200)
        Image.open(png).convert("RGB").save(OUT / "video-upscale_metrics.webp", "WEBP", quality=90,
                                            method=6)


def vsr_figure():
    """1 枚ずつの拡大と、BasicVSR のように前後のフレームの情報を双方向に伝える動画用の超解像の違い（概念図）。"""
    w, h = 1040, 430
    pale_gray, pale_blue, pale_ochre, line = "#f2f2f2", "#eaf1f5", "#f8eed8", "#999999"
    fnt = "'Noto Sans CJK JP','Hiragino Sans',sans-serif"
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img">'
         '<title>左は 1 枚ずつの拡大で、各フレームは隣を見ずに拡大される。右は動画用の超解像で、'
         '前向きと後ろ向きに特徴を伝え、前後のフレームで見た情報を合わせて拡大する</title>',
         f'<style>text{{font-family:{fnt};fill:{INK}}} .sub{{fill:{SUB}}}</style>',
         f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
         '<defs>'
         f'<marker id="g" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">'
         f'<path d="M0,0 L10,5 L0,10 z" fill="{SUB}"/></marker>'
         f'<marker id="b" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">'
         f'<path d="M0,0 L10,5 L0,10 z" fill="{BLUE}"/></marker>'
         f'<marker id="o" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">'
         f'<path d="M0,0 L10,5 L0,10 z" fill="{OCHRE}"/></marker></defs>']

    def text(x, y, t, size=18, anchor="middle", cls=""):
        c = f' class="{cls}"' if cls else ""
        p.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}"{c}>{escape(t)}</text>')

    def box(x, y, bw, bh, fill, stroke):
        p.append(f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" rx="6" fill="{fill}" stroke="{stroke}" '
                 'stroke-width="2"/>')

    def arrow(x1, y1, x2, y2, marker="g", color=SUB):
        p.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="2" '
                 f'marker-end="url(#{marker})"/>')

    names = ["t − 1", "t", "t + 1"]
    # 左: 1 枚ずつ
    text(30, 40, "1 枚ずつの拡大", 22, anchor="start")
    for k, n in enumerate(names):
        x = 40 + k * 150
        box(x, 70, 110, 56, pale_gray, line)
        text(x + 55, 104, f"入力 {n}", 18)
        arrow(x + 55, 128, x + 55, 278)
        text(x + 64, 210, "拡大", 16, anchor="start", cls="sub")
        box(x, 282, 110, 56, pale_gray, line)
        text(x + 55, 316, f"出力 {n}", 18)
    text(255, 404, "フレームどうしの線が無い。隣で何を描いたかを知らない", 16, cls="sub")
    # 右: 双方向に伝える
    ox = 540
    text(ox, 40, "動画用の超解像（BasicVSR）", 22, anchor="start")
    for k, n in enumerate(names):
        x = ox + 10 + k * 170
        box(x, 70, 130, 56, pale_gray, line)
        text(x + 65, 104, f"入力 {n}", 18)
        arrow(x + 65, 128, x + 65, 166)
        box(x, 170, 130, 70, pale_blue, BLUE)
        text(x + 65, 200, "特徴", 18)
        text(x + 65, 226, "（位置を合わせる）", 14, cls="sub")
        arrow(x + 65, 242, x + 65, 278)
        text(x + 74, 266, "拡大", 14, anchor="start", cls="sub")
        box(x, 282, 130, 56, pale_gray, line)
        text(x + 65, 316, f"出力 {n}", 18)
        if k < 2:
            arrow(x + 132, 188, x + 168, 188, "b", BLUE)
            arrow(x + 168, 222, x + 132, 222, "o", OCHRE)
    text(ox + 250, 372, "どちらの向きも、光学フローで位置を合わせて伝える（青: 前向き　黄: 後ろ向き）", 14, cls="sub")
    text(ox + 250, 404, "前後のフレームで見た情報を合わせて、同じ物を同じように描く", 16, cls="sub")
    p.append("</svg>")
    with tempfile.TemporaryDirectory() as tmp:
        svg, png = Path(tmp) / "fig.svg", Path(tmp) / "fig.png"
        svg.write_text("\n".join(p) + "\n", encoding="utf-8")
        subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--hide-scrollbars",
                        "--force-device-scale-factor=2", f"--window-size={w},{h}",
                        f"--screenshot={png}", svg.as_uri()], check=True, capture_output=True)
        Image.open(png).convert("RGB").save(OUT / "video-upscale_vsr.webp", "WEBP", quality=90, method=6)


def video():
    """正解・bicubic・Real-ESRGAN・拡散モデルで描き直し（いずれもノイズ有りの入力）を 2x2 に並べた WebM。"""
    runs = [("gt", "正解"), ("out/bicubic_noisy", "bicubic"),
            ("out/gan_noisy", "Real-ESRGAN"), ("out/diffusion_noisy", "拡散モデルで描き直し")]
    names = sorted(p.name for p in (WORK / "gt").glob("*.png"))
    with tempfile.TemporaryDirectory() as tmp:
        for k, name in enumerate(names):
            tiles = [load(d, name).crop(CROP) for d, _ in runs]
            top = labeled_row(tiles[:2], [label for _, label in runs[:2]], label_h=34)
            bottom = labeled_row(tiles[2:], [label for _, label in runs[2:]], label_h=34)
            frame = Image.new("RGB", (top.width, top.height + bottom.height), "white")
            frame.paste(top, (0, 0))
            frame.paste(bottom, (0, top.height))
            frame.save(Path(tmp) / f"{k:03d}.png")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", "24", "-stream_loop", "2",
                        "-i", str(Path(tmp) / "%03d.png"), "-c:v", "libvpx-vp9", "-b:v", "0",
                        "-crf", "30", "-pix_fmt", "yuv420p", "-an",
                        str(OUT / "video-upscale_compare.webm")], check=True)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    metrics_figure()
    vsr_figure()
    if WORK:
        diff_figure()
        frame_figure()
        input_figure()
        video()
