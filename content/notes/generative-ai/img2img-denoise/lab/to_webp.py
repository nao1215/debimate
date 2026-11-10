"""本文に載せる WebP を作る（Pillow）。PNG の元はリポジトリの外に置いたまま。

使い方: python3 to_webp.py <下絵のディレクトリ> <PNG のディレクトリ> <出力先（../images）>
"""
import json
import os
import sys

from PIL import Image

SWEEP = [30, 45, 60, 75, 86, 95, 100]


def save(src, dst, size, quality=78):
    im = Image.open(src).convert("RGB")
    im.thumbnail((size, size), Image.LANCZOS)
    im.save(dst, "WEBP", quality=quality, method=6)


def main():
    sk, png, out = sys.argv[1:4]
    os.makedirs(out, exist_ok=True)
    jobs = []
    for name in ("crisp", "blurred", "gray"):
        jobs.append((os.path.join(sk, f"sketch_{name}.png"), f"sketch_{name}.webp", 320))
        for d in SWEEP:
            jobs.append((os.path.join(png, f"{name}_{d:03d}.png"), f"{name}_{d:03d}.webp", 320))
    jobs.append((os.path.join(png, "control_txt2img.png"), "control_txt2img.webp", 320))
    jobs.append((os.path.join(png, "coins_base.png"), "coins_base.webp", 320))
    for tag, d in [("g", 30), ("g", 45), ("g", 50), ("g", 60), ("g", 75), ("c", 60)]:
        jobs.append((os.path.join(png, f"coins_{tag}_{d:03d}.png"), f"coins_{tag}_{d:03d}.webp", 320))
    # 宝箱の口の拡大（1536x1536 の (200,350)-(900,850)。1 枚目は 1.5 倍に拡大してから切る）
    for n in ["coins_base", "coins_g_030", "coins_g_045", "coins_g_050", "coins_g_060", "coins_c_060"]:
        src = os.path.join(png, n + ".png")
        if os.path.exists(src):
            im = Image.open(src).convert("RGB")
            if im.size[0] != 1536:
                im = im.resize((1536, 1536), Image.LANCZOS)
            im = im.crop((200, 350, 900, 850)).resize((420, 300), Image.LANCZOS)
            im.save(os.path.join(out, n + "_zoom.webp"), "WEBP", quality=80, method=6)
            print(n + "_zoom.webp", os.path.getsize(os.path.join(out, n + "_zoom.webp")))
    # 実験 3: 全身は生成したままの解像度（1 段目 768x1344、hires fix 1152x2016）。
    # 顔は boxes.json の face を hires fix の座標で切り抜き、1 段目は lanczos で 1.5 倍にしてから同じ範囲を切る
    # （どちらも hires fix と同じ倍率で、縮小しない）。メタデータは付けない
    boxes = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "boxes.json")))
    for seed in boxes:
        one = os.path.join(png, f"person_{seed}_1x.png")
        two = os.path.join(png, f"person_{seed}_hires.png")
        if not (os.path.exists(one) and os.path.exists(two)):
            continue
        a = Image.open(one).convert("RGB")
        b = Image.open(two).convert("RGB")
        for im, kind in ((a, "1x"), (b, "hires")):
            if seed != "20261193":  # 全身は 1 組だけ本文に載せる
                break
            clean = Image.new("RGB", im.size)
            clean.paste(im)
            clean.save(os.path.join(out, f"person_{seed}_{kind}.webp"), "WEBP", quality=88, method=6)
        k = b.size[0] / a.size[0]
        x0, y0, x1, y1 = [int(round(v * k)) for v in boxes[seed]["face"]]
        up = a.resize(b.size, Image.LANCZOS)
        for im, kind in ((up, "1x"), (b, "hires")):
            im.crop((x0, y0, x1, y1)).save(os.path.join(out, f"person_{seed}_{kind}_face.webp"), "WEBP",
                                           quality=90, method=6)
        print(f"person_{seed}: full {a.size} / {b.size}, face {x1 - x0}x{y1 - y0}")
    for src, dst, size in jobs:
        if os.path.exists(src):
            save(src, os.path.join(out, dst), size)
            print(dst, os.path.getsize(os.path.join(out, dst)))
        else:
            print("missing", src)


if __name__ == "__main__":
    main()
