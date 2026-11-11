"""cross-validation ノートの実験と図を生成するスクリプト。

本文に載せた 4 つの実験（1 回の分割と 5 分割のばらつき、iris の cv=3 と KFold(3)、
California Housing の分け方、Ridge の alpha と nested CV）を同じ順に実行し、
出力を標準出力に、図を Page Bundle に WebP で保存する。
California Housing は初回だけ scikit-learn の配布元から取得し、~/scikit_learn_data に置かれる。
実行: cd projects/ml && .venv/bin/python scripts/notes/cross-validation_gen.py
確認した版: scikit-learn 1.9.1、matplotlib 3.11.2
"""
from io import BytesIO
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch
from PIL import Image
from sklearn.datasets import fetch_california_housing, load_iris, make_regression
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.model_selection import (GridSearchCV, GroupKFold, KFold, StratifiedKFold,
                                     cross_val_score, train_test_split)
from sklearn.neighbors import NearestNeighbors

NOTE_DIR = Path(__file__).resolve().parents[2] / "notes" / "ml" / "cross-validation"
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10,
                     "axes.spines.top": False, "axes.spines.right": False})
BLUE, RED, GREEN, INK, GRAY = "#7aa6c2", "#e15759", "#59a14f", "#333333", "#999999"
CLASS_COLORS = [BLUE, RED, GREEN]
FOLD_COLORS = ["#7aa6c2", "#e15759", "#59a14f", "#f2b447", "#9c7fb8"]


def save(fig, name):
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight", facecolor="#ffffff")
    plt.close(fig)
    buf.seek(0)
    Image.open(buf).convert("RGB").save(NOTE_DIR / name, "WEBP", quality=90, method=6)


def lighten(hex_color, amount=0.75):
    rgb = np.array([int(hex_color[i:i + 2], 16) for i in (1, 3, 5)]) / 255
    return tuple(rgb + (1 - rgb) * amount)


# ---- 実験 1: 1 回の分割と 5 分割の平均は、分け方の運でどれだけ動くか ----
X, y = make_regression(n_samples=60, n_features=50, n_informative=10, noise=20, random_state=0)

holdout, cv_mean = [], []
for seed in range(200):
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=seed)
    holdout.append(Ridge(alpha=1.0).fit(X_tr, y_tr).score(X_te, y_te))
    cv = KFold(n_splits=5, shuffle=True, random_state=seed)
    cv_mean.append(cross_val_score(Ridge(alpha=1.0), X, y, cv=cv).mean())
holdout, cv_mean = np.array(holdout), np.array(cv_mean)
print(f"1 回の分割: 最小 {holdout.min():.3f}、最大 {holdout.max():.3f}、標準偏差 {holdout.std():.3f}")
print(f"5 分割の平均: 最小 {cv_mean.min():.3f}、最大 {cv_mean.max():.3f}、標準偏差 {cv_mean.std():.3f}")

# 5 分割の模式図（20 件を 5 つに分け、1 つずつ検証に回す）
fig, ax = plt.subplots(figsize=(7.2, 2.6))
for k in range(5):
    for i in range(20):
        is_val = 4 * k <= i < 4 * (k + 1)
        ax.add_patch(plt.Rectangle((i, 4 - k), 0.92, 0.8, color=RED if is_val else lighten(BLUE, 0.35)))
    ax.text(-0.6, 4 - k + 0.4, f"{k + 1} 回目", ha="right", va="center")
ax.set_xlim(-3, 20.5)
ax.set_ylim(-0.4, 5.2)
ax.axis("off")
ax.legend(handles=[Patch(color=lighten(BLUE, 0.35), label="学習に使う"), Patch(color=RED, label="検証に使う")],
          loc="upper center", bbox_to_anchor=(0.55, 1.12), ncol=2, frameon=False)
ax.text(10, -0.35, "データの番号 0〜19（4 件ずつ 5 つに分ける）", ha="center", va="center", color=INK)
save(fig, "cv_split.webp")

fig, ax = plt.subplots(figsize=(7, 3.2))
bins = np.linspace(0.25, 1.0, 31)
ax.hist(holdout, bins=bins, color=lighten(GRAY, 0.3), label="1 回の分割（学習 48 件・検証 12 件）")
ax.hist(cv_mean, bins=bins, color=BLUE, alpha=0.85, label="5 分割の平均")
ax.set_xlabel("検証の R²（Ridge、alpha=1.0、分け方の乱数を 200 通り）")
ax.set_ylabel("回数")
ax.legend(frameon=False, loc="upper left")
save(fig, "cv_holdout_spread.webp")

