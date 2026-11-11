"""regularization ノートの実験と図を生成するスクリプト。

本文に載せた実験（多項式と alpha、diabetes の係数の道筋、Lasso の選ぶ列の入れ替わり、
alpha の効き目と列の大きさ・行の数、alpha の選び方）を同じ順に実行し、
出力を標準出力に、図を Page Bundle に WebP で保存する。
実行: cd projects/ml && .venv/bin/python scripts/notes/regularization_gen.py
確認した版: scikit-learn 1.9.1、NumPy 2.5.4、matplotlib 3.11.2
"""
import warnings
from io import BytesIO
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from sklearn.datasets import load_diabetes
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import ElasticNet, Lasso, LinearRegression, Ridge
from sklearn.model_selection import GridSearchCV, KFold, PredefinedSplit, cross_val_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import PolynomialFeatures, StandardScaler

warnings.simplefilter("ignore", ConvergenceWarning)
NOTE_DIR = Path(__file__).resolve().parents[2] / "notes" / "ml" / "regularization"
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10,
                     "axes.spines.top": False, "axes.spines.right": False})
BLUE, RED, GREEN, INK, GRAY, LIGHT = "#7aa6c2", "#e15759", "#59a14f", "#333333", "#999999", "#eeeeee"


def save(fig, name):
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight", facecolor="#ffffff")
    plt.close(fig)
    buf.seek(0)
    Image.open(buf).convert("RGB").save(NOTE_DIR / name, "WEBP", quality=90, method=6)


# ---- 実験 1: 次数 15 の多項式に L2 を掛け、alpha を変える ----
rng = np.random.default_rng(3)
truth = lambda v: np.sin(v) + 0.3 * v  # noqa: E731  データを作った真の関数
x = np.sort(rng.uniform(-3, 3, 30))
y = truth(x) + rng.normal(0, 0.3, x.size)
x_new = rng.uniform(-3, 3, 1000)  # 学習に使わない新しい点
y_new = truth(x_new) + rng.normal(0, 0.3, x_new.size)

models = {}
for alpha in [0, 0.1, 100]:
    reg = LinearRegression() if alpha == 0 else Ridge(alpha=alpha)
    model = make_pipeline(PolynomialFeatures(15, include_bias=False), StandardScaler(), reg)
    model.fit(x[:, None], y)
    models[alpha] = model
    mse_train = np.mean((model.predict(x[:, None]) - y) ** 2)
    mse_new = np.mean((model.predict(x_new[:, None]) - y_new) ** 2)
    w = model[-1].coef_
    print(f"alpha={alpha:>5}: 学習の誤差 {mse_train:.3f}、新しい点の誤差 {mse_new:.3f}、"
          f"係数の絶対値の最大 {np.abs(w).max():.1f}")

grid = np.linspace(-3.2, 3.2, 400)
fig, axes = plt.subplots(1, 3, figsize=(10, 3.2), sharey=True)
titles = {0: "alpha=0（正則化なし）", 0.1: "alpha=0.1", 100: "alpha=100（強すぎる）"}
for ax, (alpha, model) in zip(axes, models.items()):
    ax.plot(grid, truth(grid), "--", color=GREEN, label="真の関数")
    ax.plot(grid, model.predict(grid[:, None]), color=RED, lw=2, label="モデル")
    ax.scatter(x, y, s=22, color=BLUE, edgecolor="white", label="学習の点", zorder=3)
    ax.set_title(titles[alpha], fontsize=10)
    ax.set_xlabel("x")
    ax.set_ylim(-2.6, 2.6)
    ax.grid(alpha=0.3)
axes[0].set_ylabel("y")
axes[0].legend(fontsize=8, loc="lower right")
fig.tight_layout()
save(fig, "regularization_curves.webp")

# ---- 実験 2: diabetes を標準化し、alpha ごとの係数の道筋を Lasso と Ridge で比べる ----
d = load_diabetes()
X, y = d.data, d.target
names = d.feature_names
Xs = StandardScaler().fit_transform(X)
i1, i2 = names.index("s1"), names.index("s2")
print("s1 と s2 の相関:", np.corrcoef(Xs[:, i1], Xs[:, i2])[0, 1].round(2))
print("正則化なしの係数:", dict(zip(names, LinearRegression().fit(Xs, y).coef_.round(1))))

