"""convex-functions ノート用の図を生成するスクリプト。

実行: cd projects/ml && uv run python scripts/notes/convex-functions_gen.py
"""
import os

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

COLOR_BLUE = "#7aa6c2"
COLOR_RED = "#e15759"
COLOR_GREEN = "#59a14f"
COLOR_ORANGE = "#f28e2b"

NOTE_DIR = os.path.expanduser(
    "~/ghq/github.com/nao1215/debimate/projects/ml/notes/math/convex-functions"
)
os.makedirs(NOTE_DIR, exist_ok=True)


def save(name: str) -> None:
    plt.savefig(os.path.join(NOTE_DIR, name), bbox_inches="tight")
    plt.close()


# ============================================================
# Fig 1: Convex vs non-convex functions
# ============================================================
x = np.linspace(-3, 3, 400)

fig, axes = plt.subplots(1, 3, figsize=(14, 4.5))

# Convex
ax = axes[0]
ax.plot(x, x ** 2, color=COLOR_BLUE, lw=2.5, label="f(x) = x²")
ax.plot(x, np.exp(x) - 1, color=COLOR_GREEN, lw=2.5, label="f(x) = e^x - 1")
ax.plot(x, np.abs(x), color=COLOR_RED, lw=2.5, label="f(x) = |x|")
ax.axhline(0, color="black", lw=0.5)
ax.axvline(0, color="black", lw=0.5)
ax.set_title("Convex functions: U-shaped, one minimum")
ax.set_ylim(-1, 10)
ax.legend(fontsize=9)
ax.grid(True, alpha=0.25)

# Non-convex (multimodal)
ax = axes[1]
y_nc = 0.3 * x ** 4 - 1.5 * x ** 2 - 0.5 * x + 2
ax.plot(x, y_nc, color=COLOR_RED, lw=2.5)
# Mark local minima
from scipy.signal import argrelextrema
y_nc_dense = 0.3 * np.linspace(-3, 3, 1000) ** 4 - 1.5 * np.linspace(-3, 3, 1000) ** 2 - 0.5 * np.linspace(-3, 3, 1000) + 2
x_dense = np.linspace(-3, 3, 1000)
mins = argrelextrema(y_nc_dense, np.less)[0]
for m in mins:
    ax.scatter([x_dense[m]], [y_nc_dense[m]], color=COLOR_ORANGE, s=100, zorder=5)
ax.annotate("local minimum\n(false summit)", (x_dense[mins[0]], y_nc_dense[mins[0]]),
            xytext=(-2.7, -2), fontsize=9,
            arrowprops=dict(arrowstyle="->", color="black"))
ax.annotate("global minimum", (x_dense[mins[1]], y_nc_dense[mins[1]]),
            xytext=(0.5, -3), fontsize=9,
            arrowprops=dict(arrowstyle="->", color="black"))
ax.set_title("Non-convex function: multiple local minima\n(SGD can get stuck)")
ax.set_ylim(-4, 6)
ax.grid(True, alpha=0.25)

# Saddle point
ax = axes[2]
xs = np.linspace(-2, 2, 50)
ys = np.linspace(-2, 2, 50)
XX, YY = np.meshgrid(xs, ys)
ZZ = XX ** 2 - YY ** 2
cs = ax.contour(XX, YY, ZZ, levels=10, cmap="RdBu_r")
ax.scatter([0], [0], s=200, color="black", marker="*", zorder=5)
ax.text(0.1, 0.15, "saddle point", fontsize=10, fontweight="bold")
ax.set_title("Saddle point: ∇f = 0 but not a minimum\n(common in high-dim non-convex)")
ax.set_xlabel("x"); ax.set_ylabel("y")
ax.set_aspect("equal")

plt.tight_layout()
save("convex_vs_nonconvex.svg")


# ============================================================
# Fig 2: Convexity definition - chord lies above the function
# ============================================================
x = np.linspace(-2, 2, 400)
y = x ** 2

# Pick 2 points
a, b = -1.3, 1.5
xa, xb = a, b
ya, yb = a ** 2, b ** 2
# Linear interpolation t * f(a) + (1-t) * f(b) for t = 0.5
t = 0.5
midx = t * xa + (1 - t) * xb
midy_func = midx ** 2
midy_chord = t * ya + (1 - t) * yb

fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))

# Convex (above)
ax = axes[0]
ax.plot(x, y, color=COLOR_BLUE, lw=2.5)
ax.plot([xa, xb], [ya, yb], color=COLOR_RED, lw=2, ls="--", label="chord")
ax.scatter([xa, xb], [ya, yb], color=COLOR_RED, s=80, zorder=5)
ax.scatter([midx], [midy_func], color=COLOR_GREEN, s=120, zorder=5,
           label=f"f((a+b)/2) = {midy_func:.2f}")
ax.scatter([midx], [midy_chord], color=COLOR_ORANGE, s=120, zorder=5,
           label=f"(f(a)+f(b))/2 = {midy_chord:.2f}")
ax.plot([midx, midx], [midy_func, midy_chord], color="gray", lw=0.7, ls=":")
ax.set_title("Convex f(x²): chord (red) lies ABOVE the function")
ax.legend(fontsize=9, loc="upper center")
ax.grid(True, alpha=0.25)
ax.set_ylim(-0.5, 3)

# Concave (below)
ax = axes[1]
y_log = np.log(np.linspace(0.1, 4, 400))
x_log = np.linspace(0.1, 4, 400)
xa2, xb2 = 0.5, 3.5
ya2, yb2 = np.log(xa2), np.log(xb2)
midx2 = (xa2 + xb2) / 2
midy_func2 = np.log(midx2)
midy_chord2 = 0.5 * ya2 + 0.5 * yb2

