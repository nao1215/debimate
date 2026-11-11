"""knn ノートの実験と図を生成するスクリプト。

本文に載せた 5 つの実験（近傍の多数決、緯度と経度の単位、緯度と経度の重み、k の選び方、
近傍の検索の索引）を同じ順に実行し、出力を標準出力に、図を Page Bundle に WebP で保存する。
実行: cd projects/ml && .venv/bin/python scripts/notes/knn_gen.py
確認した版: scikit-learn 1.9.1、NumPy 2.5.4、matplotlib 3.11.2、PyNNDescent 0.7.0
California Housing は fetch_california_housing が初回だけ StatLib の配布元から取得し、
~/scikit_learn_data に保存したものを使う。検索の時間は CPU とスレッド数で変わるので、
全て 1 スレッドに絞って測る（著者の環境は AMD Ryzen AI Max+ 395）。
"""
import time
from io import BytesIO
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pynndescent
from PIL import Image
from sklearn.datasets import fetch_california_housing
from sklearn.model_selection import GroupKFold, KFold, cross_val_score
from sklearn.neighbors import KNeighborsClassifier, KNeighborsRegressor, NearestNeighbors
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import FunctionTransformer, StandardScaler
from threadpoolctl import threadpool_limits

NOTE_DIR = Path(__file__).resolve().parents[2] / "notes" / "ml" / "knn"
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10,
                     "axes.spines.top": False, "axes.spines.right": False})
BLUE, RED, GREEN, INK, GRAY, LIGHT = "#7aa6c2", "#e15759", "#59a14f", "#333333", "#999999", "#dddddd"


def save(fig, name):
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight", facecolor="#ffffff")
    plt.close(fig)
    buf.seek(0)
    Image.open(buf).convert("RGB").save(NOTE_DIR / name, "WEBP", quality=90, method=6)


# ---- 実験 1: 近傍の多数決。k で答えが変わる ----
rng = np.random.default_rng(0)
X_a = rng.standard_normal((30, 2)) + [0, 0]  # クラス A は (0, 0) の周り
X_b = rng.standard_normal((30, 2)) + [3, 3]  # クラス B は (3, 3) の周り
X_toy = np.vstack([X_a, X_b])
y_toy = np.array(["A"] * 30 + ["B"] * 30)
query = np.array([[1.5, 1.5]])

for k in (1, 5):
    clf = KNeighborsClassifier(n_neighbors=k).fit(X_toy, y_toy)
    dist, idx = clf.kneighbors(query)
    print(f"k={k}: 近い順のラベル {[str(c) for c in y_toy[idx[0]]]}、距離 {dist[0].round(3)}、予測 {clf.predict(query)[0]}")

fig, axes = plt.subplots(1, 2, figsize=(9, 4.2), sharey=True)
for ax, k in zip(axes, (1, 5)):
    clf = KNeighborsClassifier(n_neighbors=k).fit(X_toy, y_toy)
    dist, idx = clf.kneighbors(query)
    for i in idx[0]:
        ax.plot([query[0, 0], X_toy[i, 0]], [query[0, 1], X_toy[i, 1]], "--", color=GRAY, lw=1)
    ax.scatter(X_a[:, 0], X_a[:, 1], s=40, color=BLUE, edgecolor="white", label="クラス A")
    ax.scatter(X_b[:, 0], X_b[:, 1], s=40, color=RED, edgecolor="white", label="クラス B")
    ax.scatter(X_toy[idx[0], 0], X_toy[idx[0], 1], s=170, facecolor="none", edgecolor=INK, lw=1.2,
               label=f"近い {k} 点")
    ax.scatter(*query[0], marker="*", s=110, color=GREEN, edgecolor="black", zorder=4, label="予測したい点")
    votes = {c: int((y_toy[idx[0]] == c).sum()) for c in ("A", "B")}
    ax.set_title(f"k={k}：票は A {votes['A']}・B {votes['B']}、予測は {clf.predict(query)[0]}", fontsize=11)
    ax.set_xlabel("x1")
    ax.set_xlim(-1.5, 4.5)
    ax.set_ylim(-1.0, 4.5)
    ax.legend(loc="lower right", fontsize=8.5)
axes[0].set_ylabel("x2")
fig.tight_layout()
save(fig, "knn_concept.webp")


# ---- 実験 2: California Housing の緯度と経度の単位 ----
housing = fetch_california_housing()
Xh, yh = housing.data, housing.target
names = housing.feature_names
lat, lon = Xh[:, 6], Xh[:, 7]
print("列ごとの標準偏差:", dict(zip(names, Xh.std(axis=0).round(2))))


