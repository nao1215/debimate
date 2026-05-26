"""tsne-umap ノート用の図を生成するスクリプト。"""
import os
import warnings
warnings.filterwarnings("ignore")

import matplotlib.pyplot as plt
import numpy as np
from sklearn.datasets import load_digits
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
import umap

COLOR_BLUE, COLOR_RED, COLOR_GREEN = "#7aa6c2", "#e15759", "#59a14f"

NOTE_DIR = os.path.expanduser(
    "~/ghq/github.com/nao1215/debimate/projects/ml/notes/ml/tsne-umap"
)
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
ax.set_title("PCA (linear)\nexplained variance: 0.30")
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
ax.set_title("PCA: collapses, can't unroll")
ax.set_xlabel("PC1"); ax.set_ylabel("PC2")

# UMAP - unrolls
ax = fig.add_subplot(1, 3, 3)
X_um_sr = umap.UMAP(n_components=2, n_neighbors=15, random_state=0).fit_transform(X_sr)
ax.scatter(X_um_sr[:, 0], X_um_sr[:, 1], c=color, cmap="viridis", s=8)
ax.set_title("UMAP: unrolls the manifold")
ax.set_xlabel("dim 1"); ax.set_ylabel("dim 2")

plt.tight_layout()
save("tsne_umap_swissroll.png")


print("done:", sorted(os.listdir(NOTE_DIR)))
