"""生成した PNG を、本文に載せる WebP にする（Pillow）。

  python3 to_webp.py <PNG のディレクトリ> ../images

- 全体の絵は 832x1216 を半分の 416x608 に縮める
- 顔の切り抜き（metrics.py が作る *_face.png）は 256x256 に縮める
- 骨格の画像（*_skeleton.png）は全体の絵と同じ大きさにする
- 表紙用に、同じプロンプトで seed だけを変えた 4 枚を横に並べた 1 枚（cover_seeds.webp）を作る
生成した PNG はリポジトリの外に置き、リポジトリには WebP だけを入れた。
"""
import os
import sys

from PIL import Image

src, dst = sys.argv[1], sys.argv[2]
os.makedirs(dst, exist_ok=True)
for f in sorted(os.listdir(src)):
    if not f.endswith(".png"):
        continue
    img = Image.open(os.path.join(src, f)).convert("RGB")
    if f.endswith("_face.png"):
        # 画像の端で切れて正方形でない切り抜きは、縦横比を保って白地の正方形に載せる
        side = max(img.size)
        square = Image.new("RGB", (side, side), "white")
        square.paste(img, ((side - img.width) // 2, (side - img.height) // 2))
        img = square.resize((256, 256), Image.LANCZOS)
    else:
        img = img.resize((416, 608), Image.LANCZOS)
    img.save(os.path.join(dst, f[:-4] + ".webp"), "WEBP", quality=85, method=6)

# 表紙: 同じプロンプト・seed だけを変えた 4 枚を白い隙間を挟んで並べる（4 枚目の seed 20261114 は基準の絵 base.png）
tiles = [Image.open(os.path.join(src, f"{n}.png")).convert("RGB").resize((416, 608), Image.LANCZOS)
         for n in ("seed_0", "seed_1", "seed_2", "base")]
gap = 12
cover = Image.new("RGB", (416 * 4 + gap * 3, 608), "white")
for i, t in enumerate(tiles):
    cover.paste(t, (i * (416 + gap), 0))
cover.save(os.path.join(dst, "cover_seeds.webp"), "WEBP", quality=85, method=6)
