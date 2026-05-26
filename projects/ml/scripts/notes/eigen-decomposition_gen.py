"""eigen-decomposition ノート用の図を生成するスクリプト。

実行: cd projects/ml && uv run python scripts/notes/eigen-decomposition_gen.py
"""
import os

import matplotlib.pyplot as plt
import numpy as np

COLOR_BLUE = "#7aa6c2"
COLOR_RED = "#e15759"
COLOR_GREEN = "#59a14f"
COLOR_GRAY = "#999999"

NOTE_DIR = os.path.expanduser(
    "~/ghq/github.com/nao1215/debimate/projects/ml/notes/math/eigen-decomposition"
)
os.makedirs(NOTE_DIR, exist_ok=True)


def save(name: str) -> None:
    plt.savefig(os.path.join(NOTE_DIR, name), bbox_inches="tight")
    plt.close()


# ============================================================
# Fig 1: Action of A on many vectors - eigenvectors keep direction
# ============================================================
A = np.array([[2.0, 1.0], [0.0, 3.0]])
eigvals, eigvecs = np.linalg.eig(A)

angles = np.linspace(0, np.pi, 18, endpoint=False)
vs = np.column_stack([np.cos(angles), np.sin(angles)])
Avs = (A @ vs.T).T

fig, axes = plt.subplots(1, 2, figsize=(11, 5))

ax = axes[0]
for v in vs:
    ax.quiver(0, 0, *v, angles="xy", scale_units="xy", scale=1, color=COLOR_BLUE, alpha=0.5,
              width=0.005)
# Highlight eigenvectors
for i in range(2):
    ev = eigvecs[:, i] / np.linalg.norm(eigvecs[:, i])
    ax.quiver(0, 0, *ev, angles="xy", scale_units="xy", scale=1, color=COLOR_RED,
              width=0.012, label=f"eigvec λ={eigvals[i]:.1f}")
ax.set_xlim(-1.5, 1.5); ax.set_ylim(-1.2, 1.2)
ax.set_aspect("equal"); ax.grid(True, alpha=0.25)
ax.set_title("Before A: unit vectors and eigenvector directions (red)")
ax.legend(loc="lower left", fontsize=8)

ax = axes[1]
for v, Av in zip(vs, Avs):
    ax.quiver(0, 0, *Av, angles="xy", scale_units="xy", scale=1, color=COLOR_BLUE, alpha=0.5,
              width=0.005)
for i in range(2):
    ev = eigvecs[:, i] / np.linalg.norm(eigvecs[:, i])
    Aev = A @ ev
    ax.quiver(0, 0, *Aev, angles="xy", scale_units="xy", scale=1, color=COLOR_RED,
              width=0.012, label=f"A·eigvec = λ·eigvec ({eigvals[i]:.1f}x)")
ax.set_xlim(-4, 4); ax.set_ylim(-3.5, 3.5)
ax.set_aspect("equal"); ax.grid(True, alpha=0.25)
ax.set_title("After A: most rotate, eigenvectors only scale")
ax.legend(loc="lower left", fontsize=8)

plt.tight_layout()
save("eigen_action.svg")


# ============================================================
# Fig 2: Covariance matrix eigenvectors = principal axes
# ============================================================
rng = np.random.default_rng(0)
mean = [0, 0]
cov = [[3.0, 1.4], [1.4, 1.2]]
data = rng.multivariate_normal(mean, cov, size=400)

cov_emp = np.cov(data.T)
eigvals2, eigvecs2 = np.linalg.eigh(cov_emp)
# Sort by descending eigenvalue
order = np.argsort(eigvals2)[::-1]
eigvals2 = eigvals2[order]
eigvecs2 = eigvecs2[:, order]

plt.figure(figsize=(6.5, 6))
plt.scatter(data[:, 0], data[:, 1], alpha=0.4, s=12, color=COLOR_BLUE)
for i, (lam, v) in enumerate(zip(eigvals2, eigvecs2.T)):
    scale = 2 * np.sqrt(lam)
    plt.quiver(0, 0, v[0] * scale, v[1] * scale, angles="xy", scale_units="xy", scale=1,
               color=COLOR_RED if i == 0 else COLOR_GREEN, width=0.012,
               label=f"PC{i+1}: λ={lam:.2f}")
plt.gca().set_aspect("equal")
plt.title("Covariance eigenvectors = principal axes of the cloud\n(arrow length ∝ √λ)")
plt.xlabel("x1"); plt.ylabel("x2")
plt.legend(loc="upper left")
plt.grid(True, alpha=0.25)
plt.tight_layout()
save("cov_eigen_pca.png")


