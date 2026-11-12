"""lln-clt ノートの実験と図を生成するスクリプト。

本文に載せた実験（95% 信頼区間が真の平均を含む割合、標本平均の推移、標準誤差、
標本平均の分布と歪度、平均と標準偏差の散布図、テストデータの正解率、独立でない行）を
同じ順に実行し、出力を標準出力に、図を Page Bundle に WebP で保存する。
実行: cd projects/ml && .venv/bin/python scripts/notes/lln-clt_gen.py
確認した版: scikit-learn 1.9.1、NumPy 2.5.4、SciPy 1.18.1、matplotlib 3.11.2
California Housing は fetch_california_housing が初回だけ配布元から取得し、以後は手元の写しを使う。
"""
from io import BytesIO
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from scipy import stats
from sklearn.datasets import fetch_california_housing, load_digits
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

NOTE_DIR = Path(__file__).resolve().parents[2] / "notes" / "math" / "lln-clt"
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
# 実験 1: 95% 信頼区間が真の平均を含む割合
# ============================================================
data = fetch_california_housing()
names = data.feature_names
med_inc = data.data[:, names.index("MedInc")]     # 地区の所得の中央値（1 万ドル単位）
ave_occ = data.data[:, names.index("AveOccup")]   # 地区の人口 ÷ 世帯数
print("行数:", len(ave_occ))
for name, x in [("MedInc", med_inc), ("AveOccup", ave_occ)]:
    print(f"{name:<8} 平均 {x.mean():.3f}  中央値 {np.median(x):.3f}  最大 {x.max():.1f}  "
          f"標準偏差 {x.std():.3f}  歪度 {stats.skew(x):.1f}")

rng = np.random.default_rng(0)                     # 1 回だけ作り、以後は続きを引く


def draw(x, n, reps):
    """x から重複を許して n 件を選ぶ操作を reps 回行い、平均と標準偏差を返す。"""
    means, sds = [], []
    batch = max(1, 2_000_000 // n)                 # メモリに載る分ずつ選ぶ
    while len(means) < reps:
        b = min(batch, reps - len(means))
        s = x[rng.integers(0, len(x), (b, n))]
        means.extend(s.mean(axis=1))
        sds.extend(s.std(axis=1, ddof=1) if n > 1 else np.zeros(b))
    return np.array(means), np.array(sds)


def coverage(x, n, reps=10000):
    """t 分布の 95% 信頼区間が、20640 行の平均（真の平均）を含んだ割合。"""
    m, s = draw(x, n, reps)
    half = stats.t.ppf(0.975, n - 1) * s / np.sqrt(n)
    return np.mean(np.abs(m - x.mean()) <= half)


ns = [10, 30, 100, 300, 1000, 3000, 10000, 30000, 100000]
cov = {name: [coverage(x, n) for n in ns] for name, x in [("MedInc", med_inc), ("AveOccup", ave_occ)]}
for name, c in cov.items():
    print(f"{name:<8}", "  ".join(f"n={n}: {v:.1%}" for n, v in zip(ns, c)))

fig, ax = plt.subplots(figsize=(8, 4.2))
ax.axhline(0.95, color=GRAY, ls="--", lw=1)
ax.text(ns[0], 0.965, "狙った 95%", color=GRAY, fontsize=9)
ax.plot(ns, cov["MedInc"], "o-", color=BLUE, lw=2, label="MedInc（所得の中央値、歪度 1.6）")
ax.plot(ns, cov["AveOccup"], "o-", color=RED, lw=2, label="AveOccup（地区の人口÷世帯数、歪度 97.6）")
for n in (30, 1000, 100000):
    i = ns.index(n)
    v = cov["AveOccup"][i]
    ax.annotate(f"n={n}\n{v:.0%}", (n, v), textcoords="offset points", xytext=(0, -30),
                ha="center", color=RED, fontsize=9)
ax.set_xscale("log")
ax.set_ylim(0.15, 1.02)
ax.set_xlabel("1 回に選ぶ件数 n（対数）")
ax.set_ylabel("真の平均を含んだ割合")
ax.set_title("California Housing の 20640 地区から重複を許して n 件を選び、平均の 95% 信頼区間を作った 10000 回", fontsize=10)
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=2, fontsize=9, frameon=False)
ax.grid(True, alpha=0.25)
save(fig, "lln_cover.webp")

