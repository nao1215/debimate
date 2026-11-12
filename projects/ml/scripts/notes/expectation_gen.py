"""expectation ノートの実験と図を生成するスクリプト。

本文に載せた実験（サイコロと保険金の期待値、掛け算のコイン投げ、期待値の外へ出せる計算、
log で学習した回帰モデルの予測の合計と補正）を同じ順に実行し、
出力を標準出力に、図を Page Bundle に WebP で保存する。
データは OpenML の freMTPL2freq（data_id=41214）と freMTPL2sev（data_id=41215）。
初回だけ fetch_openml がダウンロードし、以降は ~/scikit_learn_data のキャッシュを使う。
実行: cd projects/ml && .venv/bin/python scripts/notes/expectation_gen.py
確認した版: scikit-learn 1.9.1、NumPy 2.5.4、pandas、matplotlib 3.11.2
"""
from io import BytesIO
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from sklearn.compose import TransformedTargetRegressor
from sklearn.datasets import fetch_openml
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.model_selection import KFold

NOTE_DIR = Path(__file__).resolve().parents[2] / "notes" / "math" / "expectation"
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
# データ: フランスの自動車保険の保険金（1 件ごとの支払額。通貨の単位はデータに書かれていない）
# ============================================================
freq = fetch_openml(data_id=41214, as_frame=True).frame   # 契約ごとの属性
sev = fetch_openml(data_id=41215, as_frame=True).frame    # 保険金 1 件ごとの支払額
freq["IDpol"] = freq["IDpol"].astype(int)
claims = sev.merge(freq.drop(columns=["ClaimNb", "Exposure"]), on="IDpol")
y = claims["ClaimAmount"].to_numpy(float)
X = claims.drop(columns=["IDpol", "ClaimAmount"])
for col in X.select_dtypes(exclude="number"):
    X[col] = X[col].astype("category")

# ============================================================
# 実験 1: サイコロと保険金の期待値
# ============================================================
print(f"保険金 {len(y)} 件")
print(f"平均   {y.mean():8.0f}")
print(f"中央値 {np.median(y):8.0f}")
print(f"平均を超える件数の割合 {np.mean(y > y.mean()):.3f}")
top = np.sort(y)[::-1]
print(f"上位 1% の件数が合計に占める割合 {top[: len(y) // 100].sum() / y.sum():.3f}")
amounts, counts = np.unique(y, return_counts=True)
most = np.argsort(counts)[::-1][:4]
print("件数の多い額:", [(float(amounts[i]), int(counts[i])) for i in most])
print(f"この 4 つの額の件数 {counts[most].sum()}、割合 {counts[most].sum() / len(y):.3f}")

fig, ax = plt.subplots(figsize=(8, 3.6))
bins = np.logspace(0, np.log10(y.max()) + 0.05, 70)
ax.hist(y, bins=bins, color=BLUE, alpha=0.8)
ax.set_xscale("log")
for v, name, c, dy in [(np.median(y), "中央値", INK, 0.93), (y.mean(), "平均", RED, 0.80)]:
    ax.axvline(v, color=c, lw=1.6)
    ax.text(v * 1.12, ax.get_ylim()[1] * dy, f"{name} {v:,.0f}", color=c, fontsize=10)
ax.set_xlabel("1 件の支払額（対数目盛）")
ax.set_ylabel("件数")
ax.set_title("freMTPL2 の保険金 26,444 件", fontsize=11, color=INK)
save(fig, "exp_claims.webp")

# ============================================================
# 実験 2: 期待値が 1 回に 1.05 倍になるコイン投げ
# ============================================================
rng = np.random.default_rng(0)
players, rounds = 10_000, 100
factor = np.where(rng.random((players, rounds)) < 0.5, 1.5, 0.6)  # 表で 1.5 倍、裏で 0.6 倍
wealth = np.hstack([np.ones((players, 1)), np.cumprod(factor, axis=1)])
t = np.arange(rounds + 1)
for k in [10, 50, 100]:
    w = wealth[:, k]
    print(f"{k:3d} 回目: 期待値 {1.05 ** k:8.2f}  1 万人の平均 {w.mean():8.2f}  "
          f"中央値 {np.median(w):.4f}  元手を上回る人 {np.mean(w > 1):.3f}")

fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
ax = axes[0]
for i in range(30):
    ax.plot(t, wealth[i], color=GRAY, lw=0.6, alpha=0.5)
