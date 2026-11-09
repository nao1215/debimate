"""feature-selection ノート用の図を生成するスクリプト。

実行: cd projects/ml && uv run python scripts/notes/feature-selection_gen.py
"""
import os
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from sklearn.datasets import make_classification
from sklearn.feature_selection import (VarianceThreshold, SelectKBest,
                                         f_classif, mutual_info_classif, RFECV)
from sklearn.linear_model import LogisticRegression, LassoCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score, StratifiedKFold
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline

COLOR_BLUE = "#7aa6c2"
COLOR_RED = "#e15759"
COLOR_GREEN = "#59a14f"
COLOR_ORANGE = "#f28e2b"
COLOR_GRAY = "#999999"

NOTE_DIR = os.environ.get("NOTE_DIR", str(
    Path(__file__).resolve().parents[2] / "notes" / "ml" / "feature-selection"
))
os.makedirs(NOTE_DIR, exist_ok=True)


def save(name: str) -> None:
    plt.savefig(os.path.join(NOTE_DIR, name), bbox_inches="tight")
    plt.close()


# ============================================================
# Fig 1: Variance threshold - drop low-variance features
# ============================================================
rng = np.random.default_rng(0)
n = 1000
features = {
    "near_constant_0": np.zeros(n) + rng.normal(0, 0.001, n),
    "tiny_variance_1": rng.normal(0, 0.01, n),
    "small_variance_2": rng.normal(0, 0.1, n),
    "medium_variance_3": rng.normal(0, 1.0, n),
    "large_variance_4": rng.normal(0, 5.0, n),
}
X_arr = np.column_stack(list(features.values()))
vars_emp = X_arr.var(axis=0)

fig, ax = plt.subplots(figsize=(8, 4))
colors = [COLOR_RED if v < 0.05 else COLOR_GREEN for v in vars_emp]
bars = ax.barh(list(features.keys()), vars_emp, color=colors, edgecolor="white")
ax.axvline(0.05, color="black", ls="--", lw=1.5, label="threshold = 0.05")
for b, v in zip(bars, vars_emp):
    ax.text(v + 0.1, b.get_y() + b.get_height() / 2, f"{v:.4f}",
            va="center", fontsize=9)
ax.set_xscale("log")
ax.set_xlabel("variance (log scale)")
ax.set_title("VarianceThreshold: red = below threshold (dropped), green = kept")
ax.legend(fontsize=9, loc="lower right")
ax.grid(True, alpha=0.25, axis="x")
plt.tight_layout()
save("featsel_variance_threshold.svg")


# ============================================================
# Fig 2: SelectKBest with mutual information / F-test
# ============================================================
X, y = make_classification(n_samples=1500, n_features=20, n_informative=5,
                            n_redundant=2, random_state=0)

# shuffle=True で列が並べ替わるので、shuffle=False の同じデータと値の集合で突き合わせ、
# 各列が informative / redundant / noise のどれかを調べる
X_plain, _ = make_classification(n_samples=1500, n_features=20, n_informative=5,
                                 n_redundant=2, shuffle=False, random_state=0)
plain_index = {tuple(np.sort(X_plain[:, j])): j for j in range(20)}
orig_col = np.array([plain_index[tuple(np.sort(X[:, j]))] for j in range(20)])
kind = np.where(orig_col < 5, "inf", np.where(orig_col < 7, "red", ""))
print("informative:", np.where(kind == "inf")[0], "redundant:", np.where(kind == "red")[0])

# Top-K with ANOVA F-test and mutual info
f_scores, _ = f_classif(X, y)
mi_scores = mutual_info_classif(X, y, random_state=0)
print("top-5 by F-test:", np.argsort(f_scores)[::-1][:5])
print("top-5 by MI:    ", np.argsort(mi_scores)[::-1][:5])

idx = np.argsort(f_scores)[::-1]
x_pos = np.arange(20)
width = 0.4

# Normalize for visual comparison
f_norm = f_scores[idx] / f_scores[idx].max()
mi_norm = mi_scores[idx] / mi_scores[idx].max()

fig, ax = plt.subplots(figsize=(11, 4.5))
ax.bar(x_pos - width / 2, f_norm, width, color=COLOR_BLUE, edgecolor="white",
       label="ANOVA F-test (normalized)")
ax.bar(x_pos + width / 2, mi_norm, width, color=COLOR_ORANGE, edgecolor="white",
       label="Mutual information (normalized)")