settings = [("L1（Lasso）", Lasso, np.logspace(-2, 1.5, 80)), ("L2（Ridge）", Ridge, np.logspace(-1, 4, 80))]
fig, axes = plt.subplots(1, 2, figsize=(9.5, 3.6))
for ax, (title, cls, alphas) in zip(axes, settings):
    paths = np.array([cls(alpha=a).fit(Xs, y).coef_ for a in alphas])
    for j, name in enumerate(names):
        if j in (i1, i2):
            continue
        ax.semilogx(alphas, paths[:, j], color=GRAY, lw=1, alpha=0.7)
    ax.semilogx(alphas, paths[:, i1], color=RED, lw=2.2, label="s1（総コレステロール）")
    ax.semilogx(alphas, paths[:, i2], color=RED, lw=2.2, ls="--", label="s2（LDL）")
    ax.axhline(0, color=INK, lw=0.6)
    ax.set_title(title, fontsize=10)
    ax.set_xlabel("alpha（対数の軸）")
    ax.grid(alpha=0.3)
    nz = (paths != 0).sum(axis=1)
    print(title, "0 でない係数の数:", {f"{a:.3g}": int(n) for a, n in zip(alphas[::16], nz[::16])})
axes[0].set_ylabel("係数（標準化した列の 1 標準偏差あたり）")
axes[0].legend(fontsize=8, loc="lower right")
fig.tight_layout()
save(fig, "regularization_paths.webp")

# ---- 実験 3: 行を復元抽出し直すたびに、Lasso が残す列は変わるか ----
cv = KFold(n_splits=5, shuffle=True, random_state=0)
# 標準化を pipeline の中に入れ、交差検証の分割ごとに学習用の行だけで平均と標準偏差を求める
models = {"Lasso": make_pipeline(StandardScaler(), Lasso()),
          "Elastic Net": make_pipeline(StandardScaler(), ElasticNet(l1_ratio=0.5)),
          "Ridge": make_pipeline(StandardScaler(), Ridge())}
grids = {"Lasso": {"lasso__alpha": np.logspace(-2, 1, 31)},
         "Elastic Net": {"elasticnet__alpha": np.logspace(-3, 0, 31)},
         "Ridge": {"ridge__alpha": np.logspace(-3, 4, 71)}}
for label, pipe in models.items():
    search = GridSearchCV(pipe, grids[label], cv=cv).fit(X, y)
    pipe.set_params(**search.best_params_)
    print(f"{label}: 交差検証で選んだ alpha {list(search.best_params_.values())[0]:.3f}")

rng = np.random.RandomState(0)
B = 200
coefs = {label: np.zeros((B, 10)) for label in models}
for b in range(B):
    idx = rng.choice(len(y), size=len(y), replace=True)  # 442 行から 442 行を選び直す
    for label, pipe in models.items():
        coefs[label][b] = pipe.fit(X[idx], y[idx])[-1].coef_  # 選び直した行で標準化から学習し直す

L = coefs["Lasso"]
kept = L != 0
print("Lasso が残した割合:", dict(zip(names, kept.mean(axis=0).round(2))))
print("Lasso が残した列の組み合わせ:", len({tuple(r) for r in kept}), "通り")
groups = [("s1 だけ", kept[:, i1] & ~kept[:, i2]), ("s2 だけ", ~kept[:, i1] & kept[:, i2]),
          ("両方", kept[:, i1] & kept[:, i2]), ("どちらも無し", ~kept[:, i1] & ~kept[:, i2])]
print("s1・s2 の残り方:", {g: int(m.sum()) for g, m in groups})
for label, C in coefs.items():
    print(f"{label}: s2 を残した割合 {(C[:, i2] != 0).mean():.2f}、s2 の係数が正の割合 {(C[:, i2] > 0).mean():.2f}")

# 表紙: 200 回を s1・s2 の残り方で並べ替えたマス目と、10 列が残った割合
order = np.concatenate([np.flatnonzero(m) for _, m in groups])
fig, (ax, bx) = plt.subplots(1, 2, figsize=(10, 3.2), gridspec_kw={"width_ratios": [3.2, 1]})
for r, j in enumerate([i1, i2]):
    for pos, b in enumerate(order):
        if kept[b, j]:
            ax.add_patch(plt.Rectangle((pos, 1 - r), 1, 0.8, color=RED, lw=0))
        else:
            ax.add_patch(plt.Rectangle((pos, 1 - r), 1, 0.8, color=LIGHT, lw=0))
