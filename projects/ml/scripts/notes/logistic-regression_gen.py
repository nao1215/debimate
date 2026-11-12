"""logistic-regression ノートの実験と図を生成するスクリプト。

本文に載せた実験（血糖値だけのロジスティック回帰、ニュートン法による最尤推定、
血糖値と BMI の 2 列で引いた境目、既定の C=1.0 と liblinear の比較、C を動かした時の係数、
血糖値の単位を変えた時の交差検証、切片の正則化、
学習データでの確率の平均と、正則化を強めた時の区間ごとの確率、
完全に分けられるデータでの正則化なしの係数、行が少ない時の係数）を同じ順に実行し、
出力を標準出力に、図を Page Bundle に WebP で保存する。
データは OpenML の Pima Indians Diabetes（data_id=37）で、初回だけ取得してキャッシュする。
実行: cd projects/ml && .venv/bin/python scripts/notes/logistic-regression_gen.py
確認した版: scikit-learn 1.9.1、NumPy 2.5.4、SciPy 1.18.1、matplotlib 3.11.2
"""
from io import BytesIO
from pathlib import Path
import warnings

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from sklearn.datasets import fetch_openml, load_breast_cancer
from sklearn.linear_model import LogisticRegression
from sklearn.calibration import calibration_curve
from sklearn.metrics import log_loss, roc_auc_score
from sklearn.model_selection import (GridSearchCV, StratifiedKFold, cross_val_predict, cross_validate,
                                     train_test_split)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

NOTE_DIR = Path(__file__).resolve().parents[2] / "notes" / "ml" / "logistic-regression"
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10,
                     "axes.spines.top": False, "axes.spines.right": False})
BLUE, RED, GREEN, INK, GRAY = "#7aa6c2", "#e15759", "#59a14f", "#333333", "#999999"
JP = {"preg": "妊娠回数", "plas": "血糖値", "mass": "BMI", "pedi": "家族歴の指標", "age": "年齢"}


def save(fig, name):
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight", facecolor="#ffffff")
    plt.close(fig)
    buf.seek(0)
    Image.open(buf).convert("RGB").save(NOTE_DIR / name, "WEBP", quality=90, method=6)


# ============================================================
# 実験 1: 血糖値だけで学習したロジスティック回帰
# ============================================================
pima = fetch_openml(data_id=37, as_frame=True).frame
pima = pima[(pima["plas"] > 0) & (pima["mass"] > 0)]  # 血糖値か BMI が 0 の 16 行は欠損なので除く
cols = ["preg", "plas", "mass", "pedi", "age"]
X = pima[cols].to_numpy(dtype=float)
y = (pima["class"] == "tested_positive").to_numpy(dtype=int)
print(f"{len(y)} 人、陽性 {y.sum()} 人（{y.mean():.4f}）")

one = LogisticRegression(C=np.inf).fit(X[:, [1]], y)  # 列は血糖値だけ、正則化なし
w, b = one.coef_[0, 0], one.intercept_[0]
print(f"w = {w:.4f}、b = {b:.3f}、p = 0.5 になる血糖値 {-b / w:.1f} mg/dL")
for g in [100, 140, 180]:
    z = w * g + b
    print(f"血糖値 {g}: z = {z:+.2f}、p = {1 / (1 + np.exp(-z)):.3f}")

rng = np.random.default_rng(0)
grid = np.linspace(40, 205, 300)
fig, ax = plt.subplots(figsize=(7.2, 3.8))
jit = rng.uniform(-0.04, 0.04, len(y))
ax.scatter(X[y == 0, 1], y[y == 0] + jit[y == 0], s=9, color=BLUE, alpha=0.45, label="陰性の人（0）")
ax.scatter(X[y == 1, 1], y[y == 1] + jit[y == 1], s=9, color=RED, alpha=0.45, label="陽性の人（1）")
ax.plot(grid, one.predict_proba(grid[:, None])[:, 1], color=INK, lw=2, label="学習した p")
ax.axhline(0.5, color=GRAY, lw=0.8, ls=":")
ax.axvline(-b / w, color=GRAY, lw=0.8, ls=":")
ax.text(-b / w + 2, 0.53, f"p = 0.5（血糖値 {-b / w:.0f}）", fontsize=9, color=INK)
ax.set_xlabel("血糖値（mg/dL、ブドウ糖を飲んで 2 時間後）")
ax.set_ylabel("糖尿病の陽性の確率 p")
ax.set_ylim(-0.08, 1.08)
ax.legend(loc="center left", fontsize=9, frameon=False)
ax.grid(True, alpha=0.25)
fig.tight_layout()
save(fig, "lr_sigmoid.webp")

