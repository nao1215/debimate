"""ensemble-learning ノート用の図を生成するスクリプト。

実行: cd projects/ml && uv run python scripts/notes/ensemble-learning_gen.py
"""
import os

import matplotlib.pyplot as plt
import numpy as np
from sklearn.datasets import make_moons, make_classification
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import (BaggingClassifier, RandomForestClassifier,
                              GradientBoostingClassifier, StackingClassifier)
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC

COLOR_BLUE = "#7aa6c2"
COLOR_RED = "#e15759"
COLOR_GREEN = "#59a14f"
COLOR_ORANGE = "#f28e2b"
COLOR_GRAY = "#999999"

NOTE_DIR = os.path.expanduser(
    "~/ghq/github.com/nao1215/debimate/projects/ml/notes/ml/ensemble-learning"
)
os.makedirs(NOTE_DIR, exist_ok=True)


def save(name: str) -> None:
    plt.savefig(os.path.join(NOTE_DIR, name), bbox_inches="tight")
    plt.close()


# ============================================================
# Fig 1: Single tree vs Bagging vs Boosting - decision boundaries
# ============================================================
X, y = make_moons(n_samples=400, noise=0.3, random_state=0)
xx, yy = np.meshgrid(np.linspace(-2, 3, 250), np.linspace(-1.5, 2, 250))

models = [
    ("Single tree (max_depth=4)",
     DecisionTreeClassifier(max_depth=4, random_state=0)),
    ("Bagging (100 trees, averaging)",
     RandomForestClassifier(n_estimators=100, max_depth=4, random_state=0)),
    ("Boosting (100 trees, sequential)",
     GradientBoostingClassifier(n_estimators=100, max_depth=4, random_state=0)),
]

fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
for ax, (title, m) in zip(axes, models):
    m.fit(X, y)
    Z = m.predict(np.c_[xx.ravel(), yy.ravel()]).reshape(xx.shape)
    ax.contourf(xx, yy, Z, alpha=0.25, cmap="coolwarm")
    ax.scatter(X[:, 0], X[:, 1], c=y, cmap="coolwarm", edgecolor="white", s=22)
    ax.set_title(title, fontsize=10)
    ax.set_xlabel("x1"); ax.set_ylabel("x2")
plt.suptitle("Ensembles smooth out the rough boundary of a single tree", y=1.02)
plt.tight_layout()
save("ensemble_boundary_compare.png")


# ============================================================
# Fig 2: Bagging variance reduction - multiple boostrap fits
# ============================================================
rng = np.random.default_rng(0)
xx_1d = np.linspace(0, 10, 200)

def true_f(x):
    return np.sin(x) + 0.3 * x

base_color = COLOR_BLUE
fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))

# Left: many individual deep trees on bootstrap samples
ax = axes[0]
for seed in range(20):
    rng_local = np.random.default_rng(seed)
    x_train = rng_local.uniform(0, 10, 40)
    y_train = true_f(x_train) + rng_local.normal(0, 0.5, 40)
    tree = DecisionTreeClassifier(max_depth=8)  # placeholder
    # Use a tree regressor instead
    from sklearn.tree import DecisionTreeRegressor
    t = DecisionTreeRegressor(max_depth=8).fit(x_train.reshape(-1, 1), y_train)
    ax.plot(xx_1d, t.predict(xx_1d.reshape(-1, 1)),
            color=base_color, alpha=0.25, lw=1)
ax.plot(xx_1d, true_f(xx_1d), color="black", lw=2, ls="--", label="true f")
ax.set_title("20 individual deep trees on bootstrap samples\n(high variance)")
ax.set_xlabel("x"); ax.set_ylabel("y")
ax.legend()
ax.grid(True, alpha=0.25)

# Right: bagged ensemble average
ax = axes[1]
from sklearn.ensemble import BaggingRegressor
from sklearn.tree import DecisionTreeRegressor
preds_collect = []
for seed in range(20):
    rng_local = np.random.default_rng(seed)
    x_train = rng_local.uniform(0, 10, 40)
    y_train = true_f(x_train) + rng_local.normal(0, 0.5, 40)
    bag = BaggingRegressor(estimator=DecisionTreeRegressor(max_depth=8),
                            n_estimators=100, random_state=seed).fit(x_train.reshape(-1, 1), y_train)
    preds_collect.append(bag.predict(xx_1d.reshape(-1, 1)))
    ax.plot(xx_1d, bag.predict(xx_1d.reshape(-1, 1)), color=COLOR_GREEN, alpha=0.35, lw=1.2)
ax.plot(xx_1d, true_f(xx_1d), color="black", lw=2, ls="--", label="true f")
ax.set_title("20 bagged ensembles (each = 100 trees averaged)\n(low variance, similar curves)")
ax.set_xlabel("x"); ax.set_ylabel("y")
ax.legend()
ax.grid(True, alpha=0.25)

