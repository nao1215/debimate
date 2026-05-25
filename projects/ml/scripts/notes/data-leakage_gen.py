"""data-leakage ノート用の図を生成するスクリプト。

実行: cd projects/ml && uv run python scripts/notes/data-leakage_gen.py
"""
import os

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, Rectangle
from sklearn.datasets import make_classification
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score
from sklearn.pipeline import Pipeline

COLOR_BLUE = "#7aa6c2"
COLOR_RED = "#e15759"
COLOR_GREEN = "#59a14f"

NOTE_DIR = os.path.expanduser(
    "~/ghq/github.com/nao1215/debimate/projects/ml/notes/ml/data-leakage"
)
os.makedirs(NOTE_DIR, exist_ok=True)


def save(name: str) -> None:
    plt.savefig(os.path.join(NOTE_DIR, name), bbox_inches="tight")
    plt.close()


rng = np.random.default_rng(0)


# --- 図1: target leakage の CV スコア比較 ---
# 普通の二値分類データを作り、target に強相関なリーク特徴を 1 本足す。
# リークの効果で CV Accuracy が 1.0 に貼り付くのを 1 枚で見せる。
X, y = make_classification(
    n_samples=1000, n_features=10, n_informative=5,
    n_redundant=3, random_state=0,
)
leak_feature = y + 0.05 * rng.standard_normal(len(y))
X_leak = np.column_stack([X, leak_feature])
feature_names_leak = [f"x{i}" for i in range(10)] + ["leak"]

cv_clean = cross_val_score(
    RandomForestClassifier(n_estimators=100, random_state=0),
    X, y, cv=5, scoring="accuracy",
)
cv_leak = cross_val_score(
    RandomForestClassifier(n_estimators=100, random_state=0),
    X_leak, y, cv=5, scoring="accuracy",
)

fig, ax = plt.subplots(figsize=(6, 4))
ax.bar(
    ["Clean", "With leak"],
    [cv_clean.mean(), cv_leak.mean()],
    yerr=[cv_clean.std(), cv_leak.std()],
    color=[COLOR_BLUE, COLOR_RED],
    capsize=8, edgecolor="white",
)
ax.set_ylim(0, 1.08)
ax.set_ylabel("CV accuracy (5-fold mean)")
ax.set_title("CV score: clean vs with-leak")
for i, v in enumerate([cv_clean.mean(), cv_leak.mean()]):
    ax.text(i, v + 0.02, f"{v:.3f}", ha="center", fontsize=10)
plt.tight_layout()
save("data-leakage_cv_score.svg")


# --- 図2: 特徴量重要度がリーク列に集中する ---
rf_leak = RandomForestClassifier(n_estimators=100, random_state=0).fit(X_leak, y)
importances = rf_leak.feature_importances_

fig, ax = plt.subplots(figsize=(7, 4))
colors = [COLOR_BLUE] * 10 + [COLOR_RED]
ax.bar(feature_names_leak, importances, color=colors, edgecolor="white")
ax.set_xticks(range(len(feature_names_leak)))
ax.set_xticklabels(feature_names_leak, rotation=45, ha="right")
ax.set_ylabel("Feature importance")
ax.set_title("RF importance: leak column dominates")
plt.tight_layout()
save("data-leakage_importance.svg")


# --- 図2: target leakage の時間軸イラスト ---
# 予測時点 t を中心に、過去窓 (OK) と未来窓 (NG) を並べる。
fig, ax = plt.subplots(figsize=(8, 3.6))

ax.axhline(y=0, color="black", linewidth=1, zorder=1)

t_pred = 0.0
ax.axvline(x=t_pred, color="black", linestyle="-", linewidth=2, zorder=2)
ax.text(t_pred, 1.55, "Prediction time t\n(order confirmed)",
        ha="center", fontsize=10)

