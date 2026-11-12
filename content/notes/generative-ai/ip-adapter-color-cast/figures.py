"""IP-Adapter の参照で色が転ぶ話のノートの図を作る。

- ipa_cover.webp: 緑の背景の参照、参照なし、参照画像を 1 段目に linear で使った絵
- ipa_read.webp: 透明な参照を ComfyUI が読んだ絵と、画像エンコーダーが見る 224 x 224 の区画
- ipa_layers.webp: SDXL で参照が入る 11 か所と、linear・style transfer precise が使う所
- ipa_grid.webp: 銀の参照で、段（行）× 背景と型（列）を変えた絵（seed 20261113）
- ipa_metrics.webp: 人物の彩度と、背景と白の差（銀の参照、各 3 seed）
- ipa_blank.webp: 人物のいない真っ白・真っ緑の 1 枚を参照にした 1 段目
- ipa_weight.webp: 重み 0.3・0.6・0.9
- ipa_want.webp: 青い陣羽織の参照を 1 段目と 2 段目で使った絵

    uv run --with pillow==12.0.0 --with matplotlib==3.9.2 --with numpy==2.1.3 python figures.py <作業先>
作業先には lab の手順で作った ref/・ref_plain/・ref_blank/・gen/・gen_plain/・gen_blank/ がある。
計測の値は lab/metrics_*.json（measure.py の出力）を読む。
"""
import json
import sys
from pathlib import Path

import matplotlib
import numpy as np
from PIL import Image, ImageDraw, ImageFont

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402

HERE = Path(__file__).resolve().parent
LAB, IMAGES = HERE / "lab", HERE / "images"
IMAGES.mkdir(exist_ok=True)
CJK = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
font_manager.fontManager.addfont(CJK)
plt.rcParams["font.family"] = font_manager.FontProperties(fname=CJK).get_name()
INK, SUB, GRID = "#1f1f1f", "#666666", "#dddddd"
SEED = 20261113
SEEDS = (20261112, 20261113, 20261114)
CONDS = [("none", "参照なし"), ("white_stp", "白・precise"), ("white_linear", "白・linear"),
         ("black_stp", "黒・precise"), ("black_linear", "黒・linear"),
         ("green_stp", "緑・precise"), ("green_linear", "緑・linear")]
STAGES = {"s1": ("1 段目", "#4f81bd"), "s2": ("2 段目", "#e6a23c")}


def font(size):
    return ImageFont.truetype(CJK, size)


def to_webp(img, name):
    img.convert("RGB").save(IMAGES / name, "WEBP", quality=90, method=6)
    print("wrote", IMAGES / name)


def save_plot(fig, name):
    png = IMAGES / (name + ".png")
    fig.savefig(png, dpi=200, facecolor="#ffffff", bbox_inches="tight")
    plt.close(fig)
    to_webp(Image.open(png), name + ".webp")
    png.unlink()


def body(path, size=(300, 480)):
    """生成した 832 x 1216 の絵から、人物の周りを切り出して縮める。"""
    return Image.open(path).convert("RGB").crop((80, 96, 780, 1216)).resize(size, Image.LANCZOS)


def ref_body(path, size=(300, 480)):
    """正方形の参照（1216 x 1216）から、元の縦長の範囲の人物の周りを切り出す。"""
    return Image.open(path).convert("RGB").crop((192 + 80, 96, 192 + 780, 1216)).resize(size, Image.LANCZOS)


def grid(rows, row_labels, col_labels, gap=12, left=0, top=46, size=24):
    """rows は画像の 2 重のリスト。行の見出しは左、列の見出しは上に書く。"""
    w, h = rows[0][0].size
    ncol = len(rows[0])
    out = Image.new("RGB", (left + ncol * w + (ncol - 1) * gap, top + len(rows) * h + (len(rows) - 1) * gap), "white")
    d = ImageDraw.Draw(out)
    for j, lab in enumerate(col_labels):
        x = left + j * (w + gap)
        tw = d.textlength(lab, font=font(size))
        d.text((x + (w - tw) / 2, 6), lab, fill=INK, font=font(size))
    for i, row in enumerate(rows):
        y = top + i * (h + gap)
        if row_labels:
            d.text((8, y + h / 2 - size), row_labels[i], fill=INK, font=font(size))
        for j, im in enumerate(row):
            out.paste(im, (left + j * (w + gap), y))
    return out


