"""convex-functions ノートの実験と図を生成するスクリプト。

本文に載せた実験（同じ列が 2 本ある diabetes の Lasso と Elastic Net、弦で凸かどうかを数える、
seed を変えた MLP、ヘッセ行列の固有値と谷の断面、学習率と勾配降下法）を同じ順に実行し、
出力を標準出力に、図を Page Bundle に WebP で保存する。
実行: cd projects/ml && .venv/bin/python scripts/notes/convex-functions_gen.py
確認した版: scikit-learn 1.9.1、NumPy 2.5.4、matplotlib 3.11.2
"""
import warnings
from io import BytesIO
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from sklearn.datasets import load_diabetes
from sklearn.linear_model import ElasticNet, Lasso
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler

NOTE_DIR = Path(__file__).resolve().parents[2] / "notes" / "math" / "convex-functions"
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10,
                     "axes.spines.top": False, "axes.spines.right": False})
BLUE, RED, GREEN, INK, GRAY = "#7aa6c2", "#e15759", "#59a14f", "#333333", "#999999"


def save(fig, name):
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight", facecolor="#ffffff")
    plt.close(fig)
    buf.seek(0)
    Image.open(buf).convert("RGB").save(NOTE_DIR / name, "WEBP", quality=90, method=6)


# ============================================================
# 実験 1: 同じ列が 2 本ある時の Lasso と Elastic Net
# ============================================================
d = load_diabetes(as_frame=True)
X = d.data.copy()
y = d.target.to_numpy()
X["bmi_copy"] = X["bmi"] * 10 + 3          # 同じ量を別の単位で記録した列
Xs = StandardScaler().fit_transform(X)     # 標準化すると bmi と bmi_copy は同じ値になる
n = len(y)
i_bmi, i_copy = X.columns.get_loc("bmi"), X.columns.get_loc("bmi_copy")
print("bmi と bmi_copy の差の最大:", np.abs(Xs[:, i_bmi] - Xs[:, i_copy]).max())


def lasso_obj(m, alpha=1.0):
    return ((y - m.predict(Xs)) ** 2).sum() / (2 * n) + alpha * np.abs(m.coef_).sum()


def enet_obj(m, alpha=1.0, l1_ratio=0.9):
    w = m.coef_
    return (((y - m.predict(Xs)) ** 2).sum() / (2 * n)
            + alpha * l1_ratio * np.abs(w).sum() + 0.5 * alpha * (1 - l1_ratio) * (w ** 2).sum())


res = {"Lasso": [], "ElasticNet": []}
for seed in range(100):
    las = Lasso(alpha=1.0, selection="random", random_state=seed, tol=1e-10, max_iter=100000).fit(Xs, y)
    en = ElasticNet(alpha=1.0, l1_ratio=0.9, selection="random", random_state=seed,
                    tol=1e-10, max_iter=100000).fit(Xs, y)
    res["Lasso"].append((las.coef_[i_bmi], las.coef_[i_copy], lasso_obj(las)))
    res["ElasticNet"].append((en.coef_[i_bmi], en.coef_[i_copy], enet_obj(en)))
for name, r in res.items():
    r = np.array(r)
    res[name] = r
    print(f"{name:<10} bmi の係数 {r[:, 0].min():6.2f}〜{r[:, 0].max():6.2f}  "
          f"bmi_copy の係数 {r[:, 1].min():6.2f}〜{r[:, 1].max():6.2f}  "
          f"2 本の和 {(r[:, 0] + r[:, 1]).min():.4f}〜{(r[:, 0] + r[:, 1]).max():.4f}  "
          f"目的関数 {r[:, 2].min():.9f}〜{r[:, 2].max():.9f}")

# ここから図のためだけの処理（本文には載せない）。
# 2 本以外の係数を解に固定し、2 本の係数だけを動かした時の目的関数を描く。
def grid_obj(model, objf, W1, W2):
    base = model.coef_.copy()
    Z = np.empty_like(W1)
    for idx in np.ndindex(W1.shape):
        w = base.copy()
        w[i_bmi], w[i_copy] = W1[idx], W2[idx]
        resid = y - (Xs @ w + model.intercept_)
        if objf == "lasso":
            Z[idx] = (resid ** 2).sum() / (2 * n) + np.abs(w).sum()
        else:
            Z[idx] = (resid ** 2).sum() / (2 * n) + 0.9 * np.abs(w).sum() + 0.05 * (w ** 2).sum()
    return Z


