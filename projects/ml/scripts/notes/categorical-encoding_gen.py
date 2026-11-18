"""categorical-encoding ノートの実験と図を生成するスクリプト。

本文に載せた実験（意味の無い番号の列を目的変数の平均で置き換える、整数の順番を並べ替える、
学習時に無かったカテゴリ、行ごとに 1 つしか無いカテゴリの置き換え先、モデルごとの比較）を同じ順に実行し、
出力を標準出力に、図を Page Bundle に WebP で保存する。
データは OpenML の house_prices（data_id=42165、Ames の住宅価格 1460 行）を fetch_openml で 1 回取得する。
実行: cd projects/ml && .venv/bin/python scripts/notes/categorical-encoding_gen.py
確認した版: scikit-learn 1.9.1、NumPy 2.5.4、pandas 3.1.1
"""
import time
import warnings
from io import BytesIO
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Rectangle
from PIL import Image
from sklearn.compose import make_column_transformer
from sklearn.datasets import fetch_openml
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.model_selection import KFold, cross_val_score, cross_validate, train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder, StandardScaler, TargetEncoder
from sklearn.tree import DecisionTreeRegressor

NOTE_DIR = Path(__file__).resolve().parents[2] / "notes" / "ml" / "categorical-encoding"
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10,
                     "axes.spines.top": False, "axes.spines.right": False})
BLUE, RED, GREEN, INK, GRAY = "#7aa6c2", "#e15759", "#59a14f", "#333333", "#999999"


def save(fig, name):
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight", facecolor="#ffffff")
    plt.close(fig)
    buf.seek(0)
    Image.open(buf).convert("RGB").save(NOTE_DIR / name, "WEBP", quality=90, method=6)


ames = fetch_openml(data_id=42165, as_frame=True).frame
y = np.log(ames["SalePrice"].to_numpy())        # 価格の対数を予測する
cv = KFold(5, shuffle=True, random_state=0)

# ============================================================
# 実験 1: 意味の無い番号の列を、目的変数の平均で置き換える
# ============================================================
def leak_run(n_levels, seed=0):
    rng = np.random.default_rng(seed)
    if n_levels >= len(ames):
        code = np.arange(len(ames))                     # 家ごとに別の番号
    else:
        code = rng.integers(0, n_levels, len(ames))     # 番号を n_levels 通りから無作為に振る
    X = pd.DataFrame({"Neighborhood": ames["Neighborhood"].astype(str),
                      "番号": code.astype(str)})
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.3, random_state=seed)
    res = {}
    for way in ["fit→transform", "fit_transform"]:
        enc = TargetEncoder(cv=KFold(5, shuffle=True, random_state=0))
        if way == "fit→transform":
            Z_tr = enc.fit(X_tr, y_tr).transform(X_tr)  # 学習データを、学習データ全体の平均で置き換える
        else:
            Z_tr = enc.fit_transform(X_tr, y_tr)        # 交差して置き換える
        Z_te = enc.transform(X_te)
        model = LinearRegression().fit(Z_tr, y_tr)
        cv_r2 = cross_val_score(LinearRegression(), Z_tr, y_tr, cv=KFold(5, shuffle=True, random_state=1)).mean()
        res[way] = (model.score(Z_tr, y_tr), cv_r2, model.score(Z_te, y_te))
    return res


# 番号の列を入れない時の基準
X0 = ames[["Neighborhood"]].astype(str)
X0_tr, X0_te, y0_tr, y0_te = train_test_split(X0, y, test_size=0.3, random_state=0)
enc0 = TargetEncoder(cv=KFold(5, shuffle=True, random_state=0))
m0 = LinearRegression().fit(enc0.fit_transform(X0_tr, y0_tr), y0_tr)
base_te = m0.score(enc0.transform(X0_te), y0_te)
print(f"Neighborhood だけ: テストの R² {base_te:.2f}")

levels = [10, 30, 100, 300, 500, 700, 1000, 1460]
leak = {k: leak_run(k) for k in levels}
for k in levels:
    a, b = leak[k]["fit→transform"], leak[k]["fit_transform"]
    print(f"番号 {k:>4} 通り  fit→transform: 学習 {a[0]:.2f} 交差検証 {a[1]:.2f} テスト {a[2]:.2f}"
          f"  | fit_transform: 学習 {b[0]:.2f} 交差検証 {b[1]:.2f} テスト {b[2]:.2f}")

fig, ax = plt.subplots(figsize=(8.2, 4.4))
xs = np.arange(len(levels))
for way, color, tag in [("fit→transform", RED, "Z1"), ("fit_transform", BLUE, "Z2")]:
    cvv = [leak[k][way][1] for k in levels]
    tev = [leak[k][way][2] for k in levels]
    ax.plot(xs, cvv, "-o", color=color, lw=2, label=f"{tag} {way}：学習データで交差検証")
    ax.plot(xs, tev, "--s", color=color, lw=2, label=f"{tag} {way}：テストデータ")
