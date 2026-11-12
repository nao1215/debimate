"""顔の周りで切り抜いてから、MediaPipe の short（しきい値 0.5、ノードの既定）で顔を拾えるかを数える。

使い方: <ComfyUI の venv の python> -I detect_crop.py <ComfyUI のディレクトリ> <作業先> <背景除去のノートの gen> <JSON の保存先>
  detect_yolo.json の face_yolov8n の枠の中心を中心に、一辺 600・400・250 画素の正方形を切り抜く
  （枠の幅は約 118 画素なので、顔の幅は切り抜いた絵の幅の 2・3・5 割ほど）。
  返った枠の中心が切り抜いた絵の中心から 60 画素以内なら「顔に当たった」と数える。
"""
import json
import os
import sys

import numpy as np
import torch
from PIL import Image

COMFY_DIR, WORK, BGR_GEN, OUT = sys.argv[1:5]
sys.path.insert(0, COMFY_DIR)
import comfy.utils  # noqa: E402
from comfy_extras.nodes_mediapipe import FaceLandmarkerModel  # noqa: E402

torch.set_grad_enabled(False)


def main():
    model = FaceLandmarkerModel(comfy.utils.load_torch_file(
        os.path.join(COMFY_DIR, "models", "detection", "mediapipe_face_fp32.safetensors"), safe_load=True))
    yolo = json.load(open(os.path.join(WORK, "detect_yolo.json")))
    res = {}
    for side in (600, 400, 250):
        hit = []
        for name, faces in yolo.items():
            im = Image.open(os.path.join(WORK, "gen", name + ".png") if name.startswith("base_")
                            else os.path.join(BGR_GEN, name + ".png")).convert("RGB")
            b = faces[0]["box"]
            cx, cy = (b[0] + b[2]) // 2, (b[1] + b[3]) // 2
            crop = np.asarray(im.crop((cx - side // 2, cy - side // 2, cx + side // 2, cy + side // 2)))
            found = model.detect_batch([crop], num_faces=1, score_thresh=0.5, variant="short")[0]
            ok = False
            if found:
                x1, y1, x2, y2 = found[0]["bbox_xyxy"]
                ok = abs((x1 + x2) / 2 - side / 2) < 60 and abs((y1 + y2) / 2 - side / 2) < 60
            if ok:
                hit.append(name)
        res[str(side)] = {"images": len(yolo), "on_face": len(hit)}
        print(side, res[str(side)], flush=True)
    json.dump(res, open(OUT, "w"), indent=1)


if __name__ == "__main__":
    main()
