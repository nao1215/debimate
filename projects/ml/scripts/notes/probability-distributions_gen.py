"""probability-distributions ノート用の図を生成するスクリプト。

実行: cd projects/ml && uv run python scripts/notes/probability-distributions_gen.py
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
    "~/ghq/github.com/nao1215/debimate/projects/ml/notes/math/probability-distributions"
)
os.makedirs(NOTE_DIR, exist_ok=True)


def save(name: str) -> None:
    plt.savefig(os.path.join(NOTE_DIR, name), bbox_inches="tight")
    plt.close()


# ============================================================
# Fig 1: Discrete distributions (Bernoulli, Binomial, Poisson)
# ============================================================
fig, axes = plt.subplots(1, 3, figsize=(14, 4))

# Bernoulli p=0.3
ax = axes[0]
xs = [0, 1]
ax.bar(xs, [0.7, 0.3], color=[COLOR_BLUE, COLOR_RED], edgecolor="white", width=0.5)
for x, p in zip(xs, [0.7, 0.3]):
    ax.text(x, p + 0.02, f"{p:.1f}", ha="center", fontsize=11)
ax.set_xticks([0, 1]); ax.set_xticklabels(["0 (fail)", "1 (success)"])
ax.set_ylim(0, 1)
ax.set_title("Bernoulli(p=0.3)\nE[X]=p=0.3, Var=p(1-p)=0.21")
ax.set_ylabel("P(X=k)")
ax.grid(True, alpha=0.25, axis="y")

# Binomial n=20, p=0.3
ax = axes[1]
n_bin = 20
p_bin = 0.3
ks = np.arange(0, n_bin + 1)
pmf = stats.binom.pmf(ks, n_bin, p_bin)
ax.bar(ks, pmf, color=COLOR_BLUE, edgecolor="white")
ax.set_title(f"Binomial(n={n_bin}, p={p_bin})\nE[X]=np={n_bin*p_bin}, Var=np(1-p)={n_bin*p_bin*(1-p_bin):.2f}")
ax.set_xlabel("k (# successes)")
ax.set_ylabel("P(X=k)")
ax.grid(True, alpha=0.25, axis="y")

# Poisson lambda=4
ax = axes[2]
lam = 4
ks = np.arange(0, 16)
pmf = stats.poisson.pmf(ks, lam)
ax.bar(ks, pmf, color=COLOR_GREEN, edgecolor="white")
ax.set_title(f"Poisson(λ={lam})\nE[X]=Var=λ={lam}")
ax.set_xlabel("k (# events)")
ax.set_ylabel("P(X=k)")
ax.grid(True, alpha=0.25, axis="y")

plt.tight_layout()
save("distributions_discrete.svg")


# ============================================================
# Fig 2: Continuous distributions (Normal, Exponential, Beta)
# ============================================================
fig, axes = plt.subplots(1, 3, figsize=(14, 4))

# Normal: multiple (mu, sigma)
ax = axes[0]
x = np.linspace(-6, 8, 400)
for mu, sigma, color in [(0, 1, COLOR_BLUE), (2, 1, COLOR_GREEN), (0, 2, COLOR_RED)]:
    ax.plot(x, stats.norm.pdf(x, mu, sigma), color=color, lw=2,
            label=f"N(μ={mu}, σ={sigma})")
ax.set_title("Normal: shape determined by (μ, σ)")
ax.set_xlabel("x"); ax.set_ylabel("f(x)")
ax.legend(fontsize=9)
ax.grid(True, alpha=0.25)

# Exponential: multiple lambda
ax = axes[1]
x = np.linspace(0, 6, 400)
for lam, color in [(0.5, COLOR_BLUE), (1.0, COLOR_GREEN), (2.0, COLOR_RED)]:
    ax.plot(x, stats.expon.pdf(x, scale=1/lam), color=color, lw=2,
            label=f"Exp(λ={lam})")
ax.set_title("Exponential: waiting time between events")
ax.set_xlabel("x (wait time)"); ax.set_ylabel("f(x)")
ax.legend(fontsize=9)
ax.grid(True, alpha=0.25)

# Beta: different (a, b)
ax = axes[2]
x = np.linspace(0.001, 0.999, 400)
for a, b, color in [(2, 5, COLOR_BLUE), (5, 5, COLOR_GREEN), (5, 2, COLOR_RED),
                      (0.5, 0.5, COLOR_PURPLE)]:
    ax.plot(x, stats.beta.pdf(x, a, b), color=color, lw=2,
            label=f"Beta(a={a}, b={b})")
ax.set_title("Beta: prior over probabilities ∈ (0, 1)")
ax.set_xlabel("p"); ax.set_ylabel("f(p)")
ax.set_ylim(0, 3.5)
ax.legend(fontsize=9)
ax.grid(True, alpha=0.25)

plt.tight_layout()
save("distributions_continuous.svg")


# ============================================================
# Fig 3: Same parameter, different distributions on a count data
# Real data simulation: model "number of customers per hour"
# ============================================================
rng = np.random.default_rng(0)
# Generate ground truth from Poisson(λ=8)
counts = rng.poisson(8, 500)

fig, axes = plt.subplots(1, 3, figsize=(14, 4.5))
hist_kwargs = dict(bins=range(0, 25), color=COLOR_BLUE, alpha=0.6,
                    edgecolor="white", density=True)

# Fit Poisson
ax = axes[0]
ax.hist(counts, **hist_kwargs, label="data")
ks = np.arange(0, 25)
lam_fit = counts.mean()
ax.plot(ks, stats.poisson.pmf(ks, lam_fit), "o-", color=COLOR_RED, lw=2,
        label=f"Poisson(λ={lam_fit:.2f})")
ax.set_title("Fit: Poisson (correct family)")
ax.set_xlabel("counts/hour"); ax.set_ylabel("density")
ax.legend(fontsize=9)
ax.grid(True, alpha=0.25)

# Fit Normal (wrong family)
ax = axes[1]
ax.hist(counts, **hist_kwargs, label="data")
xs = np.linspace(0, 25, 200)
mu_fit, sigma_fit = counts.mean(), counts.std()
ax.plot(xs, stats.norm.pdf(xs, mu_fit, sigma_fit), "-", color=COLOR_RED, lw=2,
        label=f"N(μ={mu_fit:.1f}, σ={sigma_fit:.1f})")
ax.set_title("Fit: Normal (continuous, allows negatives)")
ax.set_xlabel("counts/hour"); ax.set_ylabel("density")
ax.legend(fontsize=9)
ax.grid(True, alpha=0.25)

# Fit Exponential (very wrong)
ax = axes[2]
ax.hist(counts, **hist_kwargs, label="data")
xs = np.linspace(0.01, 25, 200)
scale_fit = counts.mean()  # exp scale = 1/lambda = mean
ax.plot(xs, stats.expon.pdf(xs, scale=scale_fit), "-", color=COLOR_RED, lw=2,
        label=f"Exp(scale={scale_fit:.1f})")
ax.set_title("Fit: Exponential (wrong shape entirely)")
ax.set_xlabel("counts/hour"); ax.set_ylabel("density")
ax.legend(fontsize=9)
ax.grid(True, alpha=0.25)

plt.suptitle("Choosing the right distribution family matters more than fitting parameters",
             y=1.02)
plt.tight_layout()
save("distributions_family_choice.svg")


# ============================================================
# Fig 4: Relationships between distributions
# ============================================================
fig, ax = plt.subplots(figsize=(11, 6))

# Simple positional layout
nodes = {
    "Bernoulli\n(1 trial)": (1, 4),
    "Binomial\n(n trials)": (4, 4),
    "Normal\napprox": (7, 4),
    "Poisson\n(rare events)": (4, 1.5),
    "Exponential\n(wait time)": (1, 1.5),
    "Beta\n(prior over p)": (7, 1.5),
    "Gamma\n(sum of Exp)": (10, 1.5),
}

import matplotlib.patches as patches
for name, (xx, yy) in nodes.items():
    circle = patches.FancyBboxPatch((xx - 0.7, yy - 0.4), 1.4, 0.8,
                                     boxstyle="round,pad=0.05",
                                     facecolor=COLOR_BLUE, alpha=0.6,
                                     edgecolor="black", linewidth=1.2)
    ax.add_patch(circle)
    ax.text(xx, yy, name, ha="center", va="center", fontsize=9, fontweight="bold")

edges = [
    ("Bernoulli\n(1 trial)", "Binomial\n(n trials)", "n-fold sum"),
    ("Binomial\n(n trials)", "Normal\napprox", "CLT (n→∞)"),
    ("Binomial\n(n trials)", "Poisson\n(rare events)", "np→λ, n→∞"),
    ("Poisson\n(rare events)", "Exponential\n(wait time)", "inter-arrival time"),
    ("Exponential\n(wait time)", "Gamma\n(sum of Exp)", "n-fold sum"),
    ("Bernoulli\n(1 trial)", "Beta\n(prior over p)", "conjugate prior"),
]
for src, dst, label in edges:
    x0, y0 = nodes[src]
    x1, y1 = nodes[dst]
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                arrowprops=dict(arrowstyle="->", color="black", lw=1,
                                shrinkA=30, shrinkB=30))
    ax.text((x0 + x1) / 2, (y0 + y1) / 2 + 0.15, label, ha="center",
            fontsize=8, color=COLOR_RED, style="italic")

ax.set_xlim(-0.5, 11.5)
ax.set_ylim(0.5, 5)
ax.set_aspect("equal")
ax.axis("off")
ax.set_title("Distributions form a connected family", fontsize=12)
plt.tight_layout()
save("distributions_family_tree.svg")


print("done:", sorted(os.listdir(NOTE_DIR)))
