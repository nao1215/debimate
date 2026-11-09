"""LogisticRegression ノート用の図を生成するスクリプト。

実行: cd projects/ml && uv run python scripts/notes/logistic-regression_gen.py
"""
import os
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from sklearn.datasets import make_classification
from sklearn.linear_model import LogisticRegression

COLOR_BLUE = "#7aa6c2"
COLOR_RED = "#e15759"
COLOR_GREEN = "#59a14f"

NOTE_DIR = str(
    Path(__file__).resolve().parents[2] / "notes" / "ml" / "logistic-regression"
)
os.makedirs(NOTE_DIR, exist_ok=True)


def save(name):
    plt.savefig(os.path.join(NOTE_DIR, name), bbox_inches="tight")
    plt.close()
    # Remove trailing whitespace so `git diff --check` passes.
    _svg_path = Path(NOTE_DIR) / name
    if _svg_path.suffix == ".svg":
        _svg_path.write_text("\n".join(l.rstrip() for l in _svg_path.read_text().splitlines()) + "\n")


# --- 図1: シグモイド関数 ---
zs = np.linspace(-8, 8, 400)
ps = 1.0 / (1.0 + np.exp(-zs))

plt.figure(figsize=(6, 4))
plt.plot(zs, ps, color=COLOR_BLUE, linewidth=2)
plt.axhline(0.5, color="gray", linestyle="--", alpha=0.5)
plt.axvline(0, color="gray", linestyle="--", alpha=0.5)
plt.title("Sigmoid: p = 1 / (1 + exp(-z))")
plt.xlabel("z = w^T x + b")
plt.ylabel("p (probability of class 1)")
plt.grid(alpha=0.2)
plt.tight_layout()
save("logistic-regression_sigmoid.svg")


# --- 図2: 2D データでの決定境界 ---
X, y = make_classification(
    n_samples=300, n_features=2, n_informative=2, n_redundant=0,
    n_clusters_per_class=1, class_sep=1.2, random_state=0,
)
model = LogisticRegression(C=1.0, max_iter=1000).fit(X, y)

pad = 0.5
xx, yy = np.meshgrid(
    np.linspace(X[:, 0].min() - pad, X[:, 0].max() + pad, 300),
    np.linspace(X[:, 1].min() - pad, X[:, 1].max() + pad, 300),
)
Z = model.predict_proba(np.c_[xx.ravel(), yy.ravel()])[:, 1].reshape(xx.shape)

plt.figure(figsize=(6, 5))
cs = plt.contourf(xx, yy, Z, levels=20, cmap="coolwarm", alpha=0.5)
plt.colorbar(cs, label="P(class=1)")
plt.contour(xx, yy, Z, levels=[0.5], colors="black", linewidths=1.5)
plt.scatter(X[:, 0], X[:, 1], c=y, cmap="coolwarm", edgecolor="white", s=35)
plt.title("Decision boundary (p=0.5) and probability contours")
plt.xlabel("x1")
plt.ylabel("x2")
plt.tight_layout()
save("logistic-regression_boundary.png")


# --- 図3: 正則化強度 C による係数の挙動 ---
X_multi, y_multi = make_classification(
    n_samples=500, n_features=8, n_informative=5, n_redundant=2,
    random_state=0,
)
Cs = np.logspace(-3, 2, 30)
coefs = []
for C in Cs:
    # penalty 引数は scikit-learn 1.8 で deprecated。L2 はデフォルト挙動なので指定しない
    m = LogisticRegression(C=C, max_iter=2000).fit(X_multi, y_multi)
    coefs.append(m.coef_[0])
coefs = np.array(coefs)

plt.figure(figsize=(7, 4))
for i in range(coefs.shape[1]):
    plt.plot(Cs, coefs[:, i], label=f"w{i + 1}")
plt.xscale("log")
plt.axhline(0, color="gray", linewidth=0.5)
plt.xlabel("C (inverse of regularization strength)")
plt.ylabel("Coefficient value")
plt.title("L2 regularization: small C shrinks coefficients toward 0")
plt.legend(fontsize=8, ncol=2)
plt.tight_layout()
save("logistic-regression_regularization.svg")


# --- 図4: C=1.0 と C=0.001 の確率の校正（本文のコードと同じ計算） ---
from sklearn.calibration import calibration_curve
from sklearn.metrics import log_loss, roc_auc_score

rng = np.random.default_rng(0)
n = 20000
X = rng.normal(size=(n, 2))
z = 2.0 * X[:, 0] - 1.0 * X[:, 1] + 0.5
y = (rng.random(n) < 1 / (1 + np.exp(-z))).astype(int)
X_train, X_test = X[:10000], X[10000:]
y_train, y_test = y[:10000], y[10000:]

fig, ax = plt.subplots(figsize=(5.5, 5))
ax.plot([0, 1], [0, 1], "k--", alpha=0.5, label="perfectly calibrated")
for C in (1.0, 0.001):
    model = LogisticRegression(C=C).fit(X_train, y_train)
    p = model.predict_proba(X_test)[:, 1]
    w = model.coef_[0]
    print(f"C={C}: w={np.round(w, 3)}, b={model.intercept_[0]:.3f}, "
          f"odds ratio={np.round(np.exp(w), 2)}, "
          f"AUC={roc_auc_score(y_test, p):.3f}, "
          f"log loss={log_loss(y_test, p):.3f}")
    frac_pos, mean_pred = calibration_curve(y_test, p, n_bins=10)
    print("  mean_pred", np.round(mean_pred, 3), "frac_pos", np.round(frac_pos, 3))
    ax.plot(mean_pred, frac_pos, "o-", label=f"C={C}")
ax.set_xlabel("Predicted probability")
ax.set_ylabel("Observed positive rate")
ax.set_title("Calibration on test data")
ax.legend()
fig.tight_layout()
save("logistic-regression_calibration.svg")
