"""本文に載せる WebP と、冒頭の並べた図を作る（Pillow）。PNG の元はリポジトリの外に置いたまま。

使い方: python3 to_webp.py <PNG のディレクトリ> <出力先（../images）>
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

FONT = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"   # index 0 が日本語（JP）
INK, SUB = (31, 31, 31), (102, 102, 102)
KS = [0, 2, 4, 7, 10, 14, 20, 28]


def save(src, dst, size=320, quality=80):
    im = Image.open(src).convert("RGB")
    im.thumbnail((size, size), Image.LANCZOS)
    im.save(dst, "WEBP", quality=quality, method=6)


def cover(png, dst):
    """上段に途中の潜在 x_k、下段にそのステップでモデルが予測した x0 を並べる。白い背景。"""
    cell, gap, left, top = 112, 6, 150, 34
    w = left + len(KS) * (cell + gap) - gap + 12
    h = top + 2 * cell + gap + 12
    sheet = Image.new("RGB", (w, h), "white")
    d = ImageDraw.Draw(sheet)
    f = ImageFont.truetype(FONT, 17, index=0)
    fs = ImageFont.truetype(FONT, 15, index=0)
    for i, k in enumerate(KS):
        x = left + i * (cell + gap)
        d.text((x + cell / 2, 8), f"{k}", font=f, fill=SUB, anchor="mt")
        sheet.paste(Image.open(os.path.join(png, f"x_{k:02d}.png")).convert("RGB").resize((cell, cell), Image.LANCZOS),
                    (x, top))
        p = os.path.join(png, f"x0_{k:02d}.png")
        if os.path.exists(p):
            sheet.paste(Image.open(p).convert("RGB").resize((cell, cell), Image.LANCZOS), (x, top + cell + gap))
        else:
            d.rectangle([x, top + cell + gap, x + cell - 1, top + 2 * cell + gap - 1], fill=(242, 242, 242))
            d.text((x + cell / 2, top + cell + gap + cell / 2), "予測なし", font=fs, fill=SUB, anchor="mm")
    d.text((10, 8), "ステップ", font=f, fill=SUB)
    d.text((10, top + cell / 2 - 12), "途中の潜在", font=f, fill=INK)
    d.text((10, top + cell / 2 + 10), "x_k", font=fs, fill=SUB)
    d.text((10, top + cell + gap + cell / 2 - 12), "予測した画像", font=f, fill=INK)
    d.text((10, top + cell + gap + cell / 2 + 10), "x0", font=fs, fill=SUB)
    sheet.save(dst, "WEBP", quality=82, method=6)


def main():
    png, out = sys.argv[1:3]
    os.makedirs(out, exist_ok=True)
    cover(png, os.path.join(out, "diffusion_trajectory.webp"))
    names = [f"fwd_{j:02d}" for j in (27, 24, 20, 14, 10, 4, 1)] + ["x_28"]
    names += [f"steps_{n:02d}" for n in (8, 16, 28, 50)]
    names += ["sampler_euler_ancestral", "sampler_dpmpp_2m_karras", "cfg_1.0", "cfg_9.0"]
    for n in names:
        p = os.path.join(png, n + ".png")
        if os.path.exists(p):
            save(p, os.path.join(out, n.replace(".", "_") + ".webp"))
    # 潜在の色の近似（128 x 128）は、画素が見えるように最近傍で 2 倍にする
    lat = Image.open(os.path.join(png, "latent_rgb.png")).resize((256, 256), Image.NEAREST)
    lat.save(os.path.join(out, "latent_rgb.webp"), "WEBP", quality=90, method=6)


if __name__ == "__main__":
    main()
