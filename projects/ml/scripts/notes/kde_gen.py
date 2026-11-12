"""kde ノートの実験と図を生成するスクリプト。

本文に載せた実験（scipy と scikit-learn の「scott」の幅、1 点ずつのカーネルの和、
バンド幅と山の数、規則と交差検証の幅、列の散らばりと幅、0 が下限の列、診断ごとの面積）を
同じ順に実行し、出力を標準出力に、図を Page Bundle に WebP で保存する。
実行: cd projects/ml && .venv/bin/python scripts/notes/kde_gen.py
確認した版: scikit-learn 1.9.1、SciPy 1.18.1、seaborn 0.13.2、NumPy 2.5.4
"""
from io import BytesIO
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from PIL import Image
from scipy import stats
from scipy.signal import find_peaks
from sklearn.datasets import load_breast_cancer
from sklearn.model_selection import GridSearchCV, KFold
from sklearn.neighbors import KernelDensity
from sklearn.preprocessing import StandardScaler

NOTE_DIR = Path(__file__).resolve().parents[2] / "notes" / "math" / "kde"
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10,
                     "axes.spines.top": False, "axes.spines.right": False})
BLUE, RED, GREEN, INK, GRAY = "#7aa6c2", "#e15759", "#59a14f", "#333333", "#bbbbbb"
DARK_BLUE = "#2f6690"


def save(fig, name):
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight", facecolor="#ffffff")
    plt.close(fig)
    buf.seek(0)
    Image.open(buf).convert("RGB").save(NOTE_DIR / name, "WEBP", quality=90, method=6)


# ============================================================
# 実験 1（冒頭）: 同じ「scott」で、scipy と scikit-learn の幅を比べる
# ============================================================
cancer = load_breast_cancer()
names = list(cancer.feature_names)
area = cancer.data[:, names.index("mean area")]
concavity = cancer.data[:, names.index("mean concavity")]

grids = {"mean area": np.arange(0, 3000, 0.05), "mean concavity": np.arange(-1.5, 2.0, 0.0005)}
curves = {}
for col, x in [("mean area", area), ("mean concavity", concavity)]:
    xs = grids[col]
    sp = stats.gaussian_kde(x)                                  # scipy（seaborn も同じ）
    sk = KernelDensity(bandwidth="scott").fit(x[:, None])       # scikit-learn
    y_sp, y_sk = sp(xs), np.exp(sk.score_samples(xs[:, None]))
    h_sp = sp.factor * x.std(ddof=1)                            # scipy の幅をデータの単位に直す
    curves[col] = (x, xs, y_sp, y_sk, h_sp, sk.bandwidth_)
    print(f"{col}: 標準偏差 {x.std(ddof=1):.3f}")
    print(f"  scipy  幅 {h_sp:.3f}  山の数 {len(find_peaks(y_sp)[0])}")
    print(f"  sklearn 幅 {sk.bandwidth_:.3f}  山の数 {len(find_peaks(y_sk)[0])}")

x, xs, y_sp, y_sk, h_sp, h_sk = curves["mean concavity"]
neg = xs < 0
print(f"mean concavity の 0 未満の面積: scipy {np.trapezoid(y_sp[neg], xs[neg]):.3f}  "
      f"sklearn {np.trapezoid(y_sk[neg], xs[neg]):.3f}")

fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
for ax, col, title, xlim, ylim in [
        (axes[0], "mean area", "細胞核の面積（mean area）", (0, 2700), None),
        (axes[1], "mean concavity", "輪郭の凹み（mean concavity）", (-0.9, 1.3), None)]:
    x, xs, y_sp, y_sk, h_sp, h_sk = curves[col]
    ax.hist(x, bins=40, density=True, color=GRAY, alpha=0.7, label="ヒストグラム")
    ax.plot(xs, y_sk, color=RED, lw=0.8, label=f"scikit-learn の scott（幅 {h_sk:.3f}）")
    ax.plot(xs, y_sp, color=DARK_BLUE, lw=2.2, label=f"scipy の scott（幅 {h_sp:.2f}）" if h_sp > 1 else f"scipy の scott（幅 {h_sp:.4f}）")
    if col == "mean concavity":
        ax.axvline(0, color=INK, lw=0.8, ls="--")
        ax.text(-0.03, ax.get_ylim()[1] * 0.55, "0（下限）", fontsize=9, color=INK, ha="right")
    ax.set_xlim(*xlim)
    ax.set_title(title, fontsize=11)
    ax.set_xlabel("値")
    ax.legend(fontsize=8.5, loc="upper right", frameon=False)
    ax.grid(True, alpha=0.25)
