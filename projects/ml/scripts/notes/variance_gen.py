"""variance ノートの実験と図を生成するスクリプト。

本文に載せた実験（偏差の 2 乗の平均、n と n - 1 のどちらで割るか、SQLite の AVG(ts*ts) - AVG(ts)*AVG(ts)、float64 の刻み、
ずらしてから計算する、1 件ずつ届く値の分散、日ごとの分散から月の分散）を同じ順に実行し、
出力を標準出力に、図を Page Bundle に WebP で保存する。
実行: cd projects/ml && .venv/bin/python scripts/notes/variance_gen.py
確認した版: Python 3.12、SQLite 3.50.4、NumPy 2.5.4、pandas 3.1.1、scikit-learn 1.9.1
日ごとの気温の実験は OpenML の Bike_Sharing_Demand（data_id=42712）を 1 回だけ取得して使う。
"""
import math
import sqlite3
import statistics
from io import BytesIO
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from sklearn.datasets import fetch_openml
from sklearn.preprocessing import StandardScaler

NOTE_DIR = Path(__file__).resolve().parents[2] / "notes" / "math" / "variance"
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
# 実験 1: 偏差の 2 乗の平均
# ============================================================
ms = np.array([120, 80, 100, 140, 60])  # 5 回の応答時間（ms）
dev = ms - ms.mean()
print("平均:", ms.mean())
print("偏差:", dev)
print("偏差の 2 乗:", dev**2)
print("分散:", np.mean(dev**2), " np.var:", np.var(ms))

fig, axes = plt.subplots(2, 1, figsize=(8.6, 5.8), gridspec_kw={"height_ratios": [1, 1.5], "hspace": 0.45})
ax = axes[0]
ax.axhline(0, color=GRAY, lw=0.8)
ax.axvline(ms.mean(), color=INK, lw=1.0, ls="--")
ax.text(ms.mean() + 1, 0.85, "平均 100", color=INK, fontsize=9)
for k, (v, d) in enumerate(sorted(zip(ms, dev))):
    yy = 0.15 + 0.13 * k
    if d != 0:
        ax.annotate("", xy=(v, yy), xytext=(ms.mean(), yy),
                    arrowprops=dict(arrowstyle="->", color=BLUE if d < 0 else RED, lw=1.4))
        ax.text((v + ms.mean()) / 2, yy + 0.03, f"{int(d):+d}", ha="center", va="bottom", fontsize=8.5)
    ax.plot(v, 0, "o", color=INK, ms=6, zorder=3)
ax.set_xlim(50, 150)
ax.set_ylim(-0.1, 1.0)
ax.set_yticks([])
ax.spines["left"].set_visible(False)
ax.set_xlabel("応答時間（ms）")
ax.set_title("5 回の応答時間と、平均からの差（偏差）", fontsize=10)
ax = axes[1]
x0 = 0
for v, d in zip(ms, dev):
    side = abs(d)
    c = BLUE if d < 0 else RED if d > 0 else GRAY
    if side:
        ax.add_patch(plt.Rectangle((x0, 0), side, side, facecolor=c, alpha=0.3, edgecolor=c))
    ax.text(x0 + max(side, 6) / 2, side + 2, f"{int(d**2)}", ha="center", va="bottom", fontsize=9)
    ax.text(x0 + max(side, 6) / 2, -3, f"{v} ms", ha="center", va="top", fontsize=8.5)
    x0 += max(side, 6) + 8
side = np.sqrt(800)
ax.add_patch(plt.Rectangle((x0 + 6, 0), side, side, facecolor="none", edgecolor=INK, ls="--"))
ax.text(x0 + 6 + side / 2, side + 2, "平均 800 = 分散", ha="center", va="bottom", fontsize=9)
ax.text(x0 - 1, 14, "→", fontsize=14, ha="center")
ax.set_xlim(-2, x0 + 6 + side + 4)
ax.set_ylim(-12, 50)
ax.set_aspect("equal")
ax.axis("off")
ax.set_title("偏差を 1 辺とする正方形の面積（偏差の 2 乗）と、その平均", fontsize=10)
save(fig, "var_squares.webp")

