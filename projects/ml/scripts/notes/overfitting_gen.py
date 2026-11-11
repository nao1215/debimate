"""overfitting ノートの実験と図を生成するスクリプト。

本文に載せた 4 つの実験（多項式の次数、深い木と森、テストの使い回し、落ち方の見分け）を
同じ順に実行し、出力を標準出力に、図を Page Bundle に WebP で保存する。
実行: cd projects/ml && .venv/bin/python scripts/notes/overfitting_gen.py
確認した版: scikit-learn 1.9.1、NumPy 2.5.4、matplotlib 3.11.2
"""
from io import BytesIO
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from sklearn.datasets import make_classification
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import mean_squared_error
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import PolynomialFeatures, StandardScaler
from sklearn.tree import DecisionTreeClassifier

NOTE_DIR = Path(__file__).resolve().parents[2] / "notes" / "ml" / "overfitting"
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10,
                     "axes.spines.top": False, "axes.spines.right": False})
BLUE, RED, GREEN, INK, GRAY = "#7aa6c2", "#e15759", "#59a14f", "#333333", "#999999"


def save(fig, name):
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight", facecolor="#ffffff")
    plt.close(fig)
    buf.seek(0)
    Image.open(buf).convert("RGB").save(NOTE_DIR / name, "WEBP", quality=90, method=6)


# ---- 実験 3（冒頭の図）: ラベルが乱数のデータで、テストの点が上がる列を 1 本ずつ足す ----
def forward_by_test(X_tr, y_tr, X_te, y_te, X_new, y_new, rounds=20):
    """手元のテストの正解率が一番上がる列を 1 本ずつ足していく。"""
    chosen, n_eval, log = [], 0, []
    for _ in range(rounds):
        cand = []
        for c in range(X_tr.shape[1]):
            if c in chosen:
                continue
            cols = chosen + [c]
            m = LogisticRegression().fit(X_tr[:, cols], y_tr)
            cand.append((m.score(X_te[:, cols], y_te), c))
            n_eval += 1
        test, best_c = max(cand)  # テストで一番良かった列を残す
        chosen.append(best_c)
        m = LogisticRegression().fit(X_tr[:, chosen], y_tr)
        train, new = m.score(X_tr[:, chosen], y_tr), m.score(X_new[:, chosen], y_new)
        log.append((len(chosen), n_eval, train, test, new))
    return log


rng = np.random.RandomState(0)
X_all = rng.randn(11300, 50)
y_all = rng.randint(0, 2, 11300)  # ラベルは 50 列のどれとも関係ない乱数
X_tr, y_tr = X_all[:200], y_all[:200]  # 学習用 200 行
X_te, y_te = X_all[200:300], y_all[200:300]  # 手元のテスト 100 行
X_new, y_new = X_all[300:10300], y_all[300:10300]  # 後から届く新しいデータ 10000 行
X_te1k, y_te1k = X_all[10300:], y_all[10300:]  # 比較用に、テストを 1000 行にした場合

log100 = forward_by_test(X_tr, y_tr, X_te, y_te, X_new, y_new)
log1k = forward_by_test(X_tr, y_tr, X_te1k, y_te1k, X_new, y_new)
for (k, n, tr, te, nw), (*_, te1k, nw1k) in zip(log100, log1k):
    if k in (1, 5, 10, 20):
        print(f"{k:2d} 列（{n:3d} 回評価）: 訓練 {tr:.3f}、テスト 100 行 {te:.3f}、新しいデータ {nw:.3f}"
              f" ／ テスト 1000 行 {te1k:.3f}、新しいデータ {nw1k:.3f}")

h = np.array(log100)
h1k = np.array(log1k)
fig, ax = plt.subplots(figsize=(7.2, 3.8))
ax.plot(h[:, 0], h[:, 3], "o-", color=RED, lw=2, ms=3.5, label="手元のテスト 100 行の正解率")
ax.plot(h1k[:, 0], h1k[:, 3], "o--", color=RED, lw=1.2, ms=3, alpha=0.7, label="テストを 1000 行にした場合")
ax.plot(h[:, 0], h[:, 4], "o-", color=BLUE, lw=2, ms=3.5, label="同じモデルを新しいデータ 10000 行で測った正解率")
ax.axhline(0.5, color=GRAY, lw=1, ls=":")
ax.text(1, 0.47, "偶然の水準 0.5", color=GRAY, fontsize=9)
ax.set_xlim(0.5, 20.5)
ax.set_xticks([1, 5, 10, 15, 20])
ax.set_ylim(0.4, 0.8)
ax.set_xlabel("足した列の数（毎回、手元のテストが一番上がる列を選ぶ）")
ax.set_ylabel("正解率")
for arr, col, dy in ((h[:, 3], RED, 6), (h1k[:, 3], RED, -14), (h[:, 4], BLUE, -14)):
    ax.annotate(f"{arr[-1]:.2f}", (20, arr[-1]), xytext=(-12, dy), textcoords="offset points", color=col, fontsize=9.5)