# 2 列（血糖値と BMI）なら、p が同じになる所は平行な直線になる
two = LogisticRegression(C=np.inf).fit(X[:, [1, 2]], y)
(w_g, w_m), b2 = two.coef_[0], two.intercept_[0]
print(f"血糖値と BMI で学習: p = 0.5 の直線は 血糖値 = {-b2 / w_g:.1f} - {w_m / w_g:.2f} × BMI、"
      f"正解率 {two.score(X[:, [1, 2]], y):.3f}")
gg, mm = np.meshgrid(np.linspace(40, 205, 300), np.linspace(15, 70, 300))
pp = two.predict_proba(np.c_[gg.ravel(), mm.ravel()])[:, 1].reshape(gg.shape)
fig, ax = plt.subplots(figsize=(7.2, 4.4))
ax.scatter(X[y == 0, 1], X[y == 0, 2], s=9, color=BLUE, alpha=0.5, label="陰性の人")
ax.scatter(X[y == 1, 1], X[y == 1, 2], s=9, color=RED, alpha=0.5, label="陽性の人")
cs = ax.contour(gg, mm, pp, levels=[0.1, 0.3, 0.5, 0.7, 0.9], colors=INK,
                linewidths=[0.8, 0.8, 2.0, 0.8, 0.8], linestyles=[":", ":", "-", ":", ":"])
ax.clabel(cs, fmt=lambda v: f"p = {v:.1f}", fontsize=8.5)
ax.set_xlabel("血糖値（mg/dL）")
ax.set_ylabel("BMI")
ax.set_xlim(40, 205)
ax.set_ylim(15, 70)
ax.legend(loc="upper left", fontsize=9, frameon=False)
fig.tight_layout()
save(fig, "lr_boundary.webp")


# ============================================================
# 実験 2: ニュートン法で求める最尤推定
# ============================================================
Xa = np.column_stack([np.ones(len(X)), X])  # 先頭に切片の列 1 を足す
beta = np.zeros(Xa.shape[1])
for step in range(8):
    p = 1 / (1 + np.exp(-Xa @ beta))
    grad = Xa.T @ (p - y)                       # 負の対数尤度の勾配
    H = (Xa * (p * (1 - p))[:, None]).T @ Xa    # 2 回微分した行列（ヘッセ行列）
    beta -= np.linalg.solve(H, grad)
    nll = -np.sum(y * np.log(p) + (1 - y) * np.log(1 - p))
    print(f"{step + 1} 回目: 負の対数尤度 {nll:.4f}、勾配の大きさ {np.linalg.norm(grad):.1e}")
se = np.sqrt(np.diag(np.linalg.inv(H)))         # 係数の標準誤差

mle = LogisticRegression(C=np.inf, max_iter=10000).fit(X, y)  # 正則化なし
print("ニュートン法      :", beta.round(4))
print("C=np.inf の sklearn:", np.r_[mle.intercept_, mle.coef_[0]].round(4))
print("標準誤差          :", se.round(4))

units = {"preg": 1, "plas": 10, "mass": 5, "pedi": 0.5, "age": 10}
unit_label = {"preg": "1 回あたり", "plas": "10 mg/dL あたり", "mass": "5 あたり", "pedi": "0.5 あたり",
              "age": "10 歳あたり"}
