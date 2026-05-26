"""hierarchical-clustering ノート用の図を生成するスクリプト。"""
import os
import matplotlib.pyplot as plt
import numpy as np
from scipy.cluster.hierarchy import dendrogram, linkage, fcluster
from sklearn.datasets import make_blobs
from sklearn.cluster import AgglomerativeClustering

COLOR_BLUE, COLOR_RED, COLOR_GREEN, COLOR_ORANGE = "#7aa6c2", "#e15759", "#59a14f", "#f28e2b"

NOTE_DIR = os.path.expanduser(
    "~/ghq/github.com/nao1215/debimate/projects/ml/notes/ml/hierarchical-clustering"
)
os.makedirs(NOTE_DIR, exist_ok=True)


def save(name):
    plt.savefig(os.path.join(NOTE_DIR, name), bbox_inches="tight")
    plt.close()


# ============================================================
# Fig 1: Dendrogram + cluster cut at different heights
# ============================================================
X, y = make_blobs(n_samples=40, centers=3, cluster_std=0.8, random_state=0)
Z = linkage(X, method="ward")

fig, axes = plt.subplots(1, 2, figsize=(14, 5))

ax = axes[0]
dendrogram(Z, ax=ax, color_threshold=8)
ax.axhline(8, color=COLOR_RED, ls="--", lw=1.5, label="cut at h=8 → 3 clusters")
ax.axhline(15, color=COLOR_GREEN, ls="--", lw=1.5, label="cut at h=15 → 2 clusters")
ax.set_title("Dendrogram: tree of merges from bottom up")
ax.set_xlabel("sample index")
ax.set_ylabel("merge distance")
ax.legend(fontsize=9)

# Scatter with cluster colors
labels_3 = fcluster(Z, t=8, criterion="distance")
ax = axes[1]
ax.scatter(X[:, 0], X[:, 1], c=labels_3, cmap="tab10", s=80, edgecolor="white")
ax.set_title("Cut at h=8 → 3 clusters")
ax.set_xlabel("x1"); ax.set_ylabel("x2")
ax.grid(True, alpha=0.25)

plt.tight_layout()
save("hierarchical_dendrogram.svg")


# ============================================================
# Fig 2: Linkage methods comparison
# ============================================================
fig, axes = plt.subplots(2, 4, figsize=(16, 8))

methods = ["single", "complete", "average", "ward"]
descriptions = [
    "single (chaining)",
    "complete (compact)",
    "average (balanced)",
    "ward (variance-based)",
]

# Top row: dendrograms
for col, (method, desc) in enumerate(zip(methods, descriptions)):
    Z2 = linkage(X, method=method)
    dendrogram(Z2, ax=axes[0, col], no_labels=True)
    axes[0, col].set_title(f"linkage = {desc}")
    axes[0, col].set_ylabel("distance" if col == 0 else "")

# Bottom row: resulting clusters at 3
for col, method in enumerate(methods):
    ac = AgglomerativeClustering(n_clusters=3, linkage=method).fit(X)
    axes[1, col].scatter(X[:, 0], X[:, 1], c=ac.labels_, cmap="tab10", s=40,
                          edgecolor="white")
    axes[1, col].set_xlabel("x1")
    axes[1, col].set_ylabel("x2" if col == 0 else "")
    axes[1, col].grid(True, alpha=0.25)

plt.tight_layout()
save("hierarchical_linkage_compare.png")


# ============================================================
# Fig 3: Agglomerative process step by step (small example)
# ============================================================
np.random.seed(0)
points = np.array([
    [0.5, 1.0], [0.7, 0.9], [3.0, 3.0], [3.2, 2.8], [3.1, 3.2],
    [1.5, 3.5], [1.7, 3.3],
])

fig, axes = plt.subplots(1, 4, figsize=(15, 4))
stages = [
    ("Step 0: each point is a cluster", [[0], [1], [2], [3], [4], [5], [6]]),
    ("Step 1: merge closest pair", [[0, 1], [2], [3], [4], [5], [6]]),
    ("Step 2", [[0, 1], [2, 3, 4], [5], [6]]),
    ("Step 3: end with k=3", [[0, 1], [2, 3, 4], [5, 6]]),
]
colors = ["tab:blue", "tab:orange", "tab:green", "tab:red", "tab:purple", "tab:brown", "tab:pink"]
for ax, (title, clusters) in zip(axes, stages):
    for ci, cluster in enumerate(clusters):
        for idx in cluster:
            ax.scatter(points[idx, 0], points[idx, 1], color=colors[ci], s=200,
                        edgecolor="black", linewidth=0.8)
        if len(cluster) > 1:
            # Draw convex hull-ish (just lines)
            pts = points[cluster]
            from scipy.spatial import ConvexHull
            try:
                hull = ConvexHull(pts)
                for simplex in hull.simplices:
                    ax.plot(pts[simplex, 0], pts[simplex, 1], color=colors[ci], alpha=0.5)
            except Exception:
                ax.plot(pts[:, 0], pts[:, 1], color=colors[ci], alpha=0.5)
    ax.set_xlim(0, 4); ax.set_ylim(0, 4.5)
    ax.set_title(title, fontsize=10)
    ax.grid(True, alpha=0.25)

plt.suptitle("Agglomerative clustering: each step merges the 2 closest clusters",
             y=1.02)
plt.tight_layout()
save("hierarchical_steps.svg")


print("done:", sorted(os.listdir(NOTE_DIR)))
