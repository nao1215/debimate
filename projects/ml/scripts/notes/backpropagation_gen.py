"""backpropagation ノート用の図を生成するスクリプト。

実行: cd projects/ml && uv run python scripts/notes/backpropagation_gen.py
"""
import os
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

plt.rcParams.update({"svg.hashsalt": "debimate"})

COLOR_BLUE = "#4e79a7"
COLOR_RED = "#c0392b"
COLOR_GREEN = "#59a14f"
COLOR_GRAY = "#666666"
FILL_INPUT = "#dde8f0"
FILL_HIDDEN = "#f6e3c8"
FILL_OUTPUT = "#dcebd5"
FILL_LOSS = "#f3d6d3"

NOTE_DIR = Path(__file__).resolve().parents[2] / "notes" / "ml" / "backpropagation"
NOTE_DIR.mkdir(parents=True, exist_ok=True)


def save(name: str) -> None:
    plt.savefig(NOTE_DIR / name, bbox_inches="tight")
    plt.close()


def fmt(v: float) -> str:
    return f"{v:g}"


# ============================================================
# Fig 1: Tiny network forward + backward visualization
# ============================================================
# Network: x → z1 = w1*x + b1 → a1 = ReLU(z1) → z2 = w2*a1 + b2 → L = (z2 - y)^2
x, w1, b1, w2, b2, y = 2.0, 3.0, -1.0, 0.5, 2.0, 5.0
z1 = w1 * x + b1            # 5
a1 = max(0, z1)              # 5
z2 = w2 * a1 + b2            # 4.5
L = (z2 - y) ** 2            # 0.25

dL_dz2 = 2 * (z2 - y)        # -1
dL_dw2 = dL_dz2 * a1          # -5
dL_db2 = dL_dz2 * 1           # -1
dL_da1 = dL_dz2 * w2          # -0.5
dL_dz1 = dL_da1 * (1 if z1 > 0 else 0)  # -0.5
dL_dw1 = dL_dz1 * x           # -1
dL_db1 = dL_dz1 * 1           # -0.5

fig, ax = plt.subplots(figsize=(12, 5.2))
R = 0.45
nodes = [
    ("x", 0.5, 3.0, x, None),
    ("w1", 0.5, 4.6, w1, dL_dw1),
    ("b1", 0.5, 1.4, b1, dL_db1),
    ("z1", 3.0, 3.0, z1, dL_dz1),
    ("a1", 5.3, 3.0, a1, dL_da1),
    ("w2", 5.3, 4.6, w2, dL_dw2),
    ("b2", 5.3, 1.4, b2, dL_db2),
    ("z2", 7.8, 3.0, z2, dL_dz2),
    ("L", 10.3, 3.0, L, 1.0),
]
node_pos = {}
for name, xx, yy, val, grad in nodes:
    node_pos[name] = (xx, yy)
    ax.add_patch(patches.Circle((xx, yy), R, facecolor="white", edgecolor="black", lw=1.3))
    ax.text(xx, yy + 0.12, name, ha="center", va="center", fontsize=11, fontweight="normal")
    ax.text(xx, yy - 0.18, f"={fmt(val)}", ha="center", va="center", fontsize=9.5,
            color=COLOR_BLUE)
    if grad is not None:
        ax.text(xx + R + 0.08, yy + R - 0.05, f"∂L/∂{name}={fmt(grad)}", ha="left",
                va="bottom", fontsize=9.5, color=COLOR_RED)

edges_fwd = [
    ("x", "z1"), ("w1", "z1"), ("b1", "z1"),
    ("z1", "a1"),
    ("a1", "z2"), ("w2", "z2"), ("b2", "z2"),
    ("z2", "L"),
]
for src, dst in edges_fwd:
    ax.annotate("", xy=node_pos[dst], xytext=node_pos[src],
                arrowprops=dict(arrowstyle="->", color=COLOR_BLUE, lw=1.4,
                                shrinkA=17, shrinkB=17))

