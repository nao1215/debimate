"""linear-regression ノートの実験と図を生成するスクリプト。

本文に載せた実験（diabetes の単回帰と重回帰の係数、最小二乗法の直線と逆向きの直線、
他の列を引いた残りの傾き、s1 と s2・s3・中性脂肪の関係、行を選び直した時の係数と予測、
説明の列と目的変数に足した測りの誤差）を同じ順に実行し、出力を標準出力に、
図を Page Bundle に WebP で保存する。
実行: cd projects/ml && .venv/bin/python scripts/notes/linear-regression_gen.py
確認した版: scikit-learn 1.9.1、NumPy 2.5.4
"""
from io import BytesIO
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from sklearn.datasets import load_diabetes
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split

NOTE_DIR = Path(__file__).resolve().parents[2] / "notes" / "ml" / "linear-regression"
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
# 実験 1: 1 列だけの傾きと、10 列全部を入れた時の係数
# ============================================================
d = load_diabetes(scaled=False)               # 単位を元に戻した 442 行 × 10 列
X, y = d.data, d.target
names = d.feature_names

full = LinearRegression().fit(X, y)
print(f"{'列':<4} {'1 列だけの傾き':>12} {'10 列の係数':>10}")
single = []
for j, name in enumerate(names):
    b = LinearRegression().fit(X[:, [j]], y).coef_[0]
    single.append(b)
    print(f"{name:<4} {b:>14.3f} {full.coef_[j]:>12.3f}")
single = np.array(single)

# ============================================================
# 実験 2: 行を選び直した時の係数とテストの R²（表紙）
# ============================================================
rows = np.arange(len(y))
train, test = train_test_split(rows, test_size=0.3, random_state=0)  # 309 行で学習、133 行でテスト
rng = np.random.default_rng(0)
coefs, scores, preds = [], [], []
for _ in range(200):
    i = rng.choice(train, size=len(train), replace=True)  # 学習の行を重複を許して選び直す
    mb = LinearRegression().fit(X[i], y[i])
    coefs.append(mb.coef_)
    scores.append(mb.score(X[test], y[test]))  # テストの 133 行で測る R²
    preds.append(mb.predict(X[test]))
coefs, scores, preds = np.array(coefs), np.array(scores), np.array(preds)
for j in [4, 5, 6, 7]:
    print(f"{names[j]}: 係数が負になった回数 {(coefs[:, j] < 0).sum()} / 200")
print("テストの R² の 5% 点・中央値・95% 点:", np.percentile(scores, [5, 50, 95]).round(3))
print("テストの行ごとの予測の標準偏差（中央値）:", np.median(preds.std(axis=0)).round(1))
print("目的変数の標準偏差:", y.std().round(1))

sd = X.std(axis=0)
std_coefs = coefs * sd             # 列を 1 標準偏差増やした時の変化にそろえる
std_single = single * sd
lo, med, hi = np.percentile(std_coefs, [5, 50, 95], axis=0)
fig, (ax, ax2) = plt.subplots(1, 2, figsize=(10, 5.0), gridspec_kw={"width_ratios": [3, 1]})
order = np.arange(len(names))[::-1]
for k, j in enumerate(order):
    cross = lo[j] < 0 < hi[j]
    c = RED if cross else BLUE
    ax.plot([lo[j], hi[j]], [k, k], color=c, lw=5, solid_capstyle="butt", alpha=0.85)
    ax.plot(med[j], k, "o", color="white", mec=c, ms=6)
    ax.plot(std_single[j], k, "D", color=INK, ms=5)
