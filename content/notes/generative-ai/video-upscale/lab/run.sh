#!/bin/sh
# 実験の再現手順。
#   WORK: 作業ディレクトリ、SRC: Sintel の予告編（sintel_trailer-1080p.mp4）、WEIGHTS: Real-ESRGAN の重みの置き場所
#   PY: torch と spandrel の入った Python（CPU で動かした）。拡散モデルの段は ComfyUI（127.0.0.1:8188）を使う。
set -eu
cd "$(dirname "$0")"
"$PY" prepare.py "$SRC" "$WORK"
for s in clean noisy denoised; do
  "$PY" upscale.py bicubic "$WORK/$s" "$WORK/out/bicubic_$s"
  "$PY" upscale.py esrgan "$WORK/$s" "$WORK/out/animevideo_$s" "$WEIGHTS/realesr-animevideov3.pth"
  "$PY" upscale.py esrgan "$WORK/$s" "$WORK/out/gan_$s" "$WEIGHTS/RealESRGAN_x4plus_anime_6B.pth"
done
for s in clean noisy; do
  python3 comfy_upscale.py diffusion "$WORK/out/gan_$s" "$WORK/out/diffusion_$s"
done
python3 metrics.py "$WORK" metrics.json > output_metrics.txt
