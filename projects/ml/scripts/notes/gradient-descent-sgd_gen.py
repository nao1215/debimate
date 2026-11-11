"""gradient-descent-sgd ノートの実験と図を生成するスクリプト。

本文に載せた 6 つの実験（学習率と 1 回の縮み方、列の尺度と収束の回数、1 行ごとの曲率、
外れた行で跳ねる重み、バッチの大きさ、SGDRegressor の既定）を本文と同じ順に実行し、
出力を標準出力に、図を Page Bundle に WebP で保存する。
実行: cd projects/ml && .venv/bin/python scripts/notes/gradient-descent-sgd_gen.py
確認した版: scikit-learn 1.9.1、NumPy 2.5.4、matplotlib 3.11.2
"""
import warnings
from io import BytesIO
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from sklearn.datasets import fetch_california_housing
from sklearn.linear_model import LinearRegression, SGDRegressor
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import FunctionTransformer, RobustScaler, StandardScaler

NOTE_DIR = Path(__file__).resolve().parents[2] / "notes" / "math" / "gradient-descent-sgd"
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10,
                     "axes.spines.top": False, "axes.spines.right": False})
BLUE, RED, GREEN, ORANGE, PURPLE, INK, GRAY = ("#7aa6c2", "#e15759", "#59a14f", "#f28e2b",
                                              "#8e6bb0", "#333333", "#999999")


def save(fig, name):
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight", facecolor="#ffffff")
    plt.close(fig)
    buf.seek(0)
    Image.open(buf).convert("RGB").save(NOTE_DIR / name, "WEBP", quality=90, method=6)


# ---- データ: California Housing を 8:2 に分け、学習用の平均と標準偏差で標準化する ----
X, y = fetch_california_housing(return_X_y=True)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=0)
scaler = StandardScaler().fit(X_train)
Z_train = scaler.transform(X_train)


# ---- 実験 1: 2 次関数で、学習率と曲率の積 ηλ が 1 回の更新の縮み方を決める ----
print("== 実験 1: 学習率と 1 回の縮み方 ==")
lam = 2.0  # f(x) = (x - 3)² + 1 の 2 階微分（曲率）
for eta in [0.05, 0.3, 0.9, 1.05]:
    x = -0.5
    for _ in range(10):
        x = x - eta * 2 * (x - 3)  # f'(x) = 2(x - 3)
    print(f"η={eta}: ηλ={eta * lam:.1f}、1 回で距離が {abs(1 - eta * lam):.1f} 倍、"
          f"10 回後の最小点までの距離 {abs(x - 3):.4f}")

fig, ax = plt.subplots(figsize=(7.2, 3.6))
el = np.linspace(0, 2.4, 400)
ax.axvspan(0, 1, color=GREEN, alpha=0.08)
ax.axvspan(1, 2, color=ORANGE, alpha=0.10)
ax.axvspan(2, 2.4, color=RED, alpha=0.10)
ax.plot(el, np.abs(1 - el), color=INK, lw=2)
ax.axhline(1, color=GRAY, lw=1, ls="--")
for eta, c in [(0.05, BLUE), (0.3, GREEN), (0.9, ORANGE), (1.05, RED)]:
    v = eta * lam
    ax.plot(v, abs(1 - v), "o", color=c, ms=8, zorder=5)
    ax.annotate(f"η={eta}", (v, abs(1 - v)), xytext=(8, 4) if v < 1 else (10, -12), textcoords="offset points",
                color=c, fontsize=9)
ax.text(0.5, 1.28, "同じ側から近づく", ha="center", color=GREEN, fontsize=9)
ax.text(1.5, 1.28, "反対側へ飛び越えながら近づく", ha="center", color=ORANGE, fontsize=9)
ax.text(2.2, 1.28, "発散", ha="center", color=RED, fontsize=9)
ax.set_xlim(0, 2.4)
ax.set_ylim(0, 1.45)
ax.set_xlabel("学習率 × 曲率（ηλ）")
ax.set_ylabel("1 回の更新で距離が何倍になるか")
fig.tight_layout()
save(fig, "gd_contraction.webp")


