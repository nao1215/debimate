"""hyperparameter ノートの実験と図を生成するスクリプト。

California Housing に HistGradientBoostingRegressor を当て、ハイパーパラメータの探索を
次の順に実行する。出力は標準出力に、図は Page Bundle に WebP で保存する。
  1. GridSearchCV（各 3 値の 81 通りと各 2 値の 16 通り）。訓練の R² と交差検証の R²
  2. RandomizedSearchCV（81 回）をseed 30 通りで繰り返し、回数ごとの最高点を数える
  3. learning_rate を対数で選ぶ場合と一様に選ぶ場合
  4. HalvingRandomSearchCV（最初の行数を自動で決める場合と 1719 行にする場合）をseed 20 通りで
  5. 選んだ設定を訓練データ全体で学習し直し、テストデータで 1 回だけ測る
実行: cd projects/ml && .venv/bin/python scripts/notes/hyperparameter_gen.py
計算に 32 コアで 10 分ほどかかる。環境変数 HP_CACHE にファイルのパスを渡すと、
計算の結果をそこに保存し、次からは図だけを描き直す。
確認した版: scikit-learn 1.9.1、NumPy 2.5.4、SciPy 1.18.1、matplotlib 3.11.2、Pillow 13.0.0
"""
import os
import pickle
import time
from io import BytesIO
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image
from scipy.stats import loguniform, randint, uniform
from sklearn.datasets import fetch_california_housing
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.experimental import enable_halving_search_cv  # noqa: F401
from sklearn.model_selection import (GridSearchCV, HalvingRandomSearchCV, KFold,
                                     RandomizedSearchCV, train_test_split)

NOTE_DIR = Path(__file__).resolve().parents[2] / "notes" / "ml" / "hyperparameter"
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10,
                     "axes.spines.top": False, "axes.spines.right": False})
BLUE, RED, GREEN, INK, GRAY = "#7aa6c2", "#e15759", "#59a14f", "#333333", "#999999"
CACHE = os.environ.get("HP_CACHE")


def to_image(fig, dpi=200):
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, facecolor="#ffffff")
    plt.close(fig)
    buf.seek(0)
    return Image.open(buf).convert("RGB")


def save(fig, name):
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight", facecolor="#ffffff")
    plt.close(fig)
    buf.seek(0)
    Image.open(buf).convert("RGB").save(NOTE_DIR / name, "WEBP", quality=90, method=6)


# ============================================================
# データとモデル
# ============================================================
X, y = fetch_california_housing(return_X_y=True)      # 20640 行 × 8 列
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=0)
cv = KFold(n_splits=3, shuffle=True, random_state=0)
model = HistGradientBoostingRegressor(max_iter=100, early_stopping=False, random_state=0)


