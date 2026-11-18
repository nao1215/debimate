"""class-imbalance ノートの実験と図を生成するスクリプト。

本文に載せた実験（正解率と予測確率の分布、4 つの対処の比較、閾値を下げた時との比較、
確率の平均と補正、交差検証の前の SMOTE、見逃しのコストから決める閾値）を同じ順に実行し、
出力を標準出力に、図を Page Bundle に WebP で保存する。
mammography は imbalanced-learn の fetch_datasets が Zenodo から 1 回だけ取得し、
~/scikit_learn_data に保存する。
実行: cd projects/ml && .venv/bin/python scripts/notes/class-imbalance_gen.py
確認した版: scikit-learn 1.9.1、imbalanced-learn 0.14.2、NumPy 2.5.4
"""
from io import BytesIO
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from imblearn.datasets import fetch_datasets
from imblearn.over_sampling import SMOTE, RandomOverSampler
from imblearn.pipeline import make_pipeline as make_imb_pipeline
from imblearn.under_sampling import RandomUnderSampler
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, confusion_matrix, make_scorer,
                             precision_recall_curve, precision_score, recall_score,
                             roc_auc_score)
from sklearn.model_selection import (StratifiedKFold, TunedThresholdClassifierCV,
                                     cross_val_predict, cross_val_score, train_test_split)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

NOTE_DIR = Path(__file__).resolve().parents[2] / "notes" / "ml" / "class-imbalance"
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10,
                     "axes.spines.top": False, "axes.spines.right": False})
BLUE, RED, GREEN, INK, GRAY = "#7aa6c2", "#e15759", "#59a14f", "#333333", "#999999"
DARK_BLUE = "#3f6f8f"


def save(fig, name):
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight", facecolor="#ffffff")
    plt.close(fig)
    buf.seek(0)
    Image.open(buf).convert("RGB").save(NOTE_DIR / name, "WEBP", quality=90, method=6)


# ============================================================
# 実験 1: 正解率と、そのままのモデルが出す確率
# ============================================================
data = fetch_datasets(filter_data=("mammography",))["mammography"]
X, y = data.data, (data.target == 1).astype(int)   # 元のラベルは -1 と 1
print(X.shape, "陽性", y.sum(), "件、陽性の割合", round(y.mean(), 4))
print("全部を陰性と答えた時の正解率:", round(1 - y.mean(), 4))

cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=0)


def lr(weight=None):
    return LogisticRegression(class_weight=weight, max_iter=1000)


p_plain = cross_val_predict(make_pipeline(StandardScaler(), lr()), X, y,
                            cv=cv, method="predict_proba")[:, 1]
tn, fp, fn, tp = confusion_matrix(y, p_plain >= 0.5).ravel()
print(f"閾値 0.5: 正解率 {(tn + tp) / len(y):.4f}、陽性と判定 {tp + fp} 件、"
      f"見つけた陽性 {tp} / {tp + fn} 件")
print("陽性の確率の中央値:", round(float(np.median(p_plain[y == 1])), 3),
      " 陰性の確率の中央値:", round(float(np.median(p_plain[y == 0])), 4))
print("陽性で確率が 0.5 未満の割合:", round(float((p_plain[y == 1] < 0.5).mean()), 3),
      " 陰性で確率が 0.02 未満の割合:", round(float((p_plain[y == 0] < 0.02).mean()), 3))

fig, ax = plt.subplots(figsize=(7.6, 3.6))
bins = np.logspace(-5, 0, 51)
ax.hist(p_plain[y == 0], bins=bins, color=BLUE, alpha=0.75, label=f"陰性（{(y == 0).sum()} 件）")
ax.hist(p_plain[y == 1], bins=bins, color=RED, alpha=0.85, label=f"陽性（{(y == 1).sum()} 件）")
ax.set_xscale("log")
ax.set_yscale("log")
ax.axvline(0.5, color=INK, lw=1.2, ls="--")
ax.text(0.5, 2500, " 閾値 0.5", color=INK, fontsize=9, va="top")
ax.axvline(y.mean(), color=GRAY, lw=1.2, ls=":")
ax.text(y.mean(), 2500, " 陽性の割合 0.023", color=GRAY, fontsize=9, va="top")
ax.set_xlabel("そのままのロジスティック回帰が出した陽性の確率（対数目盛）")
ax.set_ylabel("件数（対数目盛）")
ax.set_ylim(0.8, 4000)
ax.legend(frameon=False, loc="upper left")
save(fig, "ci_scores.webp")

