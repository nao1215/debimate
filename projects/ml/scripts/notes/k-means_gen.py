"""k-means ノートの実験と図を生成するスクリプト。

本文に載せた実験（塊の無いデータへの k-means、手で書いた k-means の反復、k を選ぶ 3 つの指標、
同じ範囲の一様乱数との比較、n_init の既定、wine の列の単位、苦手な形）を本文と同じ順に実行し、
出力を標準出力に、図を Page Bundle に WebP で保存する。
実行: cd projects/ml && .venv/bin/python scripts/notes/k-means_gen.py
確認した版: scikit-learn 1.9.1、NumPy 2.5.4、matplotlib 3.11.2
"""
from collections import Counter
from io import BytesIO
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from sklearn.cluster import KMeans
from sklearn.datasets import load_wine, make_blobs
from sklearn.metrics import adjusted_rand_score, davies_bouldin_score, silhouette_score
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler

NOTE_DIR = Path(__file__).resolve().parents[2] / "notes" / "ml" / "k-means"
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10,
                     "axes.spines.top": False, "axes.spines.right": False})
BLUE, RED, GREEN, INK, GRAY = "#7aa6c2", "#e15759", "#59a14f", "#333333", "#999999"
PALETTE = [BLUE, RED, GREEN, "#f28e2b", "#b07aa1", "#9c755f", "#76b7b2", "#edc948"]


def save(fig, name):
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight", facecolor="#ffffff")
    plt.close(fig)
    buf.seek(0)
    Image.open(buf).convert("RGB").save(NOTE_DIR / name, "WEBP", quality=90, method=6)


def scatter_clusters(ax, X, labels, centers, colors=PALETTE, s=8):
    for c in np.unique(labels):
        m = labels == c
        ax.scatter(X[m, 0], X[m, 1], s=s, alpha=0.6, color=colors[c % len(colors)])
    ax.scatter(centers[:, 0], centers[:, 1], s=90, marker="x", color=INK, linewidths=2)
    ax.set_aspect("equal")


# ---- 実験 0: 3 つの塊と、塊の無い一様乱数に k-means を掛ける ----
X, y = make_blobs(n_samples=300, centers=3, cluster_std=1.0, random_state=0)
rng = np.random.RandomState(0)
U = rng.uniform(X.min(axis=0), X.max(axis=0), size=X.shape)  # 同じ範囲に一様に散らばる 300 点

ks = list(range(2, 9))
scores = {}
for name, data in [("3 つの塊", X), ("一様乱数", U)]:
    rows = []
    for k in ks:
        km = KMeans(n_clusters=k, n_init=10, random_state=0).fit(data)
        rows.append((km.inertia_, silhouette_score(data, km.labels_),
                     davies_bouldin_score(data, km.labels_)))
    scores[name] = np.array(rows)
    print(name)
    print("k   イナーシャ  シルエット  Davies-Bouldin")
    for k, (ine, sil, db) in zip(ks, rows):
        print(f"{k}   {ine:8.1f}   {sil:8.3f}   {db:8.3f}")

fig, axes = plt.subplots(1, 2, figsize=(9, 3.9))
for ax, (title, data, k) in zip(axes, [("3 つの塊（k=3）", X, 3), ("塊の無い一様乱数（k=4）", U, 4)]):
    km = KMeans(n_clusters=k, n_init=10, random_state=0).fit(data)
    sil = silhouette_score(data, km.labels_)
    scatter_clusters(ax, data, km.labels_, km.cluster_centers_)
    ax.set_title(f"{title}\nシルエット係数 {sil:.3f}", fontsize=11)
    ax.set_xlabel("x1")
    ax.set_ylabel("x2")
save(fig, "kmeans_cover.webp")


# ---- 実験 1: 割り当てと更新を NumPy で書き、反復ごとの中心を残す ----
rng = np.random.RandomState(0)
X1 = rng.randn(100, 2) + np.array([0, 0])
X2 = rng.randn(100, 2) + np.array([3, 3])
X3 = rng.randn(100, 2) + np.array([0, 4])
Xh = np.vstack([X1, X2, X3])