def compute():
    res = {}
    # ------------------------------------------------------------
    # 実験 1: グリッド探索（各 3 値で 81 通り、各 2 値で 16 通り）
    # ------------------------------------------------------------
    grid81 = {
        "learning_rate": [0.01, 0.1, 1.0],
        "max_leaf_nodes": [4, 32, 256],
        "min_samples_leaf": [1, 14, 200],
        "l2_regularization": [0.001, 0.1, 10.0],
    }
    grid16 = {k: [v[0], v[-1]] for k, v in grid81.items()}
    for name, grid in [("grid81", grid81), ("grid16", grid16)]:
        t = time.time()
        search = GridSearchCV(model, grid, cv=cv, scoring="r2", return_train_score=True, n_jobs=-1)
        search.fit(X_train, y_train)
        res[name] = {"cv_results": pd.DataFrame(search.cv_results_), "best_params": search.best_params_,
                     "best_score": search.best_score_, "wall": time.time() - t}

    # ------------------------------------------------------------
    # 実験 2: ランダム探索 81 回を、seed 30 通りで繰り返す
    # ------------------------------------------------------------
    dist = {
        "learning_rate": loguniform(0.01, 1.0),
        "max_leaf_nodes": randint(4, 257),
        "min_samples_leaf": randint(1, 201),
        "l2_regularization": loguniform(0.001, 10.0),
    }
    rand = []
    for seed in range(30):
        search = RandomizedSearchCV(model, dist, n_iter=81, cv=cv, scoring="r2",
                                    random_state=seed, n_jobs=-1)
        search.fit(X_train, y_train)
        rand.append(pd.DataFrame(search.cv_results_))
    res["rand"] = rand

    # ------------------------------------------------------------
    # 実験 3: learning_rate を一様に選ぶ（他は実験 2 と同じ）。16 回 × seed 30 通り
    # ------------------------------------------------------------
    dist_uniform = dict(dist, learning_rate=uniform(0.01, 0.99))  # 0.01〜1.0 を一様に
    res["uniform16"] = []
    res["log16"] = []
    for seed in range(30):
        for key, d in [("uniform16", dist_uniform), ("log16", dist)]:
            search = RandomizedSearchCV(model, d, n_iter=16, cv=cv, scoring="r2",
                                        random_state=seed, n_jobs=-1)
            search.fit(X_train, y_train)
            res[key].append(pd.DataFrame(search.cv_results_))

    # ------------------------------------------------------------
    # 実験 4: HalvingRandomSearchCV。候補 81 個、1/3 ずつ残す
    # ------------------------------------------------------------
    halving = []
    for seed in range(20):
        row = {}
        for min_resources in ["exhaust", 1719]:
            t = time.time()
            search = HalvingRandomSearchCV(model, dist, n_candidates=81, factor=3,
                                           resource="n_samples", min_resources=min_resources,
                                           cv=cv, scoring="r2", random_state=seed,
                                           refit=False, n_jobs=-1)
            search.fit(X_train, y_train)
            row[min_resources] = {"cv_results": pd.DataFrame(search.cv_results_),
                                  "n_resources": list(search.n_resources_),
                                  "n_candidates": list(search.n_candidates_),
                                  "wall": time.time() - t}
        # 同じ 81 候補を、訓練データ全体（3 分割の交差検証）でも測る
        first = row["exhaust"]["cv_results"]
        cands = [dict(p) for p in first[first["iter"] == 0]["params"]]
        other = row[1719]["cv_results"]
        assert cands == [dict(p) for p in other[other["iter"] == 0]["params"]]
        full = GridSearchCV(model, [{k: [v] for k, v in p.items()} for p in cands],
                            cv=cv, scoring="r2", n_jobs=-1).fit(X_train, y_train)
        row["cands"] = cands
        row["full_score"] = full.cv_results_["mean_test_score"]
        row["full_fit_time"] = float(np.sum(full.cv_results_["mean_fit_time"]) * cv.get_n_splits())
        halving.append(row)
    res["halving"] = halving

    # ------------------------------------------------------------
    # 実験 5: テストデータで 1 回だけ測る
    # ------------------------------------------------------------
    r0 = res["rand"][0]
    best_rand = dict(r0.loc[r0["mean_test_score"].idxmax(), "params"])   # ランダム探索（seed 0）の 1 位
    g = res["grid81"]["cv_results"]
    best_train = dict(g.loc[g["mean_train_score"].idxmax(), "params"])   # 訓練の R² が最高の組み合わせ
    tests = {}
    for name, params in [("rand81_seed0", best_rand), ("grid81", res["grid81"]["best_params"]),
                         ("grid81_by_train", best_train)]:
        m = HistGradientBoostingRegressor(max_iter=100, early_stopping=False, random_state=0, **params)
        tests[name] = {"params": params, "test_r2": m.fit(X_train, y_train).score(X_test, y_test)}
    res["tests"] = tests
    return res


if CACHE and Path(CACHE).exists():
    res = pickle.loads(Path(CACHE).read_bytes())
else:
    res = compute()
    if CACHE:
        Path(CACHE).write_bytes(pickle.dumps(res))

# ============================================================
# 出力
# ============================================================
LR_GRID = [0.01, 0.1, 1.0]
g81 = res["grid81"]["cv_results"]
g16 = res["grid16"]["cv_results"]
print(f"訓練 {len(X_train)} 行、テスト {len(X_test)} 行")
print("--- 実験 1: グリッド探索")
for name in ["grid81", "grid16"]:
    r = res[name]
    lrs = sorted({p["learning_rate"] for p in r["cv_results"]["params"]})
    print(f"{name}: {len(r['cv_results'])} 通り、learning_rate は {lrs}、"
          f"最高の CV R² {r['best_score']:.4f}  {r['best_params']}")
i_tr = g81["mean_train_score"].idxmax()
i_cv = g81["mean_test_score"].idxmax()
for label, i in [("訓練の R² が最高", i_tr), ("CV の R² が最高", i_cv)]:
    print(f"{label}: 訓練 {g81.loc[i, 'mean_train_score']:.3f}  CV {g81.loc[i, 'mean_test_score']:.3f}  "
          f"{g81.loc[i, 'params']}")