ax.axvline(0, color=GRAY, lw=1)
ax.set_yticks(range(len(names)))
ax.set_yticklabels([names[j] for j in order])
ax.set_xlabel("列を 1 標準偏差増やした時の、病状の値の変化")
ax.set_title("10 列の係数（行を 200 回選び直した 90% の範囲）", fontsize=10)
ax.plot([], [], color=RED, lw=5, label="範囲が 0 をまたぐ列")
ax.plot([], [], color=BLUE, lw=5, label="範囲が 0 をまたがない列")
ax.plot([], [], "D", color=INK, ms=5, label="その列 1 列だけで求めた傾き")
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=3, fontsize=8.5, frameon=False)
ax.grid(True, axis="x", alpha=0.25)
ax2.boxplot(scores, widths=0.5, patch_artist=True,
            boxprops={"facecolor": BLUE, "alpha": 0.6}, medianprops={"color": INK})
ax2.set_ylim(0, 0.6)
ax2.set_xticks([1])
ax2.set_xticklabels(["200 回"])
ax2.set_ylabel("テストの 133 行で測った R²")
ax2.set_title("予測の精度（テストの R²）", fontsize=10)
ax2.grid(True, axis="y", alpha=0.25)
fig.tight_layout()
save(fig, "linreg_cover.webp")

# ============================================================
# 実験 3: 最小二乗法の直線と、x と y を入れ替えた直線
# ============================================================
bmi = X[:, 2]
m = LinearRegression().fit(bmi.reshape(-1, 1), y)
r = np.corrcoef(bmi, y)[0, 1]
rev = LinearRegression().fit(y.reshape(-1, 1), bmi)      # bmi を y から予測する
print(f"y を bmi で予測する直線: 傾き {m.coef_[0]:.2f}、切片 {m.intercept_:.1f}")
print(f"bmi を y で予測する直線を y = ... の形に直した傾き: {1 / rev.coef_[0]:.2f}")
print(f"相関係数 r = {r:.3f}、r² = {r * r:.3f}、2 つの傾きの比 = {m.coef_[0] * rev.coef_[0]:.3f}")
print(f"残差の 2 乗の平均: {np.mean((y - m.predict(bmi.reshape(-1, 1))) ** 2):.0f}")

fig, ax = plt.subplots(figsize=(7.2, 4.6))
xs = np.linspace(bmi.min(), bmi.max(), 50)
pick = rng.choice(len(y), size=40, replace=False)
yhat = m.predict(bmi.reshape(-1, 1))
for i in pick:
    ax.plot([bmi[i], bmi[i]], [y[i], yhat[i]], color=RED, lw=0.8, alpha=0.6)
ax.scatter(bmi, y, s=10, color=BLUE, alpha=0.55, label="患者 442 人")
ax.plot(xs, m.predict(xs.reshape(-1, 1)), color=INK, lw=2,
        label=f"y を bmi で予測する直線（傾き {m.coef_[0]:.1f}）")
x0, y0 = rev.intercept_, rev.coef_[0]
ax.plot(xs, (xs - x0) / y0, color=GREEN, lw=2, ls="--",
        label=f"bmi を y で予測する直線（傾き {1 / y0:.1f}）")
ax.plot([], [], color=RED, lw=0.8, label="縦の差（残差）。40 人分だけ描画")
ax.set_ylim(0, 380)
ax.set_xlabel("bmi")
ax.set_ylabel("1 年後の病状の値")
ax.legend(fontsize=8.5, frameon=False, loc="upper left")
ax.grid(True, alpha=0.25)
fig.tight_layout()
save(fig, "linreg_lsq.webp")

# ============================================================
# 実験 4: 他の列を引いた残りどうしの傾き（s1 の係数）
# ============================================================
others = [k for k in range(10) if k != 4]
s1 = X[:, 4]
s1_rest = s1 - LinearRegression().fit(X[:, others], s1).predict(X[:, others])
y_rest = y - LinearRegression().fit(X[:, others], y).predict(X[:, others])
b_rest = LinearRegression().fit(s1_rest.reshape(-1, 1), y_rest).coef_[0]
r2_s1 = LinearRegression().fit(X[:, others], s1).score(X[:, others], s1)
print(f"残りどうしの傾き: {b_rest:.3f}（10 列の係数 {full.coef_[4]:.3f}）")
print(f"s1 の標準偏差 {s1.std():.1f}、他の 9 列で説明できない残りの標準偏差 {s1_rest.std():.1f}")
print(f"他の 9 列から s1 を予測した R² {r2_s1:.3f}、VIF {1 / (1 - r2_s1):.1f}")

