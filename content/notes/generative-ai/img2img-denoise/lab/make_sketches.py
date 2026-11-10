"""img2img の下絵を 3 種類作る（Pillow）。

  crisp   : 原色の図形をくっきり塗っただけの下絵
  blurred : crisp を Pillow の GaussianBlur(24) でぼかした下絵
  gray    : blurred を灰色にした下絵（明るさは同じで、色だけを抜く）

図形の位置は shapes.json にも書き出し、輪郭の一致を数える時の正解に使う。
使い方: python3 make_sketches.py <出力ディレクトリ>
"""
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFilter

SIZE = 1024
WALL = (222, 216, 202)
TABLE = (150, 100, 60)
SHAPES = [  # (名前, 種類, 外接矩形, 色)
    ("book", "rect", (150, 560, 470, 720), (30, 60, 220)),
    ("apple", "ellipse", (520, 470, 760, 710), (225, 30, 30)),
    ("lemon", "ellipse", (770, 590, 930, 710), (240, 210, 20)),
]
TABLE_TOP = 640


def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    img = Image.new("RGB", (SIZE, SIZE), WALL)
    d = ImageDraw.Draw(img)
    d.rectangle((0, TABLE_TOP, SIZE, SIZE), fill=TABLE)
    for _, kind, box, color in SHAPES:
        (d.rectangle if kind == "rect" else d.ellipse)(box, fill=color)
    img.save(os.path.join(out, "sketch_crisp.png"))
    blurred = img.filter(ImageFilter.GaussianBlur(24))
    blurred.save(os.path.join(out, "sketch_blurred.png"))
    blurred.convert("L").convert("RGB").save(os.path.join(out, "sketch_gray.png"))
    with open(os.path.join(out, "shapes.json"), "w") as f:
        json.dump({"size": SIZE, "table_top": TABLE_TOP,
                   "shapes": [{"name": n, "kind": k, "box": b, "color": c} for n, k, b, c in SHAPES]},
                  f, indent=1)


if __name__ == "__main__":
    main()
