"""probability-distributions ノートの実験と図を生成するスクリプト。

本文に載せた実験（借りられた自転車の台数とポアソン分布・負の二項分布、確率と確率密度、
馬に蹴られた兵士の数、平均と分散の関係、HistGradientBoostingRegressor の損失と予測の範囲、
指数分布とベータ分布、裾の重い分布で 3σ の外に出る割合）を
同じ順に実行し、出力を標準出力に、図を Page Bundle に WebP で保存する。
実行: cd projects/ml && .venv/bin/python scripts/notes/probability-distributions_gen.py
確認した版: scikit-learn 1.9.1、SciPy 1.18.1、NumPy 2.5.4、pandas 3.1.1
データ: OpenML の Bike_Sharing_Demand（id 42712、UCI の Bike Sharing Dataset の時間ごとの版）。
初回だけ fetch_openml がダウンロードし、~/scikit_learn_data に置く。
"""
from io import BytesIO
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from scipy import optimize, stats
from sklearn.datasets import fetch_openml
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.model_selection import train_test_split

NOTE_DIR = Path(__file__).resolve().parents[2] / "notes" / "math" / "probability-distributions"
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
# 実験 1（冒頭）: 平日 8 時に借りられた台数にポアソン分布と負の二項分布を当てはめる
# ============================================================
bike = fetch_openml("Bike_Sharing_Demand", version=2, as_frame=True, parser="liac-arff").frame
y = bike["count"].to_numpy()                      # 1 時間に借りられた台数
mask = ((bike["year"] == 1) & (bike["workingday"] == "True")
        & (bike["hour"] == 8) & (bike["weather"] == "clear")).to_numpy()
s = y[mask]                                       # 2012 年の平日 8 時、晴れの時間
mu, var = s.mean(), s.var(ddof=1)
print(f"時間の数 {len(s)}、平均 {mu:.1f} 台、分散 {var:.0f}、分散 / 平均 {var / mu:.1f}")

pois = stats.poisson(mu)                          # 平均だけで形が決まる
r = mu**2 / (var - mu)                            # 平均と分散が合うように負の二項分布の r を決める
nb = stats.nbinom(r, r / (r + mu))
norm = stats.norm(mu, np.sqrt(var))              # 比べるために、平均と分散を合わせた正規分布
for name, d in [("ポアソン分布", pois), ("負の二項分布", nb), ("正規分布", norm)]:
    lo, hi = d.ppf(0.025), d.ppf(0.975)           # 95% の範囲
    inside = np.mean((s >= lo) & (s <= hi))
    print(f"{name}: 95% の範囲 {lo:.0f}〜{hi:.0f} 台、入った時間 {inside:.0%}")
print(f"α = (分散 - 平均) / 平均^2 = {1 / r:.4f}、分散のうちポアソン分布の分 {mu / var:.1%}")

fig, ax = plt.subplots(figsize=(8.4, 4.2))
edges = np.arange(0, 1001, 25)
ax.hist(s, bins=edges, color="#d9d9d9", edgecolor="#ffffff", label="実際の時間の数（146 時間）")
k = np.arange(0, 1001)
ax.plot(k, pois.pmf(k) * len(s) * 25, color=RED, lw=2, label="ポアソン分布（平均 625）")
ax.plot(k, nb.pmf(k) * len(s) * 25, color=BLUE, lw=2, label="負の二項分布（平均 625、分散 17499）")
ytop = ax.get_ylim()[1]
for (name, d, c, yy) in [("ポアソン分布の 95% の範囲: 入ったのは 36%", pois, RED, -0.10),
                          ("負の二項分布の 95% の範囲: 入ったのは 96%", nb, BLUE, -0.20)]:
    lo, hi = d.ppf(0.025), d.ppf(0.975)
    ax.plot([lo, hi], [yy * ytop] * 2, color=c, lw=5, solid_capstyle="butt", clip_on=False)
    ax.text(lo - 12, yy * ytop, name, color=c, va="center", ha="right", fontsize=9)