ax.plot(t, 1.05 ** t, color=RED, lw=2, label="期待値 1.05^回数")
ax.plot(t, wealth.mean(axis=0), color=RED, lw=1.4, ls="--", label="1 万人の平均")
ax.plot(t, np.median(wealth, axis=0), color=INK, lw=2, label="1 万人の中央値")
ax.set_yscale("log")
ax.axhline(1, color=GRAY, lw=0.8, ls=":")
ax.set_xlabel("投げた回数")
ax.set_ylabel("元手を 1 とした資産（対数目盛）")
ax.set_title("期待値・平均・中央値（灰色は 30 人分の資産）", fontsize=10.5, color=INK)
ax.legend(fontsize=8.5, frameon=False, loc="lower left")
ax = axes[1]
w100 = wealth[:, rounds]
lw = np.log10(w100)
step = np.log10(2.5)                        # 表が 1 回増えるごとに資産は 2.5 倍。1 本の棒が表の回数 1 つに当たる
k = np.round((lw - 100 * np.log10(0.6)) / step)
edges = 100 * np.log10(0.6) + (np.arange(k.min(), k.max() + 2) - 0.5) * step
ax.hist(lw[w100 <= 1], bins=edges, color=GRAY, alpha=0.8)
ax.hist(lw[w100 > 1], bins=edges, color=BLUE, alpha=0.9)
ax.set_ylim(0, ax.get_ylim()[1] * 1.15)
for v, name, c, ha, dx in [(np.median(w100), "中央値", INK, "right", -0.15), (1.05 ** rounds, "期待値", RED, "left", 0.15)]:
    ax.axvline(np.log10(v), color=c, lw=1.6)
    ax.text(np.log10(v) + dx, ax.get_ylim()[1] * 0.95, f"{name} {v:.3g}", color=c, fontsize=9.5, ha=ha)
ticks = list(range(int(np.ceil(edges[0] / 2) * 2), int(edges[-1]) + 1, 2))
ax.set_xticks(ticks)
ax.set_xticklabels([f"$10^{{{k}}}$" for k in ticks])
ax.set_xlabel("100 回目の資産（対数目盛）")
ax.set_ylabel("人数")
ax.set_title("100 回目の 1 万人の資産の分布", fontsize=10.5, color=INK)
# 2 つの割合の和が 100.0% になるよう、上回る側を 0.1% 単位で四捨五入し、残りを元手以下にする
up_tenths = (int(np.sum(w100 > 1)) * 1000 * 2 + len(w100)) // (2 * len(w100))
ax.text(-7.0, 480, f"元手以下\n{(1000 - up_tenths) / 10:.1f}%", color=INK, fontsize=9.5, ha="center")
ax.text(2.6, 430, f"元手を上回る\n{up_tenths / 10:.1f}%", color="#3d6f8f", fontsize=9.5, ha="left")
print(f"100 回目に元手の 100 倍を超える人 {np.mean(w100 > 100):.4f}、その人たちの資産が合計に占める割合 {w100[w100 > 100].sum() / w100.sum():.3f}")
save(fig, "exp_coin.webp")

# ============================================================
# 実験 3: 期待値の外へ出せる計算と、出せない計算
# ============================================================
faces = np.arange(1, 7)       # サイコロの目 1〜6
prob = np.full(6, 1 / 6)      # どの目も確率 1/6
X1 = faces                    # 1 個目のサイコロの目
Y1 = 7 - faces                # 裏の面の目（X1 が決まると決まる）
print("E[X + Y]   =", (prob * (X1 + Y1)).sum(), "  E[X] + E[Y] =", (prob * X1).sum() + (prob * Y1).sum())
print("E[X * Y]   =", round((prob * X1 * Y1).sum(), 3), "  E[X] * E[Y] =", (prob * X1).sum() * (prob * Y1).sum())
print("E[1000 X + 5] =", (prob * (1000 * X1 + 5)).sum(), "  1000 E[X] + 5 =", 1000 * (prob * X1).sum() + 5)

z = np.log(y)
print(f"E[log y]       = {z.mean():.3f}")
print(f"exp(E[log y])  = {np.exp(z.mean()):8.0f}")
print(f"E[y]           = {y.mean():8.0f}")
print(f"log y の標準偏差 {z.std():.3f}、正規分布なら E[y] / exp(E[log y]) = exp(分散 / 2) = {np.exp(z.var() / 2):.2f}"
      f"、実際は {y.mean() / np.exp(z.mean()):.2f}")

fig, ax = plt.subplots(figsize=(8, 4))
zz = np.linspace(4, 10.2, 300)
ax.plot(zz, np.exp(zz), color=INK, lw=1.6, label="y = exp(z)")
hist, edges = np.histogram(z, bins=60, range=(0, 15.3))
centers = (edges[:-1] + edges[1:]) / 2
ax.bar(centers, hist / hist.max() * 3500, width=edges[1] - edges[0], color=BLUE, alpha=0.6,
       label="log y の分布（高さは相対）")
gm, am = np.exp(z.mean()), y.mean()
ax.plot([z.mean(), z.mean()], [0, gm], color=INK, ls="--", lw=1.2)
ax.plot([4, z.mean()], [gm, gm], color=INK, ls="--", lw=1.2)
ax.text(4.1, gm + 250, f"exp(E[log y]) = {gm:,.0f}", color=INK, fontsize=10)
ax.axhline(am, color=RED, lw=1.6)
ax.text(4.1, am + 250, f"E[y] = {am:,.0f}", color=RED, fontsize=10)
ax.text(z.mean() + 0.1, 150, f"E[log y] = {z.mean():.2f}", color=INK, fontsize=9.5)
ax.set_xlim(4, 10.2)
ax.set_ylim(0, 6000)
ax.set_xlabel("z = log y")
ax.set_ylabel("支払額")
ax.legend(fontsize=9, frameon=False, loc="upper left", bbox_to_anchor=(0.0, 0.85))
ax.set_title("log の平均を exp で戻した値と、元の平均", fontsize=11, color=INK)
save(fig, "exp_jensen.webp")