# ============================================================
# 実験 2: 4 つの対処の比較（再サンプリングは学習側の fold だけ）
# ============================================================
def hgb(weight=None):
    return HistGradientBoostingClassifier(class_weight=weight, random_state=0)


rows = {}
for model_name, base in [("ロジスティック回帰", lr), ("勾配ブースティング", hgb)]:
    candidates = {
        "そのまま": make_pipeline(StandardScaler(), base()),
        "class_weight": make_pipeline(StandardScaler(), base("balanced")),
        "ランダムオーバー": make_imb_pipeline(StandardScaler(), RandomOverSampler(random_state=0), base()),
        "SMOTE": make_imb_pipeline(StandardScaler(), SMOTE(random_state=0), base()),
        "ランダムアンダー": make_imb_pipeline(StandardScaler(), RandomUnderSampler(random_state=0), base()),
    }
    for name, model in candidates.items():
        p = cross_val_predict(model, X, y, cv=cv, method="predict_proba")[:, 1]
        rows[(model_name, name)] = p
        print(f"{model_name} {name:<10} ROC-AUC {roc_auc_score(y, p):.3f}  "
              f"PR-AUC {average_precision_score(y, p):.3f}  "
              f"閾値 0.5 の再現率 {recall_score(y, p >= 0.5):.3f}  "
              f"適合率 {precision_score(y, p >= 0.5):.3f}  確率の平均 {p.mean():.3f}")

# ============================================================
# 実験 3: class_weight と、閾値を下げただけのモデル（表紙の図）
# ============================================================
p_bal = rows[("ロジスティック回帰", "class_weight")]
r_bal, q_bal = recall_score(y, p_bal >= 0.5), precision_score(y, p_bal >= 0.5)
for t in np.round(np.arange(0.100, 0.0, -0.0001), 4):     # 再現率が並ぶまで閾値を下げる
    if recall_score(y, p_plain >= t) >= r_bal:
        break
r_low, q_low = recall_score(y, p_plain >= t), precision_score(y, p_plain >= t)
print(f"class_weight、閾値 0.5   : 再現率 {r_bal:.3f}  適合率 {q_bal:.3f}  陽性と判定 {(p_bal >= 0.5).sum()} 件")
print(f"そのまま、閾値 {t:.4f}  : 再現率 {r_low:.3f}  適合率 {q_low:.3f}  陽性と判定 {(p_plain >= t).sum()} 件")

m_plain = make_pipeline(StandardScaler(), lr()).fit(X, y)
m_bal = make_pipeline(StandardScaler(), lr("balanced")).fit(X, y)
w = (y == 0).sum() / (y == 1).sum()
print(f"陽性の重み ÷ 陰性の重み: {w:.1f}、その対数: {np.log(w):.2f}")
print("切片:", round(float(m_plain[-1].intercept_[0]), 2), "→", round(float(m_bal[-1].intercept_[0]), 2))
print("係数（そのまま）    :", m_plain[-1].coef_[0].round(2))
print("係数（class_weight）:", m_bal[-1].coef_[0].round(2))

fig, ax = plt.subplots(figsize=(6.4, 4.4))
for p, color, label in [(p_plain, DARK_BLUE, "そのまま"), (p_bal, RED, "class_weight=\"balanced\"")]:
    prec, rec, _ = precision_recall_curve(y, p)
    ax.plot(rec, prec, color=color, lw=1.8, label=f"{label}（PR-AUC {average_precision_score(y, p):.3f}）")
r05, q05 = recall_score(y, p_plain >= 0.5), precision_score(y, p_plain >= 0.5)
ax.scatter([r05], [q05], s=60, color=DARK_BLUE, zorder=5)
ax.annotate(f"そのまま・閾値 0.5\n再現率 {r05:.2f}、適合率 {q05:.2f}", (r05, q05), xytext=(0.06, 0.55),
            fontsize=9, color=DARK_BLUE, arrowprops=dict(arrowstyle="-", color=DARK_BLUE, lw=0.8))