unit_fig = unit_label
lib = LogisticRegression(solver="liblinear").fit(X, y)
fig, ax = plt.subplots(figsize=(8.6, 3.4))
for k, c in enumerate(cols):
    u = units[c]
    lo, mid, hi = np.exp((beta[k + 1] + np.array([-1.96, 0, 1.96]) * se[k + 1]) * u)
    yk = len(cols) - 1 - k
    ax.plot([lo, hi], [yk, yk], color=INK, lw=2)
    ax.plot(mid, yk, "o", color=INK, ms=7, label="最尤推定と 95% 信頼区間" if k == 0 else None)
    ax.plot(np.exp(lib.coef_[0, k] * u), yk, "D", color=RED, ms=7,
            label="liblinear（C=1.0）" if k == 0 else None)
    lib_or = np.exp(lib.coef_[0, k] * u)
    if lo <= lib_or <= hi:
        mark = "区間の中"
    elif lo - lib_or < 0.01:
        mark = "下限のすぐ外"  # 血糖値は 2 桁に丸めると 1.33 と 1.34 で差が見えにくいので 3 桁で示す
    else:
        mark = "区間の外"
    ax.text(1.03, yk, f"区間 {lo:.3f}〜{hi:.3f}、liblinear {lib_or:.3f}（{mark}）", va="center", fontsize=8.5,
            color=INK if mark == "区間の中" else RED, transform=ax.get_yaxis_transform(), clip_on=False)
    print(f"{JP[c]}（{unit_label[c]}）のオッズ比 {mid:.2f}（{lo:.2f}〜{hi:.2f}）、liblinear {lib_or:.2f}")
ax.axvline(1, color=GRAY, lw=0.8, ls=":")
ax.set_yticks(range(len(cols)))
ax.set_yticklabels([f"{JP[c]}（{unit_fig[c]}）" for c in cols][::-1])
ax.set_xscale("log")
ax.set_xticks([0.8, 1, 1.5, 2, 3])
ax.set_xticklabels(["0.8", "1", "1.5", "2", "3"])
ax.set_xlabel("オッズ比（対数目盛。1 より右は陽性のオッズを増やす）")
ax.legend(loc="lower right", fontsize=9, frameon=False)
ax.grid(True, axis="x", alpha=0.25)
fig.tight_layout()
save(fig, "lr_odds.webp")


# ============================================================
# 実験 3（冒頭）: 既定の lbfgs と liblinear の係数を最尤推定と比べる
# ============================================================
fits = {
    "正則化なし（C=np.inf）": LogisticRegression(C=np.inf, max_iter=10000),
    "既定（lbfgs、C=1.0）": LogisticRegression(max_iter=10000),
    "liblinear（C=1.0）": LogisticRegression(solver="liblinear"),
}
ratio = {}
for name, model in fits.items():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        model.fit(X, y)
    params = np.r_[model.coef_[0], model.intercept_]
    ratio[name] = params / np.r_[mle.coef_[0], mle.intercept_]
    print(f"{name:<20} 係数 {model.coef_[0].round(4)}、切片 {model.intercept_[0]:.3f}、"
          f"正解率 {model.score(X, y):.3f}、警告 {len(caught)} 件")
for name in list(fits)[1:]:
    print(f"{name} / 最尤推定（%）:", (ratio[name] * 100).round(1))

labels = [JP[c] for c in cols] + ["切片"]
fig, ax = plt.subplots(figsize=(7.6, 4.0))
pos = np.arange(len(labels))[::-1]
ax.barh(pos + 0.19, ratio["既定（lbfgs、C=1.0）"] * 100, height=0.36, color=BLUE, label="既定（lbfgs、C=1.0）")
ax.barh(pos - 0.19, ratio["liblinear（C=1.0）"] * 100, height=0.36, color=RED, label="solver=\"liblinear\"（C=1.0）")
for k in range(len(labels)):
    for off, name in [(0.19, "既定（lbfgs、C=1.0）"), (-0.19, "liblinear（C=1.0）")]:
        v = ratio[name][k] * 100
        x_text = 103 if v > 88 else v + 1.5  # 100% の点線に重ならないよう、点線の右に置く
        ax.text(x_text, pos[k] + off, f"{v:.1f}%", va="center", fontsize=8.5, color=INK)
