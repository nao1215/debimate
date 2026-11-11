"""svm ノートの実験と図を生成するスクリプト。

本文に載せた実験（マージン、C、カーネルと γ、学習時間、LinearSVC の切片、確率、他の手法との比較）を
本文と同じ順に実行し、出力を標準出力に、図を Page Bundle に WebP で保存する。
実行: cd projects/ml && .venv/bin/python scripts/notes/svm_gen.py
確認した版: scikit-learn 1.9.1、NumPy 2.5.4、matplotlib 3.11.2
学習時間は threadpoolctl で 1 スレッドに絞って測る（LIBSVM は 1 スレッドで動くため、揃える）。
学習時間は、他の処理と並行して動いていた PC（32 コア、load average 15 前後）で 2026-11-12 に測った値を
RECORDED に残し、既定ではそれで図を描く。測り直す時は SVM_MEASURE=1 を付けて実行する。
"""
import os
import time
import warnings
from io import BytesIO
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
from PIL import Image
from sklearn.datasets import (load_breast_cancer, load_digits, load_wine, make_blobs,
                              make_circles, make_classification, make_moons)
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC, LinearSVC
from threadpoolctl import threadpool_limits

# SVC(probability=True) は 1.9 で非推奨になり、毎回 FutureWarning が出る。本文で触れるので出力からは消す
warnings.filterwarnings("ignore", category=FutureWarning)

NOTE_DIR = Path(__file__).resolve().parents[2] / "notes" / "ml" / "svm"
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10,
                     "axes.spines.top": False, "axes.spines.right": False})
BLUE, RED, GREEN, INK, GRAY = "#7aa6c2", "#e15759", "#59a14f", "#333333", "#999999"


def save(fig, name):
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight", facecolor="#ffffff")
    plt.close(fig)
    buf.seek(0)
    Image.open(buf).convert("RGB").save(NOTE_DIR / name, "WEBP", quality=90, method=6)


def draw_margin(ax, model, X, y, title):
    """決定境界（実線）、マージン（破線）、サポートベクター（黒丸）を描く。"""
    xx, yy = np.meshgrid(np.linspace(X[:, 0].min() - 0.5, X[:, 0].max() + 0.5, 300),
                         np.linspace(X[:, 1].min() - 0.5, X[:, 1].max() + 0.5, 300))
    Z = model.decision_function(np.c_[xx.ravel(), yy.ravel()]).reshape(xx.shape)
    ax.contourf(xx, yy, Z, levels=[-1e9, 0, 1e9], alpha=0.12, colors=[BLUE, RED])
    ax.contour(xx, yy, Z, levels=[-1, 0, 1], colors=INK, linestyles=["--", "-", "--"],
               linewidths=[1, 1.6, 1])
    ax.scatter(X[y == 0, 0], X[y == 0, 1], s=28, color=BLUE, edgecolor="white", label="クラス 0")
    ax.scatter(X[y == 1, 0], X[y == 1, 1], s=28, color=RED, edgecolor="white", label="クラス 1")
    sv = model.support_vectors_
    ax.scatter(sv[:, 0], sv[:, 1], s=110, facecolors="none", edgecolors=INK, linewidths=1.4,
               label=f"サポートベクター（{len(sv)} 点）")
    ax.set_title(title)
    ax.set_xlabel("x1")
    ax.set_ylabel("x2")


cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=0)

# ---- 実験 1: マージンとサポートベクター ----
X, y = make_blobs(n_samples=80, centers=2, cluster_std=1.1, random_state=6)
model = SVC(kernel="linear", C=1.0).fit(X, y)
print(f"サポートベクター: {len(model.support_)} / {len(X)} 点")

# サポートベクター以外の点を全部捨てて学習し直し、係数を比べる
keep = model.support_
again = SVC(kernel="linear", C=1.0).fit(X[keep], y[keep])
print("全点の係数:", model.coef_.round(4), model.intercept_.round(4))
print("サポートベクターだけの係数:", again.coef_.round(4), again.intercept_.round(4))

fig, ax = plt.subplots(figsize=(5.6, 4.6))
draw_margin(ax, model, X, y, "線形 SVM の決定境界とマージン")
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=3, fontsize=8, frameon=False)
save(fig, "svm_linear_margin.webp")

