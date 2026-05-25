"""data-drift ノート用の図を生成するスクリプト。

実行: cd projects/ml && uv run python scripts/notes/data-drift_gen.py
"""
import os

import matplotlib.pyplot as plt
import numpy as np

COLOR_BLUE = "#7aa6c2"
COLOR_RED = "#e15759"
COLOR_GREEN = "#59a14f"

NOTE_DIR = os.path.expanduser(
    "~/ghq/github.com/nao1215/debimate/projects/ml/notes/mlops/data-drift"
)
os.makedirs(NOTE_DIR, exist_ok=True)


def save(name: str) -> None:
    plt.savefig(os.path.join(NOTE_DIR, name), bbox_inches="tight")
    plt.close()


rng = np.random.default_rng(0)


# --- 図1: covariate shift ---
# 入力分布 P(x) が訓練時と本番で変化する例。例として「ユーザー年齢」が
# 訓練時は若年中心、本番では年配中心にシフトする。
train_x = rng.normal(loc=30, scale=10, size=2000).clip(0, 100)
prod_x = rng.normal(loc=50, scale=10, size=2000).clip(0, 100)

fig, axes = plt.subplots(1, 2, figsize=(9, 3.5), sharex=True, sharey=True)
axes[0].hist(train_x, bins=30, color=COLOR_BLUE, edgecolor="white")
axes[0].set_title("Train data: age distribution")
axes[0].set_xlabel("age")
axes[0].set_ylabel("count")
axes[1].hist(prod_x, bins=30, color=COLOR_RED, edgecolor="white")
axes[1].set_title("Production data (3 months later)")
axes[1].set_xlabel("age")
fig.suptitle("Covariate shift: P(x) shifts, P(y|x) unchanged", fontsize=11)
plt.tight_layout()
save("data-drift_covariate.svg")


# --- 図2: concept drift ---
# 入力 x の分布は同じ。しかし x と y の関係が時間で反転する例。
x_common = rng.uniform(0, 10, 200)
y_t0 = 2.0 * x_common + rng.normal(0, 1, 200)
y_t1 = -1.5 * x_common + 20 + rng.normal(0, 1, 200)

fig, axes = plt.subplots(1, 2, figsize=(9, 3.5), sharex=True, sharey=True)
axes[0].scatter(x_common, y_t0, alpha=0.5, color=COLOR_BLUE, s=15)
axes[0].set_title("Train (t=0): y is positively related to x")
axes[0].set_xlabel("feature x")
axes[0].set_ylabel("target y")
axes[1].scatter(x_common, y_t1, alpha=0.5, color=COLOR_RED, s=15)
axes[1].set_title("Production (t=3mo): relation has flipped")
axes[1].set_xlabel("feature x")
fig.suptitle("Concept drift: P(y|x) changes, P(x) unchanged", fontsize=11)
plt.tight_layout()
save("data-drift_concept.svg")


# --- 図3: 精度劣化と再学習サイクル ---
# 再学習しなければ単調に下がる精度。4 週ごとに再学習を入れる場合は
# 都度回復するシミュレーション。SLA ラインで運用上の警戒域を示す。
weeks = np.arange(0, 24)
baseline = 0.85 - 0.008 * weeks + rng.normal(0, 0.005, len(weeks))

retrained = baseline.copy()
for w in [4, 8, 12, 16, 20]:
    delta_to_restore = 0.85 - retrained[w]
    retrained[w:] = retrained[w:] + delta_to_restore + rng.normal(
        0, 0.003, size=len(retrained) - w
    )

fig, ax = plt.subplots(figsize=(7, 4))
ax.plot(weeks, baseline, color=COLOR_RED, marker="o", markersize=4,
        label="No retraining (drift)")
ax.plot(weeks, retrained, color=COLOR_GREEN, marker="s", markersize=4,
        label="Periodic retraining (every 4 weeks)")
ax.axhline(0.70, color="gray", linestyle="--", alpha=0.6,
           label="SLA threshold")
ax.set_xlabel("Weeks in production")
ax.set_ylabel("Precision")
ax.set_title("Drift impact: production precision over time")
ax.set_ylim(0.55, 0.92)
ax.legend()
plt.tight_layout()
save("data-drift_decay.svg")


print("Saved figures to:", NOTE_DIR)
