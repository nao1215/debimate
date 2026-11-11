"""pca ノートの実験と図を生成するスクリプト。

本文に載せた 4 つの実験（2 次元の回転、wine の単位、wine の精度と次元数、分散の小さい軸）を
同じ順に実行し、出力を標準出力に、図を Page Bundle に WebP で保存する。
実行: cd projects/ml && .venv/bin/python scripts/notes/pca_gen.py
確認した版: scikit-learn 1.9.1、NumPy 2.5.4、matplotlib 3.11.2
"""
from io import BytesIO
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from sklearn.datasets import load_wine
from sklearn.decomposition import PCA
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

NOTE_DIR = Path(__file__).resolve().parents[2] / "notes" / "ml" / "pca"
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10,
                     "axes.spines.top": False, "axes.spines.right": False})
BLUE, RED, GREEN, INK, GRAY = "#7aa6c2", "#e15759", "#59a14f", "#333333", "#999999"
CLASS_COLORS = [BLUE, RED, GREEN]


def save(fig, name):
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight", facecolor="#ffffff")
    plt.close(fig)
    buf.seek(0)
    Image.open(buf).convert("RGB").save(NOTE_DIR / name, "WEBP", quality=90, method=6)


# ---- 実験 1: 2 次元のデータで、主成分と寄与率を固有値分解から求める ----
rng = np.random.RandomState(0)
x1 = rng.randn(200)
x2 = 0.3 * x1 + 0.1 * rng.randn(200)  # x2 は x1 の 0.3 倍に小さなノイズを足しただけ
X = np.column_stack((x1, x2))

X_centered = X - X.mean(axis=0)
eigvals, eigvecs = np.linalg.eigh(np.cov(X_centered, rowvar=False))
idx = np.argsort(eigvals)[::-1]  # 固有値の大きい順に並べる
eigvals, eigvecs = eigvals[idx], eigvecs[:, idx]
eigvecs = eigvecs * np.sign(eigvecs[0])  # 向き（符号）は任意なので x1 の成分を正に揃える

X_pca = X_centered @ eigvecs  # 主成分の座標へ回転する
X_back = X_pca[:, :1] @ eigvecs[:, :1].T  # PC1 だけ残して元の空間へ戻す
print("固有値（各主成分の分散）:", eigvals.round(4))
print("寄与率:", (eigvals / eigvals.sum()).round(4))
print("PC1 の向き:", eigvecs[:, 0].round(3))
print("PC2 を捨てた時の平均二乗誤差:", np.mean(np.sum((X_centered - X_back) ** 2, axis=1)).round(4))
# + 0.0 は、丸めた結果の -0.0 を 0.0 と表示するため
print("回転した後の PC1 と PC2 の相関:", np.corrcoef(X_pca[:, 0], X_pca[:, 1])[0, 1].round(4) + 0.0)

fig, axes = plt.subplots(1, 2, figsize=(9, 3.6))
ax = axes[0]
ax.scatter(X[:, 0], X[:, 1], s=10, alpha=0.5, color=BLUE)
origin = X.mean(axis=0)
for i, name in enumerate(["PC1", "PC2"]):
    vec = eigvecs[:, i] * np.sqrt(eigvals[i]) * 2
    ax.annotate("", xy=origin + vec, xytext=origin, arrowprops=dict(arrowstyle="->", color=INK, lw=1.5))
    offset = [0.05, 0.08] if i == 0 else [0.15, -0.3]
    ax.text(*(origin + vec * 1.15 + offset), name, color=INK, fontsize=9)
ax.set_title("元のデータと主成分の向き", fontsize=10)
ax.set_xlabel("x1")
ax.set_ylabel("x2")
ax.axis("equal")
ax = axes[1]
ax.scatter(X_pca[:, 0], X_pca[:, 1], s=10, alpha=0.5, color=BLUE)
ax.axhline(0, color=GRAY, lw=0.8)
ax.axvline(0, color=GRAY, lw=0.8)
ax.set_title("PC1・PC2 の座標へ回転した後", fontsize=10)
ax.set_xlabel("PC1（寄与率 0.993）")
ax.set_ylabel("PC2（寄与率 0.007）")
ax.axis("equal")
fig.tight_layout()
save(fig, "pca_rotation.webp")

# ---- 実験 2: wine の 13 列に PCA を掛け、PC1 がどの列で決まるかを見る ----
wine = load_wine()
Xw, yw = wine.data, wine.target
names = wine.feature_names


def pc1(data):
    p = PCA().fit(data)
    # 向きは符号を反転しても同じ軸なので、重みは絶対値で比べる
    return p.explained_variance_ratio_[0], np.abs(p.components_[0])