ax.text(5.5, 5.55, "forward (blue): values, left → right",
        ha="center", fontsize=11, color=COLOR_BLUE)
ax.text(5.5, 0.45, "backward (red): ∂L/∂node, right → left by the chain rule",
        ha="center", fontsize=11, color=COLOR_RED)

ax.set_xlim(-0.2, 12.0)
ax.set_ylim(0.2, 5.9)
ax.set_aspect("equal")
ax.axis("off")
save("backprop_tiny_network.svg")


# ============================================================
# Fig 2: Computational graph for a slightly bigger model
# ============================================================
fig, ax = plt.subplots(figsize=(11, 5.6))

positions = {
    "x1": (1, 5), "x2": (1, 1),
    "h1": (4, 5), "h2": (4, 1),
    "ŷ": (7, 3), "y": (7, 5.5),
    "L": (10, 3),
}
fills = {"x1": FILL_INPUT, "x2": FILL_INPUT, "y": FILL_INPUT,
         "h1": FILL_HIDDEN, "h2": FILL_HIDDEN, "ŷ": FILL_OUTPUT, "L": FILL_LOSS}
for name, (xx, yy) in positions.items():
    ax.add_patch(patches.Circle((xx, yy), 0.4, facecolor=fills[name],
                                edgecolor="black", lw=1.2))
    ax.text(xx, yy, name, ha="center", va="center", fontsize=12)

# (src, dst, label, label position as fraction from src)
edges = [
    ("x1", "h1", r"$w_{11}$", 0.5), ("x1", "h2", r"$w_{12}$", 0.25),
    ("x2", "h1", r"$w_{21}$", 0.25), ("x2", "h2", r"$w_{22}$", 0.5),
    ("h1", "ŷ", r"$v_1$", 0.5), ("h2", "ŷ", r"$v_2$", 0.5),
    ("ŷ", "L", "", 0.5), ("y", "L", "", 0.5),
]
for src, dst, label, frac in edges:
    x0, y0 = positions[src]
    x1, y1 = positions[dst]
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                arrowprops=dict(arrowstyle="->", color="black", lw=0.9,
                                shrinkA=16, shrinkB=16))
    if label:
        lx, ly = x0 + (x1 - x0) * frac, y0 + (y1 - y0) * frac
        ax.text(lx, ly + 0.25, label, ha="center", fontsize=11, color=COLOR_GRAY)

ax.annotate("", xy=(10.6, -0.1), xytext=(0.4, -0.1),
            arrowprops=dict(arrowstyle="->", color=COLOR_BLUE, lw=2))
ax.text(5.5, -0.55, "forward: compute h, ŷ, L (left → right)",
        ha="center", color=COLOR_BLUE, fontsize=11)
ax.annotate("", xy=(0.4, 6.4), xytext=(10.6, 6.4),
            arrowprops=dict(arrowstyle="->", color=COLOR_RED, lw=2))
ax.text(5.5, 6.65, "backward: propagate ∂L/∂(weight) by the chain rule (right → left)",
        ha="center", color=COLOR_RED, fontsize=11)

ax.set_xlim(0, 11)
ax.set_ylim(-0.9, 7.1)
ax.set_aspect("equal")
ax.axis("off")
save("backprop_computational_graph.svg")


# ============================================================
# Fig 3: Chain rule visualization - 1D
# ============================================================
# L = log(f), f = exp(g), g = h^2, h = sin(x)
fig, ax = plt.subplots(figsize=(11, 3.6))

stages = [
    (1, "x"),
    (3.5, "h = sin(x)"),
    (6, "g = h²"),
    (8.5, "f = exp(g)"),
    (11, "L = log(f)"),
]
gradients = [
    "∂L/∂f = 1/f",
    "∂f/∂g = exp(g)",
    "∂g/∂h = 2h",
    "∂h/∂x = cos(x)",
]
BW = 1.7
for x_pos, label in stages:
    ax.add_patch(patches.Rectangle((x_pos - BW / 2, 1.6), BW, 0.8, facecolor=FILL_INPUT,
                                   edgecolor="black", linewidth=1.1))
    ax.text(x_pos, 2.0, label, ha="center", va="center", fontsize=10.5)