# ============================================================
# 実験 1b: n で割るか n - 1 で割るか
# ============================================================
rng_dd = np.random.default_rng(0)
samples = rng_dd.normal(0.0, 1.0, (100_000, 5))   # 分散 1 の正規分布から 5 個を引く試行を 10 万回
v0 = samples.var(axis=1, ddof=0)
v1 = samples.var(axis=1, ddof=1)
print(f"n で割った分散の平均    : {v0.mean():.4f}")
print(f"n - 1 で割った分散の平均: {v1.mean():.4f}")

pick = int(np.argmax((samples.mean(axis=1) > 0.6) & (samples.mean(axis=1) < 0.7)))  # 平均が 0 から離れた回を 1 つ選ぶ
first5 = samples[pick]
print(f"図に使った {pick + 1} 回目の 5 個の平均: {first5.mean():.2f}")
fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.4), gridspec_kw={"width_ratios": [1.25, 1], "wspace": 0.35})
ax = axes[0]
cs = np.linspace(-1.2, 2.4, 300)
ss_c = [np.sum((first5 - c) ** 2) for c in cs]
ax.plot(cs, ss_c, color=INK, lw=1.4)
xb = first5.mean()
ss_xb = np.sum((first5 - xb) ** 2)
ss_mu = np.sum(first5 ** 2)
ax.plot(xb, ss_xb, "o", color=BLUE, ms=7, zorder=3)
ax.plot(0.0, ss_mu, "s", color=RED, ms=7, zorder=3)
ax.annotate(f"5 個の平均 {xb:.2f}\n合計 {ss_xb:.2f}（最小）", (xb, ss_xb), xytext=(xb + 0.35, ss_xb + 7.0),
            fontsize=8.5, color=INK, ha="center", arrowprops=dict(arrowstyle="-", color=GRAY))
ax.annotate(f"本当の平均 0\n合計 {ss_mu:.2f}", (0.0, ss_mu), xytext=(0.05, ss_mu + 10.0),
            fontsize=8.5, color=INK, ha="center", arrowprops=dict(arrowstyle="-", color=GRAY))
ax.set_xlabel("基準にした値 c")
ax.set_ylabel("(x - c)² の合計")
ax.set_title("ある 1 回の 5 個: 手元の平均を基準にすると合計が最も小さい", fontsize=9.5)
ax = axes[1]
labels = ["n で割る", "n - 1 で割る"]
vals_dd = [v0.mean(), v1.mean()]
ax.bar(labels, vals_dd, color=[RED, BLUE], alpha=0.75, width=0.55)
ax.axhline(1.0, color=INK, ls="--", lw=1.0)
ax.text(-0.3, 1.02, "本当の分散 1", va="bottom", ha="left", fontsize=8.5)
for k, v in enumerate(vals_dd):
    ax.text(k, v / 2, f"{v:.4f}", ha="center", va="center", fontsize=9.5)
ax.set_ylim(0, 1.25)
ax.set_ylabel("10 万回の平均")
ax.set_title("5 個から求めた分散の平均", fontsize=9.5)
save(fig, "var_ddof.webp")

# ============================================================
# 実験 2: SQLite の AVG(ts*ts) - AVG(ts)*AVG(ts)
# ============================================================
t0 = 1_794_441_600_000                      # 2026-11-12 00:00:00 UTC の Unix 時間（ミリ秒）
rng = np.random.default_rng(0)
ts = np.round(t0 + rng.normal(0, 100, 10_000)).astype(np.int64)  # 標準偏差 100 ms の 1 万個の時刻

con = sqlite3.connect(":memory:")
con.execute("CREATE TABLE ev (ts INTEGER)")
con.executemany("INSERT INTO ev VALUES (?)", [(int(v),) for v in ts])
naive = con.execute("SELECT AVG(ts * ts) - AVG(ts) * AVG(ts) FROM ev").fetchone()[0]
exact = statistics.pvariance(ts.tolist())   # 整数を分数のまま計算し、最後に 1 回だけ float に直す
print(f"statistics.pvariance（正確な値）: {float(exact):,.2f}")
print(f"np.var                         : {np.var(ts):,.2f}")
print(f"AVG(ts*ts) - AVG(ts)*AVG(ts)    : {naive:,.2f}")

