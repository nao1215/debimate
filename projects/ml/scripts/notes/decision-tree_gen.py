"""decision-tree ノートの実験と図を生成するスクリプト。

本文に載せた実験（分け方の乱数と根の列、根の分割の選び方、Gini 不純度の減少、
深さと交差検証の正解率、make_moons での制限なしの木、Mauna Loa の CO2 での外挿、斜めの境界）を同じ順に実行し、
出力を標準出力に、図を Page Bundle に WebP で保存する。
実行: cd projects/ml && .venv/bin/python scripts/notes/decision-tree_gen.py
確認した版: scikit-learn 1.9.1、NumPy 2.5.4、matplotlib 3.11.2
CO2 のデータは OpenML（data_id=41187）から 1 回だけ取得し、scikit-learn のキャッシュを使う。
"""
from collections import Counter
from io import BytesIO
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from sklearn.datasets import fetch_openml, load_breast_cancer, make_moons
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor

NOTE_DIR = Path(__file__).resolve().parents[2] / "notes" / "ml" / "decision-tree"
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10,
                     "axes.spines.top": False, "axes.spines.right": False})
BLUE, RED, GREEN, INK, GRAY = "#7aa6c2", "#e15759", "#59a14f", "#333333", "#999999"
ORANGE, PURPLE = "#f28e2b", "#9c755f"


def save(fig, name):
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight", facecolor="#ffffff")
    plt.close(fig)
    buf.seek(0)
    Image.open(buf).convert("RGB").save(NOTE_DIR / name, "WEBP", quality=90, method=6)


# ============================================================
# 実験 1: train_test_split の乱数を変えて、深さ 3 の木を 100 本作る
# ============================================================
data = load_breast_cancer()
X, y = data.data, data.target                     # 569 行 × 30 列、0 が悪性・1 が良性
names = np.array(data.feature_names)

roots, accs, used = [], [], []
preds = []
for seed in range(100):
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.3, random_state=seed, stratify=y)
    tree = DecisionTreeClassifier(max_depth=3, random_state=0).fit(X_tr, y_tr)   # 木の中の乱数は固定
    f = tree.tree_.feature
    roots.append(str(names[f[0]]))                # 根の質問に使った列
    used.append(frozenset(names[f[f >= 0]]))      # 木の中で使った列の組
    accs.append(tree.score(X_te, y_te))           # テスト 171 行の正解率
    preds.append(tree.predict(X))                 # 全 569 行への予測
print("根に選ばれた列:", Counter(roots).most_common())
print("使った列の組の種類:", len(set(used)), "/ 100")
same_root_sets = {u for u, r in zip(used, roots) if r == "worst perimeter"}
print("根が worst perimeter の", roots.count("worst perimeter"), "本で、使った列の組の種類:", len(same_root_sets))
print("テストの正解率 最小・中央値・最大:", np.round([min(accs), np.median(accs), max(accs)], 3))
P = np.array(preds)
disagree = [(P[i] != P[j]).mean() for i in range(100) for j in range(i + 1, 100)]
print(f"2 本の木で答えが違う行の割合の平均: {np.mean(disagree):.3f}")

root_counts = Counter(roots).most_common()
order = [r for r, _ in root_counts]
colors = dict(zip(order, [RED, BLUE, GREEN, ORANGE, PURPLE]))
fig, axes = plt.subplots(1, 2, figsize=(10.5, 3.9), gridspec_kw={"width_ratios": [1.05, 1]})
ax = axes[0]
ax.barh(range(len(order))[::-1], [c for _, c in root_counts], color=[colors[r] for r in order])
for i, (r, c) in enumerate(root_counts):
    ax.text(c + 1, len(order) - 1 - i, f"{c} 回", va="center", fontsize=9)