top = np.argsort(-ave_occ)[:4]
pop = data.data[:, names.index("Population")]
for i in top:
    print(f"AveOccup {ave_occ[i]:7.1f}  人口 {pop[i]:6.0f}  世帯数 {pop[i] / ave_occ[i]:4.0f}")
big = ave_occ > 20
print(f"AveOccup が 20 を超える地区: {big.sum()} 件、除いた平均 {ave_occ[~big].mean():.3f}、"
      f"除いた標準偏差 {ave_occ[~big].std():.3f}")

# ============================================================
# 実験 2: 標本平均の推移（大数の法則）
# ============================================================
N = 100000
paths = {
    "MedInc": [np.cumsum(med_inc[rng.integers(0, len(med_inc), N)]) / np.arange(1, N + 1) for _ in range(5)],
    "AveOccup": [np.cumsum(ave_occ[rng.integers(0, len(ave_occ), N)]) / np.arange(1, N + 1) for _ in range(5)],
    "Cauchy": [np.cumsum(rng.standard_cauchy(N)) / np.arange(1, N + 1) for _ in range(5)],
}
for name, ps in paths.items():
    print(f"{name:<8} n=100 / 10000 / 100000 の平均（5 本）:",
          [tuple(round(float(p[k - 1]), 3) for k in (100, 10000, 100000)) for p in ps])

fig, axes = plt.subplots(1, 3, figsize=(12, 3.8))
specs = [("MedInc", med_inc.mean(), (3.0, 4.8), "MedInc（所得の中央値）"),
         ("AveOccup", ave_occ.mean(), (2.6, 3.8), "AveOccup（地区の人口÷世帯数）"),
         ("Cauchy", 0.0, (-6, 6), "コーシー分布（期待値が無い）")]
k = np.arange(1, N + 1)
for ax, (name, mu, ylim, title) in zip(axes, specs):
    for p in paths[name]:
        ax.plot(k, p, color=RED if name != "MedInc" else BLUE, lw=0.9, alpha=0.75)
    ax.axhline(mu, color=INK, ls="--", lw=1)
    ax.text(1.3, ylim[1] - 0.08 * (ylim[1] - ylim[0]),
            f"真の平均 {mu:.3f}" if name != "Cauchy" else "中心 0（期待値ではない）", fontsize=9)
    ax.set_xscale("log")
    ax.set_ylim(*ylim)
    ax.set_title(title, fontsize=10)
    ax.set_xlabel("足した件数 n（対数）")
    ax.grid(True, alpha=0.25)
axes[0].set_ylabel("ここまでの平均")
fig.tight_layout()
save(fig, "lln_running.webp")

# ============================================================
# 実験 3: 標本平均のばらつきは σ / √n
# ============================================================
ns_se = [10, 30, 100, 300, 1000, 3000, 10000]
fig, ax = plt.subplots(figsize=(7, 4.2))
for name, x, color in [("MedInc", med_inc, BLUE), ("AveOccup", ave_occ, RED)]:
    sd_of_mean, med_s = [], []
    for n in ns_se:
        m, s = draw(x, n, 4000)
        sd_of_mean.append(m.std())
        med_s.append(np.median(s) / np.sqrt(n))
    print(f"{name:<8} 平均の標準偏差 / σ/√n / 標本の s/√n（中央値）:",
          [(n, round(a, 4), round(x.std() / np.sqrt(n), 4), round(b, 4))
           for n, a, b in zip(ns_se, sd_of_mean, med_s)])
    ax.plot(ns_se, x.std() / np.sqrt(ns_se), "-", color=color, lw=1.2, alpha=0.6)
    ax.plot(ns_se, sd_of_mean, "o", color=color, label=f"{name}: 4000 回選び直した平均の標準偏差")
    ax.plot(ns_se, med_s, "x", color=color, ms=8, mew=2, label=f"{name}: 1 回の標本から出した " + r"$s/\sqrt{n}$" + "（中央値）")
ax.set_xscale("log")
ax.set_yscale("log")
ax.set_xlabel("1 回に選ぶ件数 n（対数）")
ax.set_ylabel("平均のばらつき（対数）")
ax.set_title(r"線は $\sigma/\sqrt{n}$。点（実際のばらつき）は線に乗り、× は AveOccup だけ線から外れる", fontsize=10)
ax.legend(fontsize=8, frameon=False, loc="lower left")
ax.grid(True, which="both", alpha=0.2)
save(fig, "lln_se.webp")

