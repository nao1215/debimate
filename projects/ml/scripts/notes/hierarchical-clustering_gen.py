"""hierarchical-clustering ノートの実験と図を生成するスクリプト。

本文に載せた実験（1〜5 の回答で行の順番を変える、7 点の凝集、linkage と橋渡しの点、
同じ距離の組と行の順番、結合のたびの同点の数、wine のコフェネティック相関係数と ARI、点の数と時間・メモリ）を
本文と同じ順に実行し、出力を標準出力に、図を Page Bundle に WebP で保存する。
実行: cd projects/ml && .venv/bin/python scripts/notes/hierarchical-clustering_gen.py
確認した版: scikit-learn 1.9.1、SciPy 1.18.1、NumPy 2.5.4、matplotlib 3.11.2
"""
import json
import subprocess
import sys
from io import BytesIO
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from scipy.cluster.hierarchy import cophenet, dendrogram, fcluster, linkage
from scipy.optimize import linear_sum_assignment
from scipy.spatial.distance import pdist, squareform
from sklearn.cluster import AgglomerativeClustering, Birch
from sklearn.datasets import load_digits, load_wine, make_blobs
from sklearn.metrics import adjusted_rand_score
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

NOTE_DIR = Path(__file__).resolve().parents[2] / "notes" / "ml" / "hierarchical-clustering"
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10,
                     "axes.spines.top": False, "axes.spines.right": False})
BLUE, RED, GREEN, ORANGE, INK, GRAY = "#7aa6c2", "#e15759", "#59a14f", "#f28e2b", "#333333", "#999999"
PALETTE = [BLUE, RED, GREEN, ORANGE, "#b07aa1", "#9c755f", "#76b7b2", "#edc948"]


def save(fig, name):
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight", facecolor="#ffffff")
    plt.close(fig)
    buf.seek(0)
    Image.open(buf).convert("RGB").save(NOTE_DIR / name, "WEBP", quality=90, method=6)


def align(truth, lab):
    """クラスタの番号を、正解と最も多く重なる番号に付け替える（色をそろえるため）。"""
    k = max(truth.max(), lab.max()) + 1
    m = np.zeros((k, k), int)
    for t, l in zip(truth, lab):
        m[l, t] += 1
    r, c = linear_sum_assignment(-m)
    mp = dict(zip(r, c))
    return np.array([mp[l] for l in lab])


# ---- 実験 0: 1〜5 の回答を、行の順番だけ変えて 20 回分ける ----
rng = np.random.RandomState(0)
profiles = rng.uniform(1.5, 4.5, size=(3, 10))  # 3 つのグループの、10 問の平均的な回答
group = rng.randint(0, 3, 300)  # 300 人がどのグループか
X_cont = profiles[group] + rng.randn(300, 10) * 0.8  # 丸める前の連続値
X_int = np.clip(np.rint(X_cont), 1, 5)  # 1〜5 の整数に丸めた回答

results = {}
for name, X in [("連続値のまま", X_cont), ("1〜5 に丸めた回答", X_int)]:
    base = AgglomerativeClustering(n_clusters=3, linkage="ward").fit_predict(X)
    rows, changed, aris = [], 0, []
    for s in range(20):
        order = np.random.RandomState(s).permutation(len(X))  # 行の順番を並べ替える
        lab = AgglomerativeClustering(n_clusters=3, linkage="ward").fit_predict(X[order])
        back = np.empty_like(lab)
        back[order] = lab  # 元の行の順番に戻して比べる
        changed += adjusted_rand_score(base, back) < 0.999
        aris.append(adjusted_rand_score(group, back))
        rows.append(back)
    results[name] = (rows, changed, aris)
    print(f"{name}: 違う距離の値 {len(np.unique(pdist(X)))} 種類、"
          f"並べ替える前と分け方が変わった回 {changed}/20、"
          f"正解との ARI {min(aris):.3f}〜{max(aris):.3f}")

fig, axes = plt.subplots(1, 2, figsize=(10, 3.6))
order_people = np.argsort(group, kind="stable")
for ax, (name, (rows, changed, aris)) in zip(axes, results.items()):
    img = np.array([align(group, r)[order_people] for r in rows])
    ax.imshow(img, aspect="auto", interpolation="nearest",
              cmap=plt.matplotlib.colors.ListedColormap(PALETTE[:3]))
    ax.set_title(f"{name}\n分け方が変わった回 {changed}/20", fontsize=11)
    ax.set_xlabel("300 人（正解のグループ順に並べた）")
    ax.set_yticks([0, 9, 19])
    ax.set_yticklabels(["1", "10", "20"])
    for sp in ax.spines.values():
        sp.set_visible(False)
