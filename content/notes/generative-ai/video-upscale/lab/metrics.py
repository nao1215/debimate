"""拡大したフレームの列を、正解のフレームの列と比べる。

python3 metrics.py <作業ディレクトリ> <結果の JSON>
  <作業ディレクトリ>/gt/ が正解、<作業ディレクトリ>/out/<方式>_<入力>/ が拡大の結果。

flicker: 正解で隣り合うフレームの差がほぼ 0（輝度で 1.5 未満）の画素だけを取り出し、
         拡大の結果で隣り合うフレームの輝度がどれだけ変わったかの平均。正解なら 0 に近い。
excess:  隣り合うフレームの差を、正解の隣り合うフレームの差と比べた残り（全画素の平均）。
         |(out[t] - out[t-1]) - (gt[t] - gt[t-1])|。カメラや物の動きで説明できない変化の量。
psnr:    正解との PSNR（輝度、dB）。フレームごとに計算して平均する。
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

STATIC = 1.5


def luma(path):
    a = np.asarray(Image.open(path).convert("RGB"), dtype=np.float64)
    return 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]


def frames(d):
    return [luma(p) for p in sorted(Path(d).glob("*.png"))]


def main():
    work = Path(sys.argv[1])
    gt = frames(work / "gt")
    masks = [np.abs(gt[t] - gt[t - 1]) < STATIC for t in range(1, len(gt))]
    static_ratio = float(np.mean([m.mean() for m in masks]))
    gt_flicker = float(np.mean([np.abs(gt[t] - gt[t - 1])[masks[t - 1]].mean()
                                for t in range(1, len(gt))]))
    result = {"static_pixel_ratio": round(static_ratio, 3), "gt_flicker": round(gt_flicker, 3),
              "runs": {}}
    for d in sorted((work / "out").iterdir()):
        out = frames(d)
        flicker = np.mean([np.abs(out[t] - out[t - 1])[masks[t - 1]].mean()
                           for t in range(1, len(out))])
        excess = np.mean([np.abs((out[t] - out[t - 1]) - (gt[t] - gt[t - 1])).mean()
                          for t in range(1, len(out))])
        psnr = np.mean([10 * np.log10(255 ** 2 / np.mean((o - g) ** 2)) for o, g in zip(out, gt)])
        result["runs"][d.name] = {"flicker": round(float(flicker), 3),
                                 "excess": round(float(excess), 3), "psnr": round(float(psnr), 2)}
        print(f"{d.name:20s} flicker={flicker:6.3f}  excess={excess:6.3f}  psnr={psnr:5.2f}")
    print(f"gt                   flicker={gt_flicker:6.3f}  (static pixels {static_ratio:.1%})")
    Path(sys.argv[2]).write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
