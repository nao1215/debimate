"""本文に載せる WebP を作る（Pillow）。PNG の元はリポジトリの外に置いたまま。

使い方: python3 to_webp.py <条件の画像のディレクトリ> <PNG のディレクトリ> <出力先（../images）>
- 条件の画像と生成した絵は、縦横比を保って幅 300 px に縮める（832 × 1216 → 300 × 438）
- 本文で使わない絵（*_mannequin など）の WebP も書き出すので、本文から参照しないものは消した
- 冒頭の図（controlnet_cover.webp）は、突きのポーズの「骨格 → 絵」「深度マップ → 絵」を 1 枚に並べたもの
"""
import glob
import os
import sys

from PIL import Image

W = 300


def small(path):
    im = Image.open(path).convert("RGB")
    return im.resize((W, round(im.height * W / im.width)), Image.LANCZOS)


def main():
    cond, png, out = sys.argv[1:4]
    os.makedirs(out, exist_ok=True)
    for path in sorted(glob.glob(os.path.join(cond, "*.png"))):
        name = os.path.basename(path)[:-4]
        if name.startswith(("depth_", "openpose_", "canny_")):
            small(path).save(os.path.join(out, name + ".webp"), "WEBP", quality=82, method=6)
    for path in sorted(glob.glob(os.path.join(png, "*.png"))):
        name = os.path.basename(path)[:-4]
        small(path).save(os.path.join(out, name + ".webp"), "WEBP", quality=80, method=6)
    # 冒頭の図: 4 枚（各 240 × 351）を横に並べた 960 × 351
    seed = 20261111
    tiles = [os.path.join(cond, "openpose_lunge.png"), os.path.join(png, f"lunge_openpose_{seed}.png"),
             os.path.join(cond, "depth_lunge.png"), os.path.join(png, f"lunge_depth_{seed}.png")]
    cover = Image.new("RGB", (960, 351), (255, 255, 255))
    for i, path in enumerate(tiles):
        im = Image.open(path).convert("RGB").resize((240, 351), Image.LANCZOS)
        cover.paste(im, (i * 240, 0))
    cover.save(os.path.join(out, "controlnet_cover.webp"), "WEBP", quality=85, method=6)
    print("wrote", out)


if __name__ == "__main__":
    main()