axes[0].set_ylabel("密度")
fig.suptitle("load_breast_cancer の 569 件に、同じ bandwidth=\"scott\" で KDE を計算した", y=1.02, fontsize=12)
fig.tight_layout()
save(fig, "kde_cover.webp")


# ============================================================
# 実験 2: 1 点ずつのカーネルを足すと KDE になる
# ============================================================
sample = np.random.default_rng(5).normal(0, 1, 15)
xs = np.linspace(-4, 4, 400)
h = 0.5
kde = np.zeros_like(xs)
kernels = []
for xi in sample:
    k = np.exp(-0.5 * ((xs - xi) / h) ** 2) / (h * np.sqrt(2 * np.pi))
    kernels.append(k / len(sample))
    kde += k / len(sample)  # 1 点分のカーネルを n で割って足す
print(f"面積: {np.trapezoid(kde, xs):.3f}")

fig, ax = plt.subplots(figsize=(8.5, 4.2))
for i, k in enumerate(kernels):
    ax.plot(xs, k, color=BLUE, alpha=0.7, lw=1, label="1 点分のカーネル（n で割った後）" if i == 0 else None)
ax.plot(xs, kde, color=RED, lw=2.5, label="全てのカーネルの和（KDE）")
ax.scatter(sample, np.zeros_like(sample), color="black", s=25, zorder=5, label="データ点（15 個）")
ax.set_xlabel("x")
ax.set_ylabel("密度")
ax.legend(frameon=False)
ax.grid(True, alpha=0.25)
fig.tight_layout()
save(fig, "kde_per_point.webp")


# ============================================================
# 実験 3: バンド幅で山の数が変わる
# ============================================================
rng = np.random.default_rng(0)
data = np.concatenate([rng.normal(-2.0, 0.8, 200), rng.normal(2.0, 0.8, 200)])
xs = np.linspace(-5, 5, 400)
for h in [0.1, 0.5, 2.0]:
    kde = stats.gaussian_kde(data, bw_method=h / data.std(ddof=1))
    peaks, _ = find_peaks(kde(xs))
    print(f"h={h}: 山の数 {len(peaks)}")

fig, axes = plt.subplots(1, 3, figsize=(12, 3.6), sharey=True)
for ax, h, title in zip(axes, [0.1, 0.5, 2.0], ["h = 0.1（山 15 個）", "h = 0.5（山 2 個）", "h = 2.0（山 1 個）"]):
    ax.hist(data, bins=40, density=True, color=GRAY, alpha=0.7)
    ax.plot(xs, stats.gaussian_kde(data, bw_method=h / data.std(ddof=1))(xs), color=RED, lw=2)
    ax.set_title(title, fontsize=11)
    ax.set_xlabel("x")
    ax.grid(True, alpha=0.25)
axes[0].set_ylabel("密度")
fig.tight_layout()
save(fig, "kde_bandwidth.webp")


# ============================================================
# 実験 4: 規則の幅と交差検証の幅
# ============================================================
rule_h = {}
for rule in ["scott", "silverman"]:
    kde = stats.gaussian_kde(data, bw_method=rule)
    h = kde.factor * data.std(ddof=1)
    rule_h[rule] = h
    print(f"{rule}: h={h:.2f}, 山の数 {len(find_peaks(kde(xs))[0])}")

hs = np.arange(0.05, 2.01, 0.05)
grid = GridSearchCV(
    KernelDensity(),
    {"bandwidth": hs},
    cv=KFold(5, shuffle=True, random_state=0),
).fit(data[:, None])
h_cv = grid.best_params_["bandwidth"]
print(f"交差検証: h={h_cv:.2f}")
for rs in [1, 2]:
    g = GridSearchCV(KernelDensity(), {"bandwidth": hs}, cv=KFold(5, shuffle=True, random_state=rs)).fit(data[:, None])
    print(f"  random_state={rs}: h={g.best_params_['bandwidth']:.2f}")

fig, axes = plt.subplots(1, 2, figsize=(11, 3.8))
ax = axes[0]
ax.plot(hs, grid.cv_results_["mean_test_score"], color=INK, lw=1.8, marker="o", ms=3)
for hv, c, lab in [(h_cv, RED, f"交差検証 {h_cv:.2f}"), (rule_h["scott"], DARK_BLUE, f"scott {rule_h['scott']:.2f}"),
                   (rule_h["silverman"], GREEN, f"silverman {rule_h['silverman']:.2f}")]:
    ax.axvline(hv, color=c, lw=1.5, ls="--", label=lab)
