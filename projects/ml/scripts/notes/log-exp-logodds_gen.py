"""log-exp-logodds ノートの実験と図を生成するスクリプト。

本文に載せた 4 つの実験（digits の Naive Bayes で確率を掛ける、softmax の桁あふれ、
log1p と 2 値の交差エントロピー、ロジスティック回帰の係数と確率の変化）を同じ順に実行し、
出力を標準出力に、図を Page Bundle に WebP で保存する。
実行: cd projects/ml && .venv/bin/python scripts/notes/log-exp-logodds_gen.py
確認した版: scikit-learn 1.9.1、NumPy 2.5.4、SciPy 1.18.1、matplotlib 3.11.2
"""
import warnings
from io import BytesIO
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from scipy.special import logsumexp, softmax
from sklearn.datasets import load_breast_cancer, load_digits
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import MultinomialNB
from sklearn.preprocessing import StandardScaler

warnings.simplefilter("ignore", RuntimeWarning)  # 0 の log や exp の桁あふれの警告は、結果で見せる

NOTE_DIR = Path(__file__).resolve().parents[2] / "notes" / "math" / "log-exp-logodds"
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10,
                     "axes.spines.top": False, "axes.spines.right": False})
BLUE, RED, GREEN, INK, GRAY = "#7aa6c2", "#e15759", "#59a14f", "#333333", "#999999"


def save(fig, name):
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight", facecolor="#ffffff")
    plt.close(fig)
    buf.seek(0)
    Image.open(buf).convert("RGB").save(NOTE_DIR / name, "WEBP", quality=90, method=6)


# ---- 図: log と exp のグラフ ----
fig, axes = plt.subplots(1, 2, figsize=(10, 4))
x_pos = np.linspace(0.05, 4, 200)
ax = axes[0]
ax.plot(x_pos, np.log(x_pos), color=BLUE, lw=2, label="log(x)（自然対数）")
ax.plot(x_pos, np.log2(x_pos), color=RED, lw=1.5, ls="--", label="log2(x)")
ax.plot(x_pos, np.log10(x_pos), color=GREEN, lw=1.5, ls=":", label="log10(x)")
ax.axhline(0, color=GRAY, lw=0.6)
ax.scatter([1], [0], color=INK, zorder=5)
ax.annotate("どの底でも log(1) = 0", (1, 0), xytext=(1.6, -1.6), fontsize=9,
            arrowprops=dict(arrowstyle="->", color=INK))
ax.set_title("底だけが違う 3 つの対数", fontsize=10)
ax.set_xlabel("x")
ax.set_ylim(-3.5, 2.5)
ax.legend(fontsize=9)
ax.grid(True, alpha=0.25)
ax = axes[1]
x_all = np.linspace(-3, 2.2, 200)
xs = np.linspace(0.05, np.exp(2.2), 200)
ax.plot(x_all, np.exp(x_all), color=BLUE, lw=2, label="exp(x)")
ax.plot(xs, np.log(xs), color=RED, lw=2, label="log(x)")
ax.plot([-3, 9], [-3, 9], color=GRAY, lw=1, ls=":", label="y = x")
ax.set_title("exp と log は y = x を挟んで鏡に映した形", fontsize=10)
ax.set_xlabel("x")
ax.set_xlim(-3, 9)
ax.set_ylim(-3, 9)
ax.set_aspect("equal", adjustable="box")
ax.legend(fontsize=9, loc="upper left")
ax.grid(True, alpha=0.25)
fig.tight_layout()
save(fig, "le_curves.webp")

# ---- 実験 1: digits の Naive Bayes で、確率を掛けるか log を足すか ----
X, y = load_digits(return_X_y=True)
X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.3, random_state=0, stratify=y)
nb = MultinomialNB().fit(X_tr, y_tr)
prior = np.exp(nb.class_log_prior_)   # P(数字)、10 個
theta = np.exp(nb.feature_log_prob_)  # P(画素 | 数字)、10 × 64


def predict_product(X, k, dtype=np.float64):
    """先頭の k 画素について、確率をそのまま掛けて一番大きい数字を選ぶ"""
    score = np.tile(prior.astype(dtype), (len(X), 1))
    for j in range(k):
        score = score * theta[:, j].astype(dtype) ** X[:, j:j + 1].astype(dtype)
    return score.argmax(axis=1), (score.max(axis=1) == 0).mean()


