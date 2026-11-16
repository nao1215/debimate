"""dbscan ノートの実験と図を生成するスクリプト。

本文に載せた実験（コア点・境界点・ノイズ、三日月での k-means との比較、eps を動かした時の
塊の数とノイズ、k-距離グラフ、min_samples=1 と単連結法、密度の違う塊と HDBSCAN、wine の eps と min_samples の総当たり、
コア点のつながり方、行の順番と境界点、近傍の数とメモリ）を同じ順に実行し、
出力を標準出力に、図を Page Bundle に WebP で保存する。
実行: cd projects/ml && .venv/bin/python scripts/notes/dbscan_gen.py
確認した版: scikit-learn 1.9.1、NumPy 2.5.4、SciPy 1.18.1、matplotlib 3.11.2
"""
import subprocess
import sys
from io import BytesIO
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import cdist
from collections import deque

from sklearn.cluster import DBSCAN, HDBSCAN, OPTICS, KMeans
from sklearn.datasets import load_wine, make_blobs, make_moons
from sklearn.metrics import adjusted_rand_score
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

NOTE_DIR = Path(__file__).resolve().parents[2] / "notes" / "ml" / "dbscan"
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10,
                     "axes.spines.top": False, "axes.spines.right": False})
BLUE, RED, GREEN, ORANGE, PURPLE = "#7aa6c2", "#e15759", "#59a14f", "#f28e2b", "#9c755f"
INK, GRAY = "#333333", "#aaaaaa"
PALETTE = [BLUE, ORANGE, GREEN, PURPLE, "#b07aa1", "#edc948", "#76b7b2", "#ff9da7"]


def save(fig, name):
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight", facecolor="#ffffff")
    plt.close(fig)
    buf.seek(0)
    Image.open(buf).convert("RGB").save(NOTE_DIR / name, "WEBP", quality=90, method=6)


def n_clusters(labels):
    return len(set(labels)) - (1 if -1 in labels else 0)


def scatter_labels(ax, X, labels, core=None, s=12):
    """ラベルごとに色を変えて描く。ノイズ（-1）は灰色の x。"""
    for c in sorted(set(labels) - {-1}):
        m = labels == c
        ax.scatter(X[m, 0], X[m, 1], s=s, color=PALETTE[c % len(PALETTE)], linewidths=0)
    m = labels == -1
    ax.scatter(X[m, 0], X[m, 1], s=s, marker="x", color=GRAY, linewidths=0.8)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_aspect("equal")


# 実験 8 の子プロセス: numpy と scikit-learn だけを読み込み、1 万点の DBSCAN の間に
# メモリ（RSS）が最大でどれだけ増えたかを測る。/proc/self/clear_refs に 5 を書くと
# 最大の RSS（VmHWM）が今の RSS に戻るので、読み込みの時の山を数えずに済む（Linux 4.0 以降）
MEMORY_CHILD = """
import sys, numpy as np
from sklearn.cluster import DBSCAN, HDBSCAN
def kb(key):
    return int([l for l in open("/proc/self/status") if l.startswith(key)][0].split()[1])
X = np.random.default_rng(0).uniform(0, 1, size=(10_000, 2))
open("/proc/self/clear_refs", "w").write("5")
before = kb("VmRSS")
if sys.argv[1] == "hdbscan":
    HDBSCAN(min_samples=5, copy=True).fit(X)
else:
    DBSCAN(eps=float(sys.argv[1]), min_samples=5).fit(X)
print((kb("VmHWM") - before) / 1024)
"""


# ============================================================
# 実験 1: コア点・境界点・ノイズ
# ============================================================
rng = np.random.default_rng(3)
toy = np.vstack([
    rng.normal([0.0, 0.0], 0.35, size=(14, 2)),
    rng.normal([2.4, 0.4], 0.35, size=(12, 2)),
    [[1.2, 1.5], [3.6, -1.0], [-1.0, 1.4]],
])
model = DBSCAN(eps=0.5, min_samples=4).fit(toy)
is_core = np.zeros(len(toy), bool)
is_core[model.core_sample_indices_] = True
kind = np.where(is_core, "コア点", np.where(model.labels_ == -1, "ノイズ", "境界点"))
print("実験 1:", {k: int((kind == k).sum()) for k in ["コア点", "境界点", "ノイズ"]})

fig, ax = plt.subplots(figsize=(7.2, 4.0))
pick = {"コア点": np.flatnonzero(is_core)[0],
        "境界点": np.flatnonzero((~is_core) & (model.labels_ != -1))[0],
        "ノイズ": np.flatnonzero(model.labels_ == -1)[0]}
