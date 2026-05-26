"""linear-regression ノート用の図を生成するスクリプト。

実行: cd projects/ml && uv run python scripts/notes/linear-regression_gen.py
"""
import os

import matplotlib.pyplot as plt
import numpy as np
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import PolynomialFeatures, StandardScaler

COLOR_BLUE = "#7aa6c2"
COLOR_RED = "#e15759"
COLOR_GREEN = "#59a14f"
COLOR_ORANGE = "#f28e2b"
COLOR_GRAY = "#999999"

NOTE_DIR = os.path.expanduser(
    "~/ghq/github.com/nao1215/debimate/projects/ml/notes/ml/linear-regression"
)
os.makedirs(NOTE_DIR, exist_ok=True)


def save(name: str) -> None:
    plt.savefig(os.path.join(NOTE_DIR, name), bbox_inches="tight")
    plt.close()


# ============================================================
# Fig 1: simple linear regression fit
# ============================================================
rng = np.random.default_rng(0)
n = 60
x = np.linspace(0, 10, n)
y_true_slope, y_true_intercept = 0.7, 1.5
y = y_true_slope * x + y_true_intercept + rng.normal(0, 1.2, n)

X = x.reshape(-1, 1)
ols = LinearRegression().fit(X, y)
pred = ols.predict(X)

plt.figure(figsize=(7, 4.5))
plt.scatter(x, y, color=COLOR_BLUE, alpha=0.7, s=35, label="data")
# residual segments
for xi, yi, pi in zip(x, y, pred):
    plt.plot([xi, xi], [yi, pi], color=COLOR_GRAY, lw=0.6, alpha=0.6)
plt.plot(x, pred, color=COLOR_RED, lw=2,
         label=f"OLS: ŷ = {ols.coef_[0]:.2f} x + {ols.intercept_:.2f}")
plt.plot(x, y_true_slope * x + y_true_intercept, color=COLOR_GREEN, lw=1.5, ls=":",
         label=f"true: y = {y_true_slope} x + {y_true_intercept}")
plt.xlabel("x"); plt.ylabel("y")
plt.title("Simple linear regression: OLS fit and per-point residuals")
plt.legend(fontsize=9)
plt.grid(True, alpha=0.25)
plt.tight_layout()
save("linreg_simple_fit.svg")


# ============================================================
# Fig 2: Polynomial degree comparison (underfit/just/overfit)
# ============================================================
rng2 = np.random.default_rng(0)
x_train = np.sort(rng2.uniform(0, 1, 25))
y_train = np.sin(2 * np.pi * x_train) + rng2.normal(0, 0.25, 25)
x_grid = np.linspace(0, 1, 400)
y_true = np.sin(2 * np.pi * x_grid)

degrees = [1, 3, 15]
titles = ["degree=1 (under-fit)", "degree=3 (just right)", "degree=15 (over-fit)"]
fig, axes = plt.subplots(1, 3, figsize=(13, 4), sharey=True)
for ax, deg, title in zip(axes, degrees, titles):
    model = make_pipeline(PolynomialFeatures(deg), LinearRegression())
    model.fit(x_train.reshape(-1, 1), y_train)
    y_pred = model.predict(x_grid.reshape(-1, 1))
    ax.scatter(x_train, y_train, color=COLOR_BLUE, s=25, alpha=0.7)
    ax.plot(x_grid, y_true, color=COLOR_GREEN, lw=1.5, ls=":", label="true")
    ax.plot(x_grid, y_pred, color=COLOR_RED, lw=2, label=f"polynomial deg={deg}")
    ax.set_ylim(-2, 2)
    ax.set_title(title, fontsize=10)
    ax.set_xlabel("x")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.25)
axes[0].set_ylabel("y")
plt.tight_layout()
save("linreg_poly_complexity.svg")


# ============================================================
# Fig 3: residual diagnostics - good vs heteroscedastic
# ============================================================
rng3 = np.random.default_rng(0)
n2 = 200
x2 = np.linspace(0, 10, n2)
# Good case: homoscedastic
y_good = 1.0 * x2 + 2 + rng3.normal(0, 1.0, n2)
# Bad case: heteroscedastic (variance grows with x)
y_bad = 1.0 * x2 + 2 + rng3.normal(0, 0.3 + 0.4 * x2, n2)

