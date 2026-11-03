"""Generate the convex-functions figures and the values quoted in the article.

Run from any directory: python projects/ml/scripts/notes/convex-functions_gen.py
Requires numpy and matplotlib. Output is relative to this file's checkout.
"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

NOTE_DIR = Path(__file__).resolve().parents[2] / "notes/math/convex-functions"
BLUE, RUST, GREEN = "#45677d", "#a56045", "#587064"
plt.rcParams.update({"font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9,
                     "legend.fontsize": 8, "svg.fonttype": "none",
                     "svg.hashsalt": "convex-functions", "axes.spines.top": False,
                     "axes.spines.right": False})



def save_panels(names, groups=None):
    """Save separate panels so Hugo can stack them at mobile widths."""
    fig = plt.gcf()
    fig.tight_layout()
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    if groups is None:
        groups = [[ax] for ax in fig.axes]
    from matplotlib.transforms import Bbox
    for name, group in zip(names, groups):
        for ax in fig.axes:
            ax.set_visible(ax in group)
        bbox = Bbox.union([ax.get_tightbbox(renderer) for ax in group])
        bbox = bbox.transformed(fig.dpi_scale_trans.inverted()).padded(.08)
        fig.savefig(NOTE_DIR / name, bbox_inches=bbox, metadata={"Date": None})
    plt.close(fig)


def decorate(ax):
    ax.set_xlabel("x")
    ax.set_ylabel("f(x)")
    ax.grid(alpha=.18)


# Two endpoint values determine a chord. No random sampling is needed.
fig, axes = plt.subplots(1, 2, figsize=(9, 3.5))
for ax, fun, domain, a, b, title in [
    (axes[0], lambda x: x**2, (-2, 2), -1.3, 1.5, "Convex: x²"),
    (axes[1], np.log, (.2, 4), .5, 3.5, "Concave: log(x)"),
]:
    x = np.linspace(*domain, 400)
    midpoint = (a + b) / 2
    chord = (fun(a) + fun(b)) / 2
    ax.plot(x, fun(x), color=BLUE, label="function")
    ax.plot([a, b], [fun(a), fun(b)], "--", color=RUST, label="chord")
    ax.scatter([midpoint], [fun(midpoint)], color=BLUE, zorder=4)
    ax.scatter([midpoint], [chord], color=RUST, zorder=4)
    ax.plot([midpoint, midpoint], [fun(midpoint), chord], ":", color=GREEN)
    ax.set_title(title)
    ax.legend()
    decorate(ax)
save_panels(["convex_chord.svg", "concave_chord.svg"])
print("chord: f(midpoint)=0.01, mean(f(endpoints))=1.97")

# Convexity alone says neither that a minimum exists nor that it is unique.
fig, axes = plt.subplots(1, 3, figsize=(9, 3))
x = np.linspace(-3, 3, 400)
for ax, values, title in [
    (axes[0], x**2, "x²: unique minimizer"),
    (axes[1], np.maximum(np.abs(x)-1, 0), "max(|x|-1, 0): an interval"),
    (axes[2], np.exp(x)-1, "exp(x)-1: no minimizer"),
]:
    ax.plot(x, values, color=BLUE)
    ax.set_title(title)
    decorate(ax)
axes[0].scatter([0], [0], color=RUST, zorder=4)
axes[1].plot([-1, 1], [0, 0], color=RUST, lw=4)
axes[2].axhline(-1, ls="--", color=RUST, label="infimum = -1")
axes[2].legend()
save_panels(["convex_unique.svg", "convex_interval.svg", "convex_no_minimum.svg"])


def f_convex(x):
    return (x - 2) ** 2


def df_convex(x):
    return 2 * (x - 2)


def f_nonconvex(x):
    return 0.3 * x**4 - 1.5 * x**2 - 0.5 * x + 2


def df_nonconvex(x):
    return 1.2 * x**3 - 3 * x - 0.5


def descend(gradient, start, rate=0.1, steps=50):
    path = [float(start)]
    for _ in range(steps):
        path.append(path[-1] - rate * gradient(path[-1]))
    return np.array(path)


# Exact gradients: this is GD, not SGD. Separate shape and trajectory
# so a high initial function value does not flatten the two minima.
fig, axes = plt.subplots(2, 2, figsize=(9, 5.5))
x = np.linspace(-2.8, 2.8, 500)
stationary = np.sort(np.roots([1.2, 0, -3, -.5]).real)
minima = stationary[3.6 * stationary**2 - 3 > 0]
global_minimum = minima[np.argmin(f_nonconvex(minima))]
for column, fun, grad, title, optimum in [
    (0, f_convex, df_convex, "Convex: (x-2)²", 2),
    (1, f_nonconvex, df_nonconvex, "Non-convex: two local minima", global_minimum),
]:
    top, bottom = axes[0, column], axes[1, column]
    top.plot(x, fun(x), color=BLUE, lw=1.5)
    top.axvline(optimum, color=RUST, ls=":", label="global minimizer")
    if column == 1:
        top.scatter(minima, fun(minima), color=RUST, s=22)
    for start, color in zip([-2.5, .5, 4], [BLUE, RUST, GREEN]):
        path = descend(grad, start)
        bottom.plot(range(len(path)), path, ".-", color=color, ms=2,
                    lw=.9, label=f"start={start}")
        print(f"{title} start={start:4.1f}: x_50={path[-1]:.6f}, f(x_50)={fun(path[-1]):.6f}")
    top.set_title(title)
    top.legend()
    decorate(top)
    bottom.set_xlabel("iteration")
    bottom.set_ylabel("x")
    bottom.legend(loc="upper right")
    bottom.grid(alpha=.18)
save_panels(["convex_gd.svg", "nonconvex_gd.svg"],
            [[axes[0, 0], axes[1, 0]], [axes[0, 1], axes[1, 1]]])
assert np.allclose([descend(df_nonconvex, s)[-1] for s in [-2.5, .5, 4]],
                   [minima[0], minima[1], minima[0]], atol=1e-5)
for rate in [.1, 1, 1.1]:
    path = descend(df_convex, 0, rate=rate, steps=10)
    print(f"convex rate={rate}: x_10={path[-1]:.6f}, distance={abs(path[-1]-2):.6f}")

# Expectations are analytical integrals for Uniform(-2, 2), not sample means.
fig, axes = plt.subplots(1, 2, figsize=(9, 3.4))
x = np.linspace(-2, 2, 400)
for ax, fun, expected, title in [
    (axes[0], lambda x: x**2, 4/3, "x²: gap = Var(X) = 4/3"),
    (axes[1], lambda x: 2*x+3, 3, "2x+3: gap = 0"),
]:
    ax.plot(x, fun(x), color=BLUE)
    ax.scatter([0], [fun(0)], color=BLUE, s=55, label="f(E[X])", zorder=4)
    ax.scatter([0], [expected], facecolors="none", edgecolors=RUST, s=120,
               label="E[f(X)]", zorder=5)
    ax.plot([0, 0], [fun(0), expected], "--", color=RUST)
    ax.set_title(title)
    ax.legend()
    decorate(ax)
save_panels(["convex_jensen_square.svg", "convex_jensen_affine.svg"])
print("Jensen: E[X]=0, E[X²]=4/3, Var(X)=4/3; affine gap=0")

# The standalone example shown in the article.
import numpy as np
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(6, 3.5))
for rate, color in zip([0.1, 1.0, 1.1], ["#45677d", "#a56045", "#587064"]):
    path = [0.0]
    for _ in range(10):
        path.append(path[-1] - rate * 2 * (path[-1] - 2))
    distance = np.abs(np.array(path) - 2)
    ax.plot(range(11), distance, "o-", color=color, label=f"rate={rate}")
ax.set_xlabel("iteration")
ax.set_ylabel("distance to x=2")
ax.legend()
ax.grid(alpha=0.18)
fig.tight_layout()
fig.savefig(NOTE_DIR / "convex_learning_rate.svg", bbox_inches="tight", metadata={"Date": None})
plt.close(fig)
