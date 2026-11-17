"""correlation ノートの実験と図を生成するスクリプト。

本文に載せた実験（diabetes の積の内訳、曲がった関係、外れ値 1 点、2 列の掛け算、
相関行列、乱数どうしの相関、4 つの相関係数の比較、ξ の仕組み）を同じ順に実行し、
出力を標準出力に、図を Page Bundle に WebP で保存する。
実行: cd projects/ml && .venv/bin/python scripts/notes/correlation_gen.py
確認した版: scikit-learn 1.9.1、NumPy 2.5.4、SciPy 1.18.1、matplotlib 3.11.2
"""
from io import BytesIO
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image
from scipy import stats
from sklearn.datasets import load_diabetes
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import cross_val_score

NOTE_DIR = Path(__file__).resolve().parents[2] / "notes" / "math" / "correlation"
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10,
                     "axes.spines.top": False, "axes.spines.right": False})
BLUE, RED, GREEN, INK, GRAY = "#7aa6c2", "#e15759", "#59a14f", "#333333", "#999999"


def save(fig, name):
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight", facecolor="#ffffff")
    plt.close(fig)
    buf.seek(0)
    Image.open(buf).convert("RGB").save(NOTE_DIR / name, "WEBP", quality=90, method=6)


def zscore(a):
    return (a - a.mean()) / a.std()


# ============================================================
# 実験 1: 相関係数は z の積の平均（diabetes の bmi と 1 年後の進行度）
# ============================================================
d = load_diabetes(scaled=False)
bmi, prog = d.data[:, 2], d.target            # 442 人の BMI と、1 年後の病気の進行度
zx, zy = zscore(bmi), zscore(prog)
prod = zx * zy                                 # 点ごとの積
print("np.corrcoef:", round(np.corrcoef(bmi, prog)[0, 1], 3))
print("積の平均   :", round(prod.mean(), 3))
print(f"積が正の点: {(prod > 0).sum()} / {len(prod)}  積の合計 {prod[prod > 0].sum():.1f}")
print(f"積が負の点: {(prod < 0).sum()} / {len(prod)}  積の合計 {prod[prod < 0].sum():.1f}")
print("r の 2 乗    :", round(np.corrcoef(bmi, prog)[0, 1] ** 2, 3))

fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.2), gridspec_kw={"width_ratios": [1.25, 1]})
ax = axes[0]
pos = prod > 0
ax.scatter(zx[pos], zy[pos], s=12, color=RED, alpha=0.6, label="積が正（右上と左下）")
ax.scatter(zx[~pos], zy[~pos], s=12, color=BLUE, alpha=0.7, label="積が負（左上と右下）")
ax.axhline(0, color=GRAY, lw=0.8)
ax.axvline(0, color=GRAY, lw=0.8)
ax.set_xlabel("BMI の z（平均からのずれ ÷ 標準偏差）")
ax.set_ylabel("進行度の z")
ax.set_title(f"diabetes の 442 人（r = {prod.mean():.3f}）", fontsize=10)
ax.legend(loc="upper left", fontsize=9, frameon=False)
ax = axes[1]
vals = [prod[pos].sum(), prod[~pos].sum(), prod.sum()]
bars = ax.bar(["積が正の点", "積が負の点", "合計"], vals, color=[RED, BLUE, INK], width=0.6)
for b, v in zip(bars, vals):
    ax.text(b.get_x() + b.get_width() / 2, v + (8 if v > 0 else -8), f"{v:.1f}",
            ha="center", va="bottom" if v > 0 else "top", fontsize=9)
ax.axhline(0, color=GRAY, lw=0.8)
ax.set_ylim(-80, 340)
ax.set_title(f"積の合計（÷ 442 で r = {prod.mean():.3f}）", fontsize=10)
fig.tight_layout()
save(fig, "corr_products.webp")


