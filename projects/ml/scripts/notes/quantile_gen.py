"""quantile ノートの実験と図を生成するスクリプト。

本文に載せた実験（10 個の応答時間の 90 パーセンタイル、点の数と p99 のずれ、
サーバーごとの p99 の平均、IQR による外れ値の判定、分位回帰）を同じ順に実行し、
出力を標準出力に、図を Page Bundle に WebP で保存する。
実行: cd projects/ml && .venv/bin/python scripts/notes/quantile_gen.py
確認した版: NumPy 2.5.4、pandas 3.1.1、scikit-learn 1.9.1、matplotlib 3.11.2

PostgreSQL・DuckDB・LibreOffice Calc の値は、本文に載せた SQL と式を各ツールで
実行して得た値をそのまま書き写している（PostgreSQL 18.6、DuckDB 1.5.5、
LibreOffice 26.2.6.3）。NumPy の同じ方法の値と一致することを assert で確かめる。
"""
from io import BytesIO
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image
from sklearn.ensemble import GradientBoostingRegressor

NOTE_DIR = Path(__file__).resolve().parents[2] / "notes" / "math" / "quantile"
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10,
                     "axes.spines.top": False, "axes.spines.right": False})
BLUE, RED, GREEN, ORANGE, INK, GRAY = "#7aa6c2", "#e15759", "#59a14f", "#f28e2b", "#333333", "#999999"


def save(fig, name):
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight", facecolor="#ffffff")
    plt.close(fig)
    buf.seek(0)
    Image.open(buf).convert("RGB").save(NOTE_DIR / name, "WEBP", quality=90, method=6)


# ---- 実験 1: 同じ 10 個の応答時間の 90 パーセンタイル ----
latency_ms = [12, 13, 14, 15, 16, 18, 20, 25, 40, 900]
print("NumPy の既定（linear）:", np.quantile(latency_ms, 0.9).round(2))
print("pandas の既定:", round(pd.Series(latency_ms).quantile(0.9), 2))
for method in ["inverted_cdf", "linear", "hazen", "weibull"]:
    print(f"method={method}:", np.quantile(latency_ms, 0.9, method=method).round(2))

# 各ツールで実行して得た値（本文の SQL と式の出力）
measured = [
    ("PostgreSQL percentile_disc", 40), ("DuckDB quantile_disc", 40), ("DuckDB quantile", 40),
    ("NumPy quantile", 126), ("pandas quantile", 126), ("PostgreSQL percentile_cont", 126),
    ("DuckDB quantile_cont", 126), ("Calc PERCENTILE.INC", 126),
    ("DuckDB approx_quantile", 470),
    ("Calc PERCENTILE.EXC", 814),
]
same_as = {40: "inverted_cdf", 126: "linear", 470: "hazen", 814: "weibull"}
for _, v in measured:
    assert round(float(np.quantile(latency_ms, 0.9, method=same_as[v])), 6) == v

fig, ax = plt.subplots(figsize=(8.4, 4.4))
ys = np.arange(len(measured))[::-1]
group_color = {40: BLUE, 126: GREEN, 470: ORANGE, 814: RED}
for y, (label, v) in zip(ys, measured):
    ax.scatter(latency_ms, [y] * len(latency_ms), s=14, color="#d0d0d0", zorder=1)
    ax.scatter([v], [y], s=70, color=group_color[v], zorder=3)
    ax.text(v, y + 0.32, f"{v} ms", ha="center", va="bottom", fontsize=9, color=INK)
ax.set_yticks(ys)
ax.set_yticklabels([m[0] for m in measured], fontsize=9)
ax.set_xscale("log")
ax.set_xlim(9, 1500)
ax.set_xticks([10, 20, 50, 100, 200, 500, 1000])
ax.set_xticklabels(["10", "20", "50", "100", "200", "500", "1000"])
ax.set_xlabel("応答時間（ms、対数の軸）。灰色の点は 10 個の元の値")
ax.set_title("同じ 10 個の応答時間の 90 パーセンタイル", fontsize=11, loc="left", pad=16)
ax.grid(axis="x", color="#eeeeee")
save(fig, "q_cover.webp")


