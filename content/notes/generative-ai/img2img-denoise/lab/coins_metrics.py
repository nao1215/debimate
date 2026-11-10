"""実験 2 の絵で、明るい金色の画素の割合と、1 枚目との近さを数える。

  gold : HSV で色相 35〜60 度、彩度 0.5 以上、明度 0.75 以上の画素の割合（金貨の光る面の目安）
  ssim : 1 枚目（1.5 倍に拡大した物）と比べた SSIM（灰色、384x384 に縮めて計算）
化けたかどうかの判定は目で行った。この数は判定の補助で、正解ではない。

使い方: python3 coins_metrics.py <PNG のディレクトリ> <結果の JSON>
"""
import json
import os
import sys

import numpy as np
from PIL import Image
from skimage import color, metrics


def gold_ratio(im):
    hsv = np.asarray(im.convert("HSV"), dtype=np.float64) / 255
    h, s, v = hsv[..., 0] * 360, hsv[..., 1], hsv[..., 2]
    return float(((h >= 35) & (h <= 60) & (s >= 0.5) & (v >= 0.75)).mean())


def main():
    d, out = sys.argv[1], sys.argv[2]
    base = Image.open(os.path.join(d, "coins_base.png")).convert("RGB")
    ref = color.rgb2gray(np.asarray(base.resize((384, 384), Image.LANCZOS)) / 255)
    rows = []
    names = ["coins_base", "coins_g_030", "coins_g_045", "coins_g_050", "coins_g_060",
             "coins_g_075", "coins_c_060"]
    for n in names:
        im = Image.open(os.path.join(d, n + ".png")).convert("RGB")
        g = color.rgb2gray(np.asarray(im.resize((384, 384), Image.LANCZOS)) / 255)
        r = {"name": n, "gold": round(gold_ratio(im), 4),
             "ssim_vs_base": round(float(metrics.structural_similarity(ref, g, data_range=1.0)), 3)}
        rows.append(r)
        print(f"{n:12s} gold={r['gold'] * 100:5.2f}%  ssim_vs_base={r['ssim_vs_base']:.3f}")
    json.dump(rows, open(out, "w"), indent=1)


if __name__ == "__main__":
    main()
