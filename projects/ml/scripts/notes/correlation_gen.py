"""correlation ノート用の図を生成するスクリプト。

実行: cd projects/ml && uv run python scripts/notes/correlation_gen.py
図はこのスクリプトから見た ../../notes/math/correlation/ に保存する。
本文に載せた数値は、各図のタイトルと同じ計算で出している。
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy import stats
from sklearn.datasets import load_iris

COLOR_BLUE = "#7aa6c2"
COLOR_RED = "#e15759"

NOTE_DIR = Path(__file__).resolve().parents[2] / "notes" / "math" / "correlation"
NOTE_DIR.mkdir(parents=True, exist_ok=True)


def save(name: str) -> None:
    plt.savefig(NOTE_DIR / name, bbox_inches="tight")
    # Remove trailing whitespace so `git diff --check` passes.
    _svg_path = Path(NOTE_DIR / name)
    if _svg_path.suffix == ".svg":
        _svg_path.write_text("\n".join(line.rstrip() for line in _svg_path.read_text().splitlines()) + "\n")
    plt.close()


def three(x, y):
    return (stats.pearsonr(x, y)[0], stats.spearmanr(x, y)[0],
            stats.kendalltau(x, y)[0])


# ============================================================
# Fig 1: Pearson correlation - positive/none/negative
# ============================================================
rng = np.random.default_rng(0)
n = 200
x1 = rng.normal(size=n)
y1 = 0.8 * x1 + rng.normal(scale=0.4, size=n)
x2 = rng.normal(size=n)
y2 = rng.normal(size=n)
x3 = rng.normal(size=n)
y3 = -0.8 * x3 + rng.normal(scale=0.4, size=n)

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
# Fig 2: Pearson vs Spearman / Kendall
#   (a) monotonic but curved, (b) one outlier flips Pearson's sign
# ============================================================
rng = np.random.default_rng(0)
xa = rng.normal(size=200)
ya = np.exp(2 * xa)

rng = np.random.default_rng(0)
xb = rng.normal(size=30)
yb = xb + rng.normal(scale=0.5, size=30)
xb_out = np.append(xb, 10.0)
yb_out = np.append(yb, -10.0)

fig, axes = plt.subplots(1, 2, figsize=(10, 4))
p, s, k = three(xa, ya)
axes[0].scatter(xa, ya, s=12, alpha=0.7, color=COLOR_BLUE)
axes[0].set_title(f"(a) y = exp(2x)\nPearson={p:.2f}, Spearman={s:.2f}, Kendall={k:.2f}",
                  fontsize=10)
p0, _, _ = three(xb, yb)
p, s, k = three(xb_out, yb_out)
axes[1].scatter(xb, yb, s=16, alpha=0.8, color=COLOR_BLUE, label="30 points")
axes[1].scatter([10.0], [-10.0], s=40, color=COLOR_RED, label="1 outlier")
axes[1].set_title(f"(b) 30 points (Pearson={p0:.2f}) + 1 outlier\n"
                  f"Pearson={p:.2f}, Spearman={s:.2f}, Kendall={k:.2f}", fontsize=10)
axes[1].legend(loc="lower left", fontsize=9)
for ax in axes:
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.grid(True, alpha=0.25)
plt.tight_layout()
save("correlation_spearman_kendall.svg")


# ============================================================
# Fig 3: Anscombe's quartet - same r, totally different shapes
# ============================================================
# Anscombe (1973): 4 datasets share r = 0.816, mean(x) = 9.0, mean(y) = 7.5
x_common = np.array([10, 8, 13, 9, 11, 14, 6, 4, 12, 7, 5], dtype=float)
ds = [
    ("I", x_common,
     np.array([8.04, 6.95, 7.58, 8.81, 8.33, 9.96, 7.24, 4.26, 10.84, 4.82, 5.68])),
    ("II", x_common,
     np.array([9.14, 8.14, 8.74, 8.77, 9.26, 8.10, 6.13, 3.10, 9.13, 7.26, 4.74])),
    ("III", x_common,
     np.array([7.46, 6.77, 12.74, 7.11, 7.81, 8.84, 6.08, 5.39, 8.15, 6.42, 5.73])),
    ("IV", np.array([8, 8, 8, 8, 8, 8, 8, 19, 8, 8, 8], dtype=float),
     np.array([6.58, 5.76, 7.71, 8.84, 8.47, 7.04, 5.25, 12.50, 5.56, 7.91, 6.89])),
]

fig, axes = plt.subplots(2, 2, figsize=(11, 7))
for ax, (title, x_, y_) in zip(axes.ravel(), ds):
    ax.scatter(x_, y_, color=COLOR_BLUE, s=40, alpha=0.85)
    slope, intercept = np.polyfit(x_, y_, 1)
    xs_line = np.linspace(0, 20, 100)
    ax.plot(xs_line, slope * xs_line + intercept, color=COLOR_RED, lw=1.5, ls="--")
    r = np.corrcoef(x_, y_)[0, 1]
    ax.set_title(f"{title}: r = {r:.3f}, slope = {slope:.2f}", fontsize=10)
    ax.set_xlim(0, 20)
    ax.set_ylim(2, 14)
    ax.grid(True, alpha=0.25)
plt.suptitle("Anscombe's quartet: r ≈ 0.82 in all four, but the shapes differ", fontsize=11)
plt.tight_layout()
save("correlation_anscombe.svg")


# ============================================================
# Fig 4: Correlation matrix heatmap on iris
# ============================================================
df = load_iris(as_frame=True).frame.iloc[:, :4]
df.columns = ["sepal_len", "sepal_wid", "petal_len", "petal_wid"]
corr = df.corr()

plt.figure(figsize=(6.5, 5))
im = plt.imshow(corr, cmap="RdBu_r", vmin=-1, vmax=1)
plt.colorbar(im, label="Pearson r")
for i in range(corr.shape[0]):
    for j in range(corr.shape[1]):
        plt.text(j, i, f"{corr.iat[i, j]:.2f}", ha="center", va="center",
                 color="white" if abs(corr.iat[i, j]) > 0.5 else "black", fontsize=9)
plt.xticks(range(4), df.columns, rotation=30, ha="right")
plt.yticks(range(4), df.columns)
plt.title("Correlation matrix (iris features)")
plt.tight_layout()
save("correlation_matrix_heatmap.svg")

print("done:", sorted(p.name for p in NOTE_DIR.glob("*.svg")))
