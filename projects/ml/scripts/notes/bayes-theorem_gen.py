"""bayes-theorem ノート用の図を生成するスクリプト。

実行: cd projects/ml && uv run python scripts/notes/bayes-theorem_gen.py
"""
import os

import matplotlib.pyplot as plt
import numpy as np
from scipy import stats

COLOR_BLUE = "#7aa6c2"
COLOR_RED = "#e15759"
COLOR_GREEN = "#59a14f"
COLOR_GRAY = "#999999"
COLOR_PURPLE = "#b07aa1"

NOTE_DIR = os.path.expanduser(
    "~/ghq/github.com/nao1215/debimate/projects/ml/notes/math/bayes-theorem"
)
os.makedirs(NOTE_DIR, exist_ok=True)


def save(name: str) -> None:
    plt.savefig(os.path.join(NOTE_DIR, name), bbox_inches="tight")
    plt.close()


# ============================================================
# Fig 1: Disease testing - base rate matters (population grid visualization)
# ============================================================
# 10000 people grid
# Disease prevalence = 1% (100 sick, 9900 healthy)
# Sensitivity = 95% (sick correctly tested positive)
# Specificity = 95% (healthy correctly tested negative)
N = 10000
prev = 0.01
sens = 0.95
spec = 0.95

n_sick = int(N * prev)
n_healthy = N - n_sick
tp = int(n_sick * sens)         # 95
fn = n_sick - tp                # 5
tn = int(n_healthy * spec)      # 9405
fp = n_healthy - tn             # 495

# Visualize as a 100x100 grid colored by status
grid = np.zeros((100, 100), dtype=int)
# 0 = TN, 1 = FP, 2 = FN, 3 = TP
idx = np.arange(N)
np.random.default_rng(0).shuffle(idx)
sick_idx = idx[:n_sick]
healthy_idx = idx[n_sick:]
# For sick: first tp -> TP, rest -> FN
for k, i in enumerate(sick_idx):
    r, c = i // 100, i % 100
    grid[r, c] = 3 if k < tp else 2
for k, i in enumerate(healthy_idx):
    r, c = i // 100, i % 100
    grid[r, c] = 1 if k < fp else 0

from matplotlib.colors import ListedColormap
cmap = ListedColormap(["#e6eff5", "#f1a340", COLOR_RED, COLOR_GREEN])

fig, ax = plt.subplots(figsize=(7.5, 7))
ax.imshow(grid, cmap=cmap, vmin=0, vmax=3, aspect="equal")
ax.set_xticks([]); ax.set_yticks([])
ax.set_title(f"10,000 people · prevalence 1% · sensitivity 95% · specificity 95%\n"
             f"P(sick | positive test) = TP / (TP + FP) = {tp} / ({tp} + {fp}) = {tp/(tp+fp):.2%}")
# Legend
from matplotlib.patches import Patch
legend_elements = [
    Patch(facecolor="#e6eff5", edgecolor="black", label=f"TN: healthy & negative ({tn})"),
    Patch(facecolor="#f1a340", edgecolor="black", label=f"FP: healthy & positive ({fp})"),
    Patch(facecolor=COLOR_RED, edgecolor="black", label=f"FN: sick & negative ({fn})"),
    Patch(facecolor=COLOR_GREEN, edgecolor="black", label=f"TP: sick & positive ({tp})"),
]
ax.legend(handles=legend_elements, loc="upper center", bbox_to_anchor=(0.5, -0.05), ncol=2, fontsize=9)
plt.tight_layout()
save("disease_test_grid.png")


# ============================================================
# Fig 2: Bayes theorem components (prior, likelihood, posterior)
# ============================================================
# Simple discrete hypothesis space: 3 coins (heads probabilities)
hyps = np.array([0.3, 0.5, 0.7])
prior = np.array([1/3, 1/3, 1/3])

# Observed: 8 heads out of 10 tosses
n_heads = 8
n_total = 10
likelihood = stats.binom.pmf(n_heads, n_total, hyps)
# Posterior
unnorm = prior * likelihood
posterior = unnorm / unnorm.sum()

fig, axes = plt.subplots(1, 4, figsize=(14, 4))
labels = [f"p={h}" for h in hyps]

axes[0].bar(labels, prior, color=COLOR_BLUE, edgecolor="white")
axes[0].set_ylim(0, 1)
axes[0].set_title("Prior P(H)\nbefore data")
axes[0].set_ylabel("probability")

