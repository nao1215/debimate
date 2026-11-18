"""curse-of-dimensionality ノートの実験と図を生成するスクリプト。

本文に載せた実験（一番遠い点と一番近い点の距離の比、距離の分布の幅、
実データの比と同じ比になる乱数の列の数、digits に乱数の列を足した時の近傍と正解率、
列を減らす 2 つの方法、ハブ）を同じ順に実行し、出力を標準出力に、図を Page Bundle に WebP で保存する。
olivetti faces は初回だけ scikit-learn が公開の配布元から取得する。
実行: cd projects/ml && .venv/bin/python scripts/notes/curse-of-dimensionality_gen.py
確認した版: scikit-learn 1.9.1、NumPy 2.5.4、SciPy 1.18.1
"""
import warnings
from io import BytesIO
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from scipy.stats import spearmanr
from sklearn.datasets import fetch_olivetti_faces, load_breast_cancer, load_digits, load_wine
from sklearn.decomposition import PCA
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import pairwise_distances
from sklearn.model_selection import GridSearchCV, StratifiedKFold, cross_val_score
from sklearn.neighbors import KNeighborsClassifier, NearestNeighbors
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore", category=UserWarning)      # 値が一定の列への SelectKBest の警告
warnings.filterwarnings("ignore", category=RuntimeWarning)

NOTE_DIR = Path(__file__).resolve().parents[2] / "notes" / "ml" / "curse-of-dimensionality"
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
# 実験 1: 1000 点の中で、一番遠い点は一番近い点の何倍遠いか
# ============================================================
rng = np.random.default_rng(0)
for d in [2, 1000]:
    X = rng.random((1000, d))                      # 0〜1 の一様な乱数で 1000 点
    dist = np.linalg.norm(X[1:] - X[0], axis=1)    # 1 点目から残り 999 点までの距離
    print(f"{d:4d} 列: 一番遠い点 {dist.max():.3f}、一番近い点 {dist.min():.3f}、比 {dist.max() / dist.min():.2f} 倍")


# ============================================================
# 実験 2: 比を全ての点で測り、列の数を変える。実データも同じ物差しで測る
# ============================================================
def far_near_ratio(X):
    """各点から見た「一番遠い点までの距離 ÷ 一番近い点までの距離」の中央値。"""
    D = pairwise_distances(X)
    np.fill_diagonal(D, np.nan)                    # 自分自身との距離 0 を外す
    return float(np.median(np.nanmax(D, axis=1) / np.nanmin(D, axis=1)))


DIMS = np.unique(np.round(np.logspace(np.log10(2), np.log10(4096), 36)).astype(int))
_uniform_cache = {}


def uniform_curve(n):
    """行の数 n の一様な乱数で、列の数ごとの比を測る（同じ n の結果は使い回す）。"""
    if n not in _uniform_cache:
        r = np.random.default_rng(1)
        _uniform_cache[n] = np.array([far_near_ratio(r.random((n, d))) for d in DIMS])
    return _uniform_cache[n]


def equivalent_columns(X):
    """X と同じ比になる一様な乱数の列の数（同じ行の数で比べ、対数の上で補間する）。"""
    curve = uniform_curve(len(X))
    r = far_near_ratio(X)
    return r, float(np.exp(np.interp(-np.log(r), -np.log(curve), np.log(DIMS))))


curve1000 = uniform_curve(1000)
for d in [2, 10, 64, 1024]:
    print(f"一様な乱数 {d:4d} 列: 比 {far_near_ratio(rng.random((1000, d))):.2f}")

digits = load_digits()
Xd, yd = digits.data, digits.target                # 8×8 画素の手書き数字 1797 枚、画素は 0〜16
pick = rng.permutation(len(Xd))[:1000]
NOISE = [0, 64, 256, 1024]
noise_cols = rng.integers(0, 17, size=(len(Xd), max(NOISE))).astype(float)  # 0〜16 の乱数の画素


def with_noise(k):
    return np.hstack([Xd, noise_cols[:, :k]])