offset = {"コア点": (1.4, -0.6), "境界点": (-0.55, 1.1), "ノイズ": (-1.9, -0.25)}
for k, i in pick.items():
    ax.add_patch(plt.Circle(toy[i], 0.5, fill=False, ls="--", color=INK, lw=0.9))
    cnt = int((np.linalg.norm(toy - toy[i], axis=1) <= 0.5).sum())
    dx, dy = offset[k]
    ax.annotate(f"{k}: 近傍に {cnt} 点", toy[i], xytext=(toy[i][0] + dx, toy[i][1] + dy),
                fontsize=9, color=INK, arrowprops=dict(arrowstyle="-", color=INK, lw=0.6))
for c in sorted(set(model.labels_) - {-1}):
    m = (model.labels_ == c)
    ax.scatter(*toy[m & is_core].T, s=46, color=PALETTE[c], zorder=3, label=f"クラスタ {c} のコア点" if c == 0 else None)
    ax.scatter(*toy[m & ~is_core].T, s=46, facecolors="white", edgecolors=PALETTE[c], linewidths=1.6, zorder=3,
               label="境界点（白抜き）" if c == 0 else None)
ax.scatter(*toy[model.labels_ == -1].T, s=46, marker="x", color=GRAY, zorder=3, label="ノイズ（-1）")
ax.set_aspect("equal")
ax.set_xticks([])
ax.set_yticks([])
ax.set_title("eps=0.5、min_samples=4（点線の円の中が近傍）", fontsize=10)
ax.legend(loc="upper right", fontsize=8, frameon=False)
save(fig, "dbscan_points.webp")


# ============================================================
# 実験 2: 三日月で k-means と比べる
# ============================================================
Xm, ym = make_moons(n_samples=400, noise=0.06, random_state=0)
Xm = np.vstack([Xm, np.random.default_rng(1).uniform([-1.2, -0.7], [2.2, 1.2], size=(20, 2))])
ym = np.r_[ym, np.full(20, -1)]
lab_km = KMeans(n_clusters=2, n_init=10, random_state=0).fit_predict(Xm)
lab_db = DBSCAN(eps=0.15, min_samples=5).fit_predict(Xm)
print(f"実験 2: k-means の ARI {adjusted_rand_score(ym[:400], lab_km[:400]):.3f}、"
      f"DBSCAN の ARI {adjusted_rand_score(ym[:400], lab_db[:400]):.3f}、"
      f"DBSCAN のクラスタ {n_clusters(lab_db)} 個、ノイズ {(lab_db == -1).sum()} 点"
      f"（足した 20 点のうち {(lab_db[400:] == -1).sum()} 点）")

fig, axes = plt.subplots(1, 2, figsize=(9, 3.4))
scatter_labels(axes[0], Xm, lab_km)
axes[0].set_title("k-means（k=2）", fontsize=10)
scatter_labels(axes[1], Xm, lab_db)
axes[1].set_title("DBSCAN（eps=0.15、min_samples=5）。灰色の x はノイズ", fontsize=10)
save(fig, "dbscan_moons.webp")


# ============================================================
# 実験 3: eps を動かすと塊の数とノイズが変わる。k-距離グラフ
# ============================================================
eps_list = np.round(np.arange(0.02, 0.501, 0.01), 2)
ks, noise = [], []
for eps in eps_list:
    lab = DBSCAN(eps=eps, min_samples=5).fit_predict(Xm)
    ks.append(n_clusters(lab))
    noise.append(np.mean(lab == -1))
for eps in [0.05, 0.10, 0.15, 0.20, 0.30, 0.40]:
    i = int(np.argmin(np.abs(eps_list - eps)))
    print(f"実験 3: eps={eps:.2f} クラスタ {ks[i]:>2} 個、ノイズ {noise[i]:.0%}")
two = eps_list[np.array(ks) == 2]
print(f"実験 3: クラスタが 2 個になる eps の範囲 {two.min():.2f}〜{two.max():.2f}")

# min_samples=5 は自分を含めて 5 点なので、自分以外で 4 番目に近い点までの距離を並べる
kdist = np.sort(NearestNeighbors(n_neighbors=4).fit(Xm).kneighbors()[0][:, -1])
print(f"実験 3: 4 番目に近い点までの距離 中央値 {np.median(kdist):.3f}、95% 点 {np.percentile(kdist, 95):.3f}")

