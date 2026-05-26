"""kde ノート用の図を生成するスクリプト。

実行: cd projects/ml && uv run python scripts/notes/kde_gen.py
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
    "~/ghq/github.com/nao1215/debimate/projects/ml/notes/math/kde"
)
os.makedirs(NOTE_DIR, exist_ok=True)


def save(name: str) -> None:
    plt.savefig(os.path.join(NOTE_DIR, name), bbox_inches="tight")
    plt.close()


# ============================================================
# Fig 1: hist + simple KDE (existing)
# ============================================================
rng = np.random.default_rng(0)
data = rng.normal(loc=0, scale=1, size=500)

plt.hist(data, bins=20, density=True, alpha=0.4, color=COLOR_BLUE, label="hist")
xs = np.linspace(-4, 4, 200)
bandwidth = 0.4
kernel = np.exp(-0.5 * ((xs[:, None] - data[None, :]) / bandwidth) ** 2)
kde = kernel.mean(axis=1) / (bandwidth * (2 * np.pi) ** 0.5)
plt.plot(xs, kde, color=COLOR_ORANGE, label="kde")
plt.legend()
plt.tight_layout()
save("kde_example.svg")


# ============================================================
# Fig 2: bandwidth effect on KDE (under / good / over smoothing)
# ============================================================
rng2 = np.random.default_rng(0)
# Bimodal data
data_bimodal = np.concatenate([
    rng2.normal(-2.0, 0.8, 200),
    rng2.normal(2.0, 0.8, 200),
])
xs = np.linspace(-5, 5, 400)

fig, axes = plt.subplots(1, 3, figsize=(13, 4), sharey=True)
bws = [0.1, 0.5, 2.0]
titles = ["h=0.1 (under-smoothed, noisy)",
          "h=0.5 (good)",
          "h=2.0 (over-smoothed, peaks gone)"]

for ax, h, title in zip(axes, bws, titles):
    ax.hist(data_bimodal, bins=40, density=True, alpha=0.35, color=COLOR_BLUE)
    kde_func = stats.gaussian_kde(data_bimodal, bw_method=h / data_bimodal.std())
    ax.plot(xs, kde_func(xs), color=COLOR_RED, lw=2.2)
    ax.set_title(title, fontsize=10)
    ax.set_xlabel("x")
    ax.grid(True, alpha=0.25)
axes[0].set_ylabel("density")
plt.suptitle("Bandwidth controls smoothness — wrong h hides or invents structure", y=1.02)
plt.tight_layout()
save("kde_bandwidth.svg")


# ============================================================
# Fig 3: Per-point kernels stacked into KDE (intuition figure)
# ============================================================
rng3 = np.random.default_rng(5)
sample = rng3.normal(0, 1, 15)
xs = np.linspace(-4, 4, 400)
h = 0.5

plt.figure(figsize=(8.5, 4.5))
total = np.zeros_like(xs)
for xi in sample:
    k = np.exp(-0.5 * ((xs - xi) / h) ** 2) / (h * np.sqrt(2 * np.pi))
    k_norm = k / len(sample)
    plt.plot(xs, k_norm, color=COLOR_BLUE, alpha=0.5, lw=1)
    total += k_norm
    plt.scatter([xi], [0], color="black", s=30, zorder=5)
plt.plot(xs, total, color=COLOR_RED, lw=2.5, label="KDE = sum of all kernels / n")
plt.title("Each data point contributes a small Gaussian; their sum is the KDE")
plt.xlabel("x")
plt.ylabel("density")
plt.legend()
plt.grid(True, alpha=0.25)
plt.tight_layout()
save("kde_per_point_intuition.svg")


# ============================================================
# Fig 4: Class-conditional KDE for binary classification visualization
# ============================================================
rng4 = np.random.default_rng(2)
n = 600
# Feature 'age' for churn vs non-churn customers
class0 = rng4.normal(35, 8, int(n * 0.7))  # non-churn
class1 = rng4.normal(48, 10, int(n * 0.3))  # churn

xs = np.linspace(10, 80, 400)
kde0 = stats.gaussian_kde(class0)
kde1 = stats.gaussian_kde(class1)

plt.figure(figsize=(8, 4.5))
plt.plot(xs, kde0(xs), color=COLOR_BLUE, lw=2, label="class 0 (non-churn)")
plt.fill_between(xs, kde0(xs), alpha=0.3, color=COLOR_BLUE)
plt.plot(xs, kde1(xs), color=COLOR_RED, lw=2, label="class 1 (churn)")
plt.fill_between(xs, kde1(xs), alpha=0.3, color=COLOR_RED)
plt.xlabel("age")
plt.ylabel("density (per class)")
plt.title("Class-conditional KDE: see how the feature separates classes")
plt.legend()
plt.grid(True, alpha=0.25)
plt.tight_layout()
save("kde_class_conditional.svg")


print("done:", sorted(os.listdir(NOTE_DIR)))