axes[0].set_ylabel("行の順番を変えた回")
fig.tight_layout()
save(fig, "hc_cover.webp")


# ---- 実験 1: 7 点を single linkage で凝集する ----
points = np.array([[0.5, 1.0], [0.7, 0.9], [3.0, 3.0], [3.2, 2.8],
                   [3.1, 3.2], [1.5, 3.5], [1.7, 3.3]])
Z7 = linkage(points, method="single")
for a, b, dist, size in Z7:
    print(f"{int(a)} + {int(b)}: 距離 {dist:.3f}, 点の数 {int(size)}")

fig, axes = plt.subplots(1, 2, figsize=(10, 4), gridspec_kw={"width_ratios": [1, 1.2]})
ax = axes[0]
lab7 = fcluster(Z7, t=3, criterion="maxclust")
# 結合した組を線で結ぶ（single なので、2 つのクラスタの中で最も近い 2 点を結ぶ）
members = {i: [i] for i in range(len(points))}
for step, (a, b, dist, size) in enumerate(Z7, start=1):
    A, B = members[int(a)], members[int(b)]
    d = np.linalg.norm(points[A][:, None] - points[B][None], axis=2)
    i, j = np.unravel_index(d.argmin(), d.shape)
    p, q = points[A[i]], points[B[j]]
    ax.plot([p[0], q[0]], [p[1], q[1]], color=GRAY if step > 4 else INK, lw=1.5,
            ls="--" if step > 4 else "-", zorder=1)
    if step > 4:
        mid = (p + q) / 2
        ax.text(mid[0] + 0.1, mid[1], f"{step} 回目", fontsize=10, color=RED)
    members[len(points) + step - 1] = A + B
for i, (x, yv) in enumerate(points):
    ax.scatter(x, yv, s=330, color=PALETTE[lab7[i] - 1], zorder=3)
    ax.text(x, yv, str(i), fontsize=10, color="white", ha="center", va="center", zorder=4)
ax.set_aspect("equal")
ax.set_xlim(0, 4)
ax.set_ylim(0.4, 4)
ax.set_title("7 点と、つないだ組（破線は 5・6 回目）", fontsize=11)
ax = axes[1]
dn = dendrogram(Z7, ax=ax, color_threshold=0, above_threshold_color=INK)
# 各結合の横棒に、何回目の結合かを書く（葉の位置から横棒の中央を求める）
xpos = {leaf: 5 + 10 * k for k, leaf in enumerate(dn["leaves"])}
for step, (a, b, dist, size) in enumerate(Z7, start=1):
    xpos[len(points) + step - 1] = (xpos[int(a)] + xpos[int(b)]) / 2
    ax.text(xpos[len(points) + step - 1], dist + 0.04, f"{step}", ha="center", va="bottom",
            color=RED, fontsize=10, bbox=dict(fc="white", ec="none", pad=1))
ax.axhline(1.0, color=RED, ls="--", lw=1.2)
ax.text(ax.get_xlim()[1], 1.03, "高さ 1.0 で切ると 3 つ", ha="right", va="bottom", color=RED, fontsize=10)
ax.set_xlabel("点の番号（左右の並びに意味は無い）")
ax.set_ylabel("結合した時の距離（高さ）")
ax.set_title("樹形図（赤い数字は何回目の結合か）", fontsize=11)
fig.tight_layout()
save(fig, "hc_steps.webp")


# ---- 図: 4 つの linkage が使う距離 ----
rng = np.random.RandomState(3)
CA = rng.randn(6, 2) * 0.35 + [0, 0]
CB = rng.randn(6, 2) * 0.35 + [2.6, 0.4]
fig, axes = plt.subplots(1, 4, figsize=(12, 3.2))
d = np.linalg.norm(CA[:, None] - CB[None], axis=2)
titles = ["single\n最も近い 2 点の距離", "complete\n最も遠い 2 点の距離",
          "average\n全ての組の距離の平均", "ward\nまとめた時の 2 乗和の増え方"]