Xw_div = Xw.copy()
Xw_div[:, names.index("proline")] /= 1000  # proline の列だけ 1000 で割る
cases = [("そのまま", Xw), ("proline だけ 1000 で割る", Xw_div),
         ("標準化してから", StandardScaler().fit_transform(Xw))]
for label, data in cases:
    ratio, w = pc1(data)
    top = np.argsort(w)[::-1][:2]
    print(f"{label}: PC1 の寄与率 {ratio:.4f}、重みの大きい列", [(names[i], round(float(w[i]), 3)) for i in top])
print("列ごとの標準偏差:", {n: float(v) for n, v in zip(names, Xw.std(axis=0).round(2))})
pc2_raw = np.abs(PCA().fit(Xw).components_[1])
print("そのまま: PC2 の重みの大きい列", names[pc2_raw.argmax()], round(float(pc2_raw.max()), 3))

# 表紙: 3 通りの PC1 の重み（絶対値）をマス目に並べる
short = ["alcohol", "malic_acid", "ash", "alcalinity", "magnesium", "total_phenols", "flavanoids",
         "nonflav_phenols", "proanthocyanins", "color_intensity", "hue", "od280/od315", "proline"]
mat = np.array([pc1(d)[1] for _, d in cases])
fig, ax = plt.subplots(figsize=(9, 3.2))
ax.imshow(mat, cmap="Reds", vmin=0, vmax=1, aspect="auto")
for r in range(3):
    for c in range(13):
        v = mat[r, c]
        ax.text(c, r, f"{v:.2f}", ha="center", va="center", fontsize=7.5,
                color="#ffffff" if v > 0.6 else INK)
ax.set_xticks(range(13))
ax.set_xticklabels(short, rotation=45, ha="right", fontsize=8)
ax.set_yticks(range(3))
ax.set_yticklabels([c[0].replace("だけ ", "だけ\n") for c in cases], fontsize=9)
for r, (_, d) in enumerate(cases):
    ax.text(13.0, r, f"寄与率 {pc1(d)[0] * 100:.1f}%", va="center", fontsize=9)
for s in ax.spines.values():
    s.set_visible(False)
ax.set_title("wine の第 1 主成分（PC1）が各列に掛ける重みの大きさ", fontsize=10, loc="left")
fig.tight_layout()
save(fig, "pca_cover.webp")

# 列ごとの標準偏差（対数軸）
std = Xw.std(axis=0)
order = np.argsort(std)
fig, ax = plt.subplots(figsize=(7, 3.8))
colors = [RED if names[i] == "proline" else (GREEN if names[i] == "magnesium" else BLUE) for i in order]
ax.barh(range(13), std[order], color=colors)
ax.set_yticks(range(13))
ax.set_yticklabels([short[i] for i in order], fontsize=8)
ax.set_xscale("log")
ax.set_xlabel("標準偏差（対数軸）")
for k, i in enumerate(order):
    ax.text(std[i] * 1.1, k, f"{std[i]:.2f}", va="center", fontsize=7.5)
p_div = std[names.index("proline")] / 1000
ax.axvline(p_div, color=RED, lw=1, ls="--")
ax.text(p_div * 1.1, -1.1, f"1000 で割った proline（{p_div:.2f}）", color=RED, fontsize=8, va="center")
ax.set_ylim(-1.7, 12.6)
ax.set_xlim(0.08, 1500)
ax.set_title("wine の列ごとの標準偏差", fontsize=10, loc="left")
fig.tight_layout()
save(fig, "pca_wine_std.webp")

# ---- 実験 3: 標準化の有無と、残す主成分の数で、分類の精度がどう変わるか ----
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=0)
ks = list(range(1, 14))
acc_raw, acc_std = [], []
for k in ks:
    raw = make_pipeline(PCA(n_components=k), LogisticRegression(max_iter=5000))
    scaled = make_pipeline(StandardScaler(), PCA(n_components=k), LogisticRegression(max_iter=5000))
    acc_raw.append(cross_val_score(raw, Xw, yw, cv=cv).mean())
    acc_std.append(cross_val_score(scaled, Xw, yw, cv=cv).mean())
for k in [1, 2, 3, 5, 10, 13]:
    print(f"主成分 {k:2d} 個: 標準化なし {acc_raw[k - 1]:.3f}、標準化あり {acc_std[k - 1]:.3f}")
for col in ["proline", "magnesium"]:  # 1 列だけで当てた時の精度
    one = make_pipeline(StandardScaler(), LogisticRegression(max_iter=5000))
    print(f"{col} だけ: {cross_val_score(one, Xw[:, [names.index(col)]], yw, cv=cv).mean():.3f}")
cum = np.cumsum(PCA().fit(StandardScaler().fit_transform(Xw)).explained_variance_ratio_)
print("標準化ありの累積寄与率:", cum.round(3))
print("PCA(0.95) が選んだ数:", PCA(n_components=0.95).fit(StandardScaler().fit_transform(Xw)).n_components_)