las0 = Lasso(alpha=1.0, tol=1e-10, max_iter=100000).fit(Xs, y)
en0 = ElasticNet(alpha=1.0, l1_ratio=0.9, tol=1e-10, max_iter=100000).fit(Xs, y)
g = np.linspace(-8, 33, 161)
W1, W2 = np.meshgrid(g, g)
fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.9))
for ax, name, model, objf in [(axes[0], "Lasso", las0, "lasso"), (axes[1], "ElasticNet", en0, "enet")]:
    Z = grid_obj(model, objf, W1, W2)
    zmin = Z.min()
    ax.contourf(W1, W2, Z - zmin, levels=[0, 2, 8, 20, 40, 70, 110, 160, 220], cmap="Greys_r", alpha=0.55)
    ax.contour(W1, W2, Z - zmin, levels=[2, 8, 20, 40, 70, 110, 160], colors="#777777", linewidths=0.6)
    r = res[name]
    color = RED if name == "Lasso" else BLUE
    ax.scatter(r[:, 0], r[:, 1], s=22, color=color, edgecolor="white", linewidth=0.5, zorder=3,
               label="seed を変えた 100 回の解")
    if name == "Lasso":
        s = r[0, 0] + r[0, 1]
        ax.plot([0, s], [s, 0], color=RED, lw=1, ls="--", zorder=2)
        ax.set_title(f"Lasso: 2 本の係数は 0〜{s:.1f} に散らばる\n目的関数の値は 100 回とも同じ", fontsize=10)
    else:
        ax.set_title(f"Elastic Net: 100 回とも 1 点に集まる\nbmi {r[0, 0]:.2f}、bmi_copy {r[0, 1]:.2f}", fontsize=10)
    ax.set_xlabel("bmi の係数")
    ax.set_ylabel("bmi_copy の係数")
    ax.set_aspect("equal")
    ax.legend(loc="upper right", fontsize=9)
fig.tight_layout()
save(fig, "cvx_cover.webp")


# ============================================================
# 実験 2: 2 点を選び、弦が関数の上にあるかを数える
# ============================================================
funcs = {
    "w²": lambda w: w ** 2,
    "|w|": lambda w: np.abs(w),
    "底が平ら": lambda w: np.maximum(np.abs(w) - 1, 0) ** 2,
    "谷が 2 つ": lambda w: w ** 4 - 2 * w ** 2 + 0.3 * w,
}
rng = np.random.default_rng(0)
a, b = rng.uniform(-2, 2, 10000), rng.uniform(-2, 2, 10000)  # 弦の両端
t = rng.uniform(0.05, 0.95, 10000)                             # 両端の間のどこを見るか
for name, f in funcs.items():
    curve = f(t * a + (1 - t) * b)
    chord = t * f(a) + (1 - t) * f(b)
    below = (curve > chord + 1e-12).sum()          # 弦が関数より下に来た組
    touch = (np.isclose(curve, chord, atol=1e-9) & (np.abs(a - b) > 0.1)).sum()  # 弦が関数に重なった組
    print(f"{name:<6} 弦が下: {below:5d} 組  弦が重なる: {touch:5d} 組（10000 組中）")

# ここから図のためだけの処理（本文には載せない）。
fig, axes = plt.subplots(1, 4, figsize=(12, 3.3))
ws = np.linspace(-2, 2, 400)
chords = {"w²": (-1.6, 1.0), "|w|": (0.4, 1.7), "底が平ら": (-0.8, 0.6), "谷が 2 つ": (-1.0, 0.95)}
titles = {"w²": "w²: 狭義凸\n最小の点は 1 つ", "|w|": "|w|: 凸（0 で尖る）\n最小の点は 1 つ",
          "底が平ら": "底が平ら: 凸\n最小の点が区間に広がる", "谷が 2 つ": "谷が 2 つ: 凸でない\n局所最小が 2 つ"}
for ax, (name, f) in zip(axes, funcs.items()):
    ax.plot(ws, f(ws), color=INK, lw=1.6)
    p, q = chords[name]
    bad = name == "谷が 2 つ"
    ax.plot([p, q], [f(p), f(q)], color=RED if bad else BLUE, lw=1.6, marker="o", ms=4,
            label="弦が関数より下" if bad else "弦")
    if name == "底が平ら":
        ax.plot([-1, 1], [0, 0], color=GREEN, lw=4, alpha=0.8, label="最小の点")
    elif name == "谷が 2 つ":
        for m0 in [-1.03, 0.96]:
            ax.plot(m0, f(m0), "o", color=GREEN, ms=6)
        ax.plot([], [], "o", color=GREEN, label="局所最小")
    else:
        ax.plot(0, 0, "o", color=GREEN, ms=6, label="最小の点")
    ax.set_title(titles[name], fontsize=10)
    ax.set_xlabel("w")
    ax.legend(loc="upper center", fontsize=8)
    ax.grid(True, alpha=0.25)
    ax.set_ylim(min(f(ws).min() - 0.3, -0.3), f(ws).max() * 1.25 + 0.3)
