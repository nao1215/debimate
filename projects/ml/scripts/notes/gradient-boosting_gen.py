"""GradientBoosting ノート用の図を生成するスクリプト。

実行: cd projects/ml && uv run python scripts/notes/gradient-boosting_gen.py
"""
import os

import matplotlib.pyplot as plt
import numpy as np
from sklearn.datasets import make_classification
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor
from sklearn.metrics import log_loss
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeRegressor

COLOR_BLUE = "#7aa6c2"
COLOR_RED = "#e15759"
COLOR_GREEN = "#59a14f"
COLOR_ORANGE = "#f28e2b"

NOTE_DIR = os.path.expanduser(
    "~/ghq/github.com/nao1215/debimate/projects/ml/notes/ml/gradient-boosting"
)
os.makedirs(NOTE_DIR, exist_ok=True)


def save(name: str) -> None:
    plt.savefig(os.path.join(NOTE_DIR, name), bbox_inches="tight")
    plt.close()


rng = np.random.default_rng(0)


# --- 図1: 弱学習器を逐次足して関数を近似していく様子 ---
# 1D 回帰問題で、浅い木を 1, 3, 10, 50 本足したときの予測曲線を重ねる。
X1 = np.linspace(-3, 3, 200).reshape(-1, 1)
y1_true = np.sin(X1.ravel()) * 1.5 + 0.2 * X1.ravel() ** 2
y1_noisy = y1_true + 0.3 * rng.standard_normal(200)

fig, axes = plt.subplots(1, 4, figsize=(13, 3.2))
for ax, n_estimators in zip(axes, [1, 3, 10, 50]):
    gb = GradientBoostingRegressor(
        n_estimators=n_estimators, learning_rate=0.5, max_depth=3,
        random_state=0,
    )
    gb.fit(X1, y1_noisy)
    y_pred = gb.predict(X1)
    ax.scatter(X1, y1_noisy, alpha=0.3, s=18, color="gray", label="data")
    ax.plot(X1, y1_true, color=COLOR_GREEN, linestyle="--", linewidth=1.5,
            label="true")
    ax.plot(X1, y_pred, color=COLOR_RED, linewidth=2.2, label="prediction")
    ax.set_title(f"n_estimators = {n_estimators}")
    ax.set_xlabel("x")
    if ax is axes[0]:
        ax.set_ylabel("y")
        ax.legend(fontsize=8, loc="upper left")
plt.tight_layout()
save("gradient-boosting_progressive_fit.svg")


# --- 図2: 残差 → 次の木 の流れを可視化 ---
# 1 段目: 元データ + 1 本目の予測
# 2 段目: 残差 + 2 本目の予測
gb1 = GradientBoostingRegressor(n_estimators=1, learning_rate=1.0, max_depth=2,
                                random_state=0).fit(X1, y1_noisy)
pred1 = gb1.predict(X1)
residual = y1_noisy - pred1

# 2 本目の木は残差を学習する
stump2 = DecisionTreeRegressor(max_depth=2, random_state=0).fit(X1, residual)
pred_residual = stump2.predict(X1)
pred_combined = pred1 + pred_residual

fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
axes[0].scatter(X1, y1_noisy, alpha=0.4, s=18, color=COLOR_BLUE, label="data")
axes[0].plot(X1, pred1, color=COLOR_RED, linewidth=2,
             label="tree #1 prediction")
axes[0].set_title("Step 1: first weak learner")
axes[0].set_xlabel("x")
axes[0].set_ylabel("y")
axes[0].legend(fontsize=9)

axes[1].scatter(X1, residual, alpha=0.4, s=18, color=COLOR_ORANGE,
                label="residual (y - pred1)")
axes[1].plot(X1, pred_residual, color=COLOR_RED, linewidth=2,
             label="tree #2 fits residual")
axes[1].axhline(0, color="gray", linewidth=0.6)
axes[1].set_title("Step 2: second tree fits the residual")
axes[1].set_xlabel("x")
axes[1].set_ylabel("residual")
axes[1].legend(fontsize=9)
plt.tight_layout()
save("gradient-boosting_residual.svg")


# --- 図3: learning_rate のトレードオフ ---
X2, y2 = make_classification(
    n_samples=2000, n_features=10, n_informative=6, n_redundant=2,
    flip_y=0.05, random_state=0,
)
X_tr, X_te, y_tr, y_te = train_test_split(X2, y2, test_size=0.3, random_state=0)

learning_rates = [0.01, 0.1, 0.5]
colors = [COLOR_BLUE, COLOR_GREEN, COLOR_RED]
plt.figure(figsize=(7, 4.5))
for lr, color in zip(learning_rates, colors):
    gb = GradientBoostingClassifier(
        n_estimators=300, learning_rate=lr, max_depth=3, random_state=0,
    )
    gb.fit(X_tr, y_tr)
    test_losses = []
    for proba in gb.staged_predict_proba(X_te):
        test_losses.append(log_loss(y_te, proba))
    plt.plot(range(1, len(test_losses) + 1), test_losses, color=color,
             label=f"learning_rate = {lr}")
plt.xlabel("n_estimators (iteration)")
plt.ylabel("Test log loss")
plt.title("learning_rate trades off speed vs final performance")
plt.legend()
plt.grid(alpha=0.2)
plt.tight_layout()
save("gradient-boosting_learning_rate.svg")


# --- 図4: train / test loss と早期停止のイメージ ---
gb = GradientBoostingClassifier(
    n_estimators=500, learning_rate=0.1, max_depth=4, random_state=0,
).fit(X_tr, y_tr)

train_losses, test_losses = [], []
for proba_tr, proba_te in zip(
    gb.staged_predict_proba(X_tr), gb.staged_predict_proba(X_te)
):
    train_losses.append(log_loss(y_tr, proba_tr))
    test_losses.append(log_loss(y_te, proba_te))

best_iter = int(np.argmin(test_losses)) + 1
plt.figure(figsize=(7, 4.5))
plt.plot(range(1, 501), train_losses, color=COLOR_BLUE, label="train")
plt.plot(range(1, 501), test_losses, color=COLOR_RED, label="test")
plt.axvline(best_iter, color="gray", linestyle="--", alpha=0.7,
            label=f"early stopping point (iter={best_iter})")
plt.xlabel("n_estimators")
plt.ylabel("Log loss")
plt.title("Train keeps falling, test bottoms out then rises")
plt.legend()
plt.grid(alpha=0.2)
plt.tight_layout()
save("gradient-boosting_early_stopping.svg")


print(f"Best iteration (lowest test loss): {best_iter}")
print(f"Test loss at best iter: {test_losses[best_iter - 1]:.4f}")
print(f"Test loss at final iter (500): {test_losses[-1]:.4f}")
