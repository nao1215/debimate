"""ComfyUI に入っている BiRefNet を、前処理の正規化だけを変えて動かし、マスクを保存する。

使い方: <ComfyUI の venv の python> cutout.py <ComfyUI のディレクトリ> <PNG の保存先>
  <名前>.png ごとに次の 2 枚を書く（どちらも 8 bit のグレースケール、255 が人物）
    <名前>_plain.png     ComfyUI の RemoveBackground と同じ前処理（birefnet.json の mean 0・std 1、つまり正規化しない）
    <名前>_imagenet.png  正規化だけを BiRefNet の作者の推論例に揃えたもの（ImageNet の平均と標準偏差で正規化する）
  どちらも 1024 x 1024 に縦横比を無視して縮め、出力を bicubic で元の大きさに戻して sigmoid を掛ける。
  これは comfy/bg_removal_model.py の encode_image と同じ流れで、違うのは mean と std だけ。
モデルの読み込みは ComfyUI の load（comfy/bg_removal_model.py）をそのまま使う。
"""
import glob
import os
import sys

import numpy as np
import torch
from PIL import Image

COMFY_DIR, OUT = sys.argv[1:3]
sys.path.insert(0, COMFY_DIR)
import comfy.bg_removal_model  # noqa: E402
import comfy.clip_model  # noqa: E402
import comfy.model_management  # noqa: E402

NORMS = {
    "plain": ([0.0, 0.0, 0.0], [1.0, 1.0, 1.0]),
    "imagenet": ([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
}


def mask(bg, image, mean, std):
    comfy.model_management.load_model_gpu(bg.patcher)
    h, w = image.shape[1], image.shape[2]
    x = comfy.clip_model.clip_preprocess(image.to(bg.load_device), size=bg.image_size, mean=mean, std=std, crop=False)
    with torch.no_grad():
        out = bg.model(pixel_values=x)
    out = torch.nn.functional.interpolate(out, size=(h, w), mode="bicubic", antialias=False)
    return out.sigmoid()[0, 0].float().cpu().numpy()


def main():
    bg = comfy.bg_removal_model.load(os.path.join(COMFY_DIR, "models", "background_removal", "birefnet.safetensors"))
    names = [p for p in sorted(glob.glob(os.path.join(OUT, "*.png")))
             if not p.endswith(("_node.png", "_plain.png", "_imagenet.png"))]
    for path in names:
        rgb = np.asarray(Image.open(path).convert("RGB"), np.float32) / 255
        image = torch.from_numpy(rgb)[None]
        for key, (mean, std) in NORMS.items():
            dst = path[:-4] + f"_{key}.png"
            if os.path.exists(dst):
                continue
            m = mask(bg, image, mean, std)
            Image.fromarray(np.clip(m * 255 + 0.5, 0, 255).astype(np.uint8)).save(dst)
        print(os.path.basename(path), flush=True)


if __name__ == "__main__":
    main()
