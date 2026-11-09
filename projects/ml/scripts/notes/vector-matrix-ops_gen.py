"""vector-matrix-ops ノート用の図を生成するスクリプト。

実行: cd projects/ml && uv run python scripts/notes/vector-matrix-ops_gen.py
"""
import os
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

COLOR_BLUE = "#7aa6c2"
COLOR_RED = "#e15759"
COLOR_GREEN = "#59a14f"
COLOR_GRAY = "#999999"

NOTE_DIR = Path(__file__).resolve().parents[2] / "notes/math/vector-matrix-ops"
plt.rcParams.update({"svg.hashsalt": "vector-matrix-ops", "font.size": 11})
os.makedirs(NOTE_DIR, exist_ok=True)


def save(name: str) -> None:
    plt.savefig(NOTE_DIR / name, bbox_inches="tight",
                metadata={"Date": None} if name.endswith(".svg") else None)
    plt.close()


# ============================================================
# Fig 1: Vector addition and scalar multiplication
# ============================================================
fig, axes = plt.subplots(2, 1, figsize=(6, 9))

# Addition
a = np.array([3, 1])
b = np.array([1, 2])
c = a + b
ax = axes[0]
ax.quiver(0, 0, *a, angles="xy", scale_units="xy", scale=1, color=COLOR_BLUE, label="a = (3, 1)")
ax.quiver(0, 0, *b, angles="xy", scale_units="xy", scale=1, color=COLOR_RED, label="b = (1, 2)")
ax.quiver(0, 0, *c, angles="xy", scale_units="xy", scale=1, color=COLOR_GREEN, label="a + b = (4, 3)")
ax.quiver(*a, *b, angles="xy", scale_units="xy", scale=1, color=COLOR_RED, alpha=0.4, ls=":")
ax.set_xlim(-0.5, 5); ax.set_ylim(-0.5, 4)
ax.set_aspect("equal"); ax.grid(True, alpha=0.25)
ax.legend(loc="upper left", fontsize=9)
ax.set_title("Vector addition: parallelogram rule")

# Scalar multiplication
v = np.array([2, 1])
ax = axes[1]
for k, color in [(1.5, COLOR_GREEN), (1.0, COLOR_BLUE), (-1.0, COLOR_RED)]:
    ax.quiver(0, 0, *(k * v), angles="xy", scale_units="xy", scale=1, color=color,
              label=f"{k} * v")
ax.axhline(0, color=COLOR_GRAY, lw=0.6)
ax.axvline(0, color=COLOR_GRAY, lw=0.6)
ax.set_xlim(-3, 4); ax.set_ylim(-2, 2.5)
ax.set_aspect("equal"); ax.grid(True, alpha=0.25)
ax.legend(loc="lower right", fontsize=9)
ax.set_title("Scalar multiplication: stretch / flip")

plt.tight_layout()
save("vector_basics.svg")


# ============================================================
# Fig 2: Dot product as projection
# ============================================================
fig, axes = plt.subplots(2, 1, figsize=(6, 9))

# Acute angle (positive dot)
a = np.array([4, 1])
b = np.array([3, 2])
ax = axes[0]
unit_a = a / np.linalg.norm(a)
proj = (b @ unit_a) * unit_a
ax.quiver(0, 0, *a, angles="xy", scale_units="xy", scale=1, color=COLOR_BLUE, label="a")
ax.quiver(0, 0, *b, angles="xy", scale_units="xy", scale=1, color=COLOR_RED, label="b")
ax.quiver(0, 0, *proj, angles="xy", scale_units="xy", scale=1, color=COLOR_GREEN,
          label=f"proj_a(b)\n(signed component = (a·b) / ||a||)")
ax.plot([proj[0], b[0]], [proj[1], b[1]], color=COLOR_GRAY, ls=":")
ax.set_xlim(-0.5, 5); ax.set_ylim(-0.5, 3)
ax.set_aspect("equal"); ax.grid(True, alpha=0.25)
ax.legend(loc="upper right", fontsize=9)
ax.set_title(f"a · b = {a @ b}  (positive: acute angle)")

# Obtuse angle (negative dot)
a = np.array([4, 1])
b = np.array([-2, 2])
ax = axes[1]
unit_a = a / np.linalg.norm(a)
proj = (b @ unit_a) * unit_a
ax.quiver(0, 0, *a, angles="xy", scale_units="xy", scale=1, color=COLOR_BLUE, label="a")
ax.quiver(0, 0, *b, angles="xy", scale_units="xy", scale=1, color=COLOR_RED, label="b")
ax.quiver(0, 0, *proj, angles="xy", scale_units="xy", scale=1, color=COLOR_GREEN,
          label=f"proj_a(b)")
