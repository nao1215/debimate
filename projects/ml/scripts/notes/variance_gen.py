"""variance ノート用の図を生成するスクリプト。

実行: cd projects/ml && uv run python scripts/notes/variance_gen.py
"""
import os

import matplotlib.pyplot as plt
import numpy as np

COLOR_BLUE = "#7aa6c2"
COLOR_RED = "#e15759"
COLOR_GREEN = "#59a14f"
COLOR_GRAY = "#999999"
COLOR_ORANGE = "#f28e2b"

NOTE_DIR = os.path.expanduser(
    "~/ghq/github.com/nao1215/debimate/projects/ml/notes/math/variance"
)
os.makedirs(NOTE_DIR, exist_ok=True)


def save(name: str) -> None:
    plt.savefig(os.path.join(NOTE_DIR, name), bbox_inches="tight")
    plt.close()


# ============================================================
# Fig 1: Variance comparison (existing)
# ============================================================
rng = np.random.default_rng(0)
values1 = rng.normal(loc=0.0, scale=1.0, size=500)
values2 = rng.normal(loc=0.0, scale=3.0, size=500)

plt.figure(figsize=(6, 4))
plt.hist(values1, bins=30, color=COLOR_GREEN, alpha=0.55, edgecolor="white",
         label=f"sigma=1 (var={values1.var():.2f})")
plt.hist(values2, bins=30, color=COLOR_RED, alpha=0.45, edgecolor="white",
         label=f"sigma=3 (var={values2.var():.2f})")
plt.title("Variance comparison: same mean, different spreads")
plt.xlabel("Value")
plt.ylabel("Count")
plt.legend()
plt.tight_layout()
save("variance_hist.svg")


# ============================================================
# Fig 2: Variance decomposition (within-group + between-group)
# ============================================================
rng2 = np.random.default_rng(0)
groups = ["A", "B", "C"]
group_means = [3.0, 6.0, 9.0]
group_std = 1.0
n_per = 80
data_by_group = {
    g: rng2.normal(m, group_std, n_per) for g, m in zip(groups, group_means)
}
all_data = np.concatenate(list(data_by_group.values()))
grand_mean = all_data.mean()
total_var = all_data.var()
within_vars = [v.var() for v in data_by_group.values()]
within_var_avg = np.mean(within_vars)
between_var = np.mean([(m - grand_mean) ** 2 for m in group_means])

fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))

ax = axes[0]
colors = [COLOR_BLUE, COLOR_GREEN, COLOR_ORANGE]
for (g, data), m, c in zip(data_by_group.items(), group_means, colors):
    ax.scatter(np.full_like(data, ord(g) - ord("A")), data, alpha=0.5, color=c, s=20)
    ax.axhline(m, xmin=(ord(g) - ord("A")) / 3 + 0.05,
               xmax=(ord(g) - ord("A")) / 3 + 0.28, color=c, lw=2.5)
ax.axhline(grand_mean, color="black", ls="--", lw=1.5,
           label=f"grand mean = {grand_mean:.2f}")
ax.set_xticks([0, 1, 2]); ax.set_xticklabels(groups)
ax.set_xlabel("group"); ax.set_ylabel("value")
ax.set_title("Raw data colored by group, with group means")
ax.legend(fontsize=9)
ax.grid(True, alpha=0.25)

ax = axes[1]
labels = ["Total\n(overall var)", "Within-group\n(avg of group vars)", "Between-group\n(var of group means)"]
heights = [total_var, within_var_avg, between_var]
bar_colors = [COLOR_BLUE, COLOR_GREEN, COLOR_RED]
bars = ax.bar(labels, heights, color=bar_colors, edgecolor="white")
for b, h in zip(bars, heights):
    ax.text(b.get_x() + b.get_width() / 2, h + 0.1, f"{h:.2f}",
            ha="center", fontsize=10)
ax.set_ylabel("variance")
ax.set_title(f"Total ≈ Within + Between\n{total_var:.2f} ≈ {within_var_avg:.2f} + {between_var:.2f}")
ax.grid(True, alpha=0.25, axis="y")

plt.tight_layout()
save("variance_decomposition.svg")


# ============================================================
# Fig 3: Variance reduction by averaging (bagging effect)
# ============================================================
# Simulate n independent noisy predictors of true value mu=0
rng3 = np.random.default_rng(1)
n_trials = 5000
true_value = 0.0
noise_std = 1.0

ns = [1, 4, 16, 64, 256]
samples_by_n = {}
for n in ns:
    means = np.mean(rng3.normal(true_value, noise_std, (n_trials, n)), axis=1)
    samples_by_n[n] = means

plt.figure(figsize=(8.5, 4.5))
for n, color in zip(ns, plt.cm.viridis(np.linspace(0.15, 0.85, len(ns)))):
    samples = samples_by_n[n]
    plt.hist(samples, bins=40, alpha=0.55, density=True, color=color,
             label=f"n={n}: var = {samples.var():.3f}")
plt.axvline(true_value, color="black", ls="--", lw=1, label="true value")
plt.xlabel("ensemble average prediction")
plt.ylabel("density")
plt.title("Averaging n independent predictions cuts variance by 1/n\n"
          "(this is why bagging / random forests work)")
plt.legend(fontsize=8, loc="upper right")
plt.xlim(-3, 3)
plt.grid(True, alpha=0.25)
plt.tight_layout()
save("variance_averaging.svg")


print("done:", sorted(os.listdir(NOTE_DIR)))
