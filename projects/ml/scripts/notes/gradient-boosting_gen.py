"""gradient-boosting ノートの実験と図を生成するスクリプト。

本文に載せた 5 つの実験（残差に木を足すループ、learning_rate と本数、early stopping、
3 つの実装の比較、10,000 行の境目）を同じ順に実行し、出力を標準出力に、図を Page Bundle に
WebP で保存する。
実行: cd projects/ml && .venv/bin/python scripts/notes/gradient-boosting_gen.py
確認した版: scikit-learn 1.9.1、NumPy 2.5.4、matplotlib 3.11.2
学習は全て 1 スレッドに揃える（時間の比較を揃えるためと、結果をスレッド数に依らせないため）。
"""
import pickle
import time
from io import BytesIO
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from sklearn.datasets import fetch_california_housing
from sklearn.ensemble import (GradientBoostingRegressor, HistGradientBoostingRegressor,
                              RandomForestRegressor)
from sklearn.metrics import mean_squared_error
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeRegressor
from threadpoolctl import threadpool_limits

threadpool_limits(limits=1)

NOTE_DIR = Path(__file__).resolve().parents[2] / "notes" / "ml" / "gradient-boosting"
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10,
                     "axes.spines.top": False, "axes.spines.right": False})
BLUE, RED, GREEN, ORANGE, INK, GRAY = "#7aa6c2", "#e15759", "#59a14f", "#f28e2b", "#333333", "#999999"


def save(fig, name):
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight", facecolor="#ffffff")
    plt.close(fig)
    buf.seek(0)
    Image.open(buf).convert("RGB").save(NOTE_DIR / name, "WEBP", quality=90, method=6)


# ---- 実験 1: 残差に浅い木を足すループを手で書き、GradientBoostingRegressor と比べる ----
rng = np.random.default_rng(0)
x = np.linspace(-3, 3, 200).reshape(-1, 1)
y_true = np.sin(x.ravel()) * 1.5 + 0.2 * x.ravel() ** 2
y = y_true + 0.3 * rng.standard_normal(200)

learning_rate = 0.5
F = np.full(len(y), y.mean())  # 最初の予測は、全ての行で y の平均
for i in range(50):
    residual = y - F  # ここまでの予測が外した分
    tree = DecisionTreeRegressor(max_depth=3, random_state=0).fit(x, residual)
    F = F + learning_rate * tree.predict(x)  # 残差を当てた木の予測に learning_rate を掛けて足す

gbr = GradientBoostingRegressor(n_estimators=50, learning_rate=0.5, max_depth=3, random_state=0).fit(x, y)
print("手書きのループと GradientBoostingRegressor の予測の差の最大:", np.abs(F - gbr.predict(x)).max())

# 図: 本文の手順の最初の 2 歩（平均 → 残差を当てる 1 本目の木）。上のループと同じ learning_rate=0.5、深さ 3
F0 = np.full(len(y), y.mean())
t1 = DecisionTreeRegressor(max_depth=3, random_state=0).fit(x, y - F0)
F1 = F0 + learning_rate * t1.predict(x)
fig, axes = plt.subplots(1, 3, figsize=(12, 3.4))
axes[0].scatter(x, y, s=10, alpha=0.4, color=BLUE, label="データ")
axes[0].plot(x, F0, color=RED, lw=2, label="最初の予測（y の平均）")
axes[0].set_title("1. 最初の予測は y の平均", fontsize=10)
axes[0].set_ylabel("y")
axes[1].scatter(x, y - F0, s=10, alpha=0.5, color=ORANGE, label="残差（y − 平均）")
axes[1].plot(x, t1.predict(x), color=RED, lw=2, label="1 本目の木の予測")
axes[1].axhline(0, color=GRAY, lw=0.6)
axes[1].set_title("2. 1 本目の木は残差を当てる", fontsize=10)
axes[1].set_ylabel("残差")
axes[2].scatter(x, y, s=10, alpha=0.4, color=BLUE, label="データ")
axes[2].plot(x, F0, color=GRAY, lw=1.5, ls="--", label="平均だけ")
axes[2].plot(x, F1, color=RED, lw=2, label="平均 + 0.5 × 1 本目")
axes[2].set_title("3. 0.5 倍して足すと、データに近づく", fontsize=10)
for ax in axes:
    ax.set_xlabel("x")
    ax.legend(fontsize=8, loc="upper left")