digits_points = []
for k in NOISE:
    r, eq = equivalent_columns(with_noise(k)[pick])
    digits_points.append((64 + k, r, eq))
    print(f"digits + 乱数 {k:4d} 列（計 {64 + k:4d} 列）: 比 {r:.2f}、同じ比の一様な乱数は {eq:.0f} 列")

# 5 列の一様な乱数を、ランダムな行列で 1024 列に変換する。列は 1024 本でも、独立に動くのは 5 列分
rng_proj = np.random.default_rng(2)                 # 後の実験の乱数を変えないよう別に用意する
Z = rng_proj.random((1000, 5))
W = rng_proj.normal(size=(5, 1024))
proj_r5, proj_r1024 = far_near_ratio(Z), far_near_ratio(Z @ W)
print(f"一様な乱数 5 列: 比 {proj_r5:.2f}、それを 1024 列に変換したもの: 比 {proj_r1024:.2f}")

fig, ax = plt.subplots(figsize=(7.2, 4.4))
ax.plot(DIMS, curve1000, color=BLUE, lw=2.2, label="一様な乱数（1000 点）")
ax.plot([5, 1024], [proj_r5, proj_r1024], color=GREEN, lw=1.2, ls=":", zorder=3)
ax.scatter([5, 1024], [proj_r5, proj_r1024], color=GREEN, marker="D", s=40, zorder=4,
           label="乱数 5 列を 1024 列に変換したもの")
ax.annotate("1024 列に変換しても 5 列のまま", (1024, proj_r1024), textcoords="offset points",
            xytext=(-150, 8), color=GREEN, fontsize=9)
xs = [p[0] for p in digits_points]
ys = [p[1] for p in digits_points]
ax.plot(xs, ys, color=RED, lw=1.2, ls="--", zorder=3)
ax.scatter(xs, ys, color=RED, s=46, zorder=4, label="digits に乱数の列を足したもの")
labels = ["digits（64 列）", "+64 列", "+256 列", "+1024 列"]
offsets = [(10, 8), (8, 8), (-6, 12), (-12, 10)]
for (x, y, _), lab, off in zip(digits_points, labels, offsets):
    ax.annotate(lab, (x, y), textcoords="offset points", xytext=off, color=RED, fontsize=9)
x0, y0, eq0 = digits_points[0]
ax.plot([eq0, x0], [y0, y0], color=GRAY, lw=1, ls=":")
ax.annotate(f"乱数なら約 {eq0:.0f} 列と同じ比", (eq0, y0), textcoords="offset points", xytext=(4, -15),
            color=INK, fontsize=9)
ax.set_xscale("log")
ax.set_yscale("log")
ax.set_xlabel("列の数")
ax.set_ylabel("一番遠い点 ÷ 一番近い点（距離の比）")
ax.set_title("列が増えると、一番近い点と一番遠い点の距離が並ぶ", fontsize=11)
ax.set_ylim(0.9, 130)
ax.set_yticks([1, 1.5, 2, 3, 5, 10, 30, 100])
ax.set_yticklabels(["1", "1.5", "2", "3", "5", "10", "30", "100"])
ax.grid(True, which="major", alpha=0.25)
ax.legend(frameon=False, loc="upper right")
save(fig, "cod_cover.webp")


# ============================================================
# 実験 3: 距離の分布の幅と、近傍を集めるのに要る範囲
# ============================================================
fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
colors = [GRAY, GREEN, BLUE, RED]
for d, c in zip([2, 10, 100, 1000], colors):
    X = rng.random((1000, d))
    dist = np.linalg.norm(X[1:] - X[0], axis=1)
    rel = dist / dist.mean()
    print(f"{d:4d} 列: 距離を平均で割った値の標準偏差 {rel.std():.3f}、理論の目安 0.59/√d = {0.59 / np.sqrt(d):.3f}")
    if d == 1000:
        print(f"{d:4d} 列: 平均の ±2% に入る距離の割合 {np.mean(abs(rel - 1) <= 0.02):.0%}、"
              f"平均から一番離れた距離のずれ {abs(rel - 1).max():.1%}")
    # 1000 列の細い山を一番下に描き、100 列の山の頂が隠れないようにする
    axes[0].hist(rel, bins=np.linspace(0, 2.2, 89), histtype="step", lw=1.8, color=c, density=True,
                 label=f"{d} 列", zorder={2: 3, 10: 4, 100: 5, 1000: 2}[d])
