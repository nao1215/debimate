"""partial-derivative-gradient ノート用の図を生成するスクリプト。

実行: cd projects/ml && uv run python scripts/notes/partial-derivative-gradient_gen.py

軸ラベル・タイトルは英語で統一（matplotlib の日本語フォントは環境依存のため）。
"""
import os

import matplotlib.pyplot as plt
import numpy as np

COLOR_BLUE = "#7aa6c2"
COLOR_RED = "#e15759"
COLOR_GREEN = "#59a14f"
COLOR_GRAY = "#999999"

NOTE_DIR = os.path.expanduser(
    "~/ghq/github.com/nao1215/debimate/projects/ml/notes/math/partial-derivative-gradient"
)
os.makedirs(NOTE_DIR, exist_ok=True)


def save(name: str) -> None:
    plt.savefig(os.path.join(NOTE_DIR, name), bbox_inches="tight")
    plt.close()


# ============================================================
# Fig 1: 1D derivative as the slope of a tangent line
# ============================================================
x = np.linspace(-2, 2, 400)
y = x ** 2
x0 = 1.0
slope = 2 * x0
tangent = slope * (x - x0) + x0 ** 2

plt.figure(figsize=(6, 4))
plt.plot(x, y, color=COLOR_BLUE, lw=2, label="f(x) = x^2")
plt.plot(x, tangent, color=COLOR_RED, lw=1.6, ls="--",
         label=f"tangent at x={x0}, slope={slope}")
plt.scatter([x0], [x0 ** 2], color=COLOR_RED, zorder=5)
plt.axhline(0, color=COLOR_GRAY, lw=0.6)
plt.axvline(0, color=COLOR_GRAY, lw=0.6)
plt.title("1D derivative = slope of tangent line")
plt.xlabel("x"); plt.ylabel("f(x)")
plt.ylim(-1, 4.5)
plt.legend(fontsize=9)
plt.grid(True, alpha=0.25)
plt.tight_layout()
save("tangent_1d.svg")


# ============================================================
# Fig 2: 2D surface and partial derivatives at one point
# ============================================================
xs = np.linspace(-2, 2, 60)
ys = np.linspace(-2, 2, 60)
XX, YY = np.meshgrid(xs, ys)
ZZ = XX ** 2 + 2 * YY ** 2

fig = plt.figure(figsize=(7, 5))
ax = fig.add_subplot(111, projection="3d")
ax.plot_surface(XX, YY, ZZ, cmap="viridis", alpha=0.6, edgecolor="none")

x0, y0 = 1.0, 0.8
z0 = x0 ** 2 + 2 * y0 ** 2
# Slice along x (y fixed at y0): partial f / partial x = 2x
xs_line = np.linspace(-2, 2, 60)
zs_line_x = xs_line ** 2 + 2 * y0 ** 2
ax.plot(xs_line, np.full_like(xs_line, y0), zs_line_x,
        color=COLOR_RED, lw=2, label="slice y = y0 (∂f/∂x view)")
# Slice along y (x fixed at x0): partial f / partial y = 4y
ys_line = np.linspace(-2, 2, 60)
zs_line_y = x0 ** 2 + 2 * ys_line ** 2
ax.plot(np.full_like(ys_line, x0), ys_line, zs_line_y,
        color=COLOR_GREEN, lw=2, label="slice x = x0 (∂f/∂y view)")
ax.scatter([x0], [y0], [z0], color="black", s=40)
ax.set_xlabel("x"); ax.set_ylabel("y"); ax.set_zlabel("f(x, y)")
ax.set_title("Surface f(x, y) = x^2 + 2y^2 and two partial-derivative slices")
ax.legend(loc="upper left", fontsize=8)
plt.tight_layout()
save("surface_slices.png")


# ============================================================
# Fig 3: Gradient vector field on a contour map
# ============================================================
xs = np.linspace(-2.2, 2.2, 200)
ys = np.linspace(-2.2, 2.2, 200)
XX, YY = np.meshgrid(xs, ys)
ZZ = XX ** 2 + 2 * YY ** 2

# Gradient: grad f = (2x, 4y)
xs_q = np.linspace(-2, 2, 11)
ys_q = np.linspace(-2, 2, 11)
XQ, YQ = np.meshgrid(xs_q, ys_q)
UQ = 2 * XQ
VQ = 4 * YQ
mag = np.sqrt(UQ ** 2 + VQ ** 2)
UQn = UQ / (mag + 1e-9)
VQn = VQ / (mag + 1e-9)

plt.figure(figsize=(6, 5))
cs = plt.contour(XX, YY, ZZ, levels=12, cmap="Blues_r")
plt.clabel(cs, inline=True, fontsize=8)
plt.quiver(XQ, YQ, UQn, VQn, color=COLOR_RED, scale=25, width=0.005)
plt.title("Gradient vectors point toward steepest ascent\n(perpendicular to contours)")
plt.xlabel("x"); plt.ylabel("y")
plt.gca().set_aspect("equal")
plt.tight_layout()
save("gradient_field.svg")


# ============================================================
# Fig 4: ML example - MSE loss surface and its gradient direction
# ============================================================
# Linear model y = w * x with MSE loss, data y = 2x + noise
rng = np.random.default_rng(0)
x_data = np.linspace(-1, 1, 30)
y_data = 2.0 * x_data + rng.normal(0.0, 0.3, 30)

w_grid = np.linspace(-1, 5, 80)
b_grid = np.linspace(-3, 3, 80)
WW, BB = np.meshgrid(w_grid, b_grid)
# Loss L(w, b) = mean((y - (w x + b))^2)
LL = np.zeros_like(WW)
for i in range(WW.shape[0]):
    for j in range(WW.shape[1]):
        pred = WW[i, j] * x_data + BB[i, j]
        LL[i, j] = np.mean((y_data - pred) ** 2)

# Gradient of MSE: d L / d w = -2 mean(x (y - (w x + b)))
#                  d L / d b = -2 mean((y - (w x + b)))
w_q = np.linspace(-0.5, 4.5, 8)
b_q = np.linspace(-2.5, 2.5, 8)
WQ, BQ = np.meshgrid(w_q, b_q)
GW = np.zeros_like(WQ)
GB = np.zeros_like(BQ)
for i in range(WQ.shape[0]):
    for j in range(WQ.shape[1]):
        pred = WQ[i, j] * x_data + BQ[i, j]
        GW[i, j] = -2 * np.mean(x_data * (y_data - pred))
        GB[i, j] = -2 * np.mean(y_data - pred)
mag = np.sqrt(GW ** 2 + GB ** 2)
# Show descent direction (negative gradient) since that's what matters for training
GWn = -GW / (mag + 1e-9)
GBn = -GB / (mag + 1e-9)

plt.figure(figsize=(6.5, 5))
cs = plt.contourf(WW, BB, LL, levels=25, cmap="Blues_r")
plt.colorbar(cs, label="MSE loss")
plt.quiver(WQ, BQ, GWn, GBn, color=COLOR_RED, scale=22, width=0.005,
           label="-grad L (descent direction)")
plt.scatter([2.0], [0.0], color="black", marker="*", s=200, zorder=5,
            label="optimum (true w=2, b=0)")
plt.title("MSE loss surface for y = w x + b\nNegative gradient points to the optimum")
plt.xlabel("w"); plt.ylabel("b")
plt.legend(loc="upper right", fontsize=9)
plt.tight_layout()
save("mse_gradient.png")


print("done:", sorted(os.listdir(NOTE_DIR)))