ax.scatter([r_low], [q_low], s=70, marker="D", color=DARK_BLUE, zorder=5)
ax.annotate(f"そのまま・閾値 {t:.3f}\n適合率 {q_low:.2f}", (r_low, q_low), xytext=(0.66, 0.66),
            fontsize=9, color=DARK_BLUE, arrowprops=dict(arrowstyle="-", color=DARK_BLUE, lw=0.8))
ax.scatter([r_bal], [q_bal], s=60, color=RED, zorder=5)
ax.annotate(f"class_weight・閾値 0.5\n再現率 {r_bal:.2f}、適合率 {q_bal:.2f}", (r_bal, q_bal),
            xytext=(0.42, 0.11), fontsize=9, color=RED,
            arrowprops=dict(arrowstyle="-", color=RED, lw=0.8))
ax.axhline(y.mean(), color=GRAY, ls=":", lw=1)
ax.text(0.01, y.mean() + 0.012, "陽性の割合 0.023（でたらめに選んだ時の適合率）", fontsize=8, color=GRAY)
ax.set_xlabel("再現率（260 件の陽性のうち見つけた割合）")
ax.set_ylabel("適合率（陽性と判定した中で本当に陽性だった割合）")
ax.set_xlim(0, 1.02)
ax.set_ylim(0, 1.02)
ax.legend(frameon=False, loc="upper right", fontsize=9)
ax.grid(True, alpha=0.25)
save(fig, "ci_cover.webp")

# ============================================================
# 実験 4: 確率の平均と、重みの分を戻す補正
# ============================================================
odds = p_bal / (1 - p_bal)
p_fix = (odds / w) / (1 + odds / w)        # オッズを陽性の重みの倍率 w で割って戻す
for name, p in [("そのまま", p_plain), ("class_weight", p_bal), ("class_weight を補正", p_fix)]:
    print(f"{name:<18} 確率の平均 {p.mean():.4f}  ROC-AUC {roc_auc_score(y, p):.3f}")
print("実際の陽性の割合:", round(y.mean(), 4))


def reliability(p, edges):
    idx = np.digitize(p, edges[1:-1])
    return (np.array([p[idx == i].mean() for i in range(len(edges) - 1)]),
            np.array([y[idx == i].mean() for i in range(len(edges) - 1)]))


fig, ax = plt.subplots(figsize=(6.0, 4.4))
qs = [0, 0.5, 0.8, 0.9, 0.95, 0.98, 0.99, 1]
for p, color, marker, label in [(p_plain, DARK_BLUE, "o", "そのまま"),
                                (p_bal, RED, "s", "class_weight=\"balanced\""),
                                (p_fix, GREEN, "^", "class_weight の確率を補正")]:
    mp, fr = reliability(p, np.quantile(p, qs))
    ax.plot(mp, fr, color=color, marker=marker, lw=1.5, label=label)
ax.plot([1e-3, 1], [1e-3, 1], color=GRAY, ls="--", lw=1)
ax.text(0.0035, 0.0055, "確率どおりに陽性が出る線", rotation=33, fontsize=8, color=GRAY)
ax.set_xscale("log")
ax.set_yscale("log")
ax.set_xlim(5e-4, 1.1)
ax.set_ylim(1e-3, 1.1)
ax.set_xlabel("モデルが出した確率の平均（区間ごと、対数目盛）")
ax.set_ylabel("その区間で実際に陽性だった割合")
ax.legend(frameon=False, loc="upper left", fontsize=9)
ax.grid(True, alpha=0.25, which="both")
save(fig, "ci_reliability.webp")

# ============================================================
# 実験 5: 交差検証の前に SMOTE をかけた時
# ============================================================
X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.3, stratify=y, random_state=0)


def rf():
    return RandomForestClassifier(n_estimators=300, random_state=0, n_jobs=4)