fig.tight_layout()
save(fig, "gradient-boosting_residual.webp")

# 図: 足した木の本数ごとの予測（learning_rate=0.5、深さ 3）
fig, axes = plt.subplots(1, 4, figsize=(13, 3.2), sharey=True)
for ax, n in zip(axes, [1, 3, 10, 50]):
    pred = GradientBoostingRegressor(n_estimators=n, learning_rate=0.5, max_depth=3,
                                     random_state=0).fit(x, y).predict(x)
    ax.scatter(x, y, s=10, alpha=0.3, color=GRAY, label="データ")
    ax.plot(x, y_true, color=GREEN, ls="--", lw=1.5, label="データを作った関数")
    ax.plot(x, pred, color=RED, lw=2, label="予測")
    ax.set_title(f"木 {n} 本", fontsize=10)
    ax.set_xlabel("x")
axes[0].set_ylabel("y")
axes[0].legend(fontsize=7.5, loc="upper left")
fig.tight_layout()
save(fig, "gradient-boosting_progressive_fit.webp")

# ---- 実験 2: learning_rate と木の本数（California Housing の検証データの平均二乗誤差） ----
X, y = fetch_california_housing(return_X_y=True)
# テスト用の 2 割は、最後の評価にだけ使う
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=0)
# 学習用の残りから、さらに 2 割を検証用に取り分け、本数や learning_rate の比較に使う
X_fit, X_val, y_fit, y_val = train_test_split(X_train, y_train, test_size=0.2, random_state=0)

curves = {}
for lr in [1.0, 0.5, 0.1, 0.01]:
    model = HistGradientBoostingRegressor(learning_rate=lr, max_iter=1000, early_stopping=False,
                                          random_state=0).fit(X_fit, y_fit)
    # staged_predict は、木を 1 本足すごとの予測を順に返す
    mse = np.array([mean_squared_error(y_val, p) for p in model.staged_predict(X_val)])
    curves[lr] = mse
    print(f"learning_rate={lr}: 最小は {mse.argmin() + 1} 本で {mse.min():.4f}、"
          f"100 本で {mse[99]:.4f}、1000 本で {mse[-1]:.4f}")

fig, ax = plt.subplots(figsize=(7, 4))
for lr, color in zip(curves, [RED, ORANGE, GREEN, BLUE]):
    mse = curves[lr]
    ax.plot(np.arange(1, 1001), mse, color=color, lw=1.6, label=f"learning_rate = {lr}")
    ax.scatter([mse.argmin() + 1], [mse.min()], color=color, s=25, zorder=3)
ax.set_xscale("log")
ax.set_ylim(0.18, 0.6)
ax.set_xlabel("足した木の本数（対数目盛）")
ax.set_ylabel("検証データの平均二乗誤差")
ax.legend(fontsize=9)
ax.grid(alpha=0.2)
fig.tight_layout()
save(fig, "gradient-boosting_learning_rate.webp")

# ---- 実験 3: early stopping が止める本数と、返すモデル ----
es = HistGradientBoostingRegressor(max_iter=1000, early_stopping=True, n_iter_no_change=10,
                                   random_state=0).fit(X_fit, y_fit, X_val=X_val, y_val=y_val)
# validation_score_ は、0 本目からの検証データの損失に負号を付けた値
val_mse = -2 * es.validation_score_
best = int(val_mse.argmin())
print(f"止まった本数（n_iter_）: {es.n_iter_}、検証データの誤差が最小だった本数: {best}")
print(f"止まった時点の検証データの平均二乗誤差: {val_mse[es.n_iter_]:.4f}、"
      f"1000 本まで足した時の最小: {curves[0.1].min():.4f}（{curves[0.1].argmin() + 1} 本）")