ax.set_yticks(range(len(order))[::-1], order)
ax.set_xlim(0, 58)
ax.set_xlabel("根の質問に選ばれた回数（100 本中）")
ax.set_title("根の質問に使われた列", fontsize=10)
ax = axes[1]
rng_j = np.random.default_rng(1)
for i, r in enumerate(order):
    a = np.array([acc for acc, rr in zip(accs, roots) if rr == r])
    ax.scatter(a, len(order) - 1 - i + rng_j.uniform(-0.18, 0.18, len(a)), s=16,
               color=colors[r], alpha=0.8)
    ax.plot([np.median(a)] * 2, [len(order) - 1 - i - 0.3, len(order) - 1 - i + 0.3], color=INK, lw=1.5)
ax.set_yticks(range(len(order))[::-1], order)
ax.set_xlabel("テスト 171 行の正解率（黒い縦線は中央値）")
ax.set_title("根にした列とテストの正解率", fontsize=10)
ax.grid(True, axis="x", alpha=0.3)
fig.suptitle("breast_cancer で train_test_split の乱数だけを 0〜99 に変えて学習した、深さ 3 の決定木 100 本",
             fontsize=10.5)
fig.tight_layout()
save(fig, "dt_cover.webp")


# ============================================================
# 実験 2: 全 569 行で根の分割を選ぶ（Gini 不純度の減少）
# ============================================================
def gini(labels):
    p = np.bincount(labels, minlength=2) / len(labels)
    return 1 - np.sum(p ** 2)


root = DecisionTreeClassifier(max_depth=2, random_state=0).fit(X, y)
t = root.tree_
print("全行の Gini:", round(gini(y), 3), " 悪性・良性:", np.bincount(y))
for node in range(t.node_count):
    if t.feature[node] >= 0:
        print(f"ノード {node}: {names[t.feature[node]]} <= {t.threshold[node]:.3f}  行数 {t.n_node_samples[node]}")


def gain_curve(x, labels):
    """x の値で並べ、左の行数ごとに Gini 不純度の減少（親 - 子の重み付き平均）を返す。"""
    o = np.argsort(x, kind="stable")
    xs, ys = x[o], labels[o]
    n = len(ys)
    left_pos = np.cumsum(ys)[:-1]
    nl = np.arange(1, n)
    nr = n - nl
    pl = left_pos / nl
    pr = (ys.sum() - left_pos) / nr
    # 2 クラスでは 1 - (p^2 + (1-p)^2) = 2p(1-p) なので、gini() と同じ値になる
    child = (nl * 2 * pl * (1 - pl) + nr * 2 * pr * (1 - pr)) / n
    gain = gini(labels) - child
    gain[xs[1:] == xs[:-1]] = np.nan              # 同じ値の間では切れない
    return nl / n, gain, (xs[:-1] + xs[1:]) / 2


best = []
for j in range(X.shape[1]):
    frac, g, thr = gain_curve(X[:, j], y)
    k = np.nanargmax(g)
    best.append((g[k], names[j], thr[k]))
best.sort(reverse=True)
for g, n_, thr in best[:6]:
    print(f"{n_:<22} 閾値 {thr:9.3f}  Gini の減少 {g:.4f}")

# 分け方を変えた時、学習用の行で 1 位と 2 位の列の差がどれだけあるか
top5 = [n_ for _, n_, _ in best[:5]]
gaps, same = [], 0
for seed in range(100):
    X_tr, _, y_tr, _ = train_test_split(X, y, test_size=0.3, random_state=seed, stratify=y)
    g = np.array([np.nanmax(gain_curve(X_tr[:, j], y_tr)[1]) for j in range(X.shape[1])])
    first, second = np.argsort(g, kind="stable")[::-1][:2]
    gaps.append(g[first] - g[second])
    same += names[first] == roots[seed]
gaps = np.array(gaps)
print("学習 398 行で減少が 1 位の列が、木の根と同じ:", same, "/ 100")
print(f"1 位と 2 位の差 中央値 {np.median(gaps):.4f}  0.01 未満 {(gaps < 0.01).sum()} / 100  最大 {gaps.max():.4f}")
# 不純度の測り方を変えた時と、RandomForest・ロジスティック回帰の時の「1 位の列」
top_entropy, top_forest, top_logreg = [], [], []
same_root, ent_accs = 0, []
for seed in range(100):
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.3, random_state=seed, stratify=y)
    ent = DecisionTreeClassifier(max_depth=3, criterion="entropy", random_state=0).fit(X_tr, y_tr)
    top_entropy.append(str(names[ent.tree_.feature[0]]))
    same_root += top_entropy[-1] == roots[seed]
    ent_accs.append(ent.score(X_te, y_te))
    forest = RandomForestClassifier(n_estimators=200, random_state=0).fit(X_tr, y_tr)
    top_forest.append(str(names[np.argmax(forest.feature_importances_)]))
    logreg = make_pipeline(StandardScaler(), LogisticRegression(max_iter=5000)).fit(X_tr, y_tr)
    top_logreg.append(str(names[np.argmax(np.abs(logreg[-1].coef_[0]))]))