for ax, title in zip(axes, titles):
    ax.scatter(CA[:, 0], CA[:, 1], s=40, color=BLUE, zorder=3)
    ax.scatter(CB[:, 0], CB[:, 1], s=40, color=RED, zorder=3)
    if title.startswith("single"):
        i, j = np.unravel_index(d.argmin(), d.shape)
        ax.plot([CA[i, 0], CB[j, 0]], [CA[i, 1], CB[j, 1]], color=INK, lw=2)
    elif title.startswith("complete"):
        i, j = np.unravel_index(d.argmax(), d.shape)
        ax.plot([CA[i, 0], CB[j, 0]], [CA[i, 1], CB[j, 1]], color=INK, lw=2)
    elif title.startswith("average"):
        for i in range(len(CA)):
            for j in range(len(CB)):
                ax.plot([CA[i, 0], CB[j, 0]], [CA[i, 1], CB[j, 1]], color=GRAY, lw=0.4, alpha=0.6)
    else:
        mA, mB, mAB = CA.mean(0), CB.mean(0), np.vstack([CA, CB]).mean(0)
        for P, m in [(CA, mA), (CB, mB)]:
            for p in P:
                ax.plot([p[0], m[0]], [p[1], m[1]], color=GRAY, lw=0.6)
        for p in np.vstack([CA, CB]):
            ax.plot([p[0], mAB[0]], [p[1], mAB[1]], color=INK, lw=0.6, ls=":")
        ax.scatter(*mA, marker="x", color=INK, s=70, linewidths=2, zorder=4)
        ax.scatter(*mB, marker="x", color=INK, s=70, linewidths=2, zorder=4)
        ax.scatter(*mAB, marker="x", color=INK, s=110, linewidths=2.5, zorder=4)
    ax.set_title(title, fontsize=11)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_visible(False)
fig.tight_layout()
save(fig, "hc_linkage.webp")


# ---- 実験 2: 2 つの塊の間に 8 点を足す ----
rng = np.random.RandomState(0)
A = rng.randn(100, 2) * 0.5
B = rng.randn(100, 2) * 0.5 + [6, 0]
X2 = np.vstack([A, B])
y2 = np.r_[[0] * 100, [1] * 100]
bridge = np.column_stack([np.linspace(1.5, 4.5, 8), np.zeros(8)])  # 塊の間に一列に並べた 8 点
X2b = np.vstack([X2, bridge])
labs2 = {}
for title, data, method in [("橋渡しなし single", X2, "single"),
                            ("橋渡しあり single", X2b, "single"),
                            ("橋渡しあり ward", X2b, "ward")]:
    lab = AgglomerativeClustering(n_clusters=2, linkage=method).fit_predict(data)
    labs2[title] = lab
    print(f"{title}: 点の数 {sorted(np.bincount(lab).tolist(), reverse=True)}、"
          f"塊の 200 点の ARI {adjusted_rand_score(y2, lab[:200]):.2f}")

# 鎖の端と塊の距離、塊の点の最も近い点までの距離（single が 1 点だけを残した理由）
nn2 = np.sort(np.linalg.norm(X2[:, None] - X2[None], axis=2), axis=1)[:, 1]
print(f"鎖の端と左の塊 {np.linalg.norm(A - bridge[0], axis=1).min():.3f}、右の塊 {np.linalg.norm(B - bridge[-1], axis=1).min():.3f}、"
      f"塊の点の最も近い点までの距離の最大 {nn2.max():.3f}")

fig, axes = plt.subplots(1, 3, figsize=(12, 2.9))
for ax, (title, lab) in zip(axes, labs2.items()):
    data = X2 if len(lab) == 200 else X2b
    counts = np.bincount(lab)
    for c in np.unique(lab):
        m = lab == c
        small = counts[c] < 5  # 1 点だけのクラスタは大きな星で目立たせる
        ax.scatter(data[m, 0], data[m, 1], s=160 if small else 10, alpha=0.9 if small else 0.6,
                   color=PALETTE[c], marker="*" if small else "o", zorder=4 if small else 2)
    if len(lab) > 200:
        ax.scatter(bridge[:, 0], bridge[:, 1], s=40, facecolors="none", edgecolors=INK, lw=1)
    sizes = sorted(np.bincount(lab).tolist(), reverse=True)
    ax.set_title(f"{title}\nk=2 の点の数 {sizes[0]} と {sizes[1]}", fontsize=11)
    ax.set_aspect("equal")
    ax.axis("off")
fig.tight_layout()
save(fig, "hc_chain.webp")