def predict_log(X, k):
    """同じ計算を log の和で行う"""
    score = nb.class_log_prior_ + X[:, :k] @ nb.feature_log_prob_[:, :k].T
    return score.argmax(axis=1), score.max(axis=1)


ink = X_te.sum(axis=1)
print(f"1 枚のインクの合計: 最小 {ink.min():.0f}、中央値 {np.median(ink):.0f}、最大 {ink.max():.0f}")
print(f"P(画素 | 数字) の中央値 {np.median(theta):.4f}（1/64 = {1 / 64:.4f}）")
pred_prod, zero_share = predict_product(X_te, 64)
pred_log, best_log = predict_log(X_te, 64)
print(f"確率を掛ける: 正解率 {(pred_prod == y_te).mean():.3f}、10 個とも 0.0 の画像 {zero_share:.1%}")
print(f"log を足す:   正解率 {(pred_log == y_te).mean():.3f}（MultinomialNB.score は {nb.score(X_te, y_te):.3f}）")
print("「0」と答えた割合:", f"{(pred_prod == 0).mean():.3f}", " テストに占める「0」の割合:", f"{(y_te == 0).mean():.3f}")
print("一番大きい log の和: 最大", best_log.max().round(1), " 中央値", np.median(best_log).round(1))
for dtype in [np.float64, np.float32]:
    smallest = np.nextafter(dtype(0), dtype(1))  # 0 より大きい最小の数
    print(f"{dtype.__name__}: 0 より大きい最小の数 {smallest:.3g}、その log {np.log(np.float64(smallest)):.1f}")
pred32, zero32 = predict_product(X_te, 64, np.float32)
print(f"float32 で掛ける: 正解率 {(pred32 == y_te).mean():.3f}、10 個とも 0.0 の画像 {zero32:.1%}")

ks = np.arange(1, 65)
acc_prod, acc_log, zeros = [], [], []
for k in ks:
    pp, zs = predict_product(X_te, k)
    pl, _ = predict_log(X_te, k)
    acc_prod.append((pp == y_te).mean())
    acc_log.append((pl == y_te).mean())
    zeros.append(zs)
for k in [16, 32, 40, 48, 64]:
    print(f"画素 {k:2d} 個: 掛ける {acc_prod[k - 1]:.3f}、足す {acc_log[k - 1]:.3f}、0.0 の画像 {zeros[k - 1]:.1%}")

fig, ax = plt.subplots(figsize=(8, 4.2))
ax.bar(ks, zeros, color="#dddddd", width=1.0, label="10 個の確率が全て 0.0 になった画像の割合")
ax.plot(ks, acc_log, color=BLUE, lw=2.2, label="log の和で比べる")
ax.plot(ks, acc_prod, color=RED, lw=2.2, ls="--", label="確率をそのまま掛けて比べる")
ax.text(64.5, acc_log[-1], f"{acc_log[-1]:.1%}", color=BLUE, va="center", fontsize=10)
ax.text(64.5, acc_prod[-1], f"{acc_prod[-1]:.1%}", color=RED, va="center", fontsize=10)
ax.axhline((y_te == 0).mean(), color=GRAY, lw=0.8, ls=":")
ax.text(1, 0.035, "点線: 全て「0」と答えた時の正解率", color=GRAY, fontsize=8)
ax.set_xlabel("計算に使った画素の数（左上から順に）")
ax.set_ylabel("テストの正解率")
ax.set_xlim(0, 70)
ax.set_ylim(0, 1)
ax.set_title("digits の Naive Bayes: 確率を掛けると、画素を増やした途中から正解率が下がる", fontsize=10, loc="left")
ax.legend(fontsize=9, loc="upper left", frameon=False)
fig.tight_layout()
save(fig, "le_cover.webp")

# ---- 実験 2: softmax の桁あふれ ----


def softmax_naive(z):
    e = np.exp(z)
    return e / e.sum()


z = np.array([2.0, 1.0, 0.0])
shifts = np.arange(-1200, 1201)
valid = {}
for dtype in [np.float32, np.float64]:
    ok = np.array([np.isfinite(softmax_naive((z + c).astype(dtype))).all() for c in shifts])
    valid[dtype.__name__] = (shifts[ok].min(), shifts[ok].max())
    print(f"{dtype.__name__}: 素朴な softmax が数を返す c の範囲 {shifts[ok].min()}〜{shifts[ok].max()}")
