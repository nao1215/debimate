"""Face Redraw のノートの図を作る。

使い方: python figures.py <作業先>   （<作業先>/gen に run.py の出力、<作業先>/detect.json・detect_yolo.json・metrics.json・log_face.json）
- fr_cover.webp:  全身の立ち絵と、顔の拡大（描いたまま・顔だけ描き直した後）
- fr_latent.webp: 全身の立ち絵の顔に、潜在の格子（8 画素ごと）を重ねた図
- fr_steps.webp:  顔だけ描き直す手順（切り抜く → 拡大 → 描き直す → 縮める → 貼り戻す）を、実際の絵で並べた図
- fr_boxes.webp:  バウンディングボックス・貼り戻すマスク・切り抜く正方形の大きさの関係
- fr_detect.webp: 顔検出の枠（MediaPipe の short・full、face_yolov8n）
- fr_denoise.webp: denoise とプロンプトを変えて顔を描き直した結果
- fr_eyes.webp:   5 枚の目の周り。描いたまま・顔だけ描き直した後（0.3・0.45）・全体を 2 倍で描き直した後
- fr_lines.webp:  表示の大きさ（832 x 1216）での、あごの輪郭の線。描いたまま・顔だけ描き直した後・全体を 2 倍で描き直して縮めた絵
- fr_big.webp:    最初から 2 倍（1664 x 2432）で描いた 5 枚
"""
import json
import os
import sys

import matplotlib
import numpy as np
from PIL import Image, ImageDraw, ImageFont

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = sys.argv[1]
GEN = os.path.join(WORK, "gen")
IMG = os.path.join(HERE, "images")
FONT = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
plt.rcParams["font.family"] = "Noto Sans CJK JP"
W, H = 832, 1216
SEED = "20261120"
LINE_SEED = "20261122"


def load(name, display=True):
    im = Image.open(os.path.join(GEN, name + ".png")).convert("RGB")
    if display and im.size != (W, H):
        im = im.resize((W, H), Image.BOX)
    return im


def box(seed):
    d = json.load(open(os.path.join(WORK, "detect.json")))[f"base_{seed}"]
    return (d["full_0.5"] or d["full_0.1"])[0]["box"]


def face_crop(im, seed, pad=0.45):
    x1, y1, x2, y2 = box(seed)
    s = max(x2 - x1, y2 - y1) * (1 + 2 * pad)
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    return im.crop((int(cx - s / 2), int(cy - s / 2), int(cx + s / 2), int(cy + s / 2)))


