"""gozen-demo.webp の上の帯に左寄せで焼き込まれた札を、中央寄せに描き直す。"""
import sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter
src, dst, preview = sys.argv[1:4]
SEG = [(0, 'RPG：町の地図'), (14, 'RPG：戦闘とカットイン'), (34, '多層マップ'), (57, '人物の関係図'),
       (66, '人物の関係図：1 人に注目'), (77, 'ビデオ通話'), (91, 'スマホ画面：チャット')]
BAND = 29
font = ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Medium.ttc', 14, index=0)
im = Image.open(src)
frames, durs = [], []
for i in range(im.n_frames):
    im.seek(i)
    f = im.convert('RGB').copy()
    durs.append(im.info.get('duration', 125))
    band = f.crop((0, 0, f.width, BAND))
    # 古い札（明るい画素）を、膨らませた範囲ごと帯の暗い色で塗ってからぼかす
    m = band.convert('L').point(lambda p: 255 if p > 120 else 0).filter(ImageFilter.MaxFilter(5))
    dark = band.filter(ImageFilter.GaussianBlur(8))
    dark = Image.eval(dark, lambda v: int(v * 0.6))
    band = Image.composite(dark, band, m).filter(ImageFilter.GaussianBlur(2))
    f.paste(band, (0, 0))
    label = [t for s, t in SEG if s <= i][-1]
    d = ImageDraw.Draw(f)
    w = d.textlength(label, font=font)
    d.text(((f.width - w) / 2, BAND / 2), label, font=font, fill=(255, 255, 255), anchor='lm')
    frames.append(f)
frames[0].save(dst, save_all=True, append_images=frames[1:], duration=durs, loop=0, quality=80, method=6)
strip = Image.new('RGB', (420, 30 * 7))
for k, (s, _) in enumerate(SEG):
    strip.paste(frames[s + 3].crop((0, 0, 420, 30)), (0, 30 * k))
strip.resize((840, 420)).save(preview)
frames[0].save(dst.replace('.webp', '-poster.webp'), quality=70)
