"""hypothesis-test ノート用の図を生成するスクリプト。

実行: cd projects/ml && uv run python scripts/notes/hypothesis-test_gen.py
"""
import os

import matplotlib.pyplot as plt
import numpy as np
from scipy import stats

COLOR_BLUE = "#7aa6c2"
COLOR_RED = "#e15759"
COLOR_GREEN = "#59a14f"
COLOR_GRAY = "#999999"
COLOR_ORANGE = "#f1a340"

NOTE_DIR = os.path.expanduser(
    "~/ghq/github.com/nao1215/debimate/projects/ml/notes/math/hypothesis-test"
)
os.makedirs(NOTE_DIR, exist_ok=True)


def save(name: str) -> None:
    plt.savefig(os.path.join(NOTE_DIR, name), bbox_inches="tight")
    plt.close()


# ============================================================
# Fig 1: Null distribution, observed statistic, p-value shading
# ============================================================
# H0: mean = 0, H1: mean > 0 (one-sided z-test)
# Observed sample: n=30, sample mean = 0.45, population sigma = 1
z_obs = 0.45 * np.sqrt(30) / 1.0  # z = (xbar - mu0) / (sigma/sqrt(n))
z = np.linspace(-4, 4, 400)
pdf = stats.norm.pdf(z)

fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))

ax = axes[0]
ax.plot(z, pdf, color=COLOR_BLUE, lw=2)
ax.fill_between(z, pdf, where=(z >= z_obs), color=COLOR_RED, alpha=0.4,
                label=f"p-value = P(Z ≥ {z_obs:.2f}) = {1 - stats.norm.cdf(z_obs):.4f}")
ax.axvline(z_obs, color=COLOR_RED, lw=2)
ax.text(z_obs + 0.1, 0.35, f"observed z = {z_obs:.2f}", fontsize=10, color=COLOR_RED)
ax.set_title("p-value = tail area beyond the observed statistic under H0")
ax.set_xlabel("z (test statistic under H0)")
ax.set_ylabel("density")
ax.legend(fontsize=9)
ax.grid(True, alpha=0.25)

# Critical region with alpha = 0.05
alpha = 0.05
z_crit = stats.norm.ppf(1 - alpha)
ax = axes[1]
ax.plot(z, pdf, color=COLOR_BLUE, lw=2)
ax.fill_between(z, pdf, where=(z >= z_crit), color=COLOR_ORANGE, alpha=0.4,
                label=f"rejection region (α = {alpha})\nz_crit = {z_crit:.2f}")
ax.axvline(z_crit, color=COLOR_ORANGE, lw=1.5, ls="--")
ax.axvline(z_obs, color=COLOR_RED, lw=2, label=f"observed z = {z_obs:.2f}")
ax.set_title(f"Decision rule: reject H0 if observed z > z_crit")
ax.set_xlabel("z")
ax.legend(fontsize=9)
ax.grid(True, alpha=0.25)

plt.tight_layout()
save("p_value_concept.svg")


# ============================================================
# Fig 2: Confidence intervals over repeated experiments
# ============================================================
rng = np.random.default_rng(0)
true_mu = 5.0
sigma = 2.0
n_per = 30
n_experiments = 100

ci_lo = []
ci_hi = []
contains = []
for _ in range(n_experiments):
    sample = rng.normal(true_mu, sigma, n_per)
    xbar = sample.mean()
    se = sample.std(ddof=1) / np.sqrt(n_per)
    lo = xbar - 1.96 * se
    hi = xbar + 1.96 * se
    ci_lo.append(lo)
    ci_hi.append(hi)
    contains.append(lo <= true_mu <= hi)
ci_lo = np.array(ci_lo); ci_hi = np.array(ci_hi); contains = np.array(contains)

plt.figure(figsize=(10, 6))
for i in range(n_experiments):
    color = COLOR_BLUE if contains[i] else COLOR_RED
    plt.plot([ci_lo[i], ci_hi[i]], [i, i], color=color, lw=1.5, alpha=0.8)
    plt.scatter([(ci_lo[i] + ci_hi[i]) / 2], [i], color=color, s=10)