start = 0
label_y = [2.05, 2.05, 2.5, 2.95]
for (g, m), ly in zip(groups, label_y):
    cnt = int(m.sum())
    ax.plot([start + 0.8, start + cnt - 0.8], [1.92, 1.92], color=INK, lw=1.2)
    ax.plot([start + cnt - 0.8] * 2, [1.92, ly - 0.05], color=GRAY, lw=0.8) if cnt <= 30 else None
    ax.text(start + cnt / 2 if cnt > 30 else start + cnt, ly, f"{g} {cnt} 回",
            ha="center" if cnt > 30 else "right", fontsize=9, color=INK)
    start += cnt
ax.set_yticks([1.4, 0.4])
ax.set_yticklabels(["s1（総コレステロール）", "s2（LDL）"])
ax.set_xlim(0, len(order))
ax.set_ylim(0, 3.35)
ax.set_xticks([])
ax.set_xlabel("行を選び直した 200 回（s1・s2 の残り方で並べ替え）")
for sp in ["left", "bottom"]:
    ax.spines[sp].set_visible(False)
ax.tick_params(length=0)
ax.set_title("Lasso が 0 にしなかった回（赤いマス）", fontsize=10, loc="left")
rate = kept.mean(axis=0) * 100
ys = np.arange(10)[::-1]
bx.barh(ys, rate, color=[RED if j in (i1, i2) else BLUE for j in range(10)], height=0.7)
for yv, r in zip(ys, rate):
    bx.text(r + 2, yv, f"{r:.0f}%", va="center", fontsize=8, color=INK)
bx.set_yticks(ys)
bx.set_yticklabels(names, fontsize=9)
bx.set_xlim(0, 125)
bx.set_xticks([0, 50, 100])
bx.set_title("10 列が残った割合", fontsize=10, loc="left")
fig.tight_layout()
save(fig, "regularization_cover.webp")

# s1 と s2 の係数の散らばり
fig, axes = plt.subplots(1, 3, figsize=(10, 3.4), sharex=True, sharey=True)
for ax, (label, C) in zip(axes, coefs.items()):
    ax.axhline(0, color=INK, lw=0.6)
    ax.axvline(0, color=INK, lw=0.6)
    ax.scatter(C[:, i1], C[:, i2], s=12, alpha=0.5, color=RED)
    ax.set_title(label, fontsize=10)
    ax.set_xlabel("s1 の係数")
    ax.grid(alpha=0.3)
axes[0].set_ylabel("s2 の係数")
fig.tight_layout()
save(fig, "regularization_s1_s2.webp")

# ---- 実験 4: 同じ alpha でも、列の大きさと行の数で効き目が変わる ----
print("同梱のまま: 列の二乗の和", (X ** 2).sum(axis=0)[:3].round(3), "標準偏差", X.std(axis=0)[:3].round(4))
for label, model in [("同梱のまま", make_pipeline(Lasso(alpha=1.0))),
                     ("標準化してから", make_pipeline(StandardScaler(), Lasso(alpha=1.0)))]:
    r2 = cross_val_score(model, X, y, cv=cv).mean()
    coef = model.fit(X, y)[-1].coef_
    print(f"{label}: Lasso(alpha=1.0) が残した列 {[names[j] for j in np.flatnonzero(coef)]}、R^2 {r2:.3f}")
r2_ols = cross_val_score(LinearRegression(), X, y, cv=cv).mean()
print(f"正則化なし: R^2 {r2_ols:.3f}")
X10, y10 = np.tile(Xs, (10, 1)), np.tile(y, 10)  # 同じ 442 行を 10 回並べる
for cls, a in [(Ridge, 100.0), (Lasso, 1.0)]:
    w1 = cls(alpha=a).fit(Xs, y).coef_[[i1, i2]]
    w10 = cls(alpha=a).fit(X10, y10).coef_[[i1, i2]]
    print(f"{cls.__name__}(alpha={a}): s1, s2 の係数 442 行 {w1.round(2)} → 4420 行 {w10.round(2)}")

