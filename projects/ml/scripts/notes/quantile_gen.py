"""quantile ノート用の図を生成するスクリプト。

実行: cd projects/ml && uv run python scripts/notes/quantile_gen.py
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
    "~/ghq/github.com/nao1215/debimate/projects/ml/notes/math/quantile"
)
os.makedirs(NOTE_DIR, exist_ok=True)


def save(name: str) -> None:
    plt.savefig(os.path.join(NOTE_DIR, name), bbox_inches="tight")
    plt.close()


# ============================================================
# Fig 1: Histogram with quartiles (existing)
# ============================================================
rng = np.random.default_rng(0)
values = rng.lognormal(mean=1.0, sigma=0.6, size=500)
q1, q2, q3 = np.quantile(values, [0.25, 0.5, 0.75])

plt.figure(figsize=(6, 4))
plt.hist(values, bins=30, color=COLOR_BLUE, edgecolor="white")
for q, label, color in [(q1, "Q1", COLOR_ORANGE), (q2, "Q2 (median)", COLOR_RED),
                          (q3, "Q3", COLOR_GREEN)]:
    plt.axvline(q, color=color, linestyle="--", linewidth=2)
    plt.text(q, plt.ylim()[1] * 0.9, label, rotation=90, va="top", ha="right", color=color)
plt.title("Histogram with Quartiles")
plt.xlabel("Value")
plt.ylabel("Count")
plt.tight_layout()
save("quartile_hist.svg")


# ============================================================
# Fig 2: Boxplot (existing)
# ============================================================
plt.figure(figsize=(6, 2.5))
plt.boxplot(values, vert=False, showmeans=True)
plt.title("Boxplot (Q1, median, Q3)")
plt.xlabel("Value")
plt.tight_layout()
save("quartile_box.svg")


# ============================================================
# Fig 3: IQR-based outlier rule visualization
# ============================================================
data_with_outliers = np.concatenate([
    rng.normal(50, 8, 200),
    [10, 15, 95, 110, 130]
])
q1, q3 = np.quantile(data_with_outliers, [0.25, 0.75])
iqr = q3 - q1
lo = q1 - 1.5 * iqr
hi = q3 + 1.5 * iqr

is_outlier = (data_with_outliers < lo) | (data_with_outliers > hi)

plt.figure(figsize=(9, 4.5))
plt.scatter(data_with_outliers[~is_outlier], np.zeros((~is_outlier).sum()) + 0.5,
            color=COLOR_BLUE, alpha=0.5, s=40, label=f"in-range ({(~is_outlier).sum()})")
plt.scatter(data_with_outliers[is_outlier], np.zeros(is_outlier.sum()) + 0.5,
            color=COLOR_RED, alpha=0.85, s=80, marker="x",
            label=f"outliers ({is_outlier.sum()})")

# Show IQR box
plt.axvspan(q1, q3, alpha=0.15, color=COLOR_GREEN, label=f"IQR [Q1={q1:.1f}, Q3={q3:.1f}]")
# Show fence
plt.axvline(lo, color=COLOR_RED, ls="--", lw=1.5)
plt.axvline(hi, color=COLOR_RED, ls="--", lw=1.5)
plt.text(lo, 0.85, f"Q1 - 1.5·IQR\n= {lo:.1f}", ha="right", color=COLOR_RED, fontsize=9)
plt.text(hi, 0.85, f"Q3 + 1.5·IQR\n= {hi:.1f}", ha="left", color=COLOR_RED, fontsize=9)
plt.yticks([])
plt.ylim(0, 1)
plt.xlabel("value")
plt.title("Tukey's IQR rule: anything outside [Q1−1.5·IQR, Q3+1.5·IQR] flagged as outlier")
plt.legend(loc="upper right", fontsize=9)
plt.grid(True, alpha=0.25, axis="x")
plt.tight_layout()
save("quantile_iqr_outliers.svg")


# ============================================================
# Fig 4: Quantile regression for prediction intervals
# ============================================================
from sklearn.ensemble import GradientBoostingRegressor

rng2 = np.random.default_rng(7)
n = 200
x = np.linspace(0, 10, n)
# Heteroscedastic noise: larger variance for larger x
y = np.sin(x) * 3 + 0.5 * x + rng2.normal(0, 0.2 + 0.3 * x, n)

X = x.reshape(-1, 1)
q_low = GradientBoostingRegressor(loss="quantile", alpha=0.1, n_estimators=100,
                                  max_depth=3, random_state=0).fit(X, y)
q_med = GradientBoostingRegressor(loss="quantile", alpha=0.5, n_estimators=100,
                                  max_depth=3, random_state=0).fit(X, y)
q_high = GradientBoostingRegressor(loss="quantile", alpha=0.9, n_estimators=100,
                                   max_depth=3, random_state=0).fit(X, y)
x_grid = np.linspace(0, 10, 400).reshape(-1, 1)

plt.figure(figsize=(8, 4.5))
plt.scatter(x, y, color=COLOR_BLUE, alpha=0.4, s=20, label="data")
plt.plot(x_grid, q_med.predict(x_grid), color=COLOR_RED, lw=2, label="median (q=0.5)")
plt.fill_between(x_grid.ravel(), q_low.predict(x_grid), q_high.predict(x_grid),
                 color=COLOR_GREEN, alpha=0.25, label="80% interval (q=0.1 – q=0.9)")
plt.xlabel("x"); plt.ylabel("y")
plt.title("Quantile regression: predict median + bracket of low/high quantiles")
plt.legend()
plt.grid(True, alpha=0.25)
plt.tight_layout()
save("quantile_regression_bands.svg")


print("done:", sorted(os.listdir(NOTE_DIR)))