fig.tight_layout()
save(fig, "cvx_shapes.webp")


# ============================================================
# 実験 3: seed を変えて、止まった所の目的関数を比べる
# ============================================================
X0 = StandardScaler().fit_transform(d.data)     # 元の 10 列
mlp_loss, iters = [], []
for seed in range(20):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        m = MLPRegressor(hidden_layer_sizes=(10,), solver="lbfgs", max_iter=20000,
                         random_state=seed).fit(X0, y)
    mlp_loss.append(m.loss_)                    # 二乗誤差の半分の平均 + L2 のペナルティ
    iters.append(m.n_iter_)
mlp_loss = np.array(mlp_loss)
print("MLP の反復回数の最大:", max(iters), "（上限 20000）")
las_obj = res["Lasso"][:, 2]
for name, v in [("Lasso（100 回）", las_obj), ("MLP（20 回）", mlp_loss)]:
    gap = (v - v.min()) / v.min() * 100
    print(f"{name:<12} 最小 {v.min():9.3f}  最大 {v.max():9.3f}  最小との差の最大 {gap.max():.2e} %")

# ここから図のためだけの処理（本文には載せない）。
fig, ax = plt.subplots(figsize=(7.6, 3.4))
for k, (name, v, color) in enumerate([("Lasso\n（凸、seed 100 個）", las_obj, RED),
                                      ("MLP 隠れ層 10\n（凸でない、seed 20 個）", mlp_loss, BLUE)]):
    gap = (v - v.min()) / v.min() * 100
    jitter = np.random.default_rng(k).uniform(-0.12, 0.12, len(v))
    ax.scatter(gap, k + jitter, s=26, color=color, edgecolor="white", linewidth=0.5)
    ax.text(gap.max() + 0.4, k, f"最大 {gap.max():.1f} %" if gap.max() > 0.01 else "最大 0.0 %",
            va="center", fontsize=9, color=INK)
ax.set_yticks([0, 1])
ax.set_yticklabels(["Lasso\n（凸、seed 100 個）", "MLP 隠れ層 10\n（凸でない、seed 20 個）"])
ax.set_xlabel("止まった所の目的関数が、一番低い seed より何 % 高いか")
ax.set_ylim(-0.6, 1.6)
ax.grid(True, axis="x", alpha=0.25)
fig.tight_layout()
save(fig, "cvx_seeds.webp")


# ============================================================
# 実験 4: ヘッセ行列の固有値と、谷の断面
# ============================================================
H = Xs.T @ Xs / n                               # 二乗誤差の項 (1/2n)|y - Xw|^2 のヘッセ行列
eigvals, eigvecs = np.linalg.eigh(H)            # 昇順
print("固有値（小さい順に 3 つ）:", np.round(eigvals[:3], 6))
v0 = eigvecs[:, 0]
print("一番小さい固有値の固有ベクトルで 0.1 以上の成分:",
      {c: round(float(x), 3) for c, x in zip(X.columns, v0) if abs(x) > 0.1})
print("Elastic Net の L2 の項がヘッセ行列に足す値 alpha × (1 - l1_ratio) =", round(1.0 * (1 - 0.9), 3))

# ここから図のためだけの処理（本文には載せない）。
fig, axes = plt.subplots(1, 2, figsize=(11, 3.9))
ax = axes[0]
idx = np.arange(1, len(eigvals) + 1)
colors = [RED if k == 0 else BLUE for k in range(len(eigvals))]
ax.bar(idx, eigvals, color=colors)
ax.bar(idx, [0.1] * len(eigvals), bottom=eigvals, color=GREEN, alpha=0.6,
       label="Elastic Net が足す 0.1")
ax.set_yscale("symlog", linthresh=0.01)
ax.set_xticks(idx)
ax.set_xticklabels([f"{k}" for k in idx])
ax.set_xlabel("固有値の番号（小さい順）")
ax.set_ylabel("固有値")
ax.text(1, 0.004, "ほぼ 0", ha="center", fontsize=8, color=RED)
ax.set_title("ヘッセ行列 X^T X / n の固有値", fontsize=10)
ax.legend(loc="upper left", fontsize=9)
ax = axes[1]
s_tot = res["Lasso"][0, 0] + res["Lasso"][0, 1]
ss = np.linspace(-12, s_tot + 12, 300)
for model, objf, color, label in [(las0, "lasso", RED, "Lasso"), (en0, "enet", BLUE, "Elastic Net")]:
    tot = model.coef_[i_bmi] + model.coef_[i_copy]
    vals = grid_obj(model, objf, ss.reshape(1, -1), (tot - ss).reshape(1, -1))[0]
    ax.plot(ss, vals - vals.min(), color=color, lw=1.8, label=f"{label}（2 本の和は {tot:.2f}）")