axes[1].bar(labels, likelihood, color=COLOR_GREEN, edgecolor="white")
axes[1].set_title(f"Likelihood P(D|H)\nP(8 heads of 10 | H)")
for i, v in enumerate(likelihood):
    axes[1].text(i, v + 0.01, f"{v:.3f}", ha="center", fontsize=8)

axes[2].bar(labels, prior * likelihood, color="#f1a340", edgecolor="white")
axes[2].set_title("Prior × Likelihood\n(unnormalized)")
for i, v in enumerate(prior * likelihood):
    axes[2].text(i, v + 0.002, f"{v:.4f}", ha="center", fontsize=8)

axes[3].bar(labels, posterior, color=COLOR_RED, edgecolor="white")
axes[3].set_ylim(0, 1)
axes[3].set_title("Posterior P(H|D)\nafter data")
for i, v in enumerate(posterior):
    axes[3].text(i, v + 0.02, f"{v:.2f}", ha="center", fontsize=9)

plt.tight_layout()
save("bayes_components.svg")


# ============================================================
# Fig 3: Sequential Bayesian update (Beta-Binomial)
# ============================================================
# Coin with true heads prob = 0.65
true_p = 0.65
rng = np.random.default_rng(0)
data_seq = rng.binomial(1, true_p, size=200)

p_grid = np.linspace(0, 1, 400)
# Start with uniform prior = Beta(1, 1)
stages = [0, 5, 20, 80, 200]
fig, axes = plt.subplots(1, len(stages), figsize=(15, 3.5), sharey=True)
for ax, n in zip(axes, stages):
    if n == 0:
        a, b = 1, 1
    else:
        heads = int(data_seq[:n].sum())
        tails = n - heads
        a = 1 + heads
        b = 1 + tails
    pdf = stats.beta.pdf(p_grid, a, b)
    ax.plot(p_grid, pdf, color=COLOR_BLUE, lw=2)
    ax.fill_between(p_grid, pdf, alpha=0.3, color=COLOR_BLUE)
    ax.axvline(true_p, color=COLOR_RED, lw=1.5, ls="--", label=f"true p={true_p}")
    if n == 0:
        ax.set_title("Prior: Beta(1, 1)\nuniform, no data")
    else:
        h = int(data_seq[:n].sum())
        ax.set_title(f"After {n} tosses\n{h} heads, {n - h} tails")
    ax.set_xlabel("p (heads prob)")
    ax.set_xlim(0, 1)
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.25)
axes[0].set_ylabel("posterior density")
plt.tight_layout()
save("bayes_sequential_update.svg")


# ============================================================
# Fig 4: Effect of prior strength
# ============================================================
n_data = 30
heads_obs = 22  # 73% heads in sample
tails_obs = n_data - heads_obs

priors = [
    ("Weak prior: Beta(2, 2)", 2, 2),
    ("Medium prior: Beta(10, 10)", 10, 10),
    ("Strong prior: Beta(100, 100)", 100, 100),
]

fig, axes = plt.subplots(1, 3, figsize=(14, 4.5), sharex=True)
for ax, (title, a_prior, b_prior) in zip(axes, priors):
    prior_pdf = stats.beta.pdf(p_grid, a_prior, b_prior)
    a_post = a_prior + heads_obs
    b_post = b_prior + tails_obs
    post_pdf = stats.beta.pdf(p_grid, a_post, b_post)

    ax.plot(p_grid, prior_pdf, color=COLOR_BLUE, lw=2, label=f"prior Beta({a_prior},{b_prior})")
    ax.fill_between(p_grid, prior_pdf, alpha=0.2, color=COLOR_BLUE)
    ax.plot(p_grid, post_pdf, color=COLOR_RED, lw=2, label=f"posterior")
    ax.fill_between(p_grid, post_pdf, alpha=0.3, color=COLOR_RED)
    ax.axvline(heads_obs / n_data, color="black", lw=1, ls=":",
               label=f"sample mean = {heads_obs/n_data:.2f}")
    ax.set_title(title)
    ax.set_xlabel("p")
    ax.set_xlim(0, 1)
    ax.legend(fontsize=8, loc="upper left")
    ax.grid(True, alpha=0.25)
axes[0].set_ylabel("density")
plt.suptitle(f"Same data ({heads_obs} heads / {n_data} tosses), different priors → different posteriors",
             y=1.02)
plt.tight_layout()
save("bayes_prior_strength.svg")


print("done:", sorted(os.listdir(NOTE_DIR)))
