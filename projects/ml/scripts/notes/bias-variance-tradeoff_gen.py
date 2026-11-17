"""bias-variance-tradeoff ノートの実験と図を生成するスクリプト。

scikit-learn 同梱の手書き数字 (load_digits) に RBFSampler で列を足し、
LinearRegression・Ridge で当てはめて、本文の実験を同じ順に実行する。
出力を標準出力に、図を Page Bundle に WebP で保存する。
実行: cd projects/ml && .venv/bin/python scripts/notes/bias-variance-tradeoff_gen.py
確認した版: scikit-learn 1.9.1、NumPy 2.5.4、Matplotlib 3.11.2
"""
from io import BytesIO
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from sklearn.datasets import load_digits
from sklearn.kernel_approximation import RBFSampler
from sklearn.linear_model import LinearRegression, Ridge

NOTE_DIR = Path(__file__).resolve().parents[2] / "notes" / "ml" / "bias-variance-tradeoff"
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10,
                     "axes.spines.top": False, "axes.spines.right": False})
BLUE, RED, GREEN, INK, GRAY, ORANGE = "#7aa6c2", "#e15759", "#59a14f", "#333333", "#999999", "#f28e2b"


def save(fig, name):
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight", facecolor="#ffffff")
    plt.close(fig)
    buf.seek(0)
    Image.open(buf).convert("RGB").save(NOTE_DIR / name, "WEBP", quality=90, method=6)


# ============================================================
# 準備: データと、列を p 本に増やす関数
# ============================================================
X, y = load_digits(return_X_y=True)   # 8×8 画素の手書き数字 1797 枚
X = X / 16.0                           # 画素の値を 0〜1 に
Y = np.eye(10)[y]                      # 正解の数字の列だけ 1 にした 10 列
rng = np.random.default_rng(0)
order = rng.permutation(len(X))
test, pool = order[:400], order[400:]  # 測る 400 枚と、学習に使う行を選ぶ元の 1397 枚
n = 200                                # 1 回の学習に使う行の数
R = 40                                 # 学習し直す回数


def features(p):
    """64 画素から、乱数で決めた p 本の列を作る（全行分）。"""
    return RBFSampler(gamma=0.05, n_components=p, random_state=0).fit(X).transform(X)


# 切片を付けると山の位置が 1 本ずれるので、作った列だけで当てはめる
def bias_variance(p, n=n, make=lambda: LinearRegression(fit_intercept=False), seed=1):
    F = features(p)
    rng = np.random.default_rng(seed)
    preds = np.empty((R, len(test), 10))
    for r in range(R):
        rows = rng.choice(pool, n, replace=False)   # 毎回違う 200 行で学習し直す
        preds[r] = make().fit(F[rows], Y[rows]).predict(F[test])
    mean = preds.mean(axis=0)                        # 40 個のモデルが出した予測の平均
    bias2 = np.mean(np.sum((mean - Y[test]) ** 2, axis=1))
    var = np.mean(np.sum(preds.var(axis=0), axis=1))
    miss = np.mean(np.argmax(preds, axis=2) != y[test])
    return bias2, var, miss, preds


# ============================================================
# 実験 1: 40 個のモデルが同じ画像に付けた点数
# ============================================================
img = test[0]
print("1 枚目の画像の正解:", y[img])
strip = {}
for p in [10, 200, 4000]:
    *_, preds = bias_variance(p)
    s = preds[:, 0, y[img]]                          # 正解の数字の列に付けた点数
    strip[p] = s
    print(f"p={p:<5} 平均 {s.mean():6.2f}  正解との差 {s.mean() - 1:6.2f}  標準偏差 {s.std():6.2f}"
          f"  最小 {s.min():7.2f}  最大 {s.max():7.2f}")

fig, axes = plt.subplots(3, 1, figsize=(8.2, 4.6), sharex=True)
lo, hi = -1.5, 3.5
for ax, (p, s) in zip(axes, strip.items()):
    jitter = np.random.default_rng(3).uniform(-0.25, 0.25, len(s))
    inside = (s >= lo) & (s <= hi)
    ax.scatter(s[inside], jitter[inside], s=18, color=BLUE, alpha=0.8, edgecolor="none")
    out_l, out_r = np.sum(s < lo), np.sum(s > hi)
    if out_l:
        ax.annotate(f"← 範囲外 {out_l} 個", (lo + 0.05, 0.32), fontsize=9, color=RED)
    if out_r:
        ax.annotate(f"範囲外 {out_r} 個 →", (hi - 0.85, 0.32), fontsize=9, color=RED)
    ax.axvline(1, color=INK, lw=1, ls=":")
    ax.plot([s.mean()], [0], marker="|", ms=22, mew=2.5, color=RED)
    ax.set_ylim(-0.5, 0.6)
    ax.set_yticks([])
    ax.spines["left"].set_visible(False)
    ax.set_title(f"列 {p} 本", loc="left", fontsize=10)