axes[0].set_xlabel("1 点から他の点までの距離 ÷ その平均")
axes[0].set_ylabel("割合（密度）")
axes[0].set_title("距離の分布は平均の周りに縮む", fontsize=11)
axes[0].legend(frameon=False)

dd = np.arange(1, 201)
for frac, c in [(0.01, RED), (0.10, BLUE)]:
    side = frac ** (1 / dd)
    axes[1].plot(dd, side, color=c, lw=2, label=f"全体の {frac:.0%} を含む立方体")
    for d in [1, 3, 10, 100]:
        print(f"全体の {frac:.0%} を含む立方体の 1 辺（{d:3d} 列）: {frac ** (1 / d):.3f}")
axes[1].scatter([10], [0.01 ** 0.1], color=RED, zorder=4)
axes[1].annotate(f"10 列で 1 辺 {0.01 ** 0.1:.2f}", (10, 0.01 ** 0.1), textcoords="offset points",
                 xytext=(8, -14), color=RED, fontsize=9)
axes[1].set_xscale("log")
axes[1].set_ylim(0, 1.02)
axes[1].set_xlabel("列の数")
axes[1].set_ylabel("立方体の 1 辺 ÷ 全体の 1 辺")
axes[1].set_title("近くの点を集めるのに要る範囲", fontsize=11)
axes[1].legend(frameon=False, loc="lower right")
axes[1].grid(True, alpha=0.25)
fig.tight_layout()
save(fig, "cod_spread.webp")


# ============================================================
# 実験 4: 実データの比を、同じ行の数の一様な乱数と比べる
# ============================================================
faces = fetch_olivetti_faces()                     # 64×64 画素の顔画像 400 枚
datasets = [
    ("wine（標準化）", StandardScaler().fit_transform(load_wine().data)),
    ("breast_cancer（標準化）", StandardScaler().fit_transform(load_breast_cancer().data)),
    ("digits", Xd),
    ("olivetti faces", faces.data),
]
for name, X in datasets:
    X = X[rng.permutation(len(X))[:1000]]
    r, eq = equivalent_columns(X)
    print(f"{name:<22} {X.shape[0]:4d} 行 × {X.shape[1]:4d} 列: 比 {r:.2f}、同じ比の一様な乱数は {eq:.0f} 列")

pca = PCA().fit(Xd)
n90 = int(np.searchsorted(np.cumsum(pca.explained_variance_ratio_), 0.90) + 1)
print(f"digits の分散の 90% を説明する主成分の数: {n90}")


# ============================================================
# 実験 5: digits に乱数の列を足すと、近傍がどう変わるか
# ============================================================
def neighbors(X, q, k=5):
    nn = NearestNeighbors(n_neighbors=k + 1).fit(X)
    return nn.kneighbors(X[q:q + 1], return_distance=False)[0, 1:]   # 自分自身を外す


queries = [3, 40]
fig, axes = plt.subplots(len(queries) * 2, 6, figsize=(6.6, 5.0))
for row, q in enumerate(queries):
    for j, (k, tag) in enumerate([(0, "64 列のまま"), (1024, "乱数の列 +1024")]):
        ax_row = axes[row * 2 + j]
        nb = neighbors(with_noise(k), q)
        same = int((yd[nb] == yd[q]).sum())
        print(f"問い合わせ {q}（数字 {yd[q]}）・{tag}: 近傍 5 枚の数字 {yd[nb].tolist()}、同じ数字 {same} 枚")
        ax_row[0].imshow(Xd[q].reshape(8, 8), cmap="gray_r", vmin=0, vmax=16)
        ax_row[0].set_title("問い合わせ" if j == 0 else "", fontsize=8)
        ax_row[0].set_ylabel(tag, fontsize=8, rotation=0, ha="right", va="center")
        for t, i in enumerate(nb):
            a = ax_row[t + 1]
            a.imshow(Xd[i].reshape(8, 8), cmap="gray_r", vmin=0, vmax=16)
            ok = yd[i] == yd[q]
            for s in a.spines.values():
                s.set_visible(True)
                s.set_color(GREEN if ok else RED)
                s.set_linewidth(2.2)
            a.set_title(f"{yd[i]}", fontsize=8, color=INK if ok else RED)
        for s in ax_row[0].spines.values():
            s.set_visible(False)
        for a in ax_row:
            a.set_xticks([])
            a.set_yticks([])