full = HistGradientBoostingRegressor(max_iter=1000, early_stopping=False, random_state=0).fit(X_fit, y_fit)
print(f"テストデータの平均二乗誤差: {es.n_iter_} 本で止めたモデル "
      f"{mean_squared_error(y_test, es.predict(X_test)):.4f}、"
      f"1000 本のモデル {mean_squared_error(y_test, full.predict(X_test)):.4f}")

fig, ax = plt.subplots(figsize=(7, 3.8))
c = curves[0.1]
ax.plot(np.arange(1, 1001), c, color=GRAY, lw=1.3, label="1000 本まで足した場合")
ax.plot(np.arange(0, es.n_iter_ + 1), val_mse, color=GREEN, lw=2, label="early stopping で止めた場合")
ax.axvline(es.n_iter_, color=RED, ls="--", lw=1)
ax.text(es.n_iter_ + 8, 0.235, f"{es.n_iter_} 本で停止\n最小だった {best} 本から\n10 本続けて改善せず",
        color=RED, fontsize=8.5, va="top")
ax.scatter([c.argmin() + 1], [c.min()], color=INK, s=25, zorder=3)
ax.annotate(f"1000 本の中の最小（{c.argmin() + 1} 本）", xy=(c.argmin() + 1, c.min()),
            xytext=(c.argmin() - 330, 0.222), fontsize=8.5, color=INK,
            arrowprops=dict(arrowstyle="->", color=INK, lw=0.8))
ax.set_xlim(0, 1000)
ax.set_ylim(0.195, 0.26)
ax.set_xlabel("足した木の本数")
ax.set_ylabel("検証データの平均二乗誤差")
ax.legend(fontsize=9, loc="upper right")
ax.grid(alpha=0.2)
fig.tight_layout()
save(fig, "gradient-boosting_early_stopping.webp")

# ---- 実験 4: RandomForest、GradientBoosting、HistGradientBoosting を既定値で比べる ----
models = {
    "RandomForestRegressor": lambda: RandomForestRegressor(random_state=0),
    "GradientBoostingRegressor": lambda: GradientBoostingRegressor(random_state=0),
    "HistGradientBoostingRegressor": lambda: HistGradientBoostingRegressor(random_state=0),
}
results, seconds = {}, {}
for name, make in models.items():
    times = []
    for _ in range(3):  # 3 回学習した時間の中央値を取る
        model = make()
        start = time.perf_counter()
        model.fit(X_train, y_train)
        times.append(time.perf_counter() - start)
    seconds[name] = np.median(times)
    size_mb = len(pickle.dumps(model)) / 1e6  # 保存した時の大きさ
    results[name] = (model.score(X_test, y_test), size_mb)
    print(f"{name}: テストの R² {model.score(X_test, y_test):.3f}、大きさ {size_mb:.2f} MB")
hgb = model
print("HistGradientBoostingRegressor の early stopping:", hgb.do_early_stopping_, "、木の本数:", hgb.n_iter_)
for name, sec in seconds.items():
    print(f"{name}: 学習 {sec:.2f} 秒")

fig, axes = plt.subplots(1, 2, figsize=(9, 2.9))
labels = ["RandomForest", "GradientBoosting", "HistGradientBoosting"]
colors = [GRAY, BLUE, RED]
for ax, k, title, fmt in zip(axes, range(2), ["テストデータの R²", "保存した大きさ（MB）"], ["{:.3f}", "{:.2f}"]):
    vals = [results[n][k] for n in models]
    bars = ax.barh(labels, vals, color=colors)
    ax.invert_yaxis()
    ax.set_title(title, fontsize=10)
    for b, v in zip(bars, vals):
        ax.text(b.get_width(), b.get_y() + b.get_height() / 2, " " + fmt.format(v), va="center", fontsize=9)
    ax.set_xlim(0, 1.0 if k == 0 else max(vals) * 1.3)
    if k > 0:
        ax.set_yticklabels([])
fig.tight_layout()
save(fig, "gradient-boosting_models.webp")