for lr in LR_GRID:
    s = g81[[p["learning_rate"] == lr for p in g81["params"]]]
    print(f"  learning_rate={lr}: 27 通りの CV R² の最高 {s['mean_test_score'].max():.4f}"
          f"、最低 {s['mean_test_score'].min():.4f}")
    for mln in [4, 32, 256]:
        t = s[[p["max_leaf_nodes"] == mln for p in s["params"]]]["mean_test_score"]
        print(f"    max_leaf_nodes={mln}: CV R² {t.min():.3f}〜{t.max():.3f}")

print("--- 実験 2: ランダム探索（seed 30 通り）")
rand_scores = np.array([r["mean_test_score"].to_numpy() for r in res["rand"]])
cum = np.maximum.accumulate(rand_scores, axis=1)
best81, best16 = res["grid81"]["best_score"], res["grid16"]["best_score"]
for n in [4, 8, 16, 27, 81]:
    c = cum[:, n - 1]
    print(f"{n:2d} 回: 最高の CV R² の中央値 {np.median(c):.4f}（最小 {c.min():.4f}、最大 {c.max():.4f}）"
          f"  グリッド 81 回以上 {np.mean(c >= best81) * 30:.0f}/30、グリッド 16 回以上 {np.mean(c >= best16) * 30:.0f}/30")
r0 = res["rand"][0]
for label, r in [("グリッド 81 回の 1 位", g81), ("ランダム 81 回（seed 0）の 1 位", r0)]:
    i = r["mean_test_score"].idxmax()
    folds = [round(float(r.loc[i, f"split{k}_test_score"]), 3) for k in range(3)]
    print(f"{label}: 3 分割の R² {folds}、標準偏差 {r.loc[i, 'std_test_score']:.3f}")
# 同じ 3 分割で、ランダム 81 回の 1 位とグリッド 81 回の 1 位を分割ごとに比べる
gi = g81["mean_test_score"].idxmax()
gfold = np.array([g81.loc[gi, f"split{k}_test_score"] for k in range(3)])
all_win = 0
for r in res["rand"]:
    i = r["mean_test_score"].idxmax()
    d = np.array([r.loc[i, f"split{k}_test_score"] for k in range(3)]) - gfold
    all_win += bool((d > 0).all())
print(f"ランダム 81 回の 1 位が、3 分割の全てでグリッド 81 回の 1 位を上回った seed: {all_win}/30")
d81 = np.array([r["mean_test_score"].max() for r in res["rand"]]) - best81
print(f"ランダム 81 回の 1 位とグリッド 81 回の 1 位の CV R² の差: {d81.min():.3f}〜{d81.max():.3f}")
print("seed 0 の learning_rate の異なる値:", r0["param_learning_rate"].nunique(),
      " 最高:", dict(r0.loc[r0["mean_test_score"].idxmax(), "params"]))

print("--- 実験 3: learning_rate の選び方（16 回、seed 30 通り）")
for key in ["log16", "uniform16"]:
    best = np.array([r["mean_test_score"].max() for r in res[key]])
    lr = np.concatenate([r["param_learning_rate"].astype(float).to_numpy() for r in res[key]])
    print(f"{key}: 最高の CV R² の中央値 {np.median(best):.4f}（最小 {best.min():.4f}）"
          f"  learning_rate が 0.1 未満の割合 {np.mean(lr < 0.1):.0%}")

print("--- 実験 4: HalvingRandomSearchCV（seed 20 通り）")
H = res["halving"]
ranks = {"exhaust": [], 1719: []}
for seed, row in enumerate(H):
    full = row["full_score"]
    for mr in ["exhaust", 1719]:
        cr = row[mr]["cv_results"]
        last = cr[cr["iter"] == cr["iter"].max()]
        chosen = dict(last.loc[last["mean_test_score"].idxmax(), "params"])
        ci = row["cands"].index(chosen)
        rank = int((full > full[ci]).sum()) + 1
        ranks[mr].append(rank)
        row[f"chosen_{mr}"] = (ci, rank)
    print(f"seed {seed:2d}: 81 候補の 1 位 {full.max():.4f}  自動 {ranks['exhaust'][-1]:2d} 位"
          f"（{full[row['chosen_exhaust'][0]]:.4f}）  1719 行から {ranks[1719][-1]:2d} 位"
          f"（{full[row['chosen_1719'][0]]:.4f}）")
gaps = {"exhaust": [], 1719: []}  # 学習データ全体で測った R² の、1 位と選ばれた候補の差
for row in H:
    for mr in ["exhaust", 1719]:
        gaps[mr].append(float(row["full_score"].max() - row["full_score"][row[f"chosen_{mr}"][0]]))
