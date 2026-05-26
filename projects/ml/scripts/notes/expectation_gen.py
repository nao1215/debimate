"""expectation ノート用の図を生成するスクリプト。

実行: cd projects/ml && uv run python scripts/notes/expectation_gen.py
"""
import os

import matplotlib.pyplot as plt
import numpy as np
from scipy import stats

COLOR_BLUE = "#7aa6c2"
COLOR_RED = "#e15759"
COLOR_GREEN = "#59a14f"
COLOR_GRAY = "#999999"

NOTE_DIR = os.path.expanduser(
    "~/ghq/github.com/nao1215/debimate/projects/ml/notes/math/expectation"
)
os.makedirs(NOTE_DIR, exist_ok=True)


def save(name: str) -> None:
    plt.savefig(os.path.join(NOTE_DIR, name), bbox_inches="tight")
    plt.close()


# ============================================================
# Fig 1: Discrete distribution and its expectation as weighted center
# ============================================================
xs = np.array([1, 2, 3, 4, 5, 6])
probs = np.array([0.05, 0.10, 0.15, 0.20, 0.25, 0.25])
EX = float((xs * probs).sum())

plt.figure(figsize=(7, 4.5))
bars = plt.bar(xs, probs, color=COLOR_BLUE, edgecolor="white", width=0.7)
for x, p in zip(xs, probs):
    plt.text(x, p + 0.005, f"{p:.2f}", ha="center", fontsize=9)
plt.axvline(EX, color=COLOR_RED, lw=2, ls="--", label=f"E[X] = Σ x P(x) = {EX:.2f}")
plt.xlabel("x"); plt.ylabel("P(X = x)")
plt.title("Expectation = probability-weighted sum (center of mass)")
plt.legend()
plt.grid(True, alpha=0.25, axis="y")
plt.tight_layout()
save("expectation_discrete.svg")


# ============================================================
# Fig 2: Law of large numbers - sample mean converges to E[X]
# ============================================================
rng = np.random.default_rng(0)
true_mean = 3.5  # Expected value of a fair die
n_trials = 5000

fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))

ax = axes[0]
for seed, color in [(0, COLOR_BLUE), (1, COLOR_RED), (2, COLOR_GREEN)]:
    rng_local = np.random.default_rng(seed)
    rolls = rng_local.integers(1, 7, size=n_trials)
    running_mean = np.cumsum(rolls) / np.arange(1, n_trials + 1)
    ax.plot(running_mean, color=color, alpha=0.7, lw=1.2, label=f"trial {seed+1}")
ax.axhline(true_mean, color="black", lw=1.5, ls="--", label="E[X] = 3.5 (fair die)")
ax.set_xscale("log")
ax.set_xlabel("number of samples (log scale)")
ax.set_ylabel("running sample mean")
ax.set_title("Sample mean converges to E[X] (law of large numbers)")
ax.legend()
ax.grid(True, alpha=0.25)

# Histogram of sample means at different n
ax = axes[1]
n_repeats = 1000
sample_sizes = [10, 100, 1000]
colors = [COLOR_BLUE, COLOR_GREEN, COLOR_RED]
for n, color in zip(sample_sizes, colors):
    means = []
    rng_local = np.random.default_rng(42)
    for _ in range(n_repeats):
        rolls = rng_local.integers(1, 7, size=n)
        means.append(rolls.mean())
    ax.hist(means, bins=40, alpha=0.6, color=color, edgecolor="white",
            label=f"n={n}", density=True)
ax.axvline(true_mean, color="black", lw=1.5, ls="--")
ax.set_xlabel("sample mean")
ax.set_ylabel("density")
ax.set_title("Distribution of sample means tightens around E[X]")
ax.legend()
ax.grid(True, alpha=0.25)

plt.tight_layout()
save("law_of_large_numbers.svg")