ax.axvline(100, color=INK, lw=1, ls=":", label="正則化なしの最尤推定 = 100%")
ax.set_yticks(pos)
ax.set_yticklabels(labels)
ax.set_xlim(0, 118)
ax.set_xlabel("係数が最尤推定の何 % か（Pima の 752 人、5 列は元の単位のまま）")
ax.set_title("元の単位のまま渡すと、同じ C=1.0 でも liblinear の係数が大きく縮む", fontsize=10.5, loc="left")
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=3, fontsize=9, frameon=False)
ax.grid(True, axis="x", alpha=0.25)
fig.tight_layout()
save(fig, "lr_cover.webp")


# ============================================================
# 実験 4: C を動かした時の係数（元の単位と、標準化した後）
# ============================================================
Cs = np.logspace(-4, 2, 25)
paths = {"元の単位のまま": [], "標準化してから": []}
for C in Cs:
    raw = LogisticRegression(C=C, max_iter=10000).fit(X, y)
    paths["元の単位のまま"].append(raw.coef_[0] / mle.coef_[0])
    std = make_pipeline(StandardScaler(), LogisticRegression(C=C, max_iter=10000)).fit(X, y)
    coef = std[-1].coef_[0] / std[0].scale_           # 元の単位の係数に戻す
    paths["標準化してから"].append(coef / mle.coef_[0])
for C in [1.0, 0.01]:
    raw = LogisticRegression(C=C, max_iter=10000).fit(X, y)
    print(f"C={C}: 元の単位のまま / 最尤推定（%）", (raw.coef_[0] / mle.coef_[0] * 100).round(1))
print("列の標準偏差:", X.std(axis=0).round(2))
it_raw = LogisticRegression(max_iter=10000).fit(X, y).n_iter_[0]
it_std = make_pipeline(StandardScaler(), LogisticRegression(max_iter=10000)).fit(X, y)[-1].n_iter_[0]
print(f"C=1.0 で lbfgs が反復した回数: 元の単位のまま {it_raw} 回、標準化してから {it_std} 回")

colors = [BLUE, RED, GREEN, "#f28e2b", "#76716f"]
fig, axes = plt.subplots(1, 2, figsize=(10.5, 3.8), sharey=True)
for ax, (title, path) in zip(axes, paths.items()):
    path = np.array(path) * 100
    for k, c in enumerate(cols):
        ax.plot(Cs, path[:, k], color=colors[k], lw=2, label=JP[c])
    ax.axvline(1.0, color=INK, lw=0.8, ls=":")
    ax.text(1.15, 5, "既定の C=1.0", fontsize=8.5, color=INK)
    ax.set_xscale("log")
    ax.set_xlabel("C（左ほど正則化が強い）")
    ax.set_title(title, fontsize=10)
    ax.grid(True, alpha=0.25)
axes[0].set_ylabel("係数が最尤推定の何 % か")
axes[0].set_ylim(-5, max(np.max(paths["元の単位のまま"]), np.max(paths["標準化してから"])) * 100 + 15)
axes[1].legend(loc="upper left", bbox_to_anchor=(1.02, 1.0), fontsize=9, frameon=False)
fig.tight_layout()
save(fig, "lr_cpath.webp")

# 血糖値の単位を mg/dL から g/dL に変えるだけで、元の単位のままの列では予測の性能が落ちる
Xg = X.copy()
Xg[:, 1] /= 1000  # 血糖値を mg/dL から g/dL に直す（1 g/dL = 1000 mg/dL）
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=0)
for unit, data in [("mg/dL", X), ("g/dL", Xg)]:
    for name, model in [("元の単位のまま", make_pipeline(LogisticRegression(max_iter=10000))),
                        ("標準化してから", make_pipeline(StandardScaler(), LogisticRegression(max_iter=10000)))]:
        r = cross_validate(model, data, y, cv=cv, scoring=["roc_auc", "neg_log_loss"])
        model.fit(data, y)
        scale = model[0].scale_[1] if len(model) == 2 else 1.0
        ratio_plas = model[-1].coef_[0, 1] / scale / (mle.coef_[0, 1] * (1000 if unit == "g/dL" else 1))
        print(f"{unit:<5} {name}: 血糖値の係数 / 最尤推定 {ratio_plas * 100:5.1f}%、"
              f"交差検証の ROC-AUC {r['test_roc_auc'].mean():.3f}、log loss {-r['test_neg_log_loss'].mean():.3f}")
