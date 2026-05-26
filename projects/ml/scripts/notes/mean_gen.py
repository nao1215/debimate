"""mean ノート用の図を生成するスクリプト。

実行: cd projects/ml && uv run python scripts/notes/mean_gen.py
"""
import os

import matplotlib.pyplot as plt
import numpy as np

COLOR_BLUE = "#7aa6c2"
COLOR_RED = "#e15759"
COLOR_GREEN = "#59a14f"
COLOR_GRAY = "#999999"

NOTE_DIR = os.path.expanduser(
    "~/ghq/github.com/nao1215/debimate/projects/ml/notes/math/mean"
)
os.makedirs(NOTE_DIR, exist_ok=True)


def save(name: str) -> None:
    plt.savefig(os.path.join(NOTE_DIR, name), bbox_inches="tight")
    plt.close()


# ============================================================
# Fig 1: Skewed distribution - mean vs median (existing figure)
# ============================================================
rng = np.random.default_rng(0)
values = rng.lognormal(mean=1.0, sigma=0.7, size=500)

plt.figure(figsize=(6, 4))
plt.hist(values, bins=30, color=COLOR_BLUE, edgecolor="white")
plt.axvline(values.mean(), color=COLOR_RED, linestyle="--", linewidth=2,
            label=f"mean = {values.mean():.2f}")
plt.axvline(np.median(values), color=COLOR_GREEN, linestyle="--", linewidth=2,
            label=f"median = {np.median(values):.2f}")
plt.title("Mean vs Median on a skewed distribution")
plt.xlabel("Value")
plt.ylabel("Count")
plt.legend()
plt.tight_layout()
save("mean_hist.svg")


# ============================================================
# Fig 2: Outlier injection - mean drifts, median stays
# ============================================================
base = rng.normal(50, 5, 50)
contaminated = np.concatenate([base, [500]])  # 1 extreme outlier

fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))

ax = axes[0]
ax.hist(base, bins=18, color=COLOR_BLUE, edgecolor="white", range=(20, 110))
ax.axvline(base.mean(), color=COLOR_RED, ls="--", lw=2,
           label=f"mean = {base.mean():.2f}")
ax.axvline(np.median(base), color=COLOR_GREEN, ls="--", lw=2,
           label=f"median = {np.median(base):.2f}")
ax.set_title("Clean sample (n=50)")
ax.set_xlabel("value")
ax.set_xlim(20, 110)
ax.legend(fontsize=9)
ax.grid(True, alpha=0.25, axis="y")

ax = axes[1]
ax.hist(contaminated, bins=18, color=COLOR_BLUE, edgecolor="white", range=(20, 110))
# Annotate the outlier as an arrow off the right edge
ax.annotate("outlier = 500\n(out of view)", xy=(108, 5), xytext=(80, 13),
            arrowprops=dict(arrowstyle="->", color=COLOR_RED), fontsize=9, color=COLOR_RED)
ax.axvline(contaminated.mean(), color=COLOR_RED, ls="--", lw=2,
           label=f"mean = {contaminated.mean():.2f} (+{contaminated.mean()-base.mean():.1f})")
ax.axvline(np.median(contaminated), color=COLOR_GREEN, ls="--", lw=2,
           label=f"median = {np.median(contaminated):.2f} (+{np.median(contaminated)-np.median(base):.2f})")
ax.set_title("With 1 outlier added (n=51)")
ax.set_xlabel("value")
ax.set_xlim(20, 110)
ax.legend(fontsize=9)
ax.grid(True, alpha=0.25, axis="y")

plt.suptitle("Adding one extreme value shifts the mean but barely moves the median",
             y=1.02)
plt.tight_layout()
save("mean_outlier_drift.svg")


# ============================================================
# Fig 3: Mean as the minimizer of squared error
# ============================================================
data = rng.normal(5.0, 1.5, 50)
mean_val = data.mean()
median_val = np.median(data)

cs = np.linspace(0, 10, 400)
mse = np.array([np.mean((data - c) ** 2) for c in cs])
mae = np.array([np.mean(np.abs(data - c)) for c in cs])

fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
ax = axes[0]
ax.plot(cs, mse, color=COLOR_BLUE, lw=2, label="MSE(c) = mean((x - c)^2)")
ax.axvline(mean_val, color=COLOR_RED, ls="--", lw=2,
           label=f"argmin = mean = {mean_val:.2f}")
ax.scatter([mean_val], [np.mean((data - mean_val) ** 2)], color=COLOR_RED, s=60, zorder=5)
ax.set_xlabel("candidate center c")
ax.set_ylabel("loss")
ax.set_title("Mean minimizes squared-error loss (L2)")
ax.legend()
ax.grid(True, alpha=0.25)

ax = axes[1]
ax.plot(cs, mae, color=COLOR_BLUE, lw=2, label="MAE(c) = mean(|x - c|)")
ax.axvline(median_val, color=COLOR_GREEN, ls="--", lw=2,
           label=f"argmin = median = {median_val:.2f}")
ax.scatter([median_val], [np.mean(np.abs(data - median_val))], color=COLOR_GREEN, s=60, zorder=5)
ax.set_xlabel("candidate center c")
ax.set_ylabel("loss")
ax.set_title("Median minimizes absolute-error loss (L1)")
ax.legend()
ax.grid(True, alpha=0.25)

plt.tight_layout()
save("mean_l2_vs_median_l1.svg")


print("done:", sorted(os.listdir(NOTE_DIR)))
