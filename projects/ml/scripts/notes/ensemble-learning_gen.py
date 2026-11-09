"""ensemble-learning ノート用の図と数値を生成するスクリプト。

実行: cd projects/ml && uv run python scripts/notes/ensemble-learning_gen.py

ノート本文のコードは、このスクリプトの計算部分と同じ設定です。
本文に載せた出力は、このスクリプトの標準出力と一致します。
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from sklearn.datasets import make_classification, make_moons
from sklearn.ensemble import (BaggingRegressor, GradientBoostingClassifier,
                              RandomForestClassifier, StackingClassifier)
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor

COLOR_BLUE = "#7aa6c2"
COLOR_RED = "#e15759"
COLOR_GREEN = "#59a14f"
COLOR_ORANGE = "#f28e2b"
COLOR_GRAY = "#999999"

NOTE_DIR = Path(__file__).resolve().parents[2] / "notes" / "ml" / "ensemble-learning"
NOTE_DIR.mkdir(parents=True, exist_ok=True)


def save(name: str) -> None:
    plt.savefig(NOTE_DIR / name, bbox_inches="tight")
    plt.close()


# ============================================================
# Fig 1: Single tree vs Bagging vs Boosting - decision boundaries
# ============================================================
X, y = make_moons(n_samples=400, noise=0.3, random_state=0)
X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.5, random_state=0)
models = {
    "tree": DecisionTreeClassifier(max_depth=4, random_state=0),
    "bagging": RandomForestClassifier(n_estimators=100, max_depth=4, random_state=0),
    "boosting": GradientBoostingClassifier(n_estimators=100, max_depth=4, random_state=0),
}
titles = {
    "tree": "Single tree (max_depth=4)",
    "bagging": "Bagging: random forest (100 trees)",
    "boosting": "Boosting: gradient boosting (100 trees)",
}

xx, yy = np.meshgrid(np.linspace(-2, 3, 250), np.linspace(-1.5, 2, 250))
fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
for ax, (name, m) in zip(axes, models.items()):
    m.fit(X_tr, y_tr)
    acc_tr, acc_te = m.score(X_tr, y_tr), m.score(X_te, y_te)
    print(f"{name:8s} train={acc_tr:.3f} test={acc_te:.3f}")
    Z = m.predict(np.c_[xx.ravel(), yy.ravel()]).reshape(xx.shape)
    ax.contourf(xx, yy, Z, alpha=0.25, cmap="coolwarm")
    ax.scatter(X_tr[:, 0], X_tr[:, 1], c=y_tr, cmap="coolwarm",
               edgecolor="white", s=22)
    ax.set_title(f"{titles[name]}\ntrain acc {acc_tr:.3f} / test acc {acc_te:.3f}",
                 fontsize=10)
    ax.set_xlabel("x1"); ax.set_ylabel("x2")
plt.suptitle("Decision boundaries learned from the same 200 training points", y=1.02)
plt.tight_layout()
save("ensemble_boundary_compare.png")


# ============================================================
# Fig 2: Bagging variance reduction
# ============================================================
def true_f(x):
    return np.sin(x) + 0.3 * x


x_grid = np.linspace(0, 10, 200).reshape(-1, 1)
single, bagged = [], []
for seed in range(20):  # 訓練データを 20 回引き直す
    rng = np.random.default_rng(seed)
    x_tr = rng.uniform(0, 10, 40).reshape(-1, 1)
    y_tr1 = true_f(x_tr.ravel()) + rng.normal(0, 0.5, 40)
    tree = DecisionTreeRegressor(max_depth=8).fit(x_tr, y_tr1)
    bag = BaggingRegressor(estimator=DecisionTreeRegressor(max_depth=8),
                           n_estimators=100, random_state=seed).fit(x_tr, y_tr1)
    single.append(tree.predict(x_grid))
    bagged.append(bag.predict(x_grid))

var_single = np.var(single, axis=0).mean()
var_bagged = np.var(bagged, axis=0).mean()
print(f"single tree: {var_single:.3f}")
print(f"bagging:     {var_bagged:.3f}")

fig, axes = plt.subplots(1, 2, figsize=(13, 4.5), sharey=True)
panels = [
    (axes[0], single, COLOR_BLUE, 0.35,
     f"20 single deep trees, each on a fresh training set\n"
     f"mean variance across the 20 curves = {var_single:.3f}"),
    (axes[1], bagged, COLOR_GREEN, 0.45,
     f"20 bagging ensembles (100 trees each) on the same 20 sets\n"
     f"mean variance across the 20 curves = {var_bagged:.3f}"),
]
for ax, preds, color, alpha, title in panels:
    for p in preds:
        ax.plot(x_grid.ravel(), p, color=color, alpha=alpha, lw=1.1)
    ax.plot(x_grid.ravel(), true_f(x_grid.ravel()), color="black", lw=2, ls="--",
            label="true f")
    ax.set_title(title, fontsize=10)
    ax.set_xlabel("x"); ax.set_ylabel("y")
    ax.legend()
    ax.grid(True, alpha=0.25)
plt.tight_layout()
save("ensemble_bagging_variance.svg")


# ============================================================
# Fig 3: Boosting - residual correction
# ============================================================
x = np.linspace(0, 10, 200).reshape(-1, 1)
y3 = np.sin(x.ravel()) + 0.3 * x.ravel() + np.random.default_rng(0).normal(0, 0.4, 200)
mse_true = np.mean((y3 - true_f(x.ravel())) ** 2)
print(f"true f:   train MSE = {mse_true:.3f}")

pred = np.zeros(200)
losses, snapshots = [], {}
for r in range(1, 31):
    weak = DecisionTreeRegressor(max_depth=2).fit(x, y3 - pred)  # 残差に当てる
    pred += 0.3 * weak.predict(x)                                 # ν = 0.3
    losses.append(np.mean((y3 - pred) ** 2))
    if r in (1, 5, 30):
        snapshots[r] = pred.copy()
    if r in (1, 5, 10, 30):
        print(f"round {r:2d}: train MSE = {losses[-1]:.3f}")

fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))
ax = axes[0]
ax.scatter(x.ravel(), y3, color=COLOR_BLUE, alpha=0.5, s=15, label="data")
for (r, p), color in zip(snapshots.items(), [COLOR_RED, COLOR_GREEN, COLOR_ORANGE]):
    ax.plot(x.ravel(), p, color=color, lw=2, label=f"after {r} round{'s' if r > 1 else ''}")
ax.set_title("Boosting: each round adds a depth-2 tree fitted to the residual")
ax.set_xlabel("x"); ax.set_ylabel("y")
ax.legend()
ax.grid(True, alpha=0.25)

ax = axes[1]
ax.plot(range(1, len(losses) + 1), losses, "o-", color=COLOR_BLUE, lw=2,
        label="boosting")
ax.axhline(mse_true, color=COLOR_GRAY, ls="--",
           label=f"true f itself ({mse_true:.3f})")
ax.set_xlabel("boosting round")
ax.set_ylabel("training MSE")
ax.set_ylim(0, 0.6)
ax.set_title("Training MSE drops below the true function after round 10")
ax.legend()
ax.grid(True, alpha=0.25)
plt.tight_layout()
save("ensemble_boosting_rounds.svg")


# ============================================================
# Fig 4: Accuracy of a single tree, three ensembles and the base models
# ============================================================
X_c, y_c = make_classification(n_samples=1500, n_features=15, n_informative=8,
                               n_redundant=3, random_state=0)
base = [
    ("lr", LogisticRegression(max_iter=2000)),
    ("svc", SVC(random_state=0)),
    ("rf", RandomForestClassifier(n_estimators=50, random_state=0)),
]
models_eval = {
    "single tree": DecisionTreeClassifier(max_depth=5, random_state=0),
    "bagging (RF)": RandomForestClassifier(n_estimators=100, random_state=0),
    "boosting (GB)": GradientBoostingClassifier(n_estimators=100, max_depth=3,
                                                random_state=0),
    "stacking": StackingClassifier(estimators=base,
                                   final_estimator=LogisticRegression(max_iter=2000)),
}
models_eval.update({f"base only: {n}": m for n, m in base})

means, stds = [], []
for name, m in models_eval.items():
    s = cross_val_score(m, X_c, y_c, cv=5)
    means.append(s.mean()); stds.append(s.std())
    print(f"{name:16s} {s.mean():.3f} (±{s.std():.3f})")

labels = ["Single tree", "Bagging\n(RF)", "Boosting\n(GB)", "Stacking\n(LR+SVM+RF)",
          "LR alone", "SVM alone", "RF (50)\nalone"]
colors = [COLOR_GRAY, COLOR_GREEN, COLOR_RED, COLOR_BLUE,
          "#c9c9c9", "#c9c9c9", "#c9c9c9"]
fig, ax = plt.subplots(figsize=(10, 4.5))
xpos = np.arange(len(labels))
bars = ax.bar(xpos, means, yerr=stds, color=colors, edgecolor="white", capsize=5)
for b, m, sd in zip(bars, means, stds):
    ax.text(b.get_x() + b.get_width() / 2, m + sd + 0.004, f"{m:.3f}",
            ha="center", fontsize=10)
ax.set_xticks(xpos); ax.set_xticklabels(labels, fontsize=9)
ax.set_ylabel("5-fold CV accuracy")
ax.set_ylim(0.8, 1.0)
ax.set_title("Ensembles beat a single tree, but stacking does not beat SVM alone")
ax.grid(True, alpha=0.25, axis="y")
plt.tight_layout()
save("ensemble_accuracy_compare.svg")
