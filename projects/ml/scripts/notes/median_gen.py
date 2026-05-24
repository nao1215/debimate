"""median ノート用の図を生成するスクリプト。

実行: cd projects/ml && uv run python scripts/notes/median_gen.py
"""
import os

import matplotlib.pyplot as plt
import numpy as np

COLOR_BLUE = "#7aa6c2"
COLOR_RED = "#e15759"
COLOR_GREEN = "#59a14f"
COLOR_ORANGE = "#f28e2b"

NOTE_DIR = os.path.expanduser(
    "~/ghq/github.com/nao1215/debimate/projects/ml/notes/math/median"
)
os.makedirs(NOTE_DIR, exist_ok=True)


def save(name):
    plt.savefig(os.path.join(NOTE_DIR, name), bbox_inches="tight")
    plt.close()


rng = np.random.default_rng(0)

# --- 図1: 外れ値追加前後の mean vs median ---
base = rng.normal(loc=10.0, scale=2.0, size=200)
outlier = np.concatenate([base, [100.0, 120.0, 95.0]])

fig, axes = plt.subplots(1, 2, figsize=(10, 3.5))

for ax, data, title in [(axes[0], base, "Without outliers"),
                         (axes[1], outlier, "With 3 large outliers")]:
    ax.hist(data, bins=30, color=COLOR_BLUE, edgecolor="white")
    m = data.mean()
    med = np.median(data)
    ax.axvline(m, color=COLOR_RED, linestyle="--", linewidth=2,
               label=f"mean = {m:.2f}")
    ax.axvline(med, color=COLOR_GREEN, linestyle="--", linewidth=2,
               label=f"median = {med:.2f}")
    ax.set_title(title)
    ax.set_xlabel("Value")
    ax.set_ylabel("Count")
    ax.legend(fontsize=9)
plt.tight_layout()
save("median_outlier_effect.svg")


# --- 図2: L1 損失と median, L2 損失と mean ---
data = np.array([2.0, 3.0, 4.0, 5.0, 20.0])
candidates = np.linspace(0, 25, 200)
l1 = np.array([np.abs(data - c).sum() for c in candidates])
l2 = np.array([((data - c) ** 2).sum() for c in candidates])

l1_min = candidates[l1.argmin()]
l2_min = candidates[l2.argmin()]

fig, axes = plt.subplots(1, 2, figsize=(9, 3.5))
axes[0].plot(candidates, l1, color=COLOR_BLUE, linewidth=2)
axes[0].axvline(l1_min, color=COLOR_RED, linestyle="--",
                label=f"argmin = {l1_min:.2f}  (median = {np.median(data):.0f})")
axes[0].set_title("L1 loss  Sum|x - c|")
axes[0].set_xlabel("candidate c")
axes[0].set_ylabel("loss")
axes[0].legend(fontsize=9)

axes[1].plot(candidates, l2, color=COLOR_GREEN, linewidth=2)
axes[1].axvline(l2_min, color=COLOR_RED, linestyle="--",
                label=f"argmin = {l2_min:.2f}  (mean = {data.mean():.1f})")
axes[1].set_title("L2 loss  Sum(x - c)^2")
axes[1].set_xlabel("candidate c")
axes[1].set_ylabel("loss")
axes[1].legend(fontsize=9)
plt.tight_layout()
save("median_l1_vs_l2.svg")

print("Mean:", base.mean(), "->", outlier.mean())
print("Median:", np.median(base), "->", np.median(outlier))