X_sm, y_sm = SMOTE(random_state=0).fit_resample(X_tr, y_tr)   # 分ける前に全体へ SMOTE
before = cross_val_score(rf(), X_sm, y_sm, cv=cv, scoring="average_precision").mean()
inside = cross_val_score(make_imb_pipeline(SMOTE(random_state=0), rf()), X_tr, y_tr,
                         cv=cv, scoring="average_precision").mean()   # fold の学習側だけに SMOTE
model = make_imb_pipeline(SMOTE(random_state=0), rf()).fit(X_tr, y_tr)
test = average_precision_score(y_te, model.predict_proba(X_te)[:, 1])
print(f"SMOTE の後に交差検証   : PR-AUC {before:.3f}")
print(f"Pipeline の中で SMOTE  : PR-AUC {inside:.3f}")
print(f"使っていない 30% で評価: PR-AUC {test:.3f}")

fig, ax = plt.subplots(figsize=(6.6, 3.0))
labels = ["SMOTE をかけてから\n交差検証", "Pipeline の中で\nSMOTE して交差検証", "学習に使っていない\n30% で評価"]
vals = [before, inside, test]
bars = ax.barh(labels[::-1], vals[::-1], color=[GRAY, BLUE, RED][::-1], height=0.55)
for b, v in zip(bars, vals[::-1]):
    ax.text(v + 0.01, b.get_y() + b.get_height() / 2, f"{v:.3f}", va="center", fontsize=10)
ax.set_xlim(0, 1.1)
ax.set_xlabel("PR-AUC（ランダムフォレスト）")
save(fig, "ci_leak.webp")

# ============================================================
# 実験 6: 見逃し 1 件を誤報 10 件分と数えた時の閾値
# ============================================================
C = 10                       # 見逃し 1 件のコスト ÷ 誤報 1 件のコスト


def cost(y_true, y_pred):
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
    return fp + C * fn


ts = np.linspace(0.005, 0.6, 600)
costs = np.array([cost(y, p_plain >= s) for s in ts])
t_star = 1 / (1 + C)
print(f"そのまま、閾値 0.5      : コスト {cost(y, p_plain >= 0.5)}")
print(f"class_weight、閾値 0.5  : コスト {cost(y, p_bal >= 0.5)}")
print(f"そのまま、閾値 1/(1+C) = {t_star:.3f}: コスト {cost(y, p_plain >= t_star)}")
print(f"そのまま、一番低い閾値 {ts[costs.argmin()]:.3f}: コスト {costs.min()}")

tuned = TunedThresholdClassifierCV(make_pipeline(StandardScaler(), lr()),
                                   scoring=make_scorer(lambda a, b: -cost(a, b)), cv=5)
print("TunedThresholdClassifierCV の交差検証でのコスト:", cost(y, cross_val_predict(tuned, X, y, cv=cv)))
print("全データで選んだ閾値:", round(float(tuned.fit(X, y).best_threshold_), 3))

fig, ax = plt.subplots(figsize=(7.2, 3.8))
ax.plot(ts, costs, color=DARK_BLUE, lw=1.8, label="そのまま（閾値を動かす）")
ax.axhline(cost(y, p_bal >= 0.5), color=RED, ls="--", lw=1.3,
           label=f"class_weight・閾値 0.5（{cost(y, p_bal >= 0.5)}）")
for s, txt, xy in [(0.5, "閾値 0.5", (0.5, 1080)), (t_star, f"閾値 1/(1+10) = {t_star:.3f}", (t_star + 0.03, 740))]:
    c = cost(y, p_plain >= s)
    ax.scatter([s], [c], color=DARK_BLUE, s=50, zorder=5)
    ax.annotate(f"{txt}\nコスト {c}", (s, c), xytext=xy, fontsize=9, color=DARK_BLUE,
                ha="center" if s == 0.5 else "left",
                arrowprops=dict(arrowstyle="-", color=DARK_BLUE, lw=0.8) if s == 0.5 else None)
ax.set_xscale("log")
ax.set_xlabel("閾値（そのまま、対数目盛）")
ax.set_ylabel("誤報の件数 + 10 × 見逃しの件数")
ax.set_ylim(0, 3000)
ax.legend(frameon=False, loc="upper left", fontsize=9)
ax.grid(True, alpha=0.25)
save(fig, "ci_cost.webp")
