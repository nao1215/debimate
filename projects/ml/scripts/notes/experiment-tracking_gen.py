"""experiment-tracking ノート用の図を生成するスクリプト。

実行: cd projects/ml && uv run python scripts/notes/experiment-tracking_gen.py
"""
import os
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

COLOR_BLUE = "#7aa6c2"
COLOR_RED = "#e15759"
COLOR_GREEN = "#59a14f"
COLOR_ORANGE = "#f28e2b"
COLOR_GRAY = "#999999"

# projects/ml/scripts/notes/ から見た Page Bundle（checkout の場所に依存しない）
NOTE_DIR = str(Path(__file__).resolve().parents[2] / "notes" / "mlops" / "experiment-tracking")
os.makedirs(NOTE_DIR, exist_ok=True)


def save(name: str) -> None:
    path = os.path.join(NOTE_DIR, name)
    plt.savefig(path, bbox_inches="tight")
    plt.close()
    with open(path, encoding="utf-8") as file:
        content = file.read()
    with open(path, "w", encoding="utf-8") as file:
        file.write("\n".join(line.rstrip() for line in content.splitlines()) + "\n")


# ============================================================
# Fig 1: Hyperparameter sweep heatmap (lr × batch_size → val_acc)
# ============================================================
lrs = [1e-4, 3e-4, 1e-3, 3e-3, 1e-2]
batches = [16, 32, 64, 128, 256]
val_acc = np.array([
    [0.71, 0.74, 0.76, 0.73, 0.68],
    [0.78, 0.82, 0.85, 0.82, 0.76],
    [0.81, 0.87, 0.92, 0.88, 0.80],
    [0.77, 0.84, 0.88, 0.83, 0.74],
    [0.66, 0.70, 0.75, 0.69, 0.61],
])

fig, ax = plt.subplots(figsize=(7, 5))
im = ax.imshow(val_acc, cmap="viridis", aspect="auto", vmin=0.60, vmax=0.95)
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
ax.set_title("Synthetic example: 25 tracked runs")
plt.tight_layout()
save("experiment_sweep_heatmap.svg")


# ============================================================
# Fig 2: Multiple training curves overlaid (compare runs)
# ============================================================
epochs = np.arange(1, 51)
configs = [
    ("run #12 lr=1e-2 bs=128", 0.55, 0.020, COLOR_GRAY),
    ("run #18 lr=3e-3 bs=64", 0.82, 0.045, COLOR_ORANGE),
    ("run #23 lr=1e-3 bs=64", 0.91, 0.060, COLOR_GREEN),
    ("run #27 lr=1e-4 bs=32", 0.79, 0.015, COLOR_BLUE),
]

plt.figure(figsize=(8.5, 4.5))
for label, asymptote, rate, color in configs:
    curve = asymptote * (1 - np.exp(-rate * epochs))
    plt.plot(epochs, curve, color=color, lw=2, label=label)
plt.xlabel("epoch")
plt.ylabel("val accuracy")
plt.title("Synthetic example: compare training trajectories")
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
    "lr": rng3.uniform(-4, -1, n_runs),            # log10
    "batch_size": rng3.choice(np.arange(4, 9), n_runs),  # log2
    "dropout": rng3.uniform(0.0, 0.5, n_runs),
    "weight_decay": rng3.uniform(-6, -2, n_runs),  # log10
}
# 仮想の val_acc。最良は lr=1e-3, batch_size=64, dropout=0.2, weight_decay=1e-4 付近で、
# 外れても 0.6 程度までしか下がらないよう罰則を小さくする（負の精度を作らない）
val = (0.92
       - 0.04 * (data["lr"] - (-3.0)) ** 2
       - 0.01 * (data["batch_size"] - 6) ** 2
       - 0.6 * (data["dropout"] - 0.2) ** 2
       - 0.01 * (data["weight_decay"] - (-4)) ** 2
       + rng3.normal(0, 0.01, n_runs))
assert val.min() > 0.5 and val.max() < 1.0, (val.min(), val.max())

# 各軸の目盛りは元の値で書き、線だけを 0-1 に正規化して描く
axes_spec = [
    ("lr", (-4, -1), [(-4, "1e-4"), (-3, "1e-3"), (-2, "1e-2"), (-1, "1e-1")]),
    ("batch_size", (4, 8), [(v, str(2 ** v)) for v in range(4, 9)]),
    ("dropout", (0.0, 0.5), [(v, f"{v:.1f}") for v in np.arange(0.0, 0.51, 0.1)]),
    ("weight_decay", (-6, -2), [(v, f"1e{v}") for v in range(-6, -1)]),
]
arr_norm = np.array([(data[name] - lo) / (hi - lo) for name, (lo, hi), _ in axes_spec])

fig, ax = plt.subplots(figsize=(10, 5))
xs = np.arange(len(axes_spec))
cmap = plt.cm.viridis
norm = plt.Normalize(vmin=0.60, vmax=0.95)
top5 = set(np.argsort(val)[-5:])
for k in np.argsort(val):  # 低スコアから描き、高スコアの線を上に重ねる
    ax.plot(xs, arr_norm[:, k], color=cmap(norm(val[k])),
            alpha=0.95 if k in top5 else 0.45, lw=2.6 if k in top5 else 1.2)
for x, (name, (lo, hi), ticks) in zip(xs, axes_spec):
    ax.axvline(x, color="#555555", lw=1)
    for value, label in ticks:
        y = (value - lo) / (hi - lo)
        ax.plot([x - 0.03, x], [y, y], color="#555555", lw=1)
        ax.text(x - 0.05, y, label, ha="right", va="center", fontsize=8, color="#333333")
ax.set_xticks(xs, [name for name, _, _ in axes_spec])
ax.set_yticks([])
ax.set_xlim(-0.4, len(axes_spec) - 0.8)
ax.set_ylim(-0.05, 1.05)
for side in ("left", "right", "top"):
    ax.spines[side].set_visible(False)
ax.set_title("Synthetic example: each line = 1 run, color = val_acc (top 5 bold)")
sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
fig.colorbar(sm, ax=ax, label="val_acc")
plt.tight_layout()
save("experiment_parallel_coords.svg")


print("done:", sorted(os.listdir(NOTE_DIR)))
