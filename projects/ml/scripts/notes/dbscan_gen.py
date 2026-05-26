"""dbscan ノート用の図を生成するスクリプト。"""
import os
import matplotlib.pyplot as plt
import numpy as np
from sklearn.cluster import DBSCAN, KMeans
from sklearn.datasets import make_moons, make_blobs

COLOR_BLUE, COLOR_RED, COLOR_GREEN, COLOR_ORANGE = "#7aa6c2", "#e15759", "#59a14f", "#f28e2b"

NOTE_DIR = os.path.expanduser(
    "~/ghq/github.com/nao1215/debimate/projects/ml/notes/ml/dbscan"
)
os.makedirs(NOTE_DIR, exist_ok=True)


def save(name):
    plt.savefig(os.path.join(NOTE_DIR, name), bbox_inches="tight")
    plt.close()


# ============================================================
# Fig 1: DBSCAN vs k-means on non-convex data
# ============================================================
X_moons, _ = make_moons(n_samples=400, noise=0.08, random_state=0)

fig, axes = plt.subplots(1, 2, figsize=(13, 5))

# k-means (fails)
km = KMeans(n_clusters=2, random_state=0).fit(X_moons)
ax = axes[0]
ax.scatter(X_moons[:, 0], X_moons[:, 1], c=km.labels_, cmap="coolwarm", s=25, edgecolor="white")
ax.set_title("k-means: forces convex blobs onto non-convex data")
ax.set_xlabel("x1"); ax.set_ylabel("x2")
ax.grid(True, alpha=0.25)

# DBSCAN
db = DBSCAN(eps=0.2, min_samples=5).fit(X_moons)
ax = axes[1]
# Color noise (-1) gray, clusters by label
mask_noise = db.labels_ == -1
ax.scatter(X_moons[~mask_noise, 0], X_moons[~mask_noise, 1],
            c=db.labels_[~mask_noise], cmap="coolwarm", s=25, edgecolor="white")
ax.scatter(X_moons[mask_noise, 0], X_moons[mask_noise, 1],
            color="gray", marker="x", s=40, label=f"noise (n={mask_noise.sum()})")
ax.set_title("DBSCAN: traces the density, two crescents recovered")
ax.set_xlabel("x1"); ax.set_ylabel("x2")
ax.legend(loc="upper right", fontsize=9)
ax.grid(True, alpha=0.25)

plt.tight_layout()
save("dbscan_vs_kmeans.svg")


# ============================================================
# Fig 2: DBSCAN core/border/noise concept
# ============================================================
rng = np.random.default_rng(0)
# Generate 1 cluster of 20 points + a few noise points
cluster = rng.normal([0, 0], 0.4, (30, 2))
noise_pts = np.array([[2.5, 1.5], [-2.5, 2.0], [2.0, -2.0]])
X = np.vstack([cluster, noise_pts])

eps = 0.6
min_samples = 5

# Compute neighborhood counts manually
from sklearn.neighbors import NearestNeighbors
nbrs = NearestNeighbors(radius=eps).fit(X)
distances, indices = nbrs.radius_neighbors(X)
n_neighbors = np.array([len(i) - 1 for i in indices])  # exclude self

# Classify: core if n_neighbors >= min_samples
# Border: not core but in eps of a core point
# Noise: neither
db = DBSCAN(eps=eps, min_samples=min_samples).fit(X)
core_mask = np.zeros(len(X), dtype=bool)
core_mask[db.core_sample_indices_] = True
noise_mask = db.labels_ == -1
border_mask = (~core_mask) & (~noise_mask)

plt.figure(figsize=(8, 6))
plt.scatter(X[core_mask, 0], X[core_mask, 1], color=COLOR_RED, s=120,
            edgecolor="black", linewidth=1, label=f"core ({core_mask.sum()})")
plt.scatter(X[border_mask, 0], X[border_mask, 1], color=COLOR_ORANGE, s=70,
            edgecolor="black", linewidth=0.8, label=f"border ({border_mask.sum()})")
plt.scatter(X[noise_mask, 0], X[noise_mask, 1], color="gray", marker="x", s=80,
            label=f"noise ({noise_mask.sum()})")

# Draw eps-balls around core points
from matplotlib.patches import Circle
for x in X[core_mask]:
    circ = Circle(x, eps, fill=False, edgecolor=COLOR_RED, alpha=0.15, lw=0.8)
    plt.gca().add_patch(circ)

plt.gca().set_aspect("equal")
plt.title(f"DBSCAN core/border/noise (eps={eps}, min_samples={min_samples})")
plt.xlabel("x1"); plt.ylabel("x2")
plt.legend(loc="upper right", fontsize=10)
plt.grid(True, alpha=0.25)
plt.tight_layout()
save("dbscan_core_border_noise.svg")


# ============================================================
# Fig 3: Effect of eps on clustering result
# ============================================================
X, _ = make_blobs(n_samples=300, centers=[(0, 0), (4, 4), (-3, 3)], cluster_std=[0.8, 1.2, 0.6],
                   random_state=0)
# Add noise
noise = np.random.default_rng(0).uniform([-5, -2], [6, 6], (30, 2))
X = np.vstack([X, noise])

fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
for ax, eps in zip(axes, [0.3, 0.8, 2.0]):
    db = DBSCAN(eps=eps, min_samples=5).fit(X)
    mask_noise = db.labels_ == -1
    n_clusters = len(set(db.labels_)) - (1 if -1 in db.labels_ else 0)
    ax.scatter(X[~mask_noise, 0], X[~mask_noise, 1], c=db.labels_[~mask_noise],
                cmap="tab10", s=20, edgecolor="white")
    ax.scatter(X[mask_noise, 0], X[mask_noise, 1], color="gray", marker="x", s=30)
    ax.set_title(f"eps={eps}: {n_clusters} clusters, {mask_noise.sum()} noise")
    ax.set_xlabel("x1"); ax.set_ylabel("x2")
    ax.grid(True, alpha=0.25)
plt.suptitle("eps controls density threshold: too small → all noise, too big → 1 mega-cluster", y=1.02)
plt.tight_layout()
save("dbscan_eps_sensitivity.png")


# ============================================================
# Fig 4: k-distance plot for eps selection
# ============================================================
from sklearn.neighbors import NearestNeighbors

X2, _ = make_blobs(n_samples=500, centers=3, cluster_std=0.6, random_state=0)
k = 5
nbrs = NearestNeighbors(n_neighbors=k).fit(X2)
distances, _ = nbrs.kneighbors(X2)
k_distances = np.sort(distances[:, -1])

plt.figure(figsize=(8, 4.5))
plt.plot(k_distances, color=COLOR_BLUE, lw=2)
plt.xlabel(f"points sorted by {k}-NN distance")
plt.ylabel(f"distance to {k}th neighbor")
plt.title(f"k-distance plot: look for the elbow → suggested eps")
# Find elbow approximation (max curvature)
# Simple: pick at 95th percentile
elbow = np.percentile(k_distances, 95)
plt.axhline(elbow, color=COLOR_RED, ls="--", lw=1.5,
            label=f"suggested eps ≈ {elbow:.3f}")
plt.legend()
plt.grid(True, alpha=0.25)
plt.tight_layout()
save("dbscan_k_distance_elbow.svg")


print("done:", sorted(os.listdir(NOTE_DIR)))
