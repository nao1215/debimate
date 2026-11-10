"""本文に載せる PNG を WebP にする。

使い方:
    python3 to_webp.py <PNG の保存先> <出力先> <項目> [...]

項目の書き方:
    <条件名>/<seed>                全体を元の解像度のまま（quality 88）
    <条件名>/<seed>@x,y,w,h        元の画像の (x, y) から幅 w・高さ h を等倍で切り抜く
    <条件名>/<seed>%<長い辺>        全体を長い辺の px まで縮める（形や色だけを比べるグリッド用）

出力のファイル名は attribute-binding_<条件名>_<seed>[_crop|_s<長い辺>].webp。Pillow を使う。
"""
import os
import sys

from PIL import Image


def main():
    src, dst = sys.argv[1], sys.argv[2]
    for item in sys.argv[3:]:
        box = size = None
        if "@" in item:
            item, b = item.split("@")
            box = tuple(int(v) for v in b.split(","))
        elif "%" in item:
            item, size = item.split("%")
            size = int(size)
        cond, seed = item.split("/")
        im = Image.open(os.path.join(src, cond, f"{seed}.png")).convert("RGB")
        name = f"attribute-binding_{cond}_{seed}"
        if box:
            x, y, w, h = box
            im = im.crop((x, y, x + w, y + h))
            name += "_crop"
        elif size:
            im.thumbnail((size, size), Image.LANCZOS)
            name += f"_s{size}"
        out = os.path.join(dst, name + ".webp")
        im.save(out, "WEBP", quality=88, method=6)
        print(f"{out} {im.size[0]}x{im.size[1]} {os.path.getsize(out):,} bytes")


if __name__ == "__main__":
    main()