for mr in ["exhaust", 1719]:
    g = np.array(gaps[mr])
    worst = int(np.argmax(ranks[mr]))
    print(f"{mr}: 行数 {H[0][mr]['n_resources']}、候補 {H[0][mr]['n_candidates']}、"
          f"選んだ候補の順位の中央値 {np.median(ranks[mr]):.0f}、最悪 {max(ranks[mr])}（1 位との差 {g[worst]:.3f}）"
          f"  1 位との R² の差の中央値 {np.median(g):.3f}、最大 {g.max():.3f}")


# min_resources を既定（"smallest"）のままにした時の行数（学習は小さいので毎回計算する）
dist = {
    "learning_rate": loguniform(0.01, 1.0),
    "max_leaf_nodes": randint(4, 257),
    "min_samples_leaf": randint(1, 201),
    "l2_regularization": loguniform(0.001, 10.0),
}
default_search = HalvingRandomSearchCV(model, dist, n_candidates=81, cv=cv, scoring="r2",
                                       random_state=2, refit=False, n_jobs=-1).fit(X_train, y_train)
print(f"min_resources の既定: 行数 {list(default_search.n_resources_)}、候補 {list(default_search.n_candidates_)}")


def round_times(row, mr):
    cr = row[mr]["cv_results"]
    return [float((cr[cr["iter"] == it]["mean_fit_time"]).sum() * cv.get_n_splits())
            for it in sorted(cr["iter"].unique())]


for mr in ["exhaust", 1719]:
    tt = [sum(round_times(r, mr)) for r in H]
    print(f"{mr}: 学習時間の合計の中央値 {np.median(tt):.1f} 秒（{min(tt):.1f}〜{max(tt):.1f} 秒）")
print(f"81 候補を学習データ全体で: 学習時間の合計の中央値 {np.median([r['full_fit_time'] for r in H]):.1f} 秒")

print("--- 実験 5: テストデータ")
for name, t in res["tests"].items():
    print(f"{name}: テストの R² {t['test_r2']:.3f}  {t['params']}")

# ============================================================
# 図 1（表紙）: グリッド 81 回とランダム 81 回が試した learning_rate
# ============================================================
fig, axes = plt.subplots(1, 2, figsize=(10, 3.8), sharey=True)
r0lr = r0["param_learning_rate"].astype(float).to_numpy()
rng = np.random.default_rng(0)
glr = np.array([p["learning_rate"] for p in g81["params"]])
for ax, lr, sc, color, title in [
        (axes[0], glr * np.exp(rng.normal(0, 0.04, len(glr))), g81["mean_test_score"], RED,
         "グリッド 81 回（4 つを 3 値ずつ）"),
        (axes[1], r0lr, r0["mean_test_score"], BLUE, "ランダム 81 回（4 つを範囲から乱数で選ぶ）")]:
    ax.scatter(lr, sc, s=22, color=color, alpha=0.75, edgecolors="white", linewidths=0.4)
    ax.set_xscale("log")
    ax.set_xlim(0.008, 1.25)
    ax.set_ylim(0.4, 0.87)
    ax.grid(True, alpha=0.25)
    ax.set_xlabel("learning_rate（対数目盛り）")
    ax.set_title(title, fontsize=10.5, loc="left")
axes[0].set_ylabel("交差検証の R²")
axes[0].text(0.0105, 0.415, "learning_rate は 0.01・0.1・1.0 の 3 値だけで、27 回ずつ同じ値", fontsize=9, color=INK)
axes[0].axhline(best81, color=RED, lw=1, ls="--")
m4 = g81[[p["learning_rate"] == 0.1 and p["max_leaf_nodes"] == 4 for p in g81["params"]]]["mean_test_score"]
axes[0].annotate(f"max_leaf_nodes=4 の 9 回（{m4.mean():.3f}）", xy=(0.093, m4.mean()), xytext=(0.0105, m4.mean() - 0.06),
                 fontsize=9, color=INK, arrowprops={"arrowstyle": "->", "color": INK, "lw": 0.8})
axes[1].axhline(r0["mean_test_score"].max(), color=BLUE, lw=1, ls="--")
axes[0].text(0.0085, best81 + 0.006, f"1 位 {best81:.3f}", fontsize=9, color=RED)
axes[1].text(0.0085, r0["mean_test_score"].max() + 0.006, f"1 位 {r0['mean_test_score'].max():.3f}",
             fontsize=9, color=BLUE)
fig.tight_layout()
save(fig, "hp_cover.webp")

