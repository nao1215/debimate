"""Background Removal のノートの図を作る。

使い方: python figures.py <作業先>   （<作業先>/gen に run.py・cutout.py の出力、<作業先>/metrics.json に measure.py の出力）
- bgr_cover.webp:  白い背景で描いた髪、切り抜いて暗い背景へ置いた絵、背景色を差し引いてから置いた絵
- bgr_mask.webp:   描いた絵と BiRefNet のマスク（髪の先の拡大）
- bgr_edges.webp:  白・灰・緑の背景で描いた茶髪を切り抜いて、暗い背景へ置いた髪の先
- bgr_fringe.webp: 縁の色のずれ（ΔE）。背景色を差し引く前と後、背景と髪の組ごと
- bgr_color.webp:  背景色に近い不透明な画素（透明な所につながる塊と、つながらない塊）
- bgr_clean.webp:  白い背景で描いた銀髪で、色で取り残しを消す前と後
- bgr_rgba.webp:   ComfyUI で作った透過 PNG を、透明度どおりに表示した絵と、透明度を捨てて RGB だけを表示した絵
- bgr_norm.webp:   ComfyUI のノード（正規化なし）と、正規化だけを作者の推論例に揃えたマスクの違い
暗い背景は RGB (24, 28, 40)。切り抜く場所は、半透明の画素が最も多い 300 x 300 の窓を機械で選ぶ（lab の measure.py と同じ定義）。
"""
import json
import os
import sys

import matplotlib
import numpy as np
from scipy import ndimage
from PIL import Image, ImageDraw, ImageFont

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "lab"))
import measure  # noqa: E402

WORK = sys.argv[1]
GEN = os.path.join(WORK, "gen")
IMG = os.path.join(HERE, "images")
DARK = np.array([24, 28, 40], np.float32) / 255
FONT = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
plt.rcParams["font.family"] = "Noto Sans CJK JP"


def load(name, var="node"):
    rgb = np.asarray(Image.open(os.path.join(GEN, name + ".png")).convert("RGB"), np.float32) / 255
    a = np.asarray(Image.open(os.path.join(GEN, f"{name}_{var}.png")).convert("L"), np.float32) / 255
    return rgb, a


def on_dark(rgb, a):
    return a[..., None] * rgb + (1 - a[..., None]) * DARK


def unmix(rgb, a, back):
    fg = np.clip((rgb - (1 - a[..., None]) * back) / np.maximum(a[..., None], 0.05), 0, 1)
    return on_dark(fg, a)