ax.set_xlabel("バンド幅 h")
ax.set_ylabel("検証用の 80 点の対数尤度（5 回の平均）")
ax.set_ylim(-182, -146)
ax.legend(frameon=False, fontsize=9)
ax.grid(True, alpha=0.25)
ax.set_title("h ごとの検証用データの対数尤度", fontsize=11)
ax = axes[1]
ax.hist(data, bins=40, density=True, color=GRAY, alpha=0.7)
ax.plot(xs, stats.gaussian_kde(data, bw_method=h_cv / data.std(ddof=1))(xs), color=RED, lw=2, label=f"交差検証の h = {h_cv:.2f}")
ax.plot(xs, stats.gaussian_kde(data, bw_method="scott")(xs), color=DARK_BLUE, lw=2, label=f"scott の h = {rule_h['scott']:.2f}")
ax.set_xlabel("x")
ax.set_ylabel("密度")
ax.legend(frameon=False, fontsize=9)
ax.grid(True, alpha=0.25)
ax.set_title("2 つの h で描いた曲線", fontsize=11)
fig.tight_layout()
save(fig, "kde_cv.webp")


# ============================================================
# 実験 5: 列の散らばりと「scott」の幅（30 列）
# ============================================================
X = cancer.data
n, d = X.shape
h_scipy = np.array([stats.gaussian_kde(X[:, j]).factor * X[:, j].std(ddof=1) for j in range(d)])
h_sklearn = KernelDensity(bandwidth="scott").fit(X[:, :1]).bandwidth_
print(f"n^(-1/5) = {n ** (-1 / 5):.3f}、scikit-learn の幅 {h_sklearn:.3f}")
for col in ["mean area", "mean concavity"]:
    j = names.index(col)
    print(f"{col}: scipy {h_scipy[j]:.3f}  scikit-learn {h_sklearn:.3f}  比 {h_scipy[j] / h_sklearn:.3g}")

ax = sns.kdeplot(x=area)                                    # seaborn の曲線
line_x, line_y = ax.lines[0].get_data()
plt.close(ax.figure)
print("seaborn と scipy の差の最大:", np.abs(line_y - stats.gaussian_kde(area)(line_x)).max())

z = StandardScaler().fit_transform(area[:, None])            # 平均 0・標準偏差 1 にしてから使う
sk_z = KernelDensity(bandwidth="scott").fit(z)
xs = np.arange(0, 3000, 0.05)                               # 0.05 刻みで曲線を評価する
u = (xs - area.mean()) / area.std()                         # 評価する点も標準化した軸へ移す
y_z = np.exp(sk_z.score_samples(u[:, None])) / area.std()   # 標準化した軸の密度を元の単位に戻す
print(f"標準化してから: 幅（元の単位）{sk_z.bandwidth_ * area.std():.2f}  山の数 {len(find_peaks(y_z)[0])}")
print(f"  scipy との差の最大 {np.abs(y_z - stats.gaussian_kde(area)(xs)).max():.1e}")

stds = X.std(axis=0, ddof=1)
fig, ax = plt.subplots(figsize=(7.5, 4.6))
ax.scatter(stds, h_scipy, color=DARK_BLUE, s=22, zorder=3, label="scipy・seaborn の scott（30 列）")
ax.axhline(h_sklearn, color=RED, lw=2, label=f"scikit-learn の scott（どの列も {h_sklearn:.3f}）")
for col, dx, dy in [("mean area", 0.55, 0.9), ("mean concavity", 1.3, 0.75)]:
    j = names.index(col)
    ax.annotate(col, (stds[j], h_scipy[j]), xytext=(stds[j] * dx, h_scipy[j] * dy), fontsize=9,
                arrowprops=dict(arrowstyle="-", color=INK, lw=0.6), ha="right" if dx < 1 else "left")
ax.set_xscale("log")
ax.set_yscale("log")
ax.set_xlabel("列の標準偏差（対数）")
ax.set_ylabel("バンド幅 h（対数）")
ax.legend(frameon=False, fontsize=9, loc="upper left")
ax.grid(True, alpha=0.25, which="both")
fig.tight_layout()
save(fig, "kde_scott_width.webp")