plt.axvline(true_mu, color="black", lw=2, label=f"true μ = {true_mu}")
miss = (~contains).sum()
plt.title(f"100 experiments × 95% CI: {n_experiments - miss} cover true μ, {miss} miss\n"
          "(in the long run, ~95% should cover)")
plt.xlabel("estimated mean and 95% CI")
plt.ylabel("experiment index")
plt.legend()
plt.grid(True, alpha=0.25)
plt.tight_layout()
save("confidence_intervals.svg")


# ============================================================
# Fig 3: H0 vs H1 - type I, type II errors and power
# ============================================================
n = 30
sigma = 1.0
mu0 = 0.0
mu1 = 0.5
# Distribution of sample mean under H0 and H1
se = sigma / np.sqrt(n)
x = np.linspace(-0.6, 1.2, 600)
pdf0 = stats.norm.pdf(x, loc=mu0, scale=se)
pdf1 = stats.norm.pdf(x, loc=mu1, scale=se)
alpha = 0.05
crit = stats.norm.ppf(1 - alpha, loc=mu0, scale=se)
power = 1 - stats.norm.cdf(crit, loc=mu1, scale=se)
beta = stats.norm.cdf(crit, loc=mu1, scale=se)

plt.figure(figsize=(10, 5))
plt.plot(x, pdf0, color=COLOR_BLUE, lw=2, label=f"H0: μ = {mu0}")
plt.plot(x, pdf1, color=COLOR_GREEN, lw=2, label=f"H1: μ = {mu1}")

# Type I error (alpha, reject H0 when H0 true)
plt.fill_between(x, pdf0, where=(x >= crit), color=COLOR_RED, alpha=0.4,
                 label=f"Type I error (α = {alpha:.2f})")
# Type II error (beta, fail to reject H0 when H1 true)
plt.fill_between(x, pdf1, where=(x < crit), color=COLOR_ORANGE, alpha=0.4,
                 label=f"Type II error (β = {beta:.2f})")
# Power
plt.fill_between(x, pdf1, where=(x >= crit), color=COLOR_GREEN, alpha=0.2,
                 label=f"Power (1 - β = {power:.2f})")
plt.axvline(crit, color="black", lw=1.5, ls="--")
plt.text(crit + 0.01, max(pdf0) * 0.85, f"reject H0\nif xbar > {crit:.3f}",
         fontsize=9)
plt.xlabel("sample mean xbar")
plt.ylabel("density")
plt.title("Type I error (false positive) vs Type II error (false negative) and power")
plt.legend(loc="upper left", fontsize=9)
plt.grid(True, alpha=0.25)
plt.tight_layout()
save("type1_type2_power.svg")


# ============================================================
# Fig 4: Sample size effect on test
# ============================================================
mu1 = 0.3
sigma = 1.0
alpha = 0.05
ns = np.arange(5, 500, 5)
powers = []
ci_widths = []
for n in ns:
    se = sigma / np.sqrt(n)
    crit = stats.norm.ppf(1 - alpha, loc=0, scale=se)
    p = 1 - stats.norm.cdf(crit, loc=mu1, scale=se)
    powers.append(p)
    ci_widths.append(2 * 1.96 * se)

fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))

axes[0].plot(ns, powers, color=COLOR_BLUE, lw=2)
axes[0].axhline(0.8, color=COLOR_RED, ls="--", label="conventional 80% power")
axes[0].set_xlabel("sample size n")
axes[0].set_ylabel("power (1 - β)")
axes[0].set_title(f"Power vs sample size (μ1={mu1}, σ={sigma}, α={alpha})")
axes[0].legend(fontsize=9)
axes[0].grid(True, alpha=0.25)

axes[1].plot(ns, ci_widths, color=COLOR_GREEN, lw=2)
axes[1].set_xlabel("sample size n")
axes[1].set_ylabel("95% CI width")
axes[1].set_title("CI width shrinks as 1/√n")
axes[1].grid(True, alpha=0.25)

plt.tight_layout()
save("sample_size_effect.svg")


print("done:", sorted(os.listdir(NOTE_DIR)))
