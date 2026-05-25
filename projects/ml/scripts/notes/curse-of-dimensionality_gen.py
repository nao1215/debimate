"""curse-of-dimensionality ノート用の図を生成するスクリプト。

実行: cd projects/ml && uv run python scripts/notes/curse-of-dimensionality_gen.py
"""
import math
import os

import matplotlib.pyplot as plt
import numpy as np
from sklearn.datasets import make_classification
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import StandardScaler

COLOR_BLUE = "#7aa6c2"
COLOR_RED = "#e15759"
COLOR_GREEN = "#59a14f"

NOTE_DIR = os.path.expanduser(
    "~/ghq/github.com/nao1215/debimate/projects/ml/notes/ml/curse-of-dimensionality"
)
os.makedirs(NOTE_DIR, exist_ok=True)


def save(name: str) -> None:
    plt.savefig(os.path.join(NOTE_DIR, name), bbox_inches="tight")
    plt.close()


rng = np.random.default_rng(0)


# --- 図1: 距離の意味喪失 ---
# 1000 点をランダム配置して、ある 1 点から見たほかの点までの距離の
# min / median / max の比を次元別に計算する。
# 次元が大きくなると min/max が 1 に近づく = 距離が全部似た値になる。
dims = [2, 5, 10, 20, 50, 100, 500, 1000, 5000]
ratios_min_over_max = []
distance_spreads = []  # (max - min) / mean

for d in dims:
    points = rng.standard_normal((1000, d))
    anchor = points[0]
    dists = np.linalg.norm(points[1:] - anchor, axis=1)
    ratios_min_over_max.append(dists.min() / dists.max())
    distance_spreads.append((dists.max() - dists.min()) / dists.mean())

fig, axes = plt.subplots(1, 2, figsize=(11, 4))
axes[0].plot(dims, ratios_min_over_max, "o-", color=COLOR_BLUE, linewidth=2)
axes[0].set_xscale("log")
axes[0].set_xlabel("dimension d (log scale)")
axes[0].set_ylabel("min distance / max distance")
axes[0].set_title("Nearest / farthest distance ratio approaches 1")
axes[0].set_ylim(0, 1.05)
axes[0].axhline(1.0, color="gray", linestyle="--", alpha=0.5)

axes[1].plot(dims, distance_spreads, "o-", color=COLOR_RED, linewidth=2)
axes[1].set_xscale("log")
axes[1].set_xlabel("dimension d (log scale)")
axes[1].set_ylabel("(max - min) / mean distance")
axes[1].set_title("Relative distance spread shrinks")

plt.tight_layout()
save("curse-of-dimensionality_distance.svg")


# --- 図2: kNN/LR/RF の精度劣化シミュレーション ---
# 5 個の信号特徴量に大量のノイズ特徴量を足していき、3 モデルを比較。
def make_dataset(n_noise_features: int, seed: int = 0):
    X_sig, y = make_classification(
        n_samples=500, n_features=5, n_informative=5,
        n_redundant=0, random_state=seed,
    )
    if n_noise_features > 0:
        local_rng = np.random.default_rng(seed)
        X_noise = local_rng.standard_normal((500, n_noise_features))
        return np.column_stack([X_sig, X_noise]), y
    return X_sig, y


noise_levels = [0, 10, 50, 100, 500, 1000, 5000]
scores = {"kNN": [], "LR (L2)": [], "RF": []}

for n_noise in noise_levels:
    X, y = make_dataset(n_noise)
    # スケール感を揃えるため標準化
    X_std = StandardScaler().fit_transform(X)
    scores["kNN"].append(cross_val_score(
        KNeighborsClassifier(n_neighbors=5), X_std, y, cv=5).mean())
    scores["LR (L2)"].append(cross_val_score(
        LogisticRegression(max_iter=2000), X_std, y, cv=5).mean())
    scores["RF"].append(cross_val_score(
        RandomForestClassifier(n_estimators=100, random_state=0),
        X_std, y, cv=5).mean())

dims_total = [5 + n for n in noise_levels]
fig, ax = plt.subplots(figsize=(8, 4.5))
for name, color in zip(["LR (L2)", "RF", "kNN"],
                       [COLOR_GREEN, COLOR_BLUE, COLOR_RED]):
    ax.plot(dims_total, scores[name], "o-", color=color,
            linewidth=2, label=name)
ax.set_xscale("log")
ax.set_xlabel("Total feature count (5 informative + N noise)")
ax.set_ylabel("CV accuracy (5-fold)")
ax.set_title("kNN degrades sharply as noise dimensions grow")
ax.axhline(0.5, color="gray", linestyle="--", alpha=0.5,
           label="chance level")
ax.set_ylim(0.4, 1.0)
ax.legend()
plt.tight_layout()
save("curse-of-dimensionality_knn_decay.svg")


# --- 図3: 単位球の体積が次元で消える ---
# 半径 1 の d 次元球の体積: V_d = pi^(d/2) / Gamma(d/2 + 1)
# d=5 付近をピークに、その後急減して d=20 でほぼ 0。
d_values = list(range(1, 26))
volumes = [math.pi ** (d / 2) / math.gamma(d / 2 + 1) for d in d_values]

fig, ax = plt.subplots(figsize=(7, 4))
ax.plot(d_values, volumes, "o-", color=COLOR_BLUE, linewidth=2)
ax.set_xlabel("dimension d")
ax.set_ylabel("Volume of unit ball")
ax.set_title(
    "Volume of unit ball peaks around d=5 and vanishes for high d"
)
ax.set_xticks([1, 5, 10, 15, 20, 25])
plt.tight_layout()
save("curse-of-dimensionality_volume.svg")


print("Saved figures to:", NOTE_DIR)
print("\nDistance ratio min/max by dimension:")
for d, r in zip(dims, ratios_min_over_max):
    print(f"  d={d:<5d} min/max = {r:.3f}")
print("\nCV accuracy by total feature count:")
print(f"  {'dim':>6} {'LR':>8} {'RF':>8} {'kNN':>8}")
for d, lr_s, rf_s, knn_s in zip(
    dims_total, scores["LR (L2)"], scores["RF"], scores["kNN"]
):
    print(f"  {d:>6} {lr_s:>8.3f} {rf_s:>8.3f} {knn_s:>8.3f}")
print(f"\nUnit-ball volume at d=5: {volumes[4]:.4f}")
print(f"Unit-ball volume at d=20: {volumes[19]:.6e}")
