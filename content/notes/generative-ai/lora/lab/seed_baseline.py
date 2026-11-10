"""無関係な画像どうしの画素の差を数え、to_webp.py の差の「上限の目安」にする。

LoRA を使わず（強さ 0）、seed だけを変えた 5 枚を生成し、全ての組（10 組）の
画素の差（RGB の絶対差の平均、0〜255）を出す。seed が違えば構図は別物になる。
保存先に同じ名前の PNG があれば、生成せずに差だけを数える。
run_sweep.py の post_json() と get_json() を使う。Pillow と NumPy を使う。

使い方:
    python3 seed_baseline.py <保存先ディレクトリ> [ComfyUI の URL]
"""
import copy
import itertools
import json
import os
import sys
import time
import urllib.parse
import urllib.request

import numpy as np
from PIL import Image

from run_sweep import HERE, get_json, post_json

SEEDS = [20261110, 20261111, 20261112, 20261113, 20261114]


def main():
    out_dir = sys.argv[1]
    base = sys.argv[2] if len(sys.argv) > 2 else "http://127.0.0.1:8188"
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(HERE, "workflow_api.json")) as f:
        workflow = json.load(f)

    paths = []
    for seed in SEEDS:
        dst = os.path.join(out_dir, f"seed_{seed}.png")
        paths.append(dst)
        if os.path.exists(dst):                      # 生成済みなら差を数えるだけ
            continue
        wf = copy.deepcopy(workflow)
        wf["2"]["inputs"]["strength_model"] = 0.0   # LoRA なし（ベースモデルだけ）
        wf["2"]["inputs"]["strength_clip"] = 0.0
        wf["7"]["inputs"]["seed"] = seed
        wf["9"]["inputs"]["filename_prefix"] = f"debimate_lora/seed_{seed}"
        pid = post_json(base, "/prompt", {"prompt": wf, "client_id": "debimate-lora"})[
            "prompt_id"]
        while pid not in (hist := get_json(base, f"/history/{pid}")):
            time.sleep(3)
        img = hist[pid]["outputs"]["9"]["images"][0]
        q = urllib.parse.urlencode({"filename": img["filename"],
                                    "subfolder": img["subfolder"], "type": img["type"]})
        with urllib.request.urlopen(f"{base}/view?{q}") as r, open(dst, "wb") as f:
            f.write(r.read())

    arrs = [np.asarray(Image.open(p).convert("RGB"), dtype=np.int16) for p in paths]
    diffs = []
    for (i, a), (j, b) in itertools.combinations(enumerate(arrs), 2):
        d = float(np.abs(a - b).mean())
        diffs.append(d)
        print(f"seed {SEEDS[i]} vs {SEEDS[j]}: {d:6.2f}")
    summary = {"min": round(min(diffs), 2), "mean": round(sum(diffs) / len(diffs), 2),
               "max": round(max(diffs), 2)}
    print(f"min={summary['min']:.2f}  mean={summary['mean']:.2f}  max={summary['max']:.2f}")
    with open(os.path.join(HERE, "seed_baseline.json"), "w") as f:   # figures.py が使う
        json.dump(summary, f, indent=2)


if __name__ == "__main__":
    main()