ax.set_ylim(-0.26 * ytop, ytop)
ax.axhline(0, color=GRAY, lw=0.6)
ax.set_xlim(0, 1000)
ax.set_xlabel("1 時間に借りられた台数")
ax.set_ylabel("時間の数")
ax.set_yticks([t for t in ax.get_yticks() if t >= 0])
ax.set_title("2012 年、平日 8 時（晴れ）に借りられた台数と、当てはめた 2 つの分布", fontsize=11)
ax.legend(frameon=False, loc="upper left", fontsize=9)
save(fig, "pd_cover.webp")

# ============================================================
# 実験 2: 確率と確率密度
# ============================================================
binom = stats.binom(10, 0.3)                       # 10 回投げて、確率 0.3 の表が出る回数
print("二項分布の確率の合計:", round(binom.pmf(np.arange(11)).sum(), 6))
narrow = stats.norm(0, 0.1)                         # 平均 0、標準偏差 0.1 の正規分布
print("x = 0 の確率密度:", round(narrow.pdf(0), 3))
print("-0.1〜0.1 に入る確率:", round(narrow.cdf(0.1) - narrow.cdf(-0.1), 3))
print("x = 0 ちょうどになる確率:", narrow.cdf(0) - narrow.cdf(0))

fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
kk = np.arange(11)
axes[0].bar(kk, binom.pmf(kk), color=BLUE, width=0.7)
for x, p in zip(kk, binom.pmf(kk)):
    if p > 0.01:
        axes[0].text(x, p + 0.006, f"{p:.2f}", ha="center", fontsize=8, color=INK)
axes[0].set_xticks(kk)
axes[0].set_xlabel("表が出た回数")
axes[0].set_ylabel("確率")
axes[0].set_title("二項分布（10 回、表の確率 0.3）: 棒の高さが確率\n全ての棒の和が 1", fontsize=10)
x = np.linspace(-0.5, 0.5, 600)
axes[1].plot(x, narrow.pdf(x), color=RED, lw=2, label="標準偏差 0.1")
axes[1].plot(x, stats.norm(0, 1).pdf(x), color=GRAY, lw=1.5, ls="--", label="標準偏差 1")
xs = np.linspace(-0.1, 0.1, 100)
axes[1].fill_between(xs, narrow.pdf(xs), color=RED, alpha=0.25)
axes[1].text(0.13, 2.4, "-0.1〜0.1 の面積\n= 確率 0.683", color=RED, fontsize=9)
axes[1].text(0.02, 4.05, "高さ 3.99", color=RED, fontsize=9)
axes[1].set_ylim(0, 4.6)
axes[1].set_xlabel("x")
axes[1].set_ylabel("確率密度")
axes[1].set_title("正規分布（平均 0）: 高さは確率密度\n面積が確率で、全体の面積が 1", fontsize=10)
axes[1].legend(frameon=False, fontsize=9, loc="upper left")
fig.tight_layout()
save(fig, "pd_pmf_pdf.webp")

# ============================================================
# 実験 3: 馬に蹴られて亡くなった兵士の数（Bortkiewicz のデータ、Fisher の 10 軍団 × 20 年）
# ============================================================
deaths = np.array([0, 1, 2, 3, 4])                  # 1 軍団で 1 年に亡くなった人数
years = np.array([109, 65, 22, 3, 1])               # その人数だった軍団・年の数（計 200）
lam = (deaths * years).sum() / years.sum()
var_h = ((deaths - lam) ** 2 * years).sum() / (years.sum() - 1)
print(f"平均 {lam:.2f}、分散 {var_h:.2f}、分散 / 平均 {var_h / lam:.2f}")
expected = years.sum() * stats.poisson.pmf(deaths, lam)
print("ポアソン分布で予想した数:", expected.round(1))
binom_approx = years.sum() * stats.binom.pmf(deaths, 1000, lam / 1000)
print("1000 人がそれぞれ確率 0.00061 で亡くなる二項分布:", binom_approx.round(1))

fig, ax = plt.subplots(figsize=(6.6, 3.6))
w = 0.38
ax.bar(deaths - w / 2, years, width=w, color="#bdbdbd", label="記録（200 の軍団・年）")
ax.bar(deaths + w / 2, expected, width=w, color=RED, label="ポアソン分布（平均 0.61）で予想した数")
for d, o, e in zip(deaths, years, expected):
    ax.text(d - w / 2, o + 2, f"{o}", ha="center", fontsize=8, color=INK)
    ax.text(d + w / 2, e + 2, f"{e:.1f}", ha="center", fontsize=8, color=RED)
