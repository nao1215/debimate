"""information-theory ノート用の図を生成するスクリプト。

実行: cd projects/ml && uv run python scripts/notes/information-theory_gen.py
"""
import os

import matplotlib.pyplot as plt
import numpy as np

COLOR_BLUE = "#7aa6c2"
COLOR_RED = "#e15759"
COLOR_GREEN = "#59a14f"
COLOR_ORANGE = "#f28e2b"
COLOR_PURPLE = "#b07aa1"

NOTE_DIR = os.path.expanduser(
    "~/ghq/github.com/nao1215/debimate/projects/ml/notes/math/information-theory"
)
os.makedirs(NOTE_DIR, exist_ok=True)


def save(name: str) -> None:
    plt.savefig(os.path.join(NOTE_DIR, name), bbox_inches="tight")
    plt.close()


# ============================================================
# Fig 1: -log(p) shape and information content
# ============================================================
p = np.linspace(0.001, 1, 400)
plt.figure(figsize=(8, 4.5))
plt.plot(p, -np.log2(p), color=COLOR_BLUE, lw=2.5)
plt.xlabel("P(event)")
plt.ylabel("Information I(x) = -log₂ P(x) (bits)")
plt.title("Self-information: rare events carry more bits")
# Annotate some points
for p_val, label in [(0.5, "fair coin\n1 bit"),
                       (0.25, "1/4\n2 bits"),
                       (0.125, "1/8\n3 bits"),
                       (1.0, "certain\n0 bits")]:
    plt.scatter([p_val], [-np.log2(p_val)], s=80, color=COLOR_RED, zorder=5)
    plt.annotate(label, (p_val, -np.log2(p_val)),
                 xytext=(p_val + 0.05, -np.log2(p_val) + 0.5),
                 fontsize=9)
plt.grid(True, alpha=0.25)
plt.ylim(-0.5, 10)
plt.tight_layout()
save("info_self_information.svg")


# ============================================================
# Fig 2: Entropy of Bernoulli vs p
# ============================================================
ps = np.linspace(0.001, 0.999, 400)
H = -(ps * np.log2(ps) + (1 - ps) * np.log2(1 - ps))

plt.figure(figsize=(7.5, 4.5))
plt.plot(ps, H, color=COLOR_BLUE, lw=2.5)
plt.axvline(0.5, color=COLOR_RED, ls="--", lw=1.5,
            label="max entropy at p=0.5\n(H = 1 bit)")
plt.scatter([0.5], [1.0], color=COLOR_RED, s=100, zorder=5)
plt.xlabel("p (probability of class 1)")
plt.ylabel("Entropy H(X) (bits)")
plt.title("Bernoulli entropy: maximum uncertainty at p = 0.5")
plt.legend()
plt.grid(True, alpha=0.25)
plt.ylim(0, 1.1)
plt.tight_layout()
save("info_bernoulli_entropy.svg")


# ============================================================
# Fig 3: KL divergence between two distributions
# ============================================================
fig, axes = plt.subplots(1, 3, figsize=(14, 4.5))

cases = [
    ("Identical distributions\nKL = 0", [0.25, 0.25, 0.25, 0.25],
     [0.25, 0.25, 0.25, 0.25]),
    ("Mild divergence",  [0.4, 0.3, 0.2, 0.1], [0.25, 0.25, 0.25, 0.25]),
    ("Strong divergence", [0.7, 0.2, 0.05, 0.05], [0.25, 0.25, 0.25, 0.25]),
]
xs = np.arange(4)
width = 0.4

for ax, (title, p, q) in zip(axes, cases):
    p, q = np.array(p), np.array(q)
    kl = (p * np.log2(p / q)).sum()
    ax.bar(xs - width/2, p, width, color=COLOR_BLUE, edgecolor="white",
           label="P (true)")
    ax.bar(xs + width/2, q, width, color=COLOR_RED, edgecolor="white",
           label="Q (model)")
    ax.set_xticks(xs); ax.set_xticklabels(["A", "B", "C", "D"])
    ax.set_ylim(0, 0.8)
    ax.set_ylabel("probability")
    ax.set_title(f"{title}\nKL(P || Q) = {kl:.3f} bits")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.25, axis="y")

plt.suptitle("KL divergence: how 'wrong' a model distribution Q is vs true P", y=1.02)
plt.tight_layout()
save("info_kl_divergence.svg")


# ============================================================
# Fig 4: Cross-entropy = H(P) + KL(P||Q) -> ML loss interpretation
# ============================================================
fig, ax = plt.subplots(figsize=(9, 5))

# Bar decomposition: cross-entropy = entropy + KL
H_p = 1.0  # constant entropy of true distribution
kls = np.linspace(0, 2, 7)
ces = H_p + kls

ax.bar(range(len(kls)), [H_p] * len(kls), color=COLOR_GREEN, edgecolor="white",
       label="H(P) (irreducible, fixed)")
ax.bar(range(len(kls)), kls, bottom=[H_p] * len(kls), color=COLOR_RED, edgecolor="white",
       label="KL(P || Q) (model error, reducible)")
for i, (kl, ce) in enumerate(zip(kls, ces)):
    ax.text(i, ce + 0.05, f"CE={ce:.2f}", ha="center", fontsize=9)
ax.set_xticks(range(len(kls)))
ax.set_xticklabels([f"KL={kl:.2f}" for kl in kls])
ax.set_ylabel("Cross-entropy")
ax.set_title("Cross-entropy decomposition:\nH(P, Q) = H(P) + KL(P || Q)\n→ minimizing CE = minimizing KL (since H(P) is fixed)")
ax.legend(loc="upper left")
ax.grid(True, alpha=0.25, axis="y")
plt.tight_layout()
save("info_cross_entropy_decomp.svg")


# ============================================================
# Fig 5: Mutual information visualization (Venn-like)
# ============================================================
fig, ax = plt.subplots(figsize=(8, 5))

# Two overlapping circles representing entropy of X and Y
import matplotlib.patches as patches

circle_x = patches.Circle((-0.5, 0), 1.4, facecolor=COLOR_BLUE, alpha=0.4,
                           edgecolor="black", linewidth=1.5)
circle_y = patches.Circle((0.5, 0), 1.4, facecolor=COLOR_RED, alpha=0.4,
                           edgecolor="black", linewidth=1.5)
ax.add_patch(circle_x)
ax.add_patch(circle_y)

ax.text(-1.3, 1.5, "H(X)", fontsize=14, color=COLOR_BLUE, fontweight="bold")
ax.text(1.0, 1.5, "H(Y)", fontsize=14, color=COLOR_RED, fontweight="bold")

# Region labels
ax.text(-1.0, 0, "H(X|Y)", ha="center", fontsize=11, fontweight="bold")
ax.text(0.0, 0, "I(X;Y)\nmutual\ninformation", ha="center", fontsize=10,
        fontweight="bold")
ax.text(1.0, 0, "H(Y|X)", ha="center", fontsize=11, fontweight="bold")

ax.set_xlim(-2.5, 2.5); ax.set_ylim(-2, 2)
ax.set_aspect("equal")
ax.axis("off")
ax.set_title("Information diagram: H(X), H(Y), and their mutual information")
plt.tight_layout()
save("info_mutual_information.svg")


print("done:", sorted(os.listdir(NOTE_DIR)))