ax.set_title("ラベルが乱数のデータで、手元のテストを見ながら列を足した結果", fontsize=10.5)
ax.legend(loc="upper left", frameon=False, fontsize=9)
save(fig, "overfitting_cover.webp")

# 1 列目を選ぶ時の 50 回の評価を、そのまま並べる（揺れの上側だけが残る様子）
first = []
for c in range(50):
    m = LogisticRegression().fit(X_tr[:, [c]], y_tr)
    first.append((m.score(X_te[:, [c]], y_te), m.score(X_new[:, [c]], y_new)))
first = np.array(first)
print(f"1 列目の 50 回: テストの平均 {first[:, 0].mean():.3f}、標準偏差 {first[:, 0].std():.3f}、最大 {first[:, 0].max():.3f}"
      f"／その列の新しいデータ {first[first[:, 0].argmax(), 1]:.3f}")
fig, ax = plt.subplots(figsize=(6.8, 3.0))
bins = np.arange(0.425, 0.61, 0.01)
ax.hist(first[:, 0], bins=bins, color=RED, alpha=0.85, label="手元のテスト 100 行の正解率（50 列それぞれ）")
ax.hist(first[:, 1], bins=bins, color=BLUE, alpha=0.85, label="同じ 50 個のモデルの、新しいデータ 10000 行での正解率")
best = first[:, 0].max()
ax.annotate(f"テストで一番高い列\nを残す（{best:.2f}）", (best, 1.2), xytext=(best - 0.012, 12),
            arrowprops={"arrowstyle": "->", "color": INK}, fontsize=9)
ax.axvline(0.5, color=GRAY, ls=":", lw=1)
ax.set_xlim(0.425, 0.605)
ax.set_xlabel("正解率")
ax.set_ylabel("列の数")
ax.legend(frameon=False, fontsize=8.5, loc="upper left", bbox_to_anchor=(0.0, 1.0))
ax.set_ylim(0, 58)
save(fig, "overfitting_first_round.webp")


# ---- 実験 1: 多項式の次数を変える ----
rng = np.random.RandomState(0)


def true_f(x):
    return np.sin(1.5 * x)


x = np.sort(rng.uniform(-2, 2, 20))
y = true_f(x) + rng.normal(0, 0.25, x.size)
x_val = rng.uniform(-2, 2, 200)
y_val = true_f(x_val) + rng.normal(0, 0.25, x_val.size)

degrees = range(1, 16)
train_mse, val_mse = [], []
for d in degrees:
    model = make_pipeline(PolynomialFeatures(d), StandardScaler(), LinearRegression())
    model.fit(x[:, None], y)
    train_mse.append(mean_squared_error(y, model.predict(x[:, None])))
    val_mse.append(mean_squared_error(y_val, model.predict(x_val[:, None])))
    if d in (1, 3, 15):
        print(f"次数 {d:2d}: 訓練の誤差 {train_mse[-1]:.3f}、検証の誤差 {val_mse[-1]:.3f}")

grid = np.linspace(-2, 2, 400)
fig, axes = plt.subplots(1, 3, figsize=(9.6, 3.0), sharey=True)
for ax, d, label in zip(axes, (1, 3, 15), ("未学習", "ちょうど良い", "過学習")):
    model = make_pipeline(PolynomialFeatures(d), StandardScaler(), LinearRegression()).fit(x[:, None], y)
    ax.plot(grid, true_f(grid), color=GREEN, ls="--", lw=1.2, label="真の関数")
    ax.plot(grid, model.predict(grid[:, None]), color=RED, lw=1.8, label="モデルの予測")
    ax.scatter(x, y, s=16, color=BLUE, zorder=3, label="訓練の 20 点")
    ax.set_ylim(-2, 2)
    ax.set_title(f"次数 {d}（{label}）\n訓練の誤差 {train_mse[d - 1]:.3f}、検証の誤差 {val_mse[d - 1]:.3f}",
                 fontsize=9.5)
    ax.set_xlabel("x")
axes[0].set_ylabel("y")
axes[0].legend(loc="lower right", frameon=False, fontsize=8)
save(fig, "overfitting_fit.webp")

fig, ax = plt.subplots(figsize=(6.4, 3.4))
ax.plot(list(degrees), train_mse, "o-", color=BLUE, label="訓練の誤差")
ax.plot(list(degrees), val_mse, "o-", color=RED, label="検証の誤差")
best_d = int(np.argmin(val_mse)) + 1
ax.axvline(best_d, color=GRAY, ls=":", lw=1)
ax.set_yscale("log")
ax.text(best_d + 0.3, 3, f"検証の誤差が最小の次数 {best_d}", color=GRAY, fontsize=9)
ax.set_xlabel("多項式の次数（モデルの複雑さ）")
ax.set_ylabel("平均二乗誤差（対数目盛）")
ax.legend(frameon=False)
save(fig, "overfitting_loss.webp")
print(f"検証の誤差が最小の次数: {best_d}")


