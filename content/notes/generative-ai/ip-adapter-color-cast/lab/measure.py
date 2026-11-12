"""描いた絵の色を CIELAB で数える。

使い方: python measure.py <深度マップの PNG> <make_refs.py の保存先> <run.py の保存先> <metrics.json>
  人物: 深度マップで人形が写っている画素（値が 8 より大きい）
  背景: 人形から 48 画素より離れた画素
  back_dE   背景の平均色と白（L* 100、a* 0、b* 0）の差（CIE76 の ΔE）。文面で白い背景を頼んでいる
  body_dE   人物の平均色と、参照の人物の平均色の差（ΔE）。人物のいない参照では null
  body_lab  人物の平均の L*・a*・b*
  back_lab  背景の平均の L*・a*・b*
  chroma    人物の彩度 C* の平均（a*、b* の長さ）
色の変換は OpenCV の cvtColor（0〜1 の float の RGB を sRGB として L* 0〜100 に変換）。
"""
import glob
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image
from scipy import ndimage


def lab(path):
    rgb = np.asarray(Image.open(path).convert("RGB"), np.float32) / 255
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2Lab)


def de(a, b):
    return float(np.linalg.norm(np.asarray(a) - np.asarray(b)))


def main():
    depth_png, ref_dir, gen, out = sys.argv[1:5]
    depth = np.asarray(Image.open(depth_png).convert("L"))
    body = depth > 8
    back = ~ndimage.binary_dilation(body, iterations=48)
    res = {"body_pixels": int(body.sum()), "back_pixels": int(back.sum()), "images": {}}
    ref_body = None
    if os.path.exists(os.path.join(ref_dir, "mask.png")):  # 人物のいない参照には mask.png が無い
        ref = lab(os.path.join(ref_dir, "white.png"))
        ref_mask = np.asarray(Image.open(os.path.join(ref_dir, "mask.png"))) > 127
        ref_body = ref[ref_mask].mean(axis=0)
        res["ref_body_lab"] = [round(float(v), 2) for v in ref_body]
        res["ref_chroma"] = round(float(np.hypot(ref[ref_mask][:, 1], ref[ref_mask][:, 2]).mean()), 2)
    for path in sorted(glob.glob(os.path.join(gen, "s*.png"))):
        name = os.path.basename(path)[:-4]
        img = lab(path)
        b = img[body].mean(axis=0)
        k = img[back].mean(axis=0)
        res["images"][name] = {
            "back_dE": round(de(k, (100, 0, 0)), 2),
            "body_dE": round(de(b, ref_body), 2) if ref_body is not None else None,
            "chroma": round(float(np.hypot(img[body][:, 1], img[body][:, 2]).mean()), 2),
            "body_lab": [round(float(v), 2) for v in b],
            "back_lab": [round(float(v), 2) for v in k],
        }
    json.dump(res, open(out, "w"), indent=1, ensure_ascii=False)
    for n, v in res["images"].items():
        print(f"{n:28s} back {v['back_dE']:6.2f} body {v['body_dE']} C {v['chroma']:6.2f} "
              f"bodyLab {v['body_lab']} backLab {v['back_lab']}")


if __name__ == "__main__":
    main()
