"""Prepare quoted screenshots without changing their UI pixels.

Requires Pillow. Run with a directory containing the original downloads:
  python3 screenshots.py /tmp/wallet-research

Sources:
- sparrow-send.png: https://sparrowwallet.com/assets/images/control-your-sends-2x.png
- bluewallet-batch.png: https://bluewallet.io/uploads/features/batch.png
- rabby-confirm.webp: https://www.keystone3.com/en/docs/gen2/rabby-wallet/
  (the original screenshot downloaded from this page)

Sparrow and BlueWallet already have transparent surroundings. Preserve them.
Rabby's black window border occupies x=732..1570 in the 2304x1552 original.
Only the exterior side margins are made transparent, then mostly trimmed.
The window, including its white fields, text and original annotations, is intact.
"""
from pathlib import Path
import sys
from PIL import Image, ImageChops

source = Path(sys.argv[1])
output = Path(__file__).parent / 'images'
for filename, target in [('sparrow-send.png', 'sparrow-send.webp'),
                         ('bluewallet-batch.png', 'bluewallet-send.webp'),
                         ('rabby-confirm.webp', 'rabby-confirm.webp')]:
    original = Image.open(source / filename).convert('RGBA')
    prepared = original.copy()
    if filename == 'rabby-confirm.webp':
        assert original.size == (2304, 1552), 'Recheck screenshot border coordinates'
        alpha = prepared.getchannel('A')
        alpha.paste(0, (0, 0, 731, prepared.height))
        alpha.paste(0, (1572, 0, prepared.width, prepared.height))
        prepared.putalpha(alpha)
        prepared = prepared.crop((715, 0, 1588, 1552))
        assert ImageChops.difference(original.crop((731, 0, 1572, 1552)),
                                    prepared.crop((16, 0, 857, 1552))).getbbox() is None
    prepared.save(output / target, 'WEBP', lossless=True, exact=True, method=6)
    decoded = Image.open(output / target).convert('RGBA')
    assert decoded.tobytes() == prepared.tobytes(), 'Pixel preservation failed'
    print(f'{target}: {decoded.width}x{decoded.height}, {(output / target).stat().st_size} bytes; pixels verified')

# Optional quoted game screenshot. Decode the AVIF with ImageMagick first:
# magick gods-decks.avif gods-decks.png
# Original: https://cdn.prod.website-files.com/693a2dd63f96bcccace0cb94/693a2dd63f96bcccace0cf7d_getting_draw_decks.avif
# Context: https://portal.godsunchained.com/getting-started
if (source / 'gods-decks.png').exists():
    Image.open(source / 'gods-decks.png').save(
        output / 'gods-unchained-decks.webp', 'WEBP', lossless=True, method=6)

# Official custody comparison screenshots; preserve the originals' pixels/alpha.
# https://sparrowwallet.com/assets/images/docs/first-wallet-1.png
# https://raw.githubusercontent.com/lnbits/lnbits/main/docs/assets/wallet.jpg
for original, target in [('sparrow-keystore.png', 'sparrow-keystore.webp'),
                         ('lnbits-wallet.jpg', 'lnbits-wallet.webp')]:
    if (source / original).exists():
        Image.open(source / original).save(output / target, 'WEBP', lossless=True, exact=True, method=6)

# Safe official help: https://help.safe.global/articles/9629761095
# Download the page's change-threshold.gif as safe-threshold.gif.
if (source / 'safe-threshold.gif').exists():
    animation = Image.open(source / 'safe-threshold.gif')
    animation.seek(300)
    animation.convert('RGB').crop((250, 65, 860, 470)).save(
        output / 'safe-threshold.webp', 'WEBP', lossless=True, method=6)

# Source: MetaMask official spending-cap guide, image CID QmcjpsmNnh64pyg9Syz6jqNnUbfj56xcXkNN9jTQNqu1xL
# Make only border-connected white background transparent; preserve UI pixels.
if (source / 'metamask-cap.png').exists():
    from collections import deque
    im=Image.open(source / 'metamask-cap.png').convert('RGBA');w,h=im.size;px=im.load();q=deque()
    for x in range(w):q.extend([(x,0),(x,h-1)])
    for y in range(h):q.extend([(0,y),(w-1,y)])
    seen=set()
    while q:
     x,y=q.popleft()
     if not(0<=x<w and 0<=y<h) or (x,y) in seen:continue
     seen.add((x,y));r,g,b,a=px[x,y]
     if a and min(r,g,b)>=250:
      px[x,y]=(r,g,b,0);q.extend([(x-1,y),(x+1,y),(x,y-1),(x,y+1)])
    im.save(output / 'metamask-spending-cap.webp','WEBP',lossless=True,exact=True,method=6)
