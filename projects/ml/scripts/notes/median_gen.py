"""median ノートの図と、本文に載せている数値を生成するスクリプト。

実行: cd projects/ml && uv run --frozen python scripts/notes/median_gen.py
出力先はこのファイルから見た projects/ml/notes/math/median/。
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.linear_model import LinearRegression, QuantileRegressor

NOTE_DIR = Path(__file__).resolve().parents[2] / "notes/math/median"
NOTE_DIR.mkdir(parents=True, exist_ok=True)

BLUE, RUST, GREEN, GRAY = "#45677d", "#a56045", "#587064", "#555555"
plt.rcParams.update({"font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9,
                     "legend.fontsize": 8, "svg.fonttype": "none",
                     "svg.hashsalt": "median", "axes.spines.top": False,
                     "axes.spines.right": False})


def save(name):
    plt.savefig(NOTE_DIR / name, bbox_inches="tight", metadata={"Date": None})
    # Remove trailing whitespace so `git diff --check` passes.
    _svg_path = Path(NOTE_DIR / name)
    if _svg_path.suffix == ".svg":
        _svg_path.write_text("\n".join(line.rstrip() for line in _svg_path.read_text().splitlines()) + "\n")
    plt.close()


# --- 図1: 外れ値追加前後の mean vs median ---
rng = np.random.default_rng(0)
base = rng.normal(loc=10.0, scale=2.0, size=200)
outlier = np.concatenate([base, [100.0, 120.0, 95.0]])
print(f"mean:   {base.mean():.2f} -> {outlier.mean():.2f}")
print(f"median: {np.median(base):.2f} -> {np.median(outlier):.2f}")

fig, axes = plt.subplots(1, 2, figsize=(9, 3.2))
for ax, data, title in [(axes[0], base, "Without outliers"),
                        (axes[1], outlier, "With 3 large outliers (95, 100, 120)")]:
    ax.hist(data, bins=30, color=BLUE, alpha=0.55, edgecolor="white")
    ax.axvline(data.mean(), color=RUST, ls="--", lw=1.8,
               label=f"mean = {data.mean():.2f}")
    ax.axvline(np.median(data), color=GREEN, ls="-", lw=1.8,
               label=f"median = {np.median(data):.2f}")
    ax.set_title(title)
    ax.set_xlabel("value")
    ax.set_ylabel("count")
    ax.legend()
axes[1].plot([95, 100, 120], [6, 6, 6], "v", color=RUST, ms=6)
axes[1].annotate("outliers", xy=(107, 14), ha="center", fontsize=8, color=RUST)
plt.tight_layout()
save("median_outlier_effect.svg")


# --- 図2: L1 損失と median, L2 損失と mean ---
data = np.array([2.0, 3.0, 4.0, 5.0, 20.0])
candidates = np.linspace(0, 25, 501)
l1 = np.array([np.abs(data - c).sum() for c in candidates])
l2 = np.array([((data - c) ** 2).sum() for c in candidates])
l1_min, l2_min = candidates[l1.argmin()], candidates[l2.argmin()]
print(f"L1 argmin = {l1_min:.2f} (median {np.median(data):.1f}), "
      f"L2 argmin = {l2_min:.2f} (mean {data.mean():.1f})")

fig, axes = plt.subplots(1, 2, figsize=(9, 3.2))
for ax, loss, cmin, title, label in [
        (axes[0], l1, l1_min, "L1 loss  sum |x - c|", f"argmin = {l1_min:.1f} (median)"),
        (axes[1], l2, l2_min, "L2 loss  sum (x - c)^2", f"argmin = {l2_min:.1f} (mean)")]:
    ax.plot(candidates, loss, color=BLUE, lw=1.8)
    ax.axvline(cmin, color=RUST, ls="--", lw=1.4, label=label)
    ax.set_title(title)
    ax.set_xlabel("candidate c")
    ax.set_ylabel("loss")
    ax.legend()
plt.tight_layout()
save("median_l1_vs_l2.svg")


# --- 図3: Breakdown point。100 個中 k 個を極端な値 v に置き換える ---
rng = np.random.default_rng(1)
clean = rng.normal(50, 5, 100)
order = rng.permutation(len(clean))  # 置き換える位置の順番（500 と 5000 で共通）
ks = np.arange(0, 56)


def drift(v):
    mean_d, median_d = [], []
    for k in ks:
        x = clean.copy()
        x[order[:k]] = v
        mean_d.append(x.mean() - clean.mean())
        median_d.append(np.median(x) - np.median(clean))
    return np.array(mean_d), np.array(median_d)


results = {v: drift(v) for v in (500.0, 5000.0)}
print("clean: max - median =", f"{clean.max() - np.median(clean):.2f}")
print("   k  mean(500) median(500)  mean(5000) median(5000)")
for k in (0, 10, 30, 49, 50):
    print(f"{k:4d} {results[500.0][0][k]:10.2f} {results[500.0][1][k]:11.2f}"
          f" {results[5000.0][0][k]:11.2f} {results[5000.0][1][k]:12.2f}")

fig, axes = plt.subplots(1, 2, figsize=(9, 3.4))
for v, ls in [(500.0, "-"), (5000.0, "--")]:
    mean_d, median_d = results[v]
    axes[0].plot(ks, mean_d, color=RUST, ls=ls, lw=1.6, label=f"replaced by {v:.0f}")
    axes[1].plot(ks, median_d, color=GREEN, ls=ls, lw=1.6, label=f"replaced by {v:.0f}")
axes[0].set_title("mean: drift grows with k and with the value")
axes[0].set_ylabel("drift from clean mean")
axes[1].set_title("median: same drift for 500 and 5000 up to k = 49")
axes[1].set_ylabel("drift from clean median")
axes[1].set_ylim(-1, 30)
axes[1].annotate(f"k = 50: +{results[500.0][1][50]:.0f} / +{results[5000.0][1][50]:.0f}",
                 xy=(50, 29), xytext=(18, 24), fontsize=8, color=GRAY,
                 arrowprops={"arrowstyle": "->", "color": GRAY})
for ax in axes:
    ax.axvline(50, color=GRAY, ls=":", lw=1)
    ax.set_xlabel("k: values replaced (out of 100)")
    ax.legend(loc="upper left" if ax is axes[0] else "center left")
plt.tight_layout()
save("median_breakdown.svg")


# --- 図4: Quantile regression vs OLS on outlier-heavy data ---
rng = np.random.default_rng(42)
x_data = np.linspace(0, 10, 80)
y_data = 1.5 * x_data + 2.0 + rng.normal(0, 1.5, 80)
idx = rng.choice(80, size=10, replace=False)
y_data[idx] += rng.uniform(15, 30, 10)
print("outlier x:", np.round(np.sort(x_data[idx]), 1))

X = x_data.reshape(-1, 1)
ols = LinearRegression().fit(X, y_data)
qr = QuantileRegressor(quantile=0.5, alpha=0.0).fit(X, y_data)
print(f"OLS: slope={ols.coef_[0]:.2f} intercept={ols.intercept_:.2f}")
print(f"QR : slope={qr.coef_[0]:.2f} intercept={qr.intercept_:.2f}")

x_grid = np.linspace(0, 10, 100).reshape(-1, 1)
plt.figure(figsize=(7, 4))
plt.scatter(x_data, y_data, color=BLUE, alpha=0.55, s=16, label="data (10 upward outliers)")
plt.plot(x_grid, ols.predict(x_grid), color=RUST, lw=1.8,
         label=f"OLS: slope={ols.coef_[0]:.2f}, intercept={ols.intercept_:.2f}")
plt.plot(x_grid, qr.predict(x_grid), color=GREEN, lw=1.8,
         label=f"median regression: slope={qr.coef_[0]:.2f}, intercept={qr.intercept_:.2f}")
plt.plot(x_data, 1.5 * x_data + 2.0, color=GRAY, ls=":", lw=1.4,
         label="true: slope=1.50, intercept=2.00")
plt.xlabel("x")
plt.ylabel("y")
plt.title("OLS is pulled toward the outliers, median regression stays near the true line")
plt.legend()
plt.grid(True, alpha=0.25)
plt.tight_layout()
save("median_quantile_regression.svg")