fig, axes = plt.subplots(1, 2, figsize=(11, 3.6))
fig.subplots_adjust(wspace=0.5)
ax = axes[0]
ax.plot(eps_list, ks, color=BLUE, lw=1.8, label="クラスタの数")
ax.set_xlabel("eps")
ax.set_ylabel("クラスタの数", color=BLUE)
ax.axvspan(two.min(), two.max(), color=GREEN, alpha=0.12)
ax.text((two.min() + two.max()) / 2, max(ks) * 0.85, "クラスタが 2 個", color=GREEN, ha="center", fontsize=9)
ax2 = ax.twinx()
ax2.plot(eps_list, np.array(noise) * 100, color=RED, lw=1.5, ls="--", label="ノイズの割合")
ax2.set_ylabel("ノイズの割合（%）", color=RED)
ax2.spines["right"].set_visible(True)
ax.set_title("eps とクラスタの数・ノイズ（min_samples=5）", fontsize=10)
ax = axes[1]
ax.plot(np.arange(len(kdist)), kdist, color=INK, lw=1.4)
ax.axhspan(two.min(), two.max(), color=GREEN, alpha=0.12)
ax.text(30, (two.min() + two.max()) / 2, "クラスタが 2 個になる eps", color=GREEN, va="center", fontsize=9)
ax.set_xlabel("点（距離の小さい順）")
ax.set_ylabel("4 番目に近い点までの距離")
ax.set_title("k-距離グラフ（k=4）", fontsize=10)
save(fig, "dbscan_eps.webp")


# ============================================================
# 実験 3（続き）: min_samples=1 の DBSCAN と、単連結法を高さ eps で切った結果
# ============================================================
Z = linkage(Xm[:400], method="single")
for eps in [0.05, 0.10, 0.15]:
    lab_1 = DBSCAN(eps=eps, min_samples=1).fit_predict(Xm[:400])
    lab_s = fcluster(Z, t=eps, criterion="distance")
    print(f"実験 3: eps={eps:.2f} min_samples=1 のクラスタ {n_clusters(lab_1)} 個、ノイズ {(lab_1 == -1).sum()}、"
          f"single の木との ARI {adjusted_rand_score(lab_1, lab_s):.3f}")


# ============================================================
# 実験 4: 密度の違う塊が並ぶと、どの eps でも 3 つにならない
# ============================================================
Xd, yd = make_blobs(n_samples=[300, 300], centers=[[0, 0], [1.6, 0]], cluster_std=0.25, random_state=0)
Xs, _ = make_blobs(n_samples=[200], centers=[[5, 4]], cluster_std=1.2, random_state=1)
Xv = np.vstack([Xd, Xs])
yv = np.r_[yd, np.full(200, 2)]
rows = []
for eps in np.round(np.arange(0.05, 1.501, 0.05), 2):
    lab = DBSCAN(eps=eps, min_samples=5).fit_predict(Xv)
    a, b = set(lab[yv == 0]) - {-1}, set(lab[yv == 1]) - {-1}
    dense_split = bool(a) and bool(b) and not (a & b)  # 密な 2 つが同じ塊に入っていない
    rows.append((eps, n_clusters(lab), np.mean(lab[yv == 2] == -1), dense_split))
for eps, k, sn, split in rows:
    if eps in (0.1, 0.2, 0.3, 0.35, 0.4, 0.5, 1.0):
        print(f"実験 4: eps={eps:.2f} クラスタ {k:>2} 個、疎な塊のノイズ {sn:.0%}、密な 2 つが別のクラスタ {split}")
split_eps = [eps for eps, _, _, s in rows if s]
print(f"実験 4: 密な 2 つが別のクラスタになる eps の上限 {max(split_eps):.2f}、"
      f"その時の疎な塊のノイズ {[sn for e, _, sn, _ in rows if e == max(split_eps)][0]:.0%}")
lab_h = HDBSCAN(min_cluster_size=10, copy=True).fit_predict(Xv)
print(f"実験 4: HDBSCAN（min_cluster_size=10）クラスタ {n_clusters(lab_h)} 個、ノイズ {np.mean(lab_h == -1):.1%}、"
      f"ARI {adjusted_rand_score(yv, lab_h):.3f}")

fig, axes = plt.subplots(1, 3, figsize=(12, 3.8))
for ax, eps in zip(axes[:2], [0.2, 0.5]):
    lab = DBSCAN(eps=eps, min_samples=5).fit_predict(Xv)
    scatter_labels(ax, Xv, lab, s=7)
    ax.set_title(f"DBSCAN eps={eps}\nクラスタ {n_clusters(lab)} 個、右上の塊でノイズ {np.mean(lab[yv == 2] == -1):.0%}", fontsize=10)
scatter_labels(axes[2], Xv, lab_h, s=7)
axes[2].set_title(f"HDBSCAN min_cluster_size=10\nクラスタ {n_clusters(lab_h)} 個、ノイズ {np.mean(lab_h == -1):.0%}", fontsize=10)
save(fig, "dbscan_density.webp")