ax.axhline(base_te, color=GRAY, lw=1, ls=":")
ax.text(len(levels) - 1.05, base_te + 0.03, f"番号の列なし（テスト {base_te:.2f}）", color=GRAY, ha="right", fontsize=9)
ax.set_xticks(xs, [str(k) if k < 1460 else "1460\n（家ごとに別）" for k in levels])
ax.set_xlabel("意味の無い番号の列が取る値の種類")
ax.set_ylabel("線形回帰の R²")
ax.set_ylim(-0.1, 1.08)
ax.grid(True, alpha=0.25)
ax.legend(loc="upper left", fontsize=8.5, frameon=False)
ax.set_title("番号の列を TargetEncoder で置き換えた時の R²（Ames の住宅価格）", fontsize=10.5)
save(fig, "ce_cover.webp")

# ============================================================
# 実験 2: 整数に置き換える順番を並べ替える
# ============================================================
nb = ames[["Neighborhood"]].astype(str)
names = sorted(nb["Neighborhood"].unique())       # OrdinalEncoder の既定はアルファベット順
print("Neighborhood の種類:", len(names))

# 3 通りの置き換え方を、4 つの地区で並べる
show = ["CollgCr", "MeadowV", "NoRidge", "OldTown"]
te = TargetEncoder(cv=KFold(5, shuffle=True, random_state=0)).fit(nb, y)
te_val = dict(zip(te.categories_[0].tolist(), te.encodings_[0]))
counts = nb["Neighborhood"].value_counts()
mean_log = pd.Series(y).groupby(nb["Neighborhood"].to_numpy()).mean()
for n in show:
    print(f"{n:<8} 行 {counts[n]:>3}  整数 {names.index(n):>2}  価格の対数の平均 {mean_log[n]:.3f}  TargetEncoder {te_val[n]:.3f}")


def cv_r2(enc, model):
    return cross_val_score(make_pipeline(enc, model), nb, y, cv=cv).mean()


onehot_lin = cv_r2(OneHotEncoder(handle_unknown="ignore"), LinearRegression())
alpha_lin = cv_r2(OrdinalEncoder(categories=[names]), LinearRegression())
by_price = list(ames.groupby("Neighborhood", observed=True)["SalePrice"].median().sort_values().index.astype(str))
price_lin = cv_r2(OrdinalEncoder(categories=[by_price]), LinearRegression())
rng = np.random.default_rng(0)
perms = [list(rng.permutation(names)) for _ in range(500)]
perm_lin = np.array([cv_r2(OrdinalEncoder(categories=[p]), LinearRegression()) for p in perms])
perm_tree3 = np.array([cv_r2(OrdinalEncoder(categories=[p]), DecisionTreeRegressor(max_depth=3, random_state=0)) for p in perms])
perm_tree = np.array([cv_r2(OrdinalEncoder(categories=[p]), DecisionTreeRegressor(random_state=0)) for p in perms])
onehot_tree3 = cv_r2(OneHotEncoder(handle_unknown="ignore"), DecisionTreeRegressor(max_depth=3, random_state=0))
onehot_tree = cv_r2(OneHotEncoder(handle_unknown="ignore"), DecisionTreeRegressor(random_state=0))
print(f"線形回帰: one-hot {onehot_lin:.3f}、アルファベット順 {alpha_lin:.3f}、価格の中央値の順 {price_lin:.3f}")
print("線形回帰、無作為な順 500 通り: 最小 {:.3f} 中央値 {:.3f} 最大 {:.3f}".format(perm_lin.min(), np.median(perm_lin), perm_lin.max()))
print("決定木 max_depth=3、無作為な順: 最小 {:.3f} 中央値 {:.3f} 最大 {:.3f}、one-hot {:.3f}".format(
    perm_tree3.min(), np.median(perm_tree3), perm_tree3.max(), onehot_tree3))
print("決定木 深さの制限なし、無作為な順: 最小 {:.3f} 最大 {:.3f}、one-hot {:.3f}".format(perm_tree.min(), perm_tree.max(), onehot_tree))

fig, axes = plt.subplots(1, 2, figsize=(10, 3.9), sharey=True)
bins = np.linspace(-0.05, 0.6, 40)
for ax, vals, oh, title in [(axes[0], perm_lin, onehot_lin, "線形回帰"),
                            (axes[1], perm_tree3, onehot_tree3, "決定木（max_depth=3）")]:
    ax.hist(vals, bins=bins, color=BLUE, alpha=0.85, label="無作為な順 500 通り")
    ax.axvline(oh, color=RED, lw=2, label=f"one-hot（{oh:.2f}）")
    ax.set_title(title, fontsize=10.5)
    ax.set_xlabel("交差検証の R²")
    ax.grid(True, alpha=0.25)
