"""Arrange existing blog artwork without generating or redrawing illustrations."""
from pathlib import Path
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[2]
# Crops retain the owls while removing the broad empty areas of the banners.
SOURCES = [
    ('content/weeknotes/image/weekly-ogp-owl.webp', (380, 90, 1100, 510)),
    ('content/post/ja/2026-09-27-Xから離れたら、weeknotesを書く個人サイトが出来上がった/images/スマホでサイトを見るフクロウ.webp', (540, 130, 1460, 680)),
    ('content/post/ja/2026-09-21-Claude-for-Open-Sourceに申請して1ヶ月、まだ返事がない/images/claude-wait.webp', (170, 120, 1430, 880)),
    ('content/notes/image/notes-card-banner.webp', (570, 45, 1200, 400)),
]
canvas = Image.new('RGB', (1200, 720), '#eee7dc')
for i, (source, box) in enumerate(SOURCES):
    with Image.open(ROOT / source) as original:
        tile = ImageOps.fit(original.crop(box).convert('RGB'), (596, 356), method=Image.Resampling.LANCZOS)
    canvas.paste(tile, ((i % 2) * 604, (i // 2) * 364))
canvas.save(ROOT / 'content/weeknotes/2026/08-03/owl-collage.webp', quality=90)
