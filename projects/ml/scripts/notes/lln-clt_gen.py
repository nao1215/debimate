"""lln-clt ノート用の図を生成するスクリプト。

実行: cd projects/ml && uv run python scripts/notes/lln-clt_gen.py
"""
import os

import matplotlib.pyplot as plt
import numpy as np
from scipy import stats

COLOR_BLUE = "#7aa6c2"
COLOR_RED = "#e15759"
COLOR_GREEN = "#59a14f"
COLOR_ORANGE = "#f28e2b"
COLOR_PURPLE = "#b07aa1"

NOTE_DIR = os.path.expanduser(
    "~/ghq/github.com/nao1215/debimate/projects/ml/notes/math/lln-clt"
)
os.makedirs(NOTE_DIR, exist_ok=True)


def save(name: str) -> None:
    plt.savefig(os.path.join(NOTE_DIR, name), bbox_inches="tight")
    plt.close()


# ============================================================
# Fig 1: Law of Large Numbers (running mean convergence)
# ============================================================
rng = np.random.default_rng(0)
# Roll a fair die many times - E[X] = 3.5
n_max = 5000

fig, ax = plt.subplots(figsize=(10, 4.5))
for trial, color in [(0, COLOR_BLUE), (1, COLOR_RED), (2, COLOR_GREEN)]:
    rolls = np.random.default_rng(trial).integers(1, 7, n_max)
    running = np.cumsum(rolls) / np.arange(1, n_max + 1)
    ax.plot(running, color=color, alpha=0.65, lw=1, label=f"trial {trial+1}")
ax.axhline(3.5, color="black", ls="--", lw=1.5, label="E[X] = 3.5")
ax.set_xscale("log")
ax.set_xlabel("sample size n (log)")
ax.set_ylabel("running sample mean")
ax.set_title("Law of Large Numbers: sample mean → E[X] as n → ∞")
ax.legend()
ax.grid(True, alpha=0.25)
ax.set_ylim(2.5, 4.5)
plt.tight_layout()
save("llnclt_lln.svg")


# ============================================================
# Fig 2: Central Limit Theorem - sums of various distributions become normal
# ============================================================
n_per_avg = 30  # samples per average
n_means = 5000   # number of sample means to plot

fig, axes = plt.subplots(2, 4, figsize=(15, 7))

distributions = [
    ("uniform(0,1)", lambda r, n: r.uniform(0, 1, n), 0.5, 1/12),
    ("exponential(λ=1)", lambda r, n: r.exponential(1, n), 1, 1),
    ("Bernoulli(0.3)", lambda r, n: r.binomial(1, 0.3, n).astype(float), 0.3, 0.3 * 0.7),
    ("lognormal(0, 0.5)", lambda r, n: r.lognormal(0, 0.5, n),
     np.exp(0.5**2 / 2), (np.exp(0.5**2) - 1) * np.exp(0.5**2)),
]

for col, (name, sampler, mu, var) in enumerate(distributions):
    rng = np.random.default_rng(0)
    # Top row: original distribution
    samples_single = sampler(rng, 5000)
    axes[0, col].hist(samples_single, bins=40, color=COLOR_BLUE,
                       edgecolor="white", density=True)
    axes[0, col].set_title(f"Original: {name}")
    axes[0, col].set_xlabel("value")
    axes[0, col].grid(True, alpha=0.25)

    # Bottom row: distribution of sample means
    rng2 = np.random.default_rng(0)
    means = np.array([sampler(rng2, n_per_avg).mean() for _ in range(n_means)])
    axes[1, col].hist(means, bins=40, color=COLOR_GREEN, edgecolor="white", density=True)
    # Overlay theoretical normal: N(mu, var/n)
    se = np.sqrt(var / n_per_avg)
    xs = np.linspace(means.min(), means.max(), 200)
    axes[1, col].plot(xs, stats.norm.pdf(xs, mu, se), color=COLOR_RED, lw=2,
                       label=f"N({mu:.2f}, {se:.3f}²)")
    axes[1, col].set_title(f"Sample mean of n={n_per_avg}\n→ approx normal")
    axes[1, col].set_xlabel("sample mean")
    axes[1, col].legend(fontsize=8)
    axes[1, col].grid(True, alpha=0.25)

plt.suptitle("Central Limit Theorem: averages of any distribution → normal", y=1.02)
plt.tight_layout()
save("llnclt_clt_universal.svg")


# ============================================================
# Fig 3: CLT - effect of n on sample mean distribution
# ============================================================
# Use lognormal to highlight convergence
rng = np.random.default_rng(0)
sampler = lambda r, n: r.lognormal(0, 1, n)
mu_true = np.exp(0.5)  # E[X] of lognormal(0, 1)

fig, axes = plt.subplots(1, 4, figsize=(15, 4.2), sharex=True, sharey=False)
for ax, n in zip(axes, [1, 5, 30, 200]):
    rng2 = np.random.default_rng(0)
    means = np.array([sampler(rng2, n).mean() for _ in range(5000)])
    ax.hist(means, bins=40, color=COLOR_BLUE, edgecolor="white", density=True)
    ax.axvline(mu_true, color=COLOR_RED, lw=2, ls="--", label=f"E[X] = {mu_true:.2f}")
    ax.set_title(f"n = {n}\nspread = {means.std():.3f}")
    ax.set_xlabel("sample mean")
    ax.legend(fontsize=8)
    ax.set_xlim(0, 5)
    ax.grid(True, alpha=0.25)
axes[0].set_ylabel("density")
plt.suptitle("Larger n → sample mean concentrates around E[X] (LLN) AND becomes normal (CLT)",
             y=1.02)
plt.tight_layout()
save("llnclt_n_effect.svg")


# ============================================================
# Fig 4: Standard error shrinks as 1/√n
# ============================================================
ns = np.logspace(0.5, 4, 40).astype(int)
rng = np.random.default_rng(0)
sigma_true = 1.0
empirical_se = []
for n in ns:
    means = np.array([rng.normal(0, sigma_true, n).mean() for _ in range(500)])
    empirical_se.append(means.std())

plt.figure(figsize=(8, 4.5))
plt.loglog(ns, empirical_se, "o", color=COLOR_BLUE, label="empirical SE")
plt.loglog(ns, sigma_true / np.sqrt(ns), color=COLOR_RED, lw=2,
           label="theoretical σ/√n")
plt.xlabel("sample size n (log)")
plt.ylabel("standard error of sample mean (log)")
plt.title("SE = σ/√n: doubling precision requires 4x more data")
plt.legend()
plt.grid(True, alpha=0.25, which="both")
plt.tight_layout()
save("llnclt_se_root_n.svg")


print("done:", sorted(os.listdir(NOTE_DIR)))
