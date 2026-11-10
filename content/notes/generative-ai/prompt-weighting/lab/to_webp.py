"""本文に並べる画像を、生成した PNG から WebP（448 px）に変換する。

使い方:
    uv run --with pillow python to_webp.py <保存先> <images ディレクトリ> <実験名> <seed> <名前> [<名前> ...]

出力は <images>/<実験名>_<名前>_s<seed>.webp。
"""
import os
import sys

from PIL import Image


def main():
    src, dst, exp, seed = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
    for name in sys.argv[5:]:
        im = Image.open(os.path.join(src, exp, f"{name}_s{seed}.png")).convert("RGB")
        out = os.path.join(dst, f"{exp}_{name}_s{seed}.webp")
        im.resize((448, 448), Image.LANCZOS).save(out, quality=82, method=6)
        print(out, os.path.getsize(out))


if __name__ == "__main__":
    main()