# 標準偏差を 1 ms から 1000 万 ms まで変える
sds = 10.0 ** np.arange(0, 7.01, 0.25)
rows = []
for sd in sds:
    v = np.round(t0 + rng.normal(0, sd, 10_000)).astype(np.int64)
    if sd == 100:
        v = ts                              # 標準偏差 100 ms の点は、上で計算した 1 回分をそのまま使う
    con.execute("DELETE FROM ev")
    con.executemany("INSERT INTO ev VALUES (?)", [(int(a),) for a in v])
    nv = con.execute("SELECT AVG(ts * ts) - AVG(ts) * AVG(ts) FROM ev").fetchone()[0]
    rows.append((float(statistics.pvariance(v.tolist())), np.var(v), nv))
rows = np.array(rows)
small = rows[rows[:, 0] < 2**29]
print(f"正しい分散が刻みより小さい {len(small)} 点: AVG 式が 0 {int((small[:, 2] == 0).sum())} 点、負 {int((small[:, 2] < 0).sum())} 点、正 {int((small[:, 2] > 0).sum())} 点")
print("AVG 式が全て刻みの整数倍か:", all(float(nv) % 2**29 == 0 for nv in rows[:, 2]))
for (ex, npv, nv), sd in zip(rows, sds):
    if sd in (1, 10, 100, 1000, 1e4, 1e5, 1e6, 1e7):
        print(f"sd={sd:>10,.0f} ms  正確 {ex:>22,.1f}  np.var {npv:>22,.1f}  AVG 式 {nv:>22,.1f}")

fig, ax = plt.subplots(figsize=(8.4, 4.8))
ax.plot(rows[:, 0], rows[:, 1], "o-", color=BLUE, ms=5, label="np.var（平均を先に求めてから偏差を 2 乗）")
ax.plot(rows[:, 0], rows[:, 2], "o", color=RED, ms=6, label="SQLite の AVG(ts*ts) - AVG(ts)*AVG(ts)")
for k in (-2, -1, 1, 2):
    ax.axhline(k * 2**29, color=RED, lw=0.6, ls=":", alpha=0.6)
ax.text(1.2, 2**29 * 3.2, "536,870,912 の整数倍", color=RED, fontsize=9)
ax.set_xscale("log")
ax.set_yscale("symlog", linthresh=1)
ax.set_xlabel("正しい分散（ms²）")
ax.set_ylabel("計算した分散（ms²、0 の上下で対数）")
ax.set_title("時刻 1 万個（ミリ秒）の分散: AVG 式は 536,870,912 の整数倍に丸まり、正しい値が刻みより小さい間は 0、負、刻みの数倍のどれかになる",
             fontsize=9.5)
ax.axhline(0, color=GRAY, lw=0.8)
ax.legend(loc="lower right", fontsize=9, frameon=False)
ax.grid(True, alpha=0.25)
save(fig, "var_cover.webp")

# ============================================================
# 実験 3: float64 の刻み
# ============================================================
sq = con.execute("DELETE FROM ev")
con.executemany("INSERT INTO ev VALUES (?)", [(int(v),) for v in ts])
a, b = con.execute("SELECT AVG(ts * ts), AVG(ts) * AVG(ts) FROM ev").fetchone()
print(f"AVG(ts*ts)       = {a:.17e}")
print(f"AVG(ts)*AVG(ts)  = {b:.17e}")
print(f"差               = {a - b:,.0f}")
print(f"この大きさで float64 が表せる数の間隔: {np.spacing(a):,.0f}")

fig, ax = plt.subplots(figsize=(8.6, 2.9))
step = np.spacing(a)
ks = np.arange(-3, 4)
base = b
for k in ks:
    ax.plot([k, k], [-0.15, 0.15], color=INK, lw=1.2)
