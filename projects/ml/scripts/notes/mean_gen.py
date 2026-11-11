"""mean ノートの実験と図を生成するスクリプト。

本文に載せた実験（画像の画素の平均、1.0 を足し続けた合計、平均の書き方の比較、
California Housing の世帯人数、Python と NumPy の速さの比）を同じ順に実行し、
出力を標準出力に、図を Page Bundle に WebP で保存する。
実行: cd projects/ml && .venv/bin/python scripts/notes/mean_gen.py
確認した版: NumPy 2.5.4、pandas 3.1.1、scikit-learn 1.9.1、matplotlib 3.11.2
"""
import timeit
from io import BytesIO
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import numpy as np
import pandas as pd
from PIL import Image
from sklearn.datasets import fetch_california_housing, load_sample_images
from sklearn.preprocessing import StandardScaler

NOTE_DIR = Path(__file__).resolve().parents[2] / "notes" / "math" / "mean"
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10,
                     "axes.spines.top": False, "axes.spines.right": False})
BLUE, RED, GREEN, INK, GRAY = "#7aa6c2", "#e15759", "#59a14f", "#333333", "#999999"
CH_COLORS = {"R": RED, "G": GREEN, "B": "#4e79a7"}


def save(fig, name):
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight", facecolor="#ffffff")
    plt.close(fig)
    buf.seek(0)
    Image.open(buf).convert("RGB").save(NOTE_DIR / name, "WEBP", quality=90, method=6)


# ---- 実験 1: 画像の画素の平均を、チャンネルごとに float32 で取る ----
photos = load_sample_images().images  # 427×640 の写真 2 枚（china.jpg、flower.jpg）


def make_crops(n_images, seed=0):
    """2 枚の写真から 224×224 の切り抜きを n_images 枚作り、0〜1 の float32 にする。"""
    rng = np.random.default_rng(seed)
    crops = []
    for k in range(n_images):
        im = photos[k % 2]
        y = rng.integers(0, im.shape[0] - 224)
        x = rng.integers(0, im.shape[1] - 224)
        crops.append(im[y:y + 224, x:x + 224])
    return np.stack(crops).astype(np.float32) / 255  # 形は (枚数, 224, 224, 3)


counts = [50, 100, 200, 300, 400, 600, 800, 1000]
res32, res64 = [], []
for n in counts:
    X = make_crops(n)
    m32 = X.mean(axis=(0, 1, 2))  # float32 のまま、チャンネルごとの平均
    m64 = X.mean(axis=(0, 1, 2), dtype=np.float64)  # 合計を float64 で取る
    res32.append(m32)
    res64.append(m64)
    print(f"{n:5d} 枚: float32 {np.round(m32, 3)}  float64 {np.round(m64, 3)}")
res32, res64 = np.array(res32), np.array(res64)

fig, ax = plt.subplots(figsize=(7.2, 3.8))
for i, ch in enumerate("RGB"):
    ax.plot(counts, res64[:, i], color=CH_COLORS[ch], lw=1.5, ls="--", alpha=0.8)
    ax.plot(counts, res32[:, i], color=CH_COLORS[ch], lw=2, marker="o", ms=4)
    ax.text(1015, res64[-1, i], f"{ch} {res64[-1, i]:.3f}", color=CH_COLORS[ch], va="center", fontsize=9)
ax.text(1015, res32[-1, 0], f"3 つとも {res32[-1, 0]:.3f}", color=INK, va="center", fontsize=9)
ax.plot([], [], color=INK, lw=2, marker="o", ms=4, label="float32 のまま（X.mean(axis=(0, 1, 2))）")
ax.plot([], [], color=INK, lw=1.5, ls="--", label="合計を float64 で取る（dtype=np.float64）")
ax.set_xlabel("画像の枚数（1 枚 = 224×224 画素）")
ax.set_ylabel("チャンネルごとの画素の平均")
ax.set_xlim(0, 1120)
ax.set_ylim(0.31, 0.56)
ax.legend(loc="lower left", fontsize=9, frameon=False)
save(fig, "mean_cover.webp")

