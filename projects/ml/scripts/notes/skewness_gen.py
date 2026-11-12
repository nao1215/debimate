"""skewness ノートの実験と図を生成するスクリプト。

本文に載せた実験（単位と log1p、歪度の符号、log1p の曲線、冪変換、標本の歪度と件数、
California の列ごとの歪度、目的変数の残差）を同じ順に実行し、
出力を標準出力に、図を Page Bundle に WebP で保存する。
実行: cd projects/ml && .venv/bin/python scripts/notes/skewness_gen.py
確認した版: NumPy 2.5.4、SciPy 1.18.1、scikit-learn 1.9.1、pandas 3.1.1
California Housing は初回だけ fetch_california_housing が StatLib の配布元から取得し、以降はキャッシュを読む。
"""
from io import BytesIO
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image
from scipy import stats
from sklearn.datasets import fetch_california_housing
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PowerTransformer

NOTE_DIR = Path(__file__).resolve().parents[2] / "notes" / "math" / "skewness"
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10,
                     "axes.spines.top": False, "axes.spines.right": False})
BLUE, RED, GREEN, ORANGE, INK, GRAY = "#7aa6c2", "#e15759", "#59a14f", "#f28e2b", "#333333", "#999999"


def save(fig, name):
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight", facecolor="#ffffff")
    plt.close(fig)
    buf.seek(0)
    Image.open(buf).convert("RGB").save(NOTE_DIR / name, "WEBP", quality=90, method=6)


# ============================================================
# 実験 1（表紙）: 住宅価格の単位を変えて log1p をかける
# ============================================================
y = fetch_california_housing().target          # 地区ごとの住宅価格の中央値。単位は 10 万ドル
units = [("100 万ドル", 0.1), ("10 万ドル", 1.0), ("1 ドル", 1e5)]
for unit, scale in units:
    x = y * scale
    print(f"{unit:>7} 単位: 生の歪度 {stats.skew(x):.2f}  log1p 後の歪度 {stats.skew(np.log1p(x)):+.2f}")

fig, axes = plt.subplots(2, 2, figsize=(10, 6.2))
axes = axes.ravel()
axes[0].hist(y, bins=50, color=BLUE, edgecolor="white")
axes[0].set_title(f"生の値（どの単位でも）  歪度 {stats.skew(y):.2f}", fontsize=13)
axes[0].set_xlabel("住宅価格（10 万ドル）", fontsize=11)
for ax, (unit, scale) in zip(axes[1:], units):
    z = np.log1p(y * scale)
    ax.hist(z, bins=50, color=ORANGE if scale != 1.0 else GREEN, edgecolor="white")
    ax.set_title(f"log1p（{unit}単位）  歪度 {stats.skew(z):+.2f}", fontsize=13)
    ax.set_xlabel(f"log1p(価格 / {unit})", fontsize=11)
for ax in axes:
    ax.set_yticks([])
    ax.tick_params(labelsize=10)
plt.tight_layout(h_pad=1.5)
save(fig, "skew_cover.webp")


# ============================================================
# 実験 2: 歪度の符号と、平均・中央値の位置
# ============================================================
rng = np.random.default_rng(0)
right = rng.lognormal(0.0, 0.6, 5000)
sym = rng.normal(2.0, 0.8, 5000)
left = -rng.lognormal(0.0, 0.6, 5000) + np.exp(2)
for name, data in [("右に長い", right), ("左右対称", sym), ("左に長い", left)]:
    print(f"{name}: 歪度 {stats.skew(data):+.2f}  平均 {data.mean():.2f}  中央値 {np.median(data):.2f}")

fig, axes = plt.subplots(1, 3, figsize=(12, 3.4), sharey=True)
for ax, (title, data) in zip(axes, [("右に長い（対数正規分布）", right),
                                    ("左右対称（正規分布）", sym),
                                    ("左に長い（対数正規分布を反転）", left)]):
    ax.hist(data, bins=40, color=BLUE, alpha=0.7, edgecolor="white")
    ax.axvline(data.mean(), color=RED, ls="--", lw=2, label=f"平均 {data.mean():.2f}")
    ax.axvline(np.median(data), color=GREEN, ls="--", lw=2, label=f"中央値 {np.median(data):.2f}")
    ax.set_title(f"{title}\n歪度 {stats.skew(data):+.2f}")
    ax.set_xlabel("値")
    ax.legend(fontsize=9)
axes[0].set_ylabel("件数")
plt.tight_layout()
save(fig, "skew_sign.webp")


# ============================================================
# 実験 3: log1p の曲線と、単位の倍率ごとの歪度
# ============================================================
scales = 10.0 ** np.arange(-3, 6.01, 0.25)
sk = np.array([stats.skew(np.log1p(y * c)) for c in scales])
print(f"log(y) の歪度: {stats.skew(np.log(y)):+.3f}")
for c in [1e-3, 1e-1, 1, 10, 1e5]:
    print(f"倍率 {c:<6g}: 中央値 {np.median(y * c):10.4g}  log1p 後の歪度 {stats.skew(np.log1p(y * c)):+.3f}")