# ---- 実験 3: 同じ距離の組があると、行の順番で結果が変わる ----
P = np.array([[0.0], [1.0], [2.0]])  # 0 と 1、1 と 2 の距離はどちらも 1
tie_rows = []
for order in [[0, 1, 2], [2, 1, 0]]:
    lab = AgglomerativeClustering(n_clusters=2, linkage="complete").fit_predict(P[order])
    back = np.empty_like(lab)
    back[order] = lab
    tie_rows.append((order, back))
    print(f"行の順番 {order}: 点 0・1・2 のクラスタ {back.tolist()}")

fig, axes = plt.subplots(2, 1, figsize=(6, 2.6))
for ax, (order, back) in zip(axes, tie_rows):
    first = back[1]
    for i in range(3):
        same = back[i] == first
        ax.scatter(P[i, 0], 0, s=420, color=BLUE if same else RED, zorder=3)
        ax.text(P[i, 0], 0, str(i), ha="center", va="center", color="white", fontsize=12)
    ax.annotate("", xy=(0.82, 0.22), xytext=(0.18, 0.22),
                arrowprops=dict(arrowstyle="<->", color=GRAY))
    ax.annotate("", xy=(1.82, 0.22), xytext=(1.18, 0.22),
                arrowprops=dict(arrowstyle="<->", color=GRAY))
    ax.text(0.5, 0.3, "1", ha="center", color=GRAY)
    ax.text(1.5, 0.3, "1", ha="center", color=GRAY)
    ax.text(-0.45, 0, f"入力の順番\n{', '.join(map(str, order))}", ha="right", va="center", fontsize=10)
    ax.set_xlim(-1.4, 2.4)
    ax.set_ylim(-0.35, 0.5)
    ax.axis("off")
fig.suptitle("同じ 3 点を complete linkage で 2 つに分けた結果", fontsize=11)
fig.tight_layout()
save(fig, "hc_ties.webp")

digits = load_digits()
Xd, yd = digits.data, digits.target
print(f"digits: {len(np.unique(pdist(Xd)))} 種類の距離 / {len(Xd) * (len(Xd) - 1) // 2} 組")
for method in ["single", "complete", "average", "ward"]:
    base = AgglomerativeClustering(n_clusters=10, linkage=method).fit_predict(Xd)
    changed, aris = 0, []
    for s in range(20):
        order = np.random.RandomState(s).permutation(len(Xd))
        lab = AgglomerativeClustering(n_clusters=10, linkage=method).fit_predict(Xd[order])
        back = np.empty_like(lab)
        back[order] = lab
        changed += adjusted_rand_score(base, back) < 0.999
        aris.append(adjusted_rand_score(yd, back))
    print(f"digits {method}: 変わった回 {changed}/20、正解との ARI {min(aris):.3f}〜{max(aris):.3f}")


# ---- 実験 3b: 結合のたびに、最も近い組が同点だった回を数える ----
def count_ties(X, method):
    """最も近い組が同点だった結合の番号を返す。同点の時は番号の小さい組をつなぐ 1 通りの道筋で数える。"""
    D = squareform(pdist(X))
    np.fill_diagonal(D, np.inf)
    size = np.ones(len(X))
    alive = np.ones(len(X), bool)
    tied, heights = [], []
    for step in range(1, len(X)):
        m = D.min()
        cand = np.argwhere(D <= m * (1 + 1e-12))  # 丸め誤差の範囲で最小と等しい組
        cand = cand[cand[:, 0] < cand[:, 1]]
        if len(cand) > 1:
            tied.append(step)
        i, j = cand[0]
        heights.append(m)
        di, dj, dij = D[i].copy(), D[j].copy(), D[i, j]
        if method == "ward":  # Lance-Williams の更新式で、まとめたクラスタと他の距離を計算し直す
            T = size[i] + size[j] + size
            new = np.sqrt(np.maximum(((size[i] + size) * di**2 + (size[j] + size) * dj**2 - size * dij**2) / T, 0))
        else:  # complete: 2 つの距離の大きい方
            new = np.maximum(di, dj)
        new[~alive] = np.inf
        D[i, :] = new
        D[:, i] = new
        D[i, i] = np.inf
        D[j, :] = np.inf
        D[:, j] = np.inf
        alive[j] = False
        size[i] += size[j]
    return tied, np.array(heights)