def panels(tiles, labels, out, size, head=56, sub=None, gap=16):
    """tiles: [[PIL 画像, ...], ...]（行ごと）。labels: 列の見出し。sub: 行の見出し（左に置く）。"""
    font = ImageFont.truetype(FONT, 28)
    small = ImageFont.truetype(FONT, 24)
    tw, th = size
    left = 170 if sub else 0
    cols = max(len(r) for r in tiles)
    c = Image.new("RGB", (left + cols * tw + (cols - 1) * gap, head + len(tiles) * th + (len(tiles) - 1) * gap), "white")
    d = ImageDraw.Draw(c)
    for j, lab in enumerate(labels):
        d.text((left + j * (tw + gap) + tw // 2, head // 2), lab, fill=(30, 30, 30), font=font, anchor="mm")
    for i, row in enumerate(tiles):
        y = head + i * (th + gap)
        if sub:
            d.text((left // 2, y + th // 2), sub[i], fill=(30, 30, 30), font=small, anchor="mm")
        for j, t in enumerate(row):
            if t is not None:
                c.paste(t.resize((tw, th), Image.LANCZOS), (left + j * (tw + gap), y))
    c.save(os.path.join(IMG, out), "WEBP", quality=90, method=6)
    print("wrote", out, c.size)


def cover():
    base = load(f"base_{SEED}")
    redo = load(f"face_{SEED}_same_d45_c30")
    whole = base.crop((140, 120, 700, 1216))
    hh, gap, head = 520, 16, 56
    whole = whole.resize((whole.width * hh // whole.height, hh), Image.LANCZOS)
    faces = [face_crop(im, SEED, 0.15).resize((hh, hh), Image.LANCZOS) for im in (base, redo)]
    font = ImageFont.truetype(FONT, 28)
    c = Image.new("RGB", (whole.width + 2 * (hh + gap), hh + head), "white")
    d = ImageDraw.Draw(c)
    x = 0
    for t, lab in zip([whole] + faces, ["全身の立ち絵", "顔（描いたまま）", "顔（顔だけ描き直した）"]):
        c.paste(t, (x, head))
        d.text((x + t.width // 2, head // 2), lab, fill=(30, 30, 30), font=font, anchor="mm")
        x += t.width + gap
    c.save(os.path.join(IMG, "fr_cover.webp"), "WEBP", quality=90, method=6)
    print("wrote fr_cover.webp", c.size)


def latent():
    base = load(f"base_{SEED}")
    x1, y1, x2, y2 = box(SEED)
    # 8 画素の格子が見えるよう、顔の周りを 6 倍に拡大して線を引く
    pad = 16
    cx0, cy0 = (x1 - pad) // 8 * 8, (y1 - pad) // 8 * 8
    cx1, cy1 = cx0 + ((x2 - cx0 + pad) // 8 + 1) * 8, cy0 + ((y2 - cy0 + pad) // 8 + 1) * 8
    k = 6
    crop = base.crop((cx0, cy0, cx1, cy1)).resize(((cx1 - cx0) * k, (cy1 - cy0) * k), Image.NEAREST)
    d = ImageDraw.Draw(crop)
    for x in range(0, crop.width + 1, 8 * k):
        d.line([(x, 0), (x, crop.height)], fill=(40, 120, 230), width=1)
    for y in range(0, crop.height + 1, 8 * k):
        d.line([(0, y), (crop.width, y)], fill=(40, 120, 230), width=1)
    d.rectangle([(x1 - cx0) * k, (y1 - cy0) * k, (x2 - cx0) * k, (y2 - cy0) * k], outline=(220, 40, 40), width=3)
    whole = base.copy()
    ImageDraw.Draw(whole).rectangle([x1, y1, x2, y2], outline=(220, 40, 40), width=4)
    whole = whole.crop((140, 120, 700, 1216))
    hh = 600
    a = whole.resize((whole.width * hh // whole.height, hh), Image.LANCZOS)
    b = crop.resize((crop.width * hh // crop.height, hh), Image.LANCZOS)
    font = ImageFont.truetype(FONT, 26)
    c = Image.new("RGB", (a.width + b.width + 40, hh + 56), "white")
    c.paste(a, (0, 56))
    c.paste(b, (a.width + 40, 56))
    d = ImageDraw.Draw(c)
    d.text((a.width // 2, 28), "832 x 1216 の全身", fill=(30, 30, 30), font=font, anchor="mm")
    d.text((a.width + 40 + b.width // 2, 28), "顔の周り（青い線は 8 画素ごと）", fill=(30, 30, 30), font=font, anchor="mm")
    c.save(os.path.join(IMG, "fr_latent.webp"), "WEBP", quality=90, method=6)
    print("wrote fr_latent.webp", c.size)


def steps():
    log = json.load(open(os.path.join(WORK, "log_face.json")))
    name = f"face_{SEED}_same_d45_c30"
    g = log[name]
    x, y, side = g["crop"]
    base = load(f"base_{SEED}")
    cut = base.crop((x, y, x + side, y + side))
    big = cut.resize((1024, 1024), Image.LANCZOS)
    redo = Image.open(os.path.join(GEN, name + "_crop.png")).convert("RGB")
    small = redo.resize((side, side), Image.BOX)
    mx, my, mw, mh = g["mask"]
    m = Image.new("L", (side, side), 0)
    ImageDraw.Draw(m).rectangle([mx - x, my - y, mx - x + mw, my - y + mh], fill=255)
    from PIL import ImageFilter
    m = m.filter(ImageFilter.GaussianBlur(g["blur"] / 2))
    shown = Image.composite(Image.new("RGB", (side, side), (230, 140, 20)), small, m.point(lambda v: v * 0.35))
    final = load(name).crop((x, y, x + side, y + side))
    panels([[cut, big, redo, shown, final]],
           [f"1. 切り抜く（{side}）", "2. 拡大（1024）", "3. 描き直す（1024）", f"4. 縮める（{side}）", "5. 色の所を貼り戻す"],
           "fr_steps.webp", (300, 300))


def boxes():
    """全身の絵の頭の周りに、バウンディングボックス・貼り戻すマスク（1.3 倍）・切り抜く正方形（3 倍）を重ねる。"""
    log = json.load(open(os.path.join(WORK, "log_face.json")))
    g = log[f"face_{SEED}_same_d45_c30"]
    x, y, side = g["crop"]
    mx, my, mw, mh = g["mask"]
    x1, y1, x2, y2 = box(SEED)
    im = load(f"base_{SEED}")
    d = ImageDraw.Draw(im)
    d.rectangle([x, y, x + side, y + side], outline=(40, 120, 230), width=3)
    d.rectangle([mx, my, mx + mw, my + mh], outline=(230, 140, 20), width=3)
    d.rectangle([x1, y1, x2, y2], outline=(220, 40, 40), width=3)
    pad = 30
    im = im.crop((x - pad, y - pad, x + side + pad, y + side + pad)).resize((2 * (side + 2 * pad),) * 2, Image.LANCZOS)
    font = ImageFont.truetype(FONT, 24)
    c = Image.new("RGB", (im.width + 520, im.height), "white")
    c.paste(im, (0, 0))
    d = ImageDraw.Draw(c)
    rows = [((220, 40, 40), f"バウンディングボックス（{x2 - x1} x {y2 - y1}）"), ((230, 140, 20), f"貼り戻すマスク（1.3 倍、{mw} x {mh}）"),
            ((40, 120, 230), f"切り抜く正方形（3 倍、{side} x {side}）")]
    for i, (col, lab) in enumerate(rows):
        yy = im.height // 2 - 80 + i * 60
        d.rectangle([im.width + 24, yy, im.width + 54, yy + 30], outline=col, width=5)
        d.text((im.width + 68, yy + 15), lab, fill=(30, 30, 30), font=font, anchor="lm")
    c.save(os.path.join(IMG, "fr_boxes.webp"), "WEBP", quality=90, method=6)
    print("wrote fr_boxes.webp", c.size)


def detect():
    det = json.load(open(os.path.join(WORK, "detect.json")))
    yolo = json.load(open(os.path.join(WORK, "detect_yolo.json")))
    name = "base_20261118"
    im = load(name)
    d = ImageDraw.Draw(im)
    for key, col in (("short_0.5", (220, 40, 40)), ("full_0.5", (40, 120, 230))):
        b = det[name][key][0]["box"]
        d.rectangle(b, outline=col, width=6)
    d.rectangle(yolo[name][0]["box"], outline=(30, 160, 60), width=6)
    im = im.crop((150, 180, 600, 1000))
    im = im.resize((im.width * 640 // im.height, 640), Image.LANCZOS)
    font = ImageFont.truetype(FONT, 24)
    c = Image.new("RGB", (im.width + 420, 640), "white")
    c.paste(im, (0, 0))
    d = ImageDraw.Draw(c)
    rows = [((220, 40, 40), "MediaPipe（short、既定）"), ((40, 120, 230), "MediaPipe（full）"),
            ((30, 160, 60), "face_yolov8n")]
    for i, (col, lab) in enumerate(rows):
        y = 250 + i * 60
        d.rectangle([im.width + 30, y, im.width + 60, y + 30], outline=col, width=5)
        d.text((im.width + 74, y + 15), lab, fill=(30, 30, 30), font=font, anchor="lm")
    c.save(os.path.join(IMG, "fr_detect.webp"), "WEBP", quality=90, method=6)
    print("wrote fr_detect.webp", c.size)


def denoise():
    seed = "20261119"
    base = load(f"base_{seed}")
    row1 = [face_crop(base, seed, 0.2)] + [face_crop(load(f"face_{seed}_same_d{d}_c30"), seed, 0.2) for d in (30, 45, 60)]
    row2 = [None, None] + [face_crop(load(f"face_{seed}_face_d{d}_c30"), seed, 0.2) for d in (45, 60)]
    panels([row1, row2], ["描いたまま", "denoise 0.3", "0.45", "0.6"], "fr_denoise.webp", (260, 260),
           sub=["全身と同じ\nプロンプト", "顔用の\nプロンプト"])


def eyes():
    """5 枚の目の周りを、描いたまま・顔だけ描き直した後（0.3・0.45）・全体の描き直しで並べる。"""
    seeds = ("20261118", "20261119", "20261120", "20261121", "20261122")
    rows = []
    for name in ("base_{}", "face_{}_same_d30_c30", "face_{}_same_d45_c30", "hires_{}"):
        row = []
        for s in seeds:
            x1, y1, x2, y2 = box(s)
            row.append(load(name.format(s)).crop((x1 + 2, y1 + 14, x2 + 4, y1 + 54)))
        rows.append(row)
    panels(rows, list(seeds), "fr_eyes.webp", (240, 120),
           sub=["描いたまま", "顔だけ 0.3", "顔だけ 0.45", "全体を 2 倍で\n描き直した"])


def lines():
    """表示の大きさ（832 x 1216）の絵から、あごと髪の輪郭を切り出して 5 倍に拡大する（画素が見えるよう最近傍で）。"""
    seed = LINE_SEED
    m = json.load(open(os.path.join(HERE, "lab", "metrics.json")))[seed]
    x1, y1, x2, y2 = box(seed)
    area = (x1 - 20, y2 - 50, x1 + 60, y2 + 10)
    names = (f"base_{seed}", f"face_{seed}_same_d45_c30", f"hires_{seed}")
    tiles = [load(n).crop(area).resize((400, 300), Image.NEAREST) for n in names]
    w = [m[k]["line_display"] for k in ("base", "same_d45_c30", "hires")]
    panels([tiles], [f"描いたまま（{w[0]:.1f}）", f"顔だけ描き直した（{w[1]:.1f}）", f"全体を描き直して縮めた（{w[2]:.1f}）"],
           "fr_lines.webp", (400, 300))


def big():
    tiles = [load(f"big_{s}") for s in ("20261118", "20261119", "20261120", "20261121", "20261122")]
    panels([tiles], ["20261118", "20261119", "20261120", "20261121", "20261122"], "fr_big.webp", (240, 351))


def main():
    os.makedirs(IMG, exist_ok=True)
    for f in (cover, latent, steps, boxes, detect, denoise, eyes, lines, big):
        try:
            f()
        except FileNotFoundError as e:
            print("skip", f.__name__, e)


if __name__ == "__main__":
    main()
