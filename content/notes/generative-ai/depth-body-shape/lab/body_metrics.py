"""3D モデルの深度マップと、生成した絵の体の比率を同じ方法で数える。

関節は rtmlib の Body（performance: 人物の検出は YOLOX-x の Human-Art 学習版、姿勢は RTMPose-x）で取り、
体の輪郭（上端と下端、横幅）は背景との差で取る。値は全て比なので、絵の中の人物の大きさに依らない。

- 脚の比 = 股関節（COCO の hip）の中点から輪郭の下端まで ÷ 輪郭の上端から下端まで（脚が長いほど大きい）
- 肩より上の比 = 輪郭の上端から肩の中点まで ÷ 輪郭の上端から下端まで（頭と首が大きいほど大きい。髪も含む）
- 太ももの幅 = 股関節と膝の中間の高さで、左右の脚の区間が占める横幅の合計 ÷ 肩から足首までの縦の長さ（服が厚いほど大きい。頭頂や足先の描かれ方に左右されないよう、肩から足首で割る）

輪郭は、深度マップ（depth/ に置く）なら明るさ 13 以上、生成した絵なら背景の色（画面の縁 8 px の中央値）
との差が 32 以上の画素。

使い方: uv run --with rtmlib==0.0.13 --with onnxruntime==1.20.1 --with opencv-python-headless==4.10.0.84 \
          --with numpy==2.1.3 --with tqdm==4.67.1 python body_metrics.py <結果の JSON> <PNG>...
"""
import json
import os
import sys

import cv2
import numpy as np
from rtmlib import Body

L_SH, R_SH, L_HIP, R_HIP, L_KNEE, R_KNEE, L_ANK, R_ANK = 5, 6, 11, 12, 13, 14, 15, 16


def silhouette(img, is_depth):
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(int)
    if is_depth:
        return g >= 13
    edge = np.concatenate([img[:8].reshape(-1, 3), img[-8:].reshape(-1, 3), img[:, :8].reshape(-1, 3),
                           img[:, -8:].reshape(-1, 3)])
    bg = np.median(edge, axis=0)  # 背景の色は、画面の縁 8 px の中央値
    return np.abs(img.astype(int) - bg).max(axis=2) >= 32


def runs(row):
    """1 行の中で体の画素が続く区間 [始まり, 終わり] の列（左右の脚が別の区間になる）。"""
    out, start = [], None
    for x, v in enumerate(list(row) + [False]):
        if v and start is None:
            start = x
        elif not v and start is not None:
            out.append([start, x - 1])
            start = None
    return out


def measure(png, body):
    img = cv2.imread(png)
    is_depth = os.path.basename(os.path.dirname(os.path.abspath(png))) == "depth"  # 深度マップは depth/ に置く
    kpts, scores = body(img)
    if len(kpts) == 0:
        return {"error": "no person"}
    k = kpts[int(np.argmax(scores.mean(axis=1)))]
    y = lambda *ids: float(np.mean([k[i][1] for i in ids]))
    sh, hip, knee, ank = y(L_SH, R_SH), y(L_HIP, R_HIP), y(L_KNEE, R_KNEE), y(L_ANK, R_ANK)
    L = ank - sh
    row = int(round((hip + knee) / 2))
    mask = silhouette(img, is_depth)
    # 太ももの高さで体の画素が続く区間のうち、左右の脚の区間だけを数える（手先や籠手を除く）。
    # 脚の区間 = 股関節と膝の中間の x を含む区間。両脚が付いていれば 1 つの区間になる
    legs = []
    for h, kn in ((L_HIP, L_KNEE), (R_HIP, R_KNEE)):
        x = (k[h][0] + k[kn][0]) / 2
        hit = [r for r in runs(mask[row]) if r[0] - 4 <= x <= r[1] + 4]
        if hit and hit[0] not in legs:
            legs.append(hit[0])
    rows = np.where(mask.any(axis=1))[0]
    top, bottom = int(rows[0]), int(rows[-1])
    H = bottom - top
    return {"leg": round((bottom - hip) / H, 3), "above_shoulder": round((sh - top) / H, 3),
            "thigh_width": round(sum(b - a + 1 for a, b in legs) / L, 3), "people": int(len(kpts)),
            # 図に線を引くための縦の座標（px）と、太ももの高さで体が占める横の範囲
            "y": {"top": top, "shoulder": round(sh), "hip": round(hip), "row": row, "knee": round(knee),
                  "ankle": round(ank), "bottom": bottom}, "row_runs": legs}


def main():
    body = Body(mode="performance", backend="onnxruntime", device="cpu")
    res = {}
    for png in sys.argv[2:]:
        tag = os.path.basename(png)[:-4]
        res[tag] = measure(png, body)
        print(f"{tag:34s} {res[tag]}", flush=True)
    json.dump(res, open(sys.argv[1], "w"), indent=1)


if __name__ == "__main__":
    main()
