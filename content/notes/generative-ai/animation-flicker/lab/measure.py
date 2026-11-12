"""4 コマの絵の、隣り合うコマの差を「人形が動いていない所」だけで測る。

人形は左腕しか動かさないので、胴・脚・頭の大半は 4 コマで同じ位置にある。そこで絵の色が変われば、
それは動きではなく、ちらつきである。並べて 1 枚と大きさを揃えるため、どの絵も 1 コマ 384 x 768 に縮めて測る
（832 x 1216 の絵は縦 768 に縮め、横の中央 384 を切り出す。カメラの縦の範囲と中心は同じ）。

止まっている所: 4 コマとも人形の体があり、1 コマ目からの動きが 0.5 画素未満の画素から、動く画素の 24 画素以内
（832 x 1216 での値）を除いた所。
差: RGB の各値（0〜255）の差の絶対値の平均。コマ 1→2、2→3、3→4 の 3 つの平均を出す。

腕が付いてきたか: 4 コマ目で人形の腕が新しく入った所（1 コマ目には体が無く、4 コマ目には体がある画素）のうち、
絵が背景でない画素の割合。背景は、絵の縁 8 画素の色の中央値から RGB の差の合計が 32 未満の画素とする
（depth-body-shape の body_metrics.py と同じ決め方）。人形どおりに腕が上がれば 1 に近く、上がらなければ 0 に近い。

使い方: python3 measure.py <render_frames.py の出力先> <生成した PNG のディレクトリ> <結果の JSON>
"""
import json
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

from warp import FRAMES, doll_flow, load_coords

CELL = (384, 768)


def to_cell(img):
    """832 x 1216 の絵を、並べた 1 枚の 1 コマと同じ範囲・大きさにする。"""
    w = round(img.width * CELL[1] / img.height)
    img = img.resize((w, CELL[1]), Image.LANCZOS)
    x = (w - CELL[0]) // 2
    return img.crop((x, 0, x + CELL[0], CELL[1]))


def static_mask(passes):
    body_all, moving = None, None
    for f in FRAMES[1:]:
        flow, good, body = doll_flow(passes, "gen", f)
        mag = np.hypot(flow[..., 0], flow[..., 1])
        still = good & (mag < 0.5)
        body_all = body if body_all is None else body_all & body
        mv = body & ~still
        moving = mv if moving is None else moving | mv
    near_moving = ndimage.distance_transform_edt(~moving) <= 24
    mask = body_all & ~near_moving
    return to_cell(Image.fromarray((mask * 255).astype(np.uint8))).point(lambda v: 255 if v > 200 else 0)


def arm_region(passes):
    _, b0 = load_coords(passes, "gen", "f0")
    _, b3 = load_coords(passes, "gen", "f3")
    region = b3 & ~ndimage.binary_dilation(b0, iterations=6)
    return to_cell(Image.fromarray((region * 255).astype(np.uint8))).point(lambda v: 255 if v > 200 else 0)


def follow(frames, region):
    a = np.asarray(frames[-1], np.int32)
    border = np.concatenate([a[:8].reshape(-1, 3), a[-8:].reshape(-1, 3), a[:, :8].reshape(-1, 3), a[:, -8:].reshape(-1, 3)])
    bg = np.median(border, 0)
    fg = np.abs(a - bg).sum(-1) >= 32
    r = np.array(region) > 0
    return float(fg[r].mean())


def frames_of(gen, method, seed):
    if method == "sheet":
        sheet = Image.open(os.path.join(gen, f"sheet_{seed}.png")).convert("RGB")
        return [sheet.crop((CELL[0] * i, 0, CELL[0] * (i + 1), CELL[1])) for i in range(4)]
    names = {"redraw": [f"redraw_{f}_{seed}" for f in FRAMES],
             "img2img": [f"img2img_{f}_{seed}" for f in FRAMES],
             "img2img60": [f"img2img60_{f}_{seed}" for f in FRAMES],
             "img2img75": [f"img2img75_{f}_{seed}" for f in FRAMES],
             # 元の 1 コマ目のあとに、描き直した 2〜4 コマ目を続けた場合
             "img2img_keep": [f"redraw_f0_{seed}"] + [f"img2img_{f}_{seed}" for f in FRAMES[1:]]}
    if method.startswith("warp_"):
        names[method] = [f"{method}_{seed}_{f}" for f in FRAMES]
    return [to_cell(Image.open(os.path.join(gen, n + ".png")).convert("RGB")) for n in names[method]]


def flicker(frames, mask):
    m = np.array(mask) > 0
    a = [np.asarray(f, np.float32) for f in frames]
    return [float(np.abs(a[i + 1] - a[i])[m].mean()) for i in range(len(a) - 1)]


if __name__ == "__main__":
    from run_frames import SEEDS
    passes, gen, out = sys.argv[1:4]
    mask = static_mask(passes)
    mask.save(os.path.join(gen, "static_mask.png"))
    region = arm_region(passes)
    region.save(os.path.join(gen, "arm_region.png"))
    methods = ["redraw", "img2img", "img2img60", "img2img75", "img2img_keep", "sheet", "warp_gen_s20", "warp_gen_s3", "warp_uv_s3", "warp_uv_s20"]
    res = {"static_pixels": int((np.array(mask) > 0).sum()), "arm_pixels": int((np.array(region) > 0).sum()),
           "cell": CELL}
    for method in methods:
        for seed in SEEDS:
            try:
                frames = frames_of(gen, method, seed)
                d = flicker(frames, mask)
            except FileNotFoundError:
                continue
            res[f"{method}_{seed}"] = {"pairs": [round(v, 2) for v in d], "mean": round(sum(d) / len(d), 2),
                                    "arm_follow": round(follow(frames, region), 3)}
            print(method, seed, res[f"{method}_{seed}"])
    json.dump(res, open(out, "w"), indent=1)
