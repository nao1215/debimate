"""backpropagation ノート用の図を生成するスクリプト。

実行: cd projects/ml && uv run python scripts/notes/backpropagation_gen.py
"""
import os

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

COLOR_BLUE = "#7aa6c2"
COLOR_RED = "#e15759"
COLOR_GREEN = "#59a14f"
COLOR_ORANGE = "#f28e2b"
COLOR_PURPLE = "#b07aa1"
COLOR_GRAY = "#999999"

NOTE_DIR = os.path.expanduser(
    "~/ghq/github.com/nao1215/debimate/projects/ml/notes/ml/backpropagation"
)
os.makedirs(NOTE_DIR, exist_ok=True)


def save(name: str) -> None:
    plt.savefig(os.path.join(NOTE_DIR, name), bbox_inches="tight")
    plt.close()


# ============================================================
# Fig 1: Tiny network forward + backward visualization
# ============================================================
# Network: x → z1 = w1*x + b1 → a1 = ReLU(z1) → z2 = w2*a1 + b2 → L = (z2 - y)^2
# Use concrete numbers: x=2, w1=3, b1=-1, w2=0.5, b2=2, y=5
x, w1, b1, w2, b2, y = 2.0, 3.0, -1.0, 0.5, 2.0, 5.0
z1 = w1 * x + b1            # 5
a1 = max(0, z1)              # 5
z2 = w2 * a1 + b2            # 4.5
L = (z2 - y) ** 2            # 0.25

# Backward
dL_dz2 = 2 * (z2 - y)        # -1
dz2_dw2 = a1                  # 5
dz2_db2 = 1
dz2_da1 = w2                  # 0.5
da1_dz1 = 1 if z1 > 0 else 0  # 1
dz1_dw1 = x                   # 2
dz1_db1 = 1
dz1_dx = w1                   # 3

dL_dw2 = dL_dz2 * dz2_dw2          # -5
dL_db2 = dL_dz2 * dz2_db2          # -1
dL_da1 = dL_dz2 * dz2_da1          # -0.5
dL_dz1 = dL_da1 * da1_dz1          # -0.5
dL_dw1 = dL_dz1 * dz1_dw1          # -1
dL_db1 = dL_dz1 * dz1_db1          # -0.5

fig, ax = plt.subplots(figsize=(13, 6))
nodes = [
    ("x", 0.5, 3.5, x, None),
    ("w1", 0.5, 4.5, w1, dL_dw1),
    ("b1", 0.5, 2.5, b1, dL_db1),
    ("z1", 3, 3.5, z1, dL_dz1),
    ("a1", 5, 3.5, a1, None),
    ("w2", 5, 4.7, w2, dL_dw2),
    ("b2", 5, 2.3, b2, dL_db2),
    ("z2", 7.5, 3.5, z2, dL_dz2),
    ("L", 10, 3.5, L, 1),  # dL/dL = 1
]
node_pos = {}
for name, xx, yy, val, grad in nodes:
    node_pos[name] = (xx, yy)
    circle = patches.Circle((xx, yy), 0.5, facecolor="white", edgecolor="black", lw=1.5)
    ax.add_patch(circle)
    ax.text(xx, yy + 0.1, name, ha="center", va="center", fontsize=10, fontweight="bold")
    ax.text(xx, yy - 0.2, f"={val:.1f}", ha="center", va="center", fontsize=9, color=COLOR_BLUE)
    if grad is not None:
        ax.text(xx, yy + 0.7, f"∂L/∂{name}={grad:+.1f}", ha="center", fontsize=8.5, color=COLOR_RED)

# Forward arrows (blue)
edges_fwd = [
    ("x", "z1"), ("w1", "z1"), ("b1", "z1"),
    ("z1", "a1"),
    ("a1", "z2"), ("w2", "z2"), ("b2", "z2"),
    ("z2", "L"),
]
for src, dst in edges_fwd:
    x0, y0 = node_pos[src]
    x1, y1 = node_pos[dst]
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                arrowprops=dict(arrowstyle="->", color=COLOR_BLUE, lw=1.5,
                                connectionstyle="arc3,rad=0.0",
                                shrinkA=20, shrinkB=20))

ax.text(5, 5.6, "Forward pass (blue): compute values left → right",
        ha="center", fontsize=11, color=COLOR_BLUE, fontweight="bold")
ax.text(5, 1.4, "Backward pass (red labels): compute gradients right → left via chain rule",
        ha="center", fontsize=11, color=COLOR_RED, fontweight="bold")

ax.set_xlim(-0.5, 11)
ax.set_ylim(1, 6)
ax.set_aspect("equal")
ax.axis("off")
plt.tight_layout()
save("backprop_tiny_network.svg")


# ============================================================
# Fig 2: Computational graph for a slightly bigger model
# ============================================================
fig, ax = plt.subplots(figsize=(13, 6))

# 2 inputs → 2 hidden → 1 output
positions = {
    "x1": (1, 5), "x2": (1, 1),
    "h1": (4, 5), "h2": (4, 1),
    "y_hat": (7, 3), "y": (7, 5.5),
    "L": (10, 3),
}

for name, (xx, yy) in positions.items():
    if name in ["x1", "x2", "y"]:
        color = COLOR_BLUE
    elif name in ["h1", "h2"]:
        color = COLOR_ORANGE
    elif name == "y_hat":
        color = COLOR_GREEN
    else:
        color = COLOR_RED
    circle = patches.Circle((xx, yy), 0.35, facecolor=color, edgecolor="black", lw=1.2)
    ax.add_patch(circle)
    ax.text(xx, yy, name, ha="center", va="center", fontsize=10, color="white",
            fontweight="bold")