def condensed_tree(slt, n, mcs):
    """HDBSCAN の単連結の木から、min_cluster_size 未満の枝を落とした木（condensed tree）を作る。
    クラスタごとに、生まれた距離（birth）・消えた距離（death）・親・点の数・木の節を返す。"""
    left, right, val, size = slt["left_node"], slt["right_node"], slt["value"], slt["cluster_size"]

    def sz(node):
        return 1 if node < n else int(size[node - n])

    clusters = [dict(birth=float(val[-1]), parent=-1, size=n, node=2 * n - 2, death=0.0)]
    todo = [0]
    while todo:
        cid = todo.pop()
        node = clusters[cid]["node"]
        while node >= n:
            i = node - n
            l, r, d = int(left[i]), int(right[i]), float(val[i])
            if sz(l) >= mcs and sz(r) >= mcs:
                clusters[cid]["death"] = d
                for ch in (l, r):
                    clusters.append(dict(birth=d, parent=cid, size=sz(ch), node=ch, death=0.0))
                    todo.append(len(clusters) - 1)
                break
            if sz(l) >= mcs:
                node = l
            elif sz(r) >= mcs:
                node = r
            else:
                clusters[cid]["death"] = d
                break
    return clusters


def leaves(slt, n, node):
    out, stack = [], [node]
    while stack:
        v = stack.pop()
        if v < n:
            out.append(v)
        else:
            stack += [int(slt["left_node"][v - n]), int(slt["right_node"][v - n])]
    return set(out)


hdb = HDBSCAN(min_cluster_size=10, copy=True).fit(Xv)
slt = hdb._single_linkage_tree_
ct = condensed_tree(slt, len(Xv), 10)
chosen = {}
for c in sorted(set(hdb.labels_) - {-1}):
    pts = set(np.flatnonzero(hdb.labels_ == c))
    jac = [len(pts & leaves(slt, len(Xv), k["node"])) / len(pts | leaves(slt, len(Xv), k["node"])) for k in ct]
    chosen[int(np.argmax(jac))] = c
print(f"実験 4: HDBSCAN の木の枝 {len(ct)} 本、選ばれた枝の生まれた距離と消えた距離 "
      + "、".join(f"{ct[k]['birth']:.2f}→{ct[k]['death']:.2f}（{ct[k]['size']} 点）" for k in sorted(chosen)))

# 木を高さ h で横に切った時に残っている点は、HDBSCAN の min_samples（既定で min_cluster_size と同じ 10）で
# コア点になる点（自分を含めて 10 点が半径 h に入る点）
cd10 = NearestNeighbors(n_neighbors=9).fit(Xv).kneighbors()[0][:, -1]
for h in (0.35,):
    print(f"実験 4: 木を高さ {h} で切った時に残る点 密な塊 {(cd10[yv < 2] <= h).sum()} / 600、"
          f"まばらな塊 {(cd10[yv == 2] <= h).sum()} / 200")
children = {i: [j for j, k in enumerate(ct) if k["parent"] == i] for i in range(len(ct))}
xpos, nxt = {}, [0]


def place(i):
    if not children[i]:
        xpos[i] = nxt[0]
        nxt[0] += 1
    else:
        for j in children[i]:
            place(j)
        xpos[i] = np.mean([xpos[j] for j in children[i]])


place(0)
reach_opt = OPTICS(min_samples=5).fit(Xv)
reach = reach_opt.reachability_[reach_opt.ordering_]
reach[np.isinf(reach)] = np.nan
fig, axes = plt.subplots(1, 2, figsize=(12, 3.9), gridspec_kw={"width_ratios": [1, 1.3]})
fig.subplots_adjust(wspace=0.28)
ax = axes[0]
inside = set()  # 選ばれた枝より下の小さな枝（HDBSCAN が選ばなかった枝）は描かない
for i, k in enumerate(ct):
    if k["parent"] in chosen or k["parent"] in inside:
        inside.add(i)
for i, k in enumerate(ct):
    if i in inside:
        continue
    col = PALETTE[chosen[i]] if i in chosen else GRAY
    ax.plot([xpos[i], xpos[i]], [k["death"], k["birth"]], color=col, lw=1.2 + 6 * k["size"] / len(Xv),
            solid_capstyle="butt")
    if children[i] and i not in chosen:
        xs = [xpos[j] for j in children[i]]
        ax.plot([min(xs), max(xs)], [k["death"]] * 2, color=GRAY, lw=1)
ax.axhline(0.35, color=RED, ls="--", lw=1.2)
ax.text(np.mean([xpos[i] for i in chosen if ct[i]["birth"] < 1]), 0.31, "eps=0.35", color=RED, ha="center", va="top", fontsize=9)
ax.text(ax.get_xlim()[1], 2.1, "線の太さは\n点の数", color=INK, ha="right", va="top", fontsize=8)
ax.set_xticks([])
ax.set_ylabel("距離（eps に当たる）")
for i, c in chosen.items():
    name = "まばらな塊" if ct[i]["birth"] > 1 else "密な塊"
    ax.text(xpos[i] + 0.12, (ct[i]["birth"] + ct[i]["death"]) / 2, f"{name}\n{ct[i]['size']} 点",
            color=PALETTE[c], fontsize=9, va="center")
