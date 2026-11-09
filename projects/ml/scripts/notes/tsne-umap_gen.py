"""tsne-umap ノート用の図を生成するスクリプト。"""
import os
from pathlib import Path
import warnings
warnings.filterwarnings("ignore")

import matplotlib.pyplot as plt
import numpy as np
from sklearn.datasets import load_digits
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
import umap

COLOR_BLUE, COLOR_RED, COLOR_GREEN = "#7aa6c2", "#e15759", "#59a14f"

NOTE_DIR = str(Path(__file__).resolve().parents[2] / "notes" / "ml" / "tsne-umap")
os.makedirs(NOTE_DIR, exist_ok=True)


def save(name):
    plt.savefig(os.path.join(NOTE_DIR, name), bbox_inches="tight")
    plt.close()


digits = load_digits()
X = digits.data  # 64 dim
y = digits.target

# ============================================================
# Fig 1: PCA vs t-SNE vs UMAP on digits
# ============================================================
fig, axes = plt.subplots(1, 3, figsize=(16, 5))

# PCA
pca = PCA(n_components=2, random_state=0)
X_pca = pca.fit_transform(X)
ax = axes[0]
sc = ax.scatter(X_pca[:, 0], X_pca[:, 1], c=y, cmap="tab10", s=12, alpha=0.7)
ax.set_title(f"PCA (linear)\nexplained variance: {pca.explained_variance_ratio_.sum():.2f}")
ax.set_xlabel("PC1"); ax.set_ylabel("PC2")

# t-SNE
tsne = TSNE(n_components=2, perplexity=30, random_state=0, init="pca", max_iter=1000)
X_tsne = tsne.fit_transform(X)
ax = axes[1]
ax.scatter(X_tsne[:, 0], X_tsne[:, 1], c=y, cmap="tab10", s=12, alpha=0.7)
ax.set_title("t-SNE (nonlinear)\nperplexity=30")
ax.set_xlabel("t-SNE 1"); ax.set_ylabel("t-SNE 2")

# UMAP
um = umap.UMAP(n_components=2, n_neighbors=15, min_dist=0.1, random_state=0)
X_umap = um.fit_transform(X)
ax = axes[2]
ax.scatter(X_umap[:, 0], X_umap[:, 1], c=y, cmap="tab10", s=12, alpha=0.7)
ax.set_title("UMAP (nonlinear)\nn_neighbors=15, min_dist=0.1")
ax.set_xlabel("UMAP 1"); ax.set_ylabel("UMAP 2")

# Add colorbar
cb = plt.colorbar(sc, ax=axes, shrink=0.7)
cb.set_label("digit (0-9)")

plt.suptitle("3 reduction methods on 64-dim handwritten digits (n=1797)", y=1.02)
save("tsne_umap_compare.png")


# ============================================================
# Fig 2: t-SNE perplexity sensitivity
# ============================================================
fig, axes = plt.subplots(1, 4, figsize=(16, 4.5))
for ax, perp in zip(axes, [5, 30, 100, 500]):
    tsne = TSNE(n_components=2, perplexity=perp, random_state=0, init="pca", max_iter=1000)
    X_t = tsne.fit_transform(X)
    ax.scatter(X_t[:, 0], X_t[:, 1], c=y, cmap="tab10", s=10, alpha=0.7)
    ax.set_title(f"perplexity = {perp}")
    ax.set_xlabel("dim 1"); ax.set_ylabel("dim 2" if ax == axes[0] else "")
plt.suptitle("t-SNE perplexity: too small breaks clusters, too large blurs them",
             y=1.02)
plt.tight_layout()
save("tsne_perplexity_sensitivity.png")


# ============================================================
# Fig 3: UMAP n_neighbors / min_dist sensitivity
# ============================================================
fig, axes = plt.subplots(3, 3, figsize=(13, 12))
for col, n_neighbors in enumerate([5, 15, 50]):
    for row, min_dist in enumerate([0.0, 0.1, 0.5]):
        u = umap.UMAP(n_neighbors=n_neighbors, min_dist=min_dist, random_state=0)
        X_u = u.fit_transform(X)
        ax = axes[row, col]
        ax.scatter(X_u[:, 0], X_u[:, 1], c=y, cmap="tab10", s=10, alpha=0.7)
        ax.set_title(f"n_neighbors={n_neighbors}, min_dist={min_dist}",
                      fontsize=10)
        ax.set_xlabel("dim 1" if row == 2 else "")
        ax.set_ylabel("dim 2" if col == 0 else "")
