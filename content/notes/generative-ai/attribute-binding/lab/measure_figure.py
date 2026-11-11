"""本文の「色を数える方法」の図を作る。measure.py と同じ手順で 1 枚の画像を測り、途中の領域を描く。

    python measure_figure.py <PNG の保存先> eye_aqua 1000 ../images/attribute-binding_measure.webp

CLIPSeg（CPU）と matplotlib・Pillow を使う。左から、元の画像、CLIPSeg が返した髪の領域
（目の画素を除いた後）、その領域で青緑と数えた画素。
"""
import os
import sys
import tempfile

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

from measure import HUES, Seg, hsv, hue_share

INK, SUB, OCHRE, RED = "#1f1f1f", "#666666", "#d4a24c", "#e15759"


def main():
    src, cond, seed, out = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
    img = Image.open(os.path.join(src, cond, f"{seed}.png")).convert("RGB")
    h, s, v = hsv(img)
    m = Seg().masks(img, ["hair", "eyes", "face"])
    hair = m["hair"] & ~m["eyes"]
    lo, hi = HUES["aqua"]
    hit = hair & (s >= 0.25) & (v >= 0.2) & (h >= lo) & (h <= hi)
    share = hue_share(h, s, v, hair, "aqua")
    print(f"hair px {int(hair.sum())}, aqua px {int(hit.sum())}, share {share:.4f}")

    a = np.asarray(img, dtype=np.float32) / 255
    pale = 1 - (1 - a.mean(axis=2, keepdims=True)) * 0.35          # 薄い灰色にした元画像
    pale = np.repeat(pale, 3, axis=2)
    region = pale.copy()
    region[hair] = region[hair] * 0.45 + np.array([0xd4, 0xa2, 0x4c]) / 255 * 0.55
    counted = pale.copy()
    counted[hit] = np.array([0xe1, 0x57, 0x59]) / 255
    # 1 画素では見えないので、数えた画素の周りを 2 画素だけ太らせて描く（数は太らせる前の値）
    from scipy.ndimage import binary_dilation  # noqa: E402
    counted[binary_dilation(hit, iterations=2)] = np.array([0xe1, 0x57, 0x59]) / 255

    plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 11,
                         "text.color": INK})
    fig, axes = plt.subplots(1, 3, figsize=(9.6, 3.7))
    titles = ["元の画像", "髪の領域（CLIPSeg）", f"青緑と数えた画素（髪の {share * 100:.1f}%）"]
    for ax, im, t in zip(axes, (a, region, counted), titles):
        ax.imshow(np.clip(im, 0, 1))
        ax.set_title(t, fontsize=11, color=INK)
        ax.axis("off")
    fig.tight_layout()
    with tempfile.TemporaryDirectory() as d:
        png = os.path.join(d, "f.png")
        fig.savefig(png, dpi=200, facecolor="#ffffff", bbox_inches="tight", pad_inches=0.1)
        Image.open(png).convert("RGB").save(out, "WEBP", quality=90, method=6)


if __name__ == "__main__":
    main()
