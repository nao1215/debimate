"""bayes-theorem ノートの実験と図を生成するスクリプト。

本文に載せた実験（class_weight="balanced" の予測確率と実際の陽性の割合、判定の件数と
ベイズの定理、陽性の割合と Precision、オッズの形での補正、確率を戻す方法の比較、
ナイーブベイズに同じ列を足した時の確率）を同じ順に実行し、出力を標準出力に、
図を Page Bundle に WebP で保存する。
データは OpenML の 310 番（mammography）。初回だけ OpenML から取得し、以降は
~/scikit_learn_data のキャッシュを使う。
実行: cd projects/ml && .venv/bin/python scripts/notes/bayes-theorem_gen.py
確認した版: scikit-learn 1.9.1、NumPy 2.5.4、matplotlib 3.11.2
"""
from io import BytesIO
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from sklearn.calibration import CalibratedClassifierCV
from sklearn.datasets import fetch_openml
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import GaussianNB

NOTE_DIR = Path(__file__).resolve().parents[2] / "notes" / "math" / "bayes-theorem"
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
# 実験 1: class_weight="balanced" の予測確率と、実際に陽性だった割合
# ============================================================
mammo = fetch_openml(data_id=310, as_frame=True)          # mammography（OpenML の 310 番）
X = mammo.data.to_numpy(float)
y = (mammo.target.astype(int) == 1).astype(int).to_numpy()  # 1 = 石灰化
X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.5, stratify=y, random_state=0)
print(f"学習 {len(y_tr)} 件（陽性 {y_tr.sum()}）、テスト {len(y_te)} 件（陽性 {y_te.sum()}）")

plain = LogisticRegression(max_iter=1000).fit(X_tr, y_tr)
balanced = LogisticRegression(max_iter=1000, class_weight="balanced").fit(X_tr, y_tr)
p_plain = plain.predict_proba(X_te)[:, 1]
p_bal = balanced.predict_proba(X_te)[:, 1]

sel = (p_bal >= 0.8) & (p_bal < 0.9)
print(f"balanced が 0.8〜0.9 を付けた件数 {sel.sum()}、そのうち陽性 {y_te[sel].sum()}"
      f"（{y_te[sel].mean():.1%}）")


def correct(p, prior_train, prior_new):
    """学習時の陽性の割合 prior_train で出た確率 p を、割合 prior_new の確率に直す。"""
    odds = p / (1 - p) * (prior_new / (1 - prior_new)) / (prior_train / (1 - prior_train))
    return odds / (1 + odds)


prior = y_tr.mean()                                     # 学習データの陽性の割合
p_fix = correct(p_bal, 0.5, prior)                      # balanced は割合 0.5 で学習したのと同じ

edges = np.linspace(0, 1, 11)


def reliability(p):
    xs, ys, ns = [], [], []
    for lo, hi in zip(edges[:-1], edges[1:]):
        s = (p >= lo) & (p < hi) if hi < 1 else (p >= lo)
        if s.sum() >= 10:                               # 10 件未満の区間は描かない
            xs.append(p[s].mean()); ys.append(y_te[s].mean()); ns.append(s.sum())
    return np.array(xs), np.array(ys), np.array(ns)


for name, p in [("重み無し", p_plain), ("balanced", p_bal), ("balanced を補正", p_fix)]:
    xs, ys, ns = reliability(p)
    print(name, "区間ごとの（確率の平均, 陽性の割合, 件数）:",
          [(round(a, 2), round(b, 2), int(c)) for a, b, c in zip(xs, ys, ns)])

fig, ax = plt.subplots(figsize=(6.2, 4.6))
ax.plot([0, 1], [0, 1], ls=":", color=GRAY, lw=1)
ax.text(0.62, 0.68, "確率どおりの線", color=GRAY, rotation=36, fontsize=9)
for name, p, color, marker in [("重み無し", p_plain, BLUE, "o"),
                                ('class_weight="balanced"', p_bal, RED, "s"),
                                ("balanced をベイズの定理で補正", p_fix, GREEN, "^")]:
    xs, ys, _ = reliability(p)
    ax.plot(xs, ys, marker=marker, color=color, lw=1.8, ms=6, label=name)
xb, yb, nb_ = reliability(p_bal)
i = int(np.argmin(np.abs(xb - 0.85)))
ax.annotate(f"0.8〜0.9 の {nb_[i]} 件のうち\n陽性は {y_te[sel].sum()} 件",
            xy=(xb[i], yb[i]), xytext=(0.48, 0.30), color=RED, fontsize=9.5,
            arrowprops=dict(arrowstyle="->", color=RED, lw=1))