ax.set_title("HDBSCAN の木（min_cluster_size=10）", fontsize=10)
ax.spines["bottom"].set_visible(False)
ax = axes[1]
order_lab = yv[reach_opt.ordering_]
for g, name in sorted([(0, "密な塊"), (1, "密な塊"), (2, "まばらな塊")],
                      key=lambda t: np.flatnonzero(order_lab == t[0])[0]):  # 凡例を棒の並びの順にする
    m = order_lab == g
    hl = np.bincount(hdb.labels_[yv == g][hdb.labels_[yv == g] >= 0]).argmax()  # 木と同じ色にする
    ax.bar(np.flatnonzero(m), reach[m], width=1.0, color=PALETTE[hl], label=f"{name}（{m.sum()} 点）", linewidth=0)
for e, ls in [(0.35, "--"), (0.5, ":")]:
    ax.axhline(e, color=RED, ls=ls, lw=1.2)
    ax.text(330, e + 0.02, f"eps={e}", color=RED, va="bottom", fontsize=9)
ax.set_xlabel("OPTICS が並べた点の順番")
ax.set_ylabel("到達可能距離")
ax.set_ylim(0, 1.2)
ax.set_title("OPTICS が並べた順と到達可能距離（min_samples=5）", fontsize=10)
ax.legend(fontsize=8, frameon=False, loc="upper left")
save(fig, "dbscan_tree.webp")


# ============================================================
# 実験 5: wine で eps と min_samples を総当たりする（表紙）
# ============================================================
wine = load_wine()
Xw = StandardScaler().fit_transform(wine.data)
yw = wine.target
eps_grid = np.round(np.arange(1.0, 4.001, 0.05), 2)
ms_grid = np.arange(2, 31)
ari = np.zeros((len(ms_grid), len(eps_grid)))
k_grid = np.zeros_like(ari, dtype=int)
noise_grid = np.zeros_like(ari)
for i, ms in enumerate(ms_grid):
    for j, eps in enumerate(eps_grid):
        lab = DBSCAN(eps=eps, min_samples=ms).fit_predict(Xw)
        ari[i, j] = adjusted_rand_score(yw, lab)
        k_grid[i, j] = n_clusters(lab)
        noise_grid[i, j] = np.mean(lab == -1)
i, j = np.unravel_index(np.argmax(ari), ari.shape)
print(f"実験 5: 組み合わせ {ari.size} 通り、ARI の最大 {ari[i, j]:.3f}"
      f"（eps={eps_grid[j]}、min_samples={ms_grid[i]}、クラスタ {k_grid[i, j]} 個、ノイズ {noise_grid[i, j]:.0%}）")
m3 = k_grid == 3
i3, j3 = np.unravel_index(np.argmax(np.where(m3, ari, -1)), ari.shape)
print(f"実験 5: クラスタが 3 個になった {m3.sum()} 通りの ARI の最大 {ari[i3, j3]:.3f}（ノイズ {noise_grid[i3, j3]:.0%}）")
low = m3 & (noise_grid < 0.1)
print(f"実験 5: クラスタが 3 個でノイズ 10% 未満の組み合わせ {low.sum()} 通り、その ARI の最大 {ari[low].max():.3f}")
for i5, j5 in zip(*np.nonzero(low)):
    lab = DBSCAN(eps=eps_grid[j5], min_samples=ms_grid[i5]).fit_predict(Xw)
    sizes = sorted(np.bincount(lab[lab >= 0]).tolist(), reverse=True)
    print(f"実験 5:   eps={eps_grid[j5]} min_samples={ms_grid[i5]} クラスタの大きさ {sizes}、ノイズ {(lab == -1).sum()}")
lab = DBSCAN(eps=eps_grid[j], min_samples=ms_grid[i]).fit_predict(Xw)
print(f"実験 5: ARI が最大の組み合わせのクラスタの大きさ {sorted(np.bincount(lab[lab >= 0]).tolist(), reverse=True)}")
ari_km = adjusted_rand_score(yw, KMeans(n_clusters=3, n_init=10, random_state=0).fit_predict(Xw))
ari_hd = max(adjusted_rand_score(yw, HDBSCAN(min_cluster_size=m, copy=True).fit_predict(Xw)) for m in range(5, 31))
print(f"実験 5: k-means（k=3）の ARI {ari_km:.3f}、HDBSCAN（min_cluster_size 5〜30）の ARI の最大 {ari_hd:.3f}")

fig, ax = plt.subplots(figsize=(8.6, 4.2))
im = ax.imshow(ari, origin="lower", aspect="auto", cmap="Blues", vmin=0, vmax=1,
               extent=[eps_grid[0] - 0.025, eps_grid[-1] + 0.025, ms_grid[0] - 0.5, ms_grid[-1] + 0.5])
