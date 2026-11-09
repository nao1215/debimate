"""time-series-forecasting ノート用の図を生成するスクリプト。"""
import os
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

COLOR_BLUE, COLOR_RED, COLOR_GREEN, COLOR_ORANGE, COLOR_GRAY = \
    "#7aa6c2", "#e15759", "#59a14f", "#f28e2b", "#999999"

NOTE_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "notes", "ml", "time-series-forecasting"
)
os.makedirs(NOTE_DIR, exist_ok=True)


def save(name):
    plt.savefig(os.path.join(NOTE_DIR, name), bbox_inches="tight")
    plt.close()


# Synthetic monthly data: trend + seasonal + noise
rng = np.random.default_rng(0)
n_months = 60
t = np.arange(n_months)
trend = 100 + 0.8 * t
season = 15 * np.sin(2 * np.pi * t / 12)
noise = rng.normal(0, 4, n_months)
y = trend + season + noise

# ============================================================
# Fig 1: Classical decomposition (estimated vs true components)
# ============================================================
# 本文のコードと同じ古典的分解: 2x12 の中心化移動平均でトレンド、
# トレンドを引いた値の月ごとの平均で季節性、残りを残差とする
w = np.r_[0.5, np.ones(11), 0.5] / 12
trend_hat = np.full(n_months, np.nan)
trend_hat[6:-6] = np.convolve(y, w, mode="valid")
detrended = y - trend_hat
seasonal_by_month = np.array([np.nanmean(detrended[m::12]) for m in range(12)])
seasonal_by_month -= seasonal_by_month.mean()
seasonal_hat = seasonal_by_month[t % 12]
resid_hat = y - trend_hat - seasonal_hat

fig, axes = plt.subplots(4, 1, figsize=(11, 8), sharex=True)
axes[0].plot(t, y, color=COLOR_BLUE, lw=1.5)
axes[0].set_title("Observed")
axes[0].set_ylabel("y")
axes[1].plot(t, trend, color=COLOR_GRAY, lw=1.5, ls="--", label="true")
axes[1].plot(t, trend_hat, color=COLOR_GREEN, lw=2, label="estimated (moving average)")
axes[1].set_title("Trend")
axes[1].set_ylabel("trend")
axes[1].legend(loc="upper left", fontsize=9)
axes[2].plot(t, season, color=COLOR_GRAY, lw=1.5, ls="--", label="true")
axes[2].plot(t, seasonal_hat, color=COLOR_ORANGE, lw=2, label="estimated (monthly mean)")
axes[2].set_title("Seasonal (repeats every 12 months)")
axes[2].set_ylabel("seasonal")
axes[2].legend(loc="upper left", fontsize=9)
axes[3].plot(t, resid_hat, color=COLOR_RED, lw=1, alpha=0.8)
axes[3].axhline(0, color="black", lw=0.5)
axes[3].set_title("Residual (estimated; first and last 6 months are undefined)")
axes[3].set_ylabel("residual")
axes[3].set_xlabel("month")
for ax in axes:
    ax.grid(True, alpha=0.25)
plt.tight_layout()
save("ts_decomposition.svg")


# ============================================================
# Fig 2: Train/test split for time series (forward-only)
# ============================================================
fig, axes = plt.subplots(1, 2, figsize=(13, 4))

# Wrong: random split
ax = axes[0]
# 本文のコードと同じ train_test_split(test_size=12, random_state=0) の分割
from sklearn.model_selection import train_test_split
_, test_idx = train_test_split(t, test_size=12, random_state=0)
is_test = np.isin(t, test_idx)
ax.scatter(t[~is_test], y[~is_test], color=COLOR_BLUE, label="train", s=25)
ax.scatter(t[is_test], y[is_test], color=COLOR_RED, label="test", s=40, marker="x")
ax.set_title("WRONG: random split\n(future leaks into training)")
ax.set_xlabel("month"); ax.set_ylabel("y")
ax.legend(); ax.grid(True, alpha=0.25)