edges = [
    ("x1", "h1", "w_{11}"), ("x1", "h2", "w_{12}"),
    ("x2", "h1", "w_{21}"), ("x2", "h2", "w_{22}"),
    ("h1", "y_hat", "v_1"), ("h2", "y_hat", "v_2"),
    ("y_hat", "L", ""), ("y", "L", ""),
]
for src, dst, label in edges:
    x0, y0 = positions[src]
    x1, y1 = positions[dst]
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                arrowprops=dict(arrowstyle="->", color="black", lw=0.8,
                                shrinkA=14, shrinkB=14))
    if label:
        ax.text((x0 + x1) / 2, (y0 + y1) / 2 + 0.15, label, ha="center",
                fontsize=8, color=COLOR_GRAY)

# Annotate forward / backward
ax.annotate("", xy=(10.7, 1.5), xytext=(0.3, 1.5),
            arrowprops=dict(arrowstyle="->", color=COLOR_BLUE, lw=2))
ax.text(5.5, 0.7, "FORWARD: compute h, y_hat, L (left→right)",
        ha="center", color=COLOR_BLUE, fontsize=11, fontweight="bold")

ax.annotate("", xy=(0.3, 6.7), xytext=(10.7, 6.7),
            arrowprops=dict(arrowstyle="->", color=COLOR_RED, lw=2))
ax.text(5.5, 7.0, "BACKWARD: propagate ∂L/∂(weight) via chain rule (right→left)",
        ha="center", color=COLOR_RED, fontsize=11, fontweight="bold")

ax.set_xlim(-0.5, 11.5)
ax.set_ylim(-0.2, 7.5)
ax.set_aspect("equal")
ax.axis("off")
plt.tight_layout()
save("backprop_computational_graph.svg")


# ============================================================
# Fig 3: Chain rule visualization - 1D
# ============================================================
# L = f(g(h(x)))
# Show how dL/dx = dL/df * df/dg * dg/dh * dh/dx
fig, ax = plt.subplots(figsize=(11, 4))

stages = [
    (1, "x"),
    (3, "h = sin(x)"),
    (5, "g = h²"),
    (7, "f = exp(g)"),
    (9, "L = log(f) + ..."),
]
gradients = [
    "∂L/∂f = 1/f",
    "∂f/∂g = exp(g)",
    "∂g/∂h = 2h",
    "∂h/∂x = cos(x)",
]

for x_pos, label in stages:
    rect = patches.Rectangle((x_pos - 0.5, 1.5), 1.0, 1.0,
                              facecolor=COLOR_BLUE, alpha=0.6,
                              edgecolor="black", linewidth=1.2)
    ax.add_patch(rect)
    ax.text(x_pos, 2, label, ha="center", va="center", fontsize=10)

# Forward arrows
for i in range(len(stages) - 1):
    ax.annotate("", xy=(stages[i+1][0] - 0.55, 2), xytext=(stages[i][0] + 0.55, 2),
                arrowprops=dict(arrowstyle="->", color=COLOR_BLUE, lw=1.5))

# Gradients (reversed)
for i, grad in enumerate(gradients):
    x_pos = (stages[-(i+1)][0] + stages[-(i+2)][0]) / 2
    ax.text(x_pos, 0.7, grad, ha="center", fontsize=9, color=COLOR_RED)
    ax.annotate("", xy=(stages[-(i+2)][0] + 0.55, 1.0),
                xytext=(stages[-(i+1)][0] - 0.55, 1.0),
                arrowprops=dict(arrowstyle="->", color=COLOR_RED, lw=1.5))

ax.text(5, 3.5, "Chain rule:  ∂L/∂x = (∂L/∂f) × (∂f/∂g) × (∂g/∂h) × (∂h/∂x)",
        ha="center", fontsize=12, fontweight="bold")
ax.set_xlim(0, 10.5)
ax.set_ylim(0, 4)
ax.set_aspect("equal")
ax.axis("off")
plt.tight_layout()
save("backprop_chain_rule.svg")


# ============================================================
# Fig 4: Gradient magnitude per layer in deep nets (vanishing)
# ============================================================
# Simulate: 10-layer net forward, look at gradient magnitude at each layer for sigmoid vs ReLU
n_layers = 10
np.random.seed(0)

# For each activation, simulate gradient flow backward
def gradient_magnitudes(activation, n_layers=10, n_trials=100):
    """Roughly estimate the per-layer gradient norm at the start of training."""
    grads = []
    for layer in range(n_layers):
        # Each layer attenuates by a factor depending on activation
        if activation == "sigmoid":
            # Initial weights normal(0,1), sigmoid grad ~ 0.25 at z=0
            factor = 0.25 * 1.0  # weight initialization standard normal
        elif activation == "tanh":
            factor = 1.0 * 1.0
        elif activation == "relu":
            factor = 0.5 * 1.0  # ReLU active ~50% of time at init
        else:
            factor = 0.5
        if layer == 0:
            grads.append(1.0)
        else:
            grads.append(grads[-1] * factor)
    return np.array(grads)

layers = np.arange(1, n_layers + 1)
plt.figure(figsize=(8.5, 4.5))
for act, color in [("sigmoid", COLOR_BLUE), ("tanh", COLOR_GREEN), ("relu", COLOR_RED)]:
    g = gradient_magnitudes(act, n_layers=n_layers)
    plt.plot(layers, g, "o-", color=color, lw=2, label=act)
plt.yscale("log")
plt.xlabel("layer (from output)")
plt.ylabel("gradient magnitude (log scale)")
plt.title("Gradient shrinks by activation derivative each layer\nsigmoid in deep nets → vanishing")
plt.legend()
plt.grid(True, alpha=0.25)
plt.tight_layout()
save("backprop_vanishing.svg")


print("done:", sorted(os.listdir(NOTE_DIR)))
