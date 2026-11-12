"""joint-marginal-conditional ノートの実験と図を生成するスクリプト。

本文に載せた実験（UC Berkeley の 1973 年の大学院の出願、Palmer 基地のペンギンの
くちばしの長さと厚さ）を同じ順に実行し、出力を標準出力に、図を Page Bundle に
WebP で保存する。データは公開の配布元から 1 回だけ取得し、
projects/ml/datasets/joint-marginal-conditional/ に置いて使い回す（git では無視される）。
実行: cd projects/ml && .venv/bin/python scripts/notes/joint-marginal-conditional_gen.py
確認した版: NumPy 2.5.4、pandas 3.1.1、scikit-learn 1.9.1、matplotlib 3.11.2
"""
import urllib.request
from io import BytesIO
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image
from sklearn.linear_model import LinearRegression

ROOT = Path(__file__).resolve().parents[2]
NOTE_DIR = ROOT / "notes" / "math" / "joint-marginal-conditional"
DATA_DIR = ROOT / "datasets" / "joint-marginal-conditional"
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10,
                     "axes.spines.top": False, "axes.spines.right": False})
INK, GRAY = "#333333", "#999999"
FEMALE, MALE = "#e15759", "#4e79a7"
SPECIES_COLORS = {"Adelie": "#4e79a7", "Chinstrap": "#e15759", "Gentoo": "#59a14f"}


def save(fig, name):
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight", facecolor="#ffffff")
    plt.close(fig)
    buf.seek(0)
    Image.open(buf).convert("RGB").save(NOTE_DIR / name, "WEBP", quality=90, method=6)


def load_csv(name, url):
    """公開の配布元から CSV を 1 回だけ取得し、以降は手元の写しを読む。"""
    path = DATA_DIR / name
    if not path.exists():
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(url, path)
    return pd.read_csv(path)


# ---- 実験 1: UC Berkeley の出願（学科 × 性別 × 合否の同時分布） ----
ucb = load_csv("UCBAdmissions.csv",
               "https://vincentarelbundock.github.io/Rdatasets/csv/datasets/UCBAdmissions.csv")
counts = ucb.pivot_table(index=["Dept", "Gender"], columns="Admit",
                         values="Freq", aggfunc="sum")  # 6 学科 × 2 性別 × 2 合否 = 24 マス
n_total = counts.to_numpy().sum()
print(f"出願の合計: {n_total} 件")

# 学科を足し合わせて消す（周辺化）: 性別 × 合否の 2 × 2 の表
by_gender = counts.groupby(level="Gender").sum()
print("性別 × 合否の件数")
print(by_gender)
print("同時分布 P(性別, 合否)")
print((by_gender / n_total).round(3))
rate_all = by_gender["Admitted"] / by_gender.sum(axis=1)  # P(合格 | 性別)
print("P(合格 | 性別):", rate_all.round(3).to_dict())

# 学科を固定した条件付き分布: P(合格 | 性別, 学科)
rate = (counts["Admitted"] / counts.sum(axis=1)).unstack("Gender")
print("P(合格 | 性別, 学科)")
print(rate.round(3))
# 性別ごとに、出願がどの学科に向かったか: P(学科 | 性別)
apply = counts.sum(axis=1).unstack("Gender")
share = apply / apply.sum(axis=0)
print("P(学科 | 性別)")
print(share.round(3))
# 重み付き平均: P(合格 | 性別) = Σ_学科 P(合格 | 性別, 学科) × P(学科 | 性別)
print("重み付き平均の P(合格 | 性別):", (rate * share).sum(axis=0).round(3).to_dict())

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.6, 3.9), gridspec_kw={"width_ratios": [1.25, 1]})
depts = list(rate.index)
xs = np.arange(len(depts))
ax1.plot(xs, rate["Female"], "o", color=FEMALE, ms=7, label="女性")
ax1.plot(xs, rate["Male"], "s", color=MALE, ms=6, label="男性")
for x, d in zip(xs, depts):
    ax1.plot([x, x], [rate.loc[d, "Female"], rate.loc[d, "Male"]], color=GRAY, lw=1, zorder=0)
xa = len(depts) + 0.8
ax1.plot(xa, rate_all["Female"], "o", color=FEMALE, ms=9)
ax1.plot(xa, rate_all["Male"], "s", color=MALE, ms=8)
ax1.plot([xa, xa], [rate_all["Female"], rate_all["Male"]], color=INK, lw=1.5, zorder=0)
ax1.text(xa + 0.25, rate_all["Male"], f"{rate_all['Male']:.1%}", color=MALE, va="center", fontsize=9)
ax1.text(xa + 0.25, rate_all["Female"], f"{rate_all['Female']:.1%}", color=FEMALE, va="center", fontsize=9)
ax1.axvline(len(depts) + 0.2, color=GRAY, lw=0.8, ls=":")
ax1.set_xticks(list(xs) + [xa])
ax1.set_xticklabels([f"学科 {d}" for d in depts] + ["6 学科\nの合計"], fontsize=9)
ax1.set_ylabel("合格率 P(合格 | 性別, 学科)")
ax1.set_ylim(0, 0.9)
ax1.set_xlim(-0.5, xa + 1.0)
ax1.legend(loc="upper right", frameon=False, fontsize=9)
ax1.set_title("学科ごとの合格率と、合計した合格率", fontsize=10)

