"""hierarchical-clustering ノート用の図を生成するスクリプト。"""
import os
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
from scipy.cluster.hierarchy import dendrogram, linkage, fcluster
from sklearn.datasets import make_blobs
from sklearn.cluster import AgglomerativeClustering

COLOR_BLUE, COLOR_RED, COLOR_GREEN, COLOR_ORANGE = "#7aa6c2", "#e15759", "#59a14f", "#f28e2b"

# 出力先はこのスクリプトから見た Page Bundle（projects/ml/notes/ml/hierarchical-clustering）。
NOTE_DIR = os.environ.get("NOTE_DIR", str(
    Path(__file__).resolve().parents[2] / "notes" / "ml" / "hierarchical-clustering"
))
os.makedirs(NOTE_DIR, exist_ok=True)


def save(name):
    path = os.path.join(NOTE_DIR, name)
    plt.savefig(path, bbox_inches="tight")
    plt.close()
    if path.endswith(".svg"):
        svg = Path(path).read_text()
        Path(path).write_text("\n".join(line.rstrip() for line in svg.splitlines()) + "\n")


# ============================================================
# Fig 1: Dendrogram + cluster cut at different heights
# ============================================================
X, y = make_blobs(n_samples=40, centers=3, cluster_std=0.8, random_state=0)
Z = linkage(X, method="ward")

fig, axes = plt.subplots(1, 2, figsize=(14, 5))

ax = axes[0]
dendrogram(Z, ax=ax, color_threshold=8)
ax.axhline(8, color=COLOR_RED, ls="--", lw=1.5, label="cut at h=8 → 3 clusters")
ax.axhline(12, color=COLOR_GREEN, ls="--", lw=1.5, label="cut at h=12 → 2 clusters")
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
    sizes = sorted(np.bincount(ac.labels_), reverse=True)
    axes[1, col].set_title("k=3 cluster sizes: " + " / ".join(str(n) for n in sizes))
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

fig, axes = plt.subplots(1, 5, figsize=(15, 3.6))
# 距離は single linkage の結合距離。Step 1/2 と Step 3/4 はそれぞれ同じ距離で、
# SciPy は同距離の候補を先に見つけた順に結合する。
stages = [
    ("Step 0: 7 clusters", [[0], [1], [2], [3], [4], [5], [6]]),
    ("Step 1: 0 + 1 (d=0.224)", [[0, 1], [2], [3], [4], [5], [6]]),
    ("Step 2: 2 + 4 (d=0.224)", [[0, 1], [2, 4], [3], [5], [6]]),
    ("Step 3: 5 + 6 (d=0.283)", [[0, 1], [2, 4], [3], [5, 6]]),
    ("Step 4: 3 + {2, 4} (d=0.283)", [[0, 1], [2, 3, 4], [5, 6]]),
]
colors = ["tab:blue", "tab:orange", "tab:green", "tab:red", "tab:purple", "tab:brown", "tab:pink"]
from scipy.spatial import ConvexHull
# 点番号を置く向き（点同士が近いので、重ならない側へずらす）
label_offset = {0: (-0.22, 0), 1: (0.22, 0), 2: (-0.22, 0), 3: (0.22, -0.05),
                4: (0, 0.25), 5: (-0.22, 0), 6: (0.22, 0)}
for ax, (title, clusters) in zip(axes, stages):
    for cluster in clusters:
        # クラスタの色は含まれる最小の点番号で決め、ステップをまたいでも変えない
        color = colors[min(cluster)]
        for idx in cluster:
            ax.scatter(points[idx, 0], points[idx, 1], color=color, s=90,
                        edgecolor="black", linewidth=0.8, zorder=3)
            dx, dy = label_offset[idx]
            ax.text(points[idx, 0] + dx, points[idx, 1] + dy, str(idx), ha="center",
                    va="center", fontsize=11, zorder=4)
        if len(cluster) > 1:
            pts = points[cluster]
            try:
                hull = ConvexHull(pts)
                for simplex in hull.simplices:
                    ax.plot(pts[simplex, 0], pts[simplex, 1], color=color, alpha=0.5)
            except Exception:
                ax.plot(pts[:, 0], pts[:, 1], color=color, alpha=0.5)
    ax.set_xlim(0, 4); ax.set_ylim(0, 4.2)
    ax.set_title(title, fontsize=11)
    ax.tick_params(labelsize=8)
    ax.grid(True, alpha=0.25)

plt.suptitle("Agglomerative clustering (single linkage): four merges reduce seven clusters to three",
             y=1.02, fontsize=12)
plt.tight_layout()
save("hierarchical_steps.svg")


print("done:", sorted(os.listdir(NOTE_DIR)))
