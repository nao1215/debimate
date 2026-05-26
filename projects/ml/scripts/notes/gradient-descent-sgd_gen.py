"""gradient-descent-sgd ノート用の図を生成するスクリプト。

実行: cd projects/ml && uv run python scripts/notes/gradient-descent-sgd_gen.py
"""
import os

import matplotlib.pyplot as plt
import numpy as np

COLOR_BLUE = "#7aa6c2"
COLOR_RED = "#e15759"
COLOR_GREEN = "#59a14f"
COLOR_GRAY = "#999999"
COLOR_ORANGE = "#f1a340"

NOTE_DIR = os.path.expanduser(
    "~/ghq/github.com/nao1215/debimate/projects/ml/notes/math/gradient-descent-sgd"
)
os.makedirs(NOTE_DIR, exist_ok=True)


def save(name: str) -> None:
    plt.savefig(os.path.join(NOTE_DIR, name), bbox_inches="tight")
    plt.close()


# ============================================================
# Fig 1: 1D gradient descent on a parabola
# ============================================================
def f(x):
    return (x - 3) ** 2 + 1

def df(x):
    return 2 * (x - 3)

x_grid = np.linspace(-1, 7, 200)

plt.figure(figsize=(7, 4))
plt.plot(x_grid, f(x_grid), color=COLOR_BLUE, lw=2, label="f(x) = (x-3)^2 + 1")

x_cur = -0.5
lr = 0.2
history = [x_cur]
for _ in range(8):
    x_cur = x_cur - lr * df(x_cur)
    history.append(x_cur)
history = np.array(history)
plt.plot(history, f(history), "o-", color=COLOR_RED, lw=1.5, label=f"GD steps (lr={lr})")
for i, xi in enumerate(history[:5]):
    plt.annotate(f"step {i}", (xi, f(xi) + 0.4), fontsize=8,
                 ha="center", color=COLOR_RED)
plt.scatter([3.0], [1.0], color="black", marker="*", s=180, zorder=5, label="optimum")
plt.title("Gradient descent on a 1D parabola")
plt.xlabel("x"); plt.ylabel("f(x)")
plt.legend(); plt.grid(True, alpha=0.25)
plt.tight_layout()
save("gd_1d.svg")


# ============================================================
# Fig 2: Learning rate effect (too small / just right / too large)
# ============================================================
fig, axes = plt.subplots(1, 3, figsize=(13, 4), sharey=True)
lrs = [0.05, 0.3, 1.05]
titles = ["lr too small (slow)", "lr just right", "lr too large (overshoots & diverges)"]

for ax, lr, title in zip(axes, lrs, titles):
    ax.plot(x_grid, f(x_grid), color=COLOR_BLUE, lw=2)
    x_cur = -0.5
    history = [x_cur]
    for _ in range(12):
        x_cur = x_cur - lr * df(x_cur)
        if abs(x_cur) > 50:
            history.append(np.clip(x_cur, -1, 7))
            break
        history.append(x_cur)
    history = np.array(history)
    history_clip = np.clip(history, x_grid.min(), x_grid.max())
    ax.plot(history_clip, f(history_clip), "o-", color=COLOR_RED, lw=1.4,
            markersize=5, alpha=0.8)
    ax.scatter([3.0], [1.0], color="black", marker="*", s=140, zorder=5)
    ax.set_title(f"{title}\n(lr={lr})")
    ax.set_xlabel("x")
    ax.set_ylim(0, 30)
    ax.grid(True, alpha=0.25)
axes[0].set_ylabel("f(x)")
plt.tight_layout()
save("gd_learning_rate.svg")


# ============================================================
# Fig 3: 2D contour and descent trajectory
# ============================================================
def L(w, b):
    return (w - 2) ** 2 + 3 * (b - 0.5) ** 2

def dL(w, b):
    return 2 * (w - 2), 6 * (b - 0.5)

w_grid = np.linspace(-1, 5, 200)
b_grid = np.linspace(-2, 3, 200)
WW, BB = np.meshgrid(w_grid, b_grid)
LL = L(WW, BB)