# ---- 実験 2: 9 番目と 10 番目の間のどこを取るか ----
n = len(latency_ms)
pos = {"percentile_disc など": 9.0, "NumPy の既定など": (n - 1) * 0.9 + 1,
       "hazen（approx_quantile と同じ値）": n * 0.9 + 0.5, "PERCENTILE.EXC": (n + 1) * 0.9}
print("位置:", {k: round(v, 2) for k, v in pos.items()})

fig, ax = plt.subplots(figsize=(8, 3.6))
ranks = np.arange(1, n + 1)
ax.plot(ranks, latency_ms, color=GRAY, linewidth=1, zorder=1)  # 縦軸は普通の目盛なので、直線が補間そのもの
ax.scatter(ranks, latency_ms, s=30, color=INK, zorder=2)
for (label, p), c, ty in zip(pos.items(), [BLUE, GREEN, ORANGE, RED], [130, 280, 470, 814]):
    v = np.interp(p, ranks, latency_ms)
    ax.scatter([p], [v], s=80, color=c, zorder=3)
    ax.annotate(f"{label}\n{p:.1f} 番目 → {v:.0f} ms", (p, v), xytext=(5.4, ty),
                textcoords="data", fontsize=9, color=c, va="center",
                arrowprops=dict(arrowstyle="-", color=c, lw=0.8))
ax.set_ylim(0, 950)
ax.set_xticks(ranks)
ax.set_xlabel("小さい順に並べた時の順位")
ax.set_ylabel("応答時間（ms）")
ax.grid(color="#eeeeee")
save(fig, "q_positions.webp")


# ---- 実験 2b: 各方法が順位に割り当てる割合（目盛り）----
scales = [
    ("percentile_disc など", BLUE, None),  # 段で描く
    ("NumPy の既定など（linear）", GREEN, lambda i: (i - 1) / (n - 1)),
    ("approx_quantile と同じ値（hazen）", ORANGE, lambda i: (i - 0.5) / n),
    ("PERCENTILE.EXC（weibull）", RED, lambda i: i / (n + 1)),
]
fig, axes = plt.subplots(len(scales), 1, figsize=(9, 5.6), sharex=True)
for ax, (label, c, f) in zip(axes, scales):
    ax.set_xlim(0.3, 10.9)
    ax.set_ylim(-0.9, 1.2)
    ax.axis("off")
    ax.text(0.3, 1.05, label, color=c, fontsize=10, va="bottom")
    ax.hlines(0, 0.5, 10.5, color=GRAY, linewidth=1)
    if f is None:
        for i in ranks:  # i 番目は (i-1)/n から i/n までの幅を受け持つ
            ax.add_patch(plt.Rectangle((i - 0.45, -0.25), 0.9, 0.5, color=c, alpha=0.18 if i != 9 else 0.6))
            ax.text(i, 0.42, f"〜{i * 10}%", ha="center", fontsize=8, color=INK)
        ax.text(9, -0.62, "90% に初めて届くのは 9 番目", ha="center", fontsize=8.5, color=c)
    else:
        for i in ranks:
            ax.plot([i, i], [-0.15, 0.15], color=INK, linewidth=1)
            ax.text(i, 0.42, f"{f(i) * 100:.1f}%", ha="center", fontsize=8, color=INK)
        # 90% の位置を、両隣の目盛りから線形に求める
        p90 = np.interp(0.9, [f(i) for i in ranks], ranks)
        ax.scatter([p90], [0], s=60, color=c, zorder=3)
        ax.text(p90, -0.62, f"90% は {p90:.1f} 番目", ha="center", fontsize=8.5, color=c)
axes[-1].axis("on")
for side in ("left", "right", "top"):
    axes[-1].spines[side].set_visible(False)
axes[-1].set_yticks([])
axes[-1].set_xticks(ranks)
axes[-1].set_xlabel("小さい順に並べた時の順位（各段の上の数字が、その順位を何 % の位置とみなすか）")
fig.tight_layout()
save(fig, "q_scales.webp")


