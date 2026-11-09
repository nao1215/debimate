"""knn ノート用の図を生成するスクリプト。

実行: cd projects/ml && uv run python scripts/notes/knn_gen.py

出力先はこのスクリプトから見た ../../notes/ml/knn/。
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from sklearn.datasets import make_classification
from sklearn.neighbors import KNeighborsClassifier

COLOR_BLUE = "#7aa6c2"
COLOR_RED = "#e15759"
COLOR_GREEN = "#59a14f"

NOTE_DIR = Path(__file__).resolve().parents[2] / "notes" / "ml" / "knn"
NOTE_DIR.mkdir(parents=True, exist_ok=True)


# --- 図1: 星印の点と最も近い 5 点 ---
rng = np.random.default_rng(0)
X_a = rng.standard_normal((30, 2)) + [0, 0]
X_b = rng.standard_normal((30, 2)) + [3, 3]
X = np.vstack([X_a, X_b])
y = np.array([0] * 30 + [1] * 30)
query = np.array([1.5, 1.5])

dists = np.linalg.norm(X - query, axis=1)
nearest_idx = np.argsort(dists)[:5]
print("nearest labels:", y[nearest_idx], "dists:", dists[nearest_idx].round(3))

fig, ax = plt.subplots(figsize=(5.5, 5))
for i in nearest_idx:
    ax.plot([query[0], X[i, 0]], [query[1], X[i, 1]],
            linestyle="--", color="#888888", linewidth=1)
ax.scatter(X_a[:, 0], X_a[:, 1], s=60, color=COLOR_BLUE, edgecolor="white",
           label="class A")
ax.scatter(X_b[:, 0], X_b[:, 1], s=60, color=COLOR_RED, edgecolor="white",
           label="class B")
ax.scatter(*query, marker="*", s=300, color=COLOR_GREEN, edgecolor="black",
           label="query (k=5)")
ax.set_xlabel("x1")
ax.set_ylabel("x2")
ax.set_title("kNN: query and its 5 nearest neighbors")
ax.legend(loc="lower right")
for side in ("top", "right", "left", "bottom"):
    ax.spines[side].set_visible(False)
plt.tight_layout()
plt.savefig(NOTE_DIR / "knn_concept.svg", bbox_inches="tight")
# Remove trailing whitespace so `git diff --check` passes.
_svg_path = Path(NOTE_DIR / "knn_concept.svg")
_svg_path.write_text("\n".join(l.rstrip() for l in _svg_path.read_text().splitlines()) + "\n")
plt.close()


# --- 図2: k の違いによる決定境界 ---
X2, y2 = make_classification(
    n_samples=300, n_features=2, n_informative=2, n_redundant=0,
    n_clusters_per_class=1, class_sep=1.2, random_state=0,
)
x_min, x_max = X2[:, 0].min() - 0.5, X2[:, 0].max() + 0.5
y_min, y_max = X2[:, 1].min() - 0.5, X2[:, 1].max() + 0.5
xx, yy = np.meshgrid(np.linspace(x_min, x_max, 300),
                     np.linspace(y_min, y_max, 300))

fig, axes = plt.subplots(1, 3, figsize=(12, 4))
for ax, k in zip(axes, [1, 5, 25]):
    model = KNeighborsClassifier(n_neighbors=k).fit(X2, y2)
    zz = model.predict(np.c_[xx.ravel(), yy.ravel()]).reshape(xx.shape)
    ax.contourf(xx, yy, zz, alpha=0.3, cmap="coolwarm")
    ax.scatter(X2[:, 0], X2[:, 1], c=y2, cmap="coolwarm", edgecolor="white")
    ax.set_title(f"k = {k}")
    ax.set_xlabel("x1")
axes[0].set_ylabel("x2")
fig.suptitle("Decision boundary by k")
plt.tight_layout()
plt.savefig(NOTE_DIR / "knn_k_compare.png", dpi=120, bbox_inches="tight")
plt.close()
