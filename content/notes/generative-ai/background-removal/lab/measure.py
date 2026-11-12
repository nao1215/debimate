"""切り抜いた絵の取り残し・半透明の縁・縁の色を数える。

使い方: python measure.py <PNG の保存先> <metrics.json>
  <名前>.png（描いた絵）と、マスク <名前>_node.png / _plain.png / _imagenet.png（255 が人物）を読む。
  背景の色 B: 絵の上端 24 画素と、上から 8 割までの左右の端 24 画素の RGB の中央値（無地の背景を頼んでいる）
  色の差は CIELAB の ΔE（CIE76）。色の変換は OpenCV の cvtColor（0〜1 の float の RGB を sRGB として扱う）
  leftover   不透明（α ≥ 0.5）で、B との差が 10 未満の画素のうち、同じ条件の画素をたどって透明な所（α < 0.5）に
             つながる塊の画素数。色で取り残しを消す処理（clean）が消す画素と同じ
  enclosed   不透明で B との差が 10 未満の画素の塊のうち、透明な所につながらず、50 画素以上のもの（髪の輪に囲まれた背景など。
             色で消す処理では消えない）の画素数
  semi       半透明（0.02 < α < 0.98）の画素数
  fringe     半透明の画素を暗い背景 D（RGB 24, 28, 40）に重ねた色と、あるべき色の差の平均（ΔE）。
             あるべき色は、いちばん近い不透明（α ≥ 0.98）の画素の色と D を α で混ぜた色
  opaque255  人物の画素のうち、α がちょうど 1（8 bit で 255）の割合
  inner_dE   人物の内側（α ≥ 0.98）を黒と白の背景へ置いた 2 つの色の差の平均（ΔE）。人物が透けている量の目安
  fringe_unmix  半透明の画素の色から B を差し引いて（F = (I − (1 − α)B) / α）から重ねた時の、同じ差の平均
"""
import glob
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image
from scipy import ndimage

DARK = np.array([24, 28, 40], np.float32) / 255
VARIANTS = ("node", "plain", "imagenet")


def lab(rgb):
    return cv2.cvtColor(rgb.astype(np.float32), cv2.COLOR_RGB2Lab)


def background(rgb):
    h, w, _ = rgb.shape
    strip = np.concatenate([rgb[:24].reshape(-1, 3), rgb[:int(h * 0.8), :24].reshape(-1, 3),
                            rgb[:int(h * 0.8), -24:].reshape(-1, 3)])
    return np.median(strip, axis=0)


def leftover(rgb, alpha, back, tol=10.0):
    """色で消す処理の対象: B に近い不透明な画素の塊のうち、透明な所に接するもの。"""
    d = np.linalg.norm(lab(rgb) - lab(back[None, None]), axis=-1)
    near = (alpha >= 0.5) & (d < tol)
    clear = ndimage.binary_dilation(alpha < 0.5, iterations=1)
    labels, _ = ndimage.label(near, structure=np.ones((3, 3)))
    keep = np.unique(labels[near & clear])
    return np.isin(labels, keep[keep > 0])


def enclosed(rgb, alpha, back, tol=10.0, min_size=50):
    d = np.linalg.norm(lab(rgb) - lab(back[None, None]), axis=-1)
    near = (alpha >= 0.5) & (d < tol) & ~leftover(rgb, alpha, back, tol)
    labels, n = ndimage.label(near, structure=np.ones((3, 3)))
    sizes = ndimage.sum(near, labels, range(1, n + 1))
    return np.isin(labels, np.nonzero(sizes >= min_size)[0] + 1)


def clean(alpha, rgb, back):
    """取り残しを透明にしたαを返す（2 回かける。1 回目で開いた穴の奥の塊も透明な所に接するようになる）。"""
    a = alpha.copy()
    for _ in range(2):
        a[leftover(rgb, a, back)] = 0
    return a


def inner_de(rgb, alpha):
    inner = alpha >= 0.98
    a = alpha[..., None]
    on_black, on_white = a * rgb, a * rgb + (1 - a)
    return round(float(np.linalg.norm(lab(on_black) - lab(on_white), axis=-1)[inner].mean()), 2)


def fringe(rgb, alpha, back):
    semi = (alpha > 0.02) & (alpha < 0.98)
    _, idx = ndimage.distance_transform_edt(alpha < 0.98, return_indices=True)
    near_fg = rgb[idx[0], idx[1]]
    a = alpha[..., None]
    want = a * near_fg + (1 - a) * DARK
    raw = a * rgb + (1 - a) * DARK
    fg = np.clip((rgb - (1 - a) * back) / np.maximum(a, 0.05), 0, 1)
    unmix = a * fg + (1 - a) * DARK
    lw = lab(want)
    return (float(np.linalg.norm(lab(raw) - lw, axis=-1)[semi].mean()),
            float(np.linalg.norm(lab(unmix) - lw, axis=-1)[semi].mean()))


def main():
    out, dst = sys.argv[1:3]
    res = {}
    for path in sorted(glob.glob(os.path.join(out, "*_*_*.png"))):
        name = os.path.basename(path)[:-4]
        if name.count("_") != 2:
            continue
        rgb = np.asarray(Image.open(path).convert("RGB"), np.float32) / 255
        back = background(rgb)
        r = {"back_rgb": [round(float(v) * 255, 1) for v in back]}
        for v in VARIANTS:
            mp = os.path.join(out, f"{name}_{v}.png")
            if not os.path.exists(mp):
                continue
            alpha = np.asarray(Image.open(mp).convert("L"), np.float32) / 255
            left = leftover(rgb, alpha, back)
            f_raw, f_unmix = fringe(rgb, alpha, back)
            r[v] = {"person": int((alpha >= 0.5).sum()), "leftover": int(left.sum()),
                    "enclosed": int(enclosed(rgb, alpha, back).sum()),
                    "cleaned": int(((alpha >= 0.5) & (clean(alpha, rgb, back) < 0.5)).sum()),
                    "opaque255": round(float((alpha[alpha >= 0.5] >= 1.0).mean()), 3),
                    "inner_dE": inner_de(rgb, alpha),
                    "semi": int(((alpha > 0.02) & (alpha < 0.98)).sum()),
                    "fringe": round(f_raw, 2), "fringe_unmix": round(f_unmix, 2)}
        if "plain" in r and "imagenet" in r:
            a = np.asarray(Image.open(os.path.join(out, f"{name}_plain.png")).convert("L")) >= 128
            b = np.asarray(Image.open(os.path.join(out, f"{name}_imagenet.png")).convert("L")) >= 128
            r["plain_vs_imagenet_diff"] = int((a ^ b).sum())
        if "node" in r and "plain" in r:
            a = np.asarray(Image.open(os.path.join(out, f"{name}_node.png")).convert("L"), np.int16)
            b = np.asarray(Image.open(os.path.join(out, f"{name}_plain.png")).convert("L"), np.int16)
            r["node_vs_plain_maxdiff"] = int(np.abs(a - b).max())
        res[name] = r
        print(name, json.dumps(r, ensure_ascii=False), flush=True)
    json.dump(res, open(dst, "w"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
