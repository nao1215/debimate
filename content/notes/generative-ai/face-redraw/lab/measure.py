"""顔の描き直しと、全体を 2 倍で描き直して縮めた絵を比べる。色と差は表示する大きさ（832 x 1216）で数える。

使い方: python measure.py <作業先> <JSON の保存先>
  <作業先>/gen に run.py の出力、<作業先>/detect.json に detect.py の出力、<作業先>/log_face.json に顔の描き直しの記録がある前提。
項目（絵ごと。範囲はどれも base の絵で見つけた顔の枠）:
  face_px      顔の枠の幅と高さ（画素）。潜在（VAE が 1/8 に縮めた格子）では 8 で割ったマス数になる
  line_drawn   描いた解像度での線の太さの平均（画素）。周りより暗い細い線（明るさのブラックハット 9 x 9 が 25 以上）を線とし、
               線の画素数 ÷ 細線化した長さ。ブラックハットの窓は、表示する大きさに対する解像度の倍率だけ広げる。範囲は base と hires が頭（顔の枠を 3 倍に広げた正方形。hires は座標も 2 倍）、
               顔の描き直しは描き直した 1024 x 1024 の絵の全体
  line_display line_drawn を表示する大きさ（832 x 1216）に換算した太さ。hires は 1/2 倍、顔の描き直しは 切り抜いた辺 / 1024 倍。
               表示する大きさに縮めた絵で直に数えると、2 画素より細い線はぼけて 2 画素前後に見えるので、描いた解像度で数えて換算する
  diff         base と比べた、顔の枠の中の RGB の差の平均（0〜255）
  outside      顔の描き直しで、貼り戻すマスクの外が base と同じか（差の最大値。0 なら同じ）
  band_de      貼り戻すマスクのぼかしの帯（マスクの値が 0.1〜0.9）で、描き直した絵と base の色の差（CIE76 の ΔE の平均）
hires は、色と差は 1664 x 2432 を area で 832 x 1216 に縮めてから数える。
"""
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image
from skimage.morphology import skeletonize

WORK, OUT = sys.argv[1:3]
GEN = os.path.join(WORK, "gen")
W, H = 832, 1216


def load(name):
    im = Image.open(os.path.join(GEN, name + ".png")).convert("RGB")
    if im.size != (W, H):
        im = im.resize((W, H), Image.BOX)
    return np.asarray(im)


def gray(rgb):
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)


def lab(rgb):
    return cv2.cvtColor(rgb.astype(np.float32) / 255, cv2.COLOR_RGB2LAB)


def head(box, factor=3.0):
    x1, y1, x2, y2 = box
    side = int(max(x2 - x1, y2 - y1) * factor)
    cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
    x, y = max(cx - side // 2, 0), max(cy - side // 2, 0)
    return x, y, min(x + side, W), min(y + side, H)


def line_mask(rgb, scale=1.0):
    """表示の大きさで 9 x 9 のブラックハット。scale 倍の解像度の絵では、窓も scale 倍にする（太い線を取りこぼさない）。"""
    g = gray(rgb)
    n = int(round(9 * scale)) | 1
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (n, n))
    return cv2.morphologyEx(g, cv2.MORPH_BLACKHAT, k) >= 25


def line_w(rgb, scale=1.0):
    m = line_mask(rgb, scale)
    sk = skeletonize(m).sum()
    return float(m.sum() / sk) if sk else None


def raw(name):
    return np.asarray(Image.open(os.path.join(GEN, name + ".png")).convert("RGB"))


def mean_diff(a, b, box):
    x1, y1, x2, y2 = box
    return float(np.abs(a[y1:y2, x1:x2].astype(np.float32) - b[y1:y2, x1:x2].astype(np.float32)).mean())


def blend_mask(geo):
    """run.py の face_workflow と同じマスク（矩形をぼかす）を、絵全体の座標で作る。"""
    m = np.zeros((H, W), np.float32)
    x, y, w, h = geo["mask"]
    cx0, cy0, side = geo["crop"]
    sub = np.zeros((side, side), np.float32)
    sub[y - cy0:y - cy0 + h, x - cx0:x - cx0 + w] = 1
    r = geo["blur"]
    sub = cv2.GaussianBlur(sub, (2 * r + 1, 2 * r + 1), r / 2)
    m[cy0:cy0 + side, cx0:cx0 + side] = sub
    return m


def main():
    det = json.load(open(os.path.join(WORK, "detect.json")))
    log = json.load(open(os.path.join(WORK, "log_face.json")))
    hires_log = json.load(open(os.path.join(WORK, "log_hires.json")))
    base_log = json.load(open(os.path.join(WORK, "log_base.json")))
    res = {}
    for seed in sorted({k.split("_")[1] for k in log}):
        b = f"base_{seed}"
        box = (det[b]["full_0.5"] or det[b]["full_0.1"])[0]["box"]
        base = load(b)
        hx1, hy1, hx2, hy2 = head(box)
        lb = line_w(base[hy1:hy2, hx1:hx2])
        row = {"face_px": [box[2] - box[0], box[3] - box[1]],
               "base": {"line_drawn": lb, "line_display": lb, "seconds": base_log[b]["seconds"]}}
        lh = line_w(raw(f"hires_{seed}")[hy1 * 2:hy2 * 2, hx1 * 2:hx2 * 2], 2.0)
        hi = load(f"hires_{seed}")
        row["hires"] = {"line_drawn": lh, "line_display": lh / 2, "diff": mean_diff(hi, base, box),
                        "seconds": hires_log[f"hires_{seed}"]["seconds"]}
        big_log = os.path.join(WORK, "log_big.json")
        if os.path.exists(big_log):
            row["big"] = {"seconds": json.load(open(big_log))[f"big_{seed}"]["seconds"]}
        for name, geo in log.items():
            if not name.startswith(f"face_{seed}_"):
                continue
            f = load(name)
            m = blend_mask(geo)
            redrawn = raw(name + "_crop")
            crop = cv2.resize(redrawn, (geo["crop"][2],) * 2, interpolation=cv2.INTER_AREA)
            x, y, s = geo["crop"]
            lf = line_w(redrawn, 1024 / s)
            pasted = base.copy()
            pasted[y:y + s, x:x + s] = crop
            band = (m > 0.1) & (m < 0.9)
            de = np.linalg.norm(lab(pasted) - lab(base), axis=-1)
            row[name[len(f"face_{seed}_"):]] = {
                "line_drawn": lf, "line_display": lf * s / 1024, "diff": mean_diff(f, base, box),
                "outside": int(np.abs(f.astype(int) - base.astype(int))[m == 0].max()),
                "band_de": float(de[band].mean()), "seconds": geo["seconds"]}
        res[seed] = row
        print(seed, json.dumps(row, ensure_ascii=False), flush=True)
    json.dump(res, open(OUT, "w"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