ax.set_xlim(0, 1); ax.set_ylim(0, 1)
ax.set_xlabel("予測確率（区間ごとの平均）")
ax.set_ylabel("その区間で実際に陽性だった割合")
ax.legend(loc="upper left", frameon=False, fontsize=9)
save(fig, "bayes_cover.webp")

# ============================================================
# 実験 2: 判定の件数とベイズの定理
# ============================================================
pred = (p_bal >= 0.5).astype(int)                       # predict と同じ閾値 0.5
tp = int(((pred == 1) & (y_te == 1)).sum()); fn = int(((pred == 0) & (y_te == 1)).sum())
fp = int(((pred == 1) & (y_te == 0)).sum()); tn = int(((pred == 0) & (y_te == 0)).sum())
n = len(y_te)
print(f"TP {tp}  FN {fn}  FP {fp}  TN {tn}")
recall = tp / (tp + fn); fpr = fp / (fp + tn); prev = (tp + fn) / n
print(f"P(判定陽性 | 石灰化) = {tp}/{tp + fn} = {recall:.3f}")
print(f"P(判定陽性 | 石灰化でない) = {fp}/{fp + tn} = {fpr:.3f}")
print(f"P(石灰化) = {tp + fn}/{n} = {prev:.4f}")
bayes = recall * prev / (recall * prev + fpr * (1 - prev))
print(f"ベイズの定理で求めた P(石灰化 | 判定陽性) = {bayes:.3f}、数えた値 {tp}/{tp + fp} = {tp / (tp + fp):.3f}")

fig, axes = plt.subplots(1, 2, figsize=(7.8, 3.6), gridspec_kw={"width_ratios": [1.15, 1]})
ax = axes[0]
pos_w = (tp + fn) / n
ax.add_patch(plt.Rectangle((0, 0), 1 - pos_w, 1, color="#eeeeee"))
ax.add_patch(plt.Rectangle((0, 0), 1 - pos_w, fp / (fp + tn), color=BLUE))
ax.add_patch(plt.Rectangle((1 - pos_w, 0), pos_w, 1, color="#f6d5d5"))
ax.add_patch(plt.Rectangle((1 - pos_w, 0), pos_w, recall, color=RED))
ax.text(0.45, 0.55, f"石灰化でない {fp + tn} 件", ha="center", fontsize=10, color=INK)
ax.text(0.45, fp / (fp + tn) / 2, f"判定陽性 {fp} 件", ha="center", va="center", fontsize=10, color="#ffffff")
ax.annotate(f"石灰化 {tp + fn} 件\n（幅 {pos_w:.1%}）\nうち判定陽性 {tp} 件", xy=(1 - pos_w / 2, 0.5),
            xytext=(1.04, 0.62), fontsize=9.5, color=RED, arrowprops=dict(arrowstyle="->", color=RED))
ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.set_xticks([]); ax.set_yticks([0, 0.5, 1])
ax.set_ylabel("判定陽性になった割合")
ax.set_title("テストの 5592 件（横幅は件数の比）", fontsize=10, loc="left")
ax = axes[1]
ax.barh([1], [tp], color=RED); ax.barh([1], [fp], left=[tp], color=BLUE)
ax.barh([0], [tp], color=RED); ax.barh([0], [fn], left=[tp], color="#f6d5d5")
ax.set_yticks([0, 1], ["石灰化の\n画像", "判定陽性の\n画像"])
ax.text(tp + fp + 8, 1, f"{tp}/{tp + fp} = {tp / (tp + fp):.1%}", va="center", fontsize=10)
ax.text(tp + fn + 8, 0, f"{tp}/{tp + fn} = {recall:.1%}", va="center", fontsize=10)
ax.set_xlim(0, (tp + fp) * 1.45); ax.set_xlabel("件数")
ax.set_title(f"赤は石灰化で、判定も陽性だった {tp} 件", fontsize=10, loc="left")
for s in ["left"]:
    ax.spines[s].set_visible(False)
fig.tight_layout(w_pad=3)
save(fig, "bayes_counts.webp")