def kmeans(X, k, max_iter=100, seed=0):
    # 1. 初期の中心を、データの点からランダムに k 個選ぶ
    rng = np.random.RandomState(seed)
    centers = X[rng.choice(len(X), k, replace=False)]
    history = [centers]

    for n_iter in range(1, max_iter + 1):
        # 2. 割り当て: 各点を最も近い中心の番号にする
        dists = np.linalg.norm(X[:, None, :] - centers[None, :, :], axis=2)
        labels = np.argmin(dists, axis=1)

        # 3. 更新: 割り当てられた点の平均を新しい中心にする
        new_centers = centers.copy()
        for i in range(k):
            members = X[labels == i]
            if len(members) > 0:
                new_centers[i] = members.mean(axis=0)
            else:
                # 0 件だと平均が NaN になるので、今の中心から最も遠い点へ移す
                far = np.argmax(dists[np.arange(len(X)), labels])
                new_centers[i] = X[far]

        # 4. 中心がほぼ動かなくなったら終了
        if np.allclose(centers, new_centers, atol=1e-4):
            break
        centers = new_centers
        history.append(centers)

    return labels, centers, history, n_iter


labels_h, centers_h, history, n_iter = kmeans(Xh, k=3)
print("反復回数:", n_iter)
print("初期の中心:", history[0].round(2).tolist())
print("最後の中心:", centers_h.round(2).tolist())
print("各クラスタの点数:", np.bincount(labels_h))

steps = [0, 1, 2, len(history) - 1]
fig, axes = plt.subplots(1, 4, figsize=(12, 3.4), sharex=True, sharey=True)
for ax, step in zip(axes, steps):
    c = history[step]
    d = np.linalg.norm(Xh[:, None, :] - c[None, :, :], axis=2)
    lab = np.argmin(d, axis=1)
    scatter_clusters(ax, Xh, lab, c, s=6)
    if step > 0:
        prev = history[step - 1]
        for p, q in zip(prev, c):
            ax.annotate("", xy=q, xytext=p, arrowprops=dict(arrowstyle="->", color=INK, lw=1))
    title = "初期の中心" if step == 0 else ("収束した中心" if step == steps[-1] else f"{step} 回目の更新")
    ax.set_title(title, fontsize=10)
    ax.set_xlabel("x1")
axes[0].set_ylabel("x2")
save(fig, "kmeans_steps.webp")

# 空のクラスタ: 同じ座標の 2 点を初期の中心に選ぶ
X_dup = np.array([[0.0, 0.0], [0.0, 0.0], [5.0, 5.0]])
c_dup = X_dup[[0, 1]]
d_dup = np.linalg.norm(X_dup[:, None, :] - c_dup[None, :, :], axis=2)
lab_dup = np.argmin(d_dup, axis=1)
print("同じ座標の中心での割り当て:", lab_dup)
print("番号 1 の点の平均:", X_dup[lab_dup == 1].mean(axis=0))  # 0 件の平均は [nan nan] と RuntimeWarning


# ---- 実験 2: k を選ぶ 3 つの指標を、3 つの塊と一様乱数で重ねる ----
fig, axes = plt.subplots(1, 3, figsize=(12, 3.4))
panels = [(0, "イナーシャ（減り方が鈍る所を選ぶ）"),
          (1, "シルエット係数（高いほど良い）"),
          (2, "Davies-Bouldin（低いほど良い）")]
for ax, (j, title) in zip(axes, panels):
    for name, color, best in [("3 つの塊", BLUE, 3), ("一様乱数", RED, 4)]:
        v = scores[name][:, j]
        ax.plot(ks, v, "o-", color=color, lw=2, ms=4, label=name)
        ax.plot([best], [v[ks.index(best)]], "o", ms=10, mfc="none", mec=color, mew=2)
    ax.set_title(title, fontsize=10)
    ax.set_xlabel("k")
    ax.set_xticks(ks)
axes[0].legend(frameon=False)
save(fig, "kmeans_indicators.webp")