axes[0].annotate("正解の 1", (1, 0.45), xytext=(1.15, 0.42), fontsize=9, color=INK)
axes[0].annotate("赤い縦線は 40 個の平均", (strip[10].mean(), -0.35), xytext=(1.6, -0.35),
                 fontsize=9, color=RED)
axes[-1].set_xlim(lo, hi)
axes[-1].set_xlabel("正解の数字に付けた点数（40 個のモデル）")
fig.tight_layout()
save(fig, "bv_strip.webp")


# ============================================================
# 実験 2: 列の数 p を増やした時のバイアス² とバリアンス（表紙）
# ============================================================
ps = [5, 10, 20, 30, 50, 75, 100, 125, 150, 175, 190, 200, 210, 225, 250, 300,
      400, 500, 700, 1000, 1500, 2000, 3000, 4000]
rows = []
for p in ps:
    b2, var, miss, _ = bias_variance(p)
    rows.append((p, b2, var, miss))
    print(f"p={p:<5} バイアス² {b2:8.3f}  バリアンス {var:9.3f}  二乗誤差 {b2 + var:9.3f}  誤分類率 {miss:.3f}")
res = np.array(rows)

fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), gridspec_kw={"width_ratios": [1.35, 1]})
ax = axes[0]
ax.plot(res[:, 0], res[:, 1] + res[:, 2], color=INK, lw=2, marker="o", ms=3.5, label="テストの二乗誤差")
ax.plot(res[:, 0], res[:, 1], color=BLUE, lw=1.6, ls="--", label="バイアス²")
ax.plot(res[:, 0], res[:, 2], color=RED, lw=1.6, label="バリアンス")
ax.axvline(n, color=GRAY, ls=":", lw=1.2)
ax.text(n * 1.25, 150, "列の数 = 行の数\n（200）", fontsize=9, color=INK)
ax.set_xscale("log")
ax.set_yscale("log")
ax.set_xlabel("列の数 p（対数）")
ax.set_ylabel("値（対数）")
ax.set_title("テストの二乗誤差と、その内訳", fontsize=10)
ax.legend(fontsize=9, loc="upper left", frameon=False)
ax.grid(True, which="major", alpha=0.25)
ax = axes[1]
ax.plot(res[:, 0], res[:, 3], color=INK, lw=2, marker="o", ms=3.5)
ax.axvline(n, color=GRAY, ls=":", lw=1.2)
best_left = res[res[:, 0] < n][np.argmin(res[res[:, 0] < n][:, 3])]
ax.annotate(f"左側の最小 {best_left[3]:.3f}\n（列 {best_left[0]:.0f} 本）", (best_left[0], best_left[3]),
            xytext=(14, 0.72), fontsize=9, arrowprops={"arrowstyle": "->", "color": GRAY})
ax.annotate(f"列 4000 本で {res[-1, 3]:.3f}", (4000, res[-1, 3]), xytext=(700, 0.18), fontsize=9,
            arrowprops={"arrowstyle": "->", "color": GRAY})
ax.set_xscale("log")
ax.set_ylim(0, 0.9)
ax.set_xlabel("列の数 p（対数）")
ax.set_ylabel("誤分類率")
ax.set_title("数字の誤分類率（10 択）", fontsize=10)
ax.grid(True, which="major", alpha=0.25)
fig.tight_layout()
save(fig, "bv_cover.webp")


# ============================================================
# 実験 3: 最小の特異値と係数の大きさ
# ============================================================
rows_one = np.random.default_rng(1).choice(pool, n, replace=False)   # 1 組の 200 行
sv_rows = []
for p in ps:
    Fp = features(p)[rows_one]
    s = np.linalg.svd(Fp, compute_uv=False)                          # 大きい順の特異値
    model = LinearRegression(fit_intercept=False).fit(Fp, Y[rows_one])
    sv_rows.append((p, s[-1], s[0], np.linalg.norm(model.coef_)))
    if p in (100, 200, 4000):
        ref = np.linalg.lstsq(Fp, Y[rows_one], rcond=None)[0].T
        print(f"p={p:<5} 最小の特異値 {s[-1]:.2e}  係数の大きさ {np.linalg.norm(model.coef_):9.2f}"
              f"  NumPy の最小ノルム解と一致: {np.allclose(model.coef_, ref, atol=1e-6)}")
