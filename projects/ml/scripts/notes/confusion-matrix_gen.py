"""confusion-matrix ノートの実験と図を生成するスクリプト。

本文に載せた 4 つの実験（breast_cancer の陽性のラベル、閾値ごとの 2 つの Recall、
8 件のスコアで閾値を動かす、見逃しと誤報のコストから閾値を決める）を同じ順に実行し、
出力を標準出力に、図を Page Bundle に WebP で保存する。
実行: cd projects/ml && .venv/bin/python scripts/notes/confusion-matrix_gen.py
確認した版: scikit-learn 1.9.1、NumPy 2.5.4、matplotlib 3.11.2
"""
from io import BytesIO
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from sklearn.datasets import load_breast_cancer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix, make_scorer, precision_score, recall_score
from sklearn.model_selection import StratifiedKFold, TunedThresholdClassifierCV, train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

NOTE_DIR = Path(__file__).resolve().parents[2] / "notes" / "ml" / "confusion-matrix"
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10,
                     "axes.spines.top": False, "axes.spines.right": False})
BLUE, RED, GREEN, INK, GRAY = "#7aa6c2", "#e15759", "#59a14f", "#333333", "#999999"


def save(fig, name):
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight", facecolor="#ffffff")
    plt.close(fig)
    buf.seek(0)
    Image.open(buf).convert("RGB").save(NOTE_DIR / name, "WEBP", quality=90, method=6)


# ---- 実験 1: breast_cancer の陽性は「良性」。そのまま閾値を下げる ----
data = load_breast_cancer()
X, y = data.data, data.target
print("ラベル:", dict(enumerate(data.target_names)), "件数:", np.bincount(y))
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.5, stratify=y, random_state=0)
model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000)).fit(X_train, y_train)
proba = model.predict_proba(X_test)[:, 1]  # 解説でよく見る書き方。列 1 はラベル 1（良性）の確率
print("テスト:", np.bincount(y_test))
for threshold in [0.5, 0.1]:
    y_pred = (proba >= threshold).astype(int)
    cm = confusion_matrix(y_test, y_pred)
    print(f"閾値 {threshold}: 混同行列 {cm.tolist()}、recall_score {recall_score(y_test, y_pred):.3f}、"
          f"悪性の Recall {recall_score(y_test, y_pred, pos_label=0):.3f}、悪性の見逃し {cm[0, 1]} 件")

# 図 1（表紙）: 閾値 0.5 と 0.1 の混同行列
fig, axes = plt.subplots(1, 2, figsize=(8.4, 3.9))
for ax, threshold in zip(axes, [0.5, 0.1]):
    y_pred = (proba >= threshold).astype(int)
    cm = confusion_matrix(y_test, y_pred)
    for i in range(2):
        for j in range(2):
            miss = (i, j) == (0, 1)
            face = "#fbe3e3" if miss else ("#e4eef4" if i == j else "#f4f4f4")
            ax.add_patch(plt.Rectangle((j - 0.5, i - 0.5), 1, 1, facecolor=face,
                                       edgecolor=RED if miss else "#ffffff", linewidth=2.5 if miss else 1))
            ax.text(j, i, f"{cm[i, j]}", ha="center", va="center", fontsize=20,
                    color=RED if miss else INK)
    ax.set_xlim(-0.5, 1.5)
    ax.set_ylim(1.5, -0.5)
    ax.set_xticks([0, 1], ["予測: 悪性 (0)", "予測: 良性 (1)"])
    ax.set_yticks([0, 1], ["正解: 悪性 (0)", "正解: 良性 (1)"])
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_title(f"閾値 {threshold}\nrecall_score {recall_score(y_test, y_pred):.3f}"
                 f" ／ 悪性の見逃し {cm[0, 1]} 件", fontsize=11, color=INK)
fig.suptitle("predict_proba(X)[:, 1] に閾値を掛けた結果（breast_cancer のテスト 285 件）",
             fontsize=10, color="#555555", y=0.02)