# ---- 実験 2: iris で cv=3 と KFold(3) を比べる ----
iris = load_iris()
Xi, yi = iris.data, iris.target
print("iris の y の並び:", yi[:3], "…", yi[48:53], "…", yi[-3:])
clf = LogisticRegression(max_iter=1000)
cases = [("KFold(3)", KFold(n_splits=3)),
         ("KFold(3, shuffle=True)", KFold(n_splits=3, shuffle=True, random_state=0)),
         ("cv=3", 3)]
iris_scores = {}
for label, cv in cases:
    scores = cross_val_score(clf, Xi, yi, cv=cv)
    iris_scores[label] = scores
    print(f"{label}: 各回 {scores.round(2)}、平均 {scores.mean():.3f}")

# cv=3 は分類器なので、cross_val_score の中で StratifiedKFold(3) に置き換わる
splitters = [("KFold(3)", KFold(n_splits=3)),
             ("KFold(3, shuffle=True)", KFold(n_splits=3, shuffle=True, random_state=0)),
             ("cv=3（中身は StratifiedKFold(3)）", StratifiedKFold(n_splits=3))]
fig, axes = plt.subplots(3, 1, figsize=(9, 5.2), sharex=True)
for ax, (label, sp), key in zip(axes, splitters, iris_scores):
    for r, (_, te) in enumerate(sp.split(Xi, yi)):
        test = np.zeros(len(yi), bool)
        test[te] = True
        colors = [CLASS_COLORS[c] if t else lighten(CLASS_COLORS[c], 0.78) for c, t in zip(yi, test)]
        rgb = np.array([matplotlib.colors.to_rgb(c) for c in colors])[None, :, :]
        ax.imshow(rgb, extent=(0, len(yi), 2 - r, 2 - r + 0.8), aspect="auto", interpolation="nearest")
        ax.text(-2, 2 - r + 0.4, f"{r + 1} 回目", ha="right", va="center", fontsize=9)
    ax.set_title(f"{label}　正解率の平均 {iris_scores[key].mean():.2f}", loc="left", fontsize=11)
    ax.set_xlim(-0.5, len(yi) + 0.5)
    ax.set_ylim(-0.1, 2.9)
    ax.set_yticks([])
    ax.spines["left"].set_visible(False)
axes[-1].set_xlabel("iris の行の番号（0〜149。濃いマスが検証、薄いマスが学習）")
axes[0].legend(handles=[Patch(color=c, label=n) for c, n in zip(CLASS_COLORS, iris.target_names)],
               loc="lower right", bbox_to_anchor=(1.0, 1.02), ncol=3, frameon=False, fontsize=9)
fig.tight_layout()
save(fig, "cv_cover.webp")

# ---- 実験 3: California Housing を 3 通りに分ける ----
housing = fetch_california_housing()
Xh, yh = housing.data, housing.target
lat, lon = Xh[:, 6], Xh[:, 7]
# 緯度と経度を 0.5 度ごとのマス目に切り、同じマスの区画を 1 つのグループにする
groups = np.floor(lat / 0.5).astype(int) * 1000 + np.floor(lon / 0.5).astype(int)
print("行の数:", len(yh), "グループの数:", len(np.unique(groups)))
reg = HistGradientBoostingRegressor(random_state=0)
house_cases = [("cv=5（KFold、shuffle なし）", KFold(n_splits=5), None),
               ("KFold(5, shuffle=True)", KFold(n_splits=5, shuffle=True, random_state=0), None),
               ("GroupKFold(5)、0.5 度のマス目", GroupKFold(n_splits=5), groups)]
nn_coords = np.column_stack((lat, lon))
house_results = []
for label, cv, g in house_cases:
    scores = cross_val_score(reg, Xh, yh, cv=cv, groups=g)
    # 検証の各区画から、学習側で一番近い区画までの距離（度）
    dists = []
    folds = list(cv.split(Xh, yh, g))
    for tr, te in folds:
        nn = NearestNeighbors(n_neighbors=1).fit(nn_coords[tr])
        dists.append(nn.kneighbors(nn_coords[te])[0].ravel())
    d = np.concatenate(dists)
    same, far = (d == 0).mean(), (d >= 0.3).mean()  # 同じ地点が学習側にある割合、0.3 度以上離れた割合
    house_results.append((label, folds, scores, same, far))
    print(f"{label}: R² の平均 {scores.mean():.3f}、同じ地点が学習側にある {same:.1%}、最寄りが 0.3 度以上先 {far:.1%}")