# ============================================================
# 実験 4: 標本平均の分布（中心極限定理）と歪度
# ============================================================
rows = [("MedInc", med_inc, [1, 5, 30], BLUE), ("AveOccup", ave_occ, [30, 1000, 30000], RED)]
fig, axes = plt.subplots(2, 3, figsize=(12, 6))
for r, (name, x, nlist, color) in enumerate(rows):
    for c, n in enumerate(nlist):
        m, _ = draw(x, n, 10000)
        ax = axes[r, c]
        lo, hi = np.percentile(m, [0.5, 99.5])
        ax.hist(m, bins=np.linspace(lo, hi, 60), density=True, color=color, alpha=0.75)
        grid = np.linspace(lo, hi, 300)
        ax.plot(grid, stats.norm.pdf(grid, x.mean(), x.std() / np.sqrt(n)), color=INK, lw=1.2,
                label="中心極限定理の正規分布")
        ax.axvline(x.mean(), color=INK, ls="--", lw=1)
        below = np.mean(m < x.mean())
        ax.set_title(f"{name}、n={n}　歪度 {stats.skew(m):.2f}、真の平均より下 {below:.0%}", fontsize=10)
        ax.set_yticks([])
        print(f"{name:<8} n={n:<6} 平均の歪度 {stats.skew(m):6.2f}（γ/√n = {stats.skew(x) / np.sqrt(n):6.2f}）"
              f"  真の平均より下 {below:.1%}")
axes[0, 0].legend(fontsize=8, frameon=False, loc="upper right")
for ax in axes[1]:
    ax.set_xlabel("n 件の平均")
fig.tight_layout()
save(fig, "lln_clt_hist.webp")

# ============================================================
# 実験 5: 外れた区間はどこにあるか（n = 1000）
# ============================================================
n = 1000
idx = rng.integers(0, len(ave_occ), (3000, n))        # 1000 件を 3000 回選ぶ
sample = ave_occ[idx]
m, s = sample.mean(axis=1), sample.std(axis=1, ddof=1)
half = stats.t.ppf(0.975, n - 1) * s / np.sqrt(n)
hit = np.abs(m - ave_occ.mean()) <= half
no_big = ~(sample > 20).any(axis=1)                   # 20 を超える 10 地区を 1 件も選ばなかった回
print(f"n=1000: 含んだ {hit.mean():.1%}、下に外れた {np.mean(~hit & (m < ave_occ.mean())):.1%}、"
      f"上に外れた {np.mean(~hit & (m > ave_occ.mean())):.1%}")
print(f"20 を超える地区を 1 件も選ばなかった回 {no_big.mean():.1%}、そのうち含んだ {hit[no_big].mean():.1%}")
print(f"1 件以上選んだ回のうち含んだ {hit[~no_big].mean():.1%}")

# 手元の 1000 件だけから作るブートストラップの区間も、同じように外れるか
boot_hit = []
for b in range(500):
    xb = sample[b]
    bm = xb[rng.integers(0, n, (1000, n))].mean(axis=1)   # 手元の 1000 件から選び直した平均を 1000 個
    lo, hi = np.percentile(bm, [2.5, 97.5])
    boot_hit.append(lo <= ave_occ.mean() <= hi)
print(f"ブートストラップの 95% 区間が含んだ割合 {np.mean(boot_hit):.1%}（t の区間は同じ 500 回で {hit[:500].mean():.1%}）")

fig, ax = plt.subplots(figsize=(7.5, 4.4))
ax.scatter(m[~hit], s[~hit], s=7, color=RED, alpha=0.5, label="真の平均を含まなかった区間")
ax.scatter(m[hit], s[hit], s=7, color=BLUE, alpha=0.5, label="含んだ区間")
ax.axvline(ave_occ.mean(), color=INK, ls="--", lw=1)
ax.text(ave_occ.mean() + 0.01, 33, f"真の平均 {ave_occ.mean():.3f}", fontsize=9)
ax.set_yscale("log")
ax.set_xlim(2.85, 4.4)
ax.set_xlabel("1000 件の平均")
ax.set_ylabel("1000 件の標準偏差 s（対数）")
ax.set_title("AveOccup から 1000 件を 3000 回選んだ時の、平均と標準偏差", fontsize=10)
ax.legend(fontsize=9, frameon=True, loc="lower right")
ax.grid(True, alpha=0.2)
save(fig, "lln_scatter.webp")

