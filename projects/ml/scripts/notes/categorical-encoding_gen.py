"""categorical-encoding ノート用の図を生成するスクリプト。

実行: cd projects/ml && uv run python scripts/notes/categorical-encoding_gen.py
"""
import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder, TargetEncoder

COLOR_BLUE = "#7aa6c2"
COLOR_RED = "#e15759"
COLOR_GREEN = "#59a14f"

NOTE_DIR = os.path.expanduser(
    "~/ghq/github.com/nao1215/debimate/projects/ml/notes/ml/categorical-encoding"
)
os.makedirs(NOTE_DIR, exist_ok=True)


def save(name: str) -> None:
    plt.savefig(os.path.join(NOTE_DIR, name), bbox_inches="tight")
    plt.close()


# --- 図1: 同じ入力に対する 4 種の出力比較 ---
data = pd.DataFrame({
    "category": ["A", "B", "C", "A", "B", "C"],
    "target":   [10,  20,  30,  12,  18,  32],
})

oh = OneHotEncoder(sparse_output=False).fit_transform(data[["category"]])
ord_enc = OrdinalEncoder().fit_transform(data[["category"]])
target_map = data.groupby("category")["target"].mean()
te = data["category"].map(target_map).values.reshape(-1, 1)

hash_dim = 2
hash_result = np.zeros((len(data), hash_dim))
for i, c in enumerate(data["category"]):
    hash_result[i, hash(c) % hash_dim] = 1

fig = plt.figure(figsize=(14, 3.5))
gs = fig.add_gridspec(1, 4, width_ratios=[3, 1, 1.4, 2])
axes = [fig.add_subplot(gs[0, i]) for i in range(4)]

axes[0].imshow(oh, cmap="Blues", aspect="auto", vmin=0, vmax=1)
for i in range(oh.shape[0]):
    for j in range(oh.shape[1]):
        axes[0].text(j, i, str(int(oh[i, j])), ha="center", va="center",
                     color="black" if oh[i, j] < 0.5 else "white")
axes[0].set_xticks(range(3))
axes[0].set_xticklabels(["A", "B", "C"])
axes[0].set_yticks(range(len(data)))
axes[0].set_yticklabels(data["category"])
axes[0].set_title("One-hot encoding\n(3 columns)")

axes[1].imshow(ord_enc, cmap="Greens", aspect="auto", vmin=0, vmax=2)
for i in range(len(data)):
    axes[1].text(0, i, f"{int(ord_enc[i, 0])}", ha="center", va="center",
                 color="black")
axes[1].set_xticks([0])
axes[1].set_xticklabels(["int"])
axes[1].set_yticks(range(len(data)))
axes[1].set_yticklabels(data["category"])
axes[1].set_title("Ordinal\n(1 column)")

axes[2].imshow(te, cmap="Reds", aspect="auto", vmin=0, vmax=40)
for i in range(len(data)):
    axes[2].text(0, i, f"{te[i, 0]:.0f}", ha="center", va="center",
                 color="black")
axes[2].set_xticks([0])
axes[2].set_xticklabels(["target mean"])
axes[2].set_yticks(range(len(data)))
axes[2].set_yticklabels(data["category"])
axes[2].set_title("Target encoding\n(1 column)")

axes[3].imshow(hash_result, cmap="Purples", aspect="auto", vmin=0, vmax=1)
for i in range(hash_result.shape[0]):
    for j in range(hash_result.shape[1]):
        axes[3].text(j, i, str(int(hash_result[i, j])),
                     ha="center", va="center",
                     color="black" if hash_result[i, j] < 0.5 else "white")
axes[3].set_xticks(range(hash_dim))
axes[3].set_xticklabels([f"h{i}" for i in range(hash_dim)])
axes[3].set_yticks(range(len(data)))
axes[3].set_yticklabels(data["category"])
axes[3].set_title("Hashing trick\n(fixed 2 columns)")

fig.suptitle("Same input column, four encoding outputs", fontsize=11)
plt.tight_layout()
save("categorical-encoding_methods.svg")


# --- 図2: 基数増加に伴う列数の挙動 ---
cardinalities = [2, 10, 100, 1_000, 10_000, 100_000, 1_000_000]
onehot_cols = cardinalities
target_cols = [1] * len(cardinalities)
hash_cols = [16] * len(cardinalities)

fig, ax = plt.subplots(figsize=(7.5, 4))
ax.loglog(cardinalities, onehot_cols, "o-", color=COLOR_RED, linewidth=2,
          label="One-hot (= cardinality)")
ax.loglog(cardinalities, target_cols, "s-", color=COLOR_GREEN, linewidth=2,
          label="Target encoding (1 column)")
ax.loglog(cardinalities, hash_cols, "^-", color=COLOR_BLUE, linewidth=2,
          label="Hashing trick (fixed)")
ax.axvspan(10_000, 1_000_000, alpha=0.15, color=COLOR_RED,
           label="One-hot infeasible zone")
ax.set_xlabel("Cardinality (number of unique categories)")
ax.set_ylabel("Resulting feature columns")
ax.set_title("One-hot column count explodes with cardinality")
ax.legend(loc="upper left")
ax.grid(True, which="both", alpha=0.3)
plt.tight_layout()
save("categorical-encoding_cardinality.svg")


# --- 図3: Target encoding leak demo ---
# 真の信号が無いランダムラベル + 50 カテゴリ。
# Wrong: 全データで集約 → リーク
# Correct: Pipeline 内の TargetEncoder が CV fold で正しく fit
rng = np.random.default_rng(0)
n = 500
df = pd.DataFrame({"cat": rng.integers(0, 50, n).astype(str)})
y = rng.integers(0, 2, n)

target_map = (pd.DataFrame({"cat": df["cat"], "y": y})
              .groupby("cat")["y"].mean())
X_wrong = df["cat"].map(target_map).values.reshape(-1, 1)
cv_wrong = cross_val_score(
    LogisticRegression(max_iter=2000), X_wrong, y, cv=5,
).mean()

pipe = Pipeline([
    ("te", TargetEncoder(target_type="binary", smooth="auto", random_state=0)),
    ("clf", LogisticRegression(max_iter=2000)),
])
cv_correct = cross_val_score(pipe, df[["cat"]], y, cv=5).mean()

fig, ax = plt.subplots(figsize=(6.5, 4))
ax.bar(["Wrong\n(fit on full data)", "Correct\n(Pipeline + CV folds)"],
       [cv_wrong, cv_correct],
       color=[COLOR_RED, COLOR_BLUE], edgecolor="white")
ax.axhline(0.5, color="gray", linestyle="--", label="chance level (0.5)")
ax.set_ylim(0, 1.0)
ax.set_ylabel("CV accuracy (5-fold)")
ax.set_title("Random labels, 50 random categories:\n"
             "target encoding leaks if fit before split")
ax.legend(loc="lower right")
for i, v in enumerate([cv_wrong, cv_correct]):
    ax.text(i, v + 0.02, f"{v:.3f}", ha="center", fontsize=10)
plt.tight_layout()
save("categorical-encoding_leak.svg")


print("Saved figures to:", NOTE_DIR)
print(f"Target leak demo:")
print(f"  Wrong (full-data fit): CV accuracy = {cv_wrong:.3f}")
print(f"  Correct (Pipeline):    CV accuracy = {cv_correct:.3f}")
