"""log-exp-logodds ノート用の図を生成するスクリプト。

実行: cd projects/ml && uv run python scripts/notes/log-exp-logodds_gen.py
"""
import os

import matplotlib.pyplot as plt
import numpy as np

COLOR_BLUE = "#7aa6c2"
COLOR_RED = "#e15759"
COLOR_GREEN = "#59a14f"
COLOR_GRAY = "#999999"

NOTE_DIR = os.path.expanduser(
    "~/ghq/github.com/nao1215/debimate/projects/ml/notes/math/log-exp-logodds"
)
os.makedirs(NOTE_DIR, exist_ok=True)


def save(name: str) -> None:
    plt.savefig(os.path.join(NOTE_DIR, name), bbox_inches="tight")
    plt.close()


# ============================================================
# Fig 1: log and exp as inverse functions
# ============================================================
x_pos = np.linspace(0.05, 4, 200)
x_all = np.linspace(-3, 4, 200)

fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))

axes[0].plot(x_pos, np.log(x_pos), color=COLOR_BLUE, lw=2, label="y = log(x)  (natural log)")
axes[0].plot(x_pos, np.log2(x_pos), color=COLOR_RED, lw=1.5, ls="--", label="y = log_2(x)")
axes[0].plot(x_pos, np.log10(x_pos), color=COLOR_GREEN, lw=1.5, ls=":", label="y = log_10(x)")
axes[0].axhline(0, color=COLOR_GRAY, lw=0.6)
axes[0].axvline(1, color=COLOR_GRAY, lw=0.6, ls=":")
axes[0].scatter([1], [0], color="black", zorder=5)
axes[0].annotate("log(1)=0", (1, 0), xytext=(1.6, -1.0), fontsize=9,
                 arrowprops=dict(arrowstyle="->", color="black"))
axes[0].set_title("Logarithms of different bases share the same shape")
axes[0].set_xlabel("x"); axes[0].set_ylabel("log(x)")
axes[0].set_ylim(-3.5, 2.5)
axes[0].legend(fontsize=9); axes[0].grid(True, alpha=0.25)

axes[1].plot(x_all, np.exp(x_all), color=COLOR_BLUE, lw=2, label="y = exp(x)")
axes[1].plot(x_all, x_all, color=COLOR_GRAY, lw=1, ls=":", label="y = x (mirror)")
# Plot log(x) reflected across y=x to show inverse relationship
xs = np.linspace(0.05, np.exp(2.5), 200)
axes[1].plot(xs, np.log(xs), color=COLOR_RED, lw=2, label="y = log(x)")
axes[1].axhline(0, color=COLOR_GRAY, lw=0.6)
axes[1].set_title("exp and log are mirror images across y = x")
axes[1].set_xlabel("x"); axes[1].set_ylabel("y")
axes[1].set_xlim(-3, 5); axes[1].set_ylim(-3, 8)
axes[1].set_aspect("equal", adjustable="box")
axes[1].legend(fontsize=9, loc="upper left"); axes[1].grid(True, alpha=0.25)

plt.tight_layout()
save("log_exp_curves.svg")


# ============================================================
# Fig 2: log turns products into sums
# ============================================================
xs = np.linspace(0.5, 50, 200)

fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))

axes[0].plot(xs, xs * 5, color=COLOR_BLUE, lw=2, label="y = 5 * x")
axes[0].plot(xs, xs * 10, color=COLOR_RED, lw=2, label="y = 10 * x")
axes[0].plot(xs, xs * 50, color=COLOR_GREEN, lw=2, label="y = 50 * x")
axes[0].set_title("Linear scale: scaling is multiplicative")
axes[0].set_xlabel("x"); axes[0].set_ylabel("y")
axes[0].legend(fontsize=9); axes[0].grid(True, alpha=0.25)

axes[1].plot(xs, np.log(xs * 5), color=COLOR_BLUE, lw=2, label="log(5 * x) = log 5 + log x")
axes[1].plot(xs, np.log(xs * 10), color=COLOR_RED, lw=2, label="log(10 * x) = log 10 + log x")
axes[1].plot(xs, np.log(xs * 50), color=COLOR_GREEN, lw=2, label="log(50 * x) = log 50 + log x")
axes[1].set_title("Log scale: scaling becomes additive (parallel lines)")
axes[1].set_xlabel("x"); axes[1].set_ylabel("log(y)")
axes[1].legend(fontsize=9, loc="lower right"); axes[1].grid(True, alpha=0.25)

plt.tight_layout()
save("log_products_to_sums.svg")


# ============================================================
# Fig 3: sigmoid and log-odds relationship
# ============================================================
z = np.linspace(-6, 6, 400)
p = 1.0 / (1.0 + np.exp(-z))

p_grid = np.linspace(0.001, 0.999, 400)
logodds = np.log(p_grid / (1 - p_grid))

fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))

axes[0].plot(z, p, color=COLOR_BLUE, lw=2)
axes[0].axhline(0.5, color=COLOR_GRAY, lw=0.7, ls=":")
axes[0].axvline(0, color=COLOR_GRAY, lw=0.7, ls=":")
axes[0].set_title("Sigmoid: maps log-odds z to probability p\np = 1 / (1 + exp(-z))")
axes[0].set_xlabel("z (log-odds)"); axes[0].set_ylabel("p (probability)")
axes[0].set_ylim(-0.05, 1.05)
axes[0].grid(True, alpha=0.25)

axes[1].plot(p_grid, logodds, color=COLOR_RED, lw=2)
axes[1].axhline(0, color=COLOR_GRAY, lw=0.7, ls=":")
axes[1].axvline(0.5, color=COLOR_GRAY, lw=0.7, ls=":")
axes[1].set_title("Logit: maps probability p back to log-odds\nz = log(p / (1 - p))")
axes[1].set_xlabel("p (probability)"); axes[1].set_ylabel("z (log-odds)")
axes[1].set_ylim(-7, 7)
axes[1].grid(True, alpha=0.25)

plt.tight_layout()
save("sigmoid_logit.svg")


# ============================================================
# Fig 4: Numerical stability - product of small probabilities
# ============================================================
n_steps = np.arange(1, 800)
p_each = 0.99  # 1 サンプルあたりの尤度
# Direct multiplication
prod = np.cumprod(np.full_like(n_steps, p_each, dtype=float))
# Log-sum equivalent
log_sum = np.cumsum(np.full_like(n_steps, np.log(p_each), dtype=float))

fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))

axes[0].plot(n_steps, prod, color=COLOR_RED, lw=2, label="cumulative product (underflows)")
axes[0].set_xlabel("number of samples")
axes[0].set_ylabel("product of likelihoods")
axes[0].set_title("Direct product: underflows to 0 for many samples")
axes[0].set_yscale("symlog", linthresh=1e-100)
axes[0].axhline(np.finfo(float).tiny, color=COLOR_GRAY, ls=":", lw=1,
                label=f"float64 tiny ≈ {np.finfo(float).tiny:.0e}")
axes[0].legend(fontsize=8)
axes[0].grid(True, alpha=0.25)

axes[1].plot(n_steps, log_sum, color=COLOR_BLUE, lw=2, label="cumulative log-sum (stable)")
axes[1].set_xlabel("number of samples")
axes[1].set_ylabel("sum of log-likelihoods")
axes[1].set_title("Log-sum: stays representable even for huge n")
axes[1].legend(fontsize=9)
axes[1].grid(True, alpha=0.25)

plt.tight_layout()
save("log_numerical_stability.svg")


print("done:", sorted(os.listdir(NOTE_DIR)))
