"""フレームを 1 枚ずつ 4 倍に拡大する。

python upscale.py <方式> <入力ディレクトリ> <出力ディレクトリ> [重みファイル]
  方式: bicubic / esrgan（重みは spandrel で読める Real-ESRGAN の .pth）
"""
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

method, src, dst = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
dst.mkdir(parents=True, exist_ok=True)

if method == "esrgan":
    import spandrel
    import torch

    torch.set_num_threads(32)
    model = spandrel.ModelLoader().load_from_file(sys.argv[4]).model.eval()

for p in sorted(src.glob("*.png")):
    t = time.time()
    img = Image.open(p).convert("RGB")
    if method == "bicubic":
        out = img.resize((img.width * 4, img.height * 4), Image.Resampling.BICUBIC)
    else:
        x = torch.from_numpy(np.asarray(img, dtype=np.float32) / 255).permute(2, 0, 1)[None]
        with torch.no_grad():
            y = model(x)[0].clamp(0, 1).permute(1, 2, 0).numpy()
        out = Image.fromarray((y * 255).round().astype(np.uint8))
    out.save(dst / p.name)
    print(p.name, f"{time.time() - t:.1f}s", flush=True)