# 自前の更新が SciPy と同じ高さになるかを、同点の無い連続値で確かめる
_, h_cont = count_ties(X_cont, "ward")
print("連続値の ward の高さと SciPy の差の最大:", float(np.abs(np.sort(h_cont) - linkage(X_cont, "ward")[:, 2]).max()))
tie_cases = [("1〜5 の回答、ward", X_int, "ward", 3), ("digits、ward", Xd, "ward", 10),
             ("digits、complete", Xd, "complete", 10)]
tie_res = []
for title, X, method, k in tie_cases:
    tied, _ = count_ties(X, method)
    n = len(X)
    last = max(tied) if tied else None
    tie_res.append((title, n, k, tied))
    print(f"{title}: {n - 1} 回の結合のうち同点 {len(tied)} 回、最後の同点は {last} 回目"
          f"（その後に残るクラスタ {n - last} 個、切る数 {k}）")

fig, axes = plt.subplots(len(tie_res), 1, figsize=(10, 3.6), sharex=True)
for ax, (title, n, k, tied) in zip(axes, tie_res):
    remain = n - np.array(tied)  # 同点の結合の後に残るクラスタの数
    ax.vlines(remain, 0, 1, color=RED, lw=0.6, alpha=0.6)
    ax.axvline(k, color=INK, ls="--", lw=1.2)
    ax.text(k * 0.9, 0.5, f"切る数 {k}", ha="left", va="center", fontsize=9, color=INK,
            bbox=dict(fc="white", ec="none", pad=1))
    ax.set_xscale("log")
    ax.set_xlim(2000, 1)
    ax.set_yticks([])
    ax.minorticks_off()
    ax.set_title(f"{title}　同点 {len(tied)} 回 / 結合 {n - 1} 回、最後の同点の後に残るクラスタ {n - max(tied)} 個",
                 fontsize=10, loc="left")
    for sp in ["left", "right", "top"]:
        ax.spines[sp].set_visible(False)
axes[-1].set_xlabel("その結合の後に残るクラスタの数（対数。右へ進むほど木の上の方）")
axes[-1].set_xticks([1000, 300, 100, 30, 10, 3, 1])
axes[-1].set_xticklabels(["1000", "300", "100", "30", "10", "3", "1"])
fig.tight_layout()
save(fig, "hc_tie_steps.webp")


# ---- 実験 4: wine でコフェネティック相関係数と ARI を比べる ----
wine = load_wine()
Xw = StandardScaler().fit_transform(wine.data)
yw = wine.target
dist_w = pdist(Xw)
Zs = {}
for method in ["single", "complete", "average", "ward"]:
    Z = linkage(Xw, method=method)
    Zs[method] = Z
    c, _ = cophenet(Z, dist_w)
    lab = fcluster(Z, t=3, criterion="maxclust")
    sizes = sorted(np.bincount(lab)[1:].tolist(), reverse=True)
    print(f"{method:8s} コフェネティック相関 {c:.3f}  k=3 の点の数 {sizes}  ARI {adjusted_rand_score(yw, lab):.3f}")
lab8 = fcluster(Zs["average"], t=8, criterion="maxclust")
print("average を k=8 で切る: 点の数", sorted(np.bincount(lab8)[1:].tolist(), reverse=True),
      f"ARI {adjusted_rand_score(yw, lab8):.3f}")
print("上の 4 回の結合の高さ average", Zs["average"][-4:, 2].round(2), "ward", Zs["ward"][-4:, 2].round(2))

fig, axes = plt.subplots(1, 2, figsize=(12, 4))
for ax, method in zip(axes, ["average", "ward"]):
    Z = Zs[method]
    cut = (Z[-3, 2] + Z[-2, 2]) / 2  # k=3 になる高さ（上から 2 回目と 3 回目の結合の間）
    c, _ = cophenet(Z, dist_w)
    lab = fcluster(Z, t=3, criterion="maxclust")
    sizes = sorted(np.bincount(lab)[1:].tolist(), reverse=True)
    dendrogram(Z, ax=ax, no_labels=True, color_threshold=cut, above_threshold_color=GRAY,
               link_color_func=None)
    ax.axhline(cut, color=RED, ls="--", lw=1.2)
    ax.set_title(f"{method}　コフェネティック相関 {c:.3f}\n"
                 f"k=3 で切ると {sizes[0]}・{sizes[1]}・{sizes[2]} 本、ARI {adjusted_rand_score(yw, lab):.2f}",
                 fontsize=11)
    ax.set_ylabel("結合した時の高さ")
    ax.set_xlabel("178 本のワイン")
