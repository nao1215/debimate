"""correlation ノート用の図を生成するスクリプト。

実行: cd projects/ml && uv run python scripts/notes/correlation_gen.py
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
    "~/ghq/github.com/nao1215/debimate/projects/ml/notes/math/correlation"
)
os.makedirs(NOTE_DIR, exist_ok=True)


def save(name: str) -> None:
    plt.savefig(os.path.join(NOTE_DIR, name), bbox_inches="tight")
    plt.close()


# ============================================================
# Fig 1: Pearson correlation - positive/none/negative (existing)
# ============================================================
rng = np.random.default_rng(0)
n = 200

x1 = rng.normal(size=n); y1 = 0.8 * x1 + rng.normal(scale=0.4, size=n)
x2 = rng.normal(size=n); y2 = rng.normal(size=n)
x3 = rng.normal(size=n); y3 = -0.8 * x3 + rng.normal(scale=0.4, size=n)

fig, axes = plt.subplots(1, 3, figsize=(10, 3.3), sharex=True, sharey=True)
for ax, x, y, title in [(axes[0], x1, y1, "Positive"),
                          (axes[1], x2, y2, "None"),
                          (axes[2], x3, y3, "Negative")]:
    ax.scatter(x, y, s=10, alpha=0.7, color=COLOR_BLUE)
    r = np.corrcoef(x, y)[0, 1]
    ax.set_title(f"{title} (r={r:+.2f})")
    ax.grid(True, alpha=0.25)
plt.tight_layout()
save("correlation_scatter.svg")


# ============================================================
# Fig 2: Spearman / Kendall on monotonic nonlinear (existing)
# ============================================================
rng2 = np.random.default_rng(0)
x = rng2.normal(size=200)
y = x ** 3 + rng2.normal(scale=1.0, size=200)

r_p, _ = stats.pearsonr(x, y)
r_s, _ = stats.spearmanr(x, y)
r_k, _ = stats.kendalltau(x, y)

plt.figure(figsize=(7, 4))
plt.scatter(x, y, s=12, alpha=0.7, color=COLOR_BLUE)
plt.title(f"Monotonic (nonlinear): Pearson={r_p:.2f}, Spearman={r_s:.2f}, Kendall={r_k:.2f}")
plt.xlabel("x"); plt.ylabel("y")
plt.grid(True, alpha=0.25)
plt.tight_layout()
save("correlation_spearman_kendall.svg")


# ============================================================
# Fig 3: Anscombe's quartet - same r, totally different shapes
# ============================================================
# Anscombe's quartet (1973): 4 datasets all have r = 0.816, mean(x) = 9.0, mean(y) = 7.5
x_common = np.array([10, 8, 13, 9, 11, 14, 6, 4, 12, 7, 5], dtype=float)

ds = [
    ("I (clean)", x_common,
     np.array([8.04, 6.95, 7.58, 8.81, 8.33, 9.96, 7.24, 4.26, 10.84, 4.82, 5.68])),
    ("II (curved)", x_common,
     np.array([9.14, 8.14, 8.74, 8.77, 9.26, 8.10, 6.13, 3.10, 9.13, 7.26, 4.74])),
    ("III (outlier on linear)", x_common,
     np.array([7.46, 6.77, 12.74, 7.11, 7.81, 8.84, 6.08, 5.39, 8.15, 6.42, 5.73])),
    ("IV (single outlier dominates)",
     np.array([8, 8, 8, 8, 8, 8, 8, 19, 8, 8, 8], dtype=float),
     np.array([6.58, 5.76, 7.71, 8.84, 8.47, 7.04, 5.25, 12.50, 5.56, 7.91, 6.89])),
]

fig, axes = plt.subplots(2, 2, figsize=(11, 7), sharex=False, sharey=False)
for ax, (title, x_, y_) in zip(axes.ravel(), ds):
    ax.scatter(x_, y_, color=COLOR_BLUE, s=40, alpha=0.85)
    # Fit line
    slope, intercept = np.polyfit(x_, y_, 1)
    xs_line = np.linspace(0, 20, 100)
    ax.plot(xs_line, slope * xs_line + intercept, color=COLOR_RED, lw=1.5, ls="--")
    r = np.corrcoef(x_, y_)[0, 1]
    ax.set_title(f"{title}\nr = {r:.3f}, slope = {slope:.2f}", fontsize=10)
    ax.set_xlim(0, 20); ax.set_ylim(2, 14)
    ax.grid(True, alpha=0.25)
plt.suptitle("Anscombe's quartet: 4 datasets, all r ≈ 0.816, but the shapes are totally different\n"
             "→ always plot the data, do not trust a single number", y=1.0, fontsize=11)
plt.tight_layout()
save("correlation_anscombe.svg")


# ============================================================
# Fig 4: Correlation matrix heatmap on multi-feature data
# ============================================================
from sklearn.datasets import load_iris

iris = load_iris(as_frame=True)
df = iris.frame.iloc[:, :4]  # 4 features
corr = df.corr()

plt.figure(figsize=(6.5, 5))
im = plt.imshow(corr, cmap="RdBu_r", vmin=-1, vmax=1)
plt.colorbar(im, label="Pearson r")
for i in range(corr.shape[0]):
    for j in range(corr.shape[1]):
        plt.text(j, i, f"{corr.iat[i, j]:.2f}",
                 ha="center", va="center",
                 color="white" if abs(corr.iat[i, j]) > 0.5 else "black",
                 fontsize=9)
plt.xticks(range(4), df.columns, rotation=30, ha="right")
plt.yticks(range(4), df.columns)
plt.title("Correlation matrix heatmap (iris features)")
plt.tight_layout()
save("correlation_matrix_heatmap.svg")


print("done:", sorted(os.listdir(NOTE_DIR)))
