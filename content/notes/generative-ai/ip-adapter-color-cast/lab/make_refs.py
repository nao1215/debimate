"""参照の絵から、背景だけを差し替えた正方形の参照を作る。

使い方: python make_refs.py <参照の絵（白背景の PNG）> <保存先>
  white.png   白（255, 255, 255）
  black.png   黒（0, 0, 0）
  green.png   緑（0, 177, 64）。合成用の緑の幕に近い色
  clear_black.png  透明（RGBA。透明の画素の RGB は 0, 0, 0）
  clear_white.png  透明（RGBA。透明の画素の RGB は 255, 255, 255）
  mask.png    人物の範囲（白が人物）
背景は、明るい画素（RGB がどれも 235 以上）のかたまりのうち、縁につながるものと 3000 画素以上のものとする。
IP-Adapter の画像エンコーダーは正方形の中央を切り抜くので、縦長の絵を同じ背景で左右に足して正方形にする。
"""
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

BACKS = {"white": (255, 255, 255), "black": (0, 0, 0), "green": (0, 177, 64)}


def person_mask(rgb):
    bright = (rgb >= 235).all(axis=2)
    labels, _ = ndimage.label(bright)
    edge = np.unique(np.concatenate([labels[0], labels[-1], labels[:, 0], labels[:, -1]]))
    sizes = np.bincount(labels.ravel())
    large = np.nonzero(sizes >= 3000)[0]  # 脚の間のように縁から切れた背景も拾う
    keep = np.union1d(edge, large)
    back = np.isin(labels, keep[keep > 0])
    return ~back


def main():
    src, out = sys.argv[1:3]
    os.makedirs(out, exist_ok=True)
    rgb = np.asarray(Image.open(src).convert("RGB"))
    h, w, _ = rgb.shape
    person = person_mask(rgb)
    pad = (h - w) // 2
    square_person = np.zeros((h, h), bool)
    square_person[:, pad:pad + w] = person
    square_rgb = np.zeros((h, h, 3), np.uint8)
    square_rgb[:, pad:pad + w] = rgb
    Image.fromarray((square_person * 255).astype(np.uint8)).save(os.path.join(out, "mask.png"))
    for name, color in BACKS.items():
        img = np.where(square_person[..., None], square_rgb, np.array(color, np.uint8))
        Image.fromarray(img).save(os.path.join(out, f"{name}.png"))
    for name, under in (("clear_black", 0), ("clear_white", 255)):
        img = np.where(square_person[..., None], square_rgb, np.uint8(under))
        alpha = (square_person * 255).astype(np.uint8)
        Image.fromarray(np.dstack([img, alpha]), "RGBA").save(os.path.join(out, f"{name}.png"))
    print("person share", round(float(square_person.mean()), 3))


if __name__ == "__main__":
    main()