plt.suptitle("UMAP: n_neighbors controls global vs local, min_dist controls cluster tightness",
             y=1.02)
plt.tight_layout()
save("umap_param_grid.png")


# ============================================================
# Fig 4: Linear vs nonlinear - swiss roll example
# ============================================================
from sklearn.datasets import make_swiss_roll

X_sr, color = make_swiss_roll(n_samples=2000, noise=0.0, random_state=0)

fig = plt.figure(figsize=(15, 4.5))

# 3D original
ax = fig.add_subplot(1, 3, 1, projection="3d")
ax.scatter(X_sr[:, 0], X_sr[:, 1], X_sr[:, 2], c=color, cmap="viridis", s=8)
ax.set_title("Original 3D swiss roll")
ax.set_xlabel("x"); ax.set_ylabel("y"); ax.set_zlabel("z")

# PCA - fails to unroll
ax = fig.add_subplot(1, 3, 2)
X_pca_sr = PCA(n_components=2).fit_transform(X_sr)
ax.scatter(X_pca_sr[:, 0], X_pca_sr[:, 1], c=color, cmap="viridis", s=8)
ax.set_title("PCA: spiral kept, roll width (y) dropped")
ax.set_xlabel("PC1"); ax.set_ylabel("PC2")

# UMAP - unrolls
ax = fig.add_subplot(1, 3, 3)
X_um_sr = umap.UMAP(n_components=2, n_neighbors=15, random_state=0).fit_transform(X_sr)
ax.scatter(X_um_sr[:, 0], X_um_sr[:, 1], c=color, cmap="viridis", s=8)
ax.set_title("UMAP: color order kept, but torn")
ax.set_xlabel("dim 1"); ax.set_ylabel("dim 2")

plt.tight_layout()
save("tsne_umap_swissroll.png")

from sklearn.manifold import trustworthiness

# シートの本当の座標（巻き方向の位置 color と幅 y）に対する近傍の保ち方
T = np.c_[color, X_sr[:, 1]]
for name, Z in [("PCA", X_pca_sr), ("UMAP", X_um_sr)]:
    print(f"{name:4s} trustworthiness={trustworthiness(T, Z, n_neighbors=10):.3f}")


# ============================================================
# 本文の数値: クラスタ間距離の順位と、予測の前処理としての UMAP
# ============================================================
from scipy.spatial.distance import pdist
from scipy.stats import spearmanr
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier

def centroids(Z):
    return np.array([Z[y == k].mean(axis=0) for k in range(10)])

d_orig = pdist(centroids(X))  # 64 次元での数字の重心間距離（45 組）
for name, Z in [("PCA", X_pca), ("t-SNE", X_tsne), ("UMAP", X_umap)]:
    rho = spearmanr(d_orig, pdist(centroids(Z))).statistic
    tw = trustworthiness(X, Z, n_neighbors=10)
    print(f"{name:5s} 重心間距離の順位相関={rho:.2f} trustworthiness={tw:.3f}")

X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.3, random_state=0, stratify=y)

def knn_acc(A, B):
    return KNeighborsClassifier(n_neighbors=5).fit(A, y_tr).score(B, y_te)

print(f"64 次元のまま : {knn_acc(X_tr, X_te):.3f}")
for k in [2, 10]:
    p = PCA(n_components=k, random_state=0).fit(X_tr)
    print(f"PCA  {k:2d} 次元 : {knn_acc(p.transform(X_tr), p.transform(X_te)):.3f}")
    r = umap.UMAP(n_components=k, random_state=0).fit(X_tr)
    print(f"UMAP {k:2d} 次元 : {knn_acc(r.embedding_, r.transform(X_te)):.3f}")

print("done:", sorted(os.listdir(NOTE_DIR)))