plt.tight_layout()
save("ensemble_bagging_variance.svg")


# ============================================================
# Fig 3: Boosting - residual correction visualization
# ============================================================
rng3 = np.random.default_rng(0)
n3 = 200
x3 = np.linspace(0, 10, n3)
y3 = np.sin(x3) + 0.3 * x3 + rng3.normal(0, 0.4, n3)

from sklearn.tree import DecisionTreeRegressor
# Manually simulate boosting (depth=2 weak learners, lr=0.3)
n_rounds = 30
lr = 0.3
preds_total = np.zeros_like(x3)
preds_test = np.zeros_like(x3)
losses = []
for r in range(n_rounds):
    resid = y3 - preds_total
    weak = DecisionTreeRegressor(max_depth=2).fit(x3.reshape(-1, 1), resid)
    preds_total += lr * weak.predict(x3.reshape(-1, 1))
    losses.append(np.mean((y3 - preds_total) ** 2))

fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))

ax = axes[0]
ax.scatter(x3, y3, color=COLOR_BLUE, alpha=0.5, s=15, label="data")
# Show rounds 1, 5, 30
preds_partial = np.zeros_like(x3)
for r_idx, target_round in enumerate([1, 5, 30]):
    preds_show = np.zeros_like(x3)
    rng_l = np.random.default_rng(0)
    yy_local = y3.copy()
    for r in range(target_round):
        resid = yy_local - preds_show
        weak = DecisionTreeRegressor(max_depth=2).fit(x3.reshape(-1, 1), resid)
        preds_show += lr * weak.predict(x3.reshape(-1, 1))
    color = [COLOR_RED, COLOR_GREEN, COLOR_ORANGE][r_idx]
    ax.plot(x3, preds_show, color=color, lw=2,
            label=f"after {target_round} rounds")
ax.set_title("Boosting: each round adds a tree on the residual")
ax.set_xlabel("x"); ax.set_ylabel("y")
ax.legend()
ax.grid(True, alpha=0.25)

ax = axes[1]
ax.plot(range(1, len(losses) + 1), losses, "o-", color=COLOR_BLUE, lw=2)
ax.set_xlabel("boosting round")
ax.set_ylabel("training MSE")
ax.set_title("Loss decreases monotonically as rounds accumulate")
ax.grid(True, alpha=0.25)

plt.tight_layout()
save("ensemble_boosting_rounds.svg")


# ============================================================
# Fig 4: Three ensemble types schematic (as bar plot of accuracy)
# ============================================================
# Run on a real dataset
X_c, y_c = make_classification(n_samples=1500, n_features=15, n_informative=8,
                                 n_redundant=3, random_state=0)
from sklearn.model_selection import cross_val_score

models_eval = {
    "Single tree": DecisionTreeClassifier(max_depth=5, random_state=0),
    "Bagging\n(100 trees, RF)": RandomForestClassifier(n_estimators=100, max_depth=5, random_state=0),
    "Boosting\n(100 stumps, GB)": GradientBoostingClassifier(n_estimators=100, max_depth=3, random_state=0),
    "Stacking\n(LR + SVM + RF)": StackingClassifier(
        estimators=[("lr", LogisticRegression(max_iter=2000)),
                     ("svc", SVC(probability=True, random_state=0)),
                     ("rf", RandomForestClassifier(n_estimators=50, random_state=0))],
        final_estimator=LogisticRegression(max_iter=2000)),
}

means = []
stds = []
names = []
for name, m in models_eval.items():
    scores = cross_val_score(m, X_c, y_c, cv=5, scoring="accuracy")
    means.append(scores.mean()); stds.append(scores.std()); names.append(name)

fig, ax = plt.subplots(figsize=(9, 4.5))
xpos = np.arange(len(names))
colors = [COLOR_GRAY, COLOR_GREEN, COLOR_RED, COLOR_BLUE]
bars = ax.bar(xpos, means, yerr=stds, color=colors, edgecolor="white", capsize=5)
for b, m in zip(bars, means):
    ax.text(b.get_x() + b.get_width() / 2, m + 0.005, f"{m:.3f}",
            ha="center", fontsize=10)
ax.set_xticks(xpos); ax.set_xticklabels(names, fontsize=9)
ax.set_ylabel("5-fold CV accuracy")
ax.set_ylim(0.75, 1.0)
ax.set_title("Ensembles consistently improve over a single tree")
ax.grid(True, alpha=0.25, axis="y")
plt.tight_layout()
save("ensemble_accuracy_compare.svg")


print("done:", sorted(os.listdir(NOTE_DIR)))