# 過去 30 日の集計 (OK, green)
ax.add_patch(Rectangle((-3.0, 0.25), 3.0, 0.55,
                       facecolor=COLOR_GREEN, alpha=0.7,
                       edgecolor=COLOR_GREEN))
ax.text(-1.5, 0.52, "Aggregate over past 30 days (OK)",
        ha="center", fontsize=9, color="white", fontweight="bold")
ax.text(-1.5, 1.0, "observable at t", ha="center",
        fontsize=8, color=COLOR_GREEN)

# 未来 72h の問合せ (NG, red)
ax.add_patch(Rectangle((0.0, -0.85), 1.5, 0.55,
                       facecolor=COLOR_RED, alpha=0.7,
                       edgecolor=COLOR_RED))
ax.text(0.75, -0.58, "Support contacts in t+72h (NG)",
        ha="center", fontsize=9, color="white", fontweight="bold")
ax.text(0.75, -1.18, "does not exist at t (future info)",
        ha="center", fontsize=8, color=COLOR_RED)

for x, label in [(-3.0, "t - 30d"), (0.0, "t"), (1.5, "t + 72h")]:
    ax.text(x, -0.18, label, ha="center", fontsize=8)
    ax.plot([x, x], [-0.05, 0.05], color="black", linewidth=1)

ax.set_xlim(-4.0, 2.6)
ax.set_ylim(-1.5, 2.0)
ax.axis("off")
ax.set_title(
    "As-of timestamp matters: past window is safe, future window leaks the target"
)

plt.tight_layout()
save("data-leakage_timeline.svg")


# --- 図3: train-test contamination の典型デモ ---
# 真の信号が無いデータ (random label) で:
#   Wrong: 全データで SelectKBest を fit してから cross_val_score
#   Correct: Pipeline で SelectKBest を train fold 内に閉じる
# chance level 0.5 を Correct は守る、Wrong は不当に高くなる。
X_noise = rng.standard_normal((200, 5000))
y_noise = rng.integers(0, 2, 200)

sel_global = SelectKBest(f_classif, k=20).fit(X_noise, y_noise)
X_selected_wrong = sel_global.transform(X_noise)
cv_wrong = cross_val_score(
    LogisticRegression(max_iter=2000),
    X_selected_wrong, y_noise, cv=5, scoring="accuracy",
)

pipe = Pipeline([
    ("select", SelectKBest(f_classif, k=20)),
    ("clf", LogisticRegression(max_iter=2000)),
])
cv_correct = cross_val_score(pipe, X_noise, y_noise, cv=5, scoring="accuracy")

fig, ax = plt.subplots(figsize=(6, 4))
labels = ["Wrong\n(SelectKBest before split)", "Correct\n(Pipeline)"]
means = [cv_wrong.mean(), cv_correct.mean()]
errs = [cv_wrong.std(), cv_correct.std()]
ax.bar(labels, means, yerr=errs,
       color=[COLOR_RED, COLOR_BLUE], capsize=8, edgecolor="white")
ax.axhline(0.5, color="gray", linestyle="--", label="chance level (0.5)")
ax.set_ylim(0, 1.05)
ax.set_ylabel("CV accuracy (5-fold)")
ax.set_title(
    "Random labels with 5000 noise features:\nwrong way over-reports accuracy"
)
ax.legend(loc="lower right")
for i, v in enumerate(means):
    ax.text(i, v + 0.02, f"{v:.3f}", ha="center", fontsize=10)

plt.tight_layout()
save("data-leakage_contamination.svg")


print("Saved figures to:", NOTE_DIR)
print(f"CV clean:   {cv_clean.mean():.3f} +/- {cv_clean.std():.3f}")
print(f"CV leak:    {cv_leak.mean():.3f} +/- {cv_leak.std():.3f}")
print(f"Wrong CV (contamination):  {cv_wrong.mean():.3f}")
print(f"Correct CV (pipeline):     {cv_correct.mean():.3f}")