curves = {}
for label, data, std_on in [("mg/dL・元の単位のまま", X, False), ("g/dL・元の単位のまま", Xg, False),
                            ("標準化してから（どちらの単位も同じ）", Xg, True)]:
    steps = [StandardScaler()] if std_on else []
    search = GridSearchCV(make_pipeline(*steps, LogisticRegression(max_iter=10000)),
                          {"logisticregression__C": Cs}, cv=cv, scoring="neg_log_loss").fit(data, y)
    curves[label] = -search.cv_results_["mean_test_score"]
    print(f"{label}: 交差検証で選んだ C {search.best_params_['logisticregression__C']:.3g}、"
          f"log loss {-search.best_score_:.3f}")

fig, ax = plt.subplots(figsize=(7.2, 3.8))
for (label, curve), color, ls in zip(curves.items(), [BLUE, RED, INK], ["-", "-", "--"]):
    ax.plot(Cs, curve, color=color, lw=2, ls=ls, label=label)
ax.axvline(1.0, color=GRAY, lw=0.8, ls=":")
ax.text(0.85, 0.505, "既定の C=1.0", fontsize=8.5, color=INK, ha="right")
ax.set_xscale("log")
ax.set_xlabel("C（左ほど正則化が強い）")
ax.set_ylabel("交差検証の log loss（小さいほど良い）")
ax.legend(loc="upper right", fontsize=9, frameon=False)
ax.grid(True, alpha=0.25)
fig.tight_layout()
save(fig, "lr_unit.webp")


# ============================================================
# 実験 5: liblinear の切片と intercept_scaling
# ============================================================
lib = LogisticRegression(solver="liblinear").fit(X, y)
shift = (mle.coef_[0] - lib.coef_[0]) * X.mean(axis=0)  # 係数が縮んで下がった z（全員の平均）
print(f"切片が上がった量: {lib.intercept_[0] - mle.intercept_[0]:.3f}")
print("係数が縮んで下がった z:", dict(zip(cols, shift.round(2).tolist())), f"合計 {shift.sum():.2f}")
for name, m in [("最尤推定", mle), ("liblinear", lib)]:
    print(f"{name}: 0.5 * (切片^2 + 係数^2 の和) = {0.5 * (m.intercept_[0] ** 2 + np.sum(m.coef_ ** 2)):.1f}")

settings = {}
for s in [1, 10, 100]:
    m = LogisticRegression(solver="liblinear", intercept_scaling=s).fit(X, y)
    settings[f"intercept_scaling={s}"] = np.r_[m.coef_[0], m.intercept_]
m = make_pipeline(StandardScaler(), LogisticRegression(solver="liblinear")).fit(X, y)
sc, lr = m[0], m[-1]
coef = lr.coef_[0] / sc.scale_                                  # 元の単位に戻す
icpt = lr.intercept_[0] - np.sum(lr.coef_[0] * sc.mean_ / sc.scale_)
settings["標準化してから"] = np.r_[coef, icpt]
base = np.r_[mle.coef_[0], mle.intercept_]
for name, v in settings.items():
    print(f"liblinear {name:<20} / 最尤推定（%）:", (v / base * 100).round(1))

share = {}
for sc_val in [1, 10, 100]:
    m = LogisticRegression(solver="liblinear", intercept_scaling=sc_val).fit(X, y)
    w0 = m.intercept_[0] / sc_val                                 # 足した列の係数
    share[sc_val] = (0.5 * w0 ** 2, 0.5 * np.sum(m.coef_ ** 2))
    print(f"intercept_scaling={sc_val:<3}: 足した列の係数 {w0:8.4f}、切片に掛かる分 {share[sc_val][0]:.4f}、"
          f"係数に掛かる分 {share[sc_val][1]:.4f}")