# ============================================================
# 実験 2: 曲がった関係（y = x^2）
# ============================================================
rng = np.random.default_rng(0)
x = rng.uniform(-1, 1, 500)
y = x**2 + rng.normal(0, 0.05, 500)            # x で y がほぼ決まる
p = zscore(x) * zscore(y)
print("y = x^2 の r:", round(np.corrcoef(x, y)[0, 1], 3))
print(f"x < 0 の点の積の合計 {p[x < 0].sum():.1f}、x > 0 の点の積の合計 {p[x > 0].sum():.1f}")
x02 = rng.uniform(0, 2, 500)                   # 同じ y = x² を 0〜2 の範囲で作る
print("x を 0〜2 にした y = x^2 の r:", round(np.corrcoef(x02, x02**2 + rng.normal(0, 0.05, 500))[0, 1], 3))
curve = (x, y)

fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.0), gridspec_kw={"width_ratios": [1.25, 1]})
ax = axes[0]
zx2, zy2 = zscore(x), zscore(y)
ax.scatter(zx2[p > 0], zy2[p > 0], s=10, color=RED, alpha=0.6, label="積が正")
ax.scatter(zx2[p <= 0], zy2[p <= 0], s=10, color=BLUE, alpha=0.7, label="積が負")
ax.axhline(0, color=GRAY, lw=0.8)
ax.axvline(0, color=GRAY, lw=0.8)
ax.set_xlabel("x の z")
ax.set_ylabel("y の z")
ax.set_title(f"y = x² にノイズを足した 500 点（r = {np.corrcoef(x, y)[0, 1]:.3f}）", fontsize=10)
ax.legend(loc="upper center", fontsize=9, frameon=False)
ax = axes[1]
vals = [p[x < 0].sum(), p[x > 0].sum(), p.sum()]
bars = ax.bar(["x < 0 の点", "x > 0 の点", "合計"], vals, color=[BLUE, RED, INK], width=0.6)
for b, v in zip(bars, vals):
    ax.text(b.get_x() + b.get_width() / 2, v + (4 if v > 0 else -4), f"{v:.1f}",
            ha="center", va="bottom" if v > 0 else "top", fontsize=9)
ax.axhline(0, color=GRAY, lw=0.8)
ax.set_ylim(-140, 180)
ax.set_title("左半分と右半分で積の合計が打ち消し合う", fontsize=10)
fig.tight_layout()
save(fig, "corr_curve.webp")


# ============================================================
# 実験 3: 外れ値 1 点で符号が変わる
# ============================================================
rng = np.random.default_rng(1)
n = 1000
a = rng.normal(size=n)
b = 0.4 * a + np.sqrt(1 - 0.4**2) * rng.normal(size=n)   # r が 0.4 ほどの 1000 点
print(f"1000 点だけ: Pearson {np.corrcoef(a, b)[0, 1]:.3f}  Spearman {stats.spearmanr(a, b).statistic:.3f}")
for k in [10, 20, 30]:
    xa, ya = np.append(a, k), np.append(b, -k)            # (k, -k) に 1 点だけ足す
    p = zscore(xa) * zscore(ya)
    print(f"(+{k}, -{k}) を足す: Pearson {np.corrcoef(xa, ya)[0, 1]:+.3f}  "
          f"Spearman {stats.spearmanr(xa, ya).statistic:+.3f}  "
          f"足した 1 点の積 {p[-1]:.1f}  残り 1000 点の積の合計 {p[:-1].sum():.1f}")
outlier = (np.append(a, 30), np.append(b, -30))

ks = np.arange(0, 51)
pear, spear, kend = [], [], []
for k in ks:
    xa, ya = np.append(a, k), np.append(b, -k)
    pear.append(np.corrcoef(xa, ya)[0, 1])
    spear.append(stats.spearmanr(xa, ya).statistic)
    kend.append(stats.kendalltau(xa, ya).statistic)
fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.0))
ax = axes[0]
ax.scatter(a, b, s=6, color=BLUE, alpha=0.5, label="元の 1000 点")
ax.scatter([30], [-30], s=40, color=RED, label="足した 1 点 (30, -30)")
ax.set_xlabel("x")
ax.set_ylabel("y")
ax.set_title("1000 点に 1 点を足す", fontsize=10)
ax.legend(loc="lower left", fontsize=9, frameon=False)
ax = axes[1]
ax.plot(ks, pear, color=RED, lw=2, label="Pearson")
ax.plot(ks, spear, color=BLUE, lw=2, label="Spearman")
ax.plot(ks, kend, color=GREEN, lw=2, label="Kendall")
ax.axhline(0, color=GRAY, lw=0.8)
ax.axvline(30, color=GRAY, lw=0.8, ls=":")
ax.set_xlabel("足した 1 点の位置 k（点は (k, -k)）")
ax.set_ylabel("相関係数")
ax.set_ylim(-0.6, 0.6)
ax.set_title("1 点を遠くへ動かした時の相関係数", fontsize=10)
ax.legend(loc="lower left", fontsize=9, frameon=False)
fig.tight_layout()
save(fig, "corr_outlier.webp")


