"""hires fix の前後を比べる。

  white_b    : 白いシャツの範囲（boxes.json の shirt）のうち、1 段目で白い画素（CIELAB の L* > 85 かつ
               彩度 < 12）の b*（黄み。+ が黄、- が青）の平均を、1 段目（lanczos で 1.5 倍に拡大した物）と
               2 段目の同じ画素で比べる
  sharpness  : 明るさのラプラシアンの分散。大きいほど細かい線や縁が多い。
               画面全体と、顔の範囲（boxes.json の face）で数える。
               boxes.json の矩形は、1 段目の絵（832x1216）を目で見て付けた
  face_px    : 1 段目の顔の範囲の高さ（画素）

使い方: python3 hires_metrics.py <PNG のディレクトリ> <結果の JSON>
"""
import json
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage
from skimage import color

HERE = os.path.dirname(os.path.abspath(__file__))


def lap_var(gray):
    return float(ndimage.laplace(gray).var())


def main():
    d, out = sys.argv[1], sys.argv[2]
    boxes = json.load(open(os.path.join(HERE, "boxes.json")))
    rows = []
    for seed in sorted(boxes):
        one = Image.open(os.path.join(d, f"person_{seed}_1x.png")).convert("RGB")
        two = Image.open(os.path.join(d, f"person_{seed}_hires.png")).convert("RGB")
        up = one.resize(two.size, Image.LANCZOS)
        a = np.asarray(up, dtype=np.float64) / 255
        b = np.asarray(two, dtype=np.float64) / 255
        la, lb = color.rgb2lab(a), color.rgb2lab(b)
        k = two.size[0] / one.size[0]
        sx0, sy0, sx1, sy1 = [int(round(v * k)) for v in boxes[seed]["shirt"]]
        in_shirt = np.zeros(la.shape[:2], bool)
        in_shirt[sy0:sy1, sx0:sx1] = True
        white = in_shirt & (la[..., 0] > 85) & (np.hypot(la[..., 1], la[..., 2]) < 12)
        ga, gb = color.rgb2gray(a) * 255, color.rgb2gray(b) * 255
        x0, y0, x1, y1 = boxes[seed]["face"]  # 1 段目（832x1216）の座標
        fx0, fy0, fx1, fy1 = [int(round(v * k)) for v in (x0, y0, x1, y1)]
        row = {
            "seed": int(seed), "size_1x": one.size, "size_hires": two.size,
            "white_pixels": int(white.sum()),
            "white_b_1x": round(float(la[..., 2][white].mean()), 2),
            "white_b_hires": round(float(lb[..., 2][white].mean()), 2),
            "sharp_1x_up": round(lap_var(ga), 1), "sharp_hires": round(lap_var(gb), 1),
            "face_px": y1 - y0,
            "face_sharp_1x_up": round(lap_var(ga[fy0:fy1, fx0:fx1]), 1),
            "face_sharp_hires": round(lap_var(gb[fy0:fy1, fx0:fx1]), 1),
            "face_mean_abs_diff": round(float(np.abs(a[fy0:fy1, fx0:fx1] - b[fy0:fy1, fx0:fx1]).mean() * 255), 2),
        }
        rows.append(row)
        print(f"seed {seed}: white b* {row['white_b_1x']:+.2f} -> {row['white_b_hires']:+.2f} "
              f"({row['white_pixels']} px)  sharpness {row['sharp_1x_up']} -> {row['sharp_hires']}  "
              f"face({row['face_px']} px) {row['face_sharp_1x_up']} -> {row['face_sharp_hires']}  "
              f"face diff {row['face_mean_abs_diff']}")
    json.dump(rows, open(out, "w"), indent=1)


if __name__ == "__main__":
    main()