# ---- 実験 1 の確かめ: 600 枚で、合計が 8,388,608 を超えた後に増えた量と、0.5 より大きい画素の数 ----
X600 = make_crops(600)
bias = {}
for c, ch in enumerate("RGB"):
    v = X600[..., c].ravel()
    cs = np.cumsum(v)  # axis=(0, 1, 2) の平均と同じく、float32 で順に足した途中の合計
    k = np.searchsorted(cs, 2**23)  # 合計が 8,388,608 を超えた位置
    after = v[k + 1:]  # その後に足した画素
    grown = float(cs[-1]) - float(cs[k])
    print(f"{ch}: 8,388,608 を超えた後に増えた量 {grown:.0f}、0.5 より大きい画素 {(after > 0.5).sum()} 個、"
          f"1 として足した割合 {(after > 0.5).mean():.3f}、値の平均 {after.mean():.3f}")
    bias[ch] = ((after > 0.5).mean(), after.mean())
del X600

# 図: 間隔 1 と間隔 2 の数直線で、足した値がどこへ丸められるか
fig, axes = plt.subplots(2, 1, figsize=(8, 3.6))
rows = [
    (axes[0], "合計が 16,777,216 の時（隣の数との間隔は 2）",
     [16_777_214, 16_777_216, 16_777_218], [(1.0, 16_777_216, "1 を足す → ちょうど中間。最後の桁が 0 の側へ丸めて戻る")]),
    (axes[1], "合計が 8,388,608〜16,777,216 の時（隣の数との間隔は 1）",
     [8_388_609, 8_388_610, 8_388_611], [(0.3, 8_388_610, "0.3 の画素 → 戻る（0 を足した）"),
                                          (0.7, 8_388_611, "0.7 の画素 → 1 つ先へ（1 を足した）")]),
]
for ax, title, ticks, adds in rows:
    base = ticks[1]
    ax.plot([ticks[0] - 0.4, ticks[-1] + 0.4], [0, 0], color=INK, lw=1)
    for t in ticks:
        ax.plot([t, t], [-0.12, 0.12], color=INK, lw=1.2)
        ax.text(t, -0.32, f"{t:,}", ha="center", va="top", fontsize=9, color=INK)
    ax.plot(base, 0, "o", color=INK, ms=6)
    for j, (d, to, label) in enumerate(adds):
        x = base + d
        ax.plot(x, 0, "o", mfc="#ffffff", mec=RED, ms=6)
        ax.annotate("", xy=(to, 0.08), xytext=(x, 0.08),
                    arrowprops={"arrowstyle": "->", "color": RED, "lw": 1.2,
                                "connectionstyle": "arc3,rad=-0.6"})
        right = len(adds) == 1 or j == 1
        ax.text(x + (0.08 if right else -0.08), 0.75, label, fontsize=9, color=RED, va="center",
                ha="left" if right else "right")
    ax.set_title(title, fontsize=10, loc="left")
    ax.set_xlim(ticks[0] - 1.4, ticks[-1] + 1.6)
    ax.set_ylim(-0.75, 1.3)
    ax.axis("off")
fig.tight_layout()
save(fig, "mean_rounding.webp")

# 図: 600 枚で、1 として足した割合と、本当の値の平均
fig, ax = plt.subplots(figsize=(7.2, 3.4))
xs3 = np.arange(3)
frac = [bias[ch][0] for ch in "RGB"]
true = [bias[ch][1] for ch in "RGB"]
ax.bar(xs3 - 0.18, true, width=0.34, color="#d9d9d9")
ax.bar(xs3 + 0.18, frac, width=0.34, color=[CH_COLORS[ch] for ch in "RGB"])
for x, a, b in zip(xs3, true, frac):
    ax.text(x - 0.18, a + 0.01, f"{a:.3f}", ha="center", fontsize=9, color=INK)
    ax.text(x + 0.18, b + 0.01, f"{b:.3f}", ha="center", fontsize=9, color=INK)
ax.set_xticks(np.concatenate([xs3 - 0.18, xs3 + 0.18]),
              [f"{ch} の\n値の平均" for ch in "RGB"] + [f"{ch} を 1 として\n足した割合" for ch in "RGB"], fontsize=8.5)
