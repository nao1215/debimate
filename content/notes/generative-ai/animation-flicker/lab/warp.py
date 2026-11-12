"""仕上げた 1 コマ目を、人形の動きどおりに歪めて 2〜4 コマ目を作る（描き直さない）。

人形の表面の各点には、変形前の位置（Generated）か展開図の座標（UV）を色として描いてある（render_frames.py）。
コマ i の画素が見ている表面の点を、1 コマ目の画素から探せば、「コマ i のこの画素は 1 コマ目のどこから持ってくるか」
（流れ、flow）が決まる。人形の外の画素（髪・背景）と、探して外れた画素は、いちばん近い体の画素の流れを使う。
最後に流れをガウスでならし（sigma、画素）、1 コマ目をその流れで引き伸ばす。

使い方: python3 warp.py <1 コマ目の PNG> <render_frames.py の出力先> <gen か uv> <sigma> <保存先の接頭辞>
出力: <接頭辞>_f0.png 〜 _f3.png（f0 は 1 コマ目そのまま）
"""
import sys

import cv2
import numpy as np
from scipy import ndimage
from scipy.spatial import cKDTree

FRAMES = ["f0", "f1", "f2", "f3"]
POS_W = 0.05      # 画面の位置にも少し重みを付ける。左右の脚のように似た座標の所を取り違えないため
MATCH = 0.01      # 座標の差がこれより大きい対応は外れとみなす
MAX_SHIFT = 0.12  # 画面の長い辺の 12% より大きく動く対応も外れとみなす（腕の先でも 1 コマ目から 115 画素ほど）


def load_coords(passes, kind, frame):
    a = cv2.imread(f"{passes}/{kind}_{frame}.png", cv2.IMREAD_UNCHANGED).astype(np.float32) / 65535.0
    mask = a[..., 3] > 0.98  # 境目で 2 つの面が混ざった画素は使わない
    return np.stack([a[..., 2], a[..., 1], a[..., 0]], -1), mask  # OpenCV は BGRA の順


def doll_flow(passes, kind, frame):
    """コマ frame の各画素が、1 コマ目のどの画素から来たか（dx, dy）。対応が取れた画素の印も返す。"""
    c0, m0 = load_coords(passes, kind, "f0")
    h, w = m0.shape
    ys0, xs0 = np.nonzero(m0)

    def feats(c, ys, xs):
        return np.column_stack([c[ys, xs, 0], c[ys, xs, 1], c[ys, xs, 2], xs / w * POS_W, ys / h * POS_W])

    ci, mi = load_coords(passes, kind, frame)
    ys, xs = np.nonzero(mi)
    dist, idx = cKDTree(feats(c0, ys0, xs0)).query(feats(ci, ys, xs), k=1)
    dx, dy = xs0[idx] - xs, ys0[idx] - ys
    ok = (dist < MATCH) & (np.hypot(dx, dy) < MAX_SHIFT * max(h, w))
    flow = np.zeros((h, w, 2), np.float32)
    good = np.zeros((h, w), bool)
    flow[ys[ok], xs[ok]] = np.column_stack([dx[ok], dy[ok]])
    good[ys[ok], xs[ok]] = True
    return flow, good, mi


def warp(pic, flow, good, sigma):
    _, (iy, ix) = ndimage.distance_transform_edt(~good, return_indices=True)
    flow = flow[iy, ix]  # 体の外と外れた画素は、いちばん近い体の画素の流れ
    fx = ndimage.gaussian_filter(flow[..., 0], sigma)
    fy = ndimage.gaussian_filter(flow[..., 1], sigma)
    H, W = pic.shape[:2]
    gx, gy = np.meshgrid(np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32))
    return cv2.remap(pic, gx + fx, gy + fy, interpolation=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)


if __name__ == "__main__":
    src, passes, kind, sigma, prefix = sys.argv[1:6]
    pic = cv2.imread(src, cv2.IMREAD_COLOR)
    cv2.imwrite(f"{prefix}_f0.png", pic)
    for f in FRAMES[1:]:
        flow, good, _ = doll_flow(passes, kind, f)
        cv2.imwrite(f"{prefix}_{f}.png", warp(pic, flow, good, float(sigma)))
        print(prefix, f, "kept", round(float(good.sum()) / max(1, int(_.sum())), 3), flush=True)