# 2 次元の散布図（標準化なし・あり）
fig, axes = plt.subplots(1, 2, figsize=(9, 3.8))
for ax, (title, data, acc) in zip(axes, [("標準化なし", Xw, acc_raw[1]),
                                         ("標準化あり", StandardScaler().fit_transform(Xw), acc_std[1])]):
    Z = PCA(n_components=2).fit_transform(data)
    for c in range(3):
        ax.scatter(Z[yw == c, 0], Z[yw == c, 1], s=12, alpha=0.7, color=CLASS_COLORS[c], label=f"品種 {c}")
    ax.set_title(f"{title}（2 個で分類の精度 {acc * 100:.1f}%）", fontsize=10)
    ax.set_xlabel("PC1")
    ax.set_ylabel("PC2")
for ax in axes:
    ax.legend(fontsize=8, frameon=False)
fig.tight_layout()
save(fig, "pca_wine_scatter.webp")

# 累積寄与率と精度
fig, ax = plt.subplots(figsize=(7, 3.6))
ax.plot(ks, cum, marker="o", color=GRAY, label="累積寄与率（標準化あり）")
ax.plot(ks, acc_std, marker="o", color=BLUE, label="分類の精度（標準化あり）")
ax.plot(ks, acc_raw, marker="o", color=RED, label="分類の精度（標準化なし）")
ax.axhline(0.95, color=GRAY, lw=0.8, ls="--")
ax.text(0.6, 0.955, "95%", va="bottom", fontsize=8, color=GRAY)
ax.annotate(f"2 個で {acc_std[1] * 100:.1f}%（累積寄与率 {cum[1] * 100:.1f}%）", xy=(2, acc_std[1] + 0.01),
            xytext=(2.4, 1.07), fontsize=8, arrowprops=dict(arrowstyle="->", color=INK, lw=0.8))
ax.set_xticks(ks)
ax.set_xlabel("残す主成分の数")
ax.set_ylim(0.3, 1.12)
ax.set_xlim(0.5, 13.5)
ax.legend(fontsize=8, frameon=False, loc="lower right")
fig.tight_layout()
save(fig, "pca_components.webp")

# ---- 実験 4: クラスの違いが分散の小さい軸にある時 ----
rng = np.random.RandomState(0)
n = 400
y = rng.randint(0, 2, n)
a = rng.randn(n) * 3  # 分散が大きいが、クラスとは関係ない列
b = rng.randn(n) * 0.3 + np.where(y == 1, 0.6, -0.6)  # 分散は小さいが、クラスで値がずれる列
Xs = np.column_stack((a, b))
ps = PCA().fit(Xs)
acc_pca1 = cross_val_score(make_pipeline(PCA(n_components=1), LogisticRegression()), Xs, y, cv=cv).mean()
acc_all = cross_val_score(LogisticRegression(), Xs, y, cv=cv).mean()
acc_lda = cross_val_score(make_pipeline(LinearDiscriminantAnalysis(n_components=1), LogisticRegression()),
                          Xs, y, cv=cv).mean()
print("寄与率:", ps.explained_variance_ratio_.round(3), "PC1 の向き:", np.abs(ps.components_[0]).round(2))
print(f"PC1 だけ {acc_pca1:.3f}、2 列のまま {acc_all:.3f}、LDA で 1 軸 {acc_lda:.3f}")

fig, ax = plt.subplots(figsize=(9, 3.2))
for c, col in enumerate([BLUE, RED]):
    ax.scatter(Xs[y == c, 0], Xs[y == c, 1], s=10, alpha=0.6, color=col, label=f"クラス {c}")
ax.annotate("", xy=(8, 0), xytext=(-8, 0), arrowprops=dict(arrowstyle="->", color=INK, lw=1.5))
ax.text(8.3, -0.6, f"PC1（寄与率 {ps.explained_variance_ratio_[0] * 100:.1f}%）\nPC1 だけで精度 {acc_pca1 * 100:.1f}%",
        fontsize=8.5, color=INK)
ax.set_xlabel("a（分散が大きい列）")
ax.set_ylabel("b（分散が小さい列）")
ax.set_xlim(-11, 15)
ax.set_ylim(-2, 2)
ax.set_aspect("equal")  # 縦横の縮尺を揃え、a の広がりが b の 10 倍に見えるようにする
ax.legend(fontsize=8, frameon=False, loc="upper right", ncol=2)
ax.set_title("クラスの違いが分散の小さい列にある人工データ（縦横の縮尺は同じ）", fontsize=10, loc="left")
fig.tight_layout()
save(fig, "pca_low_variance.webp")
