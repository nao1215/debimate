"""Generate the regularization figures. Run: uv run python scripts/notes/regularization_gen.py"""
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.datasets import make_regression
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import Lasso, LinearRegression, Ridge
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import PolynomialFeatures, StandardScaler

NOTE_DIR = Path(__file__).resolve().parents[2] / "notes/ml/regularization"
NOTE_DIR.mkdir(parents=True, exist_ok=True)
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
TRUE_C, MODEL_C, DATA_C, NOISE_C = "#5f8075", "#b5544f", "#537c91", "#b8b8b8"


def save(name):
    path = NOTE_DIR / name
    plt.savefig(path, bbox_inches="tight", metadata={"Date": None})
    plt.close()
    path.write_text("\n".join(line.rstrip() for line in path.read_text().splitlines()) + "\n")


# Figure 1: degree-15 polynomial + L2 with three alphas.
rng = np.random.default_rng(3)
x = np.sort(rng.uniform(-3, 3, 30))
truth = lambda v: np.sin(v) + 0.3 * v
y = truth(x) + rng.normal(0, 0.3, x.size)
grid = np.linspace(-3.2, 3.2, 400)
fig, axes = plt.subplots(1, 3, figsize=(10, 3.2), sharey=True)
for ax, (alpha, label) in zip(axes, [(0, "no regularization"), (0.1, "moderate"), (100, "too strong")]):
    reg = LinearRegression() if alpha == 0 else Ridge(alpha=alpha)
    model = make_pipeline(PolynomialFeatures(15, include_bias=False), StandardScaler(), reg).fit(x[:, None], y)
    ax.plot(grid, truth(grid), "--", color=TRUE_C, label="true function")
    ax.plot(grid, model.predict(grid[:, None]), color=MODEL_C, lw=2, label="model")
    ax.scatter(x, y, s=22, color=DATA_C, edgecolor="white", label="training data", zorder=3)
    ax.set_title(f"alpha={alpha} ({label})", fontsize=10)
    ax.set_xlabel("x")
    ax.set_ylim(-2.6, 2.6)
    ax.grid(alpha=0.3)
axes[0].set_ylabel("y")
axes[0].legend(fontsize=8, loc="lower right")
plt.tight_layout()
save("regularization_curves.svg")

# Figure 2: coefficient paths on the same data as the article's code block.
X, y, true_coef = make_regression(n_samples=200, n_features=20, n_informative=5,
                                  noise=15, random_state=0, coef=True)
X_tr, _, y_tr, _ = train_test_split(X, y, test_size=0.3, random_state=0)
informative = np.flatnonzero(true_coef)
settings = [("L1 (Lasso)", Lasso, np.logspace(-2, 2.5, 60)), ("L2 (Ridge)", Ridge, np.logspace(-2, 4.5, 60))]
fig, axes = plt.subplots(2, 2, figsize=(9, 5.6), sharex="col", gridspec_kw={"height_ratios": [3, 2]})
for col, (title, cls, alphas) in enumerate(settings):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ConvergenceWarning)
        paths = np.array([cls(alpha=a).fit(X_tr, y_tr).coef_ for a in alphas])
    top, bottom = axes[0, col], axes[1, col]
    for j in range(X.shape[1]):
        if j in informative:
            top.semilogx(alphas, paths[:, j], color=DATA_C, lw=1.8)
        else:
            bottom.semilogx(alphas, paths[:, j], color=NOISE_C, lw=1.2)
    top.set_title(title, fontsize=11)
    top.set_ylabel("coefficient\n(5 informative)")
    bottom.set_ylabel("coefficient\n(15 noise)")
    bottom.set_xlabel("alpha (log scale)")
    for ax in (top, bottom):
        ax.axhline(0, color="black", lw=0.6)
        ax.grid(alpha=0.3)
    nonzero = (paths != 0).sum(axis=1)
    print(title, "nonzero coefs by alpha:",
          {f"{a:.3g}": int(n) for a, n in zip(alphas[::6], nonzero[::6])})
plt.tight_layout()
save("regularization_l1_l2.svg")

# Values quoted in the article (Ridge does not shrink every coefficient by the same ratio).
ols = LinearRegression().fit(X_tr, y_tr).coef_
for a in [10, 100]:
    ratio = Ridge(alpha=a).fit(X_tr, y_tr).coef_ / ols
    print(f"Ridge alpha={a}: ratio informative={np.round(ratio[informative], 2)}  "
          f"feature1={ratio[1]:.2f} feature12={ratio[12]:.2f}")