fig.tight_layout(rect=(0, 0.05, 1, 1))
save(fig, "confusion-matrix_cover.webp")

# ---- 実験 2: 閾値ごとに、既定の recall_score と悪性の Recall を並べる ----
grid = np.round(np.arange(0.05, 0.951, 0.01), 2)
rec_default, rec_malignant = [], []
for t in grid:
    y_pred = (proba >= t).astype(int)
    rec_default.append(recall_score(y_test, y_pred))
    rec_malignant.append(recall_score(y_test, y_pred, pos_label=0))
fig, ax = plt.subplots(figsize=(7, 3.6))
ax.plot(grid, rec_default, color=GRAY, linewidth=2, label="recall_score の既定（陽性 = 良性）")
ax.plot(grid, rec_malignant, color=RED, linewidth=2, label="pos_label=0 の Recall（陽性 = 悪性）")
for t in [0.5, 0.1]:
    ax.axvline(t, color="#bbbbbb", linestyle=":", linewidth=1)
    ax.text(t, 1.012, f"閾値 {t}", ha="center", fontsize=9, color="#555555")
ax.invert_xaxis()
ax.set_xlabel("predict_proba(X)[:, 1] に掛ける閾値（右へ行くほど下げる）")
ax.set_ylabel("Recall")
ax.set_ylim(min(rec_default + rec_malignant) - 0.02, 1.03)
ax.legend(loc="lower left", frameon=False)
fig.tight_layout()
save(fig, "confusion-matrix_two_recalls.webp")

# ---- 実験 2.5: 文字列のラベルで ravel() の名前がずれる（NG が見つけたい側） ----
y_true = ["OK", "NG", "OK", "NG", "NG"]
y_pred = ["OK", "OK", "OK", "NG", "NG"]
tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
print(f"labels 無し: tn={tn} fp={fp} fn={fn} tp={tp}")
tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=["OK", "NG"]).ravel()
print(f"labels 指定: tn={tn} fp={fp} fn={fn} tp={tp}")

# ---- 実験 3: 8 件のスコアで閾値を 0.3・0.5・0.7 に動かす ----
y_true = [0, 0, 0, 0, 1, 1, 1, 1]
y_score = [0.1, 0.3, 0.4, 0.8, 0.2, 0.6, 0.7, 0.9]
for threshold in [0.3, 0.5, 0.7]:
    y_pred = [int(score >= threshold) for score in y_score]
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
    precision = precision_score(y_true, y_pred, zero_division=0)
    recall = recall_score(y_true, y_pred, zero_division=0)
    print(f"{threshold:.1f}: TN={tn} FP={fp} FN={fn} TP={tp} precision={precision:.2f} recall={recall:.2f}")

fig, ax = plt.subplots(figsize=(8, 2.6))
for label, yy, color, name in [(0, 0.0, BLUE, "正解が陰性"), (1, 0.0, RED, "正解が陽性")]:
    xs = [s for s, t in zip(y_score, y_true) if t == label]
    ax.scatter(xs, [yy] * len(xs), s=160, color=color, zorder=3, label=name,
               marker="o" if label == 1 else "s", edgecolor="#ffffff")
for s in y_score:
    ax.text(s, -0.32, f"{s:.1f}", ha="center", fontsize=9, color="#555555", zorder=4,
            bbox={"facecolor": "#ffffff", "edgecolor": "none", "pad": 1})
notes = {0.3: "P 0.50 / R 0.75", 0.5: "P 0.75 / R 0.75", 0.7: "P 0.67 / R 0.50"}
for t, txt in notes.items():
    ax.axvline(t, color=INK, linestyle="--", linewidth=1, zorder=1)
    ax.text(t, 0.62, f"閾値 {t}\n{txt}", ha="center", fontsize=9, color=INK,
            bbox={"facecolor": "#ffffff", "edgecolor": "none", "pad": 1})
