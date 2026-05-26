"""perceptron ノート用の図を生成するスクリプト。

実行: cd projects/ml && uv run python scripts/notes/perceptron_gen.py
"""
import os

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

COLOR_BLUE = "#7aa6c2"
COLOR_RED = "#e15759"
COLOR_GREEN = "#59a14f"
COLOR_ORANGE = "#f28e2b"
COLOR_GRAY = "#999999"

NOTE_DIR = os.path.expanduser(
    "~/ghq/github.com/nao1215/debimate/projects/ml/notes/ml/perceptron"
)
os.makedirs(NOTE_DIR, exist_ok=True)


def save(name: str) -> None:
    plt.savefig(os.path.join(NOTE_DIR, name), bbox_inches="tight")
    plt.close()


# ============================================================
# Fig 1: AND / OR (linearly separable) vs XOR (not)
# ============================================================
def truth_table(op):
    x = np.array([[0, 0], [0, 1], [1, 0], [1, 1]])
    if op == "AND":
        y = np.array([0, 0, 0, 1])
    elif op == "OR":
        y = np.array([0, 1, 1, 1])
    elif op == "XOR":
        y = np.array([0, 1, 1, 0])
    return x, y

fig, axes = plt.subplots(1, 3, figsize=(13, 4.3))
for ax, op in zip(axes, ["AND", "OR", "XOR"]):
    X, y = truth_table(op)
    # Decision boundary attempts
    if op == "AND":
        # x1 + x2 = 1.5
        xs = np.linspace(-0.5, 1.5, 50)
        ax.plot(xs, 1.5 - xs, color=COLOR_GREEN, lw=2, label="perceptron OK")
    elif op == "OR":
        # x1 + x2 = 0.5
        xs = np.linspace(-0.5, 1.5, 50)
        ax.plot(xs, 0.5 - xs, color=COLOR_GREEN, lw=2, label="perceptron OK")
    elif op == "XOR":
        # No single line works - draw two failed attempts
        xs = np.linspace(-0.5, 1.5, 50)
        ax.plot(xs, 0.5 - xs, color=COLOR_RED, ls="--", lw=1.5,
                label="any line fails")
        ax.plot(xs, 1.5 - xs, color=COLOR_RED, ls="--", lw=1.5)

    ax.scatter(X[y == 0, 0], X[y == 0, 1], s=250, color=COLOR_BLUE, label="0",
               edgecolor="black", linewidth=1.5, zorder=5)
    ax.scatter(X[y == 1, 0], X[y == 1, 1], s=250, color=COLOR_RED, label="1",
               edgecolor="black", linewidth=1.5, zorder=5)
    for (xi, yi), lbl in zip(X, y):
        ax.annotate(str(lbl), (xi, yi), xytext=(xi + 0.06, yi + 0.06), fontsize=10)
    ax.set_xlim(-0.5, 1.5); ax.set_ylim(-0.5, 1.5)
    ax.set_aspect("equal")
    ax.set_title(f"{op}: " + ("linearly separable" if op != "XOR" else "NOT linearly separable"))
    ax.set_xlabel("x1"); ax.set_ylabel("x2")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8)

plt.suptitle("Single-layer perceptron handles AND/OR; XOR requires a hidden layer",
             y=1.02)
plt.tight_layout()
save("perceptron_separability.svg")


# ============================================================
# Fig 2: Perceptron update rule - weights moving with each misclassified point
# ============================================================
rng = np.random.default_rng(0)
# Generate linearly separable 2D data
n = 50
X1 = rng.normal([-1.5, -1.5], 0.7, (n, 2))
X2 = rng.normal([1.5, 1.5], 0.7, (n, 2))
X = np.vstack([X1, X2])
y = np.array([0] * n + [1] * n)

# Add bias term (1) to X
X_aug = np.hstack([X, np.ones((len(X), 1))])
w = np.array([0.0, 0.0, 0.0])
lr = 0.1
weights_history = [w.copy()]

# Perceptron training
for epoch in range(15):
    for i in range(len(X)):
        pred = 1 if X_aug[i] @ w > 0 else 0
        if pred != y[i]:
            w = w + lr * (y[i] - pred) * X_aug[i]
    weights_history.append(w.copy())

# Plot every-N weight boundary
fig, ax = plt.subplots(figsize=(8, 6))
ax.scatter(X[y == 0, 0], X[y == 0, 1], color=COLOR_BLUE, s=30, alpha=0.6, label="class 0")
ax.scatter(X[y == 1, 0], X[y == 1, 1], color=COLOR_RED, s=30, alpha=0.6, label="class 1")
xs = np.linspace(-4, 4, 100)
for i, w_ in enumerate(weights_history):
    if w_[1] != 0:
        ys = -(w_[0] * xs + w_[2]) / w_[1]
        alpha = 0.15 + 0.75 * (i / len(weights_history))
        color = COLOR_GREEN if i == len(weights_history) - 1 else "gray"
        lw = 2.5 if i == len(weights_history) - 1 else 0.6
        label = "final boundary" if i == len(weights_history) - 1 else None
        ax.plot(xs, ys, color=color, alpha=alpha, lw=lw, label=label)