def latlon_scaled(X, meters_per_degree):
    # 緯度と経度の 2 列を、度から距離の単位に書き直す。経度 1 度の長さは緯度で変わるので、
    # データの中心の緯度（およそ 35.6 度）の cos を経度に掛ける。州の中では、この近似で足りる
    X = X.copy()
    lat0 = np.radians(X[:, 6].mean())
    X[:, 6] = X[:, 6] * meters_per_degree
    X[:, 7] = X[:, 7] * meters_per_degree * np.cos(lat0)
    return X


def km_between(i, j):
    # 2 つの区画の間の地表の距離（km）。半径 6371km の球とみなす
    p1, p2 = np.radians(lat[i]), np.radians(lat[j])
    dp, dl = p2 - p1, np.radians(lon[j] - lon[i])
    a = np.sin(dp / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * 6371 * np.arcsin(np.sqrt(a))


cv = KFold(n_splits=5, shuffle=True, random_state=0)
knn = KNeighborsRegressor()  # 既定は n_neighbors=5、距離はユークリッド距離
# (名前, kNN に渡す値, モデル, kNN が距離を測る値)。標準化だけは、モデルの中で値が変わる
cases = [("そのまま（度）", Xh, knn, Xh),
         ("緯度・経度を km に", latlon_scaled(Xh, 111.0), knn, latlon_scaled(Xh, 111.0)),  # 緯度 1 度はおよそ 111km
         ("標準化", Xh, make_pipeline(StandardScaler(), knn), StandardScaler().fit_transform(Xh)),
         ("緯度・経度を m に", latlon_scaled(Xh, 111_000.0), knn, latlon_scaled(Xh, 111_000.0))]
unit_results, search_data = {}, {}
for label, data, model, seen in cases:
    r2 = cross_val_score(model, data, yh, cv=cv).mean()
    # 全ての区画について、自分を除いた近傍 5 区画を探し、地表の距離と、所得・人口の差を測る
    _, idx = NearestNeighbors(n_neighbors=5).fit(seen).kneighbors()
    i, j = np.repeat(np.arange(len(yh)), 5), idx.ravel()
    km = np.median(km_between(i, j))
    inc = np.median(np.abs(Xh[i, 0] - Xh[j, 0]))  # MedInc（所得の中央値）の差
    pop = np.median(np.abs(Xh[i, 4] - Xh[j, 4]))  # Population（人口）の差
    unit_results[label] = (r2, km, inc)
    search_data[label] = seen
    print(f"{label}: R² {r2:.3f}、近傍 5 区画との差の中央値は 距離 {km:.1f}km・所得 {inc:.2f}・人口 {pop:.0f}")
Xk_nopop = np.delete(latlon_scaled(Xh, 111.0), 4, axis=1)  # km にした上で Population の列を外す
print(f"緯度・経度を km にし、人口を外す: R² {cross_val_score(knn, Xk_nopop, yh, cv=cv).mean():.3f}")

# 冒頭の図: 1 つの区画（index 0、Berkeley 付近）の近傍 5 区画を地図に置く
q = 0
print("区画 0:", {n: round(float(v), 2) for n, v in zip(names, Xh[q])})
for label in ("そのまま（度）", "標準化", "緯度・経度を m に"):
    nb = NearestNeighbors(n_neighbors=6).fit(search_data[label]).kneighbors(search_data[label][[q]])[1][0]
    nb = [i for i in nb if i != q][:5]
    print(f"  {label}: 近傍の人口 {Xh[nb, 4].astype(int).tolist()}、距離 {km_between(np.full(5, q), np.array(nb)).round(0).tolist()}km")

fig, axes = plt.subplots(1, 3, figsize=(11, 4.8))
for ax, label in zip(axes, ("そのまま（度）", "標準化", "緯度・経度を m に")):
    data = search_data[label]
    nb = NearestNeighbors(n_neighbors=6).fit(data).kneighbors(data[[q]])[1][0]
    nb = [i for i in nb if i != q][:5]
    ax.scatter(lon, lat, s=1, color=LIGHT, rasterized=True)
    for i in nb:
        ax.plot([lon[q], lon[i]], [lat[q], lat[i]], color=RED, lw=1, alpha=0.7)
    ax.scatter(lon[nb], lat[nb], s=36, color=RED, edgecolor="white", zorder=3, label="近傍 5 区画")
    ax.scatter(lon[q], lat[q], marker="*", s=260, color=GREEN, edgecolor="black", zorder=4, label="予測する区画")
    r2, med_km, _ = unit_results[label]
    ax.set_title(f"{label}\nR² {r2:.2f}、近傍までの距離の中央値 {med_km:.0f}km" if med_km >= 10
                 else f"{label}\nR² {r2:.2f}、近傍までの距離の中央値 {med_km:.1f}km", fontsize=10.5)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for side in ("left", "bottom"):
        ax.spines[side].set_visible(False)
    # 右上の空いた所に、予測する区画の周り（±0.15 度、およそ 30km 四方）を拡大して置く
    ins = ax.inset_axes([0.6, 0.5, 0.4, 0.4])
    box = (lon[q] - 0.15, lon[q] + 0.15, lat[q] - 0.15, lat[q] + 0.15)
    inside = (lon > box[0]) & (lon < box[1]) & (lat > box[2]) & (lat < box[3])
    ins.scatter(lon[inside], lat[inside], s=3, color=LIGHT, rasterized=True)
    for i in nb:
        ins.plot([lon[q], lon[i]], [lat[q], lat[i]], color=RED, lw=1, alpha=0.7)
    ins.scatter(lon[q], lat[q], marker="*", s=90, color=GREEN, edgecolor="black", zorder=3)
    ins.scatter(lon[nb], lat[nb], s=22, color=RED, edgecolor="white", zorder=4)
    ins.set_xlim(box[0], box[1])
    ins.set_ylim(box[2], box[3])
    ins.set_aspect("equal")
    ins.set_xticks([])
    ins.set_yticks([])
    for side in ("top", "right", "left", "bottom"):
        ins.spines[side].set_visible(True)
        ins.spines[side].set_color(GRAY)
    ins.text(0.5, -0.04, "星の周り 30km 四方を拡大", transform=ins.transAxes, ha="center", va="top", fontsize=8.5, color=INK)
axes[0].legend(loc="lower left", fontsize=8.5, frameon=False)
fig.tight_layout()
save(fig, "knn_cover.webp")

fig, axes = plt.subplots(1, 3, figsize=(12.5, 3.0))
labels = [c[0] for c in cases]
r2s = [unit_results[l][0] for l in labels]
kms = [unit_results[l][1] for l in labels]
ypos = np.arange(len(labels))[::-1]
axes[0].barh(ypos, r2s, color=[GRAY, GRAY, BLUE, RED])
for yp, v in zip(ypos, r2s):
    axes[0].text(v + 0.01, yp, f"{v:.3f}", va="center", fontsize=9)
axes[0].set_yticks(ypos, labels)
axes[0].set_xlim(0, 1)
axes[0].set_title("5 分割の R²", fontsize=10.5)
axes[1].barh(ypos, kms, color=[GRAY, GRAY, BLUE, RED])
for yp, v in zip(ypos, kms):
    axes[1].text(v * 1.15, yp, f"{v:.1f}km", va="center", fontsize=9)
axes[1].set_xscale("log")
axes[1].set_xlim(0.1, 3000)
axes[1].set_yticks(ypos, [""] * len(labels))
axes[1].set_title("近傍 5 区画までの距離の中央値（対数の軸）", fontsize=10.5)
incs = [unit_results[l][2] for l in labels]
axes[2].barh(ypos, incs, color=[GRAY, GRAY, BLUE, RED])
for yp, v in zip(ypos, incs):
    axes[2].text(v + 0.02, yp, f"{v:.2f}", va="center", fontsize=9)
axes[2].set_xlim(0, 1.5)
axes[2].set_yticks(ypos, [""] * len(labels))
axes[2].set_title("近傍 5 区画との所得の差の中央値", fontsize=10.5)
fig.tight_layout()
save(fig, "knn_units.webp")


# ---- 実験 3: 標準化した後に、緯度と経度へ掛ける重み ----
# 緯度と経度を 0.5 度ごとのマス目に切り、同じマスの区画を 1 つのグループにする
groups = np.floor(lat / 0.5).astype(int) * 1000 + np.floor(lon / 0.5).astype(int)
gcv = GroupKFold(n_splits=5)
weights = [0.25, 0.5, 1, 2, 4, 8, 16]
r2_shuffle, r2_group = [], []
for w in weights:
    col_w = np.array([1, 1, 1, 1, 1, 1, w, w])  # 緯度と経度の 2 列だけを w 倍して、距離の中で重く見る
    model = make_pipeline(StandardScaler(), FunctionTransformer(lambda Z, c=col_w: Z * c), knn)
    r2_shuffle.append(cross_val_score(model, Xh, yh, cv=cv).mean())
    r2_group.append(cross_val_score(model, Xh, yh, cv=gcv, groups=groups).mean())
    print(f"重み {w:5}: KFold(shuffle) の R² {r2_shuffle[-1]:.3f}、GroupKFold の R² {r2_group[-1]:.3f}")
Xm = latlon_scaled(Xh, 111_000.0)
print(f"緯度・経度を m に: GroupKFold の R² {cross_val_score(knn, Xm, yh, cv=gcv, groups=groups).mean():.3f}")

fig, ax = plt.subplots(figsize=(6.4, 3.6))
ax.plot(weights, r2_shuffle, "o-", color=RED, label="KFold(shuffle=True)：同じ地域の区画が学習側に残る")
ax.plot(weights, r2_group, "o-", color=BLUE, label="GroupKFold：0.5 度のマス目ごとに外す")
for w, a, b in zip(weights, r2_shuffle, r2_group):
    if w in (1, 16):
        ax.annotate(f"{a:.3f}", (w, a), textcoords="offset points", xytext=(0, 7), ha="center", fontsize=9, color=RED)
        ax.annotate(f"{b:.3f}", (w, b), textcoords="offset points", xytext=(0, -14), ha="center", fontsize=9, color=BLUE)
ax.set_xscale("log", base=2)
ax.set_xticks(weights, ["0.25", "0.5", "1", "2", "4", "8", "16"])
ax.set_xlabel("標準化した後、緯度と経度の 2 列に掛ける重み")
ax.set_ylabel("5 分割の R²")
ax.set_ylim(0.45, 0.9)
ax.legend(fontsize=8.5, loc="lower left", frameon=False)
fig.tight_layout()
save(fig, "knn_weight.webp")


# ---- 実験 4: k の選び方 ----
ks = [1, 2, 3, 5, 8, 12, 20, 30, 50, 80, 120, 200]
valid_r2 = []
for k in ks:
    model = make_pipeline(StandardScaler(), KNeighborsRegressor(n_neighbors=k))
    valid_r2.append(cross_val_score(model, Xh, yh, cv=cv).mean())
best = ks[int(np.argmax(valid_r2))]
print("5 分割の R²:", {k: round(float(v), 3) for k, v in zip(ks, valid_r2)})
print(f"最大は k={best}")

fig, ax = plt.subplots(figsize=(6.4, 3.6))
ax.plot(ks, valid_r2, "o-", color=BLUE)
ax.axvline(best, color=RED, ls=":", lw=1.2)
ax.text(best * 1.08, 0.715, f"最大は k={best} の {max(valid_r2):.3f}", color=RED, fontsize=9, va="bottom")
for k, dx, dy, ha in ((1, 6, -16, "left"), (5, 0, -48, "center"), (200, 6, -16, "left")):
    v = valid_r2[ks.index(k)]
    arrow = {"arrowstyle": "-", "color": GRAY, "lw": 0.8} if k == 5 else None
    ax.annotate(f"k={k}：{v:.3f}", (k, v), textcoords="offset points", xytext=(dx, dy), ha=ha, fontsize=9,
                arrowprops=arrow)
ax.set_xscale("log")
ax.set_xticks(ks, [str(k) for k in ks])
ax.set_xlabel("近傍の数 k（対数の軸）")
ax.set_ylabel("5 分割の R²")
ax.set_ylim(0.45, 0.75)
fig.tight_layout()
save(fig, "knn_k.webp")


# ---- 実験 5: 近傍の検索の索引 ----
rng = np.random.RandomState(0)
N, Q = 100_000, 1_000
dims = [2, 4, 8, 16, 32, 64]
timings = {"kd_tree": [], "ball_tree": [], "brute": []}
with threadpool_limits(1):  # 行列積も含め、全て 1 スレッドで比べる
    for d in dims:
        X = rng.randn(N, d)
        q = rng.randn(Q, d)
        for alg in timings:
            nn = NearestNeighbors(n_neighbors=5, algorithm=alg).fit(X)
            t = time.perf_counter()
            nn.kneighbors(q)
            timings[alg].append(time.perf_counter() - t)
        print(f"{d:2d} 次元: " + "、".join(f"{a} {timings[a][-1]:.3f} 秒" for a in timings))


def ann_recall(X, q, label):
    # 総当たりの答えを正解にして、PyNNDescent の近似が近傍 5 点のうち何点を当てたかを測る
    with threadpool_limits(1):
        nn = NearestNeighbors(n_neighbors=5, algorithm="brute").fit(X)
        t = time.perf_counter()
        _, truth = nn.kneighbors(q)
        brute_sec = time.perf_counter() - t
    index = pynndescent.NNDescent(X, n_neighbors=30, random_state=0, n_jobs=1)
    index.prepare()
    index.query(q[:10], k=5)  # 初回の呼び出しで JIT コンパイルが走るので、測る前に 1 回呼ぶ
    rows = []
    for eps in (0.0, 0.1, 0.2, 0.4):
        t = time.perf_counter()
        found, _ = index.query(q, k=5, epsilon=eps)
        sec = time.perf_counter() - t
        recall = np.mean([len(set(a) & set(b)) / 5 for a, b in zip(found, truth)])
        rows.append((eps, sec, recall))
        print(f"{label} epsilon={eps}: {sec:.3f} 秒、再現率 {recall:.3f}（総当たり {brute_sec:.3f} 秒）")
    return brute_sec, rows


X64 = rng.randn(N + Q, 64).astype(np.float32)  # 64 列が全て独立な乱数
X8in64 = (rng.randn(N + Q, 8) @ rng.randn(8, 64)).astype(np.float32)  # 中身は 8 次元、見かけは 64 列
ann = {"64 列が全て独立な乱数": ann_recall(X64[:N], X64[N:], "独立な 64 列"),
       "8 次元のデータを 64 列に写したもの": ann_recall(X8in64[:N], X8in64[N:], "中身は 8 次元")}

fig, axes = plt.subplots(1, 2, figsize=(11, 3.9))
ax = axes[0]
for alg, color, jp in (("kd_tree", RED, "kd_tree"), ("ball_tree", GREEN, "ball_tree"), ("brute", BLUE, "brute（総当たり）")):
    ax.plot(dims, timings[alg], "o-", color=color, label=jp)
ax.axvspan(15.5, 70, color="#f2f2f2", zorder=0)
ax.text(17, 60, "15 列を超えると\nauto は brute を選ぶ", fontsize=9, color=INK, va="top")
ax.text(2.2, 60, "auto は kd_tree を選ぶ", fontsize=9, color=INK, va="top")
ax.set_xscale("log", base=2)
ax.set_yscale("log")
ax.set_xticks(dims, [str(d) for d in dims])
ax.set_xlim(1.8, 70)
ax.set_ylim(0.001, 100)
ax.set_xlabel("列の数（次元）")
ax.set_ylabel("1,000 件の近傍を探す時間（秒）")
ax.set_title("10 万件から近傍 5 点を探す（独立な乱数、1 スレッド）", fontsize=10.5)
ax.legend(fontsize=9, frameon=False, loc="lower right")
ax = axes[1]
for (label, (brute_sec, rows)), color in zip(ann.items(), (RED, BLUE)):
    secs = [r[1] for r in rows]
    recs = [r[2] for r in rows]
    ax.plot(secs, recs, "o-", color=color, label=f"PyNNDescent：{label}")
    for eps, s, r in rows:
        # 青の線は点が詰まっているので、ラベルを上下左右に振り分ける
        dx, dy, ha = {0.1: (-7, 0, "right"), 0.2: (7, -9, "left"), 0.4: (0, 8, "center")}.get(eps, (7, -3, "left")) \
            if color == BLUE else (7, -3, "left")
        ax.annotate(f"ε={eps}", (s, r), textcoords="offset points", xytext=(dx, dy), ha=ha, fontsize=8, color=color)
for (label, (brute_sec, _)), color, side in zip(ann.items(), (RED, BLUE), ("right", "left")):
    ax.axvline(brute_sec, color=color, ls="--", lw=1)
    x = brute_sec * (0.94 if side == "right" else 1.06)
    ax.text(x, 0.05, f"総当たり\n{brute_sec:.2f} 秒", ha=side, fontsize=8.5, color=color)
ax.set_xscale("log")
ax.set_xlim(0.005, 2.0)
ax.set_ylim(0, 1.1)
ax.set_xlabel("1,000 件の近傍を探す時間（秒、対数の軸）")
ax.set_ylabel("再現率（正しい近傍 5 点のうち当てた割合）")
ax.set_title("64 列での近似の検索（ε は epsilon、1 スレッド）", fontsize=10.5)
ax.legend(fontsize=9, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=1)
fig.tight_layout()
fig.subplots_adjust(wspace=0.32)
save(fig, "knn_search.webp")
