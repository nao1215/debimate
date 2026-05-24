"""ROC-AUC / PR-AUC ノート用の図を生成するスクリプト。

実行: cd projects/ml && uv run python scripts/notes/roc-pr-auc_gen.py

生成画像は projects/ml/notes/ml/roc-pr-auc/ に直接保存される。
"""
import os

import matplotlib.pyplot as plt
import numpy as np
from sklearn.datasets import make_classification
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    precision_recall_curve,
    roc_auc_score,
    roc_curve,
)

COLOR_BLUE = "#7aa6c2"
COLOR_RED = "#e15759"
COLOR_GREEN = "#59a14f"

NOTE_DIR = os.path.expanduser(
    "~/ghq/github.com/nao1215/debimate/projects/ml/notes/ml/roc-pr-auc"
)
os.makedirs(NOTE_DIR, exist_ok=True)


def save(name: str) -> None:
    plt.savefig(os.path.join(NOTE_DIR, name), bbox_inches="tight")
    plt.close()


def base_dataset(seed: int = 0):
    """十分な数の陽性・陰性を持つ basis データを作って学習する。"""
    X, y = make_classification(
        n_samples=40_000,
        n_features=10,
        n_informative=5,
        n_redundant=2,
        weights=[0.5, 0.5],
        flip_y=0.02,
        class_sep=1.0,
        random_state=seed,
    )
    model = LogisticRegression(max_iter=1000, solver="lbfgs").fit(X, y)
    scores = model.predict_proba(X)[:, 1]
    return y, scores


def subsample(y_all, scores_all, pos_ratio: float, n_total: int = 10_000,
              seed: int = 0):
    """陽性・陰性を所望の比率で取り直す。モデルの判別性能は変えない。"""
    rng = np.random.default_rng(seed)
    n_pos = int(n_total * pos_ratio)
    n_neg = n_total - n_pos
    pos_idx = np.where(y_all == 1)[0]
    neg_idx = np.where(y_all == 0)[0]
    pos_pick = rng.choice(pos_idx, size=n_pos, replace=False)
    neg_pick = rng.choice(neg_idx, size=n_neg, replace=False)
    keep = np.concatenate([pos_pick, neg_pick])
    return y_all[keep], scores_all[keep]


y_all, scores_all = base_dataset()

ratios = [
    (0.5, "Balanced 50:50", COLOR_BLUE),
    (0.1, "Mild 90:10", COLOR_GREEN),
    (0.02, "Extreme 98:2", COLOR_RED),
]
datasets = [
    (subsample(y_all, scores_all, r), name, c, r)
    for r, name, c in ratios
]


# --- 図1: 不均衡度別の ROC 曲線 ---
plt.figure(figsize=(6, 5))
for (y, ys), name, c, _ in datasets:
    fpr, tpr, _ = roc_curve(y, ys)
    auc = roc_auc_score(y, ys)
    plt.plot(fpr, tpr, color=c, label=f"{name}  AUC={auc:.3f}")
plt.plot([0, 1], [0, 1], "k--", alpha=0.3, label="Random  AUC=0.500")
plt.xlabel("FPR (False Positive Rate)")
plt.ylabel("TPR (True Positive Rate)")
plt.title("ROC curves stay similar across class ratios")
plt.legend(loc="lower right", fontsize=9)
plt.tight_layout()
save("roc-pr-auc_roc_imbalance.svg")


# --- 図2: 同じデータでの PR 曲線比較 ---
plt.figure(figsize=(6, 5))
for (y, ys), name, c, ratio in datasets:
    precision, recall, _ = precision_recall_curve(y, ys)
    pr_auc = average_precision_score(y, ys)
    plt.plot(recall, precision, color=c,
             label=f"{name}  PR-AUC={pr_auc:.3f}")
    # 各データセットの陽性比率 = ランダム時の PR ベースライン
    plt.axhline(ratio, color=c, linestyle=":", alpha=0.5)
plt.xlabel("Recall")
plt.ylabel("Precision")
plt.title("PR curves drop sharply as positives become rare")
plt.legend(loc="lower left", fontsize=9)
plt.tight_layout()
save("roc-pr-auc_pr_imbalance.svg")


# --- 図3: ROC と PR のランダム基準の非対称性 ---
plt.figure(figsize=(6, 4))
ratios_x = np.linspace(0.001, 0.5, 200)
plt.plot(ratios_x, ratios_x, color=COLOR_RED, linewidth=2,
         label="PR-AUC random = positive ratio")
plt.axhline(0.5, color=COLOR_BLUE, linestyle="--", linewidth=2,
            label="ROC-AUC random = 0.5 (constant)")
plt.xlabel("Positive class ratio")
plt.ylabel("Random baseline of the metric")
plt.title("Random baselines differ: ROC fixed at 0.5, PR moves with ratio")
plt.legend()
plt.tight_layout()
save("roc-pr-auc_baseline.svg")


# --- 図4: ROC + PR の基本並列図 (50:50 のケース) ---
(y, ys), _, _, _ = datasets[0]
fpr, tpr, _ = roc_curve(y, ys)
precision, recall, _ = precision_recall_curve(y, ys)
fig, axes = plt.subplots(1, 2, figsize=(8, 3))
axes[0].plot(fpr, tpr, color=COLOR_BLUE)
axes[0].plot([0, 1], [0, 1], "k--", alpha=0.3)
axes[0].set_title("ROC")
axes[0].set_xlabel("FPR")
axes[0].set_ylabel("TPR")
axes[1].plot(recall, precision, color=COLOR_RED)
axes[1].set_title("PR")
axes[1].set_xlabel("Recall")
axes[1].set_ylabel("Precision")
plt.tight_layout()
save("roc-pr-auc_curves.svg")


print("ROC-AUC vs PR-AUC across class ratios:")
for (y, ys), name, _, ratio in datasets:
    print(
        f"  {name} (positive={ratio * 100:.1f}%):  "
        f"ROC-AUC={roc_auc_score(y, ys):.3f}  "
        f"PR-AUC={average_precision_score(y, ys):.3f}"
    )