fig, axes = plt.subplots(1, 2, figsize=(10, 4.2), sharey=False)
ax = axes[0]
ax.scatter(s1 - s1.mean(), y, s=9, color=BLUE, alpha=0.5)
xs = np.linspace(-110, 110, 10)
ax.plot(xs, single[4] * xs + y.mean(), color=INK, lw=2)
ax.set_title(f"s1 と病状の値（傾き {single[4]:+.2f}）", fontsize=10)
ax.set_xlabel("s1（平均を引いた値）")
ax.set_ylabel("1 年後の病状の値")
ax = axes[1]
ax.scatter(s1_rest, y_rest, s=9, color=RED, alpha=0.5)
xs2 = np.linspace(s1_rest.min(), s1_rest.max(), 10)
ax.plot(xs2, b_rest * xs2, color=INK, lw=2)
ax.set_title(f"他の 9 列で説明できない残りどうし（傾き {b_rest:+.2f}）", fontsize=10)
ax.set_xlabel("s1 の残り")
ax.set_ylabel("病状の値の残り")
for a in axes:
    a.set_xlim(-110, 110)
    a.grid(True, alpha=0.25)
fig.tight_layout()
save(fig, "linreg_partial.webp")

# ============================================================
# 実験 5: s1 は s2・s3・中性脂肪から計算できる
# ============================================================
tg = np.exp(X[:, 8])                           # s5 は中性脂肪の対数なので、exp で戻す
calc = X[:, 5] + X[:, 6] + tg / 5              # LDL + HDL + 中性脂肪 / 5
print(f"s1 と s2 + s3 + 中性脂肪/5 の差: 最大 {np.abs(s1 - calc).max():.2f}、"
      f"相関係数 {np.corrcoef(s1, calc)[0, 1]:.6f}")

fig, ax = plt.subplots(figsize=(5.4, 4.6))
ax.scatter(calc, s1, s=10, color=BLUE, alpha=0.6)
lim = [90, 310]
ax.plot(lim, lim, color=RED, lw=1, ls="--", label="s1 = s2 + s3 + 中性脂肪 / 5")
ax.set_xlim(lim)
ax.set_ylim(lim)
ax.set_aspect("equal")
ax.set_xlabel("s2 + s3 + exp(s5) / 5")
ax.set_ylabel("s1（総コレステロール）")
ax.legend(fontsize=8.5, frameon=False, loc="upper left")
ax.grid(True, alpha=0.25)
fig.tight_layout()
save(fig, "linreg_friedewald.webp")

# ============================================================
# 実験 6: 同じ列を 2 回入れた時と、中性脂肪の列を足して関係をほぼ完全にした時
# ============================================================
twice = LinearRegression().fit(np.column_stack([bmi, bmi]), y)
print("bmi を 2 回入れた時の係数:", twice.coef_.round(2))
X11 = np.column_stack([X, tg])
m11 = LinearRegression().fit(X11, y)
o11 = [k for k in range(11) if k != 4]
r2_11 = LinearRegression().fit(X11[:, o11], s1).score(X11[:, o11], s1)
print(f"11 列の係数 s1 {m11.coef_[4]:.2f}、s2 {m11.coef_[5]:.2f}、s3 {m11.coef_[6]:.2f}、"
      f"中性脂肪 {m11.coef_[10]:.2f}、s1 の VIF {1 / (1 - r2_11):.0f}")
print(f"全行で学習した R²: 10 列 {full.score(X, y):.4f}、11 列 {m11.score(X11, y):.4f}")
rng = np.random.default_rng(0)
c11, s11 = [], []
for _ in range(200):
    i = rng.choice(train, size=len(train), replace=True)
    mm = LinearRegression().fit(X11[i], y[i])
    c11.append(mm.coef_)
    s11.append(mm.score(X11[test], y[test]))