ax.plot([proj[0], b[0]], [proj[1], b[1]], color=COLOR_GRAY, ls=":")
ax.set_xlim(-3, 5); ax.set_ylim(-1, 3)
ax.set_aspect("equal"); ax.grid(True, alpha=0.25)
ax.legend(loc="upper right", fontsize=9)
ax.set_title(f"a · b = {a @ b}  (negative: obtuse angle)")

plt.tight_layout()
save("dot_product_projection.svg")


# ============================================================
# Fig 3: Matrix as linear transformation of the unit square
# ============================================================
square = np.array([[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]).T

matrices = [
    ("Scale: A = [[2, 0], [0, 0.5]]", np.array([[2, 0], [0, 0.5]])),
    ("Rotate 30°: A = R(30°)", np.array([[np.cos(np.pi/6), -np.sin(np.pi/6)],
                                          [np.sin(np.pi/6),  np.cos(np.pi/6)]])),
    ("Shear: A = [[1, 0.6], [0, 1]]", np.array([[1, 0.6], [0, 1]])),
]

fig, axes = plt.subplots(3, 1, figsize=(6, 12))
for ax, (title, A) in zip(axes, matrices):
    transformed = A @ square
    ax.plot(square[0], square[1], color=COLOR_GRAY, lw=1.5, ls="--", label="original")
    ax.fill(square[0], square[1], color=COLOR_GRAY, alpha=0.15)
    ax.plot(transformed[0], transformed[1], color=COLOR_RED, lw=2, label="after A x")
    ax.fill(transformed[0], transformed[1], color=COLOR_RED, alpha=0.2)
    # Show how basis vectors are transformed
    e1, e2 = A @ np.array([1, 0]), A @ np.array([0, 1])
    ax.quiver(0, 0, *e1, angles="xy", scale_units="xy", scale=1, color=COLOR_BLUE, width=0.012)
    ax.quiver(0, 0, *e2, angles="xy", scale_units="xy", scale=1, color=COLOR_GREEN, width=0.012)
    ax.set_xlim(-0.5, 2.5); ax.set_ylim(-0.5, 2.5)
    ax.set_aspect("equal"); ax.grid(True, alpha=0.25)
    ax.set_title(title, fontsize=10)
    ax.legend(loc="upper right", fontsize=8)
plt.tight_layout()
save("matrix_transformations.png")


# ============================================================
# Fig 4: Matrix-form linear regression (X w = y_pred shape view)
# ============================================================
rng = np.random.default_rng(0)
n, d = 8, 3
X = np.round(rng.standard_normal((n, d)) * 1.5, 1)
w = np.array([1.5, -0.5, 0.8])
y_pred = X @ w
assert np.allclose(y_pred, [1.2, 1.1, 1.42, -2.32, -6.62, -1.65, -.06, 3.9])
print("y_pred:", np.round(y_pred, 2))

fig, axes = plt.subplots(3, 1, figsize=(6, 12), gridspec_kw={"height_ratios": [8, 3, 8]})

# X matrix
ax = axes[0]
ax.imshow(X, cmap="Blues", vmin=X.min()-2, vmax=X.max()+5, aspect="auto")
for i in range(n):
    for j in range(d):
        ax.text(j, i, f"{X[i, j]:.1f}", ha="center", va="center",
                fontsize=9, color="black")
ax.set_title(f"X: shape ({n}, {d})\nrows = samples, cols = features")
ax.set_xticks(range(d)); ax.set_xticklabels([f"x{j+1}" for j in range(d)])
ax.set_yticks(range(n)); ax.set_yticklabels([f"sample {i+1}" for i in range(n)])

# w vector
ax = axes[1]
ax.imshow(w.reshape(-1, 1), cmap="Greens", vmin=-2, vmax=5, aspect="auto")
for j in range(d):
    ax.text(0, j, f"{w[j]:.1f}", ha="center", va="center", fontsize=12, color="black")
ax.set_title(f"w: shape ({d},)\nweights")
ax.set_xticks([0]); ax.set_xticklabels(["w"])
ax.set_yticks(range(d)); ax.set_yticklabels([f"w{j+1}" for j in range(d)])

# y vector
ax = axes[2]
ax.imshow(y_pred.reshape(-1, 1), cmap="Reds", vmin=-8, vmax=12, aspect="auto")
for i in range(n):
    ax.text(0, i, f"{y_pred[i]:.2f}", ha="center", va="center", fontsize=10, color="black")
ax.set_title(f"y_pred = X @ w\nshape ({n},)")
ax.set_xticks([0]); ax.set_xticklabels(["y_pred"])
ax.set_yticks(range(n)); ax.set_yticklabels([f"sample {i+1}" for i in range(n)])

plt.tight_layout()
save("matrix_regression_layout.png")


print("done:", sorted(os.listdir(NOTE_DIR)))