ax.set_title("600 枚で、合計が 8,388,608 を超えた後に足した画素", fontsize=10)
ax.set_ylim(0, 0.75)
save(fig, "mean_bias.webp")

# ---- 実験 2: 1.0 を足し続けると、合計が 16,777,216 で止まる ----
n = 20_000_000
ones = np.ones((n, 2), dtype=np.float32)  # 2 列の行列。1 列目だけを見る
print("2 列の行列の axis=0 の平均:", ones.mean(axis=0))
print("1 次元の配列の平均:", ones[:, 0].copy().mean())
running = np.cumsum(ones[:, 0])  # float32 で 1 つずつ順に足した途中の合計
print("途中の合計の最後:", running[-1], " 2**24 =", 2**24)
for v in [2.0**22, 2.0**23, 2.0**24, 2.0**25]:
    print(f"{v:>12,.0f} の隣の float32 との間隔: {np.spacing(np.float32(v))}")

fig, ax = plt.subplots(figsize=(7.2, 3.4))
k = np.arange(1, n + 1)
step = 20_000
ax.plot(k[::step] / 1e6, k[::step] / 1e6, color=GRAY, lw=1.5, ls="--", label="正しい合計")
ax.plot(k[::step] / 1e6, running[::step] / 1e6, color=RED, lw=2, label="float32 で順に足した合計")
ax.axhline(2**24 / 1e6, color=INK, lw=0.8, ls=":")
ax.text(0.3, 2**24 / 1e6 + 0.5, "16,777,216（2 の 24 乗）。ここから先は 1 を足しても変わらない", fontsize=9, color=INK)
ax.set_xlabel("足した回数（百万回）")
ax.set_ylabel("合計（百万）")
ax.set_ylim(0, 21.5)
ax.legend(loc="lower right", fontsize=9, frameon=False)
save(fig, "mean_stall.webp")

# ---- 図: 順に足す場合と、2 つずつ組にして足す場合（pairwise summation） ----
fig, axes = plt.subplots(1, 2, figsize=(9, 3.4))
box = {"boxstyle": "round,pad=0.3", "fc": "#ffffff", "ec": GRAY}
ax = axes[0]
ax.set_title("順に足す（合計に 1 つずつ足す）", fontsize=10)
for i in range(8):
    ax.text(i, 0, "1", ha="center", va="center", fontsize=10, bbox=box)
    acc = i + 1
    ax.text(i, 1.4, f"{acc}", ha="center", va="center", fontsize=10,
            bbox={**box, "fc": "#fbe3e3" if i >= 5 else "#ffffff", "ec": RED if i >= 5 else GRAY})
    ax.annotate("", xy=(i, 1.15), xytext=(i, 0.25), arrowprops={"arrowstyle": "->", "color": GRAY, "lw": 0.8})
    if i > 0:
        ax.annotate("", xy=(i - 0.25, 1.4), xytext=(i - 0.75, 1.4),
                    arrowprops={"arrowstyle": "->", "color": GRAY, "lw": 0.8})
ax.text(3.5, 2.3, "赤: 合計が足す 1 の 6 倍以上。差が開くほど 1 が丸めで消えやすい", ha="center", fontsize=9, color=RED)
ax.set_xlim(-0.6, 7.6)
ax.set_ylim(-0.6, 2.8)
ax.axis("off")
ax = axes[1]
ax.set_title("2 つずつ組にして足す（pairwise summation）", fontsize=10)
levels = [[1] * 8, [2] * 4, [4] * 2, [8]]
for lv, vals in enumerate(levels):
    w = 8 / len(vals)
    for j, v in enumerate(vals):
        x = (j + 0.5) * w - 0.5
        ax.text(x, lv * 0.75, f"{v}", ha="center", va="center", fontsize=10, bbox=box)
        if lv > 0:
            for c in (2 * j, 2 * j + 1):
                cx = (c + 0.5) * (8 / len(levels[lv - 1])) - 0.5
                ax.plot([cx, x], [(lv - 1) * 0.75 + 0.18, lv * 0.75 - 0.18], color=GRAY, lw=0.8)