fig.suptitle("近い 5 枚（緑の枠は同じ数字、赤の枠は違う数字。画像は元の 64 列だけを表示）", fontsize=9)
fig.tight_layout()
save(fig, "cod_neighbors.webp")


# ============================================================
# 実験 6: 乱数の列を足した時の正解率（5 分割の交差検証）
# ============================================================
cv = StratifiedKFold(5, shuffle=True, random_state=0)
models = {
    "kNN（k=5）": KNeighborsClassifier(5),
    "ロジスティック回帰": make_pipeline(StandardScaler(), LogisticRegression(max_iter=3000)),
    "ランダムフォレスト": RandomForestClassifier(300, random_state=0, n_jobs=4),
}
NOISE_ALL = [0, 16, 64, 256, 1024]
acc = {name: [] for name in models}
for k in NOISE_ALL:
    X = with_noise(k)
    for name, m in models.items():
        acc[name].append(cross_val_score(m, X, yd, cv=cv, n_jobs=5).mean())
    print(f"乱数 +{k:4d} 列: " + "、".join(f"{n} {acc[n][-1]:.3f}" for n in models))

fig, ax = plt.subplots(figsize=(6.8, 4.0))
xpos = np.arange(len(NOISE_ALL))
for (name, vals), c in zip(acc.items(), [RED, BLUE, GREEN]):
    ax.plot(xpos, vals, marker="o", color=c, lw=2, label=name)
    ax.annotate(f"{vals[-1]:.2f}", (xpos[-1], vals[-1]), textcoords="offset points", xytext=(8, -3),
                color=c, fontsize=9)
ax.set_xticks(xpos)
ax.set_xticklabels([f"+{k}" for k in NOISE_ALL])
ax.set_xlabel("digits の 64 列に足した乱数の列の数")
ax.set_ylabel("正解率（5 分割の交差検証）")
ax.set_ylim(0.55, 1.0)
ax.grid(True, alpha=0.25)
ax.legend(frameon=False, loc="lower left")
save(fig, "cod_models.webp")


# ============================================================
# 実験 7: kNN の前に列を減らす。PCA と、正解の数字との関係で選ぶ SelectKBest
# ============================================================
inner = StratifiedKFold(3, shuffle=True, random_state=1)
remedies = {
    "そのまま": KNeighborsClassifier(5),
    "PCA → kNN": GridSearchCV(make_pipeline(PCA(random_state=0), KNeighborsClassifier(5)),
                              {"pca__n_components": [10, 20, 40]}, cv=inner),
    "SelectKBest → kNN": GridSearchCV(make_pipeline(SelectKBest(f_classif), KNeighborsClassifier(5)),
                                      {"selectkbest__k": [16, 32, 64, 128]}, cv=inner),
}
rem = {name: [] for name in remedies}
for k in NOISE_ALL:
    X = with_noise(k)
    for name, m in remedies.items():
        rem[name].append(cross_val_score(m, X, yd, cv=cv, n_jobs=5).mean())
    print(f"乱数 +{k:4d} 列: " + "、".join(f"{n} {rem[n][-1]:.3f}" for n in remedies))

pca1024 = PCA(20, random_state=0).fit(with_noise(1024))
share = float(np.sum(pca1024.components_[:, :64] ** 2) / 20)
print(f"+1024 列で PCA が選んだ 20 本の向きのうち、元の 64 列に載っている割合: {share:.3f}")
sel = SelectKBest(f_classif, k=64).fit(with_noise(1024), yd)
print(f"+1024 列で SelectKBest(k=64) が選んだ列のうち、元の 64 列: {int(sel.get_support()[:64].sum())}")
dropped = np.where(~sel.get_support()[:64])[0]
print(f"選ばれなかった元の列 {dropped.tolist()}: 値が 0 の画像の割合 {(Xd[:, dropped] == 0).mean(axis=0).round(3).tolist()}")