ax.set_xlim(0, 1)
ax.set_ylim(-0.5, 1.0)
ax.set_yticks([])
ax.spines["left"].set_visible(False)
ax.set_xlabel("スコア（破線の上か右にある点を陽性と判定。P は Precision、R は Recall）")
ax.legend(loc="lower left", frameon=False, ncol=2, bbox_to_anchor=(0, 1.0))
fig.tight_layout()
save(fig, "confusion-matrix_toy.webp")

# ---- 実験 4: 見逃し 10、誤報 1 のコストで閾値を決める ----
C_FN, C_FP = 10, 1


def cost(y_true, y_pred):
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    return C_FN * fn + C_FP * fp


neg_cost = make_scorer(lambda yt, yp: -cost(yt, yp))
grid = np.round(np.arange(0.02, 0.981, 0.01), 2)
curves, fixed, tuned_cost, tuned_thr = [], {"0.5": [], "1/11": []}, [], []
for seed in range(20):
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.5, stratify=y, random_state=seed)
    y_tr, y_te = 1 - y_tr, 1 - y_te  # 悪性を 1（陽性）に付け替える
    base = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))
    p = base.fit(X_tr, y_tr).predict_proba(X_te)[:, 1]  # 悪性の確率
    curves.append([cost(y_te, (p >= t).astype(int)) for t in grid])
    fixed["0.5"].append(cost(y_te, (p >= 0.5).astype(int)))
    fixed["1/11"].append(cost(y_te, (p >= 1 / 11).astype(int)))
    tuned = TunedThresholdClassifierCV(base, scoring=neg_cost,
                                       cv=StratifiedKFold(5, shuffle=True, random_state=0)).fit(X_tr, y_tr)
    tuned_thr.append(tuned.best_threshold_)
    tuned_cost.append(cost(y_te, tuned.predict(X_te)))
mean_curve = np.mean(curves, axis=0)
print(f"20 回の平均コスト: 閾値 0.5 {np.mean(fixed['0.5']):.1f}、閾値 1/11 {np.mean(fixed['1/11']):.1f}、"
      f"TunedThresholdClassifierCV {np.mean(tuned_cost):.1f}（選んだ閾値の中央値 {np.median(tuned_thr):.2f}）")
print(f"TunedThresholdClassifierCV が選んだ閾値: 最小 {min(tuned_thr):.2f}、最大 {max(tuned_thr):.2f}")
print(f"平均コストが最小の閾値 {grid[mean_curve.argmin()]:.2f}（{mean_curve.min():.1f}）")
print(f"seed 0 だけ: 閾値 0.5 {fixed['0.5'][0]}、閾値 1/11 {fixed['1/11'][0]}")

fig, ax = plt.subplots(figsize=(7, 3.6))
for c in curves:
    ax.plot(grid, c, color="#dddddd", linewidth=0.8)
ax.plot(grid, mean_curve, color=INK, linewidth=2, label="20 回の平均")
ax.axvline(0.5, color=GRAY, linestyle=":", linewidth=1.2)
ax.text(0.51, 125, f"0.5\n平均 {np.mean(fixed['0.5']):.1f}", fontsize=9, color="#555555")
ax.axvline(1 / 11, color=RED, linestyle="--", linewidth=1.2)
ax.text(1 / 11 + 0.01, 125, f"1/11（約 0.09）\n平均 {np.mean(fixed['1/11']):.1f}",
        fontsize=9, color=RED)
ax.set_xlabel("悪性の確率に掛ける閾値")
ax.set_ylabel("コスト（見逃し × 10 ＋ 誤報 × 1）")
ax.set_ylim(0, 160)
ax.legend(loc="upper center", bbox_to_anchor=(0.3, 1.0), frameon=False)
fig.tight_layout()
save(fig, "confusion-matrix_cost.webp")
