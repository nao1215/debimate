"""混同行列ノート用の図を生成するスクリプト。

実行: cd projects/ml && uv run python scripts/notes/confusion-matrix_gen.py

生成画像は projects/ml/notes/ml/confusion-matrix/ に直接保存される。
本文に載せる件数は、このスクリプトの print 出力から写す。
"""
import os

import matplotlib.pyplot as plt
import numpy as np
from sklearn.datasets import make_classification
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix
from sklearn.model_selection import train_test_split

plt.rcParams.update({"font.size": 12, "svg.hashsalt": "debimate"})

COLOR_BLUE = "#7aa6c2"
COLOR_RED = "#e15759"
COLOR_GREEN = "#59a14f"
COLOR_ORANGE = "#f28e2b"
COLOR_GRAY = "#999999"

NOTE_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "notes", "ml", "confusion-matrix"
)
os.makedirs(NOTE_DIR, exist_ok=True)


def save(name: str) -> None:
    plt.savefig(os.path.join(NOTE_DIR, name), bbox_inches="tight")
    plt.close()


# 陽性 10% の不均衡データでロジスティック回帰を学習し、テストデータで評価する
X, y = make_classification(
    n_samples=4000,
    n_features=10,
    n_informative=4,
    n_redundant=2,
    weights=[0.9, 0.1],
    flip_y=0.02,
    class_sep=0.8,
    random_state=0,
)
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.5, stratify=y, random_state=0
)
model = LogisticRegression(max_iter=1000).fit(X_train, y_train)
scores = model.predict_proba(X_test)[:, 1]

THRESHOLDS = (0.5, 0.2)


def cells(threshold: float):
    pred = (scores >= threshold).astype(int)
    return confusion_matrix(y_test, pred, labels=[0, 1])


# --- 図1: 閾値 0.5 と 0.2 の混同行列 ---
fig, axes = plt.subplots(1, 2, figsize=(8, 3.6))
names = [["TN", "FP"], ["FN", "TP"]]
for ax, t in zip(axes, THRESHOLDS):
    cm = cells(t)
    vmax = np.log10(len(y_test))
    ax.imshow(np.log10(cm + 1), cmap="Blues", vmin=0, vmax=vmax)
    for i in range(2):
        for j in range(2):
            dark = np.log10(cm[i, j] + 1) > 0.55 * vmax
            ax.text(j, i, f"{names[i][j]}\n{cm[i, j]}", ha="center", va="center",
                    fontsize=13, color="white" if dark else "black")
    ax.set_xticks([0, 1], ["pred 0", "pred 1"])
    ax.set_yticks([0, 1], ["true 0", "true 1"])
    tn, fp, fn, tp = cm.ravel()
    ax.set_title(f"threshold={t}  P={tp / (tp + fp):.2f} R={tp / (tp + fn):.2f}",
                 fontsize=11)
plt.tight_layout()
save("confusion-matrix_heatmaps.svg")


# --- 図2: 閾値を動かした時の FP と FN の件数 ---
grid = np.round(np.arange(0.10, 0.901, 0.01), 2)
fps, fns = [], []
for t in grid:
    tn, fp, fn, tp = cells(t).ravel()
    fps.append(fp)
    fns.append(fn)
plt.figure(figsize=(6, 3.6))
plt.plot(grid, fps, color=COLOR_RED, label="FP (false alarm)")
plt.plot(grid, fns, color=COLOR_BLUE, label="FN (missed)")
for t in THRESHOLDS:
    plt.axvline(t, color=COLOR_GRAY, linestyle=":", linewidth=1)
plt.xlabel("threshold")
plt.ylabel("count (test, n=2000)")
plt.title("Lowering the threshold trades FN for FP", fontsize=11)
plt.legend()
plt.tight_layout()
save("confusion-matrix_threshold_sweep.svg")


print(f"test: n={len(y_test)} positive={int(y_test.sum())}")
for t in THRESHOLDS + (0.1, 0.3):
    tn, fp, fn, tp = cells(t).ravel()
    print(f"{t}: TN={tn} FP={fp} FN={fn} TP={tp} "
          f"precision={tp / (tp + fp):.2f} recall={tp / (tp + fn):.2f} "
          f"accuracy={(tp + tn) / len(y_test):.3f}")
print(f"all-negative accuracy={1 - y_test.mean():.3f}")
