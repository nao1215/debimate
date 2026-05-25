"""bias-variance-tradeoff ノート用の図を生成するスクリプト。

実行: cd projects/ml && uv run python scripts/notes/bias-variance-tradeoff_gen.py

軸ラベル・タイトルは英語に統一する (matplotlib の日本語フォントが環境依存になるため)。
日本語解説は記事本文側で補う。
"""
import os

import matplotlib.pyplot as plt
import numpy as np
from sklearn.datasets import make_classification
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import learning_curve
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import PolynomialFeatures
from sklearn.tree import DecisionTreeClassifier

COLOR_BLUE = "#7aa6c2"
COLOR_RED = "#e15759"
COLOR_GREEN = "#59a14f"
COLOR_GRAY = "#999999"

NOTE_DIR = os.path.expanduser(
    "~/ghq/github.com/nao1215/debimate/projects/ml/notes/ml/bias-variance-tradeoff"
)
os.makedirs(NOTE_DIR, exist_ok=True)


def save(name: str) -> None:
    plt.savefig(os.path.join(NOTE_DIR, name), bbox_inches="tight")
    plt.close()


rng = np.random.default_rng(0)


def true_function(x: np.ndarray) -> np.ndarray:
    return np.sin(2 * np.pi * x) + 0.4 * x


# ============================================================
# Fig 1: Polynomial fit comparison (high bias / good / high variance)
# ============================================================
n_samples = 30
x_train = rng.uniform(0.0, 1.0, n_samples)
y_train = true_function(x_train) + rng.normal(0.0, 0.25, n_samples)

x_grid = np.linspace(0.0, 1.0, 200)
y_true_grid = true_function(x_grid)

degrees = [1, 3, 15]
titles = [
    "degree=1 (high bias: shape under-represented)",
    "degree=3 (just right)",
    "degree=15 (high variance: chasing noise)",
]

fig, axes = plt.subplots(1, 3, figsize=(12, 4), sharey=True)
for ax, deg, title in zip(axes, degrees, titles):
    model = make_pipeline(PolynomialFeatures(deg), LinearRegression())
    model.fit(x_train.reshape(-1, 1), y_train)
    y_pred = model.predict(x_grid.reshape(-1, 1))
    ax.scatter(x_train, y_train, color=COLOR_GRAY, s=22, label="observations")
    ax.plot(x_grid, y_true_grid, color=COLOR_GREEN, lw=2, ls="--", label="true function")
    ax.plot(x_grid, y_pred, color=COLOR_RED, lw=2, label=f"polynomial degree={deg}")
    ax.set_title(title, fontsize=10)
    ax.set_xlabel("x")
    ax.set_ylim(-1.6, 1.8)
    ax.grid(True, alpha=0.25)
axes[0].set_ylabel("y")
axes[0].legend(loc="lower right", fontsize=8)
plt.tight_layout()
save("polyfit_compare.svg")


# ============================================================
# Fig 2: Bias-Variance decomposition curve
# ============================================================
n_trials = 200
n_samples_inner = 25
x_test = np.linspace(0.05, 0.95, 50)
y_true_test = true_function(x_test)
noise_var = 0.25 ** 2

degree_range = list(range(1, 16))
bias_sq = []
variance = []
for d in degree_range:
    preds = np.zeros((n_trials, len(x_test)))
    for t in range(n_trials):
        x_tr = rng.uniform(0.0, 1.0, n_samples_inner)
        y_tr = true_function(x_tr) + rng.normal(0.0, 0.25, n_samples_inner)
        m = make_pipeline(PolynomialFeatures(d), LinearRegression())
        m.fit(x_tr.reshape(-1, 1), y_tr)
        preds[t] = m.predict(x_test.reshape(-1, 1))
    mean_pred = preds.mean(axis=0)
    bias_sq.append(np.mean((mean_pred - y_true_test) ** 2))
    variance.append(np.mean(preds.var(axis=0)))

bias_sq = np.array(bias_sq)
variance = np.array(variance)
total = bias_sq + variance + noise_var

display_cap = 1.5

fig, ax = plt.subplots(figsize=(7.5, 4.5))
ax.plot(degree_range, np.minimum(bias_sq, display_cap), color=COLOR_BLUE, lw=2, marker="o", label="Bias^2 (under-fit error)")
ax.plot(degree_range, np.minimum(variance, display_cap), color=COLOR_RED, lw=2, marker="s", label="Variance (sensitivity to training noise)")
ax.plot(degree_range, np.minimum(total, display_cap), color=COLOR_GREEN, lw=2.2, marker="^", label="Total = Bias^2 + Var + Noise")
ax.axhline(noise_var, color=COLOR_GRAY, ls=":", lw=1.2, label=f"Noise floor = {noise_var:.3f}")
ax.set_xlabel("Model complexity (polynomial degree)")
ax.set_ylabel("Expected test error (MSE)")
ax.set_title("Bias-Variance decomposition: complexity raises Var, lowers Bias")
ax.set_ylim(0, display_cap * 1.02)
ax.grid(True, alpha=0.25)
ax.legend(fontsize=9, loc="upper center")
plt.tight_layout()
save("decomposition_curve.svg")


# ============================================================
# Fig 3: Learning curves for high bias / good / high variance
# ============================================================
X, y = make_classification(
    n_samples=1500,
    n_features=20,
    n_informative=10,
    n_redundant=5,
    n_classes=2,
    random_state=0,
)

models = [
    ("high bias (depth=1)", DecisionTreeClassifier(max_depth=1, random_state=0)),
    ("just right (depth=6)", DecisionTreeClassifier(max_depth=6, random_state=0)),
    ("high variance (depth=None)", DecisionTreeClassifier(max_depth=None, random_state=0)),
]

fig, axes = plt.subplots(1, 3, figsize=(13, 4), sharey=True)
for ax, (title, est) in zip(axes, models):
    sizes, train_scores, val_scores = learning_curve(
        est,
        X,
        y,
        train_sizes=np.linspace(0.1, 1.0, 8),
        cv=5,
        scoring="accuracy",
        random_state=0,
    )
    train_mean = train_scores.mean(axis=1)
    val_mean = val_scores.mean(axis=1)
    train_std = train_scores.std(axis=1)
    val_std = val_scores.std(axis=1)
    ax.plot(sizes, train_mean, color=COLOR_BLUE, lw=2, marker="o", label="train accuracy")
    ax.fill_between(sizes, train_mean - train_std, train_mean + train_std, color=COLOR_BLUE, alpha=0.15)
    ax.plot(sizes, val_mean, color=COLOR_RED, lw=2, marker="s", label="validation accuracy")
    ax.fill_between(sizes, val_mean - val_std, val_mean + val_std, color=COLOR_RED, alpha=0.15)
    ax.set_title(title, fontsize=11)
    ax.set_xlabel("training sample size")
    ax.set_ylim(0.45, 1.02)
    ax.grid(True, alpha=0.25)
axes[0].set_ylabel("accuracy")
axes[0].legend(loc="lower right", fontsize=8)
plt.tight_layout()
save("learning_curves_diagnose.svg")


print("done:", os.listdir(NOTE_DIR))