fig.tight_layout()
save(fig, "hc_wine.webp")


# ---- 実験 5: 点の数と、時間・メモリ ----
MEASURE = r"""
import json, resource, sys, time
from sklearn.cluster import AgglomerativeClustering, Birch, KMeans
from sklearn.datasets import make_blobs
algo, n = sys.argv[1], int(sys.argv[2])
X, _ = make_blobs(n_samples=n, centers=5, n_features=10, random_state=0)
before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
t = time.perf_counter()
if algo == "ward":
    AgglomerativeClustering(n_clusters=5).fit(X)
elif algo == "kmeans":
    KMeans(n_clusters=5, n_init=10, random_state=0).fit(X)
elif algo == "birch":
    m = Birch(n_clusters=5).fit(X)
else:
    m = Birch(n_clusters=5, threshold=3.0).fit(X)
sec = time.perf_counter() - t
peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
sub = len(m.subcluster_centers_) if algo.startswith("birch") else None
print(json.dumps({"sec": sec, "peak_mb": peak / 1024, "before_mb": before / 1024, "sub": sub}))
"""
ns = [1000, 2000, 5000, 10000, 20000]
algos = {"ward": "ward", "kmeans": "k-means", "birch": "Birch（既定）", "birch3": "Birch（threshold=3.0）"}
scale = {a: [] for a in algos}
for a in ([] if "--no-scale" in sys.argv else algos):
    for n in ns:
        # 他の処理と同じ機械で測るので、3 回測って一番短い時間を使う（メモリは毎回ほぼ同じ）
        runs = [json.loads(subprocess.run([sys.executable, "-c", MEASURE, a, str(n)], capture_output=True,
                                          text=True, check=True).stdout) for _ in range(3)]
        r = min(runs, key=lambda x: x["sec"])
        scale[a].append(r)
        sub = f"、葉 {r['sub']}" if r["sub"] is not None else ""
        print(f"{algos[a]} n={n}: {r['sec']:.2f} 秒、ピークのメモリ {r['peak_mb']:.0f} MB"
              f"（fit の前 {r['before_mb']:.0f} MB）{sub}")
X20, y20 = make_blobs(n_samples=20000, centers=5, n_features=10, random_state=0)
nn20 = NearestNeighbors(n_neighbors=2).fit(X20).kneighbors(X20)[0][:, 1]
print(f"20000 点の最も近い点までの距離の中央値 {np.median(nn20):.3f}、"
      f"Birch(threshold=3.0) の正解との ARI {adjusted_rand_score(y20, Birch(n_clusters=5, threshold=3.0).fit_predict(X20)):.3f}")
print(f"n=20000 の距離の表の大きさ: {20000 * 19999 / 2 * 8 / 1e9:.2f} GB")

if all(scale.values()):  # --no-scale の時は計測も図の保存もしない
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.8))
    styles = {"ward": (RED, "o"), "kmeans": (BLUE, "s"), "birch": (ORANGE, "^"), "birch3": (GREEN, "v")}
    for a, name in algos.items():
        col, mk = styles[a]
        axes[0].plot(ns, [r["sec"] for r in scale[a]], marker=mk, color=col, label=name)
        axes[1].plot(ns, [r["peak_mb"] / 1024 for r in scale[a]], marker=mk, color=col, label=name)
    axes[0].set_ylabel("fit に掛かった時間（秒、対数）")
    axes[0].set_yscale("log")
    axes[0].set_yticks([0.01, 0.1, 1, 10])
    axes[0].set_yticklabels(["0.01", "0.1", "1", "10"])
    axes[1].set_ylabel("プロセスのピークのメモリ（GB）")
    axes[1].set_ylim(0, 3.5)
    axes[1].text(20000, scale["ward"][-1]["peak_mb"] / 1024, "ward と Birch（既定）\nがほぼ重なる  ",
                 ha="right", va="top", fontsize=9, color=INK)
    for ax in axes:
        ax.set_xscale("log")
        ax.set_xlabel("点の数（対数）")
        ax.minorticks_off()
        ax.set_xticks(ns)
        ax.set_xticklabels([f"{n:,}" for n in ns])
        ax.grid(True, which="major", color="#eeeeee")
    axes[0].legend(fontsize=9, frameon=False)
    fig.tight_layout()
    save(fig, "hc_scale.webp")
