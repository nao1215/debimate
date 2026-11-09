"""missing-values ノート用の図を生成するスクリプト。

実行: projects/ml で `uv run --frozen python scripts/notes/missing-values_gen.py`
図は projects/ml/notes/ml/missing-values/ に書き出す。
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.experimental import enable_iterative_imputer  # noqa: F401
from sklearn.impute import IterativeImputer, KNNImputer, SimpleImputer

COLOR_BLUE, COLOR_RED, COLOR_GREEN, COLOR_GRAY = "#7aa6c2", "#e15759", "#59a14f", "#999999"

NOTE_DIR = Path(__file__).resolve().parents[2] / "notes" / "ml" / "missing-values"
NOTE_DIR.mkdir(parents=True, exist_ok=True)


def save(name):
    plt.savefig(NOTE_DIR / name, bbox_inches="tight")
    plt.close()


# ============================================================
# 本文の実験 1 と同じデータ（年齢と年収、3 種類の欠け方）
# ============================================================
rng = np.random.default_rng(0)
n = 5000
age = rng.uniform(20, 70, n)
income = 100 + 8 * age + rng.normal(0, 80, n)
masks = {
    "MCAR": rng.random(n) < 0.3,
    "MAR": rng.random(n) < np.where(age < 35, 0.6, 0.15),
    "MNAR": rng.random(n) < np.where(income > 500, 0.6, 0.15),
}

# ------------------------------------------------------------
# Fig 1: MCAR / MAR / MNAR の散布図（先頭 300 点だけ描く）
# ------------------------------------------------------------
subtitles = {
    "MCAR": "missing at random positions",
    "MAR": "missing depends on age (age < 35)",
    "MNAR": "missing depends on income itself (> 500)",
}
k = 300
fig, axes = plt.subplots(1, 3, figsize=(15, 4.5), sharey=True)
for ax, (name, miss) in zip(axes, masks.items()):
    m = miss[:k]
    ax.scatter(age[:k][~m], income[:k][~m], color=COLOR_BLUE, alpha=0.6, s=20,
               label="observed")
    ax.scatter(age[:k][m], income[:k][m], color=COLOR_RED, alpha=0.6, s=40,
               marker="x", label="missing (hidden)")
    ax.set_title(f"{name}\n{subtitles[name]}")
    ax.set_xlabel("age")
    ax.grid(True, alpha=0.25)
axes[0].set_ylabel("income")
axes[0].legend(fontsize=8, loc="upper left")
plt.tight_layout()
save("missing_mcar_mar_mnar.svg")

# ------------------------------------------------------------
# Fig 2: 3 種類の欠け方での平均年収の推定
# ------------------------------------------------------------
true_mean = income.mean()
observed_means, imputed_means = [], []
for miss in masks.values():
    obs = np.where(miss, np.nan, income)
    filled = IterativeImputer(random_state=0).fit_transform(np.c_[age, obs])[:, 1]
    observed_means.append(np.nanmean(obs))
    imputed_means.append(filled.mean())

fig, ax = plt.subplots(figsize=(7, 4))
xs = np.arange(len(masks))
ax.bar(xs - 0.2, observed_means, width=0.4, color=COLOR_GRAY,
       label="observed only (= mean imputation)")
ax.bar(xs + 0.2, imputed_means, width=0.4, color=COLOR_BLUE,
       label="IterativeImputer (from age)")
ax.axhline(true_mean, color=COLOR_RED, linestyle="--", label=f"true mean {true_mean:.1f}")
for x0, v in zip(xs - 0.2, observed_means):
    ax.text(x0, v + 2, f"{v:.1f}", ha="center", fontsize=9)
for x0, v in zip(xs + 0.2, imputed_means):
    ax.text(x0, v + 2, f"{v:.1f}", ha="center", fontsize=9)
ax.set_xticks(xs)
ax.set_xticklabels(list(masks))
ax.set_ylim(380, 545)
ax.set_ylabel("estimated mean income")
ax.legend(fontsize=8, loc="upper right")
ax.grid(True, alpha=0.25, axis="y")
plt.tight_layout()
save("missing_mean_bias.svg")

# ------------------------------------------------------------
# Fig 3: 補完手法の比較（本文の実験 2 と同じデータ）
# ------------------------------------------------------------
rng2 = np.random.default_rng(0)
n2 = 300
x = rng2.uniform(0, 10, n2)
y_true = 2 * x + rng2.normal(0, 1, n2)
missing = (x > 7) & (rng2.random(n2) < 0.6)
X = np.c_[x, np.where(missing, np.nan, y_true)]

imputers = {
    "mean": SimpleImputer(strategy="mean"),
    "KNN (k=5)": KNNImputer(n_neighbors=5),
    "Iterative (BayesianRidge)": IterativeImputer(random_state=0),
    "Iterative (RandomForest)": IterativeImputer(
        estimator=RandomForestRegressor(n_estimators=30, random_state=0),
        random_state=0),
}

fig, axes = plt.subplots(1, 4, figsize=(16, 4), sharey=True)
for ax, (name, imp) in zip(axes, imputers.items()):
    y_imp = imp.fit_transform(X)[:, 1]
    mae = np.abs(y_imp[missing] - y_true[missing]).mean()
    ax.scatter(x[~missing], y_true[~missing], color=COLOR_BLUE, alpha=0.5, s=15,
               label="observed")
    ax.scatter(x[missing], y_true[missing], color=COLOR_GREEN, alpha=0.6, s=25,
               label="true (hidden)")
    ax.scatter(x[missing], y_imp[missing], color=COLOR_RED, marker="x", s=45,
               label="imputed")
    ax.set_title(f"{name}\nMAE = {mae:.2f}")
    ax.set_xlabel("x")
    ax.grid(True, alpha=0.25)
axes[0].set_ylabel("y")
axes[0].legend(fontsize=7, loc="upper left")
plt.tight_layout()
save("missing_imputation_compare.svg")

print("done:", sorted(p.name for p in NOTE_DIR.iterdir()))
