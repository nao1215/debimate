"""SaveLatent で保存した潜在（.latent、中身は safetensors）を読み、大きさと値の分布を数え、
ComfyUI のプレビューと同じ一次式（latent_rgb_factors）で 128 x 128 の色の近似を作る。

使い方: python3 latent_preview.py <final.latent> <保存先の PNG>
NumPy と Pillow を使う。
"""
import json
import struct
import sys

import numpy as np
from PIL import Image

SCALE = 0.13025                      # comfy/latent_formats.py の SDXL.scale_factor
RGB = np.array([[0.3651, 0.4232, 0.4341],     # SDXL.latent_rgb_factors（4 チャンネル → RGB）
                [-0.2533, -0.0042, 0.1068],
                [0.1076, 0.1111, -0.0362],
                [-0.3165, -0.2492, -0.2188]])
BIAS = np.array([0.1084, -0.0175, -0.0011])


def load(path):
    with open(path, "rb") as f:
        n = struct.unpack("<Q", f.read(8))[0]
        head = json.loads(f.read(n))
        meta = head["latent_tensor"]
        a, b = meta["data_offsets"]
        f.seek(8 + n + a)
        return np.frombuffer(f.read(b - a), dtype="<f4").reshape(meta["shape"])


def main():
    lat = load(sys.argv[1])[0]                        # [4, 128, 128]。SaveLatent は VAE の単位で保存する
    x = lat * SCALE                                   # process_latent_in と同じ。モデルが扱う単位
    print("shape", list(lat.shape), "values", lat.size, "vs pixels", 1024 * 1024 * 3,
          f"ratio {1024 * 1024 * 3 / lat.size:.0f}")
    for c in range(4):
        print(f"channel {c}: mean {x[c].mean():+.3f} std {x[c].std():.3f}")
    print(f"all: std {x.std():.3f}")
    rgb = np.einsum("chw,cr->hwr", x, RGB) + BIAS     # latent_preview.Latent2RGBPreviewer と同じ式
    img = (np.clip((rgb + 1) / 2, 0, 1) * 255).astype(np.uint8)
    Image.fromarray(img).save(sys.argv[2])


if __name__ == "__main__":
    main()
