"""median ノート用の図を生成するスクリプト。

実行: cd projects/ml && uv run python scripts/notes/median_gen.py
"""
import os

import matplotlib.pyplot as plt
import numpy as np

COLOR_BLUE = "#7aa6c2"
COLOR_RED = "#e15759"
COLOR_GREEN = "#59a14f"
COLOR_ORANGE = "#f28e2b"

NOTE_DIR = os.path.expanduser(
    "~/ghq/github.com/nao1215/debimate/projects/ml/notes/math/median"
)
os.makedirs(NOTE_DIR, exist_ok=True)


def save(name):
    plt.savefig(os.path.join(NOTE_DIR, name), bbox_inches="tight")
    plt.close()


rng = np.random.default_rng(0)

# --- 図1: 外れ値追加前後の mean vs median ---
base = rng.normal(loc=10.0, scale=2.0, size=200)
outlier = np.concatenate([base, [100.0, 120.0, 95.0]])

fig, axes = plt.subplots(1, 2, figsize=(10, 3.5))

for ax, data, title in [(axes[0], base, "Without outliers"),
                         (axes[1], outlier, "With 3 large outliers")]:
    ax.hist(data, bins=30, color=COLOR_BLUE, edgecolor="white")
    m = data.mean()
    med = np.median(data)
    ax.axvline(m, color=COLOR_RED, linestyle="--", linewidth=2,
               label=f"mean = {m:.2f}")
    ax.axvline(med, color=COLOR_GREEN, linestyle="--", linewidth=2,
               label=f"median = {med:.2f}")
    ax.set_title(title)
    ax.set_xlabel("Value")
    ax.set_ylabel("Count")
    ax.legend(fontsize=9)
plt.tight_layout()
save("median_outlier_effect.svg")


# --- 図2: L1 損失と median, L2 損失と mean ---
data = np.array([2.0, 3.0, 4.0, 5.0, 20.0])
candidates = np.linspace(0, 25, 200)
l1 = np.array([np.abs(data - c).sum() for c in candidates])
l2 = np.array([((data - c) ** 2).sum() for c in candidates])

l1_min = candidates[l1.argmin()]
l2_min = candidates[l2.argmin()]

fig, axes = plt.subplots(1, 2, figsize=(9, 3.5))
axes[0].plot(candidates, l1, color=COLOR_BLUE, linewidth=2)
axes[0].axvline(l1_min, color=COLOR_RED, linestyle="--",
                label=f"argmin = {l1_min:.2f}  (median = {np.median(data):.0f})")
axes[0].set_title("L1 loss  Sum|x - c|")
axes[0].set_xlabel("candidate c")
axes[0].set_ylabel("loss")
axes[0].legend(fontsize=9)

axes[1].plot(candidates, l2, color=COLOR_GREEN, linewidth=2)
axes[1].axvline(l2_min, color=COLOR_RED, linestyle="--",
                label=f"argmin = {l2_min:.2f}  (mean = {data.mean():.1f})")
axes[1].set_title("L2 loss  Sum(x - c)^2")
axes[1].set_xlabel("candidate c")
axes[1].set_ylabel("loss")
axes[1].legend(fontsize=9)
plt.tight_layout()
save("median_l1_vs_l2.svg")

print("Mean:", base.mean(), "->", outlier.mean())
print("Median:", np.median(base), "->", np.median(outlier))


# --- 図3: Breakdown point - mean drifts smoothly, median holds until 50% ---
clean = rng.normal(50, 5, 100)
fractions = np.linspace(0, 0.55, 30)
mean_drift = []
median_drift = []
clean_mean = clean.mean()
clean_median = np.median(clean)
for frac in fractions:
    n_contam = int(round(len(clean) * frac))
    contaminated = clean.copy()
    if n_contam > 0:
        # Replace n_contam values with extreme outliers
        idx = rng.choice(len(clean), size=n_contam, replace=False)
        contaminated[idx] = 500.0
    mean_drift.append(contaminated.mean() - clean_mean)
    median_drift.append(np.median(contaminated) - clean_median)

plt.figure(figsize=(7, 4.5))
plt.plot(fractions * 100, mean_drift, "o-", color=COLOR_RED, lw=2, label="mean drift")
plt.plot(fractions * 100, median_drift, "s-", color=COLOR_GREEN, lw=2, label="median drift")
plt.axvline(50, color="black", ls=":", lw=1.5, label="median breakdown = 50%")
plt.xlabel("fraction of data replaced by extreme outlier (%)")
plt.ylabel("estimator drift from clean value")
plt.title("Breakdown point: median stays put until ~50% data is contaminated")
plt.legend()
plt.grid(True, alpha=0.25)
plt.tight_layout()
save("median_breakdown.svg")


# --- 図4: Quantile regression vs OLS on outlier-heavy data ---
from sklearn.linear_model import LinearRegression, QuantileRegressor

rng2 = np.random.default_rng(42)
n = 80
x_data = np.linspace(0, 10, n)
y_clean = 1.5 * x_data + 2.0 + rng2.normal(0, 1.5, n)
# Inject outliers on upper region
y_data = y_clean.copy()
outlier_idx = rng2.choice(n, size=10, replace=False)
y_data[outlier_idx] += rng2.uniform(15, 30, 10)

X = x_data.reshape(-1, 1)
ols = LinearRegression().fit(X, y_data)
qr = QuantileRegressor(quantile=0.5, alpha=0.0).fit(X, y_data)
x_grid = np.linspace(0, 10, 100).reshape(-1, 1)

plt.figure(figsize=(7.5, 4.5))
plt.scatter(x_data, y_data, color=COLOR_BLUE, alpha=0.6, label="data with outliers")
plt.plot(x_grid, ols.predict(x_grid), color=COLOR_RED, lw=2,
         label=f"OLS (mean): slope={ols.coef_[0]:.2f}")
plt.plot(x_grid, qr.predict(x_grid), color=COLOR_GREEN, lw=2,
         label=f"Median regression: slope={qr.coef_[0]:.2f}")
plt.plot(x_data, 1.5 * x_data + 2.0, color="black", ls=":", lw=1.5,
         label="true slope=1.5")
plt.xlabel("x"); plt.ylabel("y")
plt.title("OLS (mean-based) is pulled up by outliers, quantile regression holds the median line")
plt.legend()
plt.grid(True, alpha=0.25)
plt.tight_layout()
save("median_quantile_regression.svg")