alphas = np.logspace(-4, 3, 57)
fold = np.empty(len(y), dtype=int)
for k, (_, test) in enumerate(cv.split(Xs)):
    fold[test] = k
split10 = PredefinedSplit(np.tile(fold, 10))  # 並べた同じ行は、元の行と同じ分割に入れる
fig, axes = plt.subplots(1, 2, figsize=(9.5, 3.5), sharey=True)
X10raw = np.tile(X, (10, 1))
cases = [("同梱のまま（列の二乗の和が 1）", X, y, None, False, BLUE, "-"),
         ("標準化してから", X, y, None, True, RED, "-"),
         ("標準化して同じ行を 10 回並べる", X10raw, y10, split10, True, GREEN, ":")]
for ax, cls in zip(axes, [Lasso, Ridge]):
    for label, data, target, split, scale, color, ls in cases:
        make = (lambda a: make_pipeline(StandardScaler(), cls(alpha=a))) if scale else (lambda a: cls(alpha=a))
        scores = [cross_val_score(make(a), data, target, cv=split or cv).mean() for a in alphas]
        ax.semilogx(alphas, scores, color=color, ls=ls, lw=2.4, label=label)
        print(f"{cls.__name__} {label}: R^2 が最大の alpha {alphas[int(np.argmax(scores))]:.4g}、"
              f"alpha=1 の R^2 {scores[list(np.round(alphas, 6)).index(1.0)]:.3f}")
    ax.axvline(1.0, color=GRAY, lw=1, ls="--")
    ax.text(1.15, 0.53, "既定の alpha=1.0", fontsize=8, color=GRAY)
    ax.set_title(cls.__name__, fontsize=10)
    ax.set_xlabel("alpha（対数の軸）")
    ax.set_ylim(0, 0.58)
    ax.grid(alpha=0.3)
axes[0].set_ylabel("交差検証の R^2")
axes[1].legend(fontsize=8, loc="lower left")
fig.tight_layout()
save(fig, "regularization_alpha_scale.webp")

# ---- 実験 5: 標準化と Lasso を pipeline にして、交差検証で alpha を選ぶ ----
pipe = make_pipeline(StandardScaler(), Lasso())
search = GridSearchCV(pipe, {"lasso__alpha": np.logspace(-3, 2, 26)}, cv=cv).fit(X, y)
best = search.best_params_["lasso__alpha"]
coef = search.best_estimator_[-1].coef_
print(f"選んだ alpha {best:.3f}、交差検証の R^2 {search.best_score_:.3f}、"
      f"0 にした列 {[names[j] for j in np.flatnonzero(coef == 0)]}")
for a in [0.1, 0.3, 1.0, 3.0]:
    pipe = make_pipeline(StandardScaler(), Lasso(alpha=a))
    r2 = cross_val_score(pipe, X, y, cv=cv).mean()
    coef = pipe.fit(X, y)[-1].coef_
    print(f"alpha={a}: 交差検証の R^2 {r2:.3f}、0 にした列 {[names[j] for j in np.flatnonzero(coef == 0)]}")

# ---- 補助の図: 0 の近くでの L2 と L1 のペナルティの形 ----
w = np.linspace(-1.5, 1.5, 301)
fig, axes = plt.subplots(1, 2, figsize=(8, 2.8), sharey=True)
for ax, (title, pen, tangent) in zip(axes, [("L2: w^2", w ** 2, None), ("L1: |w|", np.abs(w), None)]):
    ax.plot(w, pen, color=RED, lw=2)
    ax.axhline(0, color=INK, lw=0.6)
    ax.set_title(title, fontsize=10)
    ax.set_xlabel("係数 w")
    ax.grid(alpha=0.3)
axes[0].annotate("0 に近づくと傾きも 0 に近づく", xy=(0.3, 0.09), xytext=(-0.9, 1.95), fontsize=9,
                 arrowprops=dict(arrowstyle="->", color=INK))
axes[1].annotate("0 の近くでも傾きは 1 のまま", xy=(0.3, 0.3), xytext=(-0.9, 1.95), fontsize=9,
                 arrowprops=dict(arrowstyle="->", color=INK))
axes[0].set_ylabel("ペナルティ（alpha=1）")
axes[0].set_ylim(-0.1, 2.3)
fig.tight_layout()
save(fig, "regularization_penalty.webp")