fig, ax = plt.subplots(figsize=(7.2, 3.6))
xs = np.arange(3)
ax.bar(xs - 0.18, [share[v][0] for v in [1, 10, 100]], width=0.36, color=RED, label="切片に掛かる分 0.5 × w0²")
ax.bar(xs + 0.18, [share[v][1] for v in [1, 10, 100]], width=0.36, color=BLUE, label="5 列の係数に掛かる分")
for i, v in enumerate([1, 10, 100]):
    ax.text(i - 0.18, share[v][0] * 1.3, f"{share[v][0]:.3g}", ha="center", fontsize=8.5, color=RED)
    ax.text(i + 0.18, share[v][1] * 1.3, f"{share[v][1]:.2f}", ha="center", fontsize=8.5, color=BLUE)
    age = settings[f"intercept_scaling={v}"][4] / base[4] * 100
    ax.text(i, 200, f"年齢の係数 {age:.1f}%", ha="center", fontsize=9, color=INK)
ax.set_yscale("log")
ax.set_ylim(1e-3, 600)
ax.set_xticks(xs)
ax.set_xticklabels(["intercept_scaling=1（既定）", "10", "100"])
ax.set_ylabel("ペナルティ 0.5 × 係数² の和（対数目盛）")
ax.legend(loc="upper right", bbox_to_anchor=(1.0, 0.86), fontsize=9, frameon=False)
ax.grid(True, axis="y", alpha=0.25)
fig.tight_layout()
save(fig, "lr_scaling.webp")


# 足した列の係数がペナルティを受ける仕組みの図
fig, axes = plt.subplots(1, 2, figsize=(11.0, 3.4))
for ax, (title, extra) in zip(axes, [("lbfgs など", False), ("liblinear", True)]):
    ax.set_xlim(0, 16.5)
    ax.set_ylim(0.6, 5.6)
    ax.axis("off")
    ax.set_title(title, fontsize=11, loc="left")
    names = ["妊娠回数", "血糖値", "BMI", "家族歴", "年齢"] + (["s"] if extra else [])
    for j, nm in enumerate(names):
        x0 = 0.2 + j * 1.45
        face = "#fde2e2" if nm == "s" else "#eef3f7"
        ax.add_patch(plt.Rectangle((x0, 2.0), 1.35, 2.6, facecolor=face, edgecolor=INK, lw=0.8))
        ax.text(x0 + 0.675, 4.85, nm, ha="center", fontsize=7.5, color=RED if nm == "s" else INK)
        if nm == "s":
            ax.text(x0 + 0.675, 3.3, "s\ns\ns\ns", ha="center", va="center", fontsize=9, color=RED)
        wn = "w0" if nm == "s" else f"w{j + 1}"
        ax.text(x0 + 0.675, 1.5, wn, ha="center", fontsize=9.5, color=RED if nm == "s" else INK)
    ax.text(0.2, 0.8, "X の列（752 行）と、その下は列ごとの係数", fontsize=8.5, color=GRAY)
    tx = 9.2 if extra else 7.8
    if extra:
        ax.text(tx, 4.85, "s: 値が一定の列（intercept_scaling、既定 1）", fontsize=9, color=RED)
        ax.text(tx, 4.0, "切片 b = s × w0", fontsize=10, color=INK)
        ax.text(tx, 3.2, "ペナルティ = 0.5 ×（w1² + … + w5² + w0²）", fontsize=9, color=INK)
        ax.text(tx, 2.4, f"s = 1 なら w0 = b。最尤推定の b = {mle.intercept_[0]:.2f} では", fontsize=9, color=INK)
        ax.text(tx, 1.7, f"切片だけで 0.5 × ({mle.intercept_[0]:.2f})² = {0.5 * mle.intercept_[0] ** 2:.1f}",
                fontsize=9, color=RED)
    else:
        ax.text(tx, 4.0, "切片 b は列とは別に持つ", fontsize=10, color=INK)
        ax.text(tx, 3.2, "ペナルティ = 0.5 ×（w1² + … + w5²）", fontsize=9, color=INK)
        ax.text(tx, 2.4, "b はペナルティに入らない", fontsize=9, color=INK)
fig.tight_layout()
save(fig, "lr_intercept_col.webp")


# ============================================================
# 実験 6: 学習データでの確率の平均
# ============================================================
models = {
    "正則化なし（C=np.inf）": LogisticRegression(C=np.inf, max_iter=10000),
    "既定（lbfgs、C=1.0）": LogisticRegression(max_iter=10000),
    "lbfgs、C=0.01": LogisticRegression(C=0.01, max_iter=10000),
    "liblinear（C=1.0）": LogisticRegression(solver="liblinear"),
    "class_weight=\"balanced\"": LogisticRegression(class_weight="balanced", max_iter=10000),
}
print(f"陽性の割合                 : {y.mean():.4f}")
for name, model in models.items():
    p = model.fit(X, y).predict_proba(X)[:, 1]
    print(f"{name:<26} : 確率の平均 {p.mean():.4f}、正解率 {model.score(X, y):.3f}")