# ============================================================
# 図 2: 訓練の R² と交差検証の R²（グリッド 81 通り）
# ============================================================
fig, ax = plt.subplots(figsize=(6.4, 4.4))
colors = {0.01: GRAY, 0.1: BLUE, 1.0: RED}
for lr in LR_GRID:
    s = g81[glr == lr]
    ax.scatter(s["mean_train_score"], s["mean_test_score"], s=26, color=colors[lr],
               label=f"learning_rate={lr}", alpha=0.85, edgecolors="white", linewidths=0.4)
ax.plot([0.4, 1.0], [0.4, 1.0], color=GRAY, lw=1, ls=":")
ax.text(0.42, 0.445, "訓練 = 交差検証", fontsize=8.5, color=GRAY, rotation=37)
for i, label, dx, dy in [(i_tr, "訓練の R² で選ぶとこれ", -0.2, -0.03), (i_cv, "交差検証の R² で選ぶとこれ", -0.21, 0.045)]:
    ax.scatter(g81.loc[i, "mean_train_score"], g81.loc[i, "mean_test_score"], s=150,
               facecolors="none", edgecolors=INK, lw=1.6)
    ax.annotate(label, xy=(g81.loc[i, "mean_train_score"], g81.loc[i, "mean_test_score"]),
                xytext=(g81.loc[i, "mean_train_score"] + dx, g81.loc[i, "mean_test_score"] + dy),
                fontsize=9, arrowprops={"arrowstyle": "->", "color": INK, "lw": 0.8})
ax.set_xlim(0.4, 1.01)
ax.set_ylim(0.4, 0.9)
ax.set_xlabel("訓練の R²（学習に使った行で測る）")
ax.set_ylabel("交差検証の R²（学習に使っていない行で測る）")
ax.grid(True, alpha=0.25)
ax.legend(loc="upper left", fontsize=8.5)
fig.tight_layout()
save(fig, "hp_train_cv.webp")

# ============================================================
# 図 3: 回数ごとの最高点（ランダム 30 回の幅）とグリッド
# ============================================================
fig, ax = plt.subplots(figsize=(7.2, 4.0))
n = np.arange(1, 82)
ax.fill_between(n, np.percentile(cum, 10, axis=0), np.percentile(cum, 90, axis=0), color=BLUE, alpha=0.25,
                label="ランダム探索（seed 30 通りの 10〜90%）")
ax.plot(n, np.median(cum, axis=0), color=BLUE, lw=2, label="ランダム探索（中央値）")
ax.scatter([16, 81], [best16, best81], s=70, color=RED, zorder=4, label="グリッド探索（各 2 値と各 3 値）")
ax.text(16 + 2, best16 - 0.004, f"16 回 {best16:.3f}（learning_rate は 0.01 と 1.0）", fontsize=9, color=RED, va="top")
ax.text(81 - 1, best81 - 0.004, f"81 回 {best81:.3f}", fontsize=9, color=RED, ha="right", va="top")
ax.axhline(best81, color=RED, lw=0.8, ls="--")
ax.set_xlim(0, 84)
ax.set_ylim(0.78, 0.84)
ax.set_xlabel("試した回数")
ax.set_ylabel("それまでの最高の交差検証の R²")
ax.grid(True, alpha=0.25)
ax.legend(loc="lower right", fontsize=8.5)
fig.tight_layout()
save(fig, "hp_budget.webp")

# ============================================================
# 図 4: 4 つのハイパーパラメータと交差検証の R²（ランダム 30×81 回）
# ============================================================
allr = pd.concat(res["rand"], ignore_index=True)
fig, axes = plt.subplots(1, 4, figsize=(12, 3.3), sharey=True)
names = ["learning_rate", "max_leaf_nodes", "min_samples_leaf", "l2_regularization"]
for ax, name in zip(axes, names):
    v = allr[f"param_{name}"].astype(float)
    ax.scatter(v, allr["mean_test_score"], s=4, color=BLUE, alpha=0.35, rasterized=True)
    gvals = sorted({p[name] for p in g81["params"]})
    for gv in gvals:
        ax.axvline(gv, color=RED, lw=1, ls="--")
    if name in ("learning_rate", "l2_regularization"):
        ax.set_xscale("log")
    ax.set_title(name, fontsize=10)
    ax.set_ylim(0.4, 0.87)
    ax.grid(True, alpha=0.25)
v_mln = allr["param_max_leaf_nodes"].astype(float)
low_top = allr[v_mln < 10]["mean_test_score"].max()
high_top = allr[v_mln >= 16]["mean_test_score"].max()
mid_top = allr[(v_mln >= 10) & (v_mln < 16)]["mean_test_score"].max()
print(f"max_leaf_nodes が 10 未満の一番高い点 {low_top:.4f}、10〜15 の一番高い点 {mid_top:.4f}、16 以上の一番高い点 {high_top:.4f}")
v_lr = allr["param_learning_rate"].astype(float)
for lo, hi in [(0.01, 0.012), (0.018, 0.022)]:
    print(f"learning_rate が {lo}〜{hi} の一番高い点 {allr[(v_lr >= lo) & (v_lr < hi)]['mean_test_score'].max():.4f}")