# ============================================================
# 実験 4: 1 列ずつでは相関 0 でも、2 列そろうと予測できる
# ============================================================
rng = np.random.default_rng(2)
x1 = rng.uniform(-1, 1, 2000)
x2 = rng.uniform(-1, 1, 2000)
t = x1 * x2 + rng.normal(0, 0.05, 2000)        # 目的変数は 2 列の掛け算
X = np.column_stack([x1, x2])
print(f"r(x1, t) = {np.corrcoef(x1, t)[0, 1]:.3f}  r(x2, t) = {np.corrcoef(x2, t)[0, 1]:.3f}")
for name, model in [("LinearRegression", LinearRegression()),
                    ("HistGradientBoosting", HistGradientBoostingRegressor(random_state=0))]:
    r2 = cross_val_score(model, X, t, cv=5, scoring="r2").mean()
    print(f"{name:<20} 5 分割交差検証の R² {r2:.3f}")
inter = (x1, x2, t)

# 相関行列: diabetes の血液検査の列と進行度
df = pd.DataFrame(d.data, columns=d.feature_names)
df["target"] = d.target
print(df[["bmi", "s1", "s2", "s3", "s4", "s5", "target"]].corr().round(2))

fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.0))
ax = axes[0]
ax.scatter(x1, t, s=5, color=BLUE, alpha=0.5)
ax.set_xlabel("x1")
ax.set_ylabel("目的変数 t")
ax.set_title(f"x1 と t だけを見る（r = {np.corrcoef(x1, t)[0, 1]:.3f}）", fontsize=10)
ax = axes[1]
sc = ax.scatter(x1, x2, c=t, s=6, cmap="RdBu_r", vmin=-1, vmax=1)
ax.set_xlabel("x1")
ax.set_ylabel("x2")
ax.set_aspect("equal")
ax.set_title("x1 と x2 を一緒に見る（色が t）", fontsize=10)
cb = fig.colorbar(sc, ax=ax, fraction=0.046)
cb.set_label("t")
fig.tight_layout()
save(fig, "corr_interaction.webp")


# ============================================================
# 実験 5: 乱数どうしの相関
# ============================================================
rng = np.random.default_rng(3)
hist = {}
for m in [10, 30, 100, 1000]:
    rs = np.array([np.corrcoef(rng.normal(size=m), rng.normal(size=m))[0, 1] for _ in range(10000)])
    hist[m] = rs
    print(f"{m:>4} 行: |r| >= 0.5 の割合 {np.mean(np.abs(rs) >= 0.5):6.2%}  "
          f"|r| の 95% 点 {np.percentile(np.abs(rs), 95):.2f}")
Z = rng.normal(size=(20, 1000))                # 20 行 × 1000 列の乱数
target = rng.normal(size=20)                   # 目的変数も乱数
rcol = np.array([np.corrcoef(Z[:, j], target)[0, 1] for j in range(1000)])
print(f"20 行 × 1000 列: |r| の最大 {np.abs(rcol).max():.3f}、|r| >= 0.5 の列 {np.sum(np.abs(rcol) >= 0.5)} 本")
best = np.argmax(np.abs(rcol))
noise = (Z[:, best], target, rcol[best])

fig, ax = plt.subplots(figsize=(7.5, 3.8))
bins = np.linspace(-1, 1, 81)
for m, c in [(10, RED), (30, GREEN), (100, BLUE), (1000, INK)]:
    ax.hist(hist[m], bins=bins, histtype="step", lw=1.8, color=c, density=True, label=f"{m} 行")