# ---- 実験 2: 2 列の線形回帰で、2 列目の単位だけを k 倍にして最急降下法の回数を数える ----
print("== 実験 2: 列の尺度と収束までの回数 ==")
rng = np.random.default_rng(0)
n = 200
x1, x2 = rng.standard_normal(n), rng.standard_normal(n)
y_toy = 1.0 * x1 + 0.5 * x2 + 0.1 * rng.standard_normal(n)

scale_steps = {}
for k in [1, 2, 5, 10, 20, 50, 100]:
    Xk = np.column_stack([x1, k * x2])  # 2 列目の単位だけを k 倍にする（m を cm にするなど）
    H = Xk.T @ Xk / n  # 損失 mean((Xw - y)²) / 2 の曲率をまとめた行列（ヘッセ行列）
    lam_min, lam_max = np.linalg.eigvalsh(H)
    eta = 1.0 / lam_max  # 発散しない上限 2 / λmax の半分
    w_star = np.linalg.lstsq(Xk, y_toy)[0]
    w, steps = np.zeros(2), 0
    while np.linalg.norm(w - w_star) > 1e-3 * np.linalg.norm(w_star):
        w = w - eta * Xk.T @ (Xk @ w - y_toy) / n
        steps += 1
    scale_steps[k] = steps
    print(f"k={k:>3}: 曲率 λmin={lam_min:.2f} λmax={lam_max:.1f}、学習率 {eta:.5f}、収束までの回数 {steps}")

fig, axes = plt.subplots(1, 3, figsize=(11, 3.6), gridspec_kw={"width_ratios": [1, 1, 1.1]})
for ax, k in zip(axes[:2], [1, 10]):
    Xk = np.column_stack([x1, k * x2])
    H = Xk.T @ Xk / n
    eta = 1.0 / np.linalg.eigvalsh(H).max()
    w_star = np.linalg.lstsq(Xk, y_toy)[0]
    w1g, w2g = np.meshgrid(np.linspace(-0.2, 1.4, 200), np.linspace(-0.2, 1.4, 200) / k)
    W = np.stack([w1g.ravel(), w2g.ravel()], axis=1)
    L = (np.mean((W @ Xk.T - y_toy) ** 2, axis=1) / 2).reshape(w1g.shape)
    ax.contour(w1g, w2g * k, L, levels=np.geomspace(L.min() + 1e-3, L.max(), 14), colors=GRAY,
               linewidths=0.7)
    w, path = np.zeros(2), [np.zeros(2)]
    for _ in range(30):
        w = w - eta * Xk.T @ (Xk @ w - y_toy) / n
        path.append(w)
    path = np.array(path)
    ax.plot(path[:, 0], path[:, 1] * k, "o-", color=RED, ms=3, lw=1.2)
    ax.plot(w_star[0], w_star[1] * k, "*", color=INK, ms=13)
    ax.set_title(f"2 列目を {k} 倍（30 回の更新）", fontsize=10)
    ax.set_xlabel("1 列目の重み w1")
    ax.set_ylabel(f"2 列目の重み w2 × {k}" if k > 1 else "2 列目の重み w2")
    ax.set_aspect("equal")
ks = np.array(list(scale_steps))
st = np.array(list(scale_steps.values()))
axes[2].loglog(ks, st, "o-", color=BLUE, lw=2)
axes[2].loglog(ks, st[0] * ks ** 2, "--", color=GRAY, lw=1)
axes[2].text(14, st[0] * 14 ** 2 * 0.25, "k² に比例する線", color=GRAY, fontsize=9, rotation=27)
offsets = {1: (8, -2, "left"), 10: (-8, 8, "right"), 100: (-10, -3, "right")}
for kk, s in scale_steps.items():
    if kk in offsets:
        dx, dy, ha = offsets[kk]
        axes[2].annotate(f"{s:,} 回", (kk, s), xytext=(dx, dy), textcoords="offset points", ha=ha,
                         fontsize=9, color=BLUE)