def window(a, size=300):
    """上半分で、半透明の画素が最も多い size 四方の窓の左上（x, y）。"""
    semi = ((a > 0.02) & (a < 0.98)).astype(np.float32)
    h, w = a.shape
    ii = semi.cumsum(0).cumsum(1)
    best, at = -1, (0, 0)
    for y in range(0, h // 2 - size, 10):
        for x in range(0, w - size, 10):
            s = ii[y + size - 1, x + size - 1] - (ii[y - 1, x + size - 1] if y else 0) \
                - (ii[y + size - 1, x - 1] if x else 0) + (ii[y - 1, x - 1] if x and y else 0)
            if s > best:
                best, at = s, (x, y)
    return at


def crop(img, at, size=300):
    x, y = at
    return img[y:y + size, x:x + size]


def to_pil(x):
    return Image.fromarray((np.clip(x, 0, 1) * 255 + 0.5).astype(np.uint8))


def panels(rows, labels, out, scale=1.6, title_rows=None):
    """rows: [[画像の配列, ...], ...]。labels: 列の見出し。title_rows: 行の見出し（左に置く）。"""
    font = ImageFont.truetype(FONT, 30)
    small = ImageFont.truetype(FONT, 26)
    tiles = [[to_pil(t) for t in r] for r in rows]
    tw = max(t.width for r in tiles for t in r)
    th = max(t.height for r in tiles for t in r)
    tw, th = int(tw * scale), int(th * scale)
    left = 150 if title_rows else 0
    gap, head = 16, 56
    W = left + len(labels) * tw + (len(labels) - 1) * gap
    H = head + len(rows) * th + (len(rows) - 1) * gap
    c = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(c)
    for j, lab in enumerate(labels):
        x = left + j * (tw + gap) + tw // 2
        d.text((x, head // 2), lab, fill=(30, 30, 30), font=font, anchor="mm")
    for i, r in enumerate(tiles):
        y = head + i * (th + gap)
        if title_rows:
            d.text((left // 2, y + th // 2), title_rows[i], fill=(30, 30, 30), font=small, anchor="mm")
        for j, t in enumerate(r):
            c.paste(t.resize((tw, th), Image.NEAREST if scale >= 1.5 else Image.LANCZOS), (left + j * (tw + gap), y))
    c.save(os.path.join(IMG, out), "WEBP", quality=90, method=6)
    print("wrote", out, c.size)


def cover():
    rgb, a = load("white_brown_20261115")
    at = window(a)
    back = measure.background(rgb)
    panels([[crop(rgb, at), crop(on_dark(rgb, a), at), crop(unmix(rgb, a, back), at)]],
           ["白い背景で描いた", "切り抜いて暗い背景へ", "背景色を差し引いてから"], "bgr_cover.webp")


def mask():
    rgb, a = load("white_brown_20261115")
    at = window(a, 160)
    m = np.repeat(a[..., None], 3, -1)
    panels([[crop(rgb, at, 160), crop(m, at, 160)]], ["描いた絵", "マスク"],
           "bgr_mask.webp", scale=2.5)


def edges():
    row = []
    for back in ("white", "grey", "green"):
        rgb, a = load(f"{back}_brown_20261116")
        at = window(a, 220)
        row.append(crop(on_dark(rgb, a), at, 220))
    panels([row], ["白い背景で描いた", "灰色の背景で描いた", "緑の背景で描いた"], "bgr_edges.webp", scale=2.0)


def fringe(metrics):
    groups = [(b, h) for h in ("brown", "silver") for b in ("white", "grey", "green")]
    names = {"white": "白", "grey": "灰", "green": "緑", "brown": "茶髪", "silver": "銀髪"}
    fig, ax = plt.subplots(figsize=(8.4, 3.8))
    for i, (b, h) in enumerate(groups):
        rs = [metrics[f"{b}_{h}_{s}"]["node"] for s in (20261115, 20261116, 20261117)]
        for k, r in enumerate(rs):
            ax.plot([i - 0.12, i + 0.12], [r["fringe"], r["fringe_unmix"]], color="#9aa0a6", lw=1, zorder=1)
            ax.scatter(i - 0.12, r["fringe"], color="#d0021b", s=30, zorder=2, label="そのまま" if i == k == 0 else None)
            ax.scatter(i + 0.12, r["fringe_unmix"], color="#1f5fbf", s=30, zorder=2,
                       label="背景色を差し引いた" if i == k == 0 else None)
    ax.set_xticks(range(len(groups)), [f"{names[b]}・{names[h]}" for b, h in groups])
    ax.set_xlabel("描いた時の背景・髪の色")
    ax.set_ylabel("縁の色のずれ ΔE")
    ax.set_ylim(0, 20)
    ax.axvline(2.5, color="#cccccc", lw=1)
    ax.axhline(2.3, color="#555555", lw=1, ls="--")
    ax.text(5.45, 2.8, "人に分かる差の目安 2.3", ha="right", fontsize=9, color="#555555")
    ax.grid(axis="y", color="#eeeeee")
    ax.legend(loc="lower left", frameon=False)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    png = os.path.join(IMG, "_tmp.png")
    fig.savefig(png, dpi=200, facecolor="#ffffff")
    Image.open(png).convert("RGB").save(os.path.join(IMG, "bgr_fringe.webp"), "WEBP", quality=90, method=6)
    os.remove(png)
    print("wrote bgr_fringe.webp")


def color():
    row = []
    for name in ("white_brown_20261116", "grey_silver_20261115"):
        rgb, a = load(name)
        back = measure.background(rgb)
        img = on_dark(rgb, a)
        img[measure.leftover(rgb, a, back)] = [0.85, 0.05, 0.1]
        img[measure.enclosed(rgb, a, back)] = [0.1, 0.85, 0.95]
        row.append(img[90:690, 120:760])
    panels([row], ["白い背景・茶髪", "灰色の背景・銀髪"], "bgr_color.webp", scale=1.0)


def clean():
    rows = []
    for name in ("white_silver_20261116",):
        rgb, a = load(name)
        back = measure.background(rgb)
        at = window(a, 240)
        c = measure.clean(a, rgb, back)
        mid, right = crop(on_dark(rgb, a), at, 240), crop(on_dark(rgb, c), at, 240)
        # 消した後も残った、背景色とほぼ同じ色（ΔE 4 未満）の不透明な塊（30 画素以上）を丸で囲む
        d = np.linalg.norm(measure.lab(rgb) - measure.lab(back[None, None]), axis=-1)
        sub = crop(((c >= 0.5) & (d < 4)).astype(np.uint8), at, 240)
        labels, _ = ndimage.label(sub, structure=np.ones((3, 3)))
        for k, sl in enumerate(ndimage.find_objects(labels)):
            if sl is not None and (labels[sl] == k + 1).sum() >= 30:
                cy, cx = (sl[0].start + sl[0].stop) / 2, (sl[1].start + sl[1].stop) / 2
                r = max(sl[0].stop - sl[0].start, sl[1].stop - sl[1].start) / 2 + 8
                for img in (mid, right):
                    ring(img, cy, cx, r)
        rows.append([crop(rgb, at, 240), mid, right])
    panels(rows, ["描いた絵", "切り抜いた絵", "色で消した後"], "bgr_clean.webp", scale=1.6)


def ring(img, cy, cx, r, width=2.5):
    yy, xx = np.indices(img.shape[:2])
    dist = np.hypot(yy - cy, xx - cx)
    img[np.abs(dist - r) < width] = [1.0, 0.75, 0.0]


def rgba():
    im = np.asarray(Image.open(os.path.join(GEN, "rgba_green_brown_20261115.png")).convert("RGBA"), np.float32) / 255
    rgb, a = im[..., :3], im[..., 3]
    chk = (((np.indices(a.shape).sum(0) // 24) % 2) * 0.2 + 0.75)[..., None].repeat(3, -1)
    shown = a[..., None] * rgb + (1 - a[..., None]) * chk
    panels([[shown, rgb]], ["透明度どおりに表示", "透明度を捨てて表示"], "bgr_rgba.webp", scale=0.4)


def norm():
    name = "grey_brown_20261116"
    rgb, a = load(name, "node")
    _, b = load(name, "imagenet")
    box = (slice(150, 450), slice(150, 450))
    panels([[on_dark(rgb, a)[box], on_dark(rgb, b)[box]]], ["ComfyUI のノード（正規化なし）", "正規化あり"], "bgr_norm.webp", scale=1.6)


def main():
    os.makedirs(IMG, exist_ok=True)
    metrics = json.load(open(os.path.join(WORK, "metrics.json")))
    cover()
    mask()
    edges()
    fringe(metrics)
    color()
    clean()
    rgba()
    norm()


if __name__ == "__main__":
    main()