# ---- 実験 2: C でマージンの幅が変わる ----
rng = np.random.default_rng(0)
X2 = np.vstack([rng.normal([0, 0], 1.0, (40, 2)), rng.normal([3, 3], 1.0, (40, 2))])
y2 = np.array([0] * 40 + [1] * 40)
fig, axes = plt.subplots(1, 3, figsize=(13, 4.2))
for ax, C in zip(axes, [0.05, 1.0, 100.0]):
    m = SVC(kernel="linear", C=C).fit(X2, y2)
    width = 2 / np.linalg.norm(m.coef_[0])  # 破線どうしの間隔
    errors = (m.predict(X2) != y2).sum()
    print(f"C={C:>6}: サポートベクター {len(m.support_):2d} 点、マージンの幅 {width:.2f}、"
          f"学習データの誤り {errors} 点")
    draw_margin(ax, m, X2, y2, f"C = {C}（幅 {width:.2f}、サポートベクター {len(m.support_)} 点）")
fig.tight_layout()
save(fig, "svm_soft_margin_C.webp")

# ---- 実験 3: カーネルと γ ----
X_c, y_c = make_circles(n_samples=200, factor=0.4, noise=0.08, random_state=0)
z = X_c[:, 0] ** 2 + X_c[:, 1] ** 2  # 3 つ目の列（原点からの距離の二乗）
print(f"内側の円: z の最大 {z[y_c == 1].max():.2f}、外側の円: z の最小 {z[y_c == 0].min():.2f}")

# z を足した 3 列で引く直線の SVM と、元の 2 列に「z を足した先の内積」を返すカーネルを使う SVM を比べる
X3 = np.column_stack((X_c, z))
lin3 = SVC(kernel="linear").fit(X3, y_c)


def k_z(A, B):
    # 3 列の内積 x1*x1' + x2*x2' + z*z' を、元の 2 列だけから計算する
    return A @ B.T + np.outer((A ** 2).sum(axis=1), (B ** 2).sum(axis=1))


ker = SVC(kernel=k_z).fit(X_c, y_c)
gap = np.abs(lin3.decision_function(X3) - ker.decision_function(X_c)).max()
print(f"3 列の直線の SVM とカーネルの SVM の決定関数の差の最大: {gap:.1e}")
print(f"正解率: 3 列の直線 {lin3.score(X3, y_c):.3f}、カーネル {ker.score(X_c, y_c):.3f}")

fig = plt.figure(figsize=(10, 4.2))
ax1 = fig.add_subplot(1, 2, 1)
ax1.scatter(X_c[y_c == 0, 0], X_c[y_c == 0, 1], color=BLUE, s=22, label="外側の円（クラス 0）")
ax1.scatter(X_c[y_c == 1, 0], X_c[y_c == 1, 1], color=RED, s=22, label="内側の円（クラス 1）")
ax1.set_title("2 列のまま: 直線では分けられない")
ax1.set_xlabel("x1")
ax1.set_ylabel("x2")
ax1.set_aspect("equal")
ax1.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=2, frameon=False)
ax2 = fig.add_subplot(1, 2, 2, projection="3d")
ax2.scatter(X_c[y_c == 0, 0], X_c[y_c == 0, 1], z[y_c == 0], color=BLUE, s=18)
ax2.scatter(X_c[y_c == 1, 0], X_c[y_c == 1, 1], z[y_c == 1], color=RED, s=18)
xx, yy = np.meshgrid(np.linspace(-1.2, 1.2, 10), np.linspace(-1.2, 1.2, 10))
ax2.plot_surface(xx, yy, np.full_like(xx, 0.5), alpha=0.25, color=GREEN)
ax2.set_title("z = x1² + x2² を足すと、z = 0.5 の平面で分けられる")
ax2.set_xlabel("x1")
ax2.set_ylabel("x2")
ax2.set_zlabel("z")
fig.tight_layout()
save(fig, "svm_kernel_trick.webp")

