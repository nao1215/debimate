"""深度マップと体型・服の厚みのノートの図を作る。

- depth_cover.webp: プロンプトだけと、4 つの 3D モデルの深度マップ → 生成した絵（同じプロンプトと seed）
- depth_dolls.webp: 2 体の 3D モデルの深度マップに、頭の高さごとの目盛りを引いた図
- depth_bulk.webp: 服の厚みなし・ありの深度マップ。ありの方に、なしの輪郭を重ねる
- depth_measure.webp: 計測の線（頭頂・肩・股関節・膝・足首・足の裏と、太ももの幅）を、3D モデルの深度マップと生成した絵に引く
- depth_ratio.webp: 脚の比と肩より上の比（3D モデルと、生成した絵）
- depth_thigh.webp: 太ももの幅（鎧のプロンプトと、ゆったりした服のプロンプト）
- depth_strength.webp: 強さ 0.4・0.7・1.0 で、脚の比と太ももの幅がどう動くか
- depth_loose.webp: ゆったりした服のプロンプトで、プロンプトだけと 4 つの 3D モデルの 5 列 × 2 seed

    uv run --with pillow==12.0.0 --with matplotlib==3.9.2 --with numpy==2.1.3 \
        python figures.py <深度マップのディレクトリ> <生成した PNG のディレクトリ>

計測の値は lab/metrics.json（body_metrics.py の出力）を読む。
"""
import json
import sys
from pathlib import Path

import matplotlib
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402

HERE = Path(__file__).resolve().parent
LAB, IMAGES = HERE / "lab", HERE / "images"
IMAGES.mkdir(exist_ok=True)
CJK = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
font_manager.fontManager.addfont(CJK)
plt.rcParams["font.family"] = font_manager.FontProperties(fname=CJK).get_name()
INK, SUB, GRID = "#1f1f1f", "#666666", "#dddddd"
# 3D モデルごとの色: 現実の比率は青、アニメの比率は黄土。服の厚みありは濃く
COLORS = {"real_plain": "#9cc3db", "real_bulk": "#3f7fa6", "anime_plain": "#e6c27a", "anime_bulk": "#b07d1e"}
DOLLS = list(COLORS)
LABELS = {"text": "プロンプトだけ", "real_plain": "標準体型\n服の厚みなし", "real_bulk": "標準体型\n服の厚みあり",
          "anime_plain": "アニメ体型\n服の厚みなし", "anime_bulk": "アニメ体型\n服の厚みあり"}
SEEDS = (20261112, 20261113)
# 3D モデルの実寸（make_dolls.py の出力）。頭の高さ m と身長 m
DOLL_SIZE = {"real": (0.210, 1.590), "anime": (0.184, 1.760)}
PX_PER_M = 1216 / 2.1  # 平行投影のカメラの ortho_scale 2.1 m が縦 1216 px


def font(size):
    return ImageFont.truetype(CJK, size)


def to_webp(img, name):
    img.convert("RGB").save(IMAGES / name, "WEBP", quality=90, method=6)
    print("wrote", IMAGES / name)


def crop_fig(path, box=(166, 60, 666, 1216)):
    """832 x 1216 の絵から人物の周りを切る（3D モデルを使った絵は全て同じ枠）。"""
    return Image.open(path).convert("RGB").crop(box)


def crop_text(path):
    """プロンプトだけの絵は人物が大きく描かれるので、縦を全部残して同じ縦横比（500 : 1156）で切る。"""
    return crop_fig(path, (153, 0, 679, 1216))


