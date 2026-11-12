"""生成した絵から姿勢を検出し、3D モデルの関節の位置とのずれを数える。

検出は rtmlib の Body（performance: 人物の検出は YOLOX-x の Human-Art 学習版、姿勢は RTMPose-x）。
3D モデルの 18 点（keypoints.json）のうち、肩・肘・手首・腰・膝・足首の 12 点を COCO の 17 点の同じ関節と比べる。

- ずれ = 2 点の距離 ÷ 3D モデルの背丈（首から両足首の中点までの距離）× 100（%）
- 関節ごとの値は結果の JSON の joints に残す
- 腕 = 肘と手首の 4 点、脚 = 膝と足首の 4 点、胴 = 肩と腰の 4 点の平均
- 左右の取り違えは問わない（左右を全部入れ替えた組と、そのままの組の小さい方を採る）
- 人物が見つからない絵は "no person"

使い方: uv run --with rtmlib==0.0.13 --with onnxruntime==1.20.1 --with opencv-python-headless==4.10.0.84 \
          --with numpy==2.1.3 --with tqdm==4.67.1 python pose_metrics.py <keypoints.json> <PNG のディレクトリ> <結果の JSON>
"""
import glob
import json
import os
import sys

import cv2
import numpy as np
from rtmlib import Body

# OpenPose の 18 点の名前 → COCO の 17 点の番号
COCO = {"LShoulder": 5, "RShoulder": 6, "LElbow": 7, "RElbow": 8, "LWrist": 9, "RWrist": 10,
        "LHip": 11, "RHip": 12, "LKnee": 13, "RKnee": 14, "LAnkle": 15, "RAnkle": 16}
GROUPS = {"arms": ["Elbow", "Wrist"], "legs": ["Knee", "Ankle"], "torso": ["Shoulder", "Hip"]}


def swap(name):
    return ("R" + name[1:]) if name[0] == "L" else ("L" + name[1:])


def errors(ref, det, height, swapped):
    out, joints = {}, {}
    for g, parts in GROUPS.items():
        ds = []
        for side in "LR":
            for part in parts:
                name = side + part
                p = np.array(ref[name])
                q = det[COCO[swap(name) if swapped else name]]
                ds.append(np.linalg.norm(p - q) / height * 100)
                joints[name] = round(float(ds[-1]), 1)
        out[g] = float(np.mean(ds))
    out["joints"] = joints  # 関節ごとのずれ（%）
    return out


def main():
    kp = json.load(open(sys.argv[1]))
    order = kp["order"]
    body = Body(mode="performance", backend="onnxruntime", device="cpu")
    res = {}
    for png in sorted(glob.glob(os.path.join(sys.argv[2], "*.png"))):
        tag = os.path.basename(png)[:-4]
        pose = tag.split("_")[0]
        if pose not in kp["poses"]:
            continue
        ref = {n: p for n, p in zip(order, kp["poses"][pose]) if p is not None}
        neck = np.array(ref["Neck"])
        height = float(np.linalg.norm(neck - (np.array(ref["LAnkle"]) + np.array(ref["RAnkle"])) / 2))
        img = cv2.imread(png)
        kpts, scores = body(img)
        if len(kpts) == 0:
            res[tag] = "no person"
            print(f"{tag:34s} no person")
            continue
        best = int(np.argmax(scores.mean(axis=1)))  # 点の確からしさの平均が最も高い 1 人
        det = kpts[best]
        a, b = errors(ref, det, height, False), errors(ref, det, height, True)
        e = a if sum(a[g] for g in GROUPS) <= sum(b[g] for g in GROUPS) else b
        e["people"] = int(len(kpts))
        res[tag] = e
        print(f"{tag:34s} arms {e['arms']:5.1f}  legs {e['legs']:5.1f}  torso {e['torso']:5.1f}  people {e['people']}")
    json.dump(res, open(sys.argv[3], "w"), indent=1)


if __name__ == "__main__":
    main()
