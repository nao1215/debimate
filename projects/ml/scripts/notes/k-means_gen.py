"""k-means ノートの図（手実装の 2 枚と「k の選び方」の 1 枚）を生成するスクリプト。

実行: cd projects/ml && uv run python scripts/notes/k-means_gen.py
"""
import os

import matplotlib.pyplot as plt
import numpy as np
from sklearn.cluster import KMeans
from sklearn.datasets import make_blobs
from sklearn.metrics import davies_bouldin_score, silhouette_score

COLOR_BLUE = "#7aa6c2"
COLOR_RED = "#e15759"
COLOR_GREEN = "#59a14f"

NOTE_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "notes", "ml", "k-means"
)
os.makedirs(NOTE_DIR, exist_ok=True)


def save(name: str) -> None:
    plt.savefig(os.path.join(NOTE_DIR, name), bbox_inches="tight")
    plt.close()


# --- 「Python での実例」の手実装（本文のコードと同じ） ---
# 分かりやすい人工データ（3 クラスタ）
rng = np.random.RandomState(0)
X1 = rng.randn(100, 2) + np.array([0, 0])
X2 = rng.randn(100, 2) + np.array([3, 3])
X3 = rng.randn(100, 2) + np.array([0, 4])
X = np.vstack([X1, X2, X3])

def kmeans(X, k, max_iter=100, seed=0):
    # 1. 初期中心をデータ点からランダムに選ぶ
    rng = np.random.RandomState(seed)
    init_centers = X[rng.choice(len(X), k, replace=False)]
    centers = init_centers

    for n_iter in range(1, max_iter + 1):
        # 2. 各点を最も近い中心へ割り当て
        dists = np.linalg.norm(X[:, None, :] - centers[None, :, :], axis=2)
        labels = np.argmin(dists, axis=1)

        # 3. 割り当てられた点の平均を新しい中心にする
        new_centers = centers.copy()
        for i in range(k):
            members = X[labels == i]
            if len(members) > 0:
                new_centers[i] = members.mean(axis=0)
            else:
                # 0 件だと平均が NaN になるので、中心から最も遠い点へ移す
                far = np.argmax(dists[np.arange(len(X)), labels])
                new_centers[i] = X[far]

        # 4. 中心がほぼ動かなくなったら終了
        if np.allclose(centers, new_centers, atol=1e-4):
            break
        centers = new_centers

    return labels, centers, init_centers, n_iter

labels, centers, init_centers, n_iter = kmeans(X, k=3)
print("反復回数:", n_iter)
print("初期中心:", init_centers.round(2).tolist())
print("最終中心:", centers.round(2).tolist())
print("各クラスタの点数:", np.bincount(labels))

# 図1：元データ + 初期中心
plt.figure()
plt.scatter(X[:, 0], X[:, 1], alpha=0.3)
plt.scatter(init_centers[:, 0], init_centers[:, 1], c="black", s=120, marker="x")
plt.title("Original data + initial centers")
plt.xlabel("x1")
plt.ylabel("x2")
plt.axis("equal")
plt.savefig(os.path.join(NOTE_DIR, "original.png"), dpi=150)
plt.close()

# 図2：k-means後
plt.figure()
plt.scatter(X[:, 0], X[:, 1], c=labels, cmap="tab10", alpha=0.5)
plt.scatter(centers[:, 0], centers[:, 1], c="black", s=120, marker="x")
plt.title("k-means clustering")
plt.xlabel("x1")
plt.ylabel("x2")
plt.axis("equal")
plt.savefig(os.path.join(NOTE_DIR, "k-means.png"), dpi=150)
plt.close()


# --- 3 クラスタの人工データで k 選定指標を比較 ---
X, _ = make_blobs(n_samples=300, centers=3, cluster_std=1.0, random_state=0)

ks = list(range(2, 11))
inertias = []
silhouettes = []
db_scores = []
for k in ks:
    km = KMeans(n_clusters=k, n_init=10, random_state=0).fit(X)
    inertias.append(km.inertia_)
    silhouettes.append(silhouette_score(X, km.labels_))
    db_scores.append(davies_bouldin_score(X, km.labels_))

fig, axes = plt.subplots(1, 3, figsize=(12, 3.5))

axes[0].plot(ks, inertias, "o-", color=COLOR_BLUE, linewidth=2)
axes[0].axvline(3, color="gray", linestyle="--", alpha=0.5)
axes[0].set_title("Elbow (inertia, lower is better but monotone)")
axes[0].set_xlabel("k")
axes[0].set_ylabel("Inertia")

axes[1].plot(ks, silhouettes, "o-", color=COLOR_GREEN, linewidth=2)
axes[1].axvline(3, color="gray", linestyle="--", alpha=0.5)
axes[1].set_title("Silhouette (higher is better)")
axes[1].set_xlabel("k")
axes[1].set_ylabel("Score")

axes[2].plot(ks, db_scores, "o-", color=COLOR_RED, linewidth=2)
axes[2].axvline(3, color="gray", linestyle="--", alpha=0.5)
axes[2].set_title("Davies-Bouldin (lower is better)")
axes[2].set_xlabel("k")
axes[2].set_ylabel("Index")

fig.suptitle(
    "Three indicators agree on k=3 for a 3-cluster blob dataset",
    fontsize=11,
)
plt.tight_layout()
save("k-means_selection.svg")


print("Saved figure to:", NOTE_DIR)
print("k    inertia   silhouette   davies-bouldin")
for k, ine, sil, db in zip(ks, inertias, silhouettes, db_scores):
    print(f"{k:<5d} {ine:8.1f}   {sil:10.3f}   {db:8.3f}")