fig, axes = plt.subplots(1, 2, figsize=(12, 3.8))
xs = np.logspace(-3, 5, 400)
ax = axes[0]
ax.plot(xs, np.log1p(xs), color=INK, lw=2, label="log1p(x)")
ax.plot(xs[xs < 3], xs[xs < 3], color=BLUE, ls="--", label="x（そのまま）")
ax.plot(xs[xs > 0.3], np.log(xs[xs > 0.3]), color=RED, ls="--", label="log(x)")
ax.set_xscale("log")
ax.set_xlabel("x（対数目盛り）")
ax.set_ylabel("変換後の値")
ax.axvspan(1e-3, 0.3, color=BLUE, alpha=0.08)
ax.axvspan(30, 1e5, color=RED, alpha=0.08)
ax.text(1.2e-3, 9.5, "x が 1 より十分小さい:\nほぼ x のまま", color=BLUE, fontsize=9, va="top")
ax.text(1e3, 2.2, "x が 1 より十分大きい:\nほぼ log(x)", color=RED, fontsize=9)
ax.set_ylim(-0.3, 12)
ax.legend(loc="upper center", fontsize=9)
ax.set_title("log1p(x) は、x の大きさで別の変換になる")

ax = axes[1]
ax.plot(scales, sk, color=INK, lw=2, marker="o", ms=3)
ax.axhline(stats.skew(y), color=BLUE, ls="--", label=f"生の値の歪度 {stats.skew(y):.2f}")
ax.axhline(stats.skew(np.log(y)), color=RED, ls="--", label=f"log(y) の歪度 {stats.skew(np.log(y)):+.2f}")
for unit, scale in units:
    s = stats.skew(np.log1p(y * scale))
    ax.scatter([scale], [s], color=GREEN if scale == 1.0 else ORANGE, s=60, zorder=3)
    ax.annotate(f"{unit}単位 {s:+.2f}", (scale, s), textcoords="offset points", xytext=(6, 6), fontsize=9)
ax.set_xscale("log")
ax.set_xlabel("配布時の単位（10 万ドル）に掛ける倍率（対数目盛り）")
ax.set_ylabel("log1p 後の歪度")
ax.legend(fontsize=9, loc="lower left")
ax.set_title("住宅価格の倍率ごとの、log1p 後の歪度")
plt.tight_layout()
save(fig, "skew_log1p_scale.webp")


# ============================================================
# 実験 4: Box-Cox と Yeo-Johnson は単位で変わるか
# ============================================================
for unit, scale in units:
    x = (y * scale).reshape(-1, 1)
    bc = PowerTransformer(method="box-cox").fit(x)
    yj = PowerTransformer(method="yeo-johnson").fit(x)
    print(f"{unit:>7} 単位: log1p {stats.skew(np.log1p(x.ravel())):+.2f}"
          f"  Box-Cox {stats.skew(bc.transform(x).ravel()):+.2f} (λ={bc.lambdas_[0]:.2f})"
          f"  Yeo-Johnson {stats.skew(yj.transform(x).ravel()):+.2f} (λ={yj.lambdas_[0]:.2f})")


# ============================================================
# 実験 5: 標本の歪度は件数で変わる
# ============================================================
true_skew = (np.exp(1) + 2) * np.sqrt(np.exp(1) - 1)   # log を取った値の標準偏差が 1 の対数正規分布の歪度
print(f"対数正規分布の歪度: {true_skew:.2f}")
rng = np.random.default_rng(0)
ns = [10, 30, 100, 1000, 10000]
samples = {}
for n in ns:
    g = np.array([stats.skew(rng.lognormal(0.0, 1.0, n)) for _ in range(500)])
    samples[n] = g
    bound = (n - 2) / np.sqrt(n - 1)                    # n 件の標本の歪度が取りうる最大値
    print(f"n={n:<6} 中央値 {np.median(g):.2f}  90% 点 {np.percentile(g, 90):.2f}  上限 {bound:.2f}")

x20 = rng.lognormal(0.0, 1.0, 20)
print(f"n=20 の同じ標本: scipy skew {stats.skew(x20):.3f}"
      f"  scipy skew(bias=False) {stats.skew(x20, bias=False):.3f}  pandas skew {pd.Series(x20).skew():.3f}")

fig, ax = plt.subplots(figsize=(8, 3.8))
pos = np.arange(len(ns))
ax.boxplot([samples[n] for n in ns], positions=pos, widths=0.5, showfliers=False,
           medianprops={"color": INK}, boxprops={"color": BLUE}, whiskerprops={"color": BLUE},
           capprops={"color": BLUE})