ax.axvspan(0, s_tot, color=RED, alpha=0.08)
ax.set_xlabel("2 本の和を保ったまま bmi に配る係数")
ax.set_ylabel("目的関数 − 最小値")
ax.set_ylim(-1, 30)
ax.set_title("2 本の係数を (1, −1) の向きに動かした断面", fontsize=10)
ax.legend(loc="upper center", fontsize=9)
ax.grid(True, alpha=0.25)
fig.tight_layout()
save(fig, "cvx_hessian.webp")


# ============================================================
# 実験 5: 勾配降下法の学習率と、ヘッセ行列の一番大きい固有値
# ============================================================
L = eigvals[-1]
Xc, yc = Xs, y - y.mean()                       # 切片は平均で決まるので、y から平均を引いて外す
w_ls = np.linalg.lstsq(Xc, yc, rcond=None)[0]
f_min = ((yc - Xc @ w_ls) ** 2).sum() / (2 * n)
curves = {}
for k in [1.0, 1.9, 2.05]:
    lr, w, hist = k / L, np.zeros(Xc.shape[1]), []
    for _ in range(300):
        w -= lr * Xc.T @ (Xc @ w - yc) / n      # 勾配は X^T (Xw - y) / n
        hist.append(((yc - Xc @ w) ** 2).sum() / (2 * n) - f_min)
    curves[k] = np.array(hist)
    print(f"学習率 {k:4.2f}/L = {lr:.3f}: 10 回目 {hist[9]:.3e}  300 回目 {hist[-1]:.3e}  "
          f"bmi {w[i_bmi]:.3g}  bmi_copy {w[i_copy]:.3g}")
print(f"L（一番大きい固有値）= {L:.3f}、2/L = {2 / L:.3f}")

# ここから図のためだけの処理（本文には載せない）。
fig, ax = plt.subplots(figsize=(7.6, 3.8))
for k, color in [(1.0, GREEN), (1.9, BLUE), (2.05, RED)]:
    ax.plot(np.arange(1, 301), curves[k], color=color, lw=1.8, label=f"学習率 {k:.2f} / L")
ax.set_yscale("log")
ax.set_xlabel("更新の回数")
ax.set_ylabel("目的関数 − 最小値")
ax.set_title(f"同じ凸の目的関数でも、学習率が 2 / L（{2 / L:.3f}）を超えると発散する", fontsize=10)
ax.legend(loc="center right", fontsize=9)
ax.grid(True, alpha=0.25)
fig.tight_layout()
save(fig, "cvx_lr.webp")


# ============================================================
# 図 6: 制約 x ≤ 1 のもとで (x - 2)² を最小にする（図だけ）
# ============================================================
xs = np.linspace(-1, 4, 400)
fig, ax = plt.subplots(figsize=(7.2, 3.6))
ax.axvspan(-1, 1, color=BLUE, alpha=0.15, label="制約 x ≤ 1 を満たす範囲")
ax.plot(xs, (xs - 2) ** 2, color=INK, lw=1.8, label="(x − 2)²")
ax.plot(2, 0, "o", color=GRAY, ms=7, label="制約が無い時の最小（x = 2、微分 0）")
ax.plot(1, 1, "o", color=RED, ms=8, label="制約がある時の最小（x = 1、微分 −2）")
ax.plot([0.3, 1.7], [1 + (-2) * (0.3 - 1), 1 + (-2) * (1.7 - 1)], color=RED, lw=1.2, ls="--")
ax.annotate("", xy=(1.55, 1.0), xytext=(1.0, 1.0),
            arrowprops=dict(arrowstyle="->", color=RED, lw=1.6))
ax.text(1.6, 1.15, "下がる向きは\n制約の外", color=RED, fontsize=9)
ax.set_xlabel("x")
ax.set_ylabel("(x − 2)²")
ax.set_xlim(-1, 4)
ax.set_ylim(-0.3, 9.5)
ax.legend(loc="upper right", fontsize=8.5)
ax.grid(True, alpha=0.25)
fig.tight_layout()
save(fig, "cvx_constraint.webp")