axes[2].set_xlabel("2 列目に掛けた倍率 k")
axes[2].set_ylabel("収束までの更新の回数")
axes[2].set_title("最小点の 0.1% 以内に入るまでの回数", fontsize=10)
fig.tight_layout()
save(fig, "gd_scale.webp")


# ---- 実験 3: SGD の 1 行ごとの曲率 ||x||² + 1 を、標準化した California Housing で数える ----
print("== 実験 3: 1 行ごとの曲率 ==")
row_curv = (Z_train ** 2).sum(axis=1) + 1  # 切片の分の 1 を足す
eta0 = 0.01
eta_end = eta0 / len(Z_train) ** 0.25  # 図用: invscaling で 1 周目の最後の行の学習率
clip_curv = (np.clip(Z_train, -3, 3) ** 2).sum(axis=1) + 1
print(f"行の数 {len(row_curv)}、曲率の中央値 {np.median(row_curv):.1f}、最大 {row_curv.max():.0f}")
print(f"学習率 {eta0} で上限 2/η={2 / eta0:.0f} を超える行: {(row_curv > 2 / eta0).sum()}")
print(f"±3 で切った後の曲率の最大 {clip_curv.max():.0f}")
top = np.argsort(-row_curv)[:2]
for i in top:
    print(f"  曲率 {row_curv[i]:.0f} の行: AveRooms={X_train[i, 2]:.1f} AveBedrms={X_train[i, 3]:.1f} "
          f"Population={X_train[i, 4]:.0f} AveOccup={X_train[i, 5]:.1f}")

fig, ax = plt.subplots(figsize=(7.6, 3.4))
bins = np.geomspace(1, 1e4, 60)
ax.hist(row_curv, bins=bins, color=BLUE, label="標準化した後")
ax.hist(clip_curv, bins=bins, histtype="step", color=GREEN, lw=1.5, label="標準化して ±3 で切った後")
ax.set_xscale("log")
ax.set_yscale("log")
ax.axvline(2 / eta0, color=RED, lw=1.5, ls="--")
ax.text(2 / eta0 * 1.1, 2500, f"学習率 0.01 の上限\n2/η = {2 / eta0:.0f}\n超える行 {(row_curv > 2 / eta0).sum()}",
        color=RED, fontsize=9, va="top")
ax.axvline(2 / eta_end, color=ORANGE, lw=1.5, ls=":")
ax.text(2 / eta_end * 1.1, 60, f"1 周目の最後の上限\n{2 / eta_end:.0f}\n超える行 {(row_curv > 2 / eta_end).sum()}",
        color=ORANGE, fontsize=9, va="top")
ax.set_xlabel("1 行の曲率 ||x||² + 1（対数目盛）")
ax.set_ylabel("行の数（対数目盛）")
ax.legend(loc="upper right", fontsize=9, frameon=False, bbox_to_anchor=(1.0, 1.18), ncol=2)
fig.tight_layout()
save(fig, "gd_row_curvature.webp")


# ---- 実験 4: 1 行ずつの SGD（学習率 0.01 で固定）で、重みの大きさを更新ごとに記録する ----
print("== 実験 4: 外れた行で跳ねる重み ==")