# ============================================================
# 実験 3: 陽性の割合を変えると Precision はどう動くか
# ============================================================
rng = np.random.default_rng(0)
pos_idx = np.where(y_te == 1)[0]; neg_idx = np.where(y_te == 0)[0]
grid = np.logspace(np.log10(0.002), np.log10(0.5), 200)
formula = recall * grid / (recall * grid + fpr * (1 - grid))
measured = []
for pi in [0.5, 0.2, 0.05, 0.01, 0.005]:
    vals = []
    for _ in range(200):
        n_pos = min(len(pos_idx), round(pi / (1 - pi) * len(neg_idx)))
        n_neg = round(n_pos * (1 - pi) / pi) if n_pos == len(pos_idx) else len(neg_idx)
        idx = np.r_[rng.choice(pos_idx, n_pos, replace=False), rng.choice(neg_idx, n_neg, replace=False)]
        hit = pred[idx] == 1
        vals.append(y_te[idx][hit].mean())
    measured.append((pi, np.mean(vals)))
    print(f"陽性の割合 {pi:<5}: 数えた Precision {np.mean(vals):.3f}  "
          f"ベイズの定理 {recall * pi / (recall * pi + fpr * (1 - pi)):.3f}")

fig, ax = plt.subplots(figsize=(6.2, 4.0))
ax.plot(grid, formula, color=INK, lw=1.6, label="ベイズの定理（Recall と偽陽性率は固定）")
mx, my = zip(*measured)
ax.scatter(mx, my, color=RED, zorder=3, s=36, label="テストから選び直して数えた値（200 回の平均）")
ax.scatter([prev], [tp / (tp + fp)], color=BLUE, zorder=3, s=46, marker="D", label=f"テストそのまま（{prev:.1%}）")
ax.set_xscale("log"); ax.set_ylim(0, 1)
ax.set_xticks([0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5], ["0.2%", "0.5%", "1%", "2%", "5%", "10%", "20%", "50%"])
ax.set_xlabel("陽性の割合 P(石灰化)")
ax.set_ylabel("Precision = P(石灰化 | 判定陽性)")
ax.legend(loc="upper left", frameon=False, fontsize=9)
save(fig, "bayes_prevalence.webp")

# ============================================================
# 実験 4: オッズで書くと、重み付けは切片がずれるだけ
# ============================================================
logit = lambda p: np.log(p / (1 - p))
shift_theory = np.log((1 - prior) / prior)
print(f"切片の差（balanced - 重み無し）{(balanced.intercept_ - plain.intercept_)[0]:.2f}、"
      f"log((1 - π) / π) = {shift_theory:.2f}")
diff = logit(p_bal) - logit(p_plain)
print(f"テスト 5592 件の対数オッズの差: 中央値 {np.median(diff):.2f}、"
      f"25% 点 {np.percentile(diff, 25):.2f}、75% 点 {np.percentile(diff, 75):.2f}")
_, dup = np.unique(X_te, axis=0, return_counts=True)
print(f"6 列とも同じ値の画像の最大の組 {dup.max()} 件、差が 4.34 の画像 {np.isclose(diff, 4.34, atol=0.005).sum()} 件")
branch = diff > 5
print(f"差が 5 を超える画像 {branch.sum()} 件（石灰化 {y_te[branch].sum()} 件）、"
      f"列ごとの平均 {X_te[branch].mean(0).round(2)}（それ以外 {X_te[~branch].mean(0).round(2)}）、"
      f"重みの差 {(balanced.coef_ - plain.coef_)[0].round(2)}")
print(f"差が 5 を超える画像で、列ごとの（重みの差 × 値）の平均 "
      f"{((balanced.coef_ - plain.coef_)[0] * X_te[branch]).mean(0).round(2)}")

fig, ax = plt.subplots(figsize=(5.4, 4.6))
lx, ly = logit(p_plain), logit(p_bal)
ax.scatter(lx[y_te == 0], ly[y_te == 0], s=5, color=BLUE, alpha=0.35, label="石灰化でない")
ax.scatter(lx[y_te == 1], ly[y_te == 1], s=12, color=RED, alpha=0.8, label="石灰化")
xx = np.array([-12, 6])
ax.plot(xx, xx, ls=":", color=GRAY, lw=1)
ax.plot(xx, xx + shift_theory, color=INK, lw=1.2)
ax.annotate(f"ずれ = log((1-π)/π) = {shift_theory:.2f}\n（π は学習データで陽性が占める割合）", xy=(-5, -5 + shift_theory),
            xytext=(-2.0, -6.6), fontsize=9, color=INK, arrowprops=dict(arrowstyle="->", color=INK, lw=0.8))