# ---- 実験 3: 点の数と p99 のずれ ----
rng = np.random.default_rng(0)
true_p99 = 20 * np.exp(0.6 * 2.3263)  # 中央値 20 ms、sigma 0.6 の対数正規分布の 99% 点
sizes = [10, 20, 50, 100, 200, 500, 1000, 2000, 5000, 10000]
methods = ["inverted_cdf", "linear", "weibull"]
gap, spread = [], []
for size in sizes:
    est = np.array([[np.quantile(s, 0.99, method=m) for m in methods]
                    for s in rng.lognormal(np.log(20), 0.6, size=(500, size))])
    gap.append(np.median(est.max(axis=1) - est.min(axis=1)) / true_p99)  # 同じデータでの方法の差
    lo, hi = np.quantile(est[:, 1], [0.1, 0.9])  # 取り直すたびの linear の値の幅（中央の 80%）
    spread.append((hi - lo) / true_p99)
    print(f"{size:>5} 件: 方法の差 {gap[-1]:.1%}、取り直しの幅 {spread[-1]:.1%}")
print(f"真の p99: {true_p99:.1f} ms")

fig, ax = plt.subplots(figsize=(7.6, 3.8))
ax.plot(sizes, np.array(gap) * 100, marker="o", color=RED, label="同じデータで、3 つの方法の差")
ax.plot(sizes, np.array(spread) * 100, marker="o", color=BLUE, label="データを取り直した時の値の幅（中央の 80%）")
ax.axvline(100, color=GRAY, linestyle="--", linewidth=1)
ax.text(105, 92, "100 件", color=GRAY, fontsize=9)
ax.set_xscale("log")
ax.set_xticks(sizes)
ax.set_xticklabels([f"{s:,}" for s in sizes], fontsize=8.5)
ax.set_xlabel("1 回に集めた応答の件数")
ax.set_ylabel("本当の p99 に対する割合（%）")
ax.set_ylim(0, 100)
ax.legend(frameon=False, fontsize=9)
ax.grid(color="#eeeeee")
save(fig, "q_sample_size.webp")


# ---- 実験 4: サーバーごとの p99 を平均する ----
rng = np.random.default_rng(1)
servers = {
    "サーバー A": rng.lognormal(np.log(40), 0.6, 9000),  # 応答の 9 割を受け、遅い
    "サーバー B": rng.lognormal(np.log(20), 0.5, 500),
    "サーバー C": rng.lognormal(np.log(20), 0.5, 500),
}
p99s = {k: np.quantile(v, 0.99) for k, v in servers.items()}
avg_p99 = np.mean(list(p99s.values()))
all_p99 = np.quantile(np.concatenate(list(servers.values())), 0.99)
for k, v in p99s.items():
    print(f"{k}: {len(servers[k])} 件、p99 {v:.1f} ms")
print(f"3 台の p99 の平均: {avg_p99:.1f} ms、全ての応答をまとめた p99: {all_p99:.1f} ms")

fig, ax = plt.subplots(figsize=(7.6, 3.2))
labels = list(p99s) + ["3 台の p99 の平均", "全ての応答の p99"]
vals = list(p99s.values()) + [avg_p99, all_p99]
colors = [BLUE, BLUE, BLUE, RED, GREEN]
slo = 100  # 説明用の目標値
yy = np.arange(len(labels))[::-1]
ax.barh(yy, vals, color=colors, height=0.6)
for y, v in zip(yy, vals):
    ax.text(v + 3, y, f"{v:.0f} ms", va="center", fontsize=9)
ax.set_yticks(yy)
ax.set_yticklabels([f"{l}（{len(servers[l]):,} 件）" if l in servers else l for l in labels], fontsize=9)
ax.axvline(slo, color=GRAY, linestyle="--", linewidth=1)
ax.text(slo + 2, yy[0] + 0.45, "目標 100 ms", color=GRAY, fontsize=8.5)
ax.set_xlabel("p99（ms）")
ax.set_xlim(0, max(vals) * 1.15)
save(fig, "q_average.webp")


# ---- 実験 5: IQR のフェンスと外れ値 ----
rng = np.random.default_rng(0)
base = rng.normal(50, 8, 200)
data = np.concatenate([base, [10, 15, 95, 110, 130]])
for name, d in [("混ぜる前", base), ("5 個混ぜた後", data)]:
    a, b = np.quantile(d, [0.25, 0.75])
    print(f"{name}: IQR={b - a:.2f} 標準偏差={d.std():.2f}")
q1, q3 = np.quantile(data, [0.25, 0.75])
iqr = q3 - q1
lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
flagged = np.sort(data[(data < lo) | (data > hi)])
print(f"フェンス [{lo:.1f}, {hi:.1f}]、外れ値 {flagged.tolist()}")

