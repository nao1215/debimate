"""skewness ノート用の図を生成するスクリプト。

実行: cd projects/ml && uv run python scripts/notes/skewness_gen.py
"""
import os

import matplotlib.pyplot as plt
import numpy as np
from scipy import stats

COLOR_BLUE = "#7aa6c2"
COLOR_RED = "#e15759"
COLOR_GREEN = "#59a14f"
COLOR_ORANGE = "#f28e2b"

NOTE_DIR = os.path.expanduser(
    "~/ghq/github.com/nao1215/debimate/projects/ml/notes/math/skewness"
)
os.makedirs(NOTE_DIR, exist_ok=True)


def save(name: str) -> None:
    plt.savefig(os.path.join(NOTE_DIR, name), bbox_inches="tight")
    plt.close()


# ============================================================
# Fig 1: log1p transformation (existing)
# ============================================================
rng = np.random.default_rng(0)
raw = rng.lognormal(mean=1.0, sigma=0.8, size=1000)
log1p_vals = np.log1p(raw)

fig, axes = plt.subplots(1, 2, figsize=(9, 3.5))
axes[0].hist(raw, bins=30, color=COLOR_BLUE, edgecolor="white")
axes[0].set_title(f"Original (skewness={stats.skew(raw):.2f})")
axes[0].set_xlabel("value")
axes[1].hist(log1p_vals, bins=30, color=COLOR_ORANGE, edgecolor="white")
axes[1].set_title(f"After log1p (skewness={stats.skew(log1p_vals):.2f})")
axes[1].set_xlabel("log1p(value)")
plt.tight_layout()
save("skewness_log1p.svg")


# ============================================================
# Fig 2: positive / symmetric / negative skew, with mean & median
# ============================================================
rng2 = np.random.default_rng(0)
n = 5000
right = rng2.lognormal(0.0, 0.6, n)
sym = rng2.normal(2.0, 0.8, n)
left = -rng2.lognormal(0.0, 0.6, n) + np.exp(2)

datasets = [
    ("Right-skewed (positive)\nlognormal", right),
    ("Symmetric (≈ 0)\nnormal", sym),
    ("Left-skewed (negative)\nflipped lognormal", left),
]
fig, axes = plt.subplots(1, 3, figsize=(13, 4), sharey=True)
for ax, (title, data) in zip(axes, datasets):
    ax.hist(data, bins=40, color=COLOR_BLUE, alpha=0.6, edgecolor="white")
    m = data.mean()
    med = np.median(data)
    ax.axvline(m, color=COLOR_RED, ls="--", lw=2, label=f"mean = {m:.2f}")
    ax.axvline(med, color=COLOR_GREEN, ls="--", lw=2, label=f"median = {med:.2f}")
    sk = stats.skew(data)
    ax.set_title(f"{title}\nskewness = {sk:+.2f}", fontsize=10)
    ax.set_xlabel("value")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.25)
axes[0].set_ylabel("count")
plt.tight_layout()
save("skewness_sign_compare.svg")


# ============================================================
# Fig 3: log-transformation improves linear regression residuals
# ============================================================
from sklearn.linear_model import LinearRegression

rng3 = np.random.default_rng(3)
n = 300
# Houses price-like: positive area, multiplicative noise → right-skewed
area = rng3.uniform(30, 200, n)
true_log_price = 1.0 + 0.015 * area + rng3.normal(0, 0.25, n)
price = np.exp(true_log_price)  # right-skewed target

X = area.reshape(-1, 1)

ols_raw = LinearRegression().fit(X, price)
pred_raw = ols_raw.predict(X)
resid_raw = price - pred_raw

ols_log = LinearRegression().fit(X, np.log1p(price))
pred_log = ols_log.predict(X)
resid_log = np.log1p(price) - pred_log

fig, axes = plt.subplots(2, 2, figsize=(12, 7))

# raw scale
ax = axes[0, 0]
ax.scatter(area, price, alpha=0.45, color=COLOR_BLUE, s=18)
xs = np.linspace(30, 200, 100).reshape(-1, 1)
ax.plot(xs, ols_raw.predict(xs), color=COLOR_RED, lw=2, label="OLS on raw y")
ax.set_xlabel("area"); ax.set_ylabel("price")
ax.set_title(f"Raw target y (skew={stats.skew(price):.2f})")
ax.legend(fontsize=9)
ax.grid(True, alpha=0.25)

ax = axes[0, 1]
ax.scatter(pred_raw, resid_raw, alpha=0.45, color=COLOR_RED, s=18)
ax.axhline(0, color="black", ls="--")
ax.set_xlabel("fitted value"); ax.set_ylabel("residual")
ax.set_title("Residuals on raw y: fan-shape (heteroscedastic)")
ax.grid(True, alpha=0.25)

# log scale
ax = axes[1, 0]
ax.scatter(area, np.log1p(price), alpha=0.45, color=COLOR_BLUE, s=18)
ax.plot(xs, ols_log.predict(xs), color=COLOR_GREEN, lw=2, label="OLS on log1p(y)")
ax.set_xlabel("area"); ax.set_ylabel("log1p(price)")
ax.set_title(f"log1p target (skew={stats.skew(np.log1p(price)):.2f})")
ax.legend(fontsize=9)
ax.grid(True, alpha=0.25)

ax = axes[1, 1]
ax.scatter(pred_log, resid_log, alpha=0.45, color=COLOR_GREEN, s=18)
ax.axhline(0, color="black", ls="--")
ax.set_xlabel("fitted value"); ax.set_ylabel("residual")
ax.set_title("Residuals on log1p(y): roughly uniform")
ax.grid(True, alpha=0.25)

plt.suptitle("log1p variable transformation flattens residual pattern (a common reason to use it)",
             y=1.02, fontsize=11)
plt.tight_layout()
save("skewness_residual_diag.svg")


print("done:", sorted(os.listdir(NOTE_DIR)))
