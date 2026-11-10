"""keypoints.json の 18 点から、OpenPose の骨格の画像（黒地に色付きの棒と点）を描く（Pillow）。

色と棒の組は comfyui_controlnet_aux の draw_bodypose と同じ。棒の太さは、xinsir/controlnet-openpose-sdxl-1.0 の
model card が勧める描き方（長辺 1000〜2000 px なら棒の半幅 4 × 3、点の半径 4 × 3）に合わせる。
--thin を付けると、comfyui_controlnet_aux の既定（棒の半幅 4 = 太さ約 8、点の半径 4）で描く。

使い方: python3 draw_openpose.py <keypoints.json> <出力先> [--thin]
"""
import json
import math
import sys

from PIL import Image, ImageDraw

LIMBS = [[2, 3], [2, 6], [3, 4], [4, 5], [6, 7], [7, 8], [2, 9], [9, 10], [10, 11], [2, 12], [12, 13],
         [13, 14], [2, 1], [1, 15], [15, 17], [1, 16], [16, 18]]
COLORS = [[255, 0, 0], [255, 85, 0], [255, 170, 0], [255, 255, 0], [170, 255, 0], [85, 255, 0], [0, 255, 0],
          [0, 255, 85], [0, 255, 170], [0, 255, 255], [0, 170, 255], [0, 85, 255], [0, 0, 255], [85, 0, 255],
          [170, 0, 255], [255, 0, 255], [255, 0, 170], [255, 0, 85]]


def ratio_for(w, h):
    side = max(w, h)
    return 1.0 if side < 500 else 2.0 if side < 1000 else 3.0 if side < 2000 else 4.0


def draw(points, w, h, thin=False):
    r = 1.0 if thin else ratio_for(w, h)
    im = Image.new("RGB", (w, h), (0, 0, 0))
    d = ImageDraw.Draw(im)
    for (a, b), color in zip(LIMBS, COLORS):
        p, q = points[a - 1], points[b - 1]
        if p is None or q is None:
            continue
        # 2 点を結ぶ細長い楕円（cv2.ellipse2Poly と同じく 1 度ごとの多角形）
        cx, cy = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
        half = math.dist(p, q) / 2
        ang = math.atan2(q[1] - p[1], q[0] - p[0])
        ry = 4 * r
        poly = []
        for deg in range(0, 360):
            t = math.radians(deg)
            x, y = half * math.cos(t), ry * math.sin(t)
            poly.append((cx + x * math.cos(ang) - y * math.sin(ang), cy + x * math.sin(ang) + y * math.cos(ang)))
        d.polygon(poly, fill=tuple(int(c * 0.6) for c in color))
    for p, color in zip(points, COLORS):
        if p is None:
            continue
        rad = 4 * r
        d.ellipse([p[0] - rad, p[1] - rad, p[0] + rad, p[1] + rad], fill=tuple(color))
    return im


def main():
    kp = json.load(open(sys.argv[1]))
    out = sys.argv[2]
    thin = "--thin" in sys.argv
    for name, pts in kp["poses"].items():
        im = draw(pts, kp["width"], kp["height"], thin)
        path = f"{out}/openpose_{name}{'_thin' if thin else ''}.png"
        im.save(path)
        print(path)


if __name__ == "__main__":
    main()
