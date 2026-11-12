"""ComfyUI 本体の MediaPipe の顔検出を、ノードと同じ関数で呼び、顔の枠を JSON に書く。

使い方: <ComfyUI の venv の python> -I detect.py <ComfyUI のディレクトリ> <JSON の保存先> <PNG> [<PNG> ...]
  PNG ごとに、検出器の 2 種類（short・full）× 確信度のしきい値（0.5・0.1）で、最も確信度の高い 1 つの枠を記録する。
  short は ComfyUI の MediaPipeFaceLandmarker ノードの既定（2 m 以内の近い顔向け）、full は遠くの小さな顔向け。
  しきい値 0.5 はノードの既定（min_confidence）。
  枠は [x1, y1, x2, y2]（画素）。見つからなければ空のリスト。
  中で呼ぶのは comfy_extras/nodes_mediapipe.py の FaceLandmarkerModel.detect_batch で、ノードの execute と同じ。
"""
import json
import os
import sys

import numpy as np
import torch
from PIL import Image

COMFY_DIR, OUT = sys.argv[1:3]
PNGS = sys.argv[3:]
sys.path.insert(0, COMFY_DIR)
import comfy.utils  # noqa: E402
from comfy_extras.nodes_mediapipe import FaceLandmarkerModel  # noqa: E402

torch.set_grad_enabled(False)


def main():
    sd = comfy.utils.load_torch_file(os.path.join(COMFY_DIR, "models", "detection", "mediapipe_face_fp32.safetensors"),
                                     safe_load=True)
    model = FaceLandmarkerModel(sd)
    res = json.load(open(OUT)) if os.path.exists(OUT) else {}
    for path in PNGS:
        img = np.asarray(Image.open(path).convert("RGB"))
        found = {}
        for variant in ("short", "full"):
            for th in (0.5, 0.1):
                faces = model.detect_batch([img], num_faces=1, score_thresh=th, variant=variant)[0]
                found[f"{variant}_{th}"] = [{"score": round(float(f["score"]), 3),
                                             "box": [int(round(float(v))) for v in f["bbox_xyxy"]]} for f in faces]
        res[os.path.basename(path)[:-4]] = found
        print(os.path.basename(path), found, flush=True)
    json.dump(res, open(OUT, "w"), indent=1)


if __name__ == "__main__":
    main()