ax.plot([-3.4, 3.4], [0, 0], color=INK, lw=1)
ax.plot(0, 0, "o", color=BLUE, ms=10, zorder=3)
ax.plot((a - b) / step, 0, "o", color=RED, ms=10, zorder=3)
ax.annotate("AVG(ts)*AVG(ts)", (0, 0.18), ha="center", va="bottom", color=BLUE, fontsize=10)
ax.annotate("AVG(ts*ts)", ((a - b) / step, 0.18), ha="center", va="bottom", color=RED, fontsize=10)
ax.annotate("", xy=(1, -0.32), xytext=(0, -0.32), arrowprops=dict(arrowstyle="<->", color=INK))
ax.text(0.5, -0.42, "次の float64 まで 536,870,912", ha="center", va="top", fontsize=9)
ax.text(0, 0.62, f"正しい差 9,961.78 は 1 刻みの約 {step / float(exact) / 1e4:.1f} 万分の 1 で、刻みの間に埋もれる",
        fontsize=9, color=GREEN, ha="center")
ax.set_xlim(-3.5, 3.5)
ax.set_ylim(-0.75, 0.85)
ax.axis("off")
ax.set_title("3.22×10^24 付近の float64 は 536,870,912 おきにしか無い", fontsize=10)
save(fig, "var_grid.webp")

# ============================================================
# 実験 4: ずらしてから AVG 式で計算する
# ============================================================
x = ts.astype(np.float64)
mu = np.mean(x)
dists = 10.0 ** np.arange(0, 12.6, 0.5)
errs = []
for d in dists:
    y = x - (mu - d)                     # 平均から d だけ離れた値 c = mu - d を引く
    v = np.mean(y * y) - np.mean(y) ** 2
    errs.append(abs(v - float(exact)) / float(exact))
y = x - x[0]                             # 最初の値を引く
first = np.mean(y * y) - np.mean(y) ** 2
print(f"最初の値 {int(ts[0]):,} を引いてから AVG 式: {first:,.2f}（平均との距離 {abs(mu - x[0]):.1f} ms）")
for d, e in zip(dists, errs):
    if d in (1, 1e4, 1e6, 1e8, 1e10):
        print(f"ずらした後の平均 {d:>18,.0f} ms  相対誤差 {e:.1e}")
print("AVG 式が 0 を返した、ずらした後の平均:", [f"{d:.2e}" for d, e in zip(dists, errs) if e == 1.0])

shifted = con.execute(
    "SELECT AVG((ts - 1794441600000) * (ts - 1794441600000))"
    " - AVG(ts - 1794441600000) * AVG(ts - 1794441600000) FROM ev").fetchone()[0]
print(f"SQLite で 1794441600000 を引いてから AVG 式: {shifted:,.2f}")

fig, ax = plt.subplots(figsize=(8.2, 4.2))
errs = np.array(errs)
plot_err = np.where(errs == 0, 1e-17, errs)
ax.plot(dists, plot_err, "o-", color=RED, ms=5)
ax.plot(dists, 1.1e-16 * (dists**2 + float(exact)) / float(exact), color=GRAY, ls="--",
        label="目安の線: 1.1e-16 ×（ずらした後の平均² + 分散）÷ 分散")
ax.axvline(t0, color=INK, lw=0.8, ls=":")
ax.text(t0 * 0.55, 3e-14, "ずらさない\n（元の時刻）", ha="right", fontsize=9)
ax.axvline(abs(mu - x[0]), color=BLUE, lw=0.8, ls=":")
ax.text(abs(mu - x[0]) * 1.4, 3e-14, "最初の値を引く", fontsize=9, color=BLUE)
zero_idx = [k for k, e in enumerate(errs) if e == 1.0]   # AVG 式がちょうど 0 を返した点
ax.annotate("AVG 式が 0 を返し、\n誤差がちょうど 1", xy=(dists[zero_idx[0]], 1.0), xytext=(3e9, 1e5),
            fontsize=9, ha="right", arrowprops=dict(arrowstyle="->", color=INK, lw=0.8))
ax.set_xscale("log")
ax.set_yscale("log")
ax.set_ylim(1e-17, 1e9)
ax.set_xlabel("ずらした後の平均（ms）")
ax.set_ylabel("AVG 式の相対誤差")
ax.set_title("同じ 1 万個から定数を引いて AVG 式で計算した時の誤差", fontsize=10)
ax.legend(loc="upper left", fontsize=9, frameon=False)
ax.grid(True, alpha=0.25)
save(fig, "var_shift.webp")