axes[0].axvline(alpha_lin, color=INK, lw=1.5, ls="--", label=f"アルファベット順（{alpha_lin:.2f}）")
axes[0].axvline(price_lin, color=GREEN, lw=1.5, ls="-.", label=f"価格の中央値の順（{price_lin:.2f}）")
axes[0].set_ylabel("並べ方の数")
axes[0].legend(fontsize=8.5, frameon=False, loc="upper left", bbox_to_anchor=(0.2, 1.0))
axes[1].legend(fontsize=8.5, frameon=False, loc="upper right")
save(fig, "ce_order.webp")

# ============================================================
# 実験 3: 学習時に無かったカテゴリ
# ============================================================
cat_cols = [c for c in ames.columns if not pd.api.types.is_numeric_dtype(ames[c])]
Xc = ames[cat_cols].astype(str)
print("文字列の列:", len(cat_cols), "one-hot にした時の列:", OneHotEncoder().fit(Xc).transform(Xc).shape[1])
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")
    s_err = cross_val_score(make_pipeline(OneHotEncoder(), Ridge()), Xc, y, cv=cv)
print("handle_unknown='error'（既定）:", s_err, "警告", sum("Scoring failed" in str(x.message) for x in w), "件")
s_ign = cross_val_score(make_pipeline(OneHotEncoder(handle_unknown="ignore"), Ridge()), Xc, y, cv=cv)
print("handle_unknown='ignore'     :", s_ign.round(3))
unseen_rows, unseen_names = [], []
for tr, te in cv.split(Xc):
    seen = {c: set(Xc[c].iloc[tr]) for c in cat_cols}
    hit = np.zeros(len(te), bool)
    found = []
    for c in cat_cols:
        miss = ~Xc[c].iloc[te].isin(seen[c]).to_numpy()
        hit |= miss
        found += [f"{c}={v}" for v in sorted(set(Xc[c].iloc[te][miss]))]
    unseen_rows.append(int(hit.sum()))
    unseen_names.append(found)
for i, (n, fnd) in enumerate(zip(unseen_rows, unseen_names), 1):
    print(f"分割 {i}: 無かったカテゴリを含む行 {n} / 292  例 {fnd[:3]}")

fig, ax = plt.subplots(figsize=(8.6, 4.0))
xs = np.arange(1, 6)
ax.bar(xs, unseen_rows, color=RED, alpha=0.85, width=0.55)
for x, n, fnd in zip(xs, unseen_rows, unseen_names):
    ax.text(x, n + 0.25, f"{n} 行", ha="center", fontsize=9.5, color=INK)
    ax.text(x, n + 1.1, "\n".join(fnd[:2]), ha="center", va="bottom", fontsize=7.5, color=GRAY)
ax.set_xticks(xs, [f"分割 {i}\nR² nan → {s:.2f}" for i, s in zip(xs, s_ign)])
ax.set_ylabel("学習側に無いカテゴリを含む行")
ax.set_ylim(0, max(unseen_rows) + 3.2)
ax.grid(True, axis="y", alpha=0.25)
ax.set_title("5 分割の交差検証で、検証側だけに出てくるカテゴリ（43 列のどれか）", fontsize=10.5)
save(fig, "ce_unseen.webp")

# ============================================================
# 実験 4: 家ごとに別の番号を置き換えた値
# ============================================================
ids = pd.DataFrame({"番号": np.arange(len(ames)).astype(str)})
enc = TargetEncoder(cv=KFold(5, shuffle=True, random_state=0))
z_fit = enc.fit(ids, y).transform(ids).ravel()
z_cross = TargetEncoder(cv=KFold(5, shuffle=True, random_state=0)).fit_transform(ids, y).ravel()
print("fit→transform と y の差の最大:", np.abs(z_fit - y).max())
print("fit_transform の値: 最小 {:.4f} 最大 {:.4f}、y の平均 {:.4f}".format(z_cross.min(), z_cross.max(), y.mean()))

fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.0), sharex=True, sharey=True)
for ax, z, title, color in [(axes[0], z_fit, "fit(X, y).transform(X)", RED),
                            (axes[1], z_cross, "fit_transform(X, y)", BLUE)]:
    ax.scatter(y, z, s=6, color=color, alpha=0.6)
    lo, hi = y.min(), y.max()
    ax.plot([lo, hi], [lo, hi], color=GRAY, lw=1, ls=":")
    ax.set_title(title, fontsize=10.5)
    ax.set_xlabel("価格の対数（目的変数）")
    ax.grid(True, alpha=0.25)