c11, s11 = np.array(c11), np.array(s11)
print("11 列の s1 の係数の 5% 点・中央値・95% 点:", np.percentile(c11[:, 4], [5, 50, 95]).round(1))
print("11 列のテストの R² の 5% 点・中央値・95% 点:", np.percentile(s11, [5, 50, 95]).round(3))
print(f"11 列でテストの R² が 0.3 を下回った回数: {(s11 < 0.3).sum()} / 200"
      f"（10 列では {(scores < 0.3).sum()} / 200）")

fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))
ax = axes[0]
ax.scatter(coefs[:, 4], coefs[:, 5], s=12, color=BLUE, alpha=0.6)
ax.axhline(0, color=GRAY, lw=1)
ax.axvline(0, color=GRAY, lw=1)
ax.set_xlabel("s1 の係数")
ax.set_ylabel("s2 の係数")
ax.set_title("10 列: 200 回分の s1 と s2 の係数", fontsize=10)
ax.grid(True, alpha=0.25)
ax = axes[1]
jit = np.random.default_rng(1).uniform(-0.12, 0.12, 200)
ax.scatter(1 + jit, scores, s=10, color=BLUE, alpha=0.6)
ax.scatter(2 + jit, np.clip(s11, -1.0, None), s=10, color=RED, alpha=0.6)
low = s11 < -1.0
ax.scatter(2 + jit[low], np.full(low.sum(), -1.0), marker="v", s=22, color=RED)
ax.text(2.18, -0.97, f"-1 未満 {low.sum()} 回", fontsize=8.5, color=RED, va="bottom")
ax.set_xticks([1, 2])
ax.set_xticklabels(["元の 10 列", "中性脂肪を足した 11 列"])
ax.set_xlim(0.5, 2.7)
ax.set_ylim(-1.1, 0.6)
ax.set_ylabel("テストの 133 行で測った R²")
ax.set_title("200 回分のテストの R²", fontsize=10)
ax.grid(True, axis="y", alpha=0.25)
fig.tight_layout()
save(fig, "linreg_collinear.webp")

# ============================================================
# 実験 7: bmi と病状の値に、測りの誤差を足した時の傾き
# ============================================================
rng = np.random.default_rng(0)
b0 = m.coef_[0]
ks = [0.0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0]
bx, by = [], []
for k in ks:
    sx = [LinearRegression().fit((bmi + rng.normal(0, k * bmi.std(), len(y))).reshape(-1, 1), y).coef_[0]
          for _ in range(200)]                       # bmi に誤差
    sy = [LinearRegression().fit(bmi.reshape(-1, 1), y + rng.normal(0, k * y.std(), len(y))).coef_[0]
          for _ in range(200)]                       # 病状の値に誤差
    bx.append(np.mean(sx))
    by.append(np.mean(sy))
    print(f"誤差の標準偏差 = 元の標準偏差 × {k:<4}: bmi に足すと傾き {np.mean(sx):5.2f}"
          f"（式 {b0 / (1 + k * k):5.2f}）、病状の値に足すと傾き {np.mean(sy):5.2f}")

fig, ax = plt.subplots(figsize=(7.2, 4.2))
kk = np.linspace(0, 2, 100)
ax.plot(kk, b0 / (1 + kk ** 2), color=GRAY, lw=1, ls="--", label="式: 元の傾き ÷ (1 + 比²)")
ax.plot(ks, bx, "o-", color=RED, label="bmi に誤差を足した時")
ax.plot(ks, by, "s-", color=BLUE, label="病状の値に誤差を足した時")
ax.set_xlabel("足した誤差の標準偏差 ÷ 元の列の標準偏差")
ax.set_ylabel("bmi の傾き（200 回の平均）")
ax.set_ylim(0, 12)
ax.legend(fontsize=9, frameon=False, loc="center right")
ax.grid(True, alpha=0.25)
fig.tight_layout()
save(fig, "linreg_dilution.webp")