lat = rng.lognormal(np.log(20), 0.6, 500)  # 前の節と同じ形の応答時間 500 件
l1, l3 = np.quantile(lat, [0.25, 0.75])
l_hi = l3 + 1.5 * (l3 - l1)
print(f"応答時間 500 件: 上のフェンス {l_hi:.1f} ms、超えた件数 {(lat > l_hi).sum()}、"
      f"下のフェンスを下回った件数 {(lat < l1 - 1.5 * (l3 - l1)).sum()}")

fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.4))
ax = axes[0]
inside = data[(data >= lo) & (data <= hi)]
ax.scatter(inside, rng.uniform(-0.3, 0.3, len(inside)), s=8, color=BLUE, alpha=0.6)
ax.scatter(flagged, np.zeros(len(flagged)), s=50, color=RED, marker="x")
ax.axvspan(q1, q3, color=GREEN, alpha=0.15)
for f in (lo, hi):
    ax.axvline(f, color=RED, linestyle="--", linewidth=1)
ax.set_yticks([])
ax.set_title("正規分布 200 点 + 極端な値 5 個", fontsize=10, loc="left")
ax.set_xlabel("値（緑の帯が IQR、赤い破線がフェンス）")
ax.text(hi + 2, 0.22, f"上のフェンス {hi:.1f}", color=RED, fontsize=8.5)
ax.text(lo - 2, 0.22, f"下のフェンス {lo:.1f}", color=RED, fontsize=8.5, ha="right")
ax.set_xlim(-30, 140)
ax = axes[1]
ax.hist(lat, bins=40, color=BLUE, edgecolor="white")
ax.axvspan(l1, l3, color=GREEN, alpha=0.15)
ax.axvline(l_hi, color=RED, linestyle="--", linewidth=1)
ax.text(l_hi + 2, ax.get_ylim()[1] * 0.85, f"上のフェンス {l_hi:.0f} ms\n超えた {(lat > l_hi).sum()} 件",
        color=RED, fontsize=8.5)
ax.set_title("応答時間 500 件（右に長い分布）", fontsize=10, loc="left")
ax.set_xlabel("応答時間（ms、緑の帯が IQR）")
ax.set_ylabel("件数")
save(fig, "q_iqr.webp")


# ---- 実験 6: 分位回帰で 80% の予測区間 ----
rng2 = np.random.default_rng(7)
x = np.linspace(0, 10, 200)
y = np.sin(x) * 3 + 0.5 * x + rng2.normal(0, 0.2 + 0.3 * x, 200)
X = x.reshape(-1, 1)


def fit(q):
    return GradientBoostingRegressor(loss="quantile", alpha=q, n_estimators=100,
                                     max_depth=3, random_state=0).fit(X, y)


q_low, q_med, q_high = fit(0.1), fit(0.5), fit(0.9)
inside = (q_low.predict(X) <= y) & (y <= q_high.predict(X))
rng3 = np.random.default_rng(99)
x_new = rng3.uniform(0, 10, 5000)
y_new = np.sin(x_new) * 3 + 0.5 * x_new + rng3.normal(0, 0.2 + 0.3 * x_new)
X_new = x_new.reshape(-1, 1)
inside_new = (q_low.predict(X_new) <= y_new) & (y_new <= q_high.predict(X_new))
print(f"学習データで区間に収まった割合: {inside.mean():.0%}、新しいデータ: {inside_new.mean():.0%}")

fig, ax = plt.subplots(figsize=(7.6, 3.8))
grid = np.linspace(0, 10, 500).reshape(-1, 1)
ax.scatter(x, y, s=10, color=GRAY, alpha=0.7, label="学習データ（200 点）")
ax.fill_between(grid.ravel(), q_low.predict(grid), q_high.predict(grid), color=GREEN, alpha=0.25,
                label="q = 0.1〜0.9 の予測（80% の区間）")
ax.plot(grid.ravel(), q_med.predict(grid), color=RED, label="q = 0.5 の予測（中央値）")
ax.set_xlabel("x")
ax.set_ylabel("y")
ax.legend(frameon=False, fontsize=9, loc="upper left")
ax.set_title(f"区間に収まった割合: 学習データ {inside.mean():.0%}、同じ式で作った新しいデータ 5,000 点 {inside_new.mean():.0%}",
             fontsize=10, loc="left")
save(fig, "q_regression.webp")
