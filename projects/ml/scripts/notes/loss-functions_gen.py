"""loss-functions ノート用の図を生成するスクリプト。

実行: cd projects/ml && uv run python scripts/notes/loss-functions_gen.py
"""
import os

import matplotlib.pyplot as plt
import numpy as np

COLOR_BLUE = "#7aa6c2"
COLOR_RED = "#e15759"
COLOR_GREEN = "#59a14f"
COLOR_ORANGE = "#f28e2b"
COLOR_GRAY = "#999999"

NOTE_DIR = os.path.expanduser(
    "~/ghq/github.com/nao1215/debimate/projects/ml/notes/ml/loss-functions"
)
os.makedirs(NOTE_DIR, exist_ok=True)


def save(name: str) -> None:
    plt.savefig(os.path.join(NOTE_DIR, name), bbox_inches="tight")
    plt.close()


# ============================================================
# Fig 1: MSE / MAE / Huber loss shapes vs residual
# ============================================================
r = np.linspace(-3, 3, 400)
mse = r ** 2
mae = np.abs(r)
def huber(r, delta=1.0):
    out = np.where(np.abs(r) <= delta, 0.5 * r ** 2, delta * (np.abs(r) - 0.5 * delta))
    return out

plt.figure(figsize=(8, 4.5))
plt.plot(r, mse, color=COLOR_BLUE, lw=2.2, label="MSE: r^2 (quadratic)")
plt.plot(r, mae, color=COLOR_RED, lw=2.2, label="MAE: |r| (linear)")
plt.plot(r, huber(r, delta=1.0), color=COLOR_GREEN, lw=2.2,
         label="Huber (δ=1): quadratic near 0, linear far away")
plt.axhline(0, color=COLOR_GRAY, lw=0.5)
plt.axvline(0, color=COLOR_GRAY, lw=0.5)
plt.xlabel("residual r = y - ŷ")
plt.ylabel("loss")
plt.title("Regression losses: MSE penalizes large residuals quadratically")
plt.legend(fontsize=9)
plt.grid(True, alpha=0.25)
plt.ylim(0, 7)
plt.tight_layout()
save("loss_regression_shapes.svg")


# ============================================================
# Fig 2: MSE gradient (= residual itself) vs MAE gradient (= sign)
# ============================================================
fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))

ax = axes[0]
ax.plot(r, mse, color=COLOR_BLUE, lw=2, label="MSE = r^2")
ax.plot(r, 2 * r, color=COLOR_RED, lw=2, ls="--", label="dMSE/dr = 2r")
ax.axhline(0, color=COLOR_GRAY, lw=0.5)
ax.set_xlabel("residual r"); ax.set_ylabel("value")
ax.set_title("MSE: gradient grows with residual → outliers dominate")
ax.legend(fontsize=9)
ax.grid(True, alpha=0.25)

ax = axes[1]
ax.plot(r, mae, color=COLOR_BLUE, lw=2, label="MAE = |r|")
ax.plot(r, np.sign(r), color=COLOR_RED, lw=2, ls="--", label="dMAE/dr = sign(r)")
ax.axhline(0, color=COLOR_GRAY, lw=0.5)
ax.set_xlabel("residual r"); ax.set_ylabel("value")
ax.set_title("MAE: gradient is constant ±1 → outliers don't blow up")
ax.legend(fontsize=9)
ax.grid(True, alpha=0.25)

plt.tight_layout()
save("loss_gradient_behavior.svg")


# ============================================================
# Fig 3: Cross-entropy loss for binary classification
# ============================================================
p = np.linspace(0.001, 0.999, 400)
ce_pos = -np.log(p)        # true label = 1
ce_neg = -np.log(1 - p)    # true label = 0

plt.figure(figsize=(8.5, 4.5))
plt.plot(p, ce_pos, color=COLOR_BLUE, lw=2.2, label="true y=1: -log(p)")
plt.plot(p, ce_neg, color=COLOR_RED, lw=2.2, label="true y=0: -log(1 - p)")
plt.axvline(0.5, color=COLOR_GRAY, lw=0.5, ls=":")
plt.xlabel("predicted probability p")
plt.ylabel("loss = - log probability of true label")
plt.title("Binary cross-entropy: confident wrong predictions get infinite loss")
plt.ylim(0, 6)
plt.legend(fontsize=9)
plt.grid(True, alpha=0.25)
plt.tight_layout()
save("loss_cross_entropy.svg")


# ============================================================
# Fig 4: MSE vs MAE on outlier-laden regression
# ============================================================
from sklearn.linear_model import LinearRegression
rng = np.random.default_rng(0)

n = 80
x = np.linspace(0, 10, n)
y_clean = 1.5 * x + 2.0 + rng.normal(0, 1.0, n)
y = y_clean.copy()
y[rng.choice(n, 8, replace=False)] += rng.uniform(15, 30, 8)

X = x.reshape(-1, 1)
ols = LinearRegression().fit(X, y)  # minimizes MSE

# MAE-minimization via quantile regression at q=0.5
from sklearn.linear_model import QuantileRegressor
mae = QuantileRegressor(quantile=0.5, alpha=0.0).fit(X, y)

x_grid = np.linspace(0, 10, 200).reshape(-1, 1)
plt.figure(figsize=(8, 4.5))
plt.scatter(x, y, color=COLOR_BLUE, alpha=0.5, s=30, label="data (with outliers)")
plt.plot(x, 1.5 * x + 2.0, color="black", ls=":", lw=1.5, label="true line (slope=1.5)")
plt.plot(x_grid, ols.predict(x_grid), color=COLOR_RED, lw=2,
         label=f"MSE fit: slope={ols.coef_[0]:.2f} (pulled up by outliers)")
plt.plot(x_grid, mae.predict(x_grid), color=COLOR_GREEN, lw=2,
         label=f"MAE fit: slope={mae.coef_[0]:.2f} (robust)")
plt.xlabel("x"); plt.ylabel("y")
plt.title("Loss choice changes the model: MSE bends toward outliers, MAE ignores them")
plt.legend(fontsize=9)
plt.grid(True, alpha=0.25)
plt.tight_layout()
save("loss_mse_vs_mae_fit.svg")


print("done:", sorted(os.listdir(NOTE_DIR)))
