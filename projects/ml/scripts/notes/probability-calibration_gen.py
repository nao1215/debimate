"""probability-calibration ノート用の図を生成するスクリプト。"""
import os
import matplotlib.pyplot as plt
import numpy as np
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.datasets import make_classification
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import GaussianNB
from sklearn.svm import SVC

COLOR_BLUE, COLOR_RED, COLOR_GREEN, COLOR_ORANGE = "#7aa6c2", "#e15759", "#59a14f", "#f28e2b"

NOTE_DIR = os.path.expanduser(
    "~/ghq/github.com/nao1215/debimate/projects/ml/notes/ml/probability-calibration"
)
os.makedirs(NOTE_DIR, exist_ok=True)


def save(name):
    plt.savefig(os.path.join(NOTE_DIR, name), bbox_inches="tight")
    plt.close()


X, y = make_classification(n_samples=3000, n_features=10, n_informative=5,
                            n_redundant=2, random_state=0)
X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.5, random_state=0,
                                           stratify=y)

# ============================================================
# Fig 1: Reliability diagram - multiple classifiers
# ============================================================
models = {
    "Logistic Regression": LogisticRegression(max_iter=2000),
    "Naive Bayes": GaussianNB(),
    "Random Forest": RandomForestClassifier(n_estimators=100, random_state=0),
    "SVM (rbf)": SVC(probability=True, random_state=0),
}

plt.figure(figsize=(8.5, 6))
plt.plot([0, 1], [0, 1], "k--", lw=1, label="perfectly calibrated")

for name, clf in models.items():
    clf.fit(X_tr, y_tr)
    proba = clf.predict_proba(X_te)[:, 1]
    fop, mpv = calibration_curve(y_te, proba, n_bins=10)
    plt.plot(mpv, fop, "o-", lw=2, label=name)

plt.xlabel("predicted probability (mean)")
plt.ylabel("observed positive fraction")
plt.title("Reliability diagram: how close predicted probabilities are to truth")
plt.legend(loc="upper left", fontsize=9)
plt.grid(True, alpha=0.25)
plt.tight_layout()
save("calib_reliability_diagram.svg")


# ============================================================
# Fig 2: Before vs After calibration (Platt scaling, isotonic)
# ============================================================
base = GaussianNB().fit(X_tr, y_tr)
platt = CalibratedClassifierCV(GaussianNB(), method="sigmoid", cv=3).fit(X_tr, y_tr)
iso = CalibratedClassifierCV(GaussianNB(), method="isotonic", cv=3).fit(X_tr, y_tr)

fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
for ax, (name, clf, color) in zip(axes, [
    ("Base Naive Bayes (uncalibrated)", base, COLOR_RED),
    ("After Platt scaling (sigmoid)", platt, COLOR_GREEN),
    ("After isotonic regression", iso, COLOR_BLUE),
]):
    proba = clf.predict_proba(X_te)[:, 1]
    fop, mpv = calibration_curve(y_te, proba, n_bins=10)
    ax.plot([0, 1], [0, 1], "k--", lw=1, label="ideal")
    ax.plot(mpv, fop, "o-", color=color, lw=2.5, label="model")
    # Brier score
    brier = np.mean((proba - y_te) ** 2)
    ax.set_title(f"{name}\nBrier = {brier:.4f}")
    ax.set_xlabel("predicted prob")
    ax.set_ylabel("observed fraction")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.25)
plt.tight_layout()
save("calib_before_after.svg")


# ============================================================
# Fig 3: Histogram of predicted probabilities
# ============================================================
fig, axes = plt.subplots(1, 3, figsize=(15, 4))
for ax, (name, clf, color) in zip(axes, [
    ("Uncalibrated NB", base, COLOR_RED),
    ("After Platt (sigmoid)", platt, COLOR_GREEN),
    ("After isotonic", iso, COLOR_BLUE),
]):
    proba = clf.predict_proba(X_te)[:, 1]
    ax.hist(proba, bins=25, color=color, edgecolor="white")
    ax.set_xlabel("predicted prob")
    ax.set_ylabel("count")
    ax.set_title(name)
    ax.grid(True, alpha=0.25, axis="y")
plt.suptitle("Probability histograms: NB pushes scores to extremes, calibration spreads them",
             y=1.02)
plt.tight_layout()
save("calib_probability_histogram.svg")


print("done:", sorted(os.listdir(NOTE_DIR)))