def sgd_trace(Z, eta, epochs=2, seed=0):
    A = np.column_stack([Z, np.ones(len(Z))])  # 最後の列は切片
    curv = (A ** 2).sum(axis=1)
    rng = np.random.default_rng(seed)
    w = np.zeros(A.shape[1])
    norms, hits, mse = [], [], []
    for _ in range(epochs):
        for i in rng.permutation(len(A)):  # 1 周ごとに行の順番を混ぜる
            if eta * curv[i] > 2:
                hits.append(len(norms))  # 上限を超える行で更新した回
            w = w - eta * (A[i] @ w - y_train[i]) * A[i]  # 損失 (予測 - y)² / 2 の勾配
            norms.append(np.linalg.norm(w))
        mse.append(np.mean((A @ w - y_train) ** 2))
    return np.array(norms), hits, mse


trace = {}
for label, Z in [("標準化した後", Z_train), ("標準化して ±3 で切った後", np.clip(Z_train, -3, 3))]:
    norms, hits, mse = sgd_trace(Z, 0.01)
    trace[label] = (norms, hits)
    print(f"{label}: 1 周ごとの学習データの平均二乗誤差 {[f'{m:.3g}' for m in mse]}、"
          f"上限を超える行での更新 {len(hits)} 回")
    if hits:
        t = hits[0]
        print(f"  最初は {t + 1} 回目の更新で、重みの大きさが {norms[t - 1]:.2f} から {norms[t]:.2f} に")

fig, ax = plt.subplots(figsize=(8, 3.4))
for (label, (norms, hits)), c in zip(trace.items(), [RED, GREEN]):
    ax.plot(np.arange(1, len(norms) + 1), norms, color=c, lw=1.2, label=label)
    ax.plot(np.array(hits) + 1, norms[hits], "|", color=INK, ms=9, mew=1.2)
ax.set_yscale("log")
ax.axvline(len(Z_train), color=GRAY, lw=1, ls="--")
ax.text(len(Z_train) * 1.02, 3e3, "2 周目", color=GRAY, fontsize=9)
ax.set_xlabel("更新の回数（1 周 = 16,512 回）")
ax.set_ylabel("重みの大きさ ||w||（対数目盛）")
ax.legend(frameon=False, fontsize=9, loc="upper left")
ax.text(18000, 0.08, "縦の印: 曲率が上限 200 を超える行で更新した回", fontsize=8.5, color=INK)
fig.tight_layout()
save(fig, "gd_trace.webp")


# ---- 実験 5: 学習率 0.01 で固定し、バッチの大きさだけを変える ----
print("== 実験 5: バッチの大きさ ==")


def minibatch(Z, batch, eta=0.01, epochs=20, seed=0):
    A = np.column_stack([Z, np.ones(len(Z))])
    rng = np.random.default_rng(seed)
    w = np.zeros(A.shape[1])
    mse = []
    for _ in range(epochs):
        idx = rng.permutation(len(A))
        for s in range(0, len(A), batch):
            b = idx[s:s + batch]
            w = w - eta * A[b].T @ (A[b] @ w - y_train[b]) / len(b)  # B 行の勾配の平均
        mse.append(np.mean((A @ w - y_train) ** 2))
        if mse[-1] > 1e6:  # 発散したら打ち切る
            break
    return mse


ols_mse = np.mean((LinearRegression().fit(Z_train, y_train).predict(Z_train) - y_train) ** 2)
print(f"LinearRegression の学習データの平均二乗誤差 {ols_mse:.3f}")
A_full = np.column_stack([Z_train, np.ones(len(Z_train))])
print(f"全ての行で計算した曲率の最大 {np.linalg.eigvalsh(A_full.T @ A_full / len(A_full)).max():.2f}")
batch_mse = {}
for B in [1, 8, 32, 256, len(Z_train)]:
    batch_mse[B] = minibatch(Z_train, B)
    updates = int(np.ceil(len(Z_train) / B))
    last = batch_mse[B][-1]
    state = f"{len(batch_mse[B])} 周目に {last:.3g} になり打ち切り" if last > 1e6 else f"20 周後 {last:.3f}"
    print(f"バッチ {B:>5}: 1 周の更新 {updates:>5} 回、{state}")