# ---- 実験 2: 深い木・浅い木・深い森 ----
# flip_y=0.3: 3 割のサンプルのクラスを乱数で振り直す（ノイズの多いデータ）
# 10500 行を作り、500 行を学習とテストに、残りの 10000 行を新しいデータにする
X, y = make_classification(n_samples=10500, n_features=20, flip_y=0.3, random_state=0)
X_tr2, X_te2, y_tr2, y_te2 = train_test_split(X[:500], y[:500], test_size=0.3, random_state=0)
X_new2, y_new2 = X[500:], y[500:]

models = {
    # 深さを制限せず、葉の中のラベルが揃うまで分割 → ノイズまで覚える
    "深い木": DecisionTreeClassifier(random_state=0),
    # 深さと葉のサンプル数を絞る → 細かいノイズを覚えられない
    "浅い木": DecisionTreeClassifier(max_depth=4, min_samples_leaf=10, random_state=0),
    # 深い木を 100 本平均する
    "深い森": RandomForestClassifier(random_state=0),
}
scores = {}
for name, m in models.items():
    m.fit(X_tr2, y_tr2)
    scores[name] = (m.score(X_tr2, y_tr2), m.score(X_te2, y_te2), m.score(X_new2, y_new2))
    print(f"{name} 訓練: {scores[name][0]:.3f} テスト: {scores[name][1]:.3f} 新しいデータ: {scores[name][2]:.3f}")

fig, ax = plt.subplots(figsize=(6.8, 3.3))
names = list(scores)
pos = np.arange(len(names))
for j, (lab, col) in enumerate((("訓練 350 行", GRAY), ("テスト 150 行", RED), ("新しいデータ 10000 行", BLUE))):
    vals = [scores[n][j] for n in names]
    xs = pos + (j - 1) * 0.26
    ax.bar(xs, vals, 0.26, color=col, label=lab)
    for xx, v in zip(xs, vals):
        ax.text(xx, v + 0.01, f"{v:.3f}", ha="center", fontsize=8.5)
ax.set_xticks(pos, [f"{n}\n訓練とテストの差 {scores[n][0] - scores[n][1]:.3f}" for n in names], fontsize=9)
ax.set_ylim(0, 1.25)
ax.set_ylabel("正解率")
ax.legend(frameon=False, ncol=3, loc="upper center", fontsize=9)
save(fig, "overfitting_trees.webp")


# ---- 実験 4: 3 つの原因で、訓練・テスト・新しいデータのどこで点が落ちるか ----
rng = np.random.RandomState(0)
cases = {}
# 過学習: 実験 2 の深い木
cases["過学習\n（深い木）"] = scores["深い木"]
# テストの使い回し: 実験 3 で 20 列を足した時点
cases["テストの使い回し\n（テストを見て列を足す）"] = tuple(h[-1, 2:])
# ドリフト: 学習の後で、ラベルを決める重みの一部が入れ替わる
w = rng.randn(10)
Xd = rng.randn(10300, 10)
yd_old = (Xd @ w + rng.randn(10300) * 0.5 > 0).astype(int)
w_new = w.copy()
w_new[:3] = -w_new[:3]  # 3 列の効き方が逆になる
yd_new = (Xd @ w_new + rng.randn(10300) * 0.5 > 0).astype(int)
lr = LogisticRegression().fit(Xd[:200], yd_old[:200])
cases["ドリフト\n（学習後に関係が変わる）"] = (lr.score(Xd[:200], yd_old[:200]), lr.score(Xd[200:300], yd_old[200:300]),
                                  lr.score(Xd[300:], yd_new[300:]))
for k, v in cases.items():
    print(k.replace("\n", ""), "訓練 {:.3f} テスト {:.3f} 新しいデータ {:.3f}".format(*v))

fig, ax = plt.subplots(figsize=(7.2, 3.4))
labels = list(cases)
pos = np.arange(len(labels))
for j, (lab, col) in enumerate((("訓練", GRAY), ("手元のテスト", RED), ("新しいデータ", BLUE))):
    vals = [cases[k][j] for k in labels]
    xs = pos + (j - 1) * 0.26
    ax.bar(xs, vals, 0.26, color=col, label=lab)
    for xx, v in zip(xs, vals):
        ax.text(xx, v + 0.01, f"{v:.3f}", ha="center", fontsize=8.5)
ax.axhline(0.5, color=GRAY, lw=1, ls=":")
ax.set_xticks(pos, [f"{k}\n訓練とテストの差 {cases[k][0] - cases[k][1]:.3f}" for k in labels], fontsize=9)
ax.set_ylim(0, 1.15)
ax.set_ylabel("正解率")
ax.legend(frameon=False, ncol=3, loc="upper center")
save(fig, "overfitting_causes.webp")