print("entropy の根:", Counter(top_entropy).most_common(), " Gini と同じ根:", same_root, "/ 100")
print("テストの正解率の中央値 Gini:", round(np.median(accs), 3), " entropy:", round(np.median(ent_accs), 3))
print("RandomForest の重要度 1 位:", Counter(top_forest).most_common())
print("ロジスティック回帰の係数の絶対値 1 位:", Counter(top_logreg).most_common())

cols = [int(np.where(names == n_)[0][0]) for n_ in top5]
corr = np.corrcoef(X[:, cols], rowvar=False)
i, j = np.triu_indices(5, k=1)                     # 2 列を選ぶ 10 組
print("上位 5 列の相関係数 10 組の最小:", round(corr[i, j].min(), 3))

fig, axes = plt.subplots(1, 2, figsize=(10.5, 3.8), gridspec_kw={"width_ratios": [1.35, 1]})
ax = axes[0]
for n_ in top5 + [best[5][1]]:
    j = int(np.where(names == n_)[0][0])
    frac, g, _ = gain_curve(X[:, j], y)
    c = colors.get(n_, GRAY)
    ok = ~np.isnan(g)                                 # 同じ値の間（NaN）を飛ばして線をつなぐ
    ax.plot(frac[ok], g[ok], color=c, lw=1.4 if n_ in colors else 1.2, label=n_,
            ls="-" if n_ in colors else ":")
ax.set_xlabel("左の子に入る行の割合（列の値が小さい側）")
ax.set_ylabel("Gini 不純度の減少")
ax.set_ylim(0, 0.46)
ax.set_yticks([0, 0.1, 0.2, 0.3])
ax.legend(fontsize=8, loc="upper center", ncol=3, columnspacing=1.0, handlelength=1.6)
ax.set_title("全 569 行で、閾値の位置ごとの Gini 不純度の減少", fontsize=10)
ax.grid(True, alpha=0.3)
ax = axes[1]
ax.hist(gaps, bins=np.arange(0, 0.0285, 0.002), color=BLUE, edgecolor="#ffffff")
ax.axvline(np.median(gaps), color=INK, lw=1.2)
ax.text(np.median(gaps) + 0.0006, ax.get_ylim()[1] * 0.92, f"中央値 {np.median(gaps):.4f}", fontsize=9)
ax.set_xlabel("学習 398 行での、1 位と 2 位の列の減少の差")
ax.set_ylabel("回数（100 回中）")
ax.set_title("分け方を変えた 100 回で、1 位と 2 位の差", fontsize=10)
ax.grid(True, axis="y", alpha=0.3)
fig.tight_layout()
save(fig, "dt_gain.webp")


# 深さ 2 の木を、ノードごとの行数と不純度を入れて描く
def draw_tree(ax, t):
    pos = {0: (0.5, 0.86), 1: (0.25, 0.5), 4: (0.75, 0.5), 2: (0.12, 0.13), 3: (0.38, 0.13),
           5: (0.62, 0.13), 6: (0.88, 0.13)}
    for node, (px, py) in pos.items():
        left, right = t.children_left[node], t.children_right[node]
        for child, word in [(left, "はい"), (right, "いいえ")]:
            if child >= 0:
                cx, cy = pos[child]
                ax.plot([px, cx], [py - 0.07, cy + 0.08], color=GRAY, lw=1)
                ax.text((px + cx) / 2 + (-0.03 if child == left else 0.03), (py + cy) / 2,
                        word, ha="center", fontsize=8.5, color=INK)
        counts = (t.value[node][0] * t.n_node_samples[node]).round().astype(int)
        mal, ben = counts
        is_leaf = left < 0
        text = (f"{mal} : {ben}\nGini {t.impurity[node]:.3f}" if is_leaf else
                f"{names[t.feature[node]]} ≤ {t.threshold[node]:.3g}\n{mal} : {ben}  Gini {t.impurity[node]:.3f}")
        face = "#fbe3e3" if mal > ben else "#e3eef5"
        ax.text(px, py, text, ha="center", va="center", fontsize=9,
                bbox=dict(boxstyle="round,pad=0.45", fc=face, ec=GRAY))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")


