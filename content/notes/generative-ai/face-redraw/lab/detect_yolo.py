"""比べのために、アニメ調の顔も学習した顔検出（Bingsu/adetailer の face_yolov8n.pt）で顔の枠を JSON に書く。

使い方: python detect_yolo.py <face_yolov8n.pt> <JSON の保存先> <PNG> [<PNG> ...]
  確信度のしきい値は ADetailer の既定（ad_confidence 0.3）。最も確信度の高い 1 つの枠を [x1, y1, x2, y2] で記録する。
  ultralytics（AGPL-3.0）が要る。uv run --with ultralytics==8.3.40 で一時環境に入れて動かした。
"""
import json
import os
import sys

from ultralytics import YOLO

WEIGHTS, OUT = sys.argv[1:3]


def main():
    model = YOLO(WEIGHTS)
    res = json.load(open(OUT)) if os.path.exists(OUT) else {}
    for path in sys.argv[3:]:
        r = model.predict(path, conf=0.3, device="cpu", verbose=False)[0]
        boxes = sorted(zip(r.boxes.conf.tolist(), r.boxes.xyxy.tolist()), reverse=True)
        res[os.path.basename(path)[:-4]] = [{"score": round(s, 3), "box": [int(round(v)) for v in b]}
                                            for s, b in boxes]
        print(os.path.basename(path), res[os.path.basename(path)[:-4]][:2], flush=True)
    json.dump(res, open(OUT, "w"), indent=1)


if __name__ == "__main__":
    main()
