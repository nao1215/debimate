"""missing-values ノート用の図を生成するスクリプト。"""
import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import pandas as pd

COLOR_BLUE, COLOR_RED, COLOR_GREEN, COLOR_ORANGE, COLOR_GRAY = \
    "#7aa6c2", "#e15759", "#59a14f", "#f28e2b", "#999999"

NOTE_DIR = os.path.expanduser(
    "~/ghq/github.com/nao1215/debimate/projects/ml/notes/ml/missing-values"
)
os.makedirs(NOTE_DIR, exist_ok=True)


def save(name):
    plt.savefig(os.path.join(NOTE_DIR, name), bbox_inches="tight")
    plt.close()


# ============================================================
# Fig 1: MCAR / MAR / MNAR の概念図 (簡略可視化)
# ============================================================
rng = np.random.default_rng(0)
n = 100
age = rng.uniform(20, 70, n)
income = age * 1000 + rng.normal(0, 5000, n) + 10000

fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))

# MCAR: random
mcar = rng.random(n) < 0.3
ax = axes[0]
ax.scatter(age[~mcar], income[~mcar], color=COLOR_BLUE, alpha=0.6, s=30, label="observed")
ax.scatter(age[mcar], income[mcar], color=COLOR_RED, alpha=0.4, s=80, marker="x",
           label="missing")
ax.set_title("MCAR (Missing Completely At Random)\nmissingness is purely random\n-> any imputation works")
ax.set_xlabel("age"); ax.set_ylabel("income")
ax.legend(fontsize=8)
ax.grid(True, alpha=0.25)

# MAR: missing depends on observed variable (age < 30 -> more likely missing income)
mar_prob = np.where(age < 30, 0.6, 0.1)
mar = rng.random(n) < mar_prob
ax = axes[1]
ax.scatter(age[~mar], income[~mar], color=COLOR_BLUE, alpha=0.6, s=30, label="observed")
ax.scatter(age[mar], income[mar], color=COLOR_RED, alpha=0.4, s=80, marker="x",
           label="missing")
ax.set_title("MAR (Missing At Random)\nmissingness depends on observed vars\n-> imputable from other features")
ax.set_xlabel("age"); ax.set_ylabel("income")
ax.legend(fontsize=8)
ax.grid(True, alpha=0.25)

# MNAR: missing depends on the value itself
mnar_prob = (income - income.min()) / (income.max() - income.min())  # 高所得者ほど missing
mnar = rng.random(n) < mnar_prob * 0.6
ax = axes[2]
ax.scatter(age[~mnar], income[~mnar], color=COLOR_BLUE, alpha=0.6, s=30, label="observed")
ax.scatter(age[mnar], income[mnar], color=COLOR_RED, alpha=0.4, s=80, marker="x",
           label="missing")
ax.set_title("MNAR (Missing Not At Random)\nmissingness depends on the value itself\n-> imputation stays biased")
ax.set_xlabel("age"); ax.set_ylabel("income")
ax.legend(fontsize=8)
ax.grid(True, alpha=0.25)

plt.tight_layout()
save("missing_mcar_mar_mnar.svg")


# ============================================================
# Fig 2: Imputation methods compared
# ============================================================
from sklearn.experimental import enable_iterative_imputer  # noqa
from sklearn.impute import SimpleImputer, KNNImputer, IterativeImputer
from sklearn.ensemble import RandomForestRegressor

# Create dataset with MAR pattern
rng2 = np.random.default_rng(0)
n2 = 300
x = rng2.uniform(0, 10, n2)
y_true = 2 * x + rng2.normal(0, 1, n2)
# Inject MAR missingness in y based on x: when x > 7, drop 60% of y
missing_mask = (x > 7) & (rng2.random(n2) < 0.6)
y_obs = y_true.copy()
y_obs[missing_mask] = np.nan

df = pd.DataFrame({"x": x, "y": y_obs})

imputers = {
    "mean": SimpleImputer(strategy="mean"),
    "median": SimpleImputer(strategy="median"),
    "KNN (k=5)": KNNImputer(n_neighbors=5),
    "Iterative (RF)": IterativeImputer(estimator=RandomForestRegressor(n_estimators=30),
                                        random_state=0),
}

fig, axes = plt.subplots(1, 4, figsize=(16, 4))
for ax, (name, imp) in zip(axes, imputers.items()):
    imputed = imp.fit_transform(df)
    y_imp = imputed[:, 1]
    ax.scatter(x[~missing_mask], y_true[~missing_mask], color=COLOR_BLUE, alpha=0.5,
               s=20, label="observed")
    ax.scatter(x[missing_mask], y_true[missing_mask], color=COLOR_GREEN, alpha=0.6,
               s=30, label="true (hidden)")
    ax.scatter(x[missing_mask], y_imp[missing_mask], color=COLOR_RED, marker="x",
               s=60, label="imputed")
    ax.set_title(f"{name}\nMAE = {np.mean(np.abs(y_imp[missing_mask] - y_true[missing_mask])):.2f}")
    ax.set_xlabel("x"); ax.set_ylabel("y")
    ax.legend(fontsize=7, loc="upper left")
    ax.grid(True, alpha=0.25)
plt.suptitle("Imputation methods: simple averages collapse the structure, KNN/Iterative preserve it",
             y=1.02)
plt.tight_layout()
save("missing_imputation_compare.svg")


# ============================================================
# Fig 3: Missing indicator + imputation - the safer pattern
# ============================================================
fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))

# Left: imputation only
ax = axes[0]
ax.bar(["A", "B", "C", "D", "E"], [3.5, 4.0, 3.5, 2.0, 3.5], color=COLOR_BLUE,
       edgecolor="white")
ax.set_title("Imputation only\ndownstream model can't tell it was missing")
ax.set_ylabel("value")
ax.set_ylim(0, 5)
ax.grid(True, alpha=0.25, axis="y")

# Right: imputation + missing indicator
ax = axes[1]
xs = np.arange(5)
ax.bar(xs - 0.2, [3.5, 4.0, 3.5, 2.0, 3.5], width=0.4, color=COLOR_BLUE,
       edgecolor="white", label="imputed value")
ax.bar(xs + 0.2, [0, 0, 1, 0, 1], width=0.4, color=COLOR_RED, edgecolor="white",
       label="was_missing (0/1)")
ax.set_xticks(xs); ax.set_xticklabels(["A", "B", "C", "D", "E"])
ax.set_title("Imputation + missing indicator\nmodel learns 'was-missing' as a feature")
ax.set_ylabel("value")
ax.set_ylim(0, 5)
ax.legend(fontsize=9)
ax.grid(True, alpha=0.25, axis="y")

plt.tight_layout()
save("missing_indicator_pattern.svg")


print("done:", sorted(os.listdir(NOTE_DIR)))
