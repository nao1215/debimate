"""decision-tree ノート用の図を生成するスクリプト。

実行: cd projects/ml && uv run python scripts/notes/decision-tree_gen.py
"""
import os

import matplotlib.pyplot as plt
import numpy as np
from sklearn.datasets import make_moons, make_classification
from sklearn.tree import DecisionTreeClassifier, plot_tree

COLOR_BLUE = "#7aa6c2"
COLOR_RED = "#e15759"
COLOR_GREEN = "#59a14f"
COLOR_ORANGE = "#f28e2b"

NOTE_DIR = os.path.expanduser(
    "~/ghq/github.com/nao1215/debimate/projects/ml/notes/ml/decision-tree"
)
os.makedirs(NOTE_DIR, exist_ok=True)


def save(name: str) -> None:
    plt.savefig(os.path.join(NOTE_DIR, name), bbox_inches="tight")
    plt.close()


# ============================================================
# Fig 1: Decision boundary at increasing max_depth (axis-aligned splits)
# ============================================================
rng = np.random.default_rng(0)
X, y = make_classification(n_samples=300, n_features=2, n_informative=2,
                            n_redundant=0, n_clusters_per_class=1,
                            class_sep=0.9, random_state=0)

xx, yy = np.meshgrid(np.linspace(X[:, 0].min() - 0.5, X[:, 0].max() + 0.5, 250),
                      np.linspace(X[:, 1].min() - 0.5, X[:, 1].max() + 0.5, 250))

depths = [1, 3, 10]
titles = ["max_depth=1 (single split)", "max_depth=3 (good fit)", "max_depth=10 (over-fit)"]

fig, axes = plt.subplots(1, 3, figsize=(13, 4.3))
for ax, d, title in zip(axes, depths, titles):
    clf = DecisionTreeClassifier(max_depth=d, random_state=0).fit(X, y)
    Z = clf.predict(np.c_[xx.ravel(), yy.ravel()]).reshape(xx.shape)
    ax.contourf(xx, yy, Z, alpha=0.25, cmap="coolwarm")
    ax.scatter(X[:, 0], X[:, 1], c=y, cmap="coolwarm", edgecolor="white", s=30)
    ax.set_title(title, fontsize=10)
    ax.set_xlabel("x1"); ax.set_ylabel("x2")
plt.tight_layout()
save("decision_tree_boundary.png")


# ============================================================
# Fig 2: Tree structure visualization
# ============================================================
plt.figure(figsize=(12, 6))
clf3 = DecisionTreeClassifier(max_depth=3, random_state=0).fit(X, y)
plot_tree(clf3,
          feature_names=["x1", "x2"],
          class_names=["class 0", "class 1"],
          filled=True, rounded=True, fontsize=9)
plt.title("Decision tree (max_depth=3): each node = a 'if feature < threshold' split")
plt.tight_layout()
save("decision_tree_structure.svg")


# ============================================================
# Fig 3: Impurity curves (Gini vs Entropy) as functions of class probability
# ============================================================
p = np.linspace(0.001, 0.999, 400)
gini = 2 * p * (1 - p)
entropy = -(p * np.log2(p) + (1 - p) * np.log2(1 - p))

plt.figure(figsize=(7.5, 4.5))
plt.plot(p, gini, color=COLOR_BLUE, lw=2.2, label="Gini impurity = 2 p (1 - p)")
plt.plot(p, entropy / 2, color=COLOR_RED, lw=2.2, ls="--",
         label="Entropy / 2 (scaled for comparison)")
plt.axvline(0.5, color="black", lw=0.5, ls=":")
plt.xlabel("class 1 probability p")
plt.ylabel("impurity")
plt.title("Both metrics peak at p=0.5 (max impurity)\n"
          "and equal 0 when all samples are one class")
plt.legend()
plt.grid(True, alpha=0.25)
plt.tight_layout()
save("decision_tree_impurity.svg")


# ============================================================
# Fig 4: Non-convex moons - trees handle non-linear shapes
# ============================================================
X_m, y_m = make_moons(n_samples=300, noise=0.15, random_state=0)
xx_m, yy_m = np.meshgrid(np.linspace(-1.5, 2.5, 250),
                          np.linspace(-1.2, 1.7, 250))

depths_m = [2, 5, None]
titles_m = ["max_depth=2 (under-fit)", "max_depth=5", "max_depth=None (fully grown, over-fit)"]

fig, axes = plt.subplots(1, 3, figsize=(13, 4.3))
for ax, d, title in zip(axes, depths_m, titles_m):
    clf = DecisionTreeClassifier(max_depth=d, random_state=0).fit(X_m, y_m)
    Z = clf.predict(np.c_[xx_m.ravel(), yy_m.ravel()]).reshape(xx_m.shape)
    ax.contourf(xx_m, yy_m, Z, alpha=0.25, cmap="coolwarm")
    ax.scatter(X_m[:, 0], X_m[:, 1], c=y_m, cmap="coolwarm", edgecolor="white", s=25)
    ax.set_title(title, fontsize=10)
    ax.set_xlabel("x1"); ax.set_ylabel("x2")
plt.tight_layout()
save("decision_tree_moons.png")


print("done:", sorted(os.listdir(NOTE_DIR)))