# ============================================================
# 実験 6: テストデータの正解率も平均
# ============================================================
digits = load_digits()
X_tr, X_pool, y_tr, y_pool = train_test_split(digits.data, digits.target, test_size=0.5,
                                              random_state=0, stratify=digits.target)
model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000)).fit(X_tr, y_tr)
correct = (model.predict(X_pool) == y_pool).astype(float)   # 1 行ごとの正解（1）と不正解（0）
p = correct.mean()
print(f"手元の {len(correct)} 行での正解率 {p:.4f}")
ns_acc = [50, 100, 200, 400, 800]
acc = {}
for n in ns_acc:
    acc[n], _ = draw(correct, n, 4000)
    lo, hi = np.percentile(acc[n], [2.5, 97.5])
    print(f"n={n:<4} 正解率の 95% の範囲 {lo:.3f}〜{hi:.3f}  幅 {hi - lo:.3f}  "
          f"式の幅 2×1.96×√(p(1-p)/n) = {2 * 1.96 * np.sqrt(p * (1 - p) / n):.3f}")

fig, ax = plt.subplots(figsize=(7.5, 4.2))
pos = np.arange(len(ns_acc))
for i, n in enumerate(ns_acc):
    jitter = rng.uniform(-0.25, 0.25, 600)
    ax.scatter(i + jitter, acc[n][:600], s=4, color=BLUE, alpha=0.35)
    e = 1.96 * np.sqrt(p * (1 - p) / n)
    ax.plot([i - 0.32, i + 0.32], [p - e, p - e], color=RED, lw=2)
    ax.plot([i - 0.32, i + 0.32], [p + e, p + e], color=RED, lw=2)
ax.axhline(p, color=INK, ls="--", lw=1)
ax.set_xticks(pos, [f"{n} 件\n±{1.96 * np.sqrt(p * (1 - p) / n):.1%}" for n in ns_acc])
ax.set_xlim(-0.5, len(ns_acc) - 0.5)
ax.set_xlabel("テストに使う件数（下段は赤い棒の幅）")
ax.set_ylabel("正解率")
ax.set_title(r"同じモデルを、別の n 件で測り直した正解率（点）と $p \pm 1.96\sqrt{p(1-p)/n}$（赤）", fontsize=10)
ax.grid(True, axis="y", alpha=0.25)
save(fig, "lln_accuracy.webp")

# ============================================================
# 実験 7: 行が独立でない時
# ============================================================
def ar1(rho, n, reps):
    """1 つ前の値に rho を掛けて新しい揺れを足す系列。どの時点も平均 0、分散 1。"""
    z = rng.normal(size=(reps, n))
    x = np.empty_like(z)
    x[:, 0] = z[:, 0]
    for t in range(1, n):
        x[:, t] = rho * x[:, t - 1] + np.sqrt(1 - rho**2) * z[:, t]
    return x


ns_ar = [10, 30, 100, 300, 1000, 3000]
fig, ax = plt.subplots(figsize=(7.5, 4.2))
for rho, color in [(0.0, BLUE), (0.5, GREEN), (0.9, RED)]:
    cv = []
    for n in ns_ar:
        x = ar1(rho, n, 4000)
        half = stats.t.ppf(0.975, n - 1) * x.std(axis=1, ddof=1) / np.sqrt(n)
        cv.append(np.mean(np.abs(x.mean(axis=1)) <= half))
    limit = 2 * stats.norm.cdf(1.96 * np.sqrt((1 - rho) / (1 + rho))) - 1
    print(f"ρ={rho}: " + "  ".join(f"n={n}: {v:.1%}" for n, v in zip(ns_ar, cv)) + f"  （n が大きい時の値 {limit:.1%}）")
    ax.plot(ns_ar, cv, "o-", color=color, lw=2, label=f"ρ = {rho}")
    ax.axhline(limit, color=color, ls=":", lw=1)
ax.axhline(0.95, color=GRAY, ls="--", lw=1)
ax.set_xscale("log")
ax.set_ylim(0, 1.02)
ax.set_xlabel("系列の長さ n（対数）")
ax.set_ylabel("真の平均 0 を含んだ割合")
ax.set_title("直前の値と相関 ρ を持つ系列で、独立とみなして作った 95% 信頼区間", fontsize=10)
ax.legend(fontsize=9, frameon=False, loc="center right")
ax.grid(True, alpha=0.25)
save(fig, "lln_dependent.webp")