# 標準化した列で C を小さくすると、平均は合ったまま確率が平均の側へ縮む
calib = {}
for C in [1.0, 0.01]:
    m = make_pipeline(StandardScaler(), LogisticRegression(C=C)).fit(X, y)
    p = m.predict_proba(X)[:, 1]
    frac, mean_p = calibration_curve(y, p, n_bins=5, strategy="quantile")  # 確率の低い順に 5 等分
    calib[C] = (mean_p, frac)
    print(f"標準化、C={C}: 確率の平均 {p.mean():.4f}、正解率 {m.score(X, y):.3f}、"
          f"ROC-AUC {roc_auc_score(y, p):.3f}、log loss {log_loss(y, p):.3f}")
    print("  区間ごとの確率の平均:", mean_p.round(2), "/ 実際に陽性の割合:", frac.round(2))
    q = cross_val_predict(m, X, y, cv=cv, method="predict_proba")[:, 1]  # 学習に使っていない人の確率
    frac_cv, mean_cv = calibration_curve(y, q, n_bins=5, strategy="quantile")
    print("  交差検証の確率の平均:", mean_cv.round(2), "/ 実際に陽性の割合:", frac_cv.round(2),
          f"/ log loss {log_loss(y, q):.3f}")

fig, ax = plt.subplots(figsize=(5.6, 5.0))
ax.plot([0, 1], [0, 1], color=GRAY, lw=0.8, ls=":", label="確率と実際の割合が一致")
for C, color, mk in [(1.0, BLUE, "o"), (0.01, RED, "s")]:
    mean_p, frac = calib[C]
    ax.plot(mean_p, frac, color=color, lw=2, marker=mk, label=f"C={C}（標準化）")
    for a, f in zip(mean_p, frac):
        if C == 0.01 and (a < 0.2 or a > 0.6):
            ax.annotate(f"確率 {a:.2f}\n実際 {f:.2f}", (a, f), textcoords="offset points",
                        xytext=(12, -4) if a < 0.2 else (-70, 6), fontsize=8.5, color=RED)
ax.set_xlabel("区間ごとの確率の平均（確率の低い順に 5 等分）")
ax.set_ylabel("区間で実際に陽性だった割合")
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.set_aspect("equal")
ax.legend(loc="upper left", fontsize=9, frameon=False)
ax.grid(True, alpha=0.25)
fig.tight_layout()
save(fig, "lr_calib.webp")


# ============================================================
# 実験 7: 完全に分けられるデータで、正則化を外す
# ============================================================
bc = load_breast_cancer()
X_tr, X_te, y_tr, y_te = train_test_split(bc.data, bc.target, test_size=0.3,
                                          random_state=0, stratify=bc.target)
scaler = StandardScaler().fit(X_tr)
X_tr, X_te = scaler.transform(X_tr), scaler.transform(X_te)
tols = [1e-4, 1e-6, 1e-8, 1e-10, 1e-12]
norm = {"lbfgs": [], "newton-cg": []}
for solver in norm:
    for tol in tols:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            m = LogisticRegression(C=np.inf, solver=solver, tol=tol, max_iter=100000).fit(X_tr, y_tr)
        norm[solver].append(np.linalg.norm(m.coef_))
        print(f"{solver:<9} tol={tol:.0e}: 係数の長さ {norm[solver][-1]:7.1f}、学習の正解率 {m.score(X_tr, y_tr):.3f}、"
              f"テストの正解率 {m.score(X_te, y_te):.3f}、テストの log loss {log_loss(y_te, m.predict_proba(X_te)):.3f}、"
              f"警告 {len(caught)} 件")