# ============================================================
# Fig 3: Continuous distribution and its expectation
# ============================================================
x = np.linspace(-1, 8, 400)
pdf_norm = stats.norm.pdf(x, loc=3.0, scale=1.2)
EX_norm = 3.0
pdf_skew = stats.lognorm.pdf(x + 0.001, s=0.6, scale=np.exp(0.8))
EX_skew = float(np.exp(0.8 + 0.6 ** 2 / 2))

fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))

ax = axes[0]
ax.plot(x, pdf_norm, color=COLOR_BLUE, lw=2)
ax.fill_between(x, pdf_norm, alpha=0.3, color=COLOR_BLUE)
ax.axvline(EX_norm, color=COLOR_RED, lw=2, ls="--", label=f"E[X] = {EX_norm:.2f}")
ax.set_xlabel("x"); ax.set_ylabel("PDF f(x)")
ax.set_title("Symmetric (Normal): E[X] = mode = median")
ax.legend()
ax.grid(True, alpha=0.25)

ax = axes[1]
ax.plot(x, pdf_skew, color=COLOR_BLUE, lw=2)
ax.fill_between(x, pdf_skew, alpha=0.3, color=COLOR_BLUE)
ax.axvline(EX_skew, color=COLOR_RED, lw=2, ls="--", label=f"E[X] = {EX_skew:.2f}")
# Mode of lognormal
mode = float(np.exp(0.8 - 0.6 ** 2))
ax.axvline(mode, color=COLOR_GREEN, lw=2, ls=":", label=f"mode = {mode:.2f}")
ax.set_xlabel("x"); ax.set_ylabel("PDF f(x)")
ax.set_title("Skewed (Log-Normal): E[X] pulled by long tail")
ax.legend()
ax.grid(True, alpha=0.25)

plt.tight_layout()
save("expectation_continuous.svg")


# ============================================================
# Fig 4: Linearity of expectation - E[X+Y] = E[X] + E[Y]
# ============================================================
rng = np.random.default_rng(0)
n = 5000
# X: shifted normal, Y: chi-squared (skewed) - dependent on each other to show linearity even without independence
X = rng.normal(2.0, 1.5, n)
Y = rng.chisquare(df=3, size=n)  # mean = df = 3
# Even when X, Y are dependent, linearity holds. Let's use a copula-like dependence:
# Force correlation
Y_corr = Y + 0.5 * X  # E[Y_corr] = E[Y] + 0.5 * E[X] = 3 + 1 = 4

EX_emp = X.mean()
EY_emp = Y_corr.mean()
EXY_emp = (X + Y_corr).mean()

fig, axes = plt.subplots(1, 3, figsize=(14, 4.2))

axes[0].hist(X, bins=50, color=COLOR_BLUE, edgecolor="white", density=True)
axes[0].axvline(EX_emp, color=COLOR_RED, lw=2, ls="--")
axes[0].set_title(f"X: E[X] ≈ {EX_emp:.2f}")
axes[0].set_xlabel("X")
axes[0].grid(True, alpha=0.25)

axes[1].hist(Y_corr, bins=50, color=COLOR_GREEN, edgecolor="white", density=True)
axes[1].axvline(EY_emp, color=COLOR_RED, lw=2, ls="--")
axes[1].set_title(f"Y: E[Y] ≈ {EY_emp:.2f}")
axes[1].set_xlabel("Y")
axes[1].grid(True, alpha=0.25)

axes[2].hist(X + Y_corr, bins=50, color="#b07aa1", edgecolor="white", density=True)
axes[2].axvline(EXY_emp, color=COLOR_RED, lw=2, ls="--",
                label=f"E[X+Y] ≈ {EXY_emp:.2f}")
axes[2].axvline(EX_emp + EY_emp, color="black", lw=1.5, ls=":",
                label=f"E[X] + E[Y] ≈ {EX_emp + EY_emp:.2f}")
axes[2].set_title(f"X + Y: E[X+Y] = E[X] + E[Y] ✓")
axes[2].set_xlabel("X + Y")
axes[2].legend(fontsize=8)
axes[2].grid(True, alpha=0.25)

plt.tight_layout()
save("expectation_linearity.svg")


print("done:", sorted(os.listdir(NOTE_DIR)))
