"""class-imbalance ノート用の図を生成するスクリプト。

実行: cd projects/ml && uv run python scripts/notes/class-imbalance_gen.py
"""
import os

import matplotlib.pyplot as plt
import numpy as np
from sklearn.datasets import make_classification
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, precision_score, recall_score,
                             f1_score, average_precision_score)
from sklearn.model_selection import train_test_split

COLOR_BLUE = "#7aa6c2"
COLOR_RED = "#e15759"
COLOR_GREEN = "#59a14f"
COLOR_ORANGE = "#f28e2b"
COLOR_GRAY = "#999999"

NOTE_DIR = os.path.expanduser(
    "~/ghq/github.com/nao1215/debimate/projects/ml/notes/ml/class-imbalance"
)
os.makedirs(NOTE_DIR, exist_ok=True)


def save(name: str) -> None:
    plt.savefig(os.path.join(NOTE_DIR, name), bbox_inches="tight")
    plt.close()


# Helper
def plot_boundary(ax, model, X, y, title, xlim, ylim):
    xx, yy = np.meshgrid(np.linspace(xlim[0], xlim[1], 250),
                          np.linspace(ylim[0], ylim[1], 250))
    Z = model.predict(np.c_[xx.ravel(), yy.ravel()]).reshape(xx.shape)
    ax.contourf(xx, yy, Z, alpha=0.25, cmap="coolwarm")
    minority = y == 1
    ax.scatter(X[~minority, 0], X[~minority, 1], color=COLOR_BLUE, alpha=0.4, s=20,
               label=f"majority (n={(~minority).sum()})")
    ax.scatter(X[minority, 0], X[minority, 1], color=COLOR_RED, edgecolor="black", s=40,
               label=f"minority (n={minority.sum()})")
    ax.set_title(title, fontsize=10)
    ax.set_xlabel("x1"); ax.set_ylabel("x2")
    ax.legend(loc="upper right", fontsize=8)


# ============================================================
# Setup: heavily imbalanced 2D data
# ============================================================
X, y = make_classification(
    n_samples=1000, n_features=2, n_informative=2, n_redundant=0,
    n_clusters_per_class=1, weights=[0.95, 0.05], class_sep=1.0,
    random_state=0
)
print(f"class distribution: majority {(y == 0).sum()}, minority {(y == 1).sum()}")

xlim = (X[:, 0].min() - 0.5, X[:, 0].max() + 0.5)
ylim = (X[:, 1].min() - 0.5, X[:, 1].max() + 0.5)


# ============================================================
# Fig 1: Vanilla LR vs class_weight='balanced'
# ============================================================
plain = LogisticRegression(max_iter=2000).fit(X, y)
weighted = LogisticRegression(class_weight="balanced", max_iter=2000).fit(X, y)

fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))
plot_boundary(axes[0], plain, X, y, "Vanilla LR\n(boundary drifts toward minority)",
              xlim, ylim)
plot_boundary(axes[1], weighted, X, y,
              "LR + class_weight='balanced'\n(boundary moves to give minority a chance)",
              xlim, ylim)
plt.tight_layout()
save("imbalance_class_weight.png")


# ============================================================
# Fig 2: Resampling strategies
# ============================================================
from imblearn.over_sampling import RandomOverSampler, SMOTE
from imblearn.under_sampling import RandomUnderSampler

samplers = {
    "Original (95:5)": (X, y),
    "Random over-sampling\n(duplicate minority)":
        RandomOverSampler(random_state=0).fit_resample(X, y),
    "Random under-sampling\n(drop majority)":
        RandomUnderSampler(random_state=0).fit_resample(X, y),
    "SMOTE\n(synthesize new minority points)":
        SMOTE(random_state=0).fit_resample(X, y),
}