ax.plot(x_log, y_log, color=COLOR_BLUE, lw=2.5)
ax.plot([xa2, xb2], [ya2, yb2], color=COLOR_RED, lw=2, ls="--", label="chord")
ax.scatter([xa2, xb2], [ya2, yb2], color=COLOR_RED, s=80, zorder=5)
ax.scatter([midx2], [midy_func2], color=COLOR_GREEN, s=120, zorder=5,
           label=f"f((a+b)/2)")
ax.scatter([midx2], [midy_chord2], color=COLOR_ORANGE, s=120, zorder=5,
           label=f"(f(a)+f(b))/2")
ax.set_title("Concave log(x): chord (red) lies BELOW the function")
ax.legend(fontsize=9, loc="lower right")
ax.grid(True, alpha=0.25)

plt.tight_layout()
save("convex_chord_definition.svg")


# ============================================================
# Fig 3: SGD on convex vs non-convex - SGD trajectories
# ============================================================
rng = np.random.default_rng(0)

# Convex: f(x) = (x-2)^2
def f_conv(x): return (x - 2) ** 2
def df_conv(x): return 2 * (x - 2)

# Non-convex: f(x) = 0.3 x^4 - 1.5 x^2 - 0.5 x + 2
def f_nc(x): return 0.3 * x ** 4 - 1.5 * x ** 2 - 0.5 * x + 2
def df_nc(x): return 1.2 * x ** 3 - 3 * x - 0.5

# Run SGD from multiple starts
fig, axes = plt.subplots(1, 2, figsize=(13, 5))

x_plot = np.linspace(-3, 4, 400)

# Convex
ax = axes[0]
ax.plot(x_plot, f_conv(x_plot), color=COLOR_BLUE, lw=2)
ax.axvline(2, color="black", ls=":", label="global min")
for start, color in [(-2.5, COLOR_RED), (0.5, COLOR_GREEN), (4, COLOR_ORANGE)]:
    x_cur = start
    traj = [x_cur]
    for _ in range(50):
        x_cur -= 0.1 * df_conv(x_cur)
        traj.append(x_cur)
    ax.plot(traj, [f_conv(v) for v in traj], "o-", color=color, lw=1.5, markersize=4,
            alpha=0.7, label=f"start={start}")
ax.set_title("Convex: every start converges to global minimum")
ax.set_xlabel("x"); ax.set_ylabel("f(x)")
ax.set_ylim(-1, 20)
ax.legend(fontsize=9)
ax.grid(True, alpha=0.25)

# Non-convex
ax = axes[1]
ax.plot(x_plot, f_nc(x_plot), color=COLOR_BLUE, lw=2)
ax.axvline(1.62, color="black", ls=":", label="global min")
for start, color in [(-2.5, COLOR_RED), (0.5, COLOR_GREEN), (4, COLOR_ORANGE)]:
    x_cur = start
    traj = [x_cur]
    for _ in range(50):
        x_cur -= 0.1 * df_nc(x_cur)
        traj.append(x_cur)
    ax.plot(traj, [f_nc(v) for v in traj], "o-", color=color, lw=1.5, markersize=4,
            alpha=0.7, label=f"start={start}")
ax.set_title("Non-convex: start point determines which local min you reach")
ax.set_xlabel("x"); ax.set_ylabel("f(x)")
ax.set_ylim(-3, 8)
ax.legend(fontsize=9)
ax.grid(True, alpha=0.25)

plt.tight_layout()
save("convex_sgd_trajectories.svg")


# ============================================================
# Fig 4: Jensen's inequality visualization
# ============================================================
# For convex f: f(E[X]) <= E[f(X)]
# Example: f(x) = x^2, X ~ uniform(-2, 2)
fig, ax = plt.subplots(figsize=(8, 5))

xs_jensen = np.linspace(-3, 3, 400)
ys_jensen = xs_jensen ** 2
ax.plot(xs_jensen, ys_jensen, color=COLOR_BLUE, lw=2.5, label="f(x) = x²")

# E[X] = 0
EX = 0
# f(E[X]) = 0
fEX = EX ** 2
# E[f(X)] = E[X²] = Var(X) for zero-mean = (4)²/12 = 4/3 for uniform(-2,2)
EfX = 4 / 3

ax.scatter([EX], [fEX], color=COLOR_GREEN, s=150, zorder=5,
           label=f"f(E[X]) = {fEX:.2f}")
ax.scatter([EX], [EfX], color=COLOR_RED, s=150, zorder=5,
           label=f"E[f(X)] = {EfX:.2f}")
ax.plot([EX, EX], [fEX, EfX], color="gray", lw=2, ls=":")
ax.annotate(f"Jensen gap\n= {EfX - fEX:.2f}", (EX, (fEX + EfX) / 2),
            xytext=(0.4, 0.7), fontsize=10, color=COLOR_RED)

# Sample distribution to show
sample_x = np.linspace(-2, 2, 9)
for sx in sample_x:
    ax.scatter([sx], [0], color=COLOR_ORANGE, s=30, alpha=0.6)
    ax.scatter([sx], [sx ** 2], color=COLOR_ORANGE, s=30, alpha=0.6)
ax.text(-2, -0.3, "X samples", fontsize=9, color=COLOR_ORANGE)

ax.axhline(0, color="black", lw=0.5)
ax.set_xlabel("x")
ax.set_ylabel("f(x)")
ax.set_title("Jensen's inequality: for convex f,  f(E[X]) ≤ E[f(X)]")
ax.legend(fontsize=10)
ax.grid(True, alpha=0.25)
ax.set_ylim(-1, 7)
plt.tight_layout()
save("convex_jensen.svg")


print("done:", sorted(os.listdir(NOTE_DIR)))