axes[1].annotate(f"10 枚未満は一番高い点が {low_top:.3f}\n（16 枚以上は {high_top:.3f}）", xy=(7, low_top),
                 xytext=(40, 0.5), fontsize=8.5, color=INK,
                 bbox={"boxstyle": "round,pad=0.3", "fc": "white", "ec": GRAY, "lw": 0.6},
                 arrowprops={"arrowstyle": "->", "color": INK, "lw": 0.8})
axes[0].set_ylabel("交差検証の R²")
fig.text(0.5, -0.02, "青い点はランダム探索の 2430 回、赤い破線はグリッド探索が試した 3 値", ha="center", fontsize=9.5)
fig.tight_layout()
save(fig, "hp_importance.webp")

# ============================================================
# 図 5: learning_rate を対数で選ぶ場合と一様に選ぶ場合
# ============================================================
fig, axes = plt.subplots(1, 2, figsize=(10, 3.4), gridspec_kw={"width_ratios": [1.5, 1]})
lr_log = np.concatenate([r["param_learning_rate"].astype(float).to_numpy() for r in res["log16"]])
lr_uni = np.concatenate([r["param_learning_rate"].astype(float).to_numpy() for r in res["uniform16"]])
bins = np.geomspace(0.01, 1.0, 21)
axes[0].hist([lr_log, lr_uni], bins=bins, color=[BLUE, RED], label=["loguniform（0.01〜1.0）", "uniform（0.01〜1.0）"])
axes[0].set_xscale("log")
axes[0].axvspan(0.05, 0.3, color=GREEN, alpha=0.12)
axes[0].text(0.052, axes[0].get_ylim()[1] * 0.92, "R² が高い範囲", fontsize=9, color=GREEN)
axes[0].set_xlabel("選ばれた learning_rate（対数目盛り）")
axes[0].set_ylabel("回数（16 回 × seed 30 通り）")
axes[0].legend(fontsize=8.5, loc="upper left", bbox_to_anchor=(0.0, 0.85))
b_log = np.array([r["mean_test_score"].max() for r in res["log16"]])
b_uni = np.array([r["mean_test_score"].max() for r in res["uniform16"]])
for k, (b, c) in enumerate([(b_log, BLUE), (b_uni, RED)]):
    axes[1].scatter(np.full(len(b), k) + rng.uniform(-0.12, 0.12, len(b)), b, s=18, color=c, alpha=0.8)
    axes[1].plot([k - 0.25, k + 0.25], [np.median(b)] * 2, color=INK, lw=2)
axes[1].set_xticks([0, 1], ["対数で選ぶ", "一様に選ぶ"])
axes[1].set_xlim(-0.6, 1.6)
axes[1].set_ylabel("16 回の最高の交差検証の R²")
axes[1].grid(True, axis="y", alpha=0.25)
fig.tight_layout()
save(fig, "hp_logscale.webp")

# ============================================================
# 図 6: Halving の 1 回目（191 行）と学習データ全体での R²、min_samples_leaf ごと
# ============================================================
ANIM_SEED = int(os.environ.get("HP_ANIM_SEED", "2"))
row = H[ANIM_SEED]
cr = row["exhaust"]["cv_results"]
cands = row["cands"]
full = row["full_score"]
order = np.argsort(-full)
rank_of = np.empty(len(full), int)
rank_of[order] = np.arange(1, len(full) + 1)
it0 = cr[cr["iter"] == 0]
r0_score = np.array([float(it0[[dict(p) == c for p in it0["params"]]]["mean_test_score"].iloc[0]) for c in cands])
msl = np.array([c["min_samples_leaf"] for c in cands])
print(f"--- 図 6・動画（seed {ANIM_SEED}）")
top = int(order[0])
print(f"学習データ全体で 1 位の候補: {cands[top]}  学習データ全体の R² {full[top]:.4f}  1 回目（191 行）の R² {r0_score[top]:.4f}、"
      f"1 回目の順位 {int((r0_score > r0_score[top]).sum()) + 1} / 81")
big = msl >= 64
print(f"min_samples_leaf が 64 以上の候補 {big.sum()} 個: 1 回目の R² の最大 {r0_score[big].max():.4f}、"
      f"学習データ全体の R² の最大 {full[big].max():.4f}")
