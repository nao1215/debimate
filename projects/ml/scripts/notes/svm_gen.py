"""svm ノート用の図を生成するスクリプト。

実行: cd projects/ml && uv run python scripts/notes/svm_gen.py
"""
import os

import matplotlib.pyplot as plt
import numpy as np
from sklearn.svm import SVC
from sklearn.datasets import make_blobs, make_circles, make_moons

COLOR_BLUE = "#7aa6c2"
COLOR_RED = "#e15759"
COLOR_GREEN = "#59a14f"
COLOR_GRAY = "#999999"

NOTE_DIR = os.path.expanduser(
    "~/ghq/github.com/nao1215/debimate/projects/ml/notes/ml/svm"
)
os.makedirs(NOTE_DIR, exist_ok=True)


def save(name: str) -> None:
    plt.savefig(os.path.join(NOTE_DIR, name), bbox_inches="tight")
    plt.close()


def plot_svc_decision(ax, model, X, y, title):
    """Helper: draw decision boundary, margin, support vectors."""
    xx, yy = np.meshgrid(
        np.linspace(X[:, 0].min() - 0.5, X[:, 0].max() + 0.5, 300),
        np.linspace(X[:, 1].min() - 0.5, X[:, 1].max() + 0.5, 300),
    )
    Z = model.decision_function(np.c_[xx.ravel(), yy.ravel()]).reshape(xx.shape)
    ax.contourf(xx, yy, Z, levels=[-1e9, 0, 1e9], alpha=0.15, colors=[COLOR_BLUE, COLOR_RED])
    ax.contour(xx, yy, Z, levels=[-1, 0, 1], colors=["black", "black", "black"],
               linestyles=["--", "-", "--"], linewidths=[1, 1.6, 1])
    ax.scatter(X[:, 0], X[:, 1], c=y, cmap="coolwarm", edgecolor="white", s=35)
    # Support vectors
    ax.scatter(model.support_vectors_[:, 0], model.support_vectors_[:, 1],
               s=120, facecolors="none", edgecolors="black", linewidths=1.5,
               label=f"support vectors ({len(model.support_vectors_)})")
    ax.set_title(title)
    ax.set_xlabel("x1"); ax.set_ylabel("x2")
    ax.legend(loc="upper right", fontsize=8)


# ============================================================
# Fig 1: Linear SVM - hyperplane, margin, support vectors
# ============================================================
rng = np.random.default_rng(0)
X, y = make_blobs(n_samples=80, centers=2, cluster_std=1.1, random_state=6)

model = SVC(kernel="linear", C=1.0).fit(X, y)

plt.figure(figsize=(7, 6))
ax = plt.gca()
plot_svc_decision(ax, model, X, y,
                  "Linear SVM: maximize margin between classes\n"
                  "(solid = decision boundary, dashed = ±1 margin)")
plt.tight_layout()
save("svm_linear_margin.svg")


# ============================================================
# Fig 2: Hard vs soft margin (effect of C)
# ============================================================
# Slightly overlapping classes
rng2 = np.random.default_rng(0)
X2 = np.vstack([
    rng2.normal([0, 0], 1.0, (40, 2)),
    rng2.normal([3, 3], 1.0, (40, 2)),
])
y2 = np.array([0] * 40 + [1] * 40)
# Inject a couple of "wrong-side" points
X2[5] = [3.0, 2.5]; y2[5] = 0
X2[55] = [0.5, 0.5]; y2[55] = 1

fig, axes = plt.subplots(1, 3, figsize=(15, 5))
for ax, C in zip(axes, [0.05, 1.0, 100.0]):
    m = SVC(kernel="linear", C=C).fit(X2, y2)
    plot_svc_decision(ax, m, X2, y2, f"C = {C}")
plt.suptitle("Soft-margin SVM: small C = wide margin, lots of violations | large C = narrow margin, fewer violations", y=1.02)
plt.tight_layout()
save("svm_soft_margin_C.svg")


# ============================================================
# Fig 3: Kernel trick visualization: 2D circles -> 3D linearly separable
# ============================================================
from mpl_toolkits.mplot3d import Axes3D  # noqa
X_c, y_c = make_circles(n_samples=200, factor=0.4, noise=0.08, random_state=0)

# 3rd dim = squared radius (radial feature)
z = X_c[:, 0] ** 2 + X_c[:, 1] ** 2

fig = plt.figure(figsize=(12, 5))
ax1 = fig.add_subplot(1, 2, 1)
ax1.scatter(X_c[y_c == 0, 0], X_c[y_c == 0, 1], color=COLOR_BLUE, s=30, label="class 0")
ax1.scatter(X_c[y_c == 1, 0], X_c[y_c == 1, 1], color=COLOR_RED, s=30, label="class 1")
ax1.set_title("2D input space: NOT linearly separable")
ax1.set_xlabel("x1"); ax1.set_ylabel("x2")
ax1.set_aspect("equal")
ax1.legend()
ax1.grid(True, alpha=0.25)

ax2 = fig.add_subplot(1, 2, 2, projection="3d")
ax2.scatter(X_c[y_c == 0, 0], X_c[y_c == 0, 1], z[y_c == 0],
            color=COLOR_BLUE, s=30, label="class 0")
ax2.scatter(X_c[y_c == 1, 0], X_c[y_c == 1, 1], z[y_c == 1],
            color=COLOR_RED, s=30, label="class 1")
# Plane to suggest the separating hyperplane
xx, yy = np.meshgrid(np.linspace(-1.2, 1.2, 10), np.linspace(-1.2, 1.2, 10))
zz = np.full_like(xx, 0.5)
ax2.plot_surface(xx, yy, zz, alpha=0.2, color=COLOR_GREEN)
ax2.set_title("3D feature space (added r² as extra dim):\nlinearly separable by a plane")
ax2.set_xlabel("x1"); ax2.set_ylabel("x2"); ax2.set_zlabel("x1² + x2²")
ax2.legend()

plt.tight_layout()
save("svm_kernel_trick.png")


# ============================================================
# Fig 4: RBF kernel - effect of gamma on decision boundary
# ============================================================
X_m, y_m = make_moons(n_samples=300, noise=0.15, random_state=0)
xx_m, yy_m = np.meshgrid(np.linspace(-1.5, 2.5, 250),
                          np.linspace(-1.2, 1.7, 250))

fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
for ax, gamma in zip(axes, [0.1, 1.0, 50.0]):
    m = SVC(kernel="rbf", gamma=gamma, C=1.0).fit(X_m, y_m)
    Z = m.predict(np.c_[xx_m.ravel(), yy_m.ravel()]).reshape(xx_m.shape)
    ax.contourf(xx_m, yy_m, Z, alpha=0.25, cmap="coolwarm")
    ax.scatter(X_m[:, 0], X_m[:, 1], c=y_m, cmap="coolwarm", edgecolor="white", s=25)
    ax.set_title(f"RBF kernel, gamma={gamma}")
    ax.set_xlabel("x1"); ax.set_ylabel("x2")
plt.suptitle("RBF SVM: small γ = smooth boundary (under-fit), large γ = wiggly (over-fit)",
             y=1.02)
plt.tight_layout()
save("svm_rbf_gamma.png")


print("done:", sorted(os.listdir(NOTE_DIR)))