ax.axhline(true_skew, color=RED, ls="--", label=f"分布の歪度 {true_skew:.2f}")
for p, n in zip(pos[:2], ns[:2]):
    b = (n - 2) / np.sqrt(n - 1)
    ax.hlines(b, p - 0.3, p + 0.3, color=GRAY, ls=":", lw=2,
              label="n 件で取りうる上限 (n-2)/√(n-1)" if n == ns[0] else None)
for p, n in zip(pos, ns):
    ax.text(p + 0.28, np.median(samples[n]), f"{np.median(samples[n]):.2f}", fontsize=9, va="center")
ax.set_xticks(pos, [f"{n} 件\n上限 {(n - 2) / np.sqrt(n - 1):.2f}" for n in ns])
ax.set_ylim(0, 9)
ax.set_ylabel("標本の歪度（500 回）")
ax.set_xlabel("1 回に引く件数")
ax.legend(fontsize=9, loc="upper left")
ax.set_title("対数正規分布から引いた標本の歪度。箱は 25〜75% 点、ひげは 1.5 倍の範囲")
plt.tight_layout()
save(fig, "skew_sample_size.webp")


# ============================================================
# 実験 6: California Housing の列ごとの歪度と log1p
# ============================================================
X = fetch_california_housing(as_frame=True).frame.drop(columns=["Latitude", "Longitude"])
for col in X.columns:
    v = X[col].to_numpy()
    print(f"{col:<12} 中央値 {np.median(v):8.2f}"
          f"  生の歪度 {stats.skew(v):+6.2f}  log1p 後 {stats.skew(np.log1p(v)):+6.2f}")
for col, k in [("AveOccup", 10), ("AveBedrms", 10), ("AveBedrms", 200)]:
    v = np.sort(X[col].to_numpy())[:-k]                 # 大きい方から k 行を除く
    print(f"{col} の大きい {k} 行を除いた log1p 後の歪度: {stats.skew(np.log1p(v)):+.2f}")


fig, axes = plt.subplots(1, 2, figsize=(11, 3.6))
for ax, col, k in [(axes[0], "AveOccup", 10), (axes[1], "AveBedrms", 200)]:
    z = np.sort(np.log1p(X[col].to_numpy()))
    bins = np.linspace(z.min(), z.max(), 60)
    ax.hist(z[:-k], bins=bins, color=BLUE, edgecolor="white", label="残りの地区")
    ax.hist(z[-k:], bins=bins, color=RED, edgecolor="white", label=f"値の大きい {k} 地区")
    ax.set_yscale("log")
    ax.set_xlabel(f"log1p({col})")
    ax.set_ylabel("地区の数（対数目盛り）")
    ax.set_title(f"{col}: log1p 後の歪度 {stats.skew(z):+.2f} → {k} 地区を除くと {stats.skew(z[:-k]):+.2f}")
    ax.legend(fontsize=9)
plt.tight_layout()
save(fig, "skew_tail_rows.webp")


# ============================================================
# 実験 7: 右に歪んだ目的変数と、回帰の残差
# ============================================================
rng = np.random.default_rng(3)
area = rng.uniform(30, 200, 300)
price = np.exp(1.0 + 0.015 * area + rng.normal(0, 0.25, 300))  # 掛け算の揺れで右に歪む
Xa = area.reshape(-1, 1)
fits = {}
for name, t in [("生の y", price), ("log1p(y)", np.log1p(price))]:
    model = LinearRegression().fit(Xa, t)
    pred = model.predict(Xa)
    resid = t - pred
    low = pred < np.median(pred)
    fits[name] = (t, model, pred, resid)
    print(f"{name:<9} 残差の標準偏差: 予測値の小さい半分 {resid[low].std():.2f}、大きい半分 {resid[~low].std():.2f}")

fig, axes = plt.subplots(2, 2, figsize=(11, 6.6))
grid = np.linspace(30, 200, 100).reshape(-1, 1)
for row, (name, (t, model, pred, resid)) in enumerate(fits.items()):
    color = RED if row == 0 else GREEN
    ax = axes[row, 0]
    ax.scatter(area, t, alpha=0.45, color=BLUE, s=14)
    ax.plot(grid, model.predict(grid), color=color, lw=2, label="線形回帰の直線")
    ax.set_xlabel("面積")
    ax.set_ylabel(name)
    ax.set_title(f"{name} で学習")
    ax.legend(fontsize=9)
    ax = axes[row, 1]
    ax.scatter(pred, resid, alpha=0.45, color=color, s=14)
    ax.axhline(0, color=INK, ls="--", lw=1)
    ax.set_xlabel("予測値")
    ax.set_ylabel("残差")
    ax.set_title(f"{name} の残差" + ("（広がり、U 字に曲がる）" if row == 0 else "（幅がほぼ揃う）"))
plt.tight_layout()
save(fig, "skew_residual.webp")

print("done:", sorted(p.name for p in NOTE_DIR.iterdir()))
