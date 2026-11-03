"""Reproduce the feature importance experiments and figures.

Run from projects/ml: uv run python scripts/notes/feature-importance_gen.py
Outputs are relative to this file, so a checkout or draft remains isolated.
"""
from pathlib import Path
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import sklearn
from sklearn.datasets import load_breast_cancer
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.model_selection import train_test_split

NOTE_DIR = Path(__file__).resolve().parents[2] / "notes/ml/feature-importance"
NOTE_DIR.mkdir(parents=True, exist_ok=True)
BLUE, GREEN, BROWN = "#537c91", "#5f8075", "#9a6d46"
plt.rcParams.update({"font.size": 10, "axes.titlesize": 11, "axes.spines.top": False,
                     "axes.spines.right": False, "svg.hashsalt": "feature-importance"})
results = {"sklearn": sklearn.__version__, "numpy": np.__version__}


def save(name):
    plt.savefig(NOTE_DIR / name, bbox_inches="tight", metadata={"Date": None})
    plt.close()


# BEGIN breast-cancer
# label 1 means benign in this dataset; this example explains the model, not diagnosis.
data = load_breast_cancer()
X_tr, X_te, y_tr, y_te = train_test_split(
    data.data, data.target, test_size=0.3, stratify=data.target, random_state=0)
rf = RandomForestClassifier(n_estimators=200, random_state=0).fit(X_tr, y_tr)
mdi = rf.feature_importances_
perm = permutation_importance(
    rf, X_te, y_te, scoring="accuracy", n_repeats=20, random_state=0, n_jobs=1)
print(f"breast cancer: train={rf.score(X_tr, y_tr):.4f}, test={rf.score(X_te, y_te):.4f}")
order = np.argsort(mdi)[-8:]
fig, ax = plt.subplots(figsize=(6, 3.5))
ax.barh(data.feature_names[order], mdi[order], color=BLUE)
ax.set_xlabel("MDI (normalized impurity decrease)")
plt.tight_layout()
save("featimp_mdi.svg")
# END breast-cancer

# Use the same feature order: changes in ranking must remain visible.
fig, ax = plt.subplots(figsize=(6, 3.5))
ax.barh(data.feature_names[order], perm.importances_mean[order],
        xerr=perm.importances_std[order], color=GREEN, capsize=2)
ax.axvline(0, color="#555555", linewidth=0.7)
ax.set_xlabel("Decrease in test accuracy (mean ± SD)")
plt.tight_layout()
save("featimp_mdi_vs_permutation.svg")
results["breast_cancer"] = {"train_accuracy": rf.score(X_tr, y_tr),
    "test_accuracy": rf.score(X_te, y_te), "features": data.feature_names.tolist(),
    "mdi": mdi.tolist(), "permutation_mean": perm.importances_mean.tolist(),
    "permutation_std": perm.importances_std.tolist()}

# BEGIN noise
rng = np.random.default_rng(7)
n = 3000
signal = rng.integers(0, 2, n)
y = signal.copy()
flip = rng.random(n) < 0.15
y[flip] = 1 - y[flip]
X = np.column_stack([signal, rng.integers(0, 2, n), rng.normal(size=n)])
names = ["signal", "noise_binary", "noise_continuous"]
X_tr, X_te, y_tr, y_te = train_test_split(
    X, y, test_size=0.4, stratify=y, random_state=7)
rf_noise = RandomForestClassifier(n_estimators=200, random_state=7).fit(X_tr, y_tr)
p = permutation_importance(
    rf_noise, X_te, y_te, scoring="accuracy", n_repeats=20, random_state=7, n_jobs=1)
print(f"noise: train={rf_noise.score(X_tr, y_tr):.4f}, test={rf_noise.score(X_te, y_te):.4f}")
for name, mdi_value, pi in zip(names, rf_noise.feature_importances_, p.importances_mean):
    print(f"{name:16s} MDI={mdi_value:.4f} permutation={pi:.4f}")
fig, axes = plt.subplots(2, 1, figsize=(6, 4.8), sharex=True)
axes[0].bar(names, rf_noise.feature_importances_, color=BLUE)
axes[0].set_ylabel("MDI")
axes[1].bar(names, p.importances_mean, yerr=p.importances_std, color=GREEN, capsize=3)
axes[1].set_ylabel("Test accuracy drop")
axes[1].axhline(0, color="#555555", linewidth=0.7)
plt.tight_layout()
save("featimp_mdi_bias.svg")
# END noise
results["noise"] = {"train_accuracy": rf_noise.score(X_tr, y_tr),
    "test_accuracy": rf_noise.score(X_te, y_te), "features": names,
    "mdi": rf_noise.feature_importances_.tolist(),
    "permutation_mean": p.importances_mean.tolist(), "permutation_std": p.importances_std.tolist()}

# BEGIN correlated
# Each column is a perfect copy. A shallow forest can use either column.
rng = np.random.default_rng(12)
x = rng.normal(size=2000)
y = (x > 0).astype(int)
X = np.column_stack([x, x])
X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.4, random_state=12)
rf_pair = RandomForestClassifier(
    n_estimators=200, max_depth=1, max_features=1, random_state=12).fit(X_tr, y_tr)
baseline = rf_pair.score(X_te, y_te)
drops = []
for columns in ([0], [1], [0, 1]):
    values = []
    for _ in range(20):
        shuffled = X_te.copy()
        rows = rng.permutation(len(X_te))
        shuffled[:, columns] = X_te[rows][:, columns]
        values.append(baseline - rf_pair.score(shuffled, y_te))
    drops.append(values)
drops = np.array(drops)
for name, value in zip(["A only", "B only", "A + B"], drops.mean(axis=1)):
    print(f"{name}: accuracy drop={value:.4f}")
fig, ax = plt.subplots(figsize=(5, 3.2))
ax.bar(["A only", "B only", "A + B"], drops.mean(axis=1),
       yerr=drops.std(axis=1), color=[BLUE, BLUE, BROWN], capsize=3)
ax.set_ylabel("Decrease in test accuracy")
plt.tight_layout()
save("featimp_correlated.svg")
# END correlated
results["correlated"] = {"baseline": baseline, "mean": drops.mean(axis=1).tolist(),
                         "std": drops.std(axis=1).tolist()}
(NOTE_DIR / "results.json").write_text(json.dumps(results, indent=2) + "\n")