full_09 = minibatch(Z_train, len(Z_train), eta=0.9)
print(f"バッチ GD を学習率 0.9 で: 5 周後 {full_09[4]:.3f}、20 周後 {full_09[-1]:.3f}")

fig, ax = plt.subplots(figsize=(8, 3.6))
colors = {1: RED, 8: ORANGE, 32: GREEN, 256: BLUE, len(Z_train): PURPLE}
for B, mse in batch_mse.items():
    name = "全行（16,512）" if B == len(Z_train) else f"{B} 行"
    ax.plot(np.arange(1, len(mse) + 1), mse, "o-", color=colors[B], ms=3.5, lw=1.5, label=name)
ax.axhline(ols_mse, color=INK, lw=1, ls="--")
ax.text(20.3, ols_mse * 1.15, "最小二乗の解", fontsize=8.5, va="bottom")
ax.set_yscale("log")
ax.set_ylim(0.3, 1e7)
ax.set_xlim(0.5, 23)
ax.set_xticks([1, 5, 10, 15, 20])
ax.set_xlabel("学習データを何周したか")
ax.set_ylabel("学習データの平均二乗誤差（対数目盛）")
ax.legend(title="1 回の更新に使う行", frameon=False, fontsize=9, title_fontsize=9,
          loc="upper right", ncol=2)
fig.tight_layout()
save(fig, "gd_batch.webp")


# ---- 実験 6: SGDRegressor を既定の設定のまま 10 回ずつ学習し、テストデータの R² を測る ----
print("== 実験 6: SGDRegressor の既定 ==")
eta_end = 0.01 / len(Z_train) ** 0.25  # invscaling で 1 周目の最後の行の学習率
print(f"1 周目の最後の学習率 {eta_end:.6f} で上限 {2 / eta_end:.0f} を超える行: {(row_curv > 2 / eta_end).sum()}")
# eta0=0.001 の invscaling で、最大の曲率の行が上限 2/η を超えるのは何回目の更新までか
print(f"eta0=0.001 で曲率 {row_curv.max():.0f} の行が上限を超えるのは t <= {(0.001 * row_curv.max() / 2) ** 4:.0f}")
sd = X_train.std(axis=0)
names_cols = fetch_california_housing().feature_names
print(f"列ごとの標準偏差: 最大 {sd.max():.2f}（{names_cols[sd.argmax()]}）、最小 {sd.min():.2f}（{names_cols[sd.argmin()]}）")
raw_curv = (X_train ** 2).sum(axis=1) + 1
print(f"標準化しない時の曲率: 中央値 {np.median(raw_curv):.3g}、100 万を超える行 {(raw_curv > 1e6).mean():.1%}")
configs = {
    "そのまま": lambda s: SGDRegressor(random_state=s),
    "標準化": lambda s: make_pipeline(StandardScaler(), SGDRegressor(random_state=s)),
    "RobustScaler": lambda s: make_pipeline(RobustScaler(), SGDRegressor(random_state=s)),
    "標準化 + eta0=0.001": lambda s: make_pipeline(StandardScaler(), SGDRegressor(eta0=0.001, random_state=s)),
    "標準化 + ±3 で切る": lambda s: make_pipeline(StandardScaler(), FunctionTransformer(lambda Z: np.clip(Z, -3, 3)),
                                              SGDRegressor(random_state=s)),
}
r2 = {}
for name, make in configs.items():
    scores, n_iters, n_warn = [], [], 0
    for seed in range(10):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            model = make(seed).fit(X_train, y_train)
        n_warn += len(caught)
        scores.append(model.score(X_test, y_test))
        n_iters.append(model[-1].n_iter_ if hasattr(model, "steps") else model.n_iter_)
    r2[name] = scores
    print(f"{name}: R² {min(scores):.4g}〜{max(scores):.4g}（中央値 {np.median(scores):.4g}）、"
          f"周回 {min(n_iters)}〜{max(n_iters)}、警告 {n_warn} 件")
