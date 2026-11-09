"""partial-derivative-gradient ノート用の図を生成するスクリプト。

実行: cd projects/ml && uv run python scripts/notes/partial-derivative-gradient_gen.py

軸ラベル・タイトルは英語で統一（matplotlib の日本語フォントは環境依存のため）。
"""
import os
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

COLOR_BLUE = "#7aa6c2"
COLOR_RED = "#e15759"
COLOR_GREEN = "#59a14f"
COLOR_GRAY = "#999999"

NOTE_DIR = str(
    Path(__file__).resolve().parents[2] / "notes" / "math" / "partial-derivative-gradient"
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
# Fig 4: ML example - MSE loss surface, its negative gradient and a GD path
# ============================================================
# Linear model y = w * x + b with MSE loss, data y = 2x + noise
# (the block from here to the GD loop is the excerpt shown in the note)
rng = np.random.default_rng(0)
x_data = np.linspace(-1, 1, 30)
y_data = 2.0 * x_data + rng.normal(0.0, 0.3, 30)


def loss(w, b):
    return np.mean((y_data - (w * x_data + b)) ** 2)


def grad(w, b):
    r = y_data - (w * x_data + b)
    return np.array([-2 * np.mean(x_data * r), -2 * np.mean(r)])


w_opt, b_opt = np.polyfit(x_data, y_data, 1)  # least-squares optimum
print(f"optimum: w={w_opt:.3f}, b={b_opt:.3f}")

w0, b0 = -0.5, 2.5
h = 1e-6
numeric = [(loss(w0 + h, b0) - loss(w0 - h, b0)) / (2 * h),
           (loss(w0, b0 + h) - loss(w0, b0 - h)) / (2 * h)]
print("grad   :", np.round(grad(w0, b0), 4))
print("numeric:", np.round(numeric, 4))

d = -grad(w0, b0)
to_opt = np.array([w_opt - w0, b_opt - b0])
cos = d @ to_opt / (np.linalg.norm(d) * np.linalg.norm(to_opt))
print(f"angle between -grad and optimum: {np.degrees(np.arccos(cos)):.1f} deg")

eta = 0.3
p = np.array([w0, b0])
path = [p]
for t in range(1, 21):
    p = p - eta * grad(*p)
    path.append(p)
    if t in (1, 5, 20):
        print(f"step {t:2d}: w={p[0]:.3f}, b={p[1]:.3f}, L={loss(*p):.4f}")
path = np.array(path)

# --- drawing (omitted in the note) ---
w_grid = np.linspace(-1, 5, 80)
b_grid = np.linspace(-3, 3, 80)
WW, BB = np.meshgrid(w_grid, b_grid)
LL = np.array([[loss(w, b) for w in w_grid] for b in b_grid])

w_q = np.linspace(-0.5, 4.5, 8)
b_q = np.linspace(-2.5, 2.5, 8)
WQ, BQ = np.meshgrid(w_q, b_q)
G = np.array([[grad(w, b) for w in w_q] for b in b_q])
GW, GB = G[..., 0], G[..., 1]
mag = np.sqrt(GW ** 2 + GB ** 2)
GWn = -GW / (mag + 1e-9)
GBn = -GB / (mag + 1e-9)

plt.figure(figsize=(6.5, 5))
cs = plt.contourf(WW, BB, LL, levels=25, cmap="Blues_r")
plt.colorbar(cs, label="MSE loss")
plt.quiver(WQ, BQ, GWn, GBn, color=COLOR_RED, scale=22, width=0.005,
           label="-grad L (descent direction)")
plt.plot([w0, w_opt], [b0, b_opt], color=COLOR_GRAY, ls="--", lw=1.2,
         label="straight line to optimum")
plt.plot(path[:, 0], path[:, 1], color="black", marker="o", ms=3, lw=1.2,
         label=f"gradient descent (eta={eta}, 20 steps)")
plt.scatter([w_opt], [b_opt], color="black", marker="*", s=200, zorder=5,
            label=f"optimum (w={w_opt:.2f}, b={b_opt:.2f})")
plt.title("MSE loss surface for y = w x + b\n"
          "-grad L points downhill, not straight at the optimum")
plt.xlabel("w"); plt.ylabel("b")
plt.legend(loc="upper right", fontsize=8)
plt.tight_layout()
save("mse_gradient.png")


print("done:", sorted(os.listdir(NOTE_DIR)))