fig, axes = plt.subplots(1, 4, figsize=(17, 4.5))
for ax, (title, (Xr, yr)) in zip(axes, samplers.items()):
    minority = yr == 1
    ax.scatter(Xr[~minority, 0], Xr[~minority, 1], color=COLOR_BLUE, alpha=0.35, s=15)
    ax.scatter(Xr[minority, 0], Xr[minority, 1], color=COLOR_RED, alpha=0.5, s=20,
               edgecolor="black", linewidths=0.4)
    ax.set_title(f"{title}\n(majority={(yr==0).sum()}, minority={(yr==1).sum()})",
                 fontsize=9)
    ax.set_xlim(xlim); ax.set_ylim(ylim)
    ax.set_xlabel("x1")
axes[0].set_ylabel("x2")
plt.tight_layout()
save("imbalance_resampling.png")


# ============================================================
# Fig 3: Decision boundaries from resampling
# ============================================================
fig, axes = plt.subplots(1, 3, figsize=(15, 5))
for ax, (title, (Xr, yr)) in zip(axes, [
    ("Original (LR)", (X, y)),
    ("After random over-sampling",
     RandomOverSampler(random_state=0).fit_resample(X, y)),
    ("After SMOTE",
     SMOTE(random_state=0).fit_resample(X, y)),
]):
    m = LogisticRegression(max_iter=2000).fit(Xr, yr)
    plot_boundary(ax, m, X, y, title, xlim, ylim)
plt.tight_layout()
save("imbalance_boundary_resampling.png")


# ============================================================
# Fig 4: Metrics breakdown - Accuracy is misleading, F1/PR-AUC honest
# ============================================================
# Multi-model comparison
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3,
                                                      stratify=y, random_state=0)

plain_lr = LogisticRegression(max_iter=2000).fit(X_train, y_train)
balanced_lr = LogisticRegression(class_weight="balanced", max_iter=2000).fit(X_train, y_train)
Xs, ys = SMOTE(random_state=0).fit_resample(X_train, y_train)
smote_lr = LogisticRegression(max_iter=2000).fit(Xs, ys)

scenarios = {
    "Predict all majority\n(naive baseline)": (
        np.zeros_like(y_test), np.zeros_like(y_test, dtype=float)),
    "LR (no rebalance)":
        (plain_lr.predict(X_test), plain_lr.predict_proba(X_test)[:, 1]),
    "LR + class_weight":
        (balanced_lr.predict(X_test), balanced_lr.predict_proba(X_test)[:, 1]),
    "LR + SMOTE":
        (smote_lr.predict(X_test), smote_lr.predict_proba(X_test)[:, 1]),
}

names, acc_v, prec_v, rec_v, f1_v, pr_v = [], [], [], [], [], []
for name, (pred, proba) in scenarios.items():
    names.append(name)
    acc_v.append(accuracy_score(y_test, pred))
    prec_v.append(precision_score(y_test, pred, zero_division=0))
    rec_v.append(recall_score(y_test, pred, zero_division=0))
    f1_v.append(f1_score(y_test, pred, zero_division=0))
    pr_v.append(average_precision_score(y_test, proba))

xpos = np.arange(len(names))
width = 0.16
fig, ax = plt.subplots(figsize=(11, 5))
for i, (vals, label, color) in enumerate(zip(
    [acc_v, prec_v, rec_v, f1_v, pr_v],
    ["Accuracy", "Precision", "Recall", "F1", "PR-AUC"],
    [COLOR_GRAY, COLOR_BLUE, COLOR_GREEN, COLOR_ORANGE, COLOR_RED],
)):
    bars = ax.bar(xpos + (i - 2) * width, vals, width, label=label, color=color,
                  edgecolor="white")
ax.set_xticks(xpos); ax.set_xticklabels(names, fontsize=8)
ax.set_ylabel("score")
ax.set_ylim(0, 1.05)
ax.set_title("Same imbalanced data — 'predict all majority' gets 95% accuracy but 0 on everything else")
ax.legend(loc="upper left", ncol=5, fontsize=9)
ax.grid(True, alpha=0.25, axis="y")
plt.tight_layout()
save("imbalance_metrics_breakdown.svg")


print("done:", sorted(os.listdir(NOTE_DIR)))