ax.text(-11.3, -10.2, "ずれ 0 の線", fontsize=9, color=GRAY, rotation=38)
ax.set_xlim(-12, 6); ax.set_ylim(-12, 10)
ax.set_xlabel("重み無しの対数オッズ")
ax.set_ylabel('class_weight="balanced" の対数オッズ')
ax.legend(loc="upper left", frameon=False, fontsize=9)
save(fig, "bayes_logodds.webp")

# ============================================================
# 実験 5: 確率を戻す方法の比較
# ============================================================
pos_tr = np.where(y_tr == 1)[0]
neg_tr = rng.choice(np.where(y_tr == 0)[0], len(pos_tr), replace=False)
under_idx = np.r_[pos_tr, neg_tr]                        # 陽性と同じ数だけ陰性を残す
under = LogisticRegression(max_iter=1000).fit(X_tr[under_idx], y_tr[under_idx])
p_under = under.predict_proba(X_te)[:, 1]
cal = CalibratedClassifierCV(LogisticRegression(max_iter=1000, class_weight="balanced"),
                             method="sigmoid", cv=5).fit(X_tr, y_tr)
rows = [
    ("重み無し", p_plain),
    ('balanced のまま', p_bal),
    ('balanced をベイズの定理で補正', p_fix),
    ("アンダーサンプリングのまま", p_under),
    ("アンダーサンプリングを補正", correct(p_under, 0.5, prior)),
    ('balanced を CalibratedClassifierCV で校正', cal.predict_proba(X_te)[:, 1]),
]
for name, p in rows:
    print(f"{name:<40} log loss {log_loss(y_te, p):.4f}  確率の平均 {p.mean():.4f}  "
          f"ROC-AUC {roc_auc_score(y_te, p):.3f}")
print(f"テストの陽性の割合 {y_te.mean():.4f}")

# ============================================================
# 実験 6: ナイーブベイズに同じ列を足す
# ============================================================
nb_rows = []
for k in [1, 2, 4, 8]:
    nb = GaussianNB().fit(np.tile(X_tr, k), y_tr)        # 6 列を k 回並べる
    p = nb.predict_proba(np.tile(X_te, k))[:, 1]
    stuck = ((p > 0.999) | (p < 0.001)).mean()
    hi = p >= 0.9
    nb_rows.append((k, stuck, log_loss(y_te, p), roc_auc_score(y_te, p), y_te[hi].mean()))
    print(f"同じ列を {k} 回: 0.001 未満か 0.999 超 {stuck:.1%}  log loss {log_loss(y_te, p):.3f}  "
          f"ROC-AUC {roc_auc_score(y_te, p):.3f}  0.9 以上 {hi.sum()} 件のうち陽性 {y_te[hi].mean():.1%}")
# 対照: 列を分位変換で正規分布の形に直してから GaussianNB に渡す（独立の崩れと正規性の崩れを分ける）
from sklearn.preprocessing import QuantileTransformer
qt = QuantileTransformer(output_distribution="normal", random_state=0).fit(X_tr)
p_q = GaussianNB().fit(qt.transform(X_tr), y_tr).predict_proba(qt.transform(X_te))[:, 1]
print(f"分位変換してから 1 回: 0.001 未満か 0.999 超 {((p_q > 0.999) | (p_q < 0.001)).mean():.1%}  "
      f"log loss {log_loss(y_te, p_q):.3f}  ROC-AUC {roc_auc_score(y_te, p_q):.3f}")
print(f"参考: 重み無しのロジスティック回帰で 0.001 未満か 0.999 超 {((p_plain > 0.999) | (p_plain < 0.001)).mean():.1%}")
corr = np.corrcoef(X_tr[y_tr == 0], rowvar=False)
print(f"陰性の中での列どうしの相関係数: 絶対値の最大 {np.abs(corr[np.triu_indices(6, 1)]).max():.2f}")

fig, axes = plt.subplots(1, 3, figsize=(9.6, 3.0))
ks = [r[0] for r in nb_rows]
for ax, j, title, color in [(axes[0], 1, "0 か 1 に張り付いた予測の割合", RED),
                            (axes[1], 2, "log loss（小さいほど確率が正しい）", RED),
                            (axes[2], 3, "ROC-AUC（順位だけを見る）", BLUE)]:
    vals = [r[j] for r in nb_rows]
    ax.plot(ks, vals, marker="o", color=color, lw=1.8)
    for k_, v in zip(ks, vals):
        ax.annotate(f"{v:.0%}" if j == 1 else f"{v:.2f}" if j == 2 else f"{v:.3f}", (k_, v),
                    xytext=(0, 7), textcoords="offset points", fontsize=9, ha="center")
    ax.set_xscale("log", base=2); ax.set_xticks(ks, [str(k_) for k_ in ks])
    ax.set_xlabel("同じ 6 列を並べた回数")
    ax.set_title(title, fontsize=10, loc="left")