# ---- 実験 2b: 一様乱数を散らす範囲の縦横比を変え、シルエット係数が選ぶ k を数える ----
for ratio in [1, 2, 3]:
    picked = []
    for s in range(20):
        Ur = np.random.RandomState(100 + s).uniform([0, 0], [ratio, 1], size=(300, 2))
        sil = [silhouette_score(Ur, KMeans(n_clusters=k, n_init=10, random_state=0).fit(Ur).labels_) for k in ks]
        picked.append(ks[int(np.argmax(sil))])
    print(f"横:縦 = {ratio}:1 で選ばれた k の回数:", dict(sorted(Counter(picked).items())))


# ---- 実験 3: 同じ範囲の一様乱数 20 組で、シルエット係数の最大値を測る ----
null_best = []
for s in range(20):
    r = np.random.RandomState(100 + s)
    Ur = r.uniform(X.min(axis=0), X.max(axis=0), size=X.shape)
    best = max(silhouette_score(Ur, KMeans(n_clusters=k, n_init=10, random_state=0).fit(Ur).labels_)
               for k in ks)
    null_best.append(best)
null_best = np.array(null_best)
real_best = scores["3 つの塊"][:, 1].max()
print("一様乱数 20 組のシルエット係数の最大値:", np.sort(null_best).round(3))
print(f"一様乱数の範囲 {null_best.min():.3f}〜{null_best.max():.3f}、3 つの塊 {real_best:.3f}")

fig, ax = plt.subplots(figsize=(7, 1.9))
jit = np.random.RandomState(0).uniform(-0.15, 0.15, len(null_best))
ax.scatter(null_best, jit, s=30, color=RED, alpha=0.7, label="一様乱数 20 組（k=2〜8 で最も高い値）")
ax.scatter([real_best], [0], s=120, marker="D", color=BLUE, label="3 つの塊のデータ（k=3）")
ax.axvline(0.5, color=GRAY, ls="--", lw=1)
ax.text(0.497, 0.27, "解説でよく見る目安の 0.5", color=GRAY, fontsize=9, ha="right")
ax.set_xlim(0.35, 0.55)
ax.set_ylim(-0.4, 0.4)
ax.set_yticks([])
ax.spines["left"].set_visible(False)
ax.set_xlabel("シルエット係数")
ax.legend(frameon=False, loc="upper left", bbox_to_anchor=(0, -0.45), ncol=2, fontsize=9)
save(fig, "kmeans_null.webp")


# ---- 実験 4: 離れた 16 個の塊で、n_init の既定と 10 回を比べる ----
grid = np.array([[i * 4.0, j * 4.0] for i in range(4) for j in range(4)])
Xg, yg = make_blobs(n_samples=1600, centers=grid, cluster_std=0.6, random_state=0)
ok_auto, ok_10, bad_seed = 0, 0, None
for s in range(100):
    lab_auto = KMeans(n_clusters=16, random_state=s).fit_predict(Xg)  # n_init は既定の "auto"
    lab_10 = KMeans(n_clusters=16, n_init=10, random_state=s).fit_predict(Xg)
    if adjusted_rand_score(yg, lab_auto) > 0.999:
        ok_auto += 1
    elif bad_seed is None:
        bad_seed = s
    ok_10 += adjusted_rand_score(yg, lab_10) > 0.999
print(f"16 個の塊を正しく分けた random_state: 既定 {ok_auto}/100、n_init=10 {ok_10}/100")
print("既定で失敗した最初の random_state:", bad_seed)

km_bad = KMeans(n_clusters=16, random_state=bad_seed).fit(Xg)
km_good = KMeans(n_clusters=16, n_init=10, random_state=bad_seed).fit(Xg)
print(f"random_state={bad_seed} のイナーシャ: 既定 {km_bad.inertia_:.1f}、n_init=10 {km_good.inertia_:.1f}")
fig, axes = plt.subplots(1, 2, figsize=(9, 4.2))
cols16 = [PALETTE[i % 8] for i in range(16)]
for ax, (title, km) in zip(axes, [(f"既定（初期化 1 回）、random_state={bad_seed}", km_bad),
                                  (f"n_init=10、random_state={bad_seed}", km_good)]):
    scatter_clusters(ax, Xg, km.labels_, km.cluster_centers_, colors=cols16, s=4)
    ax.set_title(f"{title}\nイナーシャ {km.inertia_:.1f}", fontsize=10)
    ax.set_xticks([])
    ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_visible(False)
