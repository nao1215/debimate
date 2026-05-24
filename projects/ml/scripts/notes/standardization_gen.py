"""standardization ノート用の図を生成するスクリプト。

実行: cd projects/ml && uv run python scripts/notes/standardization_gen.py
"""
import os

import matplotlib.pyplot as plt
import numpy as np
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import StandardScaler

COLOR_BLUE = "#7aa6c2"
COLOR_RED = "#e15759"
COLOR_GREEN = "#59a14f"

NOTE_DIR = os.path.expanduser(
    "~/ghq/github.com/nao1215/debimate/projects/ml/notes/ml/standardization"
)
os.makedirs(NOTE_DIR, exist_ok=True)


def save(name: str) -> None:
    plt.savefig(os.path.join(NOTE_DIR, name), bbox_inches="tight")
    plt.close()


rng = np.random.default_rng(0)


# --- 図1: スケール前後のヒストグラム ---
# 金額（~数十万円）と年齢（~100）を模した 2 つの特徴量。
amount = rng.normal(50_000, 30_000, size=500).clip(0, None)
age = rng.normal(40, 12, size=500).clip(0, None)

X_raw = np.column_stack([amount, age])
X_std = StandardScaler().fit_transform(X_raw)

fig, axes = plt.subplots(2, 2, figsize=(8, 5.5))
axes[0, 0].hist(amount, bins=30, color=COLOR_BLUE, edgecolor="white")
axes[0, 0].set_title("Raw: amount (yen)")
axes[0, 0].set_xlabel("Value")
axes[0, 1].hist(age, bins=30, color=COLOR_GREEN, edgecolor="white")
axes[0, 1].set_title("Raw: age")
axes[0, 1].set_xlabel("Value")
axes[1, 0].hist(X_std[:, 0], bins=30, color=COLOR_BLUE, edgecolor="white")
axes[1, 0].set_title("Standardized: amount")
axes[1, 0].set_xlabel("Z-score")
axes[1, 1].hist(X_std[:, 1], bins=30, color=COLOR_GREEN, edgecolor="white")
axes[1, 1].set_title("Standardized: age")
axes[1, 1].set_xlabel("Z-score")
for ax in axes.ravel():
    ax.set_ylabel("Count")
plt.tight_layout()
save("standardization_hist.svg")


# --- 図2: kNN の決定境界がスケールで変わる ---
# 2 つの特徴量を、片方は ~10 倍のスケールにして混ぜる。
n = 300
class0 = rng.normal(loc=[0, 0], scale=[1, 1], size=(n // 2, 2))
class1 = rng.normal(loc=[2.5, 2.5], scale=[1, 1], size=(n // 2, 2))
X = np.vstack([class0, class1])
y = np.array([0] * (n // 2) + [1] * (n // 2))

# 片方の特徴量のスケールを 50 倍に
X_scaled_input = X.copy()
X_scaled_input[:, 0] *= 50.0


def draw_boundary(ax, X_data, y_data, model, title):
    model.fit(X_data, y_data)
    pad_x = (X_data[:, 0].max() - X_data[:, 0].min()) * 0.1
    pad_y = (X_data[:, 1].max() - X_data[:, 1].min()) * 0.1
    xx, yy = np.meshgrid(
        np.linspace(X_data[:, 0].min() - pad_x, X_data[:, 0].max() + pad_x, 300),
        np.linspace(X_data[:, 1].min() - pad_y, X_data[:, 1].max() + pad_y, 300),
    )
    Z = model.predict(np.c_[xx.ravel(), yy.ravel()]).reshape(xx.shape)
    ax.contourf(xx, yy, Z, alpha=0.3, cmap="coolwarm", levels=[-0.5, 0.5, 1.5])
    ax.scatter(X_data[:, 0], X_data[:, 1], c=y_data, cmap="coolwarm",
               edgecolor="white", s=30)
    ax.set_title(title)


fig, axes = plt.subplots(1, 3, figsize=(11, 3.5))
draw_boundary(axes[0], X, y, KNeighborsClassifier(n_neighbors=15),
              "kNN: balanced scale")
draw_boundary(axes[1], X_scaled_input, y, KNeighborsClassifier(n_neighbors=15),
              "kNN: feature 1 scaled x50 (no standardize)")
X_fixed = StandardScaler().fit_transform(X_scaled_input)
draw_boundary(axes[2], X_fixed, y, KNeighborsClassifier(n_neighbors=15),
              "kNN: after StandardScaler")
for ax in axes:
    ax.set_xlabel("x1")
    ax.set_ylabel("x2")
plt.tight_layout()
save("standardization_knn_boundary.png")


# --- 図3: LogisticRegression の係数がスケールで変わる ---
# 同じデータに対し、片方のスケールだけ変えて L2 正則化付き LR を当てる。
labels = ["balanced scale", "feature 1 x50 (raw)", "feature 1 x50 (standardized)"]
coefs = []
for X_data in [X, X_scaled_input, StandardScaler().fit_transform(X_scaled_input)]:
    lr = LogisticRegression(C=1.0, max_iter=1000).fit(X_data, y)
    coefs.append(lr.coef_[0])

coefs = np.array(coefs)
xpos = np.arange(len(labels))
width = 0.35
fig, ax = plt.subplots(figsize=(7, 4))
ax.bar(xpos - width / 2, coefs[:, 0], width, label="w1 (feature 1)",
       color=COLOR_BLUE)
ax.bar(xpos + width / 2, coefs[:, 1], width, label="w2 (feature 2)",
       color=COLOR_RED)
ax.axhline(0, color="gray", linewidth=0.6)
ax.set_xticks(xpos)
ax.set_xticklabels(labels, rotation=10)
ax.set_ylabel("Coefficient value")
ax.set_title("L2-regularized LogisticRegression coefficients")
ax.legend()
plt.tight_layout()
save("standardization_lr_coef.svg")


# --- 図4: RandomForest はスケール不変 ---
fig, axes = plt.subplots(1, 2, figsize=(8, 3.5))
draw_boundary(axes[0], X_scaled_input, y,
              RandomForestClassifier(n_estimators=50, random_state=0),
              "RandomForest: feature 1 x50 (raw)")
draw_boundary(axes[1], StandardScaler().fit_transform(X_scaled_input), y,
              RandomForestClassifier(n_estimators=50, random_state=0),
              "RandomForest: after StandardScaler")
for ax in axes:
    ax.set_xlabel("x1")
    ax.set_ylabel("x2")
plt.tight_layout()
save("standardization_rf_boundary.png")


# --- 数値で確かめる: kNN の精度がスケールで激変 ---
from sklearn.model_selection import cross_val_score

results = []
for name, X_data in [
    ("kNN balanced", (X, y)),
    ("kNN raw x50", (X_scaled_input, y)),
    ("kNN standardized", (StandardScaler().fit_transform(X_scaled_input), y)),
    ("RandomForest balanced", (X, y)),
    ("RandomForest raw x50", (X_scaled_input, y)),
    ("RandomForest standardized",
     (StandardScaler().fit_transform(X_scaled_input), y)),
]:
    Xd, yd = X_data
    if "kNN" in name:
        model = KNeighborsClassifier(n_neighbors=15)
    else:
        model = RandomForestClassifier(n_estimators=50, random_state=0)
    score = cross_val_score(model, Xd, yd, cv=5, scoring="accuracy").mean()
    results.append((name, score))


print("Accuracy by model and scaling:")
for name, score in results:
    print(f"  {name:<32s}  acc={score:.3f}")
