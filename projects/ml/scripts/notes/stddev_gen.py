"""stddev ノート用の図を生成するスクリプト。

実行: cd projects/ml && uv run python scripts/notes/stddev_gen.py
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
    "~/ghq/github.com/nao1215/debimate/projects/ml/notes/math/stddev"
)
os.makedirs(NOTE_DIR, exist_ok=True)


def save(name: str) -> None:
    plt.savefig(os.path.join(NOTE_DIR, name), bbox_inches="tight")
    plt.close()


# ============================================================
# Fig 1: histogram + mean +/- stddev (existing)
# ============================================================
rng = np.random.default_rng(1)
values = rng.normal(loc=10.0, scale=2.0, size=500)
mean = values.mean()
std = values.std()

plt.figure(figsize=(6, 4))
plt.hist(values, bins=30, color=COLOR_BLUE, edgecolor="white")
plt.axvline(mean, color=COLOR_RED, linestyle="--", linewidth=2,
            label=f"mean = {mean:.2f}")
plt.axvline(mean - std, color=COLOR_GREEN, linestyle="--", linewidth=2,
            label=f"mean - stddev = {mean - std:.2f}")
plt.axvline(mean + std, color=COLOR_GREEN, linestyle="--", linewidth=2,
            label=f"mean + stddev = {mean + std:.2f}")
plt.title("Stddev around mean")
plt.xlabel("Value")
plt.ylabel("Count")
plt.legend()
plt.tight_layout()
save("stddev_hist.svg")


# ============================================================
# Fig 2: 68-95-99.7 rule visualization
# ============================================================
x = np.linspace(-4, 4, 800)
pdf = stats.norm.pdf(x)

plt.figure(figsize=(8.5, 4.5))
plt.plot(x, pdf, color=COLOR_BLUE, lw=2)

# Shade ±3σ, ±2σ, ±1σ from outermost
plt.fill_between(x, pdf, where=(np.abs(x) <= 3), color="#cce0ec", alpha=0.6,
                 label="±3σ: 99.7%")
plt.fill_between(x, pdf, where=(np.abs(x) <= 2), color=COLOR_GREEN, alpha=0.5,
                 label="±2σ: 95.4%")
plt.fill_between(x, pdf, where=(np.abs(x) <= 1), color=COLOR_RED, alpha=0.55,
                 label="±1σ: 68.3%")

for k in [1, 2, 3]:
    for sign in [-1, 1]:
        plt.axvline(sign * k, color="black", lw=0.7, ls=":")
    plt.text(k, -0.018, f"+{k}σ", ha="center", fontsize=9)
    plt.text(-k, -0.018, f"-{k}σ", ha="center", fontsize=9)

plt.xlabel("z = (x - μ) / σ")
plt.ylabel("density")
plt.title("Normal distribution: 68-95-99.7 rule")
plt.legend(loc="upper right")
plt.ylim(-0.03, 0.45)
plt.grid(True, alpha=0.25)
plt.tight_layout()
save("stddev_normal_rule.svg")


# ============================================================
# Fig 3: Z-score normalizes different scales for comparison
# ============================================================
# Two subjects with very different distributions
rng2 = np.random.default_rng(0)
n = 200
math_scores = rng2.normal(70, 15, n).clip(0, 100)
english_scores = rng2.normal(50, 5, n).clip(0, 100)

# Highlight one student
student_math = 85
student_english = 58
z_math = (student_math - math_scores.mean()) / math_scores.std()
z_english = (student_english - english_scores.mean()) / english_scores.std()

fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))

ax = axes[0]
ax.hist(math_scores, bins=25, color=COLOR_BLUE, alpha=0.55, edgecolor="white",
        label=f"math (μ={math_scores.mean():.0f}, σ={math_scores.std():.0f})")
ax.hist(english_scores, bins=25, color=COLOR_ORANGE, alpha=0.55, edgecolor="white",
        label=f"english (μ={english_scores.mean():.0f}, σ={english_scores.std():.0f})")
ax.axvline(student_math, color=COLOR_BLUE, lw=2, label=f"student math = {student_math}")
ax.axvline(student_english, color=COLOR_ORANGE, lw=2,
           label=f"student english = {student_english}")
ax.set_title("Raw scores: different scales hide who did relatively better")
ax.set_xlabel("score"); ax.set_ylabel("count")
ax.legend(fontsize=8)
ax.grid(True, alpha=0.25, axis="y")

ax = axes[1]
math_z = (math_scores - math_scores.mean()) / math_scores.std()
eng_z = (english_scores - english_scores.mean()) / english_scores.std()
ax.hist(math_z, bins=25, color=COLOR_BLUE, alpha=0.55, edgecolor="white",
        label="math (z-score)")
ax.hist(eng_z, bins=25, color=COLOR_ORANGE, alpha=0.55, edgecolor="white",
        label="english (z-score)")
ax.axvline(z_math, color=COLOR_BLUE, lw=2,
           label=f"student math z = {z_math:+.2f}")
ax.axvline(z_english, color=COLOR_ORANGE, lw=2,
           label=f"student english z = {z_english:+.2f}")
ax.set_title(f"After z = (x - μ)/σ: english z={z_english:+.2f} > math z={z_math:+.2f}")
ax.set_xlabel("z (standard deviations from mean)"); ax.set_ylabel("count")
ax.legend(fontsize=8)
ax.grid(True, alpha=0.25, axis="y")

plt.tight_layout()
save("stddev_zscore_compare.svg")


print("done:", sorted(os.listdir(NOTE_DIR)))
