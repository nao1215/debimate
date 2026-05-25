"""joint-marginal-conditional ノート用の図を生成するスクリプト。

実行: cd projects/ml && uv run python scripts/notes/joint-marginal-conditional_gen.py
"""
import os

import matplotlib.pyplot as plt
import numpy as np

COLOR_BLUE = "#7aa6c2"
COLOR_RED = "#e15759"
COLOR_GREEN = "#59a14f"

NOTE_DIR = os.path.expanduser(
    "~/ghq/github.com/nao1215/debimate/projects/ml/notes/math/joint-marginal-conditional"
)
os.makedirs(NOTE_DIR, exist_ok=True)


def save(name: str) -> None:
    plt.savefig(os.path.join(NOTE_DIR, name), bbox_inches="tight")
    plt.close()


rng = np.random.default_rng(0)


# --- 図1: 離散の同時分布 + 周辺分布 ---
# 例: x=雲量 {少, 中, 多} × y=雨 {降る, 降らない}
x_labels = ["clouds=low", "clouds=mid", "clouds=high"]
y_labels = ["rain=yes", "rain=no"]
joint = np.array([
    [0.02, 0.28],
    [0.08, 0.22],
    [0.30, 0.10],
])

p_x = joint.sum(axis=1)  # 行方向の和 = P(x)
p_y = joint.sum(axis=0)  # 列方向の和 = P(y)

fig = plt.figure(figsize=(7, 5))
gs = fig.add_gridspec(2, 2, width_ratios=[3, 1], height_ratios=[1, 3],
                      hspace=0.05, wspace=0.05)

ax_top = fig.add_subplot(gs[0, 0])
ax_main = fig.add_subplot(gs[1, 0])
ax_right = fig.add_subplot(gs[1, 1])

im = ax_main.imshow(joint, cmap="Blues", aspect="auto", vmin=0, vmax=0.35)
for i in range(joint.shape[0]):
    for j in range(joint.shape[1]):
        ax_main.text(j, i, f"{joint[i, j]:.2f}",
                     ha="center", va="center",
                     color="black" if joint[i, j] < 0.2 else "white")
ax_main.set_xticks(range(len(y_labels)))
ax_main.set_xticklabels(y_labels)
ax_main.set_yticks(range(len(x_labels)))
ax_main.set_yticklabels(x_labels)
ax_main.set_xlabel("y (rain)")
ax_main.set_ylabel("x (clouds)")

ax_top.bar(range(len(y_labels)), p_y, color=COLOR_GREEN, edgecolor="white")
ax_top.set_xticks([])
ax_top.set_ylabel("P(y)\nmarginal")
for j, v in enumerate(p_y):
    ax_top.text(j, v + 0.02, f"{v:.2f}", ha="center", fontsize=9)
ax_top.set_xlim(-0.5, len(y_labels) - 0.5)
ax_top.set_ylim(0, 0.8)

ax_right.barh(range(len(x_labels)), p_x, color=COLOR_RED, edgecolor="white")
ax_right.set_yticks([])
ax_right.invert_yaxis()
ax_right.set_xlabel("P(x)\nmarginal")
for i, v in enumerate(p_x):
    ax_right.text(v + 0.02, i, f"{v:.2f}", va="center", fontsize=9)
ax_right.set_ylim(len(x_labels) - 0.5, -0.5)
ax_right.set_xlim(0, 0.55)

fig.suptitle("Joint P(x,y) and marginals P(x), P(y)", fontsize=11)
save("joint-marginal-conditional_discrete.svg")


# --- 図2: 同じ joint から条件付き分布を取り出す ---
# P(y | x=k) = P(x=k, y) / P(x=k) で、行を P(x) で割る。
conditionals = joint / p_x[:, None]

fig, axes = plt.subplots(1, 3, figsize=(10, 3.2), sharey=True)
for i, (ax, xlbl) in enumerate(zip(axes, x_labels)):
    ax.bar(y_labels, conditionals[i], color=COLOR_BLUE, edgecolor="white")
    for j, v in enumerate(conditionals[i]):
        ax.text(j, v + 0.02, f"{v:.2f}", ha="center", fontsize=10)
    ax.set_title(f"P(y | {xlbl})")
    ax.set_ylim(0, 1.05)
axes[0].set_ylabel("Conditional probability")
fig.suptitle("Conditional distributions: each row of the joint normalized",
             fontsize=11)
plt.tight_layout()
save("joint-marginal-conditional_conditional.svg")


# --- 図3: 連続の同時分布 (2D 正規) + 周辺分布 ---
# 相関 0.7 の二次元正規から 1000 サンプル。
mean = [0, 0]
cov = [[1.0, 0.7], [0.7, 1.0]]
samples = rng.multivariate_normal(mean, cov, size=1000)

fig = plt.figure(figsize=(7, 5))
gs = fig.add_gridspec(2, 2, width_ratios=[3, 1], height_ratios=[1, 3],
                      hspace=0.05, wspace=0.05)
ax_top = fig.add_subplot(gs[0, 0])
ax_main = fig.add_subplot(gs[1, 0])
ax_right = fig.add_subplot(gs[1, 1])

ax_main.scatter(samples[:, 0], samples[:, 1], s=8, alpha=0.4,
                color=COLOR_BLUE)
ax_main.set_xlabel("x")
ax_main.set_ylabel("y")
ax_main.axhline(0, color="gray", linewidth=0.5, alpha=0.5)
ax_main.axvline(0, color="gray", linewidth=0.5, alpha=0.5)

ax_top.hist(samples[:, 0], bins=30, color=COLOR_GREEN, edgecolor="white")
ax_top.set_xticks([])
ax_top.set_ylabel("P(x)\nmarginal")

ax_right.hist(samples[:, 1], bins=30, color=COLOR_RED, edgecolor="white",
              orientation="horizontal")
ax_right.set_yticks([])
ax_right.set_xlabel("P(y)\nmarginal")

ax_top.set_xlim(ax_main.get_xlim())
ax_right.set_ylim(ax_main.get_ylim())

fig.suptitle("Continuous joint and marginals (correlated 2D Gaussian)",
             fontsize=11)
save("joint-marginal-conditional_continuous.svg")


print("Saved figures to:", NOTE_DIR)
print(f"P(x) = {p_x}")
print(f"P(y) = {p_y}")
print(f"P(y | x=low)  = {conditionals[0]}")
print(f"P(y | x=mid)  = {conditionals[1]}")
print(f"P(y | x=high) = {conditionals[2]}")