# ============================================================
# 実験 4: log で学習した回帰モデルの予測の合計
# ============================================================
def hgb():
    return HistGradientBoostingRegressor(categorical_features="from_dtype", random_state=0)


pred = {"y で学習": np.zeros(len(y)), "log y で学習": np.zeros(len(y)), "log y で学習 + 補正": np.zeros(len(y))}
factors = []
for tr, te in KFold(5, shuffle=True, random_state=0).split(X):
    mse = hgb().fit(X.iloc[tr], y[tr])
    log = TransformedTargetRegressor(hgb(), func=np.log, inverse_func=np.exp).fit(X.iloc[tr], y[tr])
    f = np.mean(y[tr] / log.predict(X.iloc[tr]))   # 学習に使った行で、実際 ÷ 予測 の平均
    factors.append(f)
    pred["y で学習"][te] = mse.predict(X.iloc[te])
    pred["log y で学習"][te] = log.predict(X.iloc[te])
    pred["log y で学習 + 補正"][te] = log.predict(X.iloc[te]) * f

for name, p in pred.items():
    print(f"{name:<14} 合計の比 {p.sum() / y.sum():.3f}  MAE {np.abs(p - y).mean():6.0f}  "
          f"予測より実際が小さい件数 {np.mean(y < p):.3f}")
print("補正の倍率（学習に使った行、5 回）:", np.round(factors, 2))
print(f"同じ倍率を学習に使っていない行で測ると {np.mean(y / pred['log y で学習']):.2f}")

names = list(pred)
ratio = [pred[n].sum() / y.sum() for n in names]
mae = [np.abs(pred[n] - y).mean() for n in names]
colors = [BLUE, RED, GREEN]
fig, axes = plt.subplots(1, 2, figsize=(10, 3.2))
ax = axes[0]
ax.barh(names[::-1], ratio[::-1], color=colors[::-1])
ax.axvline(1, color=INK, lw=1, ls=":")
for i, v in enumerate(ratio[::-1]):
    ax.text((v if v < 0.85 else max(v, 1.0)) + 0.02, i, f"{v:.2f}", va="center", fontsize=10)
ax.set_xlim(0, 1.25)
ax.set_title("予測の合計 ÷ 実際の合計", fontsize=11, color=INK)
ax = axes[1]
ax.barh(names[::-1], mae[::-1], color=colors[::-1])
for i, v in enumerate(mae[::-1]):
    ax.text(v + 40, i, f"{v:,.0f}", va="center", fontsize=10)
ax.set_xlim(0, 2900)
ax.set_yticklabels([])
ax.set_title("MAE（支払額の単位、小さいほど良い）", fontsize=11, color=INK)
fig.suptitle("保険金 26,444 件を 5 分割の交差検証で予測", fontsize=11.5, color=INK, y=1.03)
save(fig, "exp_cover.webp")

# 予測の大きさで 10 組に分け、組ごとの予測の平均と実際の平均を比べる
# 組は、各モデル自身の予測の小さい順に作る
fig, ax = plt.subplots(figsize=(6.2, 4.6))
for name, c, mk in [("y で学習", BLUE, "o"), ("log y で学習", RED, "s"), ("log y で学習 + 補正", GREEN, "^")]:
    groups = np.array_split(np.argsort(pred[name]), 10)
    px = [pred[name][g].mean() for g in groups]
    py = [y[g].mean() for g in groups]
    ax.plot(px, py, color=c, marker=mk, ls="none", ms=6, label=name)  # 点だけ。線で結ぶと折り返して絡む
lim = [0, 6500]
ax.plot(lim, lim, color=INK, ls=":", lw=1, label="予測 = 実際")
ax.set_xlim(*lim)
ax.set_ylim(*lim)
ax.set_xlabel("組ごとの予測の平均")
ax.set_ylabel("組ごとの実際の平均")
ax.set_title("各モデルの予測の小さい順に 10 組へ分けた結果", fontsize=10.5, color=INK)
ax.legend(fontsize=9, frameon=False, loc="lower right")
save(fig, "exp_calib.webp")
for name in names:
    groups = np.array_split(np.argsort(pred[name]), 10)
    print(name, "組ごとの 実際 ÷ 予測:", np.round([y[g].mean() / pred[name][g].mean() for g in groups], 2))
    print(name, "組ごとの 予測の平均:", np.round([pred[name][g].mean() for g in groups]))
    print(name, "組ごとの 実際の平均:", np.round([y[g].mean() for g in groups]))
