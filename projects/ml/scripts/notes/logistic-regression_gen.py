"""LogisticRegression ノート用の図を生成するスクリプト。

実行: cd projects/ml && uv run python scripts/notes/logistic-regression_gen.py
"""
import os

import matplotlib.pyplot as plt
import numpy as np
from sklearn.datasets import make_classification
from sklearn.linear_model import LogisticRegression

COLOR_BLUE = "#7aa6c2"
COLOR_RED = "#e15759"
COLOR_GREEN = "#59a14f"

NOTE_DIR = os.path.expanduser(
    "~/ghq/github.com/nao1215/debimate/projects/ml/notes/ml/logistic-regression"
)
os.makedirs(NOTE_DIR, exist_ok=True)


def save(name):
    plt.savefig(os.path.join(NOTE_DIR, name), bbox_inches="tight")
    plt.close()


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


# --- 図4: 確率出力の校正イメージ ---
np.random.seed(0)
true_p = np.linspace(0.05, 0.95, 10)
counts = np.random.binomial(100, true_p)
observed_p = counts / 100.0

plt.figure(figsize=(5.5, 5))
plt.plot([0, 1], [0, 1], "k--", alpha=0.5, label="perfectly calibrated")
plt.scatter(true_p, observed_p, color=COLOR_RED, s=60, label="bin")
plt.xlabel("Predicted probability")
plt.ylabel("Observed positive rate")
plt.title("Calibration plot (illustrative)")
plt.legend()
plt.tight_layout()
save("logistic-regression_calibration.svg")