ax.text(3.5, 3.0, "いつも同じくらいの大きさ同士を足す", ha="center", fontsize=9, color=INK)
ax.set_xlim(-0.6, 7.6)
ax.set_ylim(-0.6, 3.4)
ax.axis("off")
save(fig, "mean_pairwise.webp")

# ---- 図: (枚数, 224, 224, 3) の配列のメモリの上の並び ----
fig, ax = plt.subplots(figsize=(8, 1.9))
cells = [(ch, p) for p in range(4) for ch in "RGB"]
for i, (ch, p) in enumerate(cells):
    is_g = ch == "G"
    ax.add_patch(plt.Rectangle((i, 0), 0.92, 0.9, fc="#e3f0df" if is_g else "#ffffff",
                               ec=GREEN if is_g else GRAY, lw=1.2 if is_g else 0.8))
    ax.text(i + 0.46, 0.45, f"{ch}{p}", ha="center", va="center", fontsize=10, color=INK)
for p in range(3):
    a, b = 3 * p + 1, 3 * p + 4
    ax.annotate("", xy=(b + 0.46, 0.95), xytext=(a + 0.46, 0.95),
                arrowprops={"arrowstyle": "->", "color": GREEN, "lw": 1.1, "connectionstyle": "arc3,rad=-0.4"})
    ax.text((a + b) / 2 + 0.46, 1.75, "3 つごと", ha="center", fontsize=9, color=GREEN)
ax.text(12.3, 0.45, "…", va="center", fontsize=12, color=INK)
ax.text(0, -0.45, "数字は画素の番号。1 画素の R・G・B が隣り合い、G だけを足すと 3 つごとに飛ぶ", fontsize=9, color=INK)
ax.set_xlim(-0.2, 13)
ax.set_ylim(-0.8, 2.1)
ax.axis("off")
save(fig, "mean_layout.webp")

# ---- 実験 3: 同じ 800 枚の画像で、平均の書き方を変える（G チャンネル） ----
X = make_crops(800)
flat = X.reshape(-1, 3)  # (画素の数, 3)。チャンネルが一番内側に並ぶ
ways = {
    "X.mean(axis=(0, 1, 2))": lambda: X.mean(axis=(0, 1, 2))[1],
    "X.mean(axis=(0, 1, 2), dtype=np.float64)": lambda: X.mean(axis=(0, 1, 2), dtype=np.float64)[1],
    "X[..., 1].mean()": lambda: X[..., 1].mean(),
    "np.ascontiguousarray(flat.T).mean(axis=1)": lambda: np.ascontiguousarray(flat.T).mean(axis=1)[1],
    "pd.DataFrame(flat).mean()": lambda: pd.DataFrame(flat).mean().iloc[1],
    "StandardScaler().fit(flat).mean_": lambda: StandardScaler().fit(flat).mean_[1],
}
for label, f in ways.items():
    print(f"{label:45s} G = {f():.4f}")
print("np.mean の文書の float32 の例:", np.mean(np.vstack([np.ones(512 * 512, np.float32),
                                                       np.full(512 * 512, 0.1, np.float32)])))

# ---- 実験 4: California Housing の「1 世帯あたりの人数」の平均 ----
house = fetch_california_housing(as_frame=True).frame
households = house["Population"] / house["AveOccup"]  # 区画ごとの世帯の数
occ = house["AveOccup"]
print("区画の数:", len(house))
print(f"区画ごとの値の平均: {occ.mean():.3f}")
print(f"世帯の数で重みを付けた平均: {np.average(occ, weights=households):.3f}")
print(f"全人口 / 全世帯: {house['Population'].sum() / households.sum():.3f}")
top = occ.idxmax()
print(f"最大の区画: AveOccup {occ[top]:.1f}、人口 {house['Population'][top]:.0f}、世帯 {households[top]:.0f}")
print(f"最大の区画を除いた区画ごとの平均: {occ.drop(top).mean():.3f}")
few = households < 50
print(f"世帯が 50 未満の区画: {few.sum()} 個、その AveOccup の平均 {occ[few].mean():.2f}")