sv = np.array(sv_rows)
print(f"最小の特異値 ÷ 最大の特異値（p=200）: {sv[ps.index(200), 1] / sv[ps.index(200), 2]:.1e}")

fig, axes = plt.subplots(1, 2, figsize=(10.5, 3.8))
ax = axes[0]
ax.plot(sv[:, 0], sv[:, 1], color=INK, lw=2, marker="o", ms=3.5)
ax.set_title("200 行 × p 列の行列の、最小の特異値", fontsize=10)
ax.set_ylabel("最小の特異値（対数）")
ax = axes[1]
ax.plot(sv[:, 0], sv[:, 3], color=RED, lw=2, marker="o", ms=3.5)
ax.set_title("学習した係数の大きさ（2 乗和の平方根）", fontsize=10)
ax.set_ylabel("係数の大きさ（対数）")
for ax in axes:
    ax.axvline(n, color=GRAY, ls=":", lw=1.2)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("列の数 p（対数）")
    ax.grid(True, which="major", alpha=0.25)
fig.tight_layout()
save(fig, "bv_singular.webp")


# ============================================================
# 実験 4: 列を 200 本に固定して、行を増やす
# ============================================================
ns = [50, 75, 100, 125, 150, 175, 190, 200, 210, 225, 250, 300, 400, 500, 600]
n_rows = []
for m in ns:
    b2, var, miss, _ = bias_variance(200, n=m)
    n_rows.append((m, b2 + var, miss))
    print(f"n={m:<4} 二乗誤差 {b2 + var:9.3f}  誤分類率 {miss:.3f}")
nr = np.array(n_rows)

fig, axes = plt.subplots(1, 2, figsize=(10.5, 3.8))
axes[0].plot(nr[:, 0], nr[:, 1], color=INK, lw=2, marker="o", ms=3.5)
axes[0].set_yscale("log")
axes[0].set_ylabel("テストの二乗誤差（対数）")
axes[0].set_title("列 200 本のまま、学習に使う行を増やす", fontsize=10)
axes[1].plot(nr[:, 0], nr[:, 2], color=INK, lw=2, marker="o", ms=3.5)
axes[1].set_ylim(0, 0.9)
axes[1].set_ylabel("誤分類率")
axes[1].set_title("同じ実験の誤分類率", fontsize=10)
for ax in axes:
    ax.axvline(200, color=GRAY, ls=":", lw=1.2)
    ax.set_xlabel("学習に使う行の数 n")
    ax.grid(True, alpha=0.25)
axes[1].text(212, 0.8, "行の数 = 列の数（200）", fontsize=9, color=INK)
fig.tight_layout()
save(fig, "bv_rows.webp")


# ============================================================
# 実験 4b: 山から離れた所の学習曲線（訓練と検証の誤差）と、行を足した時の内訳
# ============================================================
def train_test_error(p, n, seed=1):
    """違う n 行で R 回学習し、訓練の行とテストの行の二乗誤差を平均する。"""
    F = features(p)
    rng = np.random.default_rng(seed)
    tr, te = [], []
    for r in range(R):
        rows = rng.choice(pool, n, replace=False)
        model = LinearRegression(fit_intercept=False).fit(F[rows], Y[rows])
        tr.append(np.mean(np.sum((model.predict(F[rows]) - Y[rows]) ** 2, axis=1)))
        te.append(np.mean(np.sum((model.predict(F[test]) - Y[test]) ** 2, axis=1)))
    return np.mean(tr), np.mean(te)


curve_ns = [200, 300, 400, 600, 800, 1000]
curves = {}
for p in (10, 150):
    curves[p] = np.array([train_test_error(p, m) for m in curve_ns])
    for m, (a, b) in zip(curve_ns, curves[p]):
        print(f"p={p:<4} n={m:<5} 訓練の二乗誤差 {a:.3f}  テストの二乗誤差 {b:.3f}")

for m in (50, 200, 800):
    b2, var, miss, _ = bias_variance(10, n=m)
    print(f"p=10   n={m:<4} バイアス² {b2:.3f}  バリアンス {var:.4f}  誤分類率 {miss:.3f}")

# 列 4000 本は全ての行を通すので訓練の誤差は 0 に近いが、誤分類率は 24 通りで一番低い
a, b = train_test_error(4000, 200)
print(f"p=4000 n=200  訓練の二乗誤差 {a:.2e}  テストの二乗誤差 {b:.3f}")
best = int(np.argmin(res[:, 3]))
print(f"誤分類率が一番低い列の数: p={int(res[best, 0])}  誤分類率 {res[best, 3]:.3f}")