axes[0].set_ylim(0.6, 1.0); axes[1].set_ylim(0, 2.9); axes[2].set_ylim(0.85, 0.95)
axes[0].yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
for ax in axes:
    ax.set_xlim(0.8, 11)
fig.tight_layout(w_pad=2.5)
save(fig, "bayes_nb_copies.webp")

# ============================================================
# 実験 7: 本番の陽性の割合を、少しずつ届く正解から見積もる（Beta 分布）
# ============================================================
from scipy import stats

prod_n_neg = round(len(pos_idx) * 0.95 / 0.05)            # 陽性 130 件と陰性 2470 件で、割合 5% の本番を作る
prod = np.r_[pos_idx, rng.choice(neg_idx, prod_n_neg, replace=False)]
labels = y_te[rng.permutation(prod)]                     # 正解が届く順
priors = {"一様 Beta(1, 1)": (1.0, 1.0),
          "学習時の 2.3% を 100 件分 Beta(2.3, 97.7)": (2.3, 97.7),
          "学習時の 2.3% を 1000 件分 Beta(23, 977)": (23.0, 977.0)}
ns = [0, 50, 100, 200, 400, 800, 1600]
band = {}
for name, (a, b) in priors.items():
    rows_ = []
    for n_ in ns:
        h = int(labels[:n_].sum())
        post = stats.beta(a + h, b + n_ - h)              # 事前 Beta(a, b) に陽性 h 件・陰性 n - h 件
        rows_.append((n_, h, post.mean(), *post.ppf([0.025, 0.975])))
    band[name] = rows_
    print(name)
    for n_, h, m, lo, hi in rows_:
        if n_ in (0, 200, 1600):
            print(f"  正解 {n_:>4} 件（陽性 {h:>2}）: 事後平均 {m:.3f}  95% 信用区間 {lo:.3f}〜{hi:.3f}")
# 1 件ずつ更新しても、まとめて更新しても同じになる
a, b = priors["学習時の 2.3% を 100 件分 Beta(2.3, 97.7)"]
for v in labels[:200]:
    a, b = a + v, b + 1 - v
print("一様 Beta(1, 1) の事後平均:", "  ".join(f"{n_} 件 {m:.3f}" for n_, _, m, _, _ in band["一様 Beta(1, 1)"]))
print(f"1 件ずつ 200 回更新: Beta({a:.1f}, {b:.1f})、まとめて: Beta({2.3 + labels[:200].sum():.1f}, {97.7 + 200 - labels[:200].sum():.1f})")

fig, ax = plt.subplots(figsize=(6.6, 4.0))
for (name, rows_), color in zip(band.items(), [GRAY, BLUE, RED]):
    n_, _, m, lo, hi = map(np.array, zip(*rows_))
    if name.startswith("一様"):                            # 0 件の時の平均 0.5 は枠の外なので 50 件から描く
        n_, m, lo, hi = n_[1:], m[1:], lo[1:], hi[1:]
    xs = np.maximum(n_, 25)
    ax.plot(xs, m, marker="o", color=color, lw=1.8, ms=4, label=name)
    ax.fill_between(xs, lo, hi, color=color, alpha=0.15)
ax.axhline(0.05, ls=":", color=INK, lw=1)
ax.text(1700, 0.052, "本番の割合 5%", fontsize=9, color=INK, ha="right", va="bottom")
ax.axhline(prior, ls=":", color=GRAY, lw=1)
ax.text(1700, prior - 0.002, "学習時の割合 2.3%", fontsize=9, color=GRAY, ha="right", va="top")
ax.set_xscale("log")
ax.set_xticks(np.maximum(ns, 25), ["0"] + [str(v) for v in ns[1:]])
ax.minorticks_off()
ax.set_ylim(0, 0.16)
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
ax.set_xlabel("届いた正解の件数")
ax.set_ylabel("陽性の割合の事後平均と 95% 信用区間")
ax.legend(loc="upper right", frameon=False, fontsize=9)
save(fig, "bayes_beta.webp")