ax.set_xticks(deaths)
ax.set_xticklabels([f"{d} 人" for d in deaths])
ax.set_xlabel("1 軍団で 1 年に馬に蹴られて亡くなった人数")
ax.set_ylabel("軍団・年の数")
ax.legend(frameon=False, fontsize=9)
save(fig, "pd_horsekick.webp")

# ============================================================
# 実験 4: 条件を揃えた組ごとの平均と分散
# ============================================================
groups = bike.groupby(["year", "workingday", "hour", "weather"], observed=True)["count"]
stat = groups.agg(["mean", "var", "size"])
stat = stat[stat["size"] >= 20]                     # 20 時間以上ある組だけ
alpha_g = np.median((stat["var"] - stat["mean"]) / stat["mean"] ** 2)
print(f"組の数 {len(stat)}、分散 / 平均 の中央値 {np.median(stat['var'] / stat['mean']):.1f}")
print(f"分散 = 平均 + α × 平均^2 の α（中央値）: {alpha_g:.3f}")
small = stat[stat["mean"] < 10]
print(f"平均 10 台未満の組 {len(small)} 個の 分散 / 平均 の中央値: {np.median(small['var'] / small['mean']):.1f}")
large = stat[stat["mean"] >= 100]
print(f"平均 100 台以上の組 {len(large)} 個の 分散 / 平均 の中央値: {np.median(large['var'] / large['mean']):.1f}")

fig, ax = plt.subplots(figsize=(6.6, 4.6))
ax.scatter(stat["mean"], stat["var"], s=14, color=BLUE, alpha=0.7, label="自転車の組（年・平日か・時刻・天気）")
mm = np.logspace(-1, 3.1, 200)
ax.plot(mm, mm, color=RED, lw=2, label="分散 = 平均（ポアソン分布）")
ax.plot(mm, mm + alpha_g * mm**2, color=INK, lw=1.5, ls="--",
        label=f"分散 = 平均 + {alpha_g:.3f} × 平均²（負の二項分布）")
ax.scatter([lam], [var_h], marker="*", s=160, color=GREEN, zorder=5, label="馬に蹴られた兵士の数（200 の軍団・年）")
ax.set_xscale("log")
ax.set_yscale("log")
ax.set_xlabel("組の平均（自転車は台、兵士は人）")
ax.set_ylabel("組の分散")
ax.legend(frameon=False, fontsize=8.5, loc="upper left")
ax.grid(True, which="major", alpha=0.25)
save(fig, "pd_meanvar.webp")

# ============================================================
# 実験 4b: 日ごとに平均が違うポアソン分布を混ぜる（冒頭の平日 8 時・晴れの組）
# ============================================================
rng = np.random.default_rng(0)
mu, var = 625.144, 17499.3                        # 冒頭の組の平均と分散（後のコードで計算した値）
shape = mu**2 / (var - mu)
gam = stats.gamma(shape, scale=mu / shape)        # 日ごとの平均 λ のばらつき（平均 mu、分散 var - mu）
lam_days = gam.rvs(size=200_000, random_state=rng)
counts = rng.poisson(lam_days)                    # 日ごとの λ でポアソン分布の乱数を生成
print(f"λ の平均 {lam_days.mean():.0f}、λ の分散 {lam_days.var():.0f}、"
      f"台数の分散 {counts.var():.0f}（E[λ] + Var(λ) = {lam_days.mean() + lam_days.var():.0f}）")
picks = gam.ppf([0.1, 0.3, 0.5, 0.7, 0.9])
print("5 日の λ の例:", picks.round(0))

fig, ax = plt.subplots(figsize=(8.4, 4.0))
k = np.arange(0, 1001)
for i, lp in enumerate(picks):
    ax.plot(k, stats.poisson(lp).pmf(k) / len(picks), color=GRAY, lw=1.2,
            label="日ごとのポアソン分布（5 日、高さは 1/5）" if i == 0 else None)
    ax.text(lp, stats.poisson(lp).pmf(round(lp)) / len(picks) + 0.00012, f"λ={lp:.0f}",
            ha="center", fontsize=8, color=INK)