def labeled_grid(rows, col_labels, row_labels, cell_w, name, scale=0.5):
    """rows: 画像の 2 次元の列。None は灰色の「なし」。"""
    cw, ch = int(rows[0][0 if rows[0][0] else 1].width * scale), int(rows[0][0 if rows[0][0] else 1].height * scale)
    left, top, gap = 120 if row_labels else 20, 70, 12
    W = left + len(col_labels) * (cw + gap) + 8
    H = top + len(rows) * (ch + gap) + 8
    c = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(c)
    for j, lab in enumerate(col_labels):
        x = left + j * (cw + gap) + cw // 2
        d.multiline_text((x, top // 2), lab, font=font(20), fill=INK, anchor="mm", align="center", spacing=4)
    for i, row in enumerate(rows):
        y = top + i * (ch + gap)
        if row_labels:
            d.multiline_text((left // 2, y + ch // 2), row_labels[i], font=font(22), fill=INK, anchor="mm",
                             align="center")
        for j, im in enumerate(row):
            x = left + j * (cw + gap)
            if im is None:
                d.rectangle([x, y, x + cw, y + ch], fill="#f2f2f2")
                d.text((x + cw // 2, y + ch // 2), "なし", font=font(22), fill=SUB, anchor="mm")
            else:
                c.paste(im.resize((cw, ch), Image.LANCZOS), (x, y))
                d.rectangle([x, y, x + cw, y + ch], outline="#cccccc", width=1)
    to_webp(c, name)


def cover(depth, gen):
    seed = SEEDS[0]
    top = [None] + [crop_fig(depth / f"{k}_front.png") for k in DOLLS]
    bottom = [crop_text(gen / f"text_{seed}.png")] + [crop_fig(gen / f"{k}_front_s070_{seed}.png") for k in DOLLS]
    labeled_grid([top, bottom], [LABELS[k] for k in ["text"] + DOLLS], ["深度\nマップ", "生成した\n絵"], 0,
                 "depth_cover.webp", scale=0.44)


def loose(depth, gen):
    rows = []
    for seed in SEEDS:
        rows.append([crop_text(gen / f"loose_text_{seed}.png")] +
                    [crop_fig(gen / f"loose_{k}_front_s070_{seed}.png") for k in DOLLS])
    labeled_grid(rows, [LABELS[k] for k in ["text"] + DOLLS], [f"seed\n{s}" for s in SEEDS], 0,
                 "depth_loose.webp", scale=0.44)


def dolls(depth):
    """2 体の深度マップに、頭の高さごとの目盛りを引く。"""
    panels = []
    for kind in ("real", "anime"):
        im = Image.open(depth / f"{kind}_plain_front.png").convert("RGB")
        g = np.asarray(im.convert("L"))
        rows = np.where((g >= 13).any(axis=1))[0]
        top, bottom = int(rows[0]), int(rows[-1])
        im = im.crop((166, 60, 666, 1216))
        top, bottom = top - 60, bottom - 60
        d = ImageDraw.Draw(im)
        head_px = (bottom - top) * DOLL_SIZE[kind][0] / DOLL_SIZE[kind][1]
        n = (bottom - top) / head_px
        for i in range(int(n) + 1):
            y = top + i * head_px
            d.line([(18, y), (60, y)], fill="#e15759", width=3)
            d.text((10, y + head_px / 2), str(i + 1) if i + 1 <= n else "", font=font(22), fill="#e15759",
                   anchor="lm") if i < int(n) else None
        d.line([(39, top), (39, bottom)], fill="#e15759", width=2)
        panels.append((im, kind, n))
    W = sum(p[0].width for p in panels) + 60
    c = Image.new("RGB", (W, panels[0][0].height + 80), "white")
    d = ImageDraw.Draw(c)
    x = 20
    for im, kind, n in panels:
        c.paste(im, (x, 70))
        name = "標準体型（MPFB の既定）" if kind == "real" else "アニメ体型（脚を長く、頭を小さく）"
        d.text((x + im.width // 2, 22), name, font=font(24), fill=INK, anchor="mm")
        d.text((x + im.width // 2, 52), f"{n:.1f} 頭身", font=font(22), fill="#e15759", anchor="mm")
        x += im.width + 20
    to_webp(c.resize((c.width // 2 * 2 * 3 // 4, c.height * 3 // 4), Image.LANCZOS), "depth_dolls.webp")


def bulk(depth):
    """服の厚みなし・あり。ありの方に、なしの輪郭を赤い線で重ねる。"""
    plain = Image.open(depth / "real_plain_front.png").convert("RGB")
    thick = Image.open(depth / "real_bulk_front.png").convert("RGB")
    mask = plain.convert("L").point(lambda v: 255 if v >= 13 else 0)
    edge = mask.filter(ImageFilter.FIND_EDGES).filter(ImageFilter.MaxFilter(3))
    over = thick.copy()
    over.paste(Image.new("RGB", over.size, "#e15759"), (0, 0), edge)
    box = (166, 150, 666, 1216)
    ims = [plain.crop(box), over.crop(box)]
    W = sum(i.width for i in ims) + 60
    c = Image.new("RGB", (W, ims[0].height + 60), "white")
    d = ImageDraw.Draw(c)
    x = 20
    for im, lab in zip(ims, ["服の厚みなし", "服の厚みあり（赤い線は厚みなしの輪郭）"]):
        c.paste(im, (x, 56))
        d.text((x + im.width // 2, 28), lab, font=font(24), fill=INK, anchor="mm")
        x += im.width + 20
    to_webp(c.resize((c.width * 3 // 4, c.height * 3 // 4), Image.LANCZOS), "depth_bulk.webp")


def measure(depth, gen, m):
    """計測の線: 同じ方法で、3D モデルの深度マップと生成した絵に線を引く。"""
    panels = []
    for src, tag, title in [(depth / "real_plain_front.png", "real_plain_front", "3D モデルの深度マップ"),
                            (gen / "real_plain_front_s070_20261112.png", "real_plain_front_s070_20261112",
                             "生成した絵")]:
        im = Image.open(src).convert("RGB")
        y = m[tag]["y"]
        d = ImageDraw.Draw(im)
        for k, lab, col in [("top", "頭頂", "#666666"), ("shoulder", "肩", "#3f7fa6"), ("hip", "股関節", "#b07d1e"),
                            ("knee", "膝", "#b07d1e"), ("ankle", "足首", "#3f7fa6"), ("bottom", "足の裏", "#666666")]:
            d.line([(150, y[k]), (690, y[k])], fill=col, width=3)
            d.text((700, y[k]), lab, font=font(30), fill=col, anchor="lm")
        runs = [r for r in m[tag]["row_runs"] if r[1] - r[0] >= 8]  # 体の画素が続く区間（左右の脚）
        for a, b in runs:
            d.line([(a, y["row"]), (b, y["row"])], fill="#e15759", width=7)
        d.text((runs[0][0] - 10, y["row"]), "太ももの幅", font=font(30), fill="#e15759", anchor="rm")
        panels.append((im.crop((0, 180, 832, 1216)), title))
    W = sum(p[0].width for p in panels) + 60
    c = Image.new("RGB", (W, panels[0][0].height + 70), "white")
    d = ImageDraw.Draw(c)
    x = 20
    for im, title in panels:
        c.paste(im, (x, 64))
        d.text((x + im.width // 2, 32), title, font=font(32), fill=INK, anchor="mm")
        x += im.width + 20
    to_webp(c.resize((c.width // 2, c.height // 2), Image.LANCZOS), "depth_measure.webp")


def savefig(fig, name):
    png = IMAGES / (name + ".png")
    fig.savefig(png, dpi=200, facecolor="#ffffff", bbox_inches="tight")
    plt.close(fig)
    Image.open(png).save(IMAGES / (name + ".webp"), "WEBP", quality=90, method=6)
    png.unlink()
    print("wrote", IMAGES / (name + ".webp"))


def style(ax):
    ax.grid(axis="y", color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


def dot_panel(ax, m, key, prefix="", poses=("front", "turn"), title="", with_text=True):
    """3D モデルごとに、ポーズごとの 3D モデルの値（横線）と生成した絵の値（点）を並べる。
    ポーズが 2 つなら、各 3D モデルの左が正面、右が斜め。with_text なら左端にプロンプトだけ。"""
    cats = (["text"] if with_text else []) + DOLLS
    offs = {"front": -0.2, "turn": 0.2} if len(poses) == 2 else {"front": 0.0}
    for i, k in enumerate(cats):
        if k == "text":
            vals = [m[f"{prefix}text_{s}"][key] for s in SEEDS]
            ax.scatter([i] * len(vals), vals, s=46, color="#999999", zorder=3)
            continue
        for p in poses:
            x = i + offs[p]
            ax.hlines(m[f"{k}_{p}"][key], x - 0.15, x + 0.15, color=INK, lw=2.2, zorder=2)
            vals = [m[f"{prefix}{k}_{p}_s070_{s}"][key] for s in SEEDS]
            ax.scatter([x - 0.05, x + 0.05], vals, s=46, color=COLORS[k], edgecolor=INK, lw=0.6, zorder=3,
                       marker="o" if p == "front" else "s")
    ax.set_xticks(range(len(cats)), [LABELS[k] for k in cats], fontsize=9)
    ax.set_title(title, fontsize=12, loc="left")
    style(ax)


def ratio(m):
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
    dot_panel(axes[0], m, "leg", title="脚の比（股関節から足の裏 ÷ 全身の高さ）")
    dot_panel(axes[1], m, "above_shoulder", title="肩より上の比（頭頂から肩 ÷ 全身の高さ）")
    fig.text(0.99, 0.005, "横線 = 3D モデル、丸 = 正面の絵、四角 = 斜めの絵（各 3D モデルの左が正面、右が斜め）", ha="right",
             fontsize=9, color=SUB)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    savefig(fig, "depth_ratio")


def thigh(m):
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8), sharey=True)
    # プロンプトだけの絵は体の向きが決まらず、太ももの幅を比べられないので載せない
    dot_panel(axes[0], m, "thigh_width", title="鎧のプロンプト（正面と斜め、各 2 seed）", with_text=False)
    dot_panel(axes[1], m, "thigh_width", prefix="loose_", poses=("front",),
              title="ゆったりした服のプロンプト（正面、2 seed）", with_text=False)
    axes[0].set_ylabel("太ももの幅（÷ 肩から足首）")
    fig.text(0.99, 0.005, "横線 = 3D モデル、丸 = 正面の絵、四角 = 斜めの絵（左の図は各 3D モデルの左が正面、右が斜め）",
             ha="right", fontsize=9, color=SUB)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    savefig(fig, "depth_thigh")


def strength(m):
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
    xs = [0.4, 0.7, 1.0]
    for ax, key, title in [(axes[0], "leg", "脚の比"), (axes[1], "thigh_width", "太ももの幅")]:
        for k in DOLLS:
            ys = [np.mean([m[f"{k}_front_s{int(x * 100):03d}_{s}"][key] for s in SEEDS]) for x in xs]
            ax.plot(xs, ys, "-o", color=COLORS[k], lw=2, ms=6, mec=INK, mew=0.6,
                    label=LABELS[k].replace("\n", "・"))
            ax.hlines(m[f"{k}_front"][key], 0.36, 1.04, color=COLORS[k], lw=1.2, ls="--")
        if key == "leg":
            text = np.mean([m[f"text_{s}"][key] for s in SEEDS])
            ax.hlines(text, 0.36, 1.04, color="#999999", lw=1.2, ls=":")
            ax.text(1.05, text, "プロンプトだけ", va="center", fontsize=9, color=SUB)
        ax.set_xticks(xs)
        ax.set_xlabel("ControlNet の強さ（strength）")
        ax.set_title(f"{title}（正面。点 = 2 seed の平均、破線 = 3D モデル）", fontsize=12, loc="left")
        style(ax)
    axes[1].legend(fontsize=8, frameon=False, loc="upper left", bbox_to_anchor=(1.12, 1))
    fig.tight_layout()
    savefig(fig, "depth_strength")


def main():
    depth, gen = Path(sys.argv[1]), Path(sys.argv[2])
    m = json.load(open(LAB / "metrics.json"))
    cover(depth, gen)
    loose(depth, gen)
    dolls(depth)
    bulk(depth)
    measure(depth, gen, m)
    ratio(m)
    thigh(m)
    strength(m)


if __name__ == "__main__":
    main()