ax.plot(eps_grid[j], ms_grid[i], marker="*", color=RED, ms=13)
ax.annotate(f"最大 {ari[i, j]:.2f}", (eps_grid[j], ms_grid[i]), xytext=(eps_grid[j] + 0.25, ms_grid[i] + 1.5),
            color=RED, fontsize=10, arrowprops=dict(arrowstyle="-", color=RED, lw=0.8))
cb = fig.colorbar(im, ax=ax, pad=0.02)
cb.set_label("品種との ARI")
cb.ax.axhline(ari_km, color=RED, lw=2)
cb.ax.text(1.6, ari_km, f" k-means {ari_km:.2f}", color=RED, va="center", fontsize=9, transform=cb.ax.get_yaxis_transform())
ax.set_xlabel("eps")
ax.set_ylabel("min_samples")
ax.set_title(f"wine（標準化）を DBSCAN で分けた {ari.size} 通りの ARI", fontsize=10)
ax.spines["top"].set_visible(True)
ax.spines["right"].set_visible(True)
save(fig, "dbscan_cover.webp")


# ============================================================
# 実験 6: 品種どうしがコア点でつながる eps と、コア点になる割合
# ============================================================
def core_dist(X, ms):
    """自分を含めて ms 点が半径に入る最小の eps（自分以外で ms-1 番目に近い点までの距離）。"""
    return NearestNeighbors(n_neighbors=ms - 1).fit(X).kneighbors()[0][:, -1]


def link_eps(X, y, cd, a, b):
    """品種 a と b のコア点どうしが半径 eps でつながる最小の eps。"""
    D = cdist(X[y == a], X[y == b])
    return np.maximum(D, np.maximum(cd[y == a][:, None], cd[y == b][None, :])).min()


Xb, yb = make_blobs(n_samples=600, centers=[[0, 0], [3, 0], [1.5, 2.6]], cluster_std=0.5, random_state=0)
fig, axes = plt.subplots(1, 2, figsize=(10.5, 3.6), sharey=True)
grid = np.linspace(0, 4, 401)
for ax, (X, y, title, names) in zip(axes, [
        (Xb, yb, "離れた 3 つの塊（make_blobs）", ["塊 0", "塊 1", "塊 2"]),
        (Xw, yw, "wine（標準化）", ["品種 0", "品種 1", "品種 2"])]):
    cd = core_dist(X, 5)
    for c in range(3):
        frac = (cd[y == c][:, None] <= grid[None, :]).mean(axis=0) * 100
        ax.plot(grid, frac, color=PALETTE[c], lw=1.8, label=f"{names[c]} のコア点の割合")
    first = min(((link_eps(X, y, cd, a, b), a, b) for a, b in [(0, 1), (0, 2), (1, 2)]))
    half = [np.median(cd[y == c]) for c in range(3)]
    print(f"実験 6: {title}: 最初につながる組 {first[1]}-{first[2]} の eps {first[0]:.2f}、"
          f"{'塊' if X is Xb else '品種'}ごとに半分がコア点になる eps {np.round(half, 2).tolist()}")
    ax.axvline(first[0], color=RED, ls="--", lw=1.2)
    ax.text(first[0] + 0.05, 8, f"{names[first[1]]} と{names[first[2]]} が\nつながる eps={first[0]:.2f}",
            color=RED, fontsize=9)
    ax.set_xlim(0, 4)
    ax.set_xlabel("eps")
    ax.set_title(title + "、min_samples=5", fontsize=10)
    ax.legend(loc="center right" if X is Xb else "upper left", fontsize=8, frameon=False)
axes[0].set_ylabel("コア点になった点の割合（%）")
save(fig, "dbscan_valley.webp")
for eps in [0.3, 0.4, 0.5, 0.6]:
    lab = DBSCAN(eps=eps, min_samples=5).fit_predict(Xb)
    print(f"実験 6: 離れた 3 つの塊を eps={eps} で分けた結果: クラスタ {n_clusters(lab)} 個、"
          f"ノイズ {(lab == -1).sum()} 点、ARI {adjusted_rand_score(yb, lab):.3f}")
for X, title in [(Xb, "離れた 3 つの塊（make_blobs）"), (Xw, "wine（標準化）")]:
    nn1 = NearestNeighbors(n_neighbors=1).fit(X).kneighbors()[0][:, 0]
    pair = cdist(X, X)[np.triu_indices(len(X), 1)]
    print(f"実験 6: {title}: 一番近い点までの距離の中央値 {np.median(nn1):.2f}、全ての組の距離の中央値 {np.median(pair):.2f}、"
          f"比 {np.median(pair) / np.median(nn1):.1f} 倍")