m1 = LogisticRegression().fit(X_tr, y_tr)
print(f"既定の C=1.0    : 係数の長さ {np.linalg.norm(m1.coef_):7.1f}、学習の正解率 {m1.score(X_tr, y_tr):.3f}、"
      f"テストの正解率 {m1.score(X_te, y_te):.3f}、テストの log loss {log_loss(y_te, m1.predict_proba(X_te)):.3f}")

fig, ax = plt.subplots(figsize=(7.2, 3.6))
ax.plot(tols, norm["lbfgs"], "o-", color=RED, lw=2, label="C=np.inf、solver=\"lbfgs\"（既定）")
ax.plot(tols, norm["newton-cg"], "s-", color="#f28e2b", lw=2, label="C=np.inf、solver=\"newton-cg\"")
ax.axhline(np.linalg.norm(m1.coef_), color=BLUE, lw=2, label="既定の C=1.0（tol に依らない）")
for t, v in zip(tols, norm["lbfgs"]):
    ax.text(t, v * 1.18, f"{v:.0f}", ha="center", fontsize=8.5, color=RED)
for t, v in zip(tols, norm["newton-cg"]):
    ax.text(t, v * 0.68, f"{v:.0f}", ha="center", fontsize=8.5, color="#f28e2b")
ax.set_xscale("log")
ax.set_yscale("log")
ax.invert_xaxis()
ax.set_xlabel("tol（右ほど厳しい）")
ax.set_ylabel("30 個の係数の長さ")
ax.set_ylim(1, 5000)
ax.legend(loc="lower right", fontsize=9, frameon=True, bbox_to_anchor=(1.0, 0.27))
ax.grid(True, alpha=0.25)
fig.tight_layout()
save(fig, "lr_separation.webp")


# ============================================================
# 実験 8: 行が少ない時の係数
# ============================================================
Xs = StandardScaler().fit_transform(X)
full = np.linalg.norm(LogisticRegression(C=np.inf).fit(Xs, y).coef_)
rng = np.random.default_rng(0)
sizes = [40, 80, 160, 320]
res = {"正則化なし（C=np.inf）": [], "既定（C=1.0）": []}
for n in sizes:
    r = {k: [] for k in res}
    for _ in range(300):
        i = rng.choice(len(y), n, replace=False)       # 752 人から n 人を選ぶ
        for name, C in [("正則化なし（C=np.inf）", np.inf), ("既定（C=1.0）", 1.0)]:
            coef = LogisticRegression(C=C, max_iter=1000).fit(Xs[i], y[i]).coef_
            r[name].append(np.linalg.norm(coef) / full)
    for name in res:
        res[name].append(np.percentile(r[name], [10, 50, 90]))
        print(f"{n:>3} 人、{name:<14}: 係数の長さ / 752 人の最尤推定 "
              f"中央値 {np.median(r[name]):.2f}、90% 点 {np.percentile(r[name], 90):.2f}")

fig, ax = plt.subplots(figsize=(7.2, 3.6))
for name, c, off in [("正則化なし（C=np.inf）", RED, -0.03), ("既定（C=1.0）", BLUE, 0.03)]:
    q = np.array(res[name])
    xs_n = np.array(sizes) * (1 + off)
    ax.fill_between(xs_n, q[:, 0], q[:, 2], color=c, alpha=0.15)
    ax.plot(xs_n, q[:, 1], "o-", color=c, lw=2, label=f"{name}の中央値（帯は 10〜90% 点）")
    for xn, v in zip(xs_n, q[:, 1]):
        ax.text(xn * (1 if c == RED else 1.05), v + (0.07 if c == RED else -0.15), f"{v:.2f}", ha="center", fontsize=8.5, color=c)
ax.axhline(1, color=INK, lw=1, ls=":", label="752 人の最尤推定（= 1）")
ax.set_xscale("log")
ax.set_xticks(sizes)
ax.set_xticklabels([str(n) for n in sizes])
ax.xaxis.set_minor_formatter(plt.NullFormatter())
ax.set_xlabel("学習に使った人数（300 回選び直す）")
ax.set_ylabel("係数の長さ（752 人の最尤推定 = 1）")
ax.legend(loc="upper right", fontsize=9, frameon=False)
ax.grid(True, alpha=0.25)
fig.tight_layout()
save(fig, "lr_small_n.webp")
