"""k-means ノートの「k の選び方」セクション用の図を生成するスクリプト。

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

NOTE_DIR = os.path.expanduser(
    "~/ghq/github.com/nao1215/debimate/projects/ml/notes/ml/k-means"
)
os.makedirs(NOTE_DIR, exist_ok=True)


def save(name: str) -> None:
    plt.savefig(os.path.join(NOTE_DIR, name), bbox_inches="tight")
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