fig, ax = plt.subplots(figsize=(7.2, 3.8))
ax.scatter(households, occ, s=4, alpha=0.25, color=BLUE, edgecolors="none")
ax.set_xscale("log")
ax.set_yscale("log")
ax.axhline(occ.mean(), color=RED, lw=1.5, label=f"区画ごとの値の平均 {occ.mean():.2f}")
ax.axhline(np.average(occ, weights=households), color=INK, lw=1.5, ls="--",
           label=f"世帯の数で重みを付けた平均 {np.average(occ, weights=households):.2f}")
ax.annotate(f"人口 {house['Population'][top]:.0f}・世帯 {households[top]:.0f} の区画\nAveOccup {occ[top]:.0f}",
            xy=(households[top], occ[top]), xytext=(8, 300), fontsize=9, color=INK,
            arrowprops={"arrowstyle": "->", "color": INK, "lw": 0.8})
ax.set_xlabel("区画の世帯の数（対数）")
ax.set_ylabel("1 世帯あたりの人数 AveOccup（対数）")
ax.legend(loc="upper right", fontsize=9, frameon=False)
save(fig, "mean_weighted.webp")

# ---- 実験 5: Python の sum と NumPy の mean の速さの比を、2 通りに平均する ----
rng = np.random.default_rng(0)
sizes = [10, 100, 1_000, 10_000, 100_000, 1_000_000]
t_py, t_np = [], []
for size in sizes:
    arr = rng.normal(1000, 10, size)
    lst = arr.tolist()
    num = max(1, 200_000 // size)
    t_py.append(min(timeit.repeat(lambda: sum(lst) / len(lst), number=num, repeat=7)) / num)
    t_np.append(min(timeit.repeat(lambda: arr.mean(), number=num, repeat=7)) / num)
t_py, t_np = np.array(t_py), np.array(t_np)
r = t_py / t_np  # 1 より大きければ Python の方が遅い
for size, a, b, q in zip(sizes, t_py, t_np, r):
    print(f"{size:>9,d} 個: Python {a * 1e6:9.2f} µs、NumPy {b * 1e6:7.2f} µs、Python / NumPy = {q:.2f}")
print(f"Python / NumPy の算術平均: {r.mean():.2f}")
print(f"NumPy / Python の算術平均: {(1 / r).mean():.2f}")
print(f"Python / NumPy の幾何平均: {np.exp(np.log(r).mean()):.2f}")
print(f"NumPy / Python の幾何平均: {np.exp(np.log(1 / r).mean()):.2f}")

fig, axes = plt.subplots(1, 2, figsize=(9, 3.6), sharey=True)
xs = np.arange(len(sizes))
panels = [(axes[0], r, "Python の時間 / NumPy の時間"), (axes[1], 1 / r, "NumPy の時間 / Python の時間")]
for ax, vals, title in panels:
    ax.bar(xs, vals, color=[RED if q > 1 else BLUE for q in vals], width=0.6)
    for x, q in zip(xs, vals):
        ax.text(x, q * 1.15, f"{q:.2f}", ha="center", fontsize=8, color=INK)
    ax.set_yscale("log")
    ax.axhline(1, color=INK, lw=0.8)
    am, gm = vals.mean(), np.exp(np.log(vals).mean())
    ax.axhline(am, color=RED, lw=1.2, ls="--", label=f"算術平均 {am:.2f}")
    ax.axhline(gm, color=INK, lw=1.2, ls=":", label=f"幾何平均 {gm:.2f}")
    ax.set_xticks(xs, [f"{s:,}" for s in sizes], rotation=30, fontsize=8)
    ax.set_xlabel("配列の要素の数")
    ax.set_title(title, fontsize=10)
    handles, _ = ax.get_legend_handles_labels()
    handles += [Patch(color=RED, label="1 より上（分子の方が遅い）"), Patch(color=BLUE, label="1 より下（分子の方が速い）")]
    ax.legend(handles=handles, loc="upper left", fontsize=8.5, frameon=False)
axes[0].set_ylabel("時間の比（対数。1 より上は分子の方が遅い）")
axes[0].set_ylim(0.02, 3000)
save(fig, "mean_ratio.webp")
