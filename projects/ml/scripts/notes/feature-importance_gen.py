"""feature-importance ノート用の図を生成するスクリプト。

実行: cd projects/ml && uv run python scripts/notes/feature-importance_gen.py
"""
import os

import matplotlib.pyplot as plt
import numpy as np
from sklearn.datasets import make_classification, load_breast_cancer
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.model_selection import train_test_split

COLOR_BLUE = "#7aa6c2"
COLOR_RED = "#e15759"
COLOR_GREEN = "#59a14f"
COLOR_ORANGE = "#f28e2b"
COLOR_GRAY = "#999999"

NOTE_DIR = os.path.expanduser(
    "~/ghq/github.com/nao1215/debimate/projects/ml/notes/ml/feature-importance"
)
os.makedirs(NOTE_DIR, exist_ok=True)


def save(name: str) -> None:
    plt.savefig(os.path.join(NOTE_DIR, name), bbox_inches="tight")
    plt.close()


# ============================================================
# Fig 1: MDI (built-in tree importance) on breast cancer
# ============================================================
data = load_breast_cancer()
X, y = data.data, data.target
feature_names = data.feature_names
X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.3, random_state=0,
                                            stratify=y)

rf = RandomForestClassifier(n_estimators=200, random_state=0).fit(X_tr, y_tr)
mdi = rf.feature_importances_
order = np.argsort(mdi)[::-1][:15]

plt.figure(figsize=(8, 5.5))
plt.barh(range(len(order)), mdi[order][::-1], color=COLOR_BLUE, edgecolor="white")
plt.yticks(range(len(order)), feature_names[order][::-1])
plt.xlabel("MDI (mean decrease in impurity)")
plt.title("Built-in feature importance (top 15) on breast cancer dataset")
plt.tight_layout()
save("featimp_mdi.svg")


# ============================================================
# Fig 2: Permutation importance vs MDI
# ============================================================
perm = permutation_importance(rf, X_te, y_te, n_repeats=20, random_state=0,
                               n_jobs=-1)
perm_mean = perm.importances_mean
perm_std = perm.importances_std
order_perm = np.argsort(perm_mean)[::-1][:15]

fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))
ax = axes[0]
ax.barh(range(len(order)), mdi[order][::-1], color=COLOR_BLUE, edgecolor="white")
ax.set_yticks(range(len(order))); ax.set_yticklabels(feature_names[order][::-1],
                                                       fontsize=8)
ax.set_xlabel("MDI"); ax.set_title("MDI (built-in)")

ax = axes[1]
ax.barh(range(len(order_perm)), perm_mean[order_perm][::-1],
        xerr=perm_std[order_perm][::-1], color=COLOR_GREEN, edgecolor="white",
        ecolor="black", capsize=2)
ax.set_yticks(range(len(order_perm))); ax.set_yticklabels(feature_names[order_perm][::-1],
                                                             fontsize=8)
ax.set_xlabel("decrease in test accuracy after shuffling")
ax.set_title("Permutation importance (test set)")

plt.tight_layout()
save("featimp_mdi_vs_permutation.svg")


# ============================================================
# Fig 3: MDI bias on high-cardinality features (noise feature ID)
# ============================================================
rng = np.random.default_rng(0)
X_base, y_base = make_classification(n_samples=2000, n_features=4, n_informative=3,
                                       n_redundant=0, n_classes=2, random_state=0)

# Inject a noise high-cardinality column (random IDs)
noise_id = rng.integers(0, 2000, size=2000).reshape(-1, 1).astype(float)
X_full = np.hstack([X_base, noise_id])
feat_names = ["x1", "x2", "x3", "x4", "random_id"]

X_tr, X_te, y_tr, y_te = train_test_split(X_full, y_base, test_size=0.3,
                                            random_state=0, stratify=y_base)
rf2 = RandomForestClassifier(n_estimators=200, random_state=0).fit(X_tr, y_tr)
mdi2 = rf2.feature_importances_
perm2 = permutation_importance(rf2, X_te, y_te, n_repeats=20, random_state=0,
                                n_jobs=-1).importances_mean

x_pos = np.arange(len(feat_names))
width = 0.35

fig, ax = plt.subplots(figsize=(8, 4.5))
ax.bar(x_pos - width / 2, mdi2, width, color=COLOR_BLUE, edgecolor="white",
       label="MDI (training, biased toward high-cardinality)")
ax.bar(x_pos + width / 2, perm2, width, color=COLOR_GREEN, edgecolor="white",
       label="Permutation (test, honest)")
ax.set_xticks(x_pos); ax.set_xticklabels(feat_names)
ax.set_ylabel("importance")
ax.set_title("MDI inflates importance of useless 'random_id' (high cardinality)")
ax.legend(fontsize=9)
ax.grid(True, alpha=0.25, axis="y")
plt.tight_layout()
save("featimp_mdi_bias.svg")


# ============================================================
# Fig 4: Permutation importance procedure schematic
# ============================================================
rng4 = np.random.default_rng(0)
data4 = rng4.normal(0, 1, (8, 4))
shuffled = data4.copy()
shuffled[:, 1] = rng4.permutation(shuffled[:, 1])  # shuffle column 1

fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))

ax = axes[0]
ax.imshow(data4, cmap="Blues", aspect="auto")
for i in range(8):
    for j in range(4):
        ax.text(j, i, f"{data4[i,j]:+.1f}", ha="center", va="center", fontsize=8)
ax.set_xticks([0, 1, 2, 3]); ax.set_xticklabels(["x1", "x2", "x3", "x4"])
ax.set_yticks(range(8))
ax.set_title("1. Original X\nbaseline score = 0.92")

ax = axes[1]
im = ax.imshow(shuffled, cmap="Blues", aspect="auto")
for i in range(8):
    for j in range(4):
        color = "white" if j == 1 else "black"
        ax.text(j, i, f"{shuffled[i,j]:+.1f}", ha="center", va="center",
                fontsize=8, color=color,
                bbox=dict(boxstyle="round,pad=0.05", fc="#e15759", alpha=0.5) if j == 1 else None)
ax.set_xticks([0, 1, 2, 3]); ax.set_xticklabels(["x1", "x2 (shuffled)", "x3", "x4"])
ax.set_yticks(range(8))
ax.set_title("2. Shuffle x2 column → break its signal\nnew score = 0.65")

ax = axes[2]
ax.barh(["x1", "x2", "x3", "x4"], [0.03, 0.27, 0.05, 0.08],
        color=[COLOR_BLUE, COLOR_RED, COLOR_BLUE, COLOR_BLUE], edgecolor="white")
ax.set_xlabel("baseline - score after shuffle")
ax.set_title("3. Importance = score drop\nrepeat n_repeats times, average")
ax.grid(True, alpha=0.25, axis="x")

plt.tight_layout()
save("featimp_permutation_steps.svg")


print("done:", sorted(os.listdir(NOTE_DIR)))