ax.set_xticks(x_pos)
ax.set_xticklabels([f"{i}\n{kind[i]}" for i in idx], fontsize=8)
ax.set_xlabel("feature index (inf = informative, red = redundant, blank = noise)")
ax.set_ylabel("normalized score")
ax.set_title("Filter methods score each feature alone\n"
             "(20 features: 5 informative + 2 redundant + 13 noise)")
ax.legend(fontsize=9)
ax.grid(True, alpha=0.25, axis="y")
plt.tight_layout()
save("featsel_filter_scores.svg")


# ============================================================
# Fig 3: RFE (recursive feature elimination with CV)
# ============================================================
estimator = LogisticRegression(max_iter=2000)
rfecv = RFECV(estimator, step=1, cv=StratifiedKFold(5), scoring="accuracy",
              min_features_to_select=1, n_jobs=-1)
rfecv.fit(X, y)
print("RFECV:", rfecv.n_features_, np.where(rfecv.support_)[0])
mean_scores = rfecv.cv_results_["mean_test_score"]
std_scores = rfecv.cv_results_["std_test_score"]
n_features_grid = np.arange(1, len(mean_scores) + 1)

plt.figure(figsize=(8, 4.5))
plt.plot(n_features_grid, mean_scores, "o-", color=COLOR_BLUE, lw=2)
plt.fill_between(n_features_grid, mean_scores - std_scores,
                  mean_scores + std_scores, alpha=0.2, color=COLOR_BLUE)
plt.axvline(rfecv.n_features_, color=COLOR_RED, ls="--",
            label=f"selected = {rfecv.n_features_} features")
plt.xlabel("number of features kept")
plt.ylabel("5-fold CV accuracy")
plt.title("RFE-CV: backward elimination + CV finds the sweet spot")
plt.legend(fontsize=9)
plt.grid(True, alpha=0.25)
plt.tight_layout()
save("featsel_rfe_cv.svg")


# ============================================================
# Fig 4: Lasso vs RF importance for embedded feature selection
# ============================================================
X_emb, y_emb = make_classification(n_samples=2000, n_features=30, n_informative=8,
                                     n_redundant=4, shuffle=False, random_state=0)
# shuffle=False なので、列 0-7 が informative、8-11 が redundant（informative の線形結合）、
# 12-29 がノイズ
colors = [COLOR_GREEN] * 8 + [COLOR_ORANGE] * 4 + [COLOR_GRAY] * 18


def lasso_coef(C: float) -> np.ndarray:
    model = make_pipeline(StandardScaler(),
                          LogisticRegression(l1_ratio=1, solver="liblinear",
                                             C=C, max_iter=5000))
    return np.abs(model.fit(X_emb, y_emb)[-1].coef_[0])


rf = RandomForestClassifier(n_estimators=200, random_state=0).fit(X_emb, y_emb)
rf_imp = rf.feature_importances_

panels = []
for C in (0.5, 0.03):
    coef = lasso_coef(C)
    print(f"Lasso C={C}: non-zero {np.where(coef > 0)[0]}")
    panels.append((coef, "|Lasso coefficient|",
                   f"Lasso (L1), C = {C}: {(coef > 0).sum()} non-zero of 30"))
print("RF top-12:", np.argsort(rf_imp)[::-1][:12])
panels.append((rf_imp, "RF importance",
               "Random Forest feature_importances_ (no exact zeros)"))

fig, axes = plt.subplots(3, 1, figsize=(9, 8.5), sharex=True)
for ax, (vals, ylabel, title) in zip(axes, panels):
    ax.bar(range(30), vals, color=colors, edgecolor="white")
    ax.axvline(7.5, color="black", ls=":", lw=0.8)
    ax.axvline(11.5, color="black", ls=":", lw=0.8)
    ax.set_ylabel(ylabel)
    ax.set_title(title, fontsize=10)
    ax.grid(True, alpha=0.25, axis="y")
axes[-1].set_xlabel("feature index")
axes[-1].set_xticks(range(0, 30, 2))

from matplotlib.patches import Patch
legend_elems = [
    Patch(facecolor=COLOR_GREEN, label="informative (0-7)"),
    Patch(facecolor=COLOR_ORANGE, label="redundant (8-11)"),
    Patch(facecolor=COLOR_GRAY, label="noise (12-29)"),
]
axes[0].legend(handles=legend_elems, fontsize=9, loc="upper right")

plt.tight_layout()
save("featsel_embedded_compare.svg")


print("done:", sorted(os.listdir(NOTE_DIR)))
