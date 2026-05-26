"""feature-selection ノート用の図を生成するスクリプト。

実行: cd projects/ml && uv run python scripts/notes/feature-selection_gen.py
"""
import os

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

NOTE_DIR = os.path.expanduser(
    "~/ghq/github.com/nao1215/debimate/projects/ml/notes/ml/feature-selection"
)
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

# Top-K with ANOVA F-test and mutual info
f_scores, _ = f_classif(X, y)
mi_scores = mutual_info_classif(X, y, random_state=0)

idx = np.argsort(f_scores)[::-1]
x_pos = np.arange(20)
width = 0.4

# Normalize for visual comparison
f_norm = f_scores[idx] / f_scores[idx].max()
mi_norm = mi_scores[idx] / mi_scores[idx].max()

fig, ax = plt.subplots(figsize=(11, 4.5))
ax.bar(x_pos - width / 2, f_norm, width, color=COLOR_BLUE, edgecolor="white",
       label="ANOVA F-test (normalized)")
ax.bar(x_pos + width / 2, mi_norm, width, color=COLOR_GREEN, edgecolor="white",
       label="Mutual information (normalized)")
ax.set_xticks(x_pos); ax.set_xticklabels([f"x{i+1}" for i in idx], fontsize=8,
                                            rotation=45)
ax.set_ylabel("normalized importance score")
ax.set_title("Filter methods rank features independently from any model\n"
             "(20 features, 5 informative + 2 redundant + 13 noise)")
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
                                     n_redundant=4, random_state=0)
true_informative = np.zeros(30, dtype=bool)
# scikit-learn make_classification puts informative features first
true_informative[:8] = True

# Lasso (LogisticRegression L1)
lasso = make_pipeline(StandardScaler(),
                      LogisticRegression(penalty="l1", solver="liblinear",
                                          C=0.5, max_iter=5000))
lasso.fit(X_emb, y_emb)
lasso_coef = np.abs(lasso[-1].coef_[0])

# RF importance
rf = RandomForestClassifier(n_estimators=200, random_state=0).fit(X_emb, y_emb)
rf_imp = rf.feature_importances_

fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))

ax = axes[0]
colors = [COLOR_GREEN if true_informative[i] else COLOR_GRAY for i in range(30)]
ax.bar(range(30), lasso_coef, color=colors, edgecolor="white")
ax.set_xlabel("feature index")
ax.set_ylabel("|Lasso coefficient|")
ax.set_title(f"Lasso (L1): {(lasso_coef > 0).sum()} non-zero of 30")
ax.grid(True, alpha=0.25, axis="y")

ax = axes[1]
ax.bar(range(30), rf_imp, color=colors, edgecolor="white")
ax.set_xlabel("feature index")
ax.set_ylabel("RF feature_importances_")
ax.set_title("Random Forest importances (gray = noise feature)")
ax.grid(True, alpha=0.25, axis="y")

from matplotlib.patches import Patch
legend_elems = [
    Patch(facecolor=COLOR_GREEN, label="truly informative (first 8)"),
    Patch(facecolor=COLOR_GRAY, label="redundant or noise (22)"),
]
axes[0].legend(handles=legend_elems, fontsize=9, loc="upper right")

plt.tight_layout()
save("featsel_embedded_compare.svg")


print("done:", sorted(os.listdir(NOTE_DIR)))