surv1 = [{cands.index(dict(p)) for p in cr[cr["iter"] == it]["params"]} for it in sorted(cr["iter"].unique())]
print(f"min_samples_leaf が 64 未満の候補 {(~big).sum()} 個、2 回目へ残った 27 候補のうち 64 以上 {sum(big[i] for i in surv1[1])} 個")
print(f"min_samples_leaf が 64 以上の候補の 1 回目の R²: 異なる値 {len(set(np.round(r0_score[big], 10)))} 個"
      f"（{r0_score[big].min():.5f}〜{r0_score[big].max():.5f}）")
print("学習データ全体で 1 位の候補が測られた回:", [it + 1 for it, a in enumerate(surv1) if top in a])
fig, axes = plt.subplots(1, 2, figsize=(10, 3.6), sharex=True)
for ax, sc, title in [(axes[0], r0_score, "1 回目（191 行の 3 分割）で測った R²"),
                      (axes[1], full, "学習データ全体（15480 行の 3 分割）で測った R²")]:
    ax.scatter(msl[~big], sc[~big], s=24, color=BLUE, alpha=0.85)
    ax.scatter(msl[big], sc[big], s=24, color=RED, alpha=0.85)
    ax.axvline(64, color=GRAY, lw=1, ls="--")
    ax.set_title(title, fontsize=10, loc="left")
    ax.set_xlabel("min_samples_leaf")
    ax.grid(True, alpha=0.25)
axes[0].set_ylabel("交差検証の R²")
axes[0].text(68, 0.08, f"64 以上は全て\nR² が同じ {r0_score[big].max():.3f}",
             fontsize=8.5, color=RED)
axes[1].scatter([msl[top]], [full[top]], s=150, facecolors="none", edgecolors=INK, lw=1.6)
axes[1].annotate("学習データ全体では 1 位", xy=(msl[top], full[top]), xytext=(msl[top] + 15, full[top] - 0.08),
                 fontsize=9, arrowprops={"arrowstyle": "->", "color": INK, "lw": 0.8})
axes[0].scatter([msl[top]], [r0_score[top]], s=150, facecolors="none", edgecolors=INK, lw=1.6)
fig.tight_layout()
save(fig, "hp_halving_leaf.webp")

# ============================================================
# 図 7（動く図）: Halving の各回でどの候補が残るか
# ============================================================
times = round_times(row, "exhaust")
cum_t = np.concatenate([[0.0], np.cumsum(times)])
n_res = row["exhaust"]["n_resources"]
n_cand = row["exhaust"]["n_candidates"]
alive_by_iter = []
for it in range(len(n_res)):
    sub = cr[cr["iter"] == it]
    alive_by_iter.append({cands.index(dict(p)) for p in sub["params"]})
chosen_ci = row["chosen_exhaust"][0]
total_t = cum_t[-1]
SPEED = 0.6
print(f"各回の学習時間の合計: {[round(t, 2) for t in times]} 秒（合計 {total_t:.1f} 秒）")


