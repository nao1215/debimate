"""Reproduce the calibration experiment (train/calibration/test = 1500/750/750).

Run from projects/ml: uv run python scripts/notes/probability-calibration_gen.py
Requires scikit-learn >= 1.6 for FrozenEstimator.
"""
from pathlib import Path
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import sklearn
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.datasets import make_classification
from sklearn.frozen import FrozenEstimator
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import GaussianNB

NOTE_DIR = Path(__file__).resolve().parents[2] / "notes/ml/probability-calibration"
NOTE_DIR.mkdir(parents=True, exist_ok=True)
BLUE, GREEN, BROWN = "#537c91", "#5f8075", "#9a6d46"
plt.rcParams.update({"font.size": 10, "axes.titlesize": 11, "axes.spines.top": False,
                     "axes.spines.right": False, "svg.hashsalt": "probability-calibration"})
results = {"sklearn": sklearn.__version__, "numpy": np.__version__}


def save(name):
    plt.savefig(NOTE_DIR / name, bbox_inches="tight", metadata={"Date": None})
    plt.close()


# BEGIN split
X, y = make_classification(n_samples=3000, n_features=10,
                          n_informative=5, n_redundant=2, random_state=0)
X_tr, X_rest, y_tr, y_rest = train_test_split(
    X, y, test_size=0.5, stratify=y, random_state=0)
X_cal, X_te, y_cal, y_te = train_test_split(
    X_rest, y_rest, test_size=0.5, stratify=y_rest, random_state=0)
base = GaussianNB().fit(X_tr, y_tr)
raw = base.predict_proba(X_te)[:, 1]
observed, predicted = calibration_curve(y_te, raw, n_bins=10, strategy="uniform")
fig, ax = plt.subplots(figsize=(5, 4))
ax.plot([0, 1], [0, 1], "--", color="#777777", label="Ideal")
ax.plot(predicted, observed, "o-", color=BLUE, label="Before calibration")
ax.set(xlabel="Mean predicted probability", ylabel="Observed positive fraction",
       xlim=(0, 1), ylim=(0, 1))
ax.legend(loc="upper left")
plt.tight_layout()
save("calib_reliability_diagram.svg")
# END split

# BEGIN calibrate
models = {"Before": base}
for name, method in [("Sigmoid", "sigmoid"), ("Isotonic", "isotonic")]:
    models[name] = CalibratedClassifierCV(
        FrozenEstimator(base), method=method).fit(X_cal, y_cal)
probabilities = {name: model.predict_proba(X_te)[:, 1] for name, model in models.items()}
fig, ax = plt.subplots(figsize=(5.5, 4.3))
ax.plot([0, 1], [0, 1], "--", color="#777777", label="Ideal")
for (name, proba), color in zip(probabilities.items(), [BLUE, BROWN, GREEN]):
    brier = brier_score_loss(y_te, proba)
    auc = roc_auc_score(y_te, proba)
    print(f"{name:8s} Brier={brier:.4f} ROC AUC={auc:.4f}")
    observed, predicted = calibration_curve(y_te, proba, n_bins=10, strategy="uniform")
    ax.plot(predicted, observed, "o-", color=color, label=name, markersize=4)
ax.set(xlabel="Mean predicted probability", ylabel="Observed positive fraction",
       xlim=(0, 1), ylim=(0, 1))
ax.legend(loc="upper left")
plt.tight_layout()
save("calib_before_after.svg")
# END calibrate

# BEGIN histogram
fig, ax = plt.subplots(figsize=(5.5, 3.5))
for (name, proba), color in zip(probabilities.items(), [BLUE, BROWN, GREEN]):
    ax.hist(proba, bins=np.linspace(0, 1, 11), histtype="step", linewidth=1.5,
            color=color, label=name)
ax.set(xlabel="Predicted probability", ylabel="Number of test samples")
ax.legend(loc="upper center")
plt.tight_layout()
save("calib_probability_histogram.svg")
# END histogram

results["samples"] = {"train": len(y_tr), "calibration": len(y_cal), "test": len(y_te)}
results["models"] = {}
for name, proba in probabilities.items():
    counts, _ = np.histogram(proba, bins=np.linspace(0, 1, 11))
    results["models"][name] = {"brier": brier_score_loss(y_te, proba),
        "roc_auc": roc_auc_score(y_te, proba), "bin_counts": counts.tolist()}
(NOTE_DIR / "results.json").write_text(json.dumps(results, indent=2) + "\n")