save(fig, "kmeans_ninit.webp")


# ---- 実験 5: wine の 3 品種を、標準化の有無で k-means に分けさせる ----
wine = load_wine()
Xw, yw = wine.data, wine.target
fig, axes = plt.subplots(1, 2, figsize=(8, 3.2))
for ax, (title, data) in zip(axes, [("そのまま", Xw), ("標準化してから", StandardScaler().fit_transform(Xw))]):
    lab = KMeans(n_clusters=3, n_init=10, random_state=0).fit_predict(data)
    ari = adjusted_rand_score(yw, lab)
    tab = np.array([[np.sum((lab == c) & (yw == t)) for t in range(3)] for c in range(3)])
    tab = tab[np.argsort(tab.argmax(axis=1), kind="stable")]  # 多く含む品種の順にクラスタを並べる
    print(f"wine {title}: ARI {ari:.3f}")
    print(tab)
    ax.imshow(tab, cmap="Blues", vmin=0, vmax=70)
    for i in range(3):
        for j in range(3):
            ax.text(j, i, tab[i, j], ha="center", va="center",
                    color="#ffffff" if tab[i, j] > 40 else INK, fontsize=11)
    ax.set_xticks(range(3), [f"品種 {t}" for t in range(3)])
    ax.set_yticks(range(3), [f"クラスタ {c}" for c in range(3)])
    ax.set_title(f"{title}（ARI {ari:.2f}）", fontsize=10)
    for sp in ax.spines.values():
        sp.set_visible(False)
save(fig, "kmeans_wine.webp")


# ---- 実験 6: k-means が苦手な形を、混合ガウスモデルと比べる ----
Xb, yb = make_blobs(n_samples=600, random_state=170)
Xa = Xb @ np.array([[0.6, -0.6], [-0.4, 0.8]])  # 斜めに引き伸ばした塊
Xv, yv = make_blobs(n_samples=600, cluster_std=[1.0, 2.5, 0.5], random_state=170)  # 広がりの違う塊
Xu, yu = make_blobs(n_samples=[500, 30, 30], centers=[[0, 0], [4, 0], [4, 3]],
                    cluster_std=[1.5, 0.4, 0.4], random_state=0)  # 点の数の違う塊
cases = [("斜めに伸びた塊", Xa, yb), ("広がりの違う塊", Xv, yv), ("点の数の違う塊", Xu, yu)]
fig, axes = plt.subplots(2, 3, figsize=(12, 7.2))
for col, (title, data, truth) in enumerate(cases):
    Z = StandardScaler().fit_transform(data)
    km = KMeans(n_clusters=3, n_init=10, random_state=0).fit(Z)
    gm = GaussianMixture(n_components=3, random_state=0).fit(Z)
    lab_gm = gm.predict(Z)
    a_km, a_gm = adjusted_rand_score(truth, km.labels_), adjusted_rand_score(truth, lab_gm)
    print(f"{title}: k-means の ARI {a_km:.3f}、混合ガウスモデルの ARI {a_gm:.3f}")
    scatter_clusters(axes[0, col], Z, km.labels_, km.cluster_centers_, s=5)
    axes[0, col].set_title(f"{title}\nk-means（ARI {a_km:.2f}）", fontsize=10)
    scatter_clusters(axes[1, col], Z, lab_gm, gm.means_, s=5)
    axes[1, col].set_title(f"混合ガウスモデル（ARI {a_gm:.2f}）", fontsize=10)
    for r in range(2):
        axes[r, col].set_xticks([])
        axes[r, col].set_yticks([])
        for sp in axes[r, col].spines.values():
            sp.set_visible(False)
save(fig, "kmeans_shapes.webp")

print("Saved figures to:", NOTE_DIR)