# ============================================================
# 実験 5: 1 件ずつ届く値の分散
# ============================================================
n = s = ss = 0                           # 件数・合計・2 乗の合計だけを持つ
naive_run = []
for v in ts.tolist():
    n += 1
    s += float(v)
    ss += float(v) * float(v)
    naive_run.append(ss / n - (s / n) ** 2)

n, mean, m2 = 0, 0.0, 0.0                # Welford: 件数・平均・偏差の 2 乗の合計
welford_run = []
for v in ts.tolist():
    n += 1
    delta = v - mean
    mean += delta / n
    m2 += delta * (v - mean)
    welford_run.append(m2 / n)
print(f"1 万件後  合計と 2 乗の合計: {naive_run[-1]:,.2f}  Welford: {welford_run[-1]:,.2f}"
      f"  正確な値: {float(exact):,.2f}")
neg = sum(1 for v in naive_run if v < 0)
zero = sum(1 for v in naive_run if v == 0)
print(f"合計と 2 乗の合計の途中の値: 負 {neg} 回、0 {zero} 回 / 10,000 回")

n, mean, m2 = 0, 0.0, 0.0                # 先に t0 を引いてから同じ Welford の更新をする
for v in ts.tolist():
    n += 1
    delta = (v - t0) - mean
    mean += delta / n
    m2 += delta * ((v - t0) - mean)
print(f"t0 を引いてから Welford: {m2 / n:,.2f}")

fs = math.fsum(float(v) for v in ts.tolist()) / len(ts)
fss = math.fsum(float(v) * float(v) for v in ts.tolist()) / len(ts)
print(f"math.fsum で足した合計と 2 乗の合計から: {fss - fs * fs:,.0f}")

fig, ax = plt.subplots(figsize=(8.4, 4.4))
idx = np.arange(1, len(ts) + 1)
ax.plot(idx, naive_run, color=RED, lw=0.8, label="件数・合計・2 乗の合計から計算")
ax.plot(idx, welford_run, color=BLUE, lw=1.6, label="Welford（件数・平均・偏差の 2 乗の合計を更新）")
ax.set_xscale("log")
ax.set_yscale("symlog", linthresh=1)
ax.axhline(0, color=GRAY, lw=0.8)
ax.set_xlabel("届いた件数")
ax.set_ylabel("その時点の分散（ms²、0 の上下で対数）")
ax.set_title("時刻が 1 件ずつ届くたびに分散を求める", fontsize=10)
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=2, fontsize=9, frameon=False)
ax.grid(True, alpha=0.25)
save(fig, "var_stream.webp")

# StandardScaler.partial_fit に 1,000 件ずつ 10 回に分けて渡す
sc = StandardScaler()
for chunk in np.array_split(ts.astype(np.float64).reshape(-1, 1), 10):   # 1,000 件ずつ 10 回
    sc.partial_fit(chunk)
print(f"StandardScaler.partial_fit の分散: {sc.var_[0]:,.2f}")

# Welford の 1 回の更新: 120・80・100 の後に 140 が届く
vals = [120.0, 80.0, 100.0]
old_mean = np.mean(vals)
old_m2 = float(np.sum((np.array(vals) - old_mean) ** 2))
v = 140.0
delta = v - old_mean                 # 更新前の平均から測った差
new_mean = old_mean + delta / 4
after = v - new_mean                 # 更新後の平均から測った差
new_m2 = old_m2 + delta * after
check = float(np.sum((np.array(vals + [v]) - new_mean) ** 2))
print(f"更新前: 平均 {old_mean:.0f}、偏差の 2 乗の合計 {old_m2:.0f}")
print(f"140 が届く: 更新前の平均から測った差 {delta:.0f}、更新後の平均 {new_mean:.0f}、更新後の平均から測った差 {after:.0f}")
print(f"足す量 {delta:.0f} × {after:.0f} = {delta * after:.0f}、更新後の合計 {new_m2:.0f}（4 個から直接計算すると {check:.0f}）")