def anim_frame(it, sub_t, final=False):
    fig = plt.figure(figsize=(8.0, 4.6))
    fig.text(0.03, 0.95, f"HalvingRandomSearchCV が残す候補（学習時間の実測を {SPEED} 倍速で再生）",
             fontsize=11, ha="left", va="top")
    tb = fig.add_axes([0.08, 0.80, 0.88, 0.05])
    tb.barh([0], [total_t], color="#eeeeee")
    tb.barh([0], [sub_t], color=BLUE)
    for t in cum_t[1:-1]:
        tb.axvline(t, color="white", lw=2)
    tb.set_xlim(0, total_t)
    tb.set_ylim(-0.5, 0.5)
    for k in range(len(n_res)):
        tb.text((cum_t[k] + cum_t[k + 1]) / 2, -0.6, f"{k + 1} 回目", ha="center", va="top", fontsize=8,
                color=INK if k <= it else GRAY)
    tb.set_yticks([])
    tb.set_xticks([])
    for s in tb.spines.values():
        s.set_visible(False)
    tb.text(total_t, 1.2, f"3 分割の学習時間の累計 {sub_t:4.1f} / {total_t:.1f} 秒", ha="right", va="bottom", fontsize=9)
    ax = fig.add_axes([0.08, 0.14, 0.88, 0.56])
    alive = alive_by_iter[min(it, len(n_res) - 1)]
    xs = rank_of
    ys = full
    dead = np.array([i not in alive for i in range(len(full))])
    ax.scatter(xs[dead], ys[dead], s=26, color="#dddddd")
    ax.scatter(xs[~dead], ys[~dead], s=30, color=BLUE)
    ax.scatter([xs[top]], [ys[top]], s=160, facecolors="none", edgecolors=GREEN, lw=1.8)
    ax.text(xs[top] + 1.5, ys[top] + 0.004, "学習データ全体で 1 位", color=GREEN, fontsize=9)
    if final:
        ax.scatter([xs[chosen_ci]], [ys[chosen_ci]], s=170, facecolors="none", edgecolors=RED, lw=2)
        ax.text(xs[chosen_ci] + 1.5, ys[chosen_ci] + 0.006, f"選ばれた候補（{rank_of[chosen_ci]} 位）",
                color=RED, fontsize=9)
    ax.set_xlim(-1, 84)
    ax.set_ylim(full.min() - 0.03, full.max() + 0.03)
    ax.set_xlabel("81 候補を、学習データ全体で測った交差検証の R² が高い順に並べた順位")
    ax.set_ylabel("学習データ全体での R²")
    ax.grid(True, alpha=0.25)
    if it < len(n_res):
        msg = f"{it + 1} 回目: {n_cand[it]} 候補を {n_res[it]} 行で測る"
        if it + 1 < len(n_res):
            msg += f" → 上位 {n_cand[it + 1]} 候補が次へ"
    else:
        msg = "最後に残った 1 候補を選ぶ"
    ax.set_title(msg, fontsize=10.5, loc="left")
    ax.text(84, full.max() + 0.025, "青: この回で測る候補　灰: 落ちた候補", ha="right", va="top", fontsize=8.5, color=INK)
    return to_image(fig, dpi=100)


frames, durations = [], []
STEP_MS = 250
for it in range(len(n_res)):
    t0, t1 = cum_t[it], cum_t[it + 1]
    steps = max(1, int(round((t1 - t0) / SPEED * 1000 / STEP_MS)))
    for k in range(steps):
        frames.append(anim_frame(it, t0 + (t1 - t0) * (k + 1) / steps))
        durations.append(STEP_MS)
frames.append(anim_frame(len(n_res), total_t, final=True))
durations.append(3000)
print(f"動画: {len(frames)} コマ、{sum(durations) / 1000:.1f} 秒")
frames[0].save(NOTE_DIR / "hp_halving.webp", "WEBP", save_all=True, append_images=frames[1:],
               duration=durations, loop=0, quality=75, method=6)

# ============================================================
# 図 8: 選ばれた候補の、1 位との R² の差（seed 20 通り）。順位は点の横に添える
# ============================================================
fold_std = float(g81.loc[g81["mean_test_score"].idxmax(), "std_test_score"])
fig, ax = plt.subplots(figsize=(7.6, 3.2))
ax.axvspan(0, fold_std, color=GRAY, alpha=0.15)
ax.text(fold_std / 2, 1.72, f"1 候補の分け方による揺れ\n（標準偏差 {fold_std:.3f}）", fontsize=8.5,
        ha="center", va="top", color=INK)
for k, (mr, c) in enumerate([(1719, BLUE), ("exhaust", RED)]):
    g = np.array(gaps[mr])
    ys = np.full(len(g), k) + rng.uniform(-0.15, 0.15, len(g))
    ax.scatter(g, ys, s=28, color=c, alpha=0.85)
    ax.plot([np.median(g)] * 2, [k - 0.3, k + 0.3], color=INK, lw=2)
    ax.text(np.median(g) + 0.0003, k - 0.32, f"中央値 {np.median(g):.3f}（順位の中央値 {np.median(ranks[mr]):.0f} 位）",
            fontsize=8.5, va="top")
    worst = int(np.argmax(ranks[mr]))
    ax.annotate(f"{ranks[mr][worst]} 位", xy=(g[worst], ys[worst]), xytext=(g[worst], k + 0.42),
                fontsize=8.5, ha="center", color=INK,
                arrowprops={"arrowstyle": "-", "color": GRAY, "lw": 0.6})
ax.set_yticks([0, 1], ["最初の行数を 1719 行に\n（1719 行から 3 回）",
                       f"最初の行数を自動で決める\n（{H[0]['exhaust']['n_resources'][0]} 行から 5 回）"])
ax.set_ylim(-0.7, 1.8)
ax.set_xlim(-0.0005, 0.02)
ax.set_xlabel("学習データ全体で測った R² の、81 候補の 1 位と選ばれた候補の差")
ax.grid(True, axis="x", alpha=0.25)
fig.tight_layout()
save(fig, "hp_halving_rank.webp")