X_m, y_m = make_moons(n_samples=300, noise=0.15, random_state=0)
xx_m, yy_m = np.meshgrid(np.linspace(-1.5, 2.5, 250), np.linspace(-1.2, 1.7, 250))
fig, axes = plt.subplots(1, 3, figsize=(13, 3.8))
for ax, gamma in zip(axes, [0.1, 1.0, 1000.0]):
    m = SVC(kernel="rbf", gamma=gamma, C=1.0).fit(X_m, y_m)
    test = cross_val_score(SVC(kernel="rbf", gamma=gamma, C=1.0), X_m, y_m, cv=cv).mean()
    print(f"gamma={gamma:>6}: サポートベクター {len(m.support_):3d} 点、"
          f"学習データの正解率 {m.score(X_m, y_m):.3f}、交差検証の正解率 {test:.3f}")
    Z = m.predict(np.c_[xx_m.ravel(), yy_m.ravel()]).reshape(xx_m.shape)
    ax.contourf(xx_m, yy_m, Z, levels=[-0.5, 0.5, 1.5], alpha=0.2, colors=[BLUE, RED])
    ax.scatter(X_m[y_m == 0, 0], X_m[y_m == 0, 1], s=14, color=BLUE, edgecolor="white")
    ax.scatter(X_m[y_m == 1, 0], X_m[y_m == 1, 1], s=14, color=RED, edgecolor="white")
    ax.set_title(f"γ = {gamma}（交差検証の正解率 {test:.3f}）")
    ax.set_xlabel("x1")
    ax.set_ylabel("x2")
fig.tight_layout()
save(fig, "svm_rbf_gamma.webp")

# ---- 実験 4: 行の数と学習の時間 ----
sizes = [1000, 2000, 5000, 10000, 20000, 40000]
models = {
    "SVC（RBF）": lambda: make_pipeline(StandardScaler(), SVC()),
    "LinearSVC": lambda: make_pipeline(StandardScaler(), LinearSVC()),
    "ロジスティック回帰": lambda: make_pipeline(StandardScaler(), LogisticRegression()),
    "勾配ブースティング": lambda: HistGradientBoostingClassifier(random_state=0),
}
# 2026-11-12 に下の測定で得た値（秒、後ろ 5000 行の正解率）と SVC のサポートベクターの数
RECORDED = {
    "SVC（RBF）": ([0.033, 0.054, 0.314, 1.246, 6.323, 20.848], [0.893, 0.906, 0.940, 0.929, 0.928, 0.944]),
    "LinearSVC": ([0.003, 0.004, 0.006, 0.012, 0.037, 0.083], [0.739, 0.751, 0.735, 0.735, 0.753, 0.754]),
    "ロジスティック回帰": ([0.003, 0.003, 0.005, 0.008, 0.023, 0.047], [0.738, 0.753, 0.736, 0.733, 0.753, 0.754]),
    "勾配ブースティング": ([0.176, 0.230, 0.239, 0.349, 0.746, 1.041], [0.887, 0.906, 0.938, 0.929, 0.919, 0.931]),
}
RECORDED_SV = [600, 1017, 1883, 3389, 6019, 9877]
# 同じ日に 1 回ずつ測った別の回では、4 万行の SVC は 11.285 秒と 22.676 秒だった（並行の負荷による揺れ）
if os.environ.get("SVM_MEASURE") == "1":
    times = {k: [] for k in models}
    accs = {k: [] for k in models}
    n_sv = []
    with threadpool_limits(1):
        for n in sizes:
            # 先頭 n 行で学習し、後ろの 5000 行で正解率を測る
            Xt, yt = make_classification(n_samples=n + 5000, n_features=20, n_informative=10,
                                         flip_y=0.05, random_state=0)
            for name, make in models.items():
                spent = []
                for _ in range(3):  # 3 回測って中央値を取る
                    m = make()
                    start = time.perf_counter()
                    m.fit(Xt[:n], yt[:n])
                    spent.append(time.perf_counter() - start)
                times[name].append(float(np.median(spent)))
                accs[name].append(m.score(Xt[n:], yt[n:]))
                if name == "SVC（RBF）":
                    n_sv.append(len(m[-1].support_))
else:
    times = {k: v[0] for k, v in RECORDED.items()}
    accs = {k: v[1] for k, v in RECORDED.items()}
    n_sv = RECORDED_SV
