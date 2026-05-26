"""regression-metrics ノート用の図を生成するスクリプト。

実行: cd projects/ml && uv run python scripts/notes/regression-metrics_gen.py
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
    "~/ghq/github.com/nao1215/debimate/projects/ml/notes/ml/regression-metrics"
)
os.makedirs(NOTE_DIR, exist_ok=True)


def save(name: str) -> None:
    plt.savefig(os.path.join(NOTE_DIR, name), bbox_inches="tight")
    plt.close()


# ============================================================
# Fig 1: pred vs true scatter with RMSE/MAE/R²
# ============================================================
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.linear_model import LinearRegression
rng = np.random.default_rng(0)
n = 100
x = np.linspace(0, 10, n)
y = 2 * x + 1 + rng.normal(0, 2, n)
ols = LinearRegression().fit(x.reshape(-1, 1), y)
pred = ols.predict(x.reshape(-1, 1))

rmse = np.sqrt(mean_squared_error(y, pred))
mae = mean_absolute_error(y, pred)
r2 = r2_score(y, pred)

plt.figure(figsize=(7, 5.5))
plt.scatter(y, pred, color=COLOR_BLUE, alpha=0.6, s=30)
lims = [min(y.min(), pred.min()) - 1, max(y.max(), pred.max()) + 1]
plt.plot(lims, lims, color=COLOR_RED, lw=1.5, ls="--", label="y = ŷ (ideal)")
plt.xlim(lims); plt.ylim(lims)
plt.xlabel("true y"); plt.ylabel("predicted ŷ")
plt.title(f"True vs predicted\nRMSE = {rmse:.2f}, MAE = {mae:.2f}, R² = {r2:.3f}")
plt.legend()
plt.grid(True, alpha=0.25)
plt.gca().set_aspect("equal")
plt.tight_layout()
save("regmetrics_scatter.svg")


# ============================================================
# Fig 2: Effect of one outlier on RMSE vs MAE
# ============================================================
y_true = rng.normal(50, 5, 50)
pred_clean = y_true + rng.normal(0, 2, 50)

# Inject one big residual
pred_with_outlier = pred_clean.copy()
pred_with_outlier[0] = y_true[0] + 40  # huge miss on 1 point

scenarios = [
    ("Clean (50 small residuals)", y_true, pred_clean),
    ("With 1 large residual (+40 on 1 sample)", y_true, pred_with_outlier),
]

fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
for ax, (title, yt, yp) in zip(axes, scenarios):
    rmse_v = np.sqrt(mean_squared_error(yt, yp))
    mae_v = mean_absolute_error(yt, yp)
    residuals = yp - yt
    ax.hist(residuals, bins=20, color=COLOR_BLUE, edgecolor="white")
    ax.axvline(0, color="black", lw=1)
    ax.set_title(f"{title}\nRMSE = {rmse_v:.2f}, MAE = {mae_v:.2f}, "
                 f"ratio RMSE/MAE = {rmse_v/mae_v:.2f}", fontsize=10)
    ax.set_xlabel("residual ŷ - y")
    ax.set_ylabel("count")
    ax.grid(True, alpha=0.25, axis="y")
plt.suptitle("One large residual barely moves MAE but more than doubles RMSE", y=1.02)
plt.tight_layout()
save("regmetrics_outlier_sensitivity.svg")


# ============================================================
# Fig 3: R² visualized as 'variance explained / variance total'
# ============================================================
n3 = 80
x3 = np.linspace(0, 10, n3)
y3 = 1.0 * x3 + rng.normal(0, 1.5, n3)
m3 = LinearRegression().fit(x3.reshape(-1, 1), y3)
pred3 = m3.predict(x3.reshape(-1, 1))
ybar = y3.mean()

SS_tot = ((y3 - ybar) ** 2).sum()
SS_res = ((y3 - pred3) ** 2).sum()
SS_reg = ((pred3 - ybar) ** 2).sum()
r2_val = 1 - SS_res / SS_tot

fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))

ax = axes[0]
ax.scatter(x3, y3, color=COLOR_BLUE, alpha=0.6, s=30)
ax.axhline(ybar, color=COLOR_GREEN, lw=2, ls="--", label=f"ybar = {ybar:.2f} (baseline)")
ax.plot(x3, pred3, color=COLOR_RED, lw=2, label="model ŷ")
for xi, yi, pi in zip(x3, y3, pred3):
    ax.plot([xi, xi], [yi, pi], color=COLOR_GRAY, lw=0.5, alpha=0.5)
ax.set_xlabel("x"); ax.set_ylabel("y")
ax.set_title("Residual (y - ŷ) is what the model fails to explain")
ax.legend(fontsize=9)
ax.grid(True, alpha=0.25)

ax = axes[1]
bars = ax.bar(["SS_tot\n(total variance)", "SS_res\n(unexplained)", "SS_reg\n(explained)"],
              [SS_tot, SS_res, SS_reg],
              color=[COLOR_BLUE, COLOR_RED, COLOR_GREEN], edgecolor="white")
for b, v in zip(bars, [SS_tot, SS_res, SS_reg]):
    ax.text(b.get_x() + b.get_width() / 2, v + SS_tot * 0.02, f"{v:.1f}",
            ha="center", fontsize=10)
ax.set_ylabel("sum of squares")
ax.set_title(f"R² = 1 - SS_res / SS_tot = 1 - {SS_res:.1f} / {SS_tot:.1f} = {r2_val:.3f}")
ax.grid(True, alpha=0.25, axis="y")

plt.tight_layout()
save("regmetrics_r2_decomp.svg")


# ============================================================
# Fig 4: MAE vs MAPE: scale sensitivity
# ============================================================
# Tasks of very different magnitudes
n4 = 100
small_true = rng.uniform(10, 100, n4)
small_pred = small_true * (1 + rng.normal(0, 0.05, n4))  # ~5% relative error

big_true = rng.uniform(10000, 100000, n4)
big_pred = big_true * (1 + rng.normal(0, 0.05, n4))  # ~5% relative error

mae_small = mean_absolute_error(small_true, small_pred)
mae_big = mean_absolute_error(big_true, big_pred)
mape_small = np.mean(np.abs((small_true - small_pred) / small_true)) * 100
mape_big = np.mean(np.abs((big_true - big_pred) / big_true)) * 100

fig, ax = plt.subplots(figsize=(8, 4.5))
labels = ["small-scale task\n(true ∈ 10-100)", "big-scale task\n(true ∈ 10k-100k)"]
mae_vals = [mae_small, mae_big]
mape_vals = [mape_small, mape_big]
xpos = np.arange(len(labels))

ax2 = ax.twinx()
b1 = ax.bar(xpos - 0.2, mae_vals, width=0.4, color=COLOR_BLUE, label="MAE (abs unit)")
b2 = ax2.bar(xpos + 0.2, mape_vals, width=0.4, color=COLOR_RED, label="MAPE (%)")
for b, v in zip(b1, mae_vals):
    ax.text(b.get_x() + b.get_width() / 2, v, f"{v:.1f}",
            ha="center", va="bottom", fontsize=10, color=COLOR_BLUE)
for b, v in zip(b2, mape_vals):
    ax2.text(b.get_x() + b.get_width() / 2, v, f"{v:.1f}%",
             ha="center", va="bottom", fontsize=10, color=COLOR_RED)

ax.set_xticks(xpos); ax.set_xticklabels(labels)
ax.set_ylabel("MAE (absolute unit)", color=COLOR_BLUE)
ax2.set_ylabel("MAPE (% of true)", color=COLOR_RED)
ax.set_yscale("log")
ax.tick_params(axis="y", labelcolor=COLOR_BLUE)
ax2.tick_params(axis="y", labelcolor=COLOR_RED)
ax.set_title("MAE = absolute unit (scale-dependent), MAPE = relative (% of true)")
plt.tight_layout()
save("regmetrics_mae_vs_mape.svg")


print("done:", sorted(os.listdir(NOTE_DIR)))