fig, axes = plt.subplots(1, 2, figsize=(10.5, 3.8), sharey=True)
for ax, p, title in zip(axes, (10, 150), ("列 10 本（バイアス側）", "列 150 本（バリアンス側）")):
    ax.plot(curve_ns, curves[p][:, 0], color=BLUE, lw=2, marker="o", ms=3.5, label="訓練の行の二乗誤差")
    ax.plot(curve_ns, curves[p][:, 1], color=RED, lw=2, marker="s", ms=3.5, label="テストの行の二乗誤差")
    ax.set_title(title, fontsize=10)
    ax.set_xlabel("学習に使う行の数 n")
    ax.grid(True, alpha=0.25)
axes[0].set_ylabel("二乗誤差")
axes[0].set_ylim(0, 0.8)
axes[1].legend(fontsize=9, frameon=False, loc="upper right")
fig.tight_layout()
save(fig, "bv_curve.webp")


# ============================================================
# 実験 5: Ridge の alpha で山が消える
# ============================================================
alphas = [1e-3, 1e-2, 1e-1]
ridge = {}
for a in alphas:
    ridge[a] = []
    for p in ps:
        b2, var, miss, _ = bias_variance(p, make=lambda a=a: Ridge(alpha=a, fit_intercept=False))
        ridge[a].append((b2 + var, miss))
    ridge[a] = np.array(ridge[a])
for p in (50, 200, 4000):
    i = ps.index(p)
    cells = "  ".join(f"alpha={a:g} {ridge[a][i, 0]:7.3f}" for a in alphas)
    print(f"p={p:<5} LinearRegression {res[i, 1] + res[i, 2]:9.3f}  {cells}")

fig, ax = plt.subplots(figsize=(7.4, 4.0))
ax.plot(res[:, 0], res[:, 1] + res[:, 2], color=INK, lw=2, marker="o", ms=3, label="LinearRegression")
for a, c in zip(alphas, [ORANGE, GREEN, BLUE]):
    ax.plot(ps, ridge[a][:, 0], color=c, lw=1.8, marker="o", ms=3, label=f"Ridge の alpha={a:g}")
ax.axvline(n, color=GRAY, ls=":", lw=1.2)
ax.set_xscale("log")
ax.set_yscale("log")
ax.set_xlabel("列の数 p（対数）")
ax.set_ylabel("テストの二乗誤差（対数）")
ax.legend(fontsize=9, frameon=False)
ax.grid(True, which="major", alpha=0.25)
fig.tight_layout()
save(fig, "bv_ridge.webp")


# ============================================================
# 実験 6: 手元の 200 行だけでバリアンスを測る（ブートストラップ）
# ============================================================
def boot_variance(p, base, seed=2):
    F = features(p)
    rng = np.random.default_rng(seed)
    preds = np.empty((R, len(test), 10))
    uniq = []
    for r in range(R):
        rows = rng.choice(base, len(base), replace=True)   # 重複を許して 200 行を選び直す
        uniq.append(len(np.unique(rows)))
        preds[r] = LinearRegression(fit_intercept=False).fit(F[rows], Y[rows]).predict(F[test])
    return np.mean(np.sum(preds.var(axis=0), axis=1)), np.mean(uniq)


boot = [boot_variance(p, rows_one) for p in ps]
bvar = np.array([b[0] for b in boot])
print(f"選び直した 200 行に含まれる、違う行の数（平均）: {np.mean([b[1] for b in boot]):.1f}")
for p in (50, 125, 200, 1000):
    i = ps.index(p)
    print(f"p={p:<5} 別の 200 行のバリアンス {res[i, 2]:9.3f}  ブートストラップのバリアンス {bvar[i]:9.3f}")

fig, ax = plt.subplots(figsize=(7.4, 4.0))
ax.plot(res[:, 0], res[:, 2], color=RED, lw=2, marker="o", ms=3, label="別の 200 行で学習を繰り返したバリアンス")
ax.plot(ps, bvar, color=BLUE, lw=2, ls="--", marker="o", ms=3, label="手元の 200 行のブートストラップ")
ax.axvline(n, color=GRAY, ls=":", lw=1.2)
ax.axvline(127, color=BLUE, ls=":", lw=1.2)
ax.text(205, 2e-2, "200", fontsize=9, color=INK)
ax.text(84, 2e-2, "約 127", fontsize=9, color=BLUE)
ax.set_xscale("log")
ax.set_yscale("log")
ax.set_xlabel("列の数 p（対数）")
ax.set_ylabel("バリアンス（対数）")
ax.legend(fontsize=9, frameon=False, loc="upper right")
ax.grid(True, which="major", alpha=0.25)
fig.tight_layout()
save(fig, "bv_bootstrap.webp")