fig, ax = plt.subplots(figsize=(9.5, 3.9))
draw_tree(ax, t)
ax.set_title("全 569 行で学習した深さ 2 の決定木（各箱の数は 悪性 : 良性 の行数。赤は悪性の方が多い箱）", fontsize=10)
save(fig, "dt_tree.webp")


# ============================================================
# 実験 3: 深さと交差検証の正解率
# ============================================================
depths = list(range(1, 13))
cv_mean, cv_std, train_acc, leaves = [], [], [], []
for d in depths + [None]:
    m = DecisionTreeClassifier(max_depth=d, random_state=0)
    s = cross_val_score(m, X, y, cv=5)
    m.fit(X, y)
    cv_mean.append(s.mean())
    cv_std.append(s.std())
    train_acc.append(m.score(X, y))
    leaves.append(m.get_n_leaves())
    print(f"max_depth={str(d):<4} 交差検証 {s.mean():.3f}（±{s.std():.3f}）  学習データ {m.score(X, y):.3f}"
          f"  葉 {m.get_n_leaves()}  根 {names[m.tree_.feature[0]]}")

# ノイズの少ない三日月型のデータでは、制限なしの木が一番良いこともある
X_m, y_m = make_moons(n_samples=300, noise=0.15, random_state=0)
for d in [2, 5, None]:
    m = DecisionTreeClassifier(max_depth=d, random_state=0)
    s = cross_val_score(m, X_m, y_m, cv=5)
    m.fit(X_m, y_m)
    print(f"make_moons max_depth={str(d):<4} 交差検証 {s.mean():.3f}（±{s.std():.3f}）"
          f"  学習データ {m.score(X_m, y_m):.3f}  葉 {m.get_n_leaves()}")

fig, axes = plt.subplots(1, 2, figsize=(10.5, 3.6))
xs = depths + [13]
xl = [str(d) for d in depths] + ["None"]
ax = axes[0]
ax.plot(xs, train_acc, color=GRAY, marker="o", ms=4, label="学習に使った 569 行の正解率")
ax.errorbar(xs, cv_mean, yerr=cv_std, color=RED, marker="o", ms=4, capsize=2, label="5 分割の交差検証の正解率")
ax.set_xticks(xs, xl)
ax.set_xlabel("max_depth（None は既定の制限なし）")
ax.set_ylim(0.85, 1.01)
ax.legend(fontsize=8.5, loc="lower right")
ax.set_title("深さと正解率", fontsize=10)
ax.grid(True, alpha=0.3)
ax = axes[1]
ax.bar(xs, leaves, color=BLUE)
for x_, l_ in zip(xs, leaves):
    ax.text(x_, l_ + 0.4, str(l_), ha="center", fontsize=8)
ax.set_xticks(xs, xl)
ax.set_xlabel("max_depth（None は既定の制限なし）")
ax.set_ylabel("葉の数")
ax.set_title("深さと葉の数", fontsize=10)
fig.tight_layout()
save(fig, "dt_depth.webp")