ax.set_xlabel("無関係な乱数 2 列の相関係数 r（10000 回）")
ax.set_ylabel("密度")
ax.set_xlim(-1, 1)
ax.set_title("行が少ないほど、無関係でも大きな r が出る", fontsize=10)
ax.legend(fontsize=9, frameon=False)
fig.tight_layout()
save(fig, "corr_noise.webp")


# ============================================================
# 実験 6: 4 つの相関係数を同じデータで比べる
# ============================================================
def four(x, y):
    return (np.corrcoef(x, y)[0, 1], stats.spearmanr(x, y).statistic,
            stats.kendalltau(x, y).statistic, stats.chatterjeexi(x, y).statistic)


rng = np.random.default_rng(4)
xl = rng.normal(size=500)
cases = {
    "直線にノイズ": (xl, xl + 0.5 * rng.normal(size=500)),
    "y = exp(x)": (xu := rng.uniform(0, 10, 500), np.exp(xu)),
    "y = x²": curve,
    "外れ値 1 点（k = 30）": outlier,
    "x1 と t": (inter[0], inter[2]),
}
print(f"{'':<12}{'Pearson':>9}{'Spearman':>10}{'Kendall':>9}{'ξ':>8}")
for name, (x, y) in cases.items():
    print(f"{name:<12}" + "".join(f"{v:>9.3f}" for v in four(x, y)))
xs = rng.uniform(-1, 1, 500)
print(f"ξ(x, x²) = {stats.chatterjeexi(xs, xs**2).statistic:.3f}  "
      f"ξ(x², x) = {stats.chatterjeexi(xs**2, xs).statistic:.3f}")


# ============================================================
# 図: ξ の仕組み（x の順に並べた y の順位）
# ============================================================
rng = np.random.default_rng(5)
xs = np.sort(rng.uniform(-1, 1, 60))
fig, axes = plt.subplots(1, 2, figsize=(10.5, 3.8), sharey=True)
for ax, ys, title in [(axes[0], xs**2 + rng.normal(0, 0.02, 60), "y = x²（x で y が決まる）"),
                      (axes[1], rng.normal(size=60), "y は x と無関係な乱数")]:
    rk = stats.rankdata(ys)
    xi = stats.chatterjeexi(xs, ys).statistic
    ax.plot(np.arange(60), rk, color=GRAY, lw=1)
    ax.scatter(np.arange(60), rk, s=14, color=RED if ax is axes[0] else BLUE, zorder=3)
    ax.set_xlabel("x の小さい順に並べた番号")
    ax.set_title(f"{title}　ξ = {xi:.2f}", fontsize=10)
axes[0].set_ylabel("y の順位（1〜60）")
fig.tight_layout()
save(fig, "corr_xi.webp")


# ============================================================
# 表紙: 4 つの思い込みの反例
# ============================================================
fig, axes = plt.subplots(1, 4, figsize=(13, 3.5))
ax = axes[0]
ax.scatter(*curve, s=4, color=BLUE, alpha=0.6)
ax.set_title(f"y = x²　r = {np.corrcoef(*curve)[0, 1]:.2f}", fontsize=11)
ax = axes[1]
ax.scatter(a, b, s=3, color=BLUE, alpha=0.5)
ax.scatter([30], [-30], s=30, color=RED)
ax.set_title(f"1 点を足すと　r = {np.corrcoef(a, b)[0, 1]:.2f} → {np.corrcoef(*outlier)[0, 1]:.2f}",
             fontsize=11)
ax = axes[2]
ax.scatter(inter[0], inter[2], s=3, color=BLUE, alpha=0.5)
ax.set_title(f"x1 と t　r = {np.corrcoef(inter[0], inter[2])[0, 1]:.2f}", fontsize=11)
ax.text(0.5, -0.2, "x2 と合わせると R² 0.97", transform=ax.transAxes, ha="center", fontsize=10,
        color=RED)
ax = axes[3]
ax.scatter(noise[0], noise[1], s=18, color=BLUE)
ax.set_title(f"乱数 20 行　r = {noise[2]:.2f}", fontsize=11)
ax.text(0.5, -0.2, "1000 列の中で最大の列", transform=ax.transAxes, ha="center", fontsize=10,
        color=RED)
for ax in axes:
    ax.set_xticks([])
    ax.set_yticks([])
fig.tight_layout()
save(fig, "corr_cover.webp")