# ============================================================
# 実験 7: 行の順番を変えると、境界点が入るクラスタが変わる
# ============================================================
Xo, _ = make_blobs(n_samples=[200, 200], centers=[[0, 0], [1.6, 0]], cluster_std=0.4, random_state=0)
base = DBSCAN(eps=0.25, min_samples=15).fit(Xo)
core_o = np.zeros(len(Xo), bool)
core_o[base.core_sample_indices_] = True


def canon(labels):
    """クラスタの番号を、元の行の番号で一番若いコア点の番号に付け替える（番号の振り方の違いを消す）。"""
    out = np.full(len(labels), -1)
    for c in set(labels) - {-1}:
        out[labels == c] = np.flatnonzero((labels == c) & core_o).min()
    return out


ref = canon(base.labels_)
rng = np.random.default_rng(0)
changed = np.zeros(len(Xo), bool)
outcomes = {}
for _ in range(100):
    p = rng.permutation(len(Xo))
    lab = np.empty(len(Xo), int)
    lab[p] = DBSCAN(eps=0.25, min_samples=15).fit(Xo[p]).labels_
    cl = canon(lab)
    changed |= cl != ref
    outcomes.setdefault(tuple(cl), p)
print(f"実験 7: クラスタ {n_clusters(base.labels_)} 個、コア点 {core_o.sum()}、"
      f"境界点 {((~core_o) & (base.labels_ != -1)).sum()}、ノイズ {(base.labels_ == -1).sum()}")
print(f"実験 7: 100 回並べ替えて、入るクラスタが変わった点 {changed.sum()}、違う分け方 {len(outcomes)} 通り、"
      f"変わった点はすべて境界点 {bool(np.all(~core_o[changed]))}")

nbrs_o = NearestNeighbors(radius=0.25).fit(Xo).radius_neighbors(Xo, return_distance=False)


def expand(order):
    """scikit-learn と同じく行の順にコア点を探し、見つけたコア点から近傍を伝ってクラスタを広げる。
    点ごとに、入ったクラスタ（広がった順の番号）と、最初のコア点から何回伝って届いたかを返す。"""
    lab, hop = np.full(len(Xo), -1), np.full(len(Xo), -1)
    c = 0
    for i in order:
        if lab[i] != -1 or not core_o[i]:
            continue
        lab[i], hop[i] = c, 0
        q = deque([i])
        while q:
            u = q.popleft()
            if not core_o[u]:
                continue
            for v in nbrs_o[u]:
                if lab[v] == -1:
                    lab[v], hop[v] = c, hop[u] + 1
                    q.append(v)
        c += 1
    return lab, hop


runs = []
for key, perm in list(outcomes.items())[:2]:
    lab, hop = expand(perm)
    assert np.array_equal(canon(lab), np.array(key)), "自前の広げ方が scikit-learn の結果と違う"
    # 塊の色は、広がった順ではなく左右の位置で決める（左の塊を橙、右の塊を青）
    side = {c: int(Xo[lab == c, 0].mean() > 0.8) for c in set(lab) - {-1}}
    runs.append((lab, hop, side))
    first = "左" if side[0] == 0 else "右"
    print(f"実験 7: {len(runs)} 通り目は{first}の塊が先に広がり、変わった {changed.sum()} 点は{first}の塊に入る。"
          f"伝う回数 {hop[lab == 0].max()} 回と {hop[lab == 1].max()} 回")

steps = [(c, h) for c in (0, 1) for h in range(max(r[1][r[0] == c].max() for r in runs) + 1)]
STEP_MS = 400  # 近傍を 1 回伝うごとに 0.4 秒で表示する
frames = []
lo, hi = Xo.min(axis=0) - 0.2, Xo.max(axis=0) + 0.2
for t in range(len(steps) + 1):
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.0), dpi=110)
    fig.subplots_adjust(left=0.02, right=0.98, bottom=0.03, top=0.80, wspace=0.08)
    for n_run, (ax, (lab, hop, side)) in enumerate(zip(axes, runs)):
        done = np.zeros(len(Xo), bool)
        for c, h in steps[:t]:
            done |= (lab == c) & (hop == h)
        ax.scatter(*Xo[~done].T, s=9, color="#dddddd", linewidths=0)
        for c in (0, 1):
            m = done & (lab == c)
            col = [ORANGE, BLUE][side[c]]
            ax.scatter(*Xo[m & core_o].T, s=11, color=col, linewidths=0)
            ax.scatter(*Xo[m & ~core_o].T, s=11, facecolors="white", edgecolors=col, linewidths=0.9)
        if t == len(steps):
            ax.scatter(*Xo[lab == -1].T, s=10, marker="x", color=GRAY, linewidths=0.8)
        ax.scatter(*Xo[changed].T, s=90, facecolors="none", edgecolors=RED, linewidths=1.2)
        first = "左" if side[0] == 0 else "右"
        ax.set_title(f"並べ替え {n_run + 1} 通り目: {first}の塊のコア点が先に出てくる", fontsize=10)
        ax.set_xlim(lo[0], hi[0])
        ax.set_ylim(lo[1], hi[1])
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_aspect("equal")
        for sp in ax.spines.values():
            sp.set_visible(False)
    if t == 0:
        stage = "最初の状態（灰色はまだどのクラスタにも入っていない点）"
    elif t < len(steps):
        c, h = steps[t - 1]
        stage = f"{'1' if c == 0 else '2'} つ目のクラスタが近傍を {h} 回伝ったところ"
    else:
        stage = "終わり。赤い丸の点は先に広がったクラスタに入り、灰色の x はノイズ"
    fig.suptitle(f"{stage}（近傍を 1 回伝うごとに 0.4 秒で表示）", fontsize=10, y=0.98)
    buf = BytesIO()
    fig.savefig(buf, format="png", facecolor="#ffffff")
    plt.close(fig)
    buf.seek(0)
    frames.append(Image.open(buf).convert("RGB"))
