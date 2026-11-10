"""生成した絵が下絵にどれだけ近いかを数える。

  ssim        : 下絵（実際に渡したもの）と出力の SSIM。両方を灰色にし 256x256 に縮めて計算
  edge_f1     : 下絵の図形の輪郭（shapes.json から描いた線）と、出力の Canny エッジの一致。
                recall は輪郭のうち 4 px（256x256 上）以内に出力のエッジがある割合、precision は
                出力のエッジのうち輪郭から 4 px 以内にある割合で、その調和平均。
                下絵に無い模様（木目など）が増えると precision が下がる
  delta_e     : 色の付いた下絵（blurred）と出力を 32x32 に縮め、CIELAB の色差 CIEDE2000 を
                平均したもの。灰色の下絵から描いた絵も、狙った色の配置（blurred）と比べる
  chroma      : 出力の彩度（CIELAB の a*, b* の長さ）の平均
  flat        : 図形の内側（縁から 24 px 内側）の明るさの標準偏差の平均。小さいほど平らな板

使い方: python3 metrics.py <下絵のディレクトリ> <PNG のディレクトリ> <結果の JSON> [下絵の名前 ...]
"""
import json
import os
import sys

import numpy as np
from scipy import ndimage
from PIL import Image, ImageDraw
from skimage import color, feature, metrics, morphology

DENOISES = [0.3, 0.45, 0.6, 0.75, 0.86, 0.95, 1.0]


def load(path, size=None):
    im = Image.open(path).convert("RGB")
    if size:
        im = im.resize((size, size), Image.LANCZOS)
    return np.asarray(im, dtype=np.float64) / 255.0


def shape_masks(spec, size, shrink=0):
    """図形ごとのマスク（shrink は縁から内側へ削る画素数、元の 1024 px 基準）。"""
    k = size / spec["size"]
    masks = []
    for s in spec["shapes"]:
        m = Image.new("L", (size, size), 0)
        x0, y0, x1, y1 = [v * k for v in s["box"]]
        box = (x0 + shrink * k, y0 + shrink * k, x1 - shrink * k, y1 - shrink * k)
        (ImageDraw.Draw(m).rectangle if s["kind"] == "rect" else ImageDraw.Draw(m).ellipse)(box, fill=255)
        masks.append(np.asarray(m) > 0)
    return masks


def outline(spec, size):
    """下絵の輪郭: 図形の縁と、壁と机の境目（図形の外側だけ）。"""
    masks = shape_masks(spec, size)
    edge = np.zeros((size, size), bool)
    for m in masks:
        edge |= m & ~ndimage.binary_erosion(m)
    y = int(spec["table_top"] * size / spec["size"])
    covered = np.any(masks, axis=0)
    edge[y, :] |= ~covered[y, :]
    return edge


def measure(sketch_png, out_png, spec, color_ref):
    s256, o256 = load(sketch_png, 256), load(out_png, 256)
    ssim = metrics.structural_similarity(color.rgb2gray(s256), color.rgb2gray(o256), data_range=1.0)
    edges = feature.canny(color.rgb2gray(o256), sigma=2.0)
    near = morphology.binary_dilation(edges, morphology.disk(4))
    ref = outline(spec, 256)
    recall = float(near[ref].mean())
    precision = float(morphology.binary_dilation(ref, morphology.disk(4))[edges].mean()) if edges.any() else 0.0
    edge_f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    s32, o32 = load(color_ref, 32), load(out_png, 32)
    de = color.deltaE_ciede2000(color.rgb2lab(s32), color.rgb2lab(o32)).mean()
    lab = color.rgb2lab(load(out_png, 256))
    chroma = np.hypot(lab[..., 1], lab[..., 2]).mean()
    gray512 = color.rgb2gray(load(out_png, 512))
    flat = float(np.mean([gray512[m].std() for m in shape_masks(spec, 512, shrink=24)]))
    return {"ssim": round(float(ssim), 3), "edge_f1": round(edge_f1, 3),
            "edge_recall": round(recall, 3), "edge_precision": round(precision, 3),
            "delta_e": round(float(de), 1), "chroma": round(float(chroma), 1),
            "flat": round(flat * 255, 1)}


def main():
    sketch_dir, png_dir, out_json = sys.argv[1:4]
    names = sys.argv[4:] or ["crisp", "blurred", "gray"]
    spec = json.load(open(os.path.join(sketch_dir, "shapes.json")))
    rows = []
    for name in names:
        sk = os.path.join(sketch_dir, f"sketch_{name}.png")
        ref = os.path.join(sketch_dir, "sketch_blurred.png")
        base = measure(sk, sk, spec, ref)
        print(f"{name:8s} sketch : chroma={base['chroma']:5.1f} flat={base['flat']:5.1f}")
        for d in DENOISES:
            png = os.path.join(png_dir, f"{name}_{int(round(d * 100)):03d}.png")
            if not os.path.exists(png):
                continue
            m = measure(sk, png, spec, ref)
            m.update({"sketch": name, "denoise": d})
            rows.append(m)
            print(f"{name:8s} d={d:4.2f}: ssim={m['ssim']:.3f} edge_f1={m['edge_f1']:.3f} "
                  f"dE={m['delta_e']:5.1f} chroma={m['chroma']:5.1f} flat={m['flat']:5.1f}")
    # 対照: 下絵を使わない txt2img（run_extra.py control）を、crisp の下絵と比べる
    ctrl = os.path.join(png_dir, "control_txt2img.png")
    if os.path.exists(ctrl):
        m = measure(os.path.join(sketch_dir, "sketch_crisp.png"), ctrl, spec,
                    os.path.join(sketch_dir, "sketch_blurred.png"))
        m.update({"sketch": "control_txt2img", "denoise": None})
        rows.append(m)
        print(f"txt2img (no sketch) vs crisp: ssim={m['ssim']:.3f} edge_f1={m['edge_f1']:.3f} "
              f"dE={m['delta_e']:5.1f} chroma={m['chroma']:5.1f} flat={m['flat']:5.1f}")
    with open(out_json, "w") as f:
        json.dump(rows, f, indent=1)


if __name__ == "__main__":
    main()