axes[0].set_ylabel("番号の列を置き換えた値")
axes[0].text(11.0, 13.0, "置き換えた値が\n目的変数そのもの", color=RED, fontsize=9)
axes[1].text(11.0, 13.0, "どの家も平均の\n付近に縮む", color=BLUE, fontsize=9)
save(fig, "ce_identity.webp")

# 交差した置き換え（cross fitting）の模式図
fig, ax = plt.subplots(figsize=(8.8, 2.7))
ax.set_xlim(0.3, 9.6)
ax.set_ylim(0.3, 5.5)
ax.axis("off")
for row in range(5):
    yy = 4.4 - row
    for blk in range(5):
        is_self = blk == row
        ax.add_patch(Rectangle((1.6 + blk * 1.1, yy), 1.0, 0.7,
                               facecolor=RED if is_self else BLUE, alpha=0.85 if is_self else 0.35,
                               edgecolor="#ffffff"))
        label, text_color = ("置き換える", "#ffffff") if is_self else ("平均を計算", INK)
        ax.text(2.1 + blk * 1.1, yy + 0.35, label, ha="center", va="center", fontsize=8, color=text_color)
    ax.text(1.4, yy + 0.35, f"{row + 1} 回目", ha="right", va="center", fontsize=9, color=INK)
for blk in range(5):
    ax.text(2.1 + blk * 1.1, 5.25, f"行の組 {blk + 1}", ha="center", fontsize=9, color=INK)
ax.text(7.25, 2.75, "どの行も、自分を含まない\n4 組の平均で置き換わる", fontsize=9.5, color=INK, va="center")
save(fig, "ce_crossfit.webp")

# ============================================================
# 実験 5: モデルと置き換え方の組み合わせ（全 79 列）
# ============================================================
X_all = ames.drop(columns=["Id", "SalePrice"])
num_cols = [c for c in X_all.columns if pd.api.types.is_numeric_dtype(X_all[c])]
X_all[cat_cols] = X_all[cat_cols].fillna("欠損").astype(str)   # 欠損も 1 つのカテゴリとして扱う
X_cat = X_all.copy()
X_cat[cat_cols] = X_cat[cat_cols].astype("category")        # HistGradientBoosting にカテゴリだと伝える型

encoders = {
    "one-hot": lambda: OneHotEncoder(handle_unknown="ignore", sparse_output=False),
    "整数": lambda: OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1),
    "目的変数の平均": lambda: TargetEncoder(cv=KFold(5, shuffle=True, random_state=0)),
}
rows = []
for enc_name, mk in encoders.items():
    for model_name in ["Ridge", "HistGradientBoosting"]:
        if model_name == "Ridge":
            pre = make_column_transformer((make_pipeline(SimpleImputer(), StandardScaler()), num_cols),
                                          (make_pipeline(mk(), StandardScaler()), cat_cols))
            model = make_pipeline(pre, Ridge(alpha=10.0))
        else:
            pre = make_column_transformer(("passthrough", num_cols), (mk(), cat_cols))
            model = make_pipeline(pre, HistGradientBoostingRegressor(random_state=0))
        r = cross_validate(model, X_all, y, cv=cv, scoring="neg_root_mean_squared_error")
        rows.append((model_name, enc_name, -r["test_score"].mean(), r["fit_time"].mean(),
                     model.fit(X_all, y)[0].transform(X_all.iloc[:5]).shape[1]))
r = cross_validate(HistGradientBoostingRegressor(random_state=0), X_cat, y, cv=cv,
                   scoring="neg_root_mean_squared_error")
rows.append(("HistGradientBoosting", "カテゴリのまま", -r["test_score"].mean(), r["fit_time"].mean(), X_cat.shape[1]))
for m, e, rmse, t, ncol in rows:
    print(f"{m:<21} {e:<8} RMSE {rmse:.4f}  モデルに渡す列 {ncol}")

# ============================================================
# 補足: 10 万行 × 1 万種類を one-hot にした時の大きさ（本文の疎行列の段落）
# ============================================================
rng = np.random.default_rng(0)
many = rng.integers(0, 10_000, 100_000).astype(str).reshape(-1, 1)
sp = OneHotEncoder().fit_transform(many)               # 既定は CSR 形式の疎行列
dense_gb = sp.shape[0] * sp.shape[1] * 8 / 1e9
sparse_mb = (sp.data.nbytes + sp.indices.nbytes + sp.indptr.nbytes) / 1e6
print(f"one-hot {sp.shape}: 密な float64 {dense_gb:.1f} GB、CSR {sparse_mb:.1f} MB")