X2 = x2.reshape(-1, 1)
m_good = LinearRegression().fit(X2, y_good); resid_good = y_good - m_good.predict(X2)
m_bad = LinearRegression().fit(X2, y_bad); resid_bad = y_bad - m_bad.predict(X2)

fig, axes = plt.subplots(2, 2, figsize=(11, 6.5))
ax = axes[0, 0]
ax.scatter(x2, y_good, color=COLOR_BLUE, alpha=0.4, s=15)
ax.plot(x2, m_good.predict(X2), color=COLOR_RED, lw=2)
ax.set_title("Homoscedastic data + fit"); ax.set_xlabel("x"); ax.set_ylabel("y")
ax.grid(True, alpha=0.25)

ax = axes[0, 1]
ax.scatter(m_good.predict(X2), resid_good, color=COLOR_GREEN, alpha=0.4, s=15)
ax.axhline(0, color="black", ls="--")
ax.set_title("Residuals: uniform around 0 (good)")
ax.set_xlabel("fitted ŷ"); ax.set_ylabel("residual")
ax.grid(True, alpha=0.25)

ax = axes[1, 0]
ax.scatter(x2, y_bad, color=COLOR_BLUE, alpha=0.4, s=15)
ax.plot(x2, m_bad.predict(X2), color=COLOR_RED, lw=2)
ax.set_title("Heteroscedastic data + fit"); ax.set_xlabel("x"); ax.set_ylabel("y")
ax.grid(True, alpha=0.25)

ax = axes[1, 1]
ax.scatter(m_bad.predict(X2), resid_bad, color=COLOR_RED, alpha=0.4, s=15)
ax.axhline(0, color="black", ls="--")
ax.set_title("Residuals: fan-shaped (bad → fix with log y or weighted least squares)")
ax.set_xlabel("fitted ŷ"); ax.set_ylabel("residual")
ax.grid(True, alpha=0.25)

plt.tight_layout()
save("linreg_residual_diag.svg")


# ============================================================
# Fig 4: Ridge / Lasso coefficient shrinkage
# ============================================================
from sklearn.datasets import make_regression
rng4 = np.random.default_rng(0)
X_reg, y_reg, true_coef = make_regression(n_samples=80, n_features=20, n_informative=5,
                                           noise=10.0, random_state=0, coef=True)

alphas = np.logspace(-2, 2, 30)

# Ridge
ridge_coefs = np.zeros((len(alphas), X_reg.shape[1]))
for i, a in enumerate(alphas):
    m = make_pipeline(StandardScaler(), Ridge(alpha=a)).fit(X_reg, y_reg)
    ridge_coefs[i] = m[-1].coef_

# Lasso
lasso_coefs = np.zeros((len(alphas), X_reg.shape[1]))
for i, a in enumerate(alphas):
    m = make_pipeline(StandardScaler(), Lasso(alpha=a, max_iter=20000)).fit(X_reg, y_reg)
    lasso_coefs[i] = m[-1].coef_

fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))
for k in range(X_reg.shape[1]):
    color = COLOR_RED if true_coef[k] != 0 else COLOR_GRAY
    axes[0].plot(alphas, ridge_coefs[:, k], color=color, alpha=0.65, lw=1.3)
    axes[1].plot(alphas, lasso_coefs[:, k], color=color, alpha=0.65, lw=1.3)
for ax, title in zip(axes, ["Ridge (L2): all weights shrink smoothly",
                             "Lasso (L1): irrelevant weights collapse to 0"]):
    ax.set_xscale("log")
    ax.set_xlabel("regularization α (log scale)")
    ax.set_ylabel("coefficient")
    ax.set_title(title)
    ax.axhline(0, color="black", lw=0.5)
    ax.grid(True, alpha=0.25)
# Legend marker
from matplotlib.lines import Line2D
legend_elems = [
    Line2D([0], [0], color=COLOR_RED, lw=2, label="true informative (5 features)"),
    Line2D([0], [0], color=COLOR_GRAY, lw=2, label="true zero (15 features)"),
]
axes[0].legend(handles=legend_elems, fontsize=9, loc="upper right")
plt.tight_layout()
save("linreg_ridge_lasso.svg")


print("done:", sorted(os.listdir(NOTE_DIR)))