# ============================================================
# 実験 6: 0 が下限の列で、境界の密度が低く出る
# ============================================================
kde = stats.gaussian_kde(concavity)
print(f"幅 {kde.factor * concavity.std(ddof=1):.4f}、0 未満にはみ出した面積 {kde.integrate_box_1d(-np.inf, 0):.3f}")
counts, _ = np.histogram(concavity, bins=[0, 0.01, 0.02])
print("0〜0.01 のデータの割合:", round((concavity < 0.01).mean(), 3))
print("0〜0.01 のヒストグラムの密度:", round(counts[0] / len(concavity) / 0.01, 2))
reflected = lambda t: kde(t) + kde(-t)                       # 0 で折り返して足す（t >= 0 で使う）
print(f"x=0 の密度: KDE {kde(0)[0]:.2f}  折り返し {reflected(0)[0]:.2f}")
ts = np.linspace(0, 0.5, 5001)
print(f"折り返した曲線の 0 以上の面積 {np.trapezoid(reflected(ts), ts):.3f}")

fig, ax = plt.subplots(figsize=(8.5, 4.2))
xs = np.linspace(-0.1, 0.45, 1101)
ax.hist(concavity, bins=np.arange(0, 0.45, 0.01), density=True, color=GRAY, alpha=0.7, label="ヒストグラム（幅 0.01）")
y = kde(xs)
ax.plot(xs, y, color=DARK_BLUE, lw=2, label="そのままの KDE")
ax.fill_between(xs[xs < 0], y[xs < 0], color=DARK_BLUE, alpha=0.3, label="0 未満にはみ出した面積 0.075")
ax.plot(ts[ts <= 0.45], reflected(ts[ts <= 0.45]), color=RED, lw=2, label="0 で折り返した KDE")
ax.axvline(0, color=INK, lw=0.8, ls="--")
ax.set_xlim(-0.1, 0.45)
ax.set_xlabel("輪郭の凹み（mean concavity）")
ax.set_ylabel("密度")
ax.legend(frameon=False, fontsize=9)
ax.grid(True, alpha=0.25)
fig.tight_layout()
save(fig, "kde_boundary.webp")


# ============================================================
# 実験 7: 診断ごとの mean area の KDE と、人数で見た逆転
# ============================================================
malignant = area[cancer.target == 0]   # 悪性 212 件
benign = area[cancer.target == 1]      # 良性 357 件
kde_m, kde_b = stats.gaussian_kde(malignant), stats.gaussian_kde(benign)
a = np.linspace(100, 2600, 2501)
diff_density = kde_m(a) - kde_b(a)
diff_count = len(malignant) * kde_m(a) - len(benign) * kde_b(a)
print(f"悪性 {len(malignant)} 件、良性 {len(benign)} 件")
print("密度が逆転する mean area:", a[np.flatnonzero(np.diff(np.sign(diff_density)))])
print("件数が逆転する mean area:", a[np.flatnonzero(np.diff(np.sign(diff_count)))])

fig, axes = plt.subplots(1, 2, figsize=(11, 3.9))
cross_d = a[np.flatnonzero(np.diff(np.sign(diff_density)))][0]
cross_c = a[np.flatnonzero(np.diff(np.sign(diff_count)))][0]
for ax, (yb, ym), title, ylab, cross in [
        (axes[0], (kde_b(a), kde_m(a)), "診断ごとの密度（曲線の面積はそれぞれ 1）", "密度", cross_d),
        (axes[1], (len(benign) * kde_b(a), len(malignant) * kde_m(a)), "件数を掛けた曲線", "件数 × 密度", cross_c)]:
    ax.plot(a, yb, color=BLUE, lw=2, label=f"良性（{len(benign)} 件）")
    ax.fill_between(a, yb, color=BLUE, alpha=0.25)
    ax.plot(a, ym, color=RED, lw=2, label=f"悪性（{len(malignant)} 件）")
    ax.fill_between(a, ym, color=RED, alpha=0.2)
    ax.axvline(cross, color=INK, lw=1, ls="--")
    ax.text(cross + 40, max(yb.max(), ym.max()) * 0.9, f"{cross:.0f} で交わる", fontsize=9)
    ax.set_xlim(100, 2600)
    ax.set_title(title, fontsize=11)
    ax.set_xlabel("細胞核の面積（mean area）")
    ax.set_ylabel(ylab)
    ax.legend(frameon=False, fontsize=9, loc="center right")
    ax.grid(True, alpha=0.25)
fig.tight_layout()
save(fig, "kde_class.webp")