ax.set_xlim(-4, 4); ax.set_ylim(-4, 4)
ax.set_aspect("equal")
ax.set_xlabel("x1"); ax.set_ylabel("x2")
ax.set_title("Perceptron learning: boundary moves with each epoch\n(thin gray = early, thick green = converged)")
ax.legend()
ax.grid(True, alpha=0.25)
plt.tight_layout()
save("perceptron_learning_trajectory.svg")


# ============================================================
# Fig 3: Multilayer perceptron solves XOR
# ============================================================
from sklearn.neural_network import MLPClassifier
X_xor, y_xor = truth_table("XOR")
mlp = MLPClassifier(hidden_layer_sizes=(4,), activation="tanh",
                    max_iter=10000, random_state=0).fit(X_xor, y_xor)

xx, yy = np.meshgrid(np.linspace(-0.5, 1.5, 200), np.linspace(-0.5, 1.5, 200))
Z = mlp.predict(np.c_[xx.ravel(), yy.ravel()]).reshape(xx.shape)

plt.figure(figsize=(6.5, 6))
plt.contourf(xx, yy, Z, alpha=0.3, cmap="coolwarm")
plt.scatter(X_xor[y_xor == 0, 0], X_xor[y_xor == 0, 1], color=COLOR_BLUE, s=250,
            edgecolor="black", linewidth=1.5)
plt.scatter(X_xor[y_xor == 1, 0], X_xor[y_xor == 1, 1], color=COLOR_RED, s=250,
            edgecolor="black", linewidth=1.5)
for (xi, yi), lbl in zip(X_xor, y_xor):
    plt.annotate(str(lbl), (xi, yi), xytext=(xi + 0.06, yi + 0.06), fontsize=11)
plt.xlim(-0.5, 1.5); plt.ylim(-0.5, 1.5)
plt.gca().set_aspect("equal")
plt.title("MLP with 1 hidden layer (4 units) solves XOR\n(non-linear boundary)")
plt.xlabel("x1"); plt.ylabel("x2")
plt.grid(True, alpha=0.25)
plt.tight_layout()
save("perceptron_mlp_xor.svg")


# ============================================================
# Fig 4: Network architecture diagram
# ============================================================
fig, ax = plt.subplots(figsize=(10, 5.5))

# Single perceptron (left)
ax.text(1.5, 4.5, "Single perceptron", ha="center", fontsize=12, fontweight="bold")
# Inputs
for i, y_pos in enumerate([3.5, 2.5, 1.5]):
    circle = patches.Circle((0.5, y_pos), 0.2, facecolor=COLOR_BLUE, edgecolor="black")
    ax.add_patch(circle)
    ax.text(0.1, y_pos, f"x{i+1}", ha="right", va="center", fontsize=10)
# Output neuron
circle = patches.Circle((2.5, 2.5), 0.3, facecolor=COLOR_RED, edgecolor="black")
ax.add_patch(circle)
ax.text(2.5, 2.5, "Σ", ha="center", va="center", fontsize=12, color="white")
# Connections
for y_pos in [3.5, 2.5, 1.5]:
    ax.plot([0.7, 2.2], [y_pos, 2.5], "k-", lw=0.8, alpha=0.6)
ax.text(2.5, 1.7, "step\nfunction", ha="center", fontsize=9, style="italic")
ax.annotate("", xy=(3.7, 2.5), xytext=(2.8, 2.5),
            arrowprops=dict(arrowstyle="->", color="black"))
ax.text(3.9, 2.5, "ŷ", ha="left", va="center", fontsize=11)

# MLP (right)
ax.text(7.5, 4.5, "Multilayer perceptron (1 hidden layer)", ha="center", fontsize=12, fontweight="bold")
# Inputs
for i, y_pos in enumerate([3.5, 2.5, 1.5]):
    circle = patches.Circle((5.5, y_pos), 0.2, facecolor=COLOR_BLUE, edgecolor="black")
    ax.add_patch(circle)
# Hidden layer
for j, y_pos in enumerate([3.8, 2.8, 1.8, 0.8]):
    circle = patches.Circle((7.5, y_pos), 0.2, facecolor=COLOR_ORANGE, edgecolor="black")
    ax.add_patch(circle)
# Output
circle = patches.Circle((9.5, 2.5), 0.3, facecolor=COLOR_RED, edgecolor="black")
ax.add_patch(circle)
# Connections
for y_in in [3.5, 2.5, 1.5]:
    for y_h in [3.8, 2.8, 1.8, 0.8]:
        ax.plot([5.7, 7.3], [y_in, y_h], "k-", lw=0.4, alpha=0.4)
for y_h in [3.8, 2.8, 1.8, 0.8]:
    ax.plot([7.7, 9.2], [y_h, 2.5], "k-", lw=0.4, alpha=0.4)
ax.text(7.5, 0.2, "non-linear\nactivation", ha="center", fontsize=9, style="italic")
ax.annotate("", xy=(10.7, 2.5), xytext=(9.8, 2.5),
            arrowprops=dict(arrowstyle="->", color="black"))
ax.text(10.9, 2.5, "ŷ", ha="left", va="center", fontsize=11)

ax.set_xlim(0, 11.5); ax.set_ylim(0, 5)
ax.axis("off")
plt.tight_layout()
save("perceptron_architecture.svg")


print("done:", sorted(os.listdir(NOTE_DIR)))