for i, n in enumerate(sizes):
    print(f"{n:6d} 行: SVC {times['SVC（RBF）'][i]:7.3f} / 勾配ブースティング {times['勾配ブースティング'][i]:.3f}"
          f" / LinearSVC {times['LinearSVC'][i]:.3f} / ロジスティック回帰 {times['ロジスティック回帰'][i]:.3f} 秒")
print("4 万行の正解率: " + "、".join(f"{k} {accs[k][-1]:.3f}" for k in models))
slope = np.polyfit(np.log(sizes[2:]), np.log(times["SVC（RBF）"][2:]), 1)[0]
print(f"SVC の学習時間の傾き（5000 行以降、両対数）: {slope:.2f}")

fig, ax = plt.subplots(figsize=(6.4, 4.0))
styles = {"SVC（RBF）": (RED, "o"), "LinearSVC": (BLUE, "s"),
          "ロジスティック回帰": (GRAY, "^"), "勾配ブースティング": (GREEN, "D")}
for name in models:
    c, mk = styles[name]
    ax.plot(sizes, times[name], marker=mk, color=c, label=f"{name}: 4 万行の正解率 {accs[name][-1]:.3f}")
ax.set_xscale("log")
ax.set_yscale("log")
ax.set_xticks(sizes)
ax.set_xticklabels([f"{n:,}" for n in sizes])
ax.minorticks_off()
ax.set_yticks([0.01, 0.1, 1, 10])
ax.set_yticklabels(["0.01", "0.1", "1", "10"])
ax.set_xlabel("学習に使った行の数（20 列）")
ax.set_ylabel("学習の時間（秒、1 スレッド）")
ax.set_title("行の数を増やした時の学習の時間")
ax.legend(fontsize=8, loc="upper left")
ax.grid(True, which="major", alpha=0.3)
save(fig, "svm_fit_time.webp")

# ---- 実験 5: LinearSVC は、列を原点から離すと精度が落ちる ----
Xb, yb = make_blobs(n_samples=400, centers=[[0, 0], [2, 2]], cluster_std=1.0, random_state=0)
shifts = [0, 1, 3, 10, 30, 100, 300, 1000]
acc_svc, acc_lin, acc_std = [], [], []
for s in shifts:
    Xs = Xb + s  # 2 列とも同じ値 s だけずらす。点の並びは変わらない
    acc_svc.append(cross_val_score(SVC(kernel="linear"), Xs, yb, cv=cv).mean())
    acc_lin.append(cross_val_score(LinearSVC(), Xs, yb, cv=cv).mean())
    acc_std.append(cross_val_score(make_pipeline(StandardScaler(), LinearSVC()), Xs, yb, cv=cv).mean())
    print(f"ずらし幅 {s:4d}: SVC {acc_svc[-1]:.3f} / LinearSVC {acc_lin[-1]:.3f} / 標準化+LinearSVC {acc_std[-1]:.3f}")
print(f"各列の標準偏差: {Xb.std(axis=0).round(2)}")

X_far = Xb + 1000
svc_far = SVC(kernel="linear").fit(X_far, yb)
lin_far = LinearSVC().fit(X_far, yb)
lin_scaled = LinearSVC(intercept_scaling=1000, max_iter=100000).fit(X_far, yb)
print("SVC(kernel='linear') の係数:", svc_far.coef_.round(3), "切片:", svc_far.intercept_.round(1))
print("LinearSVC の係数:", lin_far.coef_.round(3), "切片:", lin_far.intercept_.round(2))
acc_scaled = cross_val_score(LinearSVC(intercept_scaling=1000, max_iter=100000), X_far, yb, cv=cv).mean()
print(f"LinearSVC(intercept_scaling=1000) の交差検証の正解率: {acc_scaled:.3f}、切片: {lin_scaled.intercept_.round(1)}")

fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.2), gridspec_kw={"width_ratios": [1.15, 1]})
ax = axes[0]
xs = [max(s, 0.3) for s in shifts]  # 0 は対数の軸に置けないので左端に置く
ax.plot(xs, acc_svc, marker="o", color=INK, label="SVC(kernel='linear')")
ax.plot(xs, acc_std, marker="^", color=GREEN, linestyle=":", label="標準化 + LinearSVC")
ax.plot(xs, acc_lin, marker="s", color=RED, label="LinearSVC")
ax.set_xscale("log")
ax.set_xticks(xs)
ax.set_xticklabels(["0"] + [str(s) for s in shifts[1:]])
ax.set_ylim(0.4, 1.0)
ax.set_xlabel("2 列に足した値（ずらし幅）")
ax.set_ylabel("交差検証の正解率")
ax.set_title("同じ点の並びを原点から離していく")
ax.annotate(f"{acc_lin[-1]:.3f}", (xs[-1], acc_lin[-1]), textcoords="offset points",
            xytext=(-6, -14), ha="right", color=RED)
ax.legend(fontsize=8, loc="lower left")
ax.grid(True, alpha=0.3)

ax = axes[1]
ax.scatter(X_far[yb == 0, 0], X_far[yb == 0, 1], s=12, color=BLUE, alpha=0.7, label="クラス 0")
ax.scatter(X_far[yb == 1, 0], X_far[yb == 1, 1], s=12, color=RED, alpha=0.7, label="クラス 1")
gx = np.linspace(X_far[:, 0].min() - 0.5, X_far[:, 0].max() + 0.5, 200)
for est, color, style, label in [(svc_far, INK, "-", "SVC(kernel='linear')"),
                                 (lin_far, RED, "--", "LinearSVC")]:
    w, b = est.coef_[0], est.intercept_[0]
    ax.plot(gx, -(w[0] * gx + b) / w[1], color=color,
            linestyle=style, linewidth=1.8, label=f"{label} の境界")
ax.set_xlim(X_far[:, 0].min() - 0.5, X_far[:, 0].max() + 0.5)
ax.set_ylim(X_far[:, 1].min() - 0.5, X_far[:, 1].max() + 0.5)
ax.set_xlabel("x1")
ax.set_ylabel("x2")
ax.set_title("ずらし幅 1000 の時の境界")
ax.legend(fontsize=8, loc="upper left")
fig.tight_layout()
save(fig, "svm_cover.webp")

# ---- 実験 6: probability=True の確率と predict の食い違い ----
Xbc, ybc = load_breast_cancer(return_X_y=True)
Xbc_s = StandardScaler().fit_transform(Xbc)
prob_model = SVC(probability=True, random_state=0).fit(Xbc_s, ybc)
dec = prob_model.decision_function(Xbc_s)
p_benign = prob_model.predict_proba(Xbc_s)[:, 1]  # クラス 1（良性）の確率
pred = prob_model.predict(Xbc_s)
A, B = prob_model.probA_[0], prob_model.probB_[0]
# scikit-learn の 2 クラスの predict_proba は、ほぼ 1 / (1 + exp(A * dec - B)) になる
gap = np.abs(p_benign - 1 / (1 + np.exp(A * dec - B))).max()
print(f"Platt scaling の式と predict_proba の差の最大: {gap:.4f}")
near = np.abs(dec) < 0.5
print(f"決定関数が -0.5〜0.5 の {near.sum()} 点での差の最大: "
      f"{np.abs(p_benign - 1 / (1 + np.exp(A * dec - B)))[near].max():.4f}")


def libsvm_pair_coupling(r01, k=2):
    """LIBSVM の multiclass_probability を 2 クラスで写したもの。p = 0.5 から始め、誤差が 0.005 / k 未満で止める。"""
    r = np.array([[0.0, r01], [1 - r01, 0.0]])
    P = np.full(k, 1.0 / k)
    Q = np.array([[r[1][0] ** 2, -r[1][0] * r[0][1]], [-r[1][0] * r[0][1], r[0][1] ** 2]])
    for _ in range(max(100, k)):
        Qp = Q @ P
        pQp = P @ Qp
        if np.abs(Qp - pQp).max() < 0.005 / k:
            break
        for t in range(k):
            diff = (-Qp[t] + pQp) / Q[t][t]
            P[t] += diff
            pQp = (pQp + diff * (diff * Q[t][t] + 2 * Qp[t])) / (1 + diff) / (1 + diff)
            Qp = (Qp + diff * Q[t]) / (1 + diff)
            P /= 1 + diff
    return P