# Right: forward-only
ax = axes[1]
cutoff = 48
ax.scatter(t[:cutoff], y[:cutoff], color=COLOR_BLUE, label=f"train (months 0-{cutoff-1})",
            s=25)
ax.scatter(t[cutoff:], y[cutoff:], color=COLOR_RED, label=f"test (months {cutoff}-)",
            s=40, marker="x")
ax.axvline(cutoff - 0.5, color="black", ls="--", lw=1)
ax.set_title("RIGHT: forward-only split\n(predict future from past only)")
ax.set_xlabel("month"); ax.set_ylabel("y")
ax.legend(); ax.grid(True, alpha=0.25)

plt.tight_layout()
save("ts_train_test_split.svg")


# ============================================================
# Fig 3: Walk-forward / Expanding window CV
# ============================================================
fig, ax = plt.subplots(figsize=(12, 5))

n_splits = 5
total = 60
train_min = 20
test_size = 8

for fold in range(n_splits):
    train_end = train_min + fold * test_size
    test_start = train_end
    test_end = train_end + test_size
    if test_end > total:
        break
    ax.barh(fold, train_end, height=0.6, color=COLOR_BLUE, alpha=0.7,
            label="train" if fold == 0 else "")
    ax.barh(fold, test_size, left=test_start, height=0.6, color=COLOR_RED, alpha=0.7,
            label="test" if fold == 0 else "")

ax.set_yticks(range(n_splits))
ax.set_yticklabels([f"fold {i+1}" for i in range(n_splits)])
ax.set_xlabel("time")
ax.invert_yaxis()
ax.set_title("Walk-forward CV (expanding window):\ntraining grows, test always after train")
ax.legend(fontsize=10, loc="upper right")
ax.grid(True, alpha=0.25, axis="x")
plt.tight_layout()
save("ts_walkforward_cv.svg")


# ============================================================
# Fig 4: 3 models predicting future months
# ============================================================
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import GradientBoostingRegressor

# Predict last 12 months
train_end = 48
y_train = y[:train_end]
t_train = t[:train_end]
t_test = t[train_end:]
y_test = y[train_end:]

# Baseline: last value (naive)
naive_pred = np.full_like(y_test, y_train[-1], dtype=float)

# Linear trend model
lr = LinearRegression().fit(t_train.reshape(-1, 1), y_train)
lr_pred = lr.predict(t_test.reshape(-1, 1))

# Linear with seasonal (use month index)
features_train = np.column_stack([
    t_train,
    np.sin(2 * np.pi * t_train / 12),
    np.cos(2 * np.pi * t_train / 12),
])
features_test = np.column_stack([
    t_test,
    np.sin(2 * np.pi * t_test / 12),
    np.cos(2 * np.pi * t_test / 12),
])
season_lr = LinearRegression().fit(features_train, y_train)
season_pred = season_lr.predict(features_test)

plt.figure(figsize=(11, 4.5))
plt.plot(t_train, y_train, color=COLOR_BLUE, lw=1.5, label="train")
plt.plot(t_test, y_test, color="black", lw=1.5, ls="--", label="true future")
plt.plot(t_test, naive_pred, "o-", color=COLOR_GRAY, lw=1.5, alpha=0.7,
         label=f"naive (last value)  MAE={np.mean(np.abs(naive_pred-y_test)):.1f}")
plt.plot(t_test, lr_pred, "o-", color=COLOR_ORANGE, lw=1.5,
         label=f"linear trend  MAE={np.mean(np.abs(lr_pred-y_test)):.1f}")
plt.plot(t_test, season_pred, "o-", color=COLOR_RED, lw=1.5,
         label=f"trend + seasonal  MAE={np.mean(np.abs(season_pred-y_test)):.1f}")
plt.axvline(train_end - 0.5, color="black", ls=":", lw=1)
plt.xlabel("month"); plt.ylabel("y")
plt.title("Adding seasonal features beats a naive baseline")
plt.legend(loc="upper left", fontsize=9)
plt.grid(True, alpha=0.25)
plt.tight_layout()
save("ts_forecast_compare.svg")


print("done:", sorted(os.listdir(NOTE_DIR)))
