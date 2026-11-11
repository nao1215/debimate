"""Sintel の予告編から正解の 48 フレームと、縮小・劣化させた入力を作る。

python3 prepare.py <sintel_trailer-1080p.mp4> <作業ディレクトリ>
  gt/       正解。34.0 秒から 48 フレーム、1280x720 を切り出して 1024x576 に縮小
  clean/    正解を 256x144 に縮小しただけの入力
  noisy/    clean にフレームごとに独立なガウスノイズ（σ=4）を足し、H.264（CRF 26）で圧縮した入力
  denoised/ noisy に時間方向のノイズ除去（ffmpeg の hqdn3d）を掛けた入力
"""
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

SRC, WORK = Path(sys.argv[1]), Path(sys.argv[2])
START, FRAMES, SIGMA, SEED = "34.0", 48, 4.0, 20261111


def ff(*args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True)


for d in ["gt", "clean", "noisy_raw", "noisy", "denoised"]:
    (WORK / d).mkdir(parents=True, exist_ok=True)

ff("-ss", START, "-i", str(SRC), "-frames:v", str(FRAMES),
   "-vf", "crop=1280:720:320:180,scale=1024:576:flags=area", str(WORK / "gt/%03d.png"))
ff("-i", str(WORK / "gt/%03d.png"), "-vf", "scale=256:144:flags=area", str(WORK / "clean/%03d.png"))

rng = np.random.default_rng(SEED)
for p in sorted((WORK / "clean").glob("*.png")):
    a = np.asarray(Image.open(p).convert("RGB"), dtype=np.float64)
    a = a + rng.normal(0, SIGMA, a.shape)
    Image.fromarray(np.clip(a.round(), 0, 255).astype(np.uint8)).save(WORK / "noisy_raw" / p.name)

ff("-framerate", "24", "-i", str(WORK / "noisy_raw/%03d.png"), "-c:v", "libx264", "-crf", "26",
   "-pix_fmt", "yuv420p", str(WORK / "noisy.mp4"))
ff("-i", str(WORK / "noisy.mp4"), str(WORK / "noisy/%03d.png"))
ff("-i", str(WORK / "noisy.mp4"), "-vf", "hqdn3d=luma_spatial=1:chroma_spatial=1:luma_tmp=8:chroma_tmp=8",
   str(WORK / "denoised/%03d.png"))