ols_r2 = LinearRegression().fit(X_train, y_train).score(X_test, y_test)
print(f"LinearRegression: R² {ols_r2:.4f}")
clip_ols = make_pipeline(StandardScaler(), FunctionTransformer(lambda Z: np.clip(Z, -3, 3)), LinearRegression())
print(f"標準化 + ±3 で切る + LinearRegression: R² {clip_ols.fit(X_train, y_train).score(X_test, y_test):.4f}")

fig, ax = plt.subplots(figsize=(8.2, 3.6))
names = list(r2)[::-1]
for i, name in enumerate(names):
    vals = np.array(r2[name])
    good = vals > 0
    ax.plot(vals, np.full(10, i) + np.linspace(-0.12, 0.12, 10), "o", ms=5,
            color=GREEN if good.all() else RED, alpha=0.8)
    med = np.median(vals)
    if med > 0:
        label = f"中央値 ${med:.3f}$"
    elif med > -1e5:
        label = f"中央値 ${med:.0f}$"
    else:
        mant, exp = f"{med:.1e}".split("e+")
        label = f"中央値 ${mant}\\times 10^{{{int(exp)}}}$"
    ax.text(3, i, label, fontsize=8.5, ha="left", va="center", color=INK)
ax.set_xscale("symlog", linthresh=1)
ax.axvline(ols_r2, color=INK, lw=1, ls="--")
ax.axvline(0, color=GRAY, lw=0.8)
ax.text(-0.3, len(names) - 0.35, f"LinearRegression {ols_r2:.3f}（破線）", fontsize=8.5, ha="right")
ax.set_yticks(range(len(names)))
ax.set_yticklabels(names)
ax.set_ylim(-0.6, len(names) - 0.2)
ax.set_xlim(-1e31, 3e3)
ax.set_xticks([-1e30, -1e20, -1e10, -1e3, -1, 1])
ax.set_xticklabels([r"$-10^{30}$", r"$-10^{20}$", r"$-10^{10}$", r"$-1000$", r"$-1$", r"$1$"])
ax.set_xlabel("テストデータの R²（$-1$ より左は左ほど桁で縮めた目盛。灰色の実線は R² = 0）")
fig.tight_layout()
save(fig, "gd_cover.webp")


# ---- 図: invscaling の学習率と、最大の曲率 8595 の行の上限 2 / 8595 ----
fig, ax = plt.subplots(figsize=(7.6, 3.4))
t = np.geomspace(1, len(Z_train) * 10, 400)
for e0, c in [(0.01, RED), (0.001, GREEN)]:
    ax.loglog(t, e0 / t ** 0.25, color=c, lw=2, label=f"eta0={e0}")
limit = 2 / row_curv.max()
ax.axhline(limit, color=INK, lw=1, ls="--")
ax.text(1.3, limit * 0.68, f"曲率 {row_curv.max():.0f} の行の上限 2/{row_curv.max():.0f}", fontsize=9)
cross = (0.001 / limit) ** 4
ax.plot(cross, limit, "o", color=GREEN, ms=6)
ax.annotate(f"{cross:.0f} 回目で上限を下回る", (cross, limit), xytext=(10, 12), textcoords="offset points",
            fontsize=9, color=GREEN)
for ep in range(1, 11):
    ax.axvline(len(Z_train) * ep, color=GRAY, lw=0.5, alpha=0.5)
ax.text(len(Z_train) * 0.9, 0.0075, "灰色の縦線: 1 周の終わりごと（10 周まで）", fontsize=8.5, color=GRAY, ha="right")
ax.set_xlabel("更新した行の数 t（対数目盛）")
ax.set_ylabel("学習率 eta0 / t^0.25（対数目盛）")
ax.legend(frameon=False, fontsize=9, loc="lower left")
fig.tight_layout()
save(fig, "gd_invscaling.webp")