# LIBSVM の内部では決定関数の符号が逆で、ペアの確率は [1e-7, 1 - 1e-7] に切り詰められる
coupled = np.array([libsvm_pair_coupling(np.clip(1 / (1 + np.exp(-A * f + B)), 1e-7, 1 - 1e-7))[1]
                    for f in dec])
print(f"LIBSVM の反復を写した値と predict_proba の差の最大: {np.abs(coupled - p_benign).max():.1e}")
odd = np.where(pred != (p_benign > 0.5).astype(int))[0]
print(f"Platt scaling の係数 A={A:.3f}、B={B:.3f}、確率が 0.5 になる決定関数の値 {B / A:.3f}")
print(f"predict と predict_proba が食い違う点: {len(odd)} / {len(ybc)}")
for i in odd:
    print(f"  決定関数 {dec[i]:.3f}、predict {pred[i]}（良性）、良性の確率 {p_benign[i]:.3f}")

Xd, yd = load_digits(return_X_y=True)
odd_d = 0
for tr, te in cv.split(Xd, yd):
    md = SVC(probability=True, random_state=0).fit(Xd[tr], yd[tr])
    odd_d += (md.predict(Xd[te]) != md.predict_proba(Xd[te]).argmax(axis=1)).sum()
print(f"digits（10 クラス）で食い違う点: {odd_d} / {len(yd)}")

fig, axes = plt.subplots(1, 2, figsize=(10.5, 3.9))
for ax, (lo, hi), title in [(axes[0], (-3, 3), "決定関数の値と良性の確率"),
                            (axes[1], (-0.15, 0.25), "0 の付近を拡大")]:
    sel = (dec >= lo) & (dec <= hi)
    ax.scatter(dec[sel & (pred == 0)], p_benign[sel & (pred == 0)], s=14, color=BLUE,
               label="predict が悪性（0）")
    ax.scatter(dec[sel & (pred == 1)], p_benign[sel & (pred == 1)], s=14, color=GREEN,
               label="predict が良性（1）")
    ax.scatter(dec[odd], p_benign[odd], s=120, facecolors="none", edgecolors=RED, linewidths=1.8,
               label="predict と確率が食い違う点")
    g = np.linspace(lo, hi, 200)
    ax.plot(g, 1 / (1 + np.exp(A * g - B)), color=GRAY, linewidth=1, label="Platt scaling の曲線")
    ax.axhline(0.5, color=INK, linestyle=":", linewidth=1)
    ax.axvline(0, color=INK, linestyle=":", linewidth=1)
    ax.set_xlim(lo, hi)
    ax.set_xlabel("決定関数の値（0 より大きいと predict は良性）")
    ax.set_ylabel("predict_proba の良性の確率")
    ax.set_title(title)
axes[1].axvspan(0, B / A, color=RED, alpha=0.1)
axes[1].annotate(f"0〜{B / A:.3f} は predict が良性、\n確率は 0.5 未満", (B / A, 0.25),
                 textcoords="offset points", xytext=(8, 0), color=RED, fontsize=9)
axes[0].legend(fontsize=8, loc="upper left")
fig.tight_layout()
save(fig, "svm_proba.webp")

# ---- 実験 7: 他の手法との比較（5 分割の交差検証の正解率） ----
compare = {
    "SVC（標準化なし）": lambda: SVC(),
    "SVC（標準化あり）": lambda: make_pipeline(StandardScaler(), SVC()),
    "ロジスティック回帰（標準化あり）": lambda: make_pipeline(StandardScaler(), LogisticRegression(max_iter=5000)),
    "勾配ブースティング": lambda: HistGradientBoostingClassifier(random_state=0),
}
for dname, loader in [("breast_cancer", load_breast_cancer), ("wine", load_wine), ("digits", load_digits)]:
    Xc, yc = loader(return_X_y=True)
    print(f"{dname}（{Xc.shape[0]} 行 {Xc.shape[1]} 列）: " +
          "、".join(f"{k} {cross_val_score(f(), Xc, yc, cv=cv).mean():.3f}" for k, f in compare.items()))