for i in range(len(stages) - 1):
    ax.annotate("", xy=(stages[i + 1][0] - BW / 2 - 0.05, 2),
                xytext=(stages[i][0] + BW / 2 + 0.05, 2),
                arrowprops=dict(arrowstyle="->", color=COLOR_BLUE, lw=1.5))

for i, grad in enumerate(gradients):
    right, left = stages[-(i + 1)][0], stages[-(i + 2)][0]
    ax.text((right + left) / 2, 0.75, grad, ha="center", fontsize=10, color=COLOR_RED)
    ax.annotate("", xy=(left + 0.3, 1.25), xytext=(right - 0.3, 1.25),
                arrowprops=dict(arrowstyle="->", color=COLOR_RED, lw=1.5))

ax.text(6, 3.0, "∂L/∂x = (∂L/∂f) × (∂f/∂g) × (∂g/∂h) × (∂h/∂x)",
        ha="center", fontsize=12)
ax.set_xlim(-0.1, 12.1)
ax.set_ylim(0.4, 3.4)
ax.set_aspect("equal")
ax.axis("off")
save("backprop_chain_rule.svg")


# ============================================================
# Fig 4: Gradient norm per layer in a 10-layer MLP (vanishing)
# ============================================================
# 本文の実験コードと同じ関数。NumPy で forward と backward を書き、
# 各層の重みの勾配のノルム ||∂L/∂W_i|| を測る。
ACTS = {
    "sigmoid": (lambda z: 1 / (1 + np.exp(-z)),
                lambda z: (s := 1 / (1 + np.exp(-z))) * (1 - s)),
    "tanh": (np.tanh, lambda z: 1 - np.tanh(z) ** 2),
    "relu": (lambda z: np.maximum(z, 0), lambda z: (z > 0).astype(float)),
}


def layer_grad_norms(act, n_layers=10, width=64, batch=256, seed=0):
    rng = np.random.default_rng(seed)
    f, df = ACTS[act]
    # 重みは平均 0、標準偏差 1/√width の正規分布で初期化する
    Ws = [rng.normal(0, 1 / np.sqrt(width), (width, width)) for _ in range(n_layers)]
    x = rng.normal(size=(batch, width))
    t = rng.normal(size=(batch, width))

    # forward: 各層の入力 h と活性化前の z を保持する
    hs, zs = [x], []
    for W in Ws:
        zs.append(hs[-1] @ W)
        hs.append(f(zs[-1]))

    # L は二乗誤差の和をバッチ数で割ったもの。g は ∂L/∂(最終層の出力)
    g = 2 * (hs[-1] - t) / batch

    # backward: 出力側から 1 層ずつ連鎖律を適用する
    norms = [0.0] * n_layers
    for i in reversed(range(n_layers)):
        g = g * df(zs[i])                       # ∂L/∂z_i
        norms[i] = np.linalg.norm(hs[i].T @ g)  # ||∂L/∂W_i||
        g = g @ Ws[i].T                         # ∂L/∂h_i（1 つ入力側の層へ渡す）
    return norms


layers = np.arange(1, 11)
plt.figure(figsize=(8, 4.2))
for act, color, marker in [("sigmoid", COLOR_BLUE, "o"), ("tanh", COLOR_GREEN, "s"),
                           ("relu", COLOR_RED, "^")]:
    n = np.array(layer_grad_norms(act))
    plt.plot(layers, n / n[-1], marker=marker, color=color, lw=1.8, label=act)
plt.yscale("log")
plt.xticks(layers)
plt.xlabel("layer (1 = input side, 10 = output side)")
plt.ylabel("||∂L/∂W_i|| / ||∂L/∂W_10||")
plt.title("10-layer MLP at initialization: gradient norm relative to the last layer")
plt.legend()
plt.grid(True, alpha=0.25)
save("backprop_vanishing.svg")


print("done:", sorted(os.listdir(NOTE_DIR)))