fig, axes = plt.subplots(1, 2, figsize=(10.2, 3.9), gridspec_kw={"width_ratios": [1.5, 1], "wspace": 0.25})
ax = axes[0]
for yy, data, m, lab in ((1.0, vals, old_mean, "届く前（3 個）"), (0.0, vals + [v], new_mean, "140 が届いた後（4 個）")):
    ax.plot([60, 150], [yy, yy], color=GRAY, lw=0.8)
    for a_ in data:
        ax.plot(a_, yy, "o", color=RED if a_ == v and yy == 0.0 else INK, ms=7, zorder=3)
    ax.plot([m, m], [yy - 0.18, yy + 0.18], color=BLUE, lw=1.6)
    ax.text(m, yy + 0.22, f"平均 {m:.0f}", color=BLUE, ha="center", va="bottom", fontsize=9)
    ax.text(58, yy, lab, ha="right", va="center", fontsize=9)
ax.annotate("", xy=(v, 0.55), xytext=(old_mean, 0.55), arrowprops=dict(arrowstyle="->", color=RED, lw=1.4))
ax.text((v + old_mean) / 2, 0.6, f"更新前の平均から測った差 {delta:.0f}", color=RED, ha="center", va="bottom", fontsize=9)
ax.annotate("", xy=(v, -0.42), xytext=(new_mean, -0.42), arrowprops=dict(arrowstyle="->", color=GREEN, lw=1.4))
ax.text((v + new_mean) / 2, -0.47, f"更新後の平均から測った差 {after:.0f}", color=GREEN, ha="center", va="top", fontsize=9)
ax.set_xlim(12, 160)
ax.set_ylim(-0.75, 1.5)
ax.axis("off")
ax.set_title("値が 1 件届くと平均が 100 から 110 へ動く", fontsize=10)
ax = axes[1]
ax.add_patch(plt.Rectangle((0, 0), delta, after, facecolor=RED, alpha=0.25, edgecolor=RED))
ax.text(delta / 2, after / 2, f"{delta:.0f} × {after:.0f}\n= {delta * after:.0f}", ha="center", va="center", fontsize=10)
ax.text(delta / 2, -2, f"更新前の平均から測った差 {delta:.0f}", ha="center", va="top", fontsize=9, color=RED)
ax.text(-2, after / 2, f"更新後の\n平均から\n測った差\n{after:.0f}", ha="right", va="center", fontsize=9, color=GREEN)
ax.text(delta / 2, after + 3, f"偏差の 2 乗の合計 {old_m2:.0f} + {delta * after:.0f} = {new_m2:.0f}",
        ha="center", va="bottom", fontsize=9)
ax.set_xlim(-22, delta + 6)
ax.set_ylim(-10, after + 12)
ax.set_aspect("equal")
ax.axis("off")
ax.set_title("偏差の 2 乗の合計に足す量", fontsize=10)
save(fig, "var_welford.webp")

# ============================================================
# 実験 6: 日ごとの分散から月の分散を出す
# ============================================================
df = fetch_openml(data_id=42712, as_frame=True, parser="liac-arff").frame
df["day"] = (df["hour"].diff() < 0).cumsum()          # 時刻が 0 時に戻った所で日を変える
jan = df[(df["year"] == 0) & (df["month"] == 1)]      # 2011 年 1 月
daily = jan.groupby("day")["temp"].agg(n="count", mean="mean", var=lambda t: t.var(ddof=0))
print(f"日数 {len(daily)}、時間数 {int(daily['n'].sum())}")
print(f"日ごとの分散の平均         : {daily['var'].mean():.2f}")
print(f"1 月全体の分散（正しい値） : {jan['temp'].var(ddof=0):.2f}")

N = daily["n"].sum()
M = (daily["n"] * daily["mean"]).sum() / N
within = (daily["n"] * daily["var"]).sum() / N        # 日の中のばらつき（件数で重み付け）
between = (daily["n"] * (daily["mean"] - M) ** 2).sum() / N   # 日と日の差（日の平均のばらつき）
print(f"日の中のばらつき {within:.2f} + 日と日の差 {between:.2f} = {within + between:.2f}")

fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.0), gridspec_kw={"width_ratios": [2.6, 1]})
ax = axes[0]
for d, g in jan.groupby("day"):
    k = d - jan["day"].min() + 1
    ax.plot(np.full(len(g), k), g["temp"], "o", color=BLUE, ms=2.2, alpha=0.6)
    ax.plot([k - 0.4, k + 0.4], [g["temp"].mean()] * 2, color=INK, lw=1.4)