def cover(work):
    ims = [ref_body(work / "ref_plain/green.png"), body(work / f"gen_plain/s1_none_{SEED}.png"),
           body(work / f"gen_plain/s1_green_linear_{SEED}.png")]
    to_webp(grid([ims], None, ["参照（背景は緑）", "参照なし", "参照画像を使った"], size=26), "ipa_cover.webp")


def read(work):
    """透明な参照（市松模様で表示）→ ComfyUI が読んだ絵 → 224 x 224 の 16 x 16 区画。"""
    side = 420
    rgba = Image.open(work / "ref_plain/clear_black.png").resize((side, side), Image.LANCZOS)
    checker = Image.new("RGB", (side, side), "white")
    cd = ImageDraw.Draw(checker)
    for y in range(0, side, 20):
        for x in range(0, side, 20):
            if (x // 20 + y // 20) % 2:
                cd.rectangle((x, y, x + 19, y + 19), fill="#cccccc")
    checker.paste(rgba, (0, 0), rgba)
    seen = Image.open(work / "ref_plain/read_clear_black.png").resize((side, side), Image.LANCZOS)  # LoadImage → SaveImage の出力
    small = Image.open(work / "ref_plain/clear_black.png").convert("RGB").resize((224, 224), Image.BICUBIC)
    mask = np.asarray(Image.open(work / "ref_plain/mask.png").resize((224, 224))) > 127
    person = mask.reshape(16, 14, 16, 14).any(axis=(1, 3))
    patches = small.resize((side, side), Image.NEAREST)
    pd = ImageDraw.Draw(patches, "RGBA")
    cell = side / 16
    for i in range(16):
        for j in range(16):
            box = (j * cell, i * cell, (j + 1) * cell, (i + 1) * cell)
            if not person[i, j]:
                pd.rectangle(box, fill=(70, 120, 200, 110))
            pd.rectangle(box, outline=(200, 200, 200, 255))
    labels = ["透明な参照（下の RGB は黒）", "ComfyUI が読んだ絵",
              f"224 x 224 の区画（青: 背景だけ {100 - person.mean() * 100:.0f}%）"]
    out = grid([[checker, seen, patches]], None, labels, gap=40, size=22)
    d = ImageDraw.Draw(out)
    for k in range(2):
        x = (k + 1) * side + k * 40 + 6
        d.polygon([(x, 46 + side / 2 - 10), (x + 26, 46 + side / 2), (x, 46 + side / 2 + 10)], fill=SUB)
    to_webp(out, "ipa_read.webp")


def layers():
    """SDXL の U-Net で参照が入る 11 か所（ComfyUI の transformer_index の順）。"""
    names = ["下り 1", "下り 2", "下り 3", "下り 4", "中央", "上り 1", "上り 2", "上り 3", "上り 4", "上り 5", "上り 6"]
    ys = [3, 3, 2, 2, 1, 2, 2, 2, 3, 3, 3]
    xs = list(range(11))
    fig, axes = plt.subplots(2, 1, figsize=(8.2, 4.4))
    for ax, (title, colors, marks) in zip(axes, [
        ("linear: 11 か所すべてに同じ重みで足す", ["#4f81bd"] * 11, {}),
        ("style transfer precise: 1 か所に足し、1 か所で遠ざける",
         ["#eeeeee"] * 3 + ["#e6a23c"] + ["#eeeeee"] * 2 + ["#4f81bd"] + ["#eeeeee"] * 4,
         {3: "配置（遠ざける）", 6: "色・質感"})]):
        ax.plot(xs, ys, color=GRID, zorder=1)
        for x, y, c, n in zip(xs, ys, colors, names):
            ax.scatter([x], [y], s=900, color=c, edgecolor="#999999", zorder=2, marker="s")
            ax.text(x, y - 0.62, n, ha="center", va="top", fontsize=8, color=SUB)
            ax.text(x, y, str(x), ha="center", va="center", fontsize=9,
                    color="white" if c != "#eeeeee" else SUB, zorder=3)
        for x, lab in marks.items():
            ax.text(x, ys[x] + 0.5, lab, ha="center", va="bottom", fontsize=9, color=INK)
        ax.set_title(title, loc="left", fontsize=10, color=INK)
        ax.set_xlim(-0.7, 10.7)
        ax.set_ylim(0.1, 4.1)
        ax.axis("off")
    fig.tight_layout()
    save_plot(fig, "ipa_layers")


def grid_fig(work):
    rows = []
    for st in STAGES:
        rows.append([body(work / f"gen_plain/{st}_{c}_{SEED}.png", (190, 304)) for c, _ in CONDS])
    to_webp(grid(rows, [STAGES[s][0] for s in STAGES], [lab for _, lab in CONDS], left=96, size=20),
            "ipa_grid.webp")


def metrics():
    res = json.load(open(LAB / "metrics_plain.json"))["images"]
    fig, axes = plt.subplots(1, 2, figsize=(8.4, 3.9), sharey=True)
    keys = [("chroma", "人物の彩度 C*（参照の人物は 3.9）"), ("back_dE", "背景と白の差 ΔE")]
    for ax, (key, xlabel) in zip(axes, keys):
        for i, (c, _) in enumerate(CONDS):
            for st, (lab, color) in STAGES.items():
                vals = [res[f"{st}_{c}_{s}"][key] for s in SEEDS]
                y = len(CONDS) - 1 - i + (0.15 if st == "s1" else -0.15)
                ax.scatter(vals, [y] * 3, s=34, color=color, zorder=3, edgecolor="white", linewidth=0.6,
                           label=lab if i == 0 else None)
        ax.set_xlabel(xlabel, color=INK, fontsize=10)
        ax.grid(axis="x", color=GRID, zorder=0)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
    axes[1].set_xscale("symlog", linthresh=10)
    axes[1].set_xticks([0, 5, 10, 20, 50, 80])
    axes[1].set_xticklabels(["0", "5", "10", "20", "50", "80"])
    axes[0].set_yticks(range(len(CONDS)))
    axes[0].set_yticklabels([lab for _, lab in CONDS][::-1])
    axes[0].legend(frameon=False, loc="upper right", fontsize=9)
    fig.tight_layout()
    save_plot(fig, "ipa_metrics")


def blank(work):
    tile = lambda c: Image.new("RGB", (190, 304), c)  # noqa: E731
    rows = [[tile((255, 255, 255)), body(work / f"gen_blank/s1_white_stp_{SEED}.png", (190, 304)),
             body(work / f"gen_blank/s1_white_linear_{SEED}.png", (190, 304))],
            [tile((0, 177, 64)), body(work / f"gen_blank/s1_green_stp_{SEED}.png", (190, 304)),
             body(work / f"gen_blank/s1_green_linear_{SEED}.png", (190, 304))]]
    out = grid(rows, None, ["参照（人物なし）", "1 段目・precise", "1 段目・linear"], size=20)
    ImageDraw.Draw(out).rectangle((0, 46, 189, 46 + 303), outline="#bbbbbb")
    to_webp(out, "ipa_blank.webp")


def weight(work):
    rows = [[body(work / f"gen_plain/s1_white_stp{w}_{SEED}.png", (190, 304)) for w in ("_w3", "", "_w9")],
            [body(work / f"gen_plain/s2_green_linear{w}_{SEED}.png", (190, 304)) for w in ("_w3", "", "_w9")]]
    to_webp(grid(rows, ["1 段目\n白・precise", "2 段目\n緑・linear"], ["重み 0.3", "重み 0.6", "重み 0.9"],
                 left=150, size=20), "ipa_weight.webp")


def want(work):
    ims = [ref_body(work / "ref/white.png", (220, 352)), body(work / f"gen/s1_none_{SEED}.png", (220, 352)),
           body(work / f"gen/s1_white_stp_{SEED}.png", (220, 352)),
           body(work / f"gen/s2_white_stp_{SEED}.png", (220, 352))]
    to_webp(grid([ims], None, ["参照", "参照なし", "1 段目・precise", "2 段目・precise"], size=20), "ipa_want.webp")


def main():
    work = Path(sys.argv[1])
    cover(work)
    read(work)
    layers()
    grid_fig(work)
    metrics()
    blank(work)
    weight(work)
    want(work)


if __name__ == "__main__":
    main()