ax.plot(k, nb.pmf(k), color=BLUE, lw=2.2, label="多くの日を混ぜた分布（負の二項分布）")
ax.set_xlim(250, 1000)
ax.set_ylim(0, None)
ax.set_xlabel("1 時間に借りられた台数")
ax.set_ylabel("確率")
ax.set_title("日ごとの平均 λ が違う細い山を混ぜると、幅の広い山になる", fontsize=11)
ax.legend(frameon=False, fontsize=8.5, loc="upper right")
save(fig, "pd_mixture.webp")

# ============================================================
# 実験 5: 損失を選んで平均を予測し、その周りの 95% の範囲に入るか
# ============================================================
X = bike.drop(columns="count").copy()
for c in X.select_dtypes("category"):
    X[c] = X[c].cat.codes                           # 季節・天気などを整数の番号にする
X_tr, X_rest, y_tr, y_rest = train_test_split(X, y, test_size=0.4, random_state=0)
X_cal, X_te, y_cal, y_te = train_test_split(X_rest, y_rest, test_size=0.5, random_state=0)

sq = HistGradientBoostingRegressor(loss="squared_error", random_state=0).fit(X_tr, y_tr)
pred_sq = sq.predict(X_te)
print(f"squared_error: 負の予測 {np.sum(pred_sq < 0)} 件 / {len(y_te)} 件、最小 {pred_sq.min():.1f} 台")

po = HistGradientBoostingRegressor(loss="poisson", random_state=0).fit(X_tr, y_tr)
mu_cal, mu_te = po.predict(X_cal), po.predict(X_te)
print(f"poisson: 負の予測 {np.sum(mu_te < 0)} 件、予測の平均 {mu_te.mean():.1f} 台、実際の平均 {y_te.mean():.1f} 台")


def nb_nll(log_a):                                  # 評価用とは別の 2 割で α を最尤推定する
    rr = 1 / np.exp(log_a)
    return -stats.nbinom.logpmf(y_cal, rr, rr / (rr + mu_cal)).sum()


alpha = np.exp(optimize.minimize_scalar(nb_nll, bounds=(-10, 2), method="bounded").x)
rr = 1 / alpha
ranges = {"ポアソン分布": stats.poisson(mu_te), "負の二項分布": stats.nbinom(rr, rr / (rr + mu_te))}
print(f"負の二項分布の α: {alpha:.4f}")
inside = {}
for name, d in ranges.items():
    inside[name] = (y_te >= d.ppf(0.025)) & (y_te <= d.ppf(0.975))
    print(f"{name}: 予測した平均の周りの 95% の範囲に入った時間 {inside[name].mean():.0%}")
bins = [(0, 20), (20, 100), (100, 300), (300, 2000)]
for lo, hi in bins:
    k = (mu_te >= lo) & (mu_te < hi)
    print(f"予測 {lo}〜{hi} 台（{k.sum()} 時間）: "
          + "、".join(f"{n} {inside[n][k].mean():.0%}" for n in ranges))

fig, ax = plt.subplots(figsize=(7.4, 3.8))
xs = np.arange(len(bins))
labels = ["20 台未満", "20〜100 台", "100〜300 台", "300 台以上"]
for i, (name, c) in enumerate([("ポアソン分布", RED), ("負の二項分布", BLUE)]):
    vals = [inside[name][(mu_te >= lo) & (mu_te < hi)].mean() * 100 for lo, hi in bins]
    ax.bar(xs + (i - 0.5) * 0.38, vals, width=0.38, color=c, label=f"{name}の 95% の範囲")
    for xx, v in zip(xs + (i - 0.5) * 0.38, vals):
        ax.text(xx, v - 4.5, f"{v:.0f}%", ha="center", va="top", fontsize=9, color=INK, zorder=4)
ax.axhline(95, color=INK, lw=1, ls="--", zorder=1)
ax.text(3.62, 95, "95%", va="center", fontsize=9, color=INK)
ax.set_xticks(xs)
ax.set_xticklabels([f"予測した平均\n{x}" for x in labels])
ax.set_ylim(0, 112)
ax.set_ylabel("範囲に入った時間の割合（%）")
ax.legend(frameon=False, fontsize=9, loc="upper center", bbox_to_anchor=(0.5, 1.13), ncol=2)
save(fig, "pd_model_cover.webp")


