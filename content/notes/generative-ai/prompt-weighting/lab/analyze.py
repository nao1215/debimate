"""run.py が保存した PNG の色を数え、条件ごとに seed で平均して表にする。

指標（どれも全画素で数える。1024 x 1024 = 1,048,576 画素）
  sat     : HSV の彩度の平均（0〜1）
  neon    : 蛍光色に寄った画素の割合。Pillow の HSV（0〜255）で S > 190 かつ V > 170、
            かつ色相が 40〜250（赤と赤紫を除く、黄〜緑〜青〜紫）の画素
  red     : 赤い画素の割合。色相が 0〜10 または 245〜255、S > 90、V > 50
  white   : 白い画素の割合。S < 30 かつ V > 200
  blue    : 青い画素の割合。色相が 140〜185、S > 90、V > 50
  yellow  : 黄色い画素の割合。色相が 25〜50、S > 120、V > 120（実験 1 のレモン）
  dark    : 黒に近い画素の割合。V < 60（実験 4 の黒い服）
  diff    : 基準の条件（同じ seed）との画素の差。RGB の絶対差の平均（0〜255）

使い方:
    uv run --with numpy --with pillow python analyze.py <保存先> <実験名> [結果の JSON]
"""
import json
import os
import sys
from collections import defaultdict

import numpy as np
from PIL import Image

import conditions

BASELINE = {"positive": "w1.0", "negative": "w1.0", "position": "none", "ablation": "full",
            "lighting": "none_neg1.0"}


def metrics(path):
    im = Image.open(path).convert("RGB")
    rgb = np.asarray(im, dtype=np.int16)
    hsv = np.asarray(im.convert("HSV"), dtype=np.int16)
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    return rgb, {
        "sat": float((s / 255).mean()),
        "neon": float(((s > 190) & (v > 170) & (h >= 40) & (h <= 250)).mean()),
        "red": float((((h <= 10) | (h >= 245)) & (s > 90) & (v > 50)).mean()),
        "white": float(((s < 30) & (v > 200)).mean()),
        "blue": float(((h >= 140) & (h <= 185) & (s > 90) & (v > 50)).mean()),
        "yellow": float(((h >= 25) & (h <= 50) & (s > 120) & (v > 120)).mean()),
        "dark": float((v < 60).mean()),
    }


def main():
    out_dir, exp = sys.argv[1], sys.argv[2]
    json_out = sys.argv[3] if len(sys.argv) > 3 else None
    d = os.path.join(out_dir, exp)
    conds = conditions.EXPERIMENTS[exp]()
    base_rgb = {}
    for c in conds:
        if c["name"] == BASELINE[exp]:
            base_rgb[c["seed"]] = metrics(os.path.join(d, f"{c['name']}_s{c['seed']}.png"))[0]

    rows, order = defaultdict(list), []
    for c in conds:
        rgb, m = metrics(os.path.join(d, f"{c['name']}_s{c['seed']}.png"))
        m["diff"] = float(np.abs(rgb - base_rgb[c["seed"]]).mean())
        m["seed"] = c["seed"]
        if c["name"] not in rows:
            order.append(c["name"])
        rows[c["name"]].append(m)

    keys = ["sat", "neon", "red", "white", "blue", "yellow", "dark", "diff"]
    print(f"{'condition':<22}" + "".join(f"{k:>8}" for k in keys) + "   (mean of seeds)")
    summary = []
    for name in order:
        ms = rows[name]
        mean = {k: sum(m[k] for m in ms) / len(ms) for k in keys}
        print(f"{name:<22}" + "".join(f"{mean[k]:8.3f}" if k != "diff" else f"{mean[k]:8.1f}"
                                      for k in keys))
        summary.append({"name": name, **{k: round(mean[k], 4) for k in keys},
                        "per_seed": [{k: round(m[k], 4) for k in keys + ["seed"]} for m in ms]})
    if json_out:
        with open(json_out, "w") as f:
            json.dump(summary, f, indent=1)


if __name__ == "__main__":
    main()
