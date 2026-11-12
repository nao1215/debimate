"""3D モデルの深度マップから、輪郭（Canny エッジ）の画像を作る（OpenCV）。

3D モデルには服の皺や顔の凹凸が無いので、輪郭は体の外形と、手前の腕・脚の縁だけになる。
使い方: python3 make_canny.py <render_poses.py の出力先>
"""
import glob
import os
import sys

import cv2

for path in sorted(glob.glob(os.path.join(sys.argv[1], "depth_*.png"))):
    depth = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    edges = cv2.Canny(depth, 20, 60)
    out = path.replace("depth_", "canny_")
    cv2.imwrite(out, edges)
    print(out)
