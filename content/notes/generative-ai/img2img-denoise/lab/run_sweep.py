"""下絵 3 種 × denoise 7 段を、同じ seed で 1 枚ずつ生成する。

使い方: python3 run_sweep.py <下絵のディレクトリ> <PNG の保存先> [下絵の名前 ...]
  下絵の名前は crisp / blurred / gray（省略時は 3 種とも）
結果（prompt_id・秒数・送る直前の負荷）は <PNG の保存先>/sweep_log.json に追記する。
"""
import copy
import json
import os
import sys

import comfy

HERE = os.path.dirname(os.path.abspath(__file__))
DENOISES = [0.3, 0.45, 0.6, 0.75, 0.86, 0.95, 1.0]


def main():
    sketch_dir, out = sys.argv[1], sys.argv[2]
    names = sys.argv[3:] or ["crisp", "blurred", "gray"]
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(HERE, "workflow_img2img.json")) as f:
        workflow = json.load(f)
    log_path = os.path.join(out, "sweep_log.json")
    log = json.load(open(log_path)) if os.path.exists(log_path) else []
    for name in names:
        image = comfy.upload(os.path.join(sketch_dir, f"sketch_{name}.png"))
        for d in DENOISES:
            wf = copy.deepcopy(workflow)
            wf["5"]["inputs"]["image"] = image
            wf["7"]["inputs"]["denoise"] = d
            png = os.path.join(out, f"{name}_{int(round(d * 100)):03d}.png")
            r = comfy.run(wf, png, "9")
            r.update({"sketch": name, "denoise": d, "png": os.path.basename(png)})
            print(json.dumps(r, ensure_ascii=False), flush=True)
            log.append(r)
            with open(log_path, "w") as f:
                json.dump(log, f, indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