print("c = 0:", softmax_naive(z).round(4), " c = 88（float32）:", softmax_naive((z + 88).astype(np.float32)))
print("c = 88 で最大値を引く版:", softmax((z + 88).astype(np.float32)).round(4))
a = np.array([-1000.0, -1001.0, -1002.0])  # log p_k
print("確率に戻してから足す:", np.log(np.sum(np.exp(a))))
m = a.max()
print("最大値を括り出す:", m + np.log(np.sum(np.exp(a - m))), " logsumexp:", logsumexp(a))
print("softmax:", np.exp(a - logsumexp(a)))
logits = np.array([12.0, 11.0, 9.5, 7.0], dtype=np.float32)
for T in [1.0, 0.2, 0.13]:
    t = np.float32(T)
    print(f"temperature {T}: 素朴 {softmax_naive(logits / t).round(4)}、最大値を引く {softmax(logits / t).round(4)}")

fig, ax = plt.subplots(figsize=(8, 3.4))
rows = [("最大値を引く softmax", (-1200, 1200), BLUE),
        ("素朴な softmax（float64）", valid["float64"], GRAY),
        ("素朴な softmax（float32）", valid["float32"], RED)]
for i, (label, (lo, hi), color) in enumerate(rows):
    ax.barh(i, 2400, left=-1200, color="#f3d6d6" if i else "#e6eef4", height=0.55)
    ax.barh(i, hi - lo, left=lo, color=color, height=0.55)
    if not i:
        ax.text(0, i, "-1200〜1200 の全てで正しい答え", ha="center", va="center", fontsize=9, color="#ffffff")
    if i:
        ax.text(lo - 15, i, f"{lo}", ha="right", va="center", fontsize=9)
        ax.text(hi + 15, i, f"{hi}", ha="left", va="center", fontsize=9)
        ax.text(1150, i, "nan", ha="right", va="center", fontsize=9, color=RED)
        ax.text(-1150, i, "nan", ha="left", va="center", fontsize=9, color=RED)
ax.set_yticks(range(3))
ax.set_yticklabels([r[0] for r in rows])
ax.set_xlabel("ロジット [2, 1, 0] の全てに足した値 c")
ax.set_xlim(-1200, 1200)
ax.set_title("同じ c を足しても答えは [0.665, 0.245, 0.090] のはず。濃い帯が、その答えを返した範囲", fontsize=10, loc="left")
fig.tight_layout()
save(fig, "le_softmax.webp")

# ---- 実験 3: log1p と 2 値の交差エントロピー ----
for x in [1e-4, 1e-8, 1e-12, 1e-16]:
    naive, exact = np.log(1 + x), np.log1p(x)
    print(f"x = {x:g}: log(1 + x) = {naive:.6e}、log1p(x) = {exact:.6e}、相対誤差 {abs(naive - exact) / exact:.1e}")
zs64 = np.arange(0, 60, 0.01)
first_inf = {}
for dtype in [np.float32, np.float64]:
    zz = zs64.astype(dtype)
    p = 1 / (1 + np.exp(-zz))     # sigmoid で確率にしてから
    loss = -np.log(1 - p)         # 正解が 0 の時の交差エントロピー
    first_inf[dtype.__name__] = float(zz[np.isinf(loss)][0])
    print(f"{dtype.__name__}: 確率にしてから log を取ると、z = {first_inf[dtype.__name__]:.2f} で inf")
p40 = 1 / (1 + np.exp(-40.0))
print("z = 40: p =", p40, " 確率から log1p で計算:", -np.log1p(-p40))
print("z = 40 をロジットのまま計算:", np.logaddexp(0, 40.0), " z + log1p(exp(-z)):", 40.0 + np.log1p(np.exp(-40.0)))

fig, axes = plt.subplots(1, 2, figsize=(10, 4))
ax = axes[0]
xg = np.array([1e-4, 1e-8, 1e-12, 1e-16])
rel = np.abs(np.log(1 + xg) - np.log1p(xg)) / np.log1p(xg)
labels = ["1e-4", "1e-8", "1e-12", "1e-16"]
ax.bar(labels, rel, color=RED, width=0.55)
ax.set_yscale("log")
ax.set_ylim(1e-15, 1e3)
for k, v in enumerate(rel):
    ax.text(k, v * 2, f"{v:.1e}" if v < 0.5 else "100%\n（答えが 0.0）", ha="center", va="bottom", fontsize=9)
