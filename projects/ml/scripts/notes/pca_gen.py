"""pca ノートの実例コードと図を生成するスクリプト。

本文の「Python での実例」のコードと同じ処理を行い、図を Page Bundle に保存する。
実行: cd projects/ml && uv run python scripts/notes/pca_gen.py
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

NOTE_DIR = Path(__file__).resolve().parents[2] / "notes" / "ml" / "pca"
plt.rcParams["svg.hashsalt"] = "pca"  # 再生成で SVG の差分が出ないようにする

# 分かりやすい人工データ（x2 は x1 の 0.3 倍に小さなノイズを足しただけ）
rng = np.random.RandomState(0)
x = rng.randn(200)
y = 0.3 * x + 0.1 * rng.randn(200)
X = np.column_stack((x, y))

# 平均中心化 → 共分散行列 → 固有値分解
X_centered = X - X.mean(axis=0)
cov = np.cov(X_centered, rowvar=False)
eigvals, eigvecs = np.linalg.eigh(cov)

# 固有値の大きい順に並べ、向き（符号）は任意なので x1 成分を正に揃える
idx = np.argsort(eigvals)[::-1]
eigvals, eigvecs = eigvals[idx], eigvecs[:, idx]
eigvecs = eigvecs * np.sign(eigvecs[0])

print("固有値（各主成分の分散）:", eigvals.round(4))
print("寄与率:", (eigvals / eigvals.sum()).round(4))
print("PC1 の向き:", eigvecs[:, 0].round(3))

# 回転（PCA 変換）と、PC1 だけ残して元の空間へ戻した時の誤差
X_pca = X_centered @ eigvecs
X_back = X_pca[:, :1] @ eigvecs[:, :1].T
print("PCA 後の共分散:\n", np.cov(X_pca, rowvar=False).round(4) + 0.0)
print("PC2 を捨てた時の平均二乗誤差:", np.mean(np.sum((X_centered - X_back) ** 2, axis=1)).round(4))

# scikit-learn でも同じ寄与率になる
print("sklearn の寄与率:", PCA().fit(X).explained_variance_ratio_.round(4))

# x2 だけ単位を変えて 100 倍にすると、標準化の有無で PC1 が変わる
X_cm = np.column_stack((x, y * 100))
raw = PCA().fit(X_cm)
std = PCA().fit(StandardScaler().fit_transform(X_cm))
print("100 倍・標準化なし PC1:", np.abs(raw.components_[0]).round(3),
      "寄与率", raw.explained_variance_ratio_.round(4))
print("100 倍・標準化あり PC1:", np.abs(std.components_[0]).round(3),
      "寄与率", std.explained_variance_ratio_.round(4))

# 図：左が元データと主成分軸、右が主成分軸へ回転した後
POINT = "#7aa6c2"
INK = "#333333"
fig, axes = plt.subplots(1, 2, figsize=(10, 4))
ax = axes[0]
ax.scatter(X[:, 0], X[:, 1], s=12, alpha=0.5, color=POINT)
origin = X.mean(axis=0)
for i, name in enumerate(["PC1", "PC2"]):
    vec = eigvecs[:, i] * np.sqrt(eigvals[i]) * 2
    ax.annotate("", xy=origin + vec, xytext=origin,
                arrowprops=dict(arrowstyle="->", color=INK, lw=1.5))
    ax.text(*(origin + vec * 1.1 + [0.05, 0.05]), name, color=INK, fontsize=9)
ax.set_title("Original data (x1, x2) with principal axes", fontsize=10)
ax.set_xlabel("x1")
ax.set_ylabel("x2")
ax.axis("equal")

ax = axes[1]
ax.scatter(X_pca[:, 0], X_pca[:, 1], s=12, alpha=0.5, color=POINT)
ax.axhline(0, color=INK, lw=0.8)
ax.axvline(0, color=INK, lw=0.8)
ax.set_title("After PCA (rotated to PC1, PC2)", fontsize=10)
ax.set_xlabel("PC1")
ax.set_ylabel("PC2")
ax.axis("equal")

plt.tight_layout()
plt.savefig(NOTE_DIR / "pca_rotation.svg", bbox_inches="tight", metadata={"Date": None})
# Remove trailing whitespace so `git diff --check` passes.
_svg_path = Path(NOTE_DIR / "pca_rotation.svg")
_svg_path.write_text("\n".join(l.rstrip() for l in _svg_path.read_text().splitlines()) + "\n")
