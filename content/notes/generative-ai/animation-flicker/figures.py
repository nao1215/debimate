"""生成した絵を動かすとちらつく話のノートの図を作る。

- flicker_cover.webp（動く）: 4 通りの作り方で作った 4 コマを、横に並べて同時に再生する
- flicker_doll.webp: 3D モデルの 4 コマと、計測に使う 2 つの範囲（止まっている所・腕が新しく入る所）
- flicker_diff.webp: 2 コマ目と 3 コマ目の差を、明るさで描いた図（作り方ごと）
- flicker_tradeoff.webp: ちらつき（横）と、腕が付いてきた割合（縦）の散布図
- flicker_denoise.webp: 元の 1 コマ目と、弱く描き直す強さ（denoise）0.45・0.6・0.75 の 4 コマ目
- flicker_steps.webp: txt2img と img2img が、ノイズを除く列のどこから描き始めるか
- flicker_warp_how.webp: 3D モデルの表面の座標を色にした絵（1 コマ目と 4 コマ目）と、手の 1 点の対応
- flicker_tear.webp: 流れのならし 3 画素と 20 画素で歪めた 4 コマ目の腕の周り
- flicker_sheet.webp: 1 枚ずつ描いた顔と、並べて 1 枚で描いた顔を同じ大きさで並べる

    uv run --with pillow==12.0.0 --with matplotlib==3.9.2 --with numpy==2.1.3 --with scipy==1.14.1 \
        --with opencv-python-headless==4.10.0.84 python figures.py <render_frames.py の出力先> <生成した PNG のディレクトリ>

計測の値は lab/metrics.json（measure.py の出力）を読む。
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
sys.path.insert(0, str(LAB))
from measure import CELL, frames_of  # noqa: E402
from warp import doll_flow, load_coords  # noqa: E402

IMAGES.mkdir(exist_ok=True)
CJK = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
font_manager.fontManager.addfont(CJK)
plt.rcParams["font.family"] = font_manager.FontProperties(fname=CJK).get_name()
INK, SUB, GRID = "#1f1f1f", "#666666", "#dddddd"
SEED = 20261112
SEEDS = (20261112, 20261113, 20261114)
# 作り方ごとの呼び名と色（本文の呼び名と揃える）
METHODS = {"redraw": ("1 コマずつ描く", "#c0504d"),
           "img2img": ("弱く描き直す 0.45", "#e6a23c"),
           "img2img60": ("弱く描き直す 0.6", "#c98a2b"),
           "img2img75": ("弱く描き直す 0.75", "#9c6a1e"),
           "sheet": ("並べて 1 枚", "#4f81bd"),
           "warp_gen_s20": ("1 枚を歪める", "#2e8b57")}
COVER = ["redraw", "img2img", "sheet", "warp_gen_s20"]


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


def labeled_row(images, labels, gap=16, top=44, size=26):
    w, h = images[0].size
    out = Image.new("RGB", (len(images) * w + (len(images) - 1) * gap, h + top), "white")
    d = ImageDraw.Draw(out)
    for i, (im, lab) in enumerate(zip(images, labels)):
        x = i * (w + gap)
        out.paste(im, (x, top))
        tw = d.textlength(lab, font=font(size))
        d.text((x + (w - tw) / 2, 4), lab, fill=INK, font=font(size))
    return out


def cover(gen):
    """4 通りの 4 コマを同時に再生する。1 コマ 0.5 秒で 1→4→1→4 と進め、最後に 4 コマ目で 3 秒止める。"""
    sets = [frames_of(gen, m, SEED) for m in COVER]
    order = [0, 1, 2, 3, 2, 1, 0, 1, 2, 3]
    frames, durs = [], []
    for n, k in enumerate(order):
        row = labeled_row([s[k].crop((10, 60, 374, 740)).resize((216, 404), Image.LANCZOS) for s in sets],
                          [METHODS[m][0] for m in COVER], top=40, size=20, gap=12)
        canvas = Image.new("RGB", (row.width, row.height + 40), "white")
        canvas.paste(row, (0, 0))
        d = ImageDraw.Draw(canvas)
        y = row.height + 8
        d.text((8, y), f"コマ {k + 1} / 4", fill=INK, font=font(20))
        # 何コマ目かが分かる帯
        x0, bw = 120, canvas.width - 130
        d.rectangle([x0, y + 10, x0 + bw, y + 22], fill="#eeeeee")
        d.rectangle([x0, y + 10, x0 + bw * (k + 1) / 4, y + 22], fill="#888888")
        frames.append(canvas)
        durs.append(3000 if n == len(order) - 1 else 500)
    frames[0].save(IMAGES / "flicker_cover.webp", "WEBP", save_all=True, append_images=frames[1:],
                   duration=durs, loop=0, quality=60, method=6)
    print("wrote flicker_cover.webp", sum(durs) / 1000, "s")


def doll(passes, gen):
    cells = []
    for f in ("f0", "f1", "f2", "f3"):
        im = Image.open(f"{passes}/depth_{f}.png").convert("RGB")
        w = round(im.width * CELL[1] / im.height)
        im = im.resize((w, CELL[1]), Image.LANCZOS)
        x = (w - CELL[0]) // 2
        cells.append(im.crop((x, 0, x + CELL[0], CELL[1])))
    static = np.array(Image.open(f"{gen}/static_mask.png")) > 0
    arm = np.array(Image.open(f"{gen}/arm_region.png")) > 0
    a = np.asarray(cells[3]).astype(np.float32)
    a[static] = a[static] * 0.4 + np.array([60, 140, 220]) * 0.6
    a[arm] = a[arm] * 0.3 + np.array([240, 140, 40]) * 0.7
    cells.append(Image.fromarray(a.astype(np.uint8)))
    cells = [c.crop((20, 40, 364, 740)) for c in cells]
    to_webp(labeled_row(cells, ["コマ 1", "コマ 2", "コマ 3", "コマ 4", "計測の範囲"], size=24), "flicker_doll.webp")


def diff(gen):
    """2 コマ目と 3 コマ目の差の絶対値を 4 倍して白黒で描く（明るいほど差が大きい）。"""
    ims = []
    for m in COVER:
        fr = frames_of(gen, m, SEED)
        d = np.abs(np.asarray(fr[2], np.float32) - np.asarray(fr[1], np.float32)).mean(-1) * 4
        ims.append(Image.fromarray(np.clip(d, 0, 255).astype(np.uint8)).convert("RGB").crop((20, 40, 364, 740)))
    to_webp(labeled_row(ims, [METHODS[m][0] for m in COVER], size=24), "flicker_diff.webp")


def tradeoff():
    res = json.load(open(LAB / "metrics.json"))
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    for m, (lab, color) in METHODS.items():
        xs = [res[f"{m}_{s}"]["mean"] for s in SEEDS if f"{m}_{s}" in res]
        ys = [res[f"{m}_{s}"]["arm_follow"] for s in SEEDS if f"{m}_{s}" in res]
        ax.scatter(xs, ys, s=60, color=color, label=lab, zorder=3, edgecolor="white", linewidth=0.8)
    ax.set_xlabel("ちらつき（止まっている所の、隣り合うコマの差の平均。0〜255）", color=INK)
    ax.set_ylabel("腕が付いてきた割合", color=INK)
    ax.set_xlim(-1, 25)
    ax.set_ylim(-0.05, 1.05)
    ax.grid(color=GRID, zorder=0)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.legend(frameon=False, loc="center right", fontsize=9)
    ax.set_title("左上ほど良い（ちらつかず、3D モデルどおりに動く）。各 3 seed", color=SUB, fontsize=10, loc="left")
    save_plot(fig, "flicker_tradeoff")


def denoise(gen):
    """元にした 1 コマ目と、denoise 0.45・0.6・0.75 で描き直した 4 コマ目。"""
    ims = [frames_of(gen, "redraw", SEED)[0].crop((20, 130, 364, 740))]
    labels = ["元の 1 コマ目"]
    for m in ("img2img", "img2img60", "img2img75"):
        ims.append(frames_of(gen, m, SEED)[3].crop((20, 130, 364, 740)))
        labels.append(f"{METHODS[m][0].split()[-1]}・コマ 4")
    to_webp(labeled_row(ims, labels, size=24), "flicker_denoise.webp")


def steps():
    """28 ステップで描く時、txt2img と img2img（denoise 0.75・0.45）がノイズを除く列のどこから描き始めるか。
    ComfyUI は denoise が 1 未満の時、int(28 / denoise) 段の列を作り、末尾の 28 段だけを使う（img2img Denoise のノート）。"""
    rows = [("txt2img（1 コマずつ描く）", 0.0), ("img2img denoise 0.75", 1 - 28 / int(28 / 0.75)),
            ("img2img denoise 0.45", 1 - 28 / int(28 / 0.45))]
    fig, ax = plt.subplots(figsize=(7.4, 2.6))
    pose = 6 / 28
    ax.axvspan(0, pose, color="#f3d9b1", zorder=0)
    ax.text(pose / 2, len(rows) - 0.35, "姿勢が決まる\n（28 段の前 6 段）", ha="center", va="bottom", fontsize=9, color=INK)
    for i, (lab, start) in enumerate(rows):
        y = len(rows) - 1 - i
        ax.barh(y, 1 - start, left=start, height=0.45, color="#7f9fbf", zorder=2)
        if start > 0:
            ax.barh(y, start, left=0, height=0.45, color="#e8e8e8", zorder=1)
            ax.text(start / 2 + (pose / 2 if start > pose * 1.5 else 0.02), y, "飛ばす", ha="center", va="center",
                    fontsize=9, color=SUB, zorder=3)
        ax.text(-0.02, y, lab, ha="right", va="center", fontsize=10, color=INK)
        ax.text(start + 0.01, y + 0.3, f"{start * 100:.0f}% から描く", ha="left", va="bottom", fontsize=8, color=SUB)
    ax.set_xlim(0, 1)
    ax.set_ylim(-0.6, len(rows) + 0.3)
    ax.set_yticks([])
    ax.set_xticks([0, 0.5, 1])
    ax.set_xticklabels(["ノイズが多い", "", "ノイズが少ない"])
    for sp in ("top", "right", "left"):
        ax.spines[sp].set_visible(False)
    save_plot(fig, "flicker_steps")


def warp_how(passes):
    """表面の座標（変形前の位置 x・y・z を赤・緑・青）を色にした絵と、手の 1 点の対応。"""
    flow, good, _ = doll_flow(passes, "gen", "f3")
    mag = np.hypot(flow[..., 0], flow[..., 1])
    ys, xs = np.nonzero(good & (mag > 0.5))
    i = np.argmax(xs)
    p3 = (int(xs[i]), int(ys[i]))
    p0 = (int(xs[i] + flow[ys[i], xs[i], 0]), int(ys[i] + flow[ys[i], xs[i], 1]))
    tiles = []
    for f, p in (("f0", p0), ("f3", p3)):
        c, m = load_coords(passes, "gen", f)
        rgb = np.full(c.shape, 255, np.uint8)
        rgb[m] = (np.clip(c[m], 0, 1) * 255).astype(np.uint8)
        im = Image.fromarray(rgb).crop((150, 100, 700, 1150))
        d = ImageDraw.Draw(im)
        q = (p[0] - 150, p[1] - 100)
        d.ellipse([q[0] - 12, q[1] - 12, q[0] + 12, q[1] + 12], outline=INK, width=4)
        tiles.append(im.resize((im.width * 2 // 3, im.height * 2 // 3), Image.LANCZOS))
    to_webp(labeled_row(tiles, ["コマ 1 の表面の座標", "コマ 4 の表面の座標"], size=24, gap=40), "flicker_warp_how.webp")
    print("hand point", p0, "->", p3)


def tear(gen):
    """腕の周り: 元の絵、ならし 3 画素のコマ 4、ならし 20 画素のコマ 2 とコマ 4。"""
    box = (380, 380, 760, 860)
    picks = [(f"redraw_f0_{SEED}", "元の絵（コマ 1）"), (f"warp_gen_s3_{SEED}_f3", "ならし 3 画素・コマ 4"),
             (f"warp_gen_s20_{SEED}_f1", "ならし 20 画素・コマ 2"), (f"warp_gen_s20_{SEED}_f3", "ならし 20 画素・コマ 4")]
    ims = [Image.open(f"{gen}/{n}.png").convert("RGB").crop(box) for n, _ in picks]
    labels = [lab for _, lab in picks]
    to_webp(labeled_row(ims, labels, size=24), "flicker_tear.webp")


def sheet(gen):
    """顔の周りを、どちらも 3D モデルの 1 m が同じ画素数になる大きさで並べる。"""
    one = Image.open(f"{gen}/redraw_f0_{SEED}.png").convert("RGB")
    s = Image.open(f"{gen}/sheet_{SEED}.png").convert("RGB")
    k = 1216 / 768  # 並べた 1 枚の 1 コマは、1 枚ずつの絵の 768/1216 倍の大きさ
    box = (230, 150, 470, 390)
    face_one = one.crop(box).resize((360, 360), Image.LANCZOS)
    x0 = (round(832 * 768 / 1216) - 384) // 2
    fb = [round(box[0] * 768 / 1216) - x0, round(box[1] * 768 / 1216), round(box[2] * 768 / 1216) - x0,
          round(box[3] * 768 / 1216)]
    face_sheet = s.crop(fb).resize((360, 360), Image.LANCZOS)
    to_webp(labeled_row([face_one, face_sheet], ["1 コマずつ描く", f"並べて 1 枚（{k:.2f} 倍に拡大）"],
                        size=22, gap=24), "flicker_sheet.webp")


if __name__ == "__main__":
    passes, gen = sys.argv[1:3]
    cover(gen)
    doll(passes, gen)
    diff(gen)
    tradeoff()
    denoise(gen)
    steps()
    warp_how(passes)
    tear(gen)
    sheet(gen)