# ============================================================
# 実験 6: 指数分布の無記憶性と、ベータ分布の更新
# ============================================================
expo = stats.expon(scale=1 / 2)                     # 1 秒あたり平均 2 件届く時の、要求の間隔
print(f"指数分布: f(0) = {expo.pdf(0):.1f}、平均 {expo.mean():.2f} 秒、分散 {expo.var():.2f}")
print(f"1 秒待っても届かない確率: {expo.sf(1):.4f}")
print(f"3 秒待って届かなかった後、さらに 1 秒届かない確率: {expo.sf(4) / expo.sf(3):.4f}")
a, b, h, t = 1, 1, 7, 3                             # Beta(1, 1) から始めて、表 7 回・裏 3 回を見る
post = stats.beta(a + h, b + t)
lo, hi = post.ppf([0.025, 0.975])
print(f"事後分布 Beta({a + h}, {b + t}): 平均 {post.mean():.3f}、95% の範囲 {lo:.2f}〜{hi:.2f}")

fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
x = np.linspace(0, 3, 600)
for lam, c, ls in [(2, RED, "-"), (1, BLUE, "-"), (0.5, GRAY, "--")]:
    axes[0].plot(x, stats.expon(scale=1 / lam).pdf(x), color=c, lw=2, ls=ls, label=f"λ = {lam}（平均 {1 / lam:g} 秒）")
axes[0].set_xlabel("次の要求が届くまでの時間（秒）")
axes[0].set_ylabel("確率密度")
axes[0].set_title("指数分布: 0 で最も高く、右へ単調に下がる", fontsize=10)
axes[0].legend(frameon=False, fontsize=9)
x = np.linspace(0.002, 0.998, 600)
for (pa, pb), c, ls in [((0.5, 0.5), GRAY, "--"), ((2, 2), BLUE, "-"), ((2, 5), GREEN, "-"), ((8, 4), RED, "-")]:
    axes[1].plot(x, stats.beta(pa, pb).pdf(x), color=c, lw=2, ls=ls, label=f"Beta({pa:g}, {pb:g})")
axes[1].set_ylim(0, 4.2)
axes[1].set_xlabel("x（0〜1 の割合）")
axes[1].set_ylabel("確率密度")
axes[1].set_title("ベータ分布: a, b で U 字・山型・偏った形になる", fontsize=10)
axes[1].legend(frameon=False, fontsize=9, loc="upper center", ncol=2)
fig.tight_layout()
save(fig, "pd_exp_beta.webp")

# ============================================================
# 実験 7: 裾の重い分布では 3σ の外が多い
# ============================================================
t3 = stats.t(3, scale=np.sqrt(1 / 3))               # 自由度 3 の t 分布を、分散が 1 になるように縮めたもの
for k in [2, 3, 4]:
    print(f"{k}σ の外: 正規分布 {2 * stats.norm.sf(k):.3%}、t 分布 {2 * t3.sf(k):.3%}")

fig, ax = plt.subplots(figsize=(7.4, 3.6))
k = np.linspace(0, 5, 300)
ax.semilogy(k, 2 * stats.norm.sf(k), color=BLUE, lw=2, label="正規分布")
ax.semilogy(k, 2 * t3.sf(k), color=RED, lw=2, label="t 分布（自由度 3、分散 1）")
for kk in [3, 4]:
    pn, pt = 2 * stats.norm.sf(kk), 2 * t3.sf(kk)
    ax.plot([kk, kk], [pn, pt], color=GRAY, lw=1, ls=":")
    ax.text(kk + 0.08, pn, f"{pn:.3%}", fontsize=9, color=BLUE, va="center")
    ax.text(kk + 0.08, pt * 1.6, f"{pt:.3%}", fontsize=9, color=RED, va="center")
ax.set_ylim(1e-7, 1.5)
ax.set_xlabel("平均から何標準偏差より外か")
ax.set_ylabel("外れる確率（対数の目盛り）")
ax.legend(frameon=False, fontsize=9, loc="lower left")
save(fig, "pd_tails.webp")