h = 0.38
ax2.barh(xs - h / 2, share["Female"], height=h, color=FEMALE, label="女性")
ax2.barh(xs + h / 2, share["Male"], height=h, color=MALE, label="男性")
ax2.set_yticks(xs)
dept_rate = counts["Admitted"].groupby(level="Dept").sum() / counts.sum(axis=1).groupby(level="Dept").sum()
ax2.set_yticklabels([f"学科 {d}（合格率 {dept_rate[d]:.0%}）" for d in depts], fontsize=9)
ax2.invert_yaxis()
ax2.set_xlim(0, 0.36)
ax2.set_xlabel("出願の割合 P(学科 | 性別)")
ax2.legend(loc="lower right", frameon=False, fontsize=9)
ax2.set_title("性別ごとに、出願した学科の割合", fontsize=10)
fig.tight_layout()
save(fig, "jmc_ucb.webp")

# ---- 実験 2: ペンギンのくちばしの長さと厚さ ----
peng = load_csv("penguins.csv",
                "https://raw.githubusercontent.com/allisonhorst/palmerpenguins/main/inst/extdata/penguins.csv")
peng = peng.dropna(subset=["bill_length_mm", "bill_depth_mm"])  # 欠けた 2 羽を除く
x, y = peng[["bill_length_mm"]], peng["bill_depth_mm"]
print(f"ペンギン: {len(peng)} 羽", peng["species"].value_counts().to_dict())

# 長さだけで厚さを予測する回帰と、種を足した回帰
m1 = LinearRegression().fit(x, y)
X2 = pd.get_dummies(peng[["bill_length_mm", "species"]], drop_first=True, dtype=float)
m2 = LinearRegression().fit(X2, y)
print(f"長さだけ: 長さの係数 {m1.coef_[0]:+.3f}")
print("長さ + 種:", {c: round(float(v), 3) for c, v in zip(X2.columns, m2.coef_)})
for sp, g in peng.groupby("species"):
    s = LinearRegression().fit(g[["bill_length_mm"]], g["bill_depth_mm"]).coef_[0]
    r = np.corrcoef(g["bill_length_mm"], g["bill_depth_mm"])[0, 1]
    print(f"{sp:<9} {len(g):3d} 羽: 傾き {s:+.3f}  相関 r = {r:+.2f}")
print(f"全体: 相関 r = {np.corrcoef(peng['bill_length_mm'], y)[0, 1]:+.2f}")

fig, ax = plt.subplots(figsize=(7.2, 4.4))
grid = np.linspace(32, 60, 50)
for sp, g in peng.groupby("species"):
    c = SPECIES_COLORS[sp]
    ax.scatter(g["bill_length_mm"], g["bill_depth_mm"], s=12, alpha=0.55, color=c, label=sp)
    lo, hi = g["bill_length_mm"].min(), g["bill_length_mm"].max()
    gx = pd.DataFrame({"bill_length_mm": np.linspace(lo, hi, 20)})
    for col in X2.columns[1:]:
        gx[col] = 1.0 if col == f"species_{sp}" else 0.0
    ax.plot(gx["bill_length_mm"], m2.predict(gx[X2.columns]), color=c, lw=2.2)
ax.plot(grid, m1.predict(pd.DataFrame({"bill_length_mm": grid})), color=INK, lw=2, ls="--")
ax.text(58.5, m1.predict(pd.DataFrame({"bill_length_mm": [58.5]}))[0] - 0.55,
        f"種を混ぜた回帰\n傾き {m1.coef_[0]:+.3f}", ha="right", va="top", fontsize=9, color=INK)
ax.text(33, 21.6, f"種を足した回帰（実線）: 傾き {m2.coef_[0]:+.3f}", fontsize=9, color=INK)
ax.set_xlabel("くちばしの長さ（mm）")
ax.set_ylabel("くちばしの厚さ（mm）")
ax.set_xlim(31, 60.5)
ax.set_ylim(12.5, 22.3)
ax.legend(loc="lower left", frameon=False, fontsize=9, markerscale=1.5)
save(fig, "jmc_cover.webp")