fig, axes = plt.subplots(1, 3, figsize=(10.5, 4.4), sharey=True)
for ax, (label, folds, scores, same, far) in zip(axes, house_results):
    fold_of = np.empty(len(yh), int)
    for k, (_, te) in enumerate(folds):
        fold_of[te] = k
    # 描く順で色が偏らないように混ぜる。KFold の shuffle と同じ種だと同じ並びになるので別の種にする
    order = np.random.RandomState(12345).permutation(len(yh))
    ax.scatter(lon[order], lat[order], c=[FOLD_COLORS[k] for k in fold_of[order]], s=1.2, linewidths=0)
    ax.set_title(f"{label}\nR² の平均 {scores.mean():.2f}、同じ地点が学習側に {same:.0%}", fontsize=10)
    ax.set_xlabel("経度")
    ax.set_aspect("equal")
axes[0].set_ylabel("緯度")
fig.legend(handles=[Patch(color=c, label=f"{k + 1} 回目の検証") for k, c in enumerate(FOLD_COLORS)],
           loc="lower center", bbox_to_anchor=(0.5, -0.06), ncol=5, frameon=False, fontsize=9)
fig.tight_layout()
save(fig, "cv_california.webp")

# 検証の行の近くに学習側の区画が残る割合を、分け方ごとに並べる
fig, ax = plt.subplots(figsize=(7.4, 3.0))
ypos = np.arange(len(house_results))[::-1]
sames = [r[3] * 100 for r in house_results]
fars = [r[4] * 100 for r in house_results]
ax.barh(ypos + 0.18, sames, height=0.34, color=RED, label="同じ地点が学習側にある")
ax.barh(ypos - 0.18, fars, height=0.34, color=BLUE, label="最寄りが 0.3 度以上先")
for yv, a, b, (label, _, scores, _, _) in zip(ypos, sames, fars, house_results):
    ax.text(a + 0.8, yv + 0.18, f"{a:.1f}%", va="center", fontsize=9)
    ax.text(b + 0.8, yv - 0.18, f"{b:.1f}%", va="center", fontsize=9)
    ax.text(72, yv, f"R² {scores.mean():.3f}", va="center", fontsize=10, color=INK)
ax.set_yticks(ypos)
ax.set_yticklabels([r[0] for r in house_results])
ax.set_xlim(0, 82)
ax.set_xlabel("検証の行のうちの割合（%）")
ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.45, -0.25), ncol=2)
save(fig, "cv_california_nearby.webp")

# ---- 実験 4: Ridge の alpha を 5 分割で選び、選んだ後のスコアを nested CV で測り直す ----
alphas = np.logspace(-2, 3, 20)
cv = KFold(n_splits=5, shuffle=True, random_state=0)
for alpha in (0.01, 1.0):
    scores = cross_val_score(Ridge(alpha=alpha), X, y, cv=cv)
    print(f"alpha={alpha}: 各回 {scores.round(3)}、平均 {scores.mean():.3f}、標準偏差 {scores.std():.3f}")
grid = GridSearchCV(Ridge(), param_grid={"alpha": alphas}, cv=cv).fit(X, y)
print(f"選んだ alpha: {grid.best_params_['alpha']:.3f}、その時の 5 分割の R²: {grid.best_score_:.3f}")
outer = KFold(n_splits=5, shuffle=True, random_state=1)
nested = cross_val_score(GridSearchCV(Ridge(), param_grid={"alpha": alphas}, cv=cv), X, y, cv=outer)
print(f"nested CV の R²: 各回 {nested.round(3)}、平均 {nested.mean():.3f}")

curves = {60: grid}
X300, y300 = make_regression(n_samples=300, n_features=50, n_informative=10, noise=20, random_state=0)
curves[300] = GridSearchCV(Ridge(), param_grid={"alpha": alphas}, cv=cv).fit(X300, y300)
fig, ax = plt.subplots(figsize=(6.4, 3.8))
for n, color, marker in ((60, BLUE, "o"), (300, GRAY, "s")):
    g = curves[n]
    ax.errorbar(alphas, g.cv_results_["mean_test_score"], yerr=g.cv_results_["std_test_score"],
                color=color, marker=marker, markersize=4, capsize=2, label=f"{n} 件・特徴量 50 個")
best = grid.best_params_["alpha"]
ax.axvline(best, color=BLUE, linestyle="--", linewidth=1, label=f"60 件で選んだ alpha = {best:.2f}")
ax.set_xscale("log")
ax.set_xlabel("Ridge の alpha（正則化の強さ）")
ax.set_ylabel("5 分割の R²（平均 ± 標準偏差）")
ax.set_ylim(-0.45, 1.05)
ax.grid(alpha=0.25)
ax.legend(frameon=False, fontsize=9, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=3)
save(fig, "cv_alpha.webp")