ax.plot([0.5, 31.5], [M, M], color=RED, lw=1, ls="--")
ax.text(31.6, M, "1 月の平均", color=RED, fontsize=9, va="center", ha="left")
ax.set_xlim(0.3, 35.5)
ax.set_xticks([1, 5, 10, 15, 20, 25, 31])
ax.set_xlabel("日（2011 年 1 月）")
ax.set_ylabel("1 時間ごとの気温（℃）")
ax.set_title("点は 1 時間ごとの気温、横線は日の平均", fontsize=10)
ax.grid(True, alpha=0.25)
ax = axes[1]
ax.bar([0], [daily["var"].mean()], color=BLUE, width=0.6)
ax.bar([1], [within], color=BLUE, width=0.6)
ax.bar([1], [between], bottom=[within], color=RED, width=0.6)
ax.text(0, daily["var"].mean() + 0.2, f"{daily['var'].mean():.2f}", ha="center", fontsize=9)
ax.text(1, within / 2, f"日の中\n{within:.2f}", ha="center", va="center", fontsize=9)
ax.text(1, within + between / 2, f"日と日の差\n{between:.2f}", ha="center", va="center",
        fontsize=9, color="#ffffff")
ax.text(1, within + between + 0.2, f"{within + between:.2f}", ha="center", fontsize=9)
ax.set_xticks([0, 1], ["日ごとの分散\nを平均", "1 月全体\nの分散"])
ax.set_ylabel("分散（℃²）")
ax.set_ylim(0, 11.5)
ax.set_title("分散の比較", fontsize=10)
save(fig, "var_merge.webp")


def merge(a, b):
    """(件数, 平均, 偏差の 2 乗の合計) の 2 組を 1 組にまとめる。"""
    na, ma, m2a = a
    nb, mb, m2b = b
    n = na + nb
    delta = mb - ma
    return n, ma + delta * nb / n, m2a + m2b + delta**2 * na * nb / n


rows = [(r["n"], r["mean"], r["var"] * r["n"]) for _, r in daily.iterrows()]  # 分散 × 件数 = 偏差の 2 乗の合計
acc = rows[0]
for r in rows[1:]:
    acc = merge(acc, r)
print(f"日ごとの (件数, 平均, 分散) を順にまとめた分散: {acc[2] / acc[0]:.2f}")

# ============================================================
# 実験 7: n 個を平均した値の分散
# ============================================================
rng = np.random.default_rng(1)
ns = np.array([1, 2, 4, 8, 16, 32, 64, 128])
trials = 20_000
res = {}
for rho in (0.0, 0.3):
    vs = []
    for k in ns:
        common = rng.normal(size=(trials, 1))           # 全員に共通する揺れ
        own = rng.normal(size=(trials, k))              # 1 個ずつの揺れ
        z = np.sqrt(rho) * common + np.sqrt(1 - rho) * own   # 分散 1、互いの相関 rho
        vs.append(z.mean(axis=1).var())
    res[rho] = np.array(vs)
    print(f"相関 {rho}: " + "  ".join(f"n={k} {v:.3f}" for k, v in zip(ns, vs)))

fig, ax = plt.subplots(figsize=(7.6, 4.2))
nn = np.linspace(1, 128, 400)
ax.plot(nn, 1 / nn, color=BLUE, lw=1.2, label="式 1/n（相関 0）")
ax.plot(nn, 0.3 + 0.7 / nn, color=RED, lw=1.2, label="式 0.3 + 0.7/n（相関 0.3）")
ax.plot(ns, res[0.0], "o", color=BLUE, ms=6, label="実測（相関 0）")
ax.plot(ns, res[0.3], "s", color=RED, ms=6, label="実測（相関 0.3）")
ax.axhline(0.3, color=RED, lw=0.8, ls=":")
ax.set_xscale("log", base=2)
ax.set_xticks(ns, [str(k) for k in ns])
ax.set_xlabel("平均した個数 n")
ax.set_ylabel("平均の分散（1 個の分散を 1 とする）")
ax.set_title("分散 1 の値を n 個平均した時の分散", fontsize=10)
ax.legend(fontsize=9, frameon=False)
ax.grid(True, alpha=0.25)
save(fig, "var_average.webp")