# 縦の帯で切った条件付き分布: P(厚さ | 長さ ≈ c) と、その中の種の内訳
bands = [40, 44, 48]
HALF = 1.5  # 帯の半幅（mm）
fig, axes = plt.subplots(1, 2, figsize=(10, 4.2), gridspec_kw={"width_ratios": [1.1, 1]})
ax = axes[0]
for sp, g in peng.groupby("species"):
    ax.scatter(g["bill_length_mm"], g["bill_depth_mm"], s=8, alpha=0.45, color=SPECIES_COLORS[sp], label=sp)
for c in bands:
    ax.axvspan(c - HALF, c + HALF, color=GRAY, alpha=0.22, lw=0)
    ax.text(c, 22.0, f"≈ {c}", ha="center", fontsize=8.5, color=INK)
ax.set_xlabel("くちばしの長さ（mm）")
ax.set_ylabel("くちばしの厚さ（mm）")
ax.set_ylim(12.5, 22.6)
ax.legend(loc="lower left", frameon=False, fontsize=8.5, markerscale=1.5)

ax = axes[1]
for row, c in enumerate(bands):
    b = peng[(peng["bill_length_mm"] - c).abs() < HALF]
    mean_all = b["bill_depth_mm"].mean()
    by_sp = b.groupby("species")["bill_depth_mm"].agg(["size", "mean"])
    print(f"長さ ≈ {c} の帯: {len(b)} 羽 E[厚さ|長さ] = {mean_all:.2f}",
          "  ".join(f"{sp} {int(r['size'])} 羽 {r['mean']:.2f}" for sp, r in by_sp.iterrows()))
    base = row * 1.0
    for sp, g in b.groupby("species"):
        jitter = np.random.default_rng(row).uniform(-0.28, 0.28, len(g))
        ax.scatter(g["bill_depth_mm"], base + jitter, s=9, alpha=0.6, color=SPECIES_COLORS[sp])
    ax.plot([mean_all, mean_all], [base - 0.4, base + 0.4], color=INK, lw=2)
    ax.text(mean_all + 0.12, base - 0.36, f"平均 {mean_all:.2f}", ha="left", va="center", fontsize=8.5, color=INK)
ax.set_yticks(range(len(bands)))
ax.set_yticklabels([f"長さ ≈ {c}\n（±{HALF} mm）" for c in bands], fontsize=9)
ax.set_ylim(len(bands) - 0.4, -0.8)
ax.set_xlabel("帯に入ったペンギンのくちばしの厚さ（mm）")
ax.set_xlim(12.5, 22)
ax.set_title("帯ごとの厚さの分布 P(厚さ | 長さ ≈ c)", fontsize=10)
fig.tight_layout()
save(fig, "jmc_slices.webp")

# 混ぜる比率と、混ぜたデータで引いた回帰の傾き（Adelie と Gentoo の 2 種）
ag = peng[peng["species"].isin(["Adelie", "Gentoo"])]
is_g = (ag["species"] == "Gentoo").to_numpy()
n_a, n_g = (~is_g).sum(), is_g.sum()
shares = np.linspace(0, 1, 41)
slopes = []
for p in shares:
    w = np.where(is_g, p / n_g, (1 - p) / n_a)  # Gentoo が全体の p を占めるように重みを付ける
    slopes.append(LinearRegression().fit(ag[["bill_length_mm"]], ag["bill_depth_mm"],
                                         sample_weight=w).coef_[0])
slopes = np.array(slopes)
for p, s in zip(shares, slopes):
    print(f"Gentoo の割合 {p:.1%}: 傾き {s:+.3f}")
neg = shares[slopes < 0]
print(f"傾きが負になる割合: {neg.min():.1%}〜{neg.max():.1%}")

fig, ax = plt.subplots(figsize=(7.2, 3.6))
ax.axhline(0, color=GRAY, lw=0.8)
ax.plot(shares * 100, slopes, color=INK, lw=2)
ax.plot([0], [slopes[0]], "o", color=SPECIES_COLORS["Adelie"], ms=8)
ax.plot([100], [slopes[-1]], "o", color=SPECIES_COLORS["Gentoo"], ms=8)
ax.text(2, slopes[0] + 0.02, f"Adelie だけ {slopes[0]:+.3f}", fontsize=9, color=SPECIES_COLORS["Adelie"])
ax.text(98, slopes[-1] + 0.02, f"Gentoo だけ {slopes[-1]:+.3f}", fontsize=9, ha="right",
        color=SPECIES_COLORS["Gentoo"])
i_min = int(np.argmin(slopes))
ax.text(shares[i_min] * 100, slopes[i_min] - 0.03, f"最も負 {slopes[i_min]:+.3f}（Gentoo {shares[i_min]:.0%}）",
        ha="center", va="top", fontsize=9, color=INK)
ax.set_xlabel("混ぜたデータに占める Gentoo の割合（%）")
ax.set_ylabel("回帰の傾き（長さ → 厚さ）")
ax.set_ylim(-0.3, 0.27)
save(fig, "jmc_mix.webp")