durations = [1500] + [STEP_MS] * (len(frames) - 2) + [3500]
frames[0].save(NOTE_DIR / "dbscan_order.webp", "WEBP", save_all=True, append_images=frames[1:],
               duration=durations, loop=0, quality=80, method=6)
print(f"実験 7: 動く図のコマ {len(frames)} 枚、全体 {sum(durations) / 1000:.1f} 秒")


# ============================================================
# 実験 8: 近傍の数とメモリ
# ============================================================
Xu = np.random.default_rng(0).uniform(0, 1, size=(10_000, 2))
nn_u = NearestNeighbors().fit(Xu)
mem_rows = []
for eps in [0.01, 0.03, 0.1, 0.2, 0.3, 0.5, 1.0, 1.5]:
    avg = np.mean([len(a) for a in nn_u.radius_neighbors(Xu, radius=eps, return_distance=False)])
    out = subprocess.run([sys.executable, "-c", MEMORY_CHILD, str(eps)], capture_output=True, text=True, check=True)
    mb = float(out.stdout.strip())
    mem_rows.append((eps, avg, mb))
    print(f"実験 8: eps={eps:<4} 平均の近傍数 {avg:5.0f} 点、増えたメモリ {mb:6.0f} MB、"
          f"10000 × 平均の近傍数 × 8 バイト {10_000 * avg * 8 / 2**20:6.0f} MB")

out = subprocess.run([sys.executable, "-c", MEMORY_CHILD, "hdbscan"], capture_output=True, text=True, check=True)
mb_hdb = float(out.stdout.strip())
print(f"実験 8: HDBSCAN（min_samples=5）で増えたメモリ {mb_hdb:.0f} MB")

fig, ax = plt.subplots(figsize=(7, 3.8))
avg = np.array([r[1] for r in mem_rows])
mb = np.array([r[2] for r in mem_rows])
ax.plot(avg, mb, "o-", color=RED, lw=1.6, label="DBSCAN で増えた最大のメモリ（実測）")
xs = np.linspace(0, 10_000, 50)
ax.plot(xs, 10_000 * xs * 8 / 2**20, ls="--", color=INK, lw=1, label="点の数 × 平均の近傍数 × 8 バイト")
for e, a, m in mem_rows:  # 点の左上に eps を書く（0.01・0.03 は原点に重なるので省く）
    if e == 0.1:  # 原点の近くは線が混むので、空いた所に札を置いて細い線で点を指す
        ax.annotate(f"eps={e}", (a, m), xytext=(1500, 45), textcoords="data", fontsize=8, color=INK,
                    ha="left", va="center", arrowprops=dict(arrowstyle="-", color=INK, lw=0.6))
    elif e == 1.5:  # 赤い線に掛からないよう点の真下に置く
        ax.annotate(f"eps={e}", (a, m), xytext=(0, -18), textcoords="offset points", fontsize=8, color=INK,
                    ha="center")
    elif e >= 0.2:
        ax.annotate(f"eps={e}", (a, m), xytext=(-6, 4), textcoords="offset points", fontsize=8, color=INK,
                    ha="right")
ax.axhline(mb_hdb, color=BLUE, lw=1.4, label=f"HDBSCAN（eps を持たない）{mb_hdb:.0f} MB")
ax.set_xlabel("平均の近傍数（点）")
ax.set_ylabel("メモリ（MB）")
ax.set_title("1 万点の一様乱数で eps を広げた時のメモリ", fontsize=10)
ax.legend(fontsize=8, frameon=False, loc="upper left")
save(fig, "dbscan_memory.webp")