fig, ax = plt.subplots(figsize=(6.8, 4.0))
for (name, vals), c in zip(rem.items(), [RED, ORANGE, GREEN]):
    ax.plot(xpos, vals, marker="o", color=c, lw=2, label=name)
    ax.annotate(f"{vals[-1]:.2f}", (xpos[-1], vals[-1]), textcoords="offset points", xytext=(8, -3),
                color=c, fontsize=9)
ax.set_xticks(xpos)
ax.set_xticklabels([f"+{k}" for k in NOISE_ALL])
ax.set_xlabel("digits の 64 列に足した乱数の列の数")
ax.set_ylabel("kNN の正解率（5 分割の交差検証）")
ax.set_ylim(0.55, 1.0)
ax.grid(True, alpha=0.25)
ax.legend(frameon=False, loc="lower left")
save(fig, "cod_reduce.webp")


# ============================================================
# 実験 8: ハブ。何度も近傍に選ばれる点と、一度も選ばれない点
# ============================================================
def k_occurrence(X, k=10):
    """各点が、他の点の近傍 k 個に何回選ばれたか。"""
    nn = NearestNeighbors(n_neighbors=k + 1).fit(X)
    ind = nn.kneighbors(X, return_distance=False)[:, 1:]
    return np.bincount(ind.ravel(), minlength=len(X))


fig, axes = plt.subplots(1, 3, figsize=(11, 3.6))
hub_data = {}
for d in [3, 20, 100]:
    X = rng.normal(size=(2000, d))                  # 標準正規分布の 2000 点
    c = k_occurrence(X)
    r = np.linalg.norm(X - X.mean(axis=0), axis=1)  # 点の集まりの中心からの距離
    hub_data[d] = (c, r)
    rho = spearmanr(r, c)[0]
    print(f"正規分布 {d:3d} 列: 選ばれた回数の最大 {c.max()}、一度も選ばれない点 {np.mean(c == 0):.1%}、"
          f"中心からの距離との順位相関 {rho:.2f}、中心からの距離の範囲 {r.min():.1f}〜{r.max():.1f}")
bins = np.arange(0, hub_data[100][0].max() + 11, 10)
for d, c in [(3, GRAY), (100, RED)]:
    axes[0].hist(hub_data[d][0], bins=bins, color=c, alpha=0.65, label=f"{d} 列")
axes[0].set_yscale("log")
axes[0].set_xlabel("他の点の近傍 10 個に選ばれた回数")
axes[0].set_ylabel("点の数（対数）")
axes[0].set_title("選ばれる回数の偏り", fontsize=11)
axes[0].legend(frameon=False)
for ax, d in zip(axes[1:], [3, 100]):
    c, r = hub_data[d]
    ax.scatter(r, c, s=5, color=GRAY if d == 3 else RED, alpha=0.5)
    ax.set_xlabel("中心からの距離")
    ax.set_ylabel("選ばれた回数")
    ax.axhline(10, color=INK, lw=0.8, ls="--")
    ax.annotate("平均 10 回", (1.0, 10), xycoords=("axes fraction", "data"), xytext=(0, 4),
                textcoords="offset points", va="bottom", ha="right", fontsize=8, color=INK,
                bbox=dict(boxstyle="square,pad=0.15", fc="white", ec="none"), zorder=5)
    ax.set_xlim(left=0)
    ax.yaxis.get_major_locator().set_params(integer=True)
    ax.set_title(f"{d} 列（点ごとの回数と中心からの距離）", fontsize=11)
fig.tight_layout()
save(fig, "cod_hub.webp")

for k in [0, 1024]:
    X = with_noise(k)
    c = k_occurrence(X, 5)
    print(f"digits + 乱数 {k:4d} 列: 近傍 5 個に選ばれた回数の最大 {c.max()}、一度も選ばれない画像 {np.mean(c == 0):.1%}")
