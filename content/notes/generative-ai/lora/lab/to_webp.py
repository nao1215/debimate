"""run_sweep.py が保存した 5 枚の PNG を、本文に並べる WebP に変換する。

あわせて、強さ 0 の画像との画素の差（RGB の絶対差の平均、0〜255）と、
各画像の明るさ（グレースケールにした画素の平均、0〜255）を数える。
Pillow と NumPy を使う。

使い方:
    python3 to_webp.py <PNG のディレクトリ> <images ディレクトリ> <名前（ancestral / euler）>
"""
import json
import os
import sys

import numpy as np
from PIL import Image

WEIGHTS = [0.0, 0.25, 0.5, 0.75, 1.0]
HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    src, dst, tag = sys.argv[1], sys.argv[2], sys.argv[3]
    imgs = [Image.open(os.path.join(src, f"weight_{w:.2f}.png")).convert("RGB")
            for w in WEIGHTS]

    # 本文で並べる 5 枚（1 枚 512 px の WebP）。強さはキャプションで示す
    for w, im in zip(WEIGHTS, imgs):
        name = f"lora_{tag}_{int(w * 100):03d}.webp"   # 例: lora_euler_025.webp
        im.resize((512, 512), Image.LANCZOS).save(os.path.join(dst, name), quality=85)

    base = np.asarray(imgs[0], dtype=np.int16)
    rows = []
    prev = base
    for w, im in zip(WEIGHTS, imgs):
        a = np.asarray(im, dtype=np.int16)
        mad0 = float(np.abs(a - base).mean())
        step = float(np.abs(a - prev).mean())
        luma = float(np.asarray(im.convert("L"), dtype=np.float64).mean())
        rows.append({"weight": w, "mad_vs_0": round(mad0, 2), "mad_vs_prev": round(step, 2),
                     "brightness": round(luma, 1)})
        print(f"weight={w:.2f}  diff_from_0={mad0:6.2f}  diff_from_prev={step:6.2f}"
              f"  brightness={luma:6.1f}")
        prev = a
    with open(os.path.join(HERE, f"pixel_change_{tag}.json"), "w") as f:
        json.dump(rows, f, indent=2)


if __name__ == "__main__":
    main()
