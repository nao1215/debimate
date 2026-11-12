"""実験の条件の節に置く図: 3 つの姿勢の深度マップを並べる（Pillow）。

使い方: python3 poses_figure.py   # ../images の depth_*.webp から ../images/controlnet_poses.webp
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

IMAGES = Path(__file__).resolve().parent.parent / "images"
FONT = ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", 22)
POSES = [("raise", "腕を上げる"), ("lunge", "突き"), ("lookback", "振り返る")]

cells = [Image.open(IMAGES / f"depth_{p}.webp").convert("RGB") for p, _ in POSES]
w, h = cells[0].size
left, top, gap = 10, 44, 10
c = Image.new("RGB", (left + 3 * (w + gap), top + h + gap), "white")
d = ImageDraw.Draw(c)
for j, (_, name) in enumerate(POSES):
    d.text((left + j * (w + gap) + w // 2, top // 2), name, font=FONT, fill="#1f1f1f", anchor="mm")
for j in range(3):
    c.paste(cells[j], (left + j * (w + gap), top))
c.save(IMAGES / "controlnet_poses.webp", "WEBP", quality=90, method=6)
print("wrote", IMAGES / "controlnet_poses.webp", c.size)