# ============================================================
# 実験 4: Mauna Loa の CO2 で、学習した期間の外を予測する
# ============================================================
co2 = fetch_openml(data_id=41187, as_frame=True).frame
year = (co2.year + (co2.month - 1) / 12 + (co2.day - 1) / 365).to_numpy()
ppm = co2.co2.to_numpy()
train = year < 1991                                  # 1958〜1990 年で学習、1991〜2001 年を予測
T = year.reshape(-1, 1)
models = {
    "決定木（max_depth=6）": DecisionTreeRegressor(max_depth=6, random_state=0),
    "RandomForest": RandomForestRegressor(n_estimators=200, random_state=0),
    "HistGradientBoosting": HistGradientBoostingRegressor(random_state=0),
    "線形回帰": LinearRegression(),
}
pred = {}
for label, m in models.items():
    m.fit(T[train], ppm[train])
    pred[label] = m.predict(T)
    p = pred[label][~train]
    print(f"{label:<22} 1991 年以降の平均絶対誤差 {np.abs(p - ppm[~train]).mean():5.2f} ppm"
          f"  予測の範囲 {p.min():.1f}〜{p.max():.1f}")
print(f"学習 {train.sum()} 週、予測 {(~train).sum()} 週。1991 年以降の実測 {ppm[~train].min():.1f}〜{ppm[~train].max():.1f}")

fig, ax = plt.subplots(figsize=(10, 4))
ax.plot(year, ppm, color=GRAY, lw=0.8, label="実測（週ごと）")
style = {"決定木（max_depth=6）": (RED, "-"), "RandomForest": (ORANGE, "--"),
         "HistGradientBoosting": (PURPLE, ":"), "線形回帰": (BLUE, "-")}
for label, p in pred.items():
    c, ls = style[label]
    ax.plot(year, p, color=c, ls=ls, lw=1.6, label=label)
ax.axvspan(1991, year.max(), color="#f2f2f2", zorder=0)
ax.text(1996, 318, "学習に使っていない期間", ha="center", fontsize=9, color=INK)
ax.set_xlabel("年")
ax.set_ylabel("CO2 濃度（ppm）")
ax.legend(fontsize=8.5, loc="upper left")
ax.set_title("Mauna Loa の CO2 濃度を、年だけを入力にして予測する（1990 年までで学習）", fontsize=10)
ax.grid(True, alpha=0.3)
fig.tight_layout()
save(fig, "dt_co2.webp")


# ============================================================
# 実験 5: 同じ点を、境界が軸に沿う向きと 45 度の向きでラベル付けする
# ============================================================
rng = np.random.default_rng(0)
Z = rng.uniform(-1, 1, (400, 2))
fits = {}
for deg in [0, 45]:
    w = np.array([np.cos(np.radians(deg)), np.sin(np.radians(deg))])
    label = (Z @ w > 0).astype(int)                  # 境界は w に直交する直線
    tree = DecisionTreeClassifier(random_state=0)
    logreg = LogisticRegression()
    print(f"{deg:>2} 度: 決定木 交差検証 {cross_val_score(tree, Z, label, cv=5).mean():.3f}"
          f"  葉 {tree.fit(Z, label).get_n_leaves()}"
          f"  ロジスティック回帰 交差検証 {cross_val_score(logreg, Z, label, cv=5).mean():.3f}")
    fits[deg] = (label, tree, logreg.fit(Z, label))

gx, gy = np.meshgrid(np.linspace(-1, 1, 300), np.linspace(-1, 1, 300))
grid = np.column_stack([gx.ravel(), gy.ravel()])
fig, axes = plt.subplots(1, 3, figsize=(11, 3.8))
panels = [(0, "tree", "境界が縦の直線: 決定木"), (45, "tree", "境界が 45 度: 決定木"),
          (45, "logreg", "境界が 45 度: ロジスティック回帰")]
for ax, (deg, kind, title) in zip(axes, panels):
    label, tree, logreg = fits[deg]
    m = tree if kind == "tree" else logreg
    ax.contourf(gx, gy, m.predict(grid).reshape(gx.shape), levels=[-0.5, 0.5, 1.5],
                colors=["#fbe3e3", "#e3eef5"])
    ax.scatter(Z[:, 0], Z[:, 1], c=np.where(label == 1, BLUE, RED), s=7)
    extra = f"（葉 {tree.get_n_leaves()}）" if kind == "tree" else ""
    ax.set_title(title + extra, fontsize=10)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
fig.tight_layout()
save(fig, "dt_rotate.webp")