ax.set_xlabel("x")
ax.set_ylabel("log(1 + x) の相対誤差（log1p(x) との差）")
ax.set_title("x が小さいほど log(1 + x) は誤差が大きい", fontsize=10)
ax.grid(True, alpha=0.25)
ax = axes[1]
zp = np.linspace(0, 45, 900)
ax.plot(zp, np.logaddexp(0, zp), color=BLUE, lw=2.4, label="ロジットのまま計算（正しい値）")
for dtype, color, ls in [(np.float64, GRAY, "-"), (np.float32, RED, "--")]:
    zz = zp.astype(dtype)
    loss = -np.log(1 - 1 / (1 + np.exp(-zz)))
    shown = np.where(np.isinf(loss), np.nan, loss)
    ax.plot(zp, shown, color=color, lw=1.6, ls=ls, label=f"確率にしてから log（{dtype.__name__}）")
    fi = first_inf[dtype.__name__]
    ax.axvline(fi, color=color, lw=0.8, ls=":")
    ax.text(fi + 0.5, 3, f"z = {fi:.2f} から inf", color=color, fontsize=8)
ax.set_xlabel("ロジット z（正解は 0）")
ax.set_ylabel("交差エントロピー")
ax.set_title("確率に戻してから log を取ると、損失が inf になる", fontsize=10)
ax.legend(fontsize=8, loc="upper left", frameon=False)
ax.grid(True, alpha=0.25)
fig.tight_layout()
save(fig, "le_log1p.webp")

# ---- 実験 4: ロジスティック回帰の係数と、確率の変化 ----
bc = load_breast_cancer()
Xb_tr, Xb_te, yb_tr, yb_te = train_test_split(bc.data, bc.target, test_size=0.3, random_state=0, stratify=bc.target)
scaler = StandardScaler().fit(Xb_tr)
Xb_tr, Xb_te = scaler.transform(Xb_tr), scaler.transform(Xb_te)
clf = LogisticRegression(max_iter=5000).fit(Xb_tr, yb_tr)
j = np.abs(clf.coef_[0]).argmax()    # 係数の絶対値が最大の列
b = clf.coef_[0][j]
p_before = clf.predict_proba(Xb_te)[:, 1]   # 良性（target = 1）の確率
X_plus = Xb_te.copy()
X_plus[:, j] += 1                            # その列だけ 1 標準偏差増やす
p_after = clf.predict_proba(X_plus)[:, 1]
odds_ratio = (p_after / (1 - p_after)) / (p_before / (1 - p_before))
dp = p_after - p_before
print(f"列 {bc.feature_names[j]}: 係数 {b:.3f}、exp(係数) {np.exp(b):.3f}、テストの正解率 {clf.score(Xb_te, yb_te):.3f}")
print(f"オッズの比: {odds_ratio.min():.4f}〜{odds_ratio.max():.4f}（{len(dp)} 件）")
print(f"確率の変化: {dp.min() * 100:.1f}〜{dp.max() * 100:.1f} ポイント、"
      f"1 ポイント未満 {(np.abs(dp) < 0.01).sum()} 件、10 ポイント超 {(np.abs(dp) > 0.1).sum()} 件")

for p0 in [0.5, 0.99]:
    o = p0 / (1 - p0) * np.exp(b)
    print(f"もとの確率 {p0}: オッズ {p0 / (1 - p0):.1f} → {o:.2f}、確率 {o / (1 + o):.4f}（{(o / (1 + o) - p0) * 100:.1f} ポイント）")
i_max = np.abs(dp).argmax()
print(f"変化が最大の件: もとの確率 {p_before[i_max]:.3f} → {p_after[i_max]:.3f}")

fig, ax = plt.subplots(figsize=(8, 4.2))
pg = np.linspace(0.0005, 0.9995, 400)
og = pg / (1 - pg) * np.exp(b)
ax.plot(pg, (og / (1 + og) - pg) * 100, color=GRAY, lw=1.2, label="同じオッズの比で動かした時の理論の線")
ax.scatter(p_before, dp * 100, s=16, color=RED, alpha=0.75, zorder=3, label=f"テストの {len(dp)} 件")
ax.axhline(0, color=GRAY, lw=0.6)
ax.set_xlabel("もとの良性の確率")
ax.set_ylabel("確率の変化（ポイント）")
ax.set_title(f"{bc.feature_names[j]} を 1 標準偏差増やした時の良性の確率の変化"
             f"（オッズは全件 {np.exp(b):.2f} 倍）", fontsize=10, loc="left")
ax.legend(fontsize=9, loc="lower left", frameon=False)
ax.grid(True, alpha=0.25)
fig.tight_layout()
save(fig, "le_odds.webp")