# ============================================================
# Fig 3: Spectrum and explained variance ratio
# ============================================================
# Higher-dim synthetic data
rng = np.random.default_rng(0)
true_components = np.array([
    [3.0, 0.0, 0.0, 0.0, 0.0],
    [0.0, 2.0, 0.0, 0.0, 0.0],
    [0.0, 0.0, 1.2, 0.0, 0.0],
    [0.0, 0.0, 0.0, 0.6, 0.0],
    [0.0, 0.0, 0.0, 0.0, 0.2],
])
Z = rng.standard_normal((600, 5))
X = Z @ true_components
cov_emp = np.cov(X.T)
eigvals5, _ = np.linalg.eigh(cov_emp)
eigvals5 = np.sort(eigvals5)[::-1]
ratio = eigvals5 / eigvals5.sum()
cumratio = np.cumsum(ratio)

fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
axes[0].bar(range(1, 6), eigvals5, color=COLOR_BLUE, edgecolor="white")
for i, v in enumerate(eigvals5, start=1):
    axes[0].text(i, v + 0.1, f"{v:.2f}", ha="center", fontsize=9)
axes[0].set_xlabel("Component index")
axes[0].set_ylabel("Eigenvalue λ_i")
axes[0].set_title("Spectrum: eigenvalue per component")
axes[0].grid(True, alpha=0.25, axis="y")

axes[1].bar(range(1, 6), ratio, color=COLOR_BLUE, edgecolor="white",
            label="per-component ratio")
axes[1].plot(range(1, 6), cumratio, "o-", color=COLOR_RED, lw=2, label="cumulative ratio")
for i, v in enumerate(cumratio, start=1):
    axes[1].text(i, v + 0.03, f"{v:.2f}", ha="center", fontsize=9, color=COLOR_RED)
axes[1].set_xlabel("Component index")
axes[1].set_ylabel("Explained variance ratio")
axes[1].set_title("How much variance each PC explains")
axes[1].set_ylim(0, 1.1)
axes[1].legend(fontsize=9)
axes[1].grid(True, alpha=0.25, axis="y")

plt.tight_layout()
save("eigen_spectrum.svg")


# ============================================================
# Fig 4: Diagonalization as 'rotate-scale-rotate-back'
# ============================================================
A = np.array([[3.0, 1.0], [1.0, 2.0]])  # symmetric
eigvals, eigvecs = np.linalg.eigh(A)
# Sort descending
order = np.argsort(eigvals)[::-1]
eigvals = eigvals[order]
eigvecs = eigvecs[:, order]

# Make a circle
theta = np.linspace(0, 2 * np.pi, 100)
circle = np.array([np.cos(theta), np.sin(theta)])

# Stage 1: original circle
# Stage 2: after rotating into eigenbasis (Q^T)
Q = eigvecs
QT_circle = Q.T @ circle
# Stage 3: after applying Λ (scale)
Lambda = np.diag(eigvals)
scaled = Lambda @ QT_circle
# Stage 4: rotate back
final = Q @ scaled
# Verify: final == A @ circle
true_final = A @ circle

fig, axes = plt.subplots(1, 4, figsize=(15, 4.2), sharex=True, sharey=True)
stages = [
    (circle, "1. Original unit circle", COLOR_BLUE),
    (QT_circle, "2. Rotate to eigenbasis (Q^T)", COLOR_GREEN),
    (scaled, "3. Scale by eigenvalues (Λ)", COLOR_RED),
    (final, "4. Rotate back (Q)\n= same as A·x", COLOR_BLUE),
]
for ax, (data, title, color) in zip(axes, stages):
    ax.plot(data[0], data[1], color=color, lw=2)
    ax.fill(data[0], data[1], color=color, alpha=0.2)
    ax.axhline(0, color=COLOR_GRAY, lw=0.5)
    ax.axvline(0, color=COLOR_GRAY, lw=0.5)
    ax.set_aspect("equal")
    ax.set_xlim(-4, 4); ax.set_ylim(-4, 4)
    ax.grid(True, alpha=0.25)
    ax.set_title(title, fontsize=9)
plt.suptitle("Spectral decomposition: A = Q Λ Q^T as rotate-scale-rotate-back", y=1.02)
plt.tight_layout()
save("diagonalization_steps.svg")


print("done:", sorted(os.listdir(NOTE_DIR)))
