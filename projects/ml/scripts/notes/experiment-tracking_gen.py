"""experiment-tracking ノート用の図を生成するスクリプト。

実行: cd projects/ml && uv run python scripts/notes/experiment-tracking_gen.py
"""
import os

import matplotlib.pyplot as plt
import numpy as np

COLOR_BLUE = "#7aa6c2"
COLOR_RED = "#e15759"
COLOR_GREEN = "#59a14f"
COLOR_ORANGE = "#f28e2b"
COLOR_GRAY = "#999999"

NOTE_DIR = os.path.expanduser(
    "~/ghq/github.com/nao1215/debimate/projects/ml/notes/mlops/experiment-tracking"
)
os.makedirs(NOTE_DIR, exist_ok=True)


def save(name: str) -> None:
    plt.savefig(os.path.join(NOTE_DIR, name), bbox_inches="tight")
    plt.close()


# ============================================================
# Fig 1: Hyperparameter sweep heatmap (lr × batch_size → val_acc)
# ============================================================
rng = np.random.default_rng(0)
lrs = [1e-4, 3e-4, 1e-3, 3e-3, 1e-2]
batches = [16, 32, 64, 128, 256]
# Simulate val_acc surface peaking at (lr=1e-3, bs=64)
val_acc = np.zeros((len(lrs), len(batches)))
for i, lr in enumerate(lrs):
    for j, bs in enumerate(batches):
        # Concave around best (1e-3, 64)
        d_lr = np.log10(lr / 1e-3)
        d_bs = np.log2(bs / 64)
        val_acc[i, j] = 0.92 - 0.05 * d_lr ** 2 - 0.02 * d_bs ** 2 + rng.normal(0, 0.005)

fig, ax = plt.subplots(figsize=(7, 5))
im = ax.imshow(val_acc, cmap="viridis", aspect="auto", vmin=0.75, vmax=0.93)
ax.set_xticks(range(len(batches))); ax.set_xticklabels(batches)
ax.set_yticks(range(len(lrs))); ax.set_yticklabels([f"{lr:.0e}" for lr in lrs])
ax.set_xlabel("batch_size"); ax.set_ylabel("learning_rate")
for i in range(len(lrs)):
    for j in range(len(batches)):
        color = "white" if val_acc[i, j] < 0.85 else "black"
        ax.text(j, i, f"{val_acc[i, j]:.3f}", ha="center", va="center",
                color=color, fontsize=9)
# Best mark
best = np.unravel_index(np.argmax(val_acc), val_acc.shape)
ax.scatter([best[1]], [best[0]], s=300, facecolors="none", edgecolors=COLOR_RED, linewidths=2.5)
plt.colorbar(im, ax=ax, label="val_acc")
ax.set_title("Hyperparameter sweep: 25 runs logged to tracking server")
plt.tight_layout()
save("experiment_sweep_heatmap.svg")


# ============================================================
# Fig 2: Multiple training curves overlaid (compare runs)
# ============================================================
rng2 = np.random.default_rng(1)
epochs = np.arange(1, 51)
runs = []
configs = [
    ("run #12 lr=1e-2 bs=128", 0.55, 0.020, COLOR_GRAY),
    ("run #18 lr=3e-3 bs=64", 0.82, 0.045, COLOR_ORANGE),
    ("run #23 lr=1e-3 bs=64", 0.91, 0.060, COLOR_GREEN),
    ("run #27 lr=1e-4 bs=32", 0.79, 0.015, COLOR_BLUE),
]

plt.figure(figsize=(8.5, 4.5))
for label, asymptote, rate, color in configs:
    curve = asymptote * (1 - np.exp(-rate * epochs)) + rng2.normal(0, 0.005, 50)
    plt.plot(epochs, curve, color=color, lw=2, label=label)
plt.xlabel("epoch")
plt.ylabel("val accuracy")
plt.title("Tracked runs let you compare training trajectories side by side")
plt.legend(loc="lower right", fontsize=9)
plt.grid(True, alpha=0.25)
plt.tight_layout()
save("experiment_compare_runs.svg")


# ============================================================
# Fig 3: Parallel coordinates plot for multi-dim hyperparam exploration
# ============================================================
n_runs = 40
rng3 = np.random.default_rng(2)
data = {
    "lr (log10)": rng3.uniform(-4, -1, n_runs),
    "batch_size (log2)": rng3.choice(np.arange(4, 9), n_runs),
    "dropout": rng3.uniform(0.0, 0.5, n_runs),
    "weight_decay (log10)": rng3.uniform(-6, -2, n_runs),
}
# val_acc model
val = []
for k in range(n_runs):
    s = -0.5 * (data["lr (log10)"][k] - (-3.0)) ** 2 \
        - 0.05 * (data["batch_size (log2)"][k] - 6) ** 2 \
        - 1.2 * (data["dropout"][k] - 0.2) ** 2 \
        - 0.05 * (data["weight_decay (log10)"][k] - (-4)) ** 2 \
        + 0.92 + rng3.normal(0, 0.015)
    val.append(s)
val = np.array(val)

# Normalize each axis
axes_names = list(data.keys())
arr = np.array([data[n] for n in axes_names])
arr_norm = (arr - arr.min(axis=1, keepdims=True)) / (
    arr.max(axis=1, keepdims=True) - arr.min(axis=1, keepdims=True))

plt.figure(figsize=(10, 5))
xs = np.arange(len(axes_names))
cmap = plt.cm.viridis
val_norm = (val - val.min()) / (val.max() - val.min())
for k in range(n_runs):
    plt.plot(xs, arr_norm[:, k], color=cmap(val_norm[k]),
             alpha=0.55, lw=1.4)
plt.xticks(xs, axes_names, rotation=15)
plt.ylim(-0.05, 1.05)
plt.title("Parallel coordinates: each line = 1 logged run, color = val_acc")
sm = plt.cm.ScalarMappable(cmap=cmap)
sm.set_array(val)
plt.colorbar(sm, ax=plt.gca(), label="val_acc")
plt.grid(True, alpha=0.25, axis="y")
plt.tight_layout()
save("experiment_parallel_coords.svg")


print("done:", sorted(os.listdir(NOTE_DIR)))