# ---- 実験 5: 学習に使う行数を変え、既定の設定のまま 10 回ずつ学習する ----
# random_state を渡さない学習は NumPy の大域の乱数を使う。種をここで 1 回だけ固定すると、
# 10 回の学習は互いに違う乱数を使いつつ、スクリプト全体を流し直した時の結果は同じになる
np.random.seed(0)
order = np.random.RandomState(0).permutation(len(X_train))
sizes = [8000, 9000, 10000, 10001, 11000, 12000, 14000, 16000]
r2_default, n_iter_1000 = {}, {}
for n in sizes:
    rows = order[:n]  # 学習用のデータから、同じ順に n 行を使う
    fits = [HistGradientBoostingRegressor().fit(X_train[rows], y_train[rows]) for _ in range(10)]
    r2_default[n] = [m.score(X_test, y_test) for m in fits]
    long_fits = [HistGradientBoostingRegressor(max_iter=1000).fit(X_train[rows], y_train[rows])
                 for _ in range(10)]
    n_iter_1000[n] = [m.n_iter_ for m in long_fits]
    print(f"{n:>5} 行: early stopping {fits[0].do_early_stopping_}、"
          f"R² {min(r2_default[n]):.4f}〜{max(r2_default[n]):.4f}、"
          f"max_iter=1000 の木の本数 {min(n_iter_1000[n])}〜{max(n_iter_1000[n])}")

# 10,001 行で、乱数の種を固定した場合と、early stopping を切った場合
rows = order[:10001]
for label, params in [("random_state=0", {"random_state": 0}), ("early_stopping=False", {"early_stopping": False})]:
    scores = [HistGradientBoostingRegressor(**params).fit(X_train[rows], y_train[rows]).score(X_test, y_test)
              for _ in range(10)]
    print(f"10001 行、{label}: R² {min(scores):.4f}〜{max(scores):.4f}")


def strip(ax, data, ylabel):
    for i, n in enumerate(sizes):
        on = n > 10000
        jitter = np.linspace(-0.18, 0.18, len(data[n])) if on else np.zeros(len(data[n]))
        ax.scatter(i + jitter, data[n], s=22 if on else 45, color=RED if on else BLUE, alpha=0.8, zorder=3)
    ax.set_xticks(range(len(sizes)))
    ax.set_xticklabels([f"{n:,}" for n in sizes])
    ax.axvline(2.5, color=GRAY, ls=":", lw=1)
    ax.set_xlabel("学習に使った行数")
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", alpha=0.2)


fig, ax = plt.subplots(figsize=(8, 3.8))
strip(ax, r2_default, "テストデータの R²")
ax.text(1.0, np.mean(r2_default[10000]) + 0.0025, "10 回とも同じ値\n（10 個の点が 1 つに重なる）",
        color=BLUE, ha="center", fontsize=9)
ax.text(5.0, min(min(v) for v in r2_default.values()) - 0.0025,
        "10 回とも違う値（学習のたびに検証用の行を乱数で選ぶ）", color=RED, ha="center", fontsize=9)
ax.set_ylim(min(min(v) for v in r2_default.values()) - 0.004, max(max(v) for v in r2_default.values()) + 0.004)
ax.set_title("HistGradientBoostingRegressor を既定の設定のまま 10 回ずつ学習", fontsize=10)
fig.tight_layout()
save(fig, "gradient-boosting_cover.webp")

fig, ax = plt.subplots(figsize=(8, 3.6))
strip(ax, n_iter_1000, "学習した木の本数（n_iter_）")
ax.set_ylim(0, 1100)
ax.text(1.0, 1030, "1000 本全部", color=BLUE, ha="center", fontsize=9)
on_iters = [v for n in sizes if n > 10000 for v in n_iter_1000[n]]
ax.text(5.0, max(on_iters) + 60, f"{min(on_iters)}〜{max(on_iters)} 本で停止", color=RED, ha="center", fontsize=9)
fig.tight_layout()
save(fig, "gradient-boosting_n_iter.webp")