plt.figure(figsize=(6.5, 5))
cs = plt.contour(WW, BB, LL, levels=15, cmap="Blues_r")
plt.clabel(cs, inline=True, fontsize=7)

w_cur, b_cur = -0.5, 2.2
lr = 0.12
hist_w, hist_b = [w_cur], [b_cur]
for _ in range(20):
    gw, gb = dL(w_cur, b_cur)
    w_cur = w_cur - lr * gw
    b_cur = b_cur - lr * gb
    hist_w.append(w_cur)
    hist_b.append(b_cur)
plt.plot(hist_w, hist_b, "o-", color=COLOR_RED, lw=1.5, markersize=4,
         label=f"GD trajectory (lr={lr})")
plt.scatter([2.0], [0.5], color="black", marker="*", s=180, zorder=5, label="optimum")
plt.title("Gradient descent on 2D loss surface\n(steps perpendicular to contours)")
plt.xlabel("w"); plt.ylabel("b")
plt.legend()
plt.tight_layout()
save("gd_2d_trajectory.svg")


# ============================================================
# Fig 4: Full-batch GD vs SGD vs mini-batch (noisy trajectories)
# ============================================================
# Use a synthetic regression dataset
rng = np.random.default_rng(0)
n_data = 500
x_data = rng.uniform(-2, 2, n_data)
y_data = 2.0 * x_data + 0.5 + rng.normal(0, 0.5, n_data)

def loss_full(w, b):
    return np.mean((y_data - (w * x_data + b)) ** 2)

def grad_full(w, b, idx=None):
    if idx is None:
        xs, ys = x_data, y_data
    else:
        xs, ys = x_data[idx], y_data[idx]
    err = ys - (w * xs + b)
    gw = -2 * np.mean(xs * err)
    gb = -2 * np.mean(err)
    return gw, gb

def run(method, lr, steps, batch=None):
    w_cur, b_cur = -1.0, -1.5
    hist = [(w_cur, b_cur)]
    for s in range(steps):
        if method == "full":
            gw, gb = grad_full(w_cur, b_cur)
        elif method == "sgd":
            i = rng.integers(0, n_data)
            gw, gb = grad_full(w_cur, b_cur, idx=[i])
        elif method == "mini":
            idx = rng.choice(n_data, size=batch, replace=False)
            gw, gb = grad_full(w_cur, b_cur, idx=idx)
        w_cur -= lr * gw
        b_cur -= lr * gb
        hist.append((w_cur, b_cur))
    return np.array(hist)

steps = 80
traj_full = run("full", lr=0.1, steps=steps)
traj_sgd = run("sgd", lr=0.05, steps=steps)
traj_mini = run("mini", lr=0.1, steps=steps, batch=32)

w_grid = np.linspace(-1.5, 3.5, 200)
b_grid = np.linspace(-2, 2.5, 200)
WW, BB = np.meshgrid(w_grid, b_grid)
LL = np.array([[loss_full(w, b) for w in w_grid] for b in b_grid])

fig, axes = plt.subplots(1, 3, figsize=(14, 4.5), sharex=True, sharey=True)
titles = ["Full-batch GD (smooth, all data per step)",
          "SGD batch=1 (noisy, 1 sample per step)",
          "Mini-batch GD batch=32 (compromise)"]
trajs = [traj_full, traj_sgd, traj_mini]
colors = [COLOR_BLUE, COLOR_RED, COLOR_GREEN]

for ax, traj, title, color in zip(axes, trajs, titles, colors):
    ax.contour(WW, BB, LL, levels=12, cmap="Blues_r", alpha=0.6)
    ax.plot(traj[:, 0], traj[:, 1], "o-", color=color, lw=0.9, markersize=3, alpha=0.85)
    ax.scatter([2.0], [0.5], color="black", marker="*", s=140, zorder=5)
    ax.set_title(title, fontsize=10)
    ax.set_xlabel("w")
axes[0].set_ylabel("b")
plt.tight_layout()
save("gd_vs_sgd.svg")


print("done:", sorted(os.listdir(NOTE_DIR)))
