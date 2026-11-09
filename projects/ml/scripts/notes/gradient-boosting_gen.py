"""GradientBoosting ノート用の図を生成するスクリプト。

実行: cd projects/ml && uv run python scripts/notes/gradient-boosting_gen.py
"""
from pathlib import Path

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

NOTE_DIR = Path(__file__).resolve().parents[2] / "notes/ml/gradient-boosting"
NOTE_DIR.mkdir(parents=True, exist_ok=True)


def save(name: str) -> None:
    plt.savefig(NOTE_DIR / name, bbox_inches="tight")
    # Remove trailing whitespace so `git diff --check` passes.
    _svg_path = Path(NOTE_DIR / name)
    if _svg_path.suffix == ".svg":
        _svg_path.write_text("\n".join(line.rstrip() for line in _svg_path.read_text().splitlines()) + "\n")
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
# test は最後の評価だけに使い、本数や学習率の比較は検証データで行う。
X2, y2 = make_classification(
    n_samples=2000, n_features=10, n_informative=6, n_redundant=2,
    flip_y=0.05, random_state=0,
)
X_tr, X_te, y_tr, y_te = train_test_split(X2, y2, test_size=0.3, random_state=0)
# GradientBoostingClassifier(validation_fraction=0.2, random_state=0) が
# 内部で行う分割と同じ分割（stratify=y）で、学習用と検証用に分ける。
X_fit, X_val, y_fit, y_val = train_test_split(
    X_tr, y_tr, test_size=0.2, random_state=0, stratify=y_tr,
)

learning_rates = [0.01, 0.1, 0.5]
colors = [COLOR_BLUE, COLOR_GREEN, COLOR_RED]
plt.figure(figsize=(7, 4.5))
for lr, color in zip(learning_rates, colors):
    gb = GradientBoostingClassifier(
        n_estimators=300, learning_rate=lr, max_depth=3, random_state=0,
    )
    gb.fit(X_fit, y_fit)
    val_losses = [log_loss(y_val, p) for p in gb.staged_predict_proba(X_val)]
    best = int(np.argmin(val_losses)) + 1
    print(f"learning_rate={lr}: best iter={best}, "
          f"min val loss={min(val_losses):.3f}, val loss at 300={val_losses[-1]:.3f}")
    plt.plot(range(1, len(val_losses) + 1), val_losses, color=color,
             label=f"learning_rate = {lr}")
plt.xlabel("n_estimators (iteration)")
plt.ylabel("Validation log loss")
plt.title("learning_rate trades off speed vs final performance")
plt.legend()
plt.grid(alpha=0.2)
plt.tight_layout()
save("gradient-boosting_learning_rate.svg")


# --- 図4: train / validation loss と早期停止 ---
# 早期停止は検証データの loss で決め、test は止めたモデルの評価に 1 回だけ使う。
es = GradientBoostingClassifier(
    n_estimators=500, learning_rate=0.1, max_depth=4, random_state=0,
    validation_fraction=0.2, n_iter_no_change=20,
).fit(X_tr, y_tr)
stop_iter = es.n_estimators_

# 曲線を描くため、同じ分割・同じ設定で 500 本まで学習したモデルも作る。
full = GradientBoostingClassifier(
    n_estimators=500, learning_rate=0.1, max_depth=4, random_state=0,
).fit(X_fit, y_fit)

train_losses, val_losses = [], []
for proba_fit, proba_val in zip(
    full.staged_predict_proba(X_fit), full.staged_predict_proba(X_val)
):
    train_losses.append(log_loss(y_fit, proba_fit))
    val_losses.append(log_loss(y_val, proba_val))
best_val_iter = int(np.argmin(val_losses)) + 1

plt.figure(figsize=(7, 4.5))
plt.plot(range(1, 501), train_losses, color=COLOR_BLUE, label="train")
plt.plot(range(1, 501), val_losses, color=COLOR_ORANGE, label="validation")
plt.scatter([best_val_iter], [val_losses[best_val_iter - 1]], color=COLOR_ORANGE,
            zorder=3, label=f"lowest validation loss (iter={best_val_iter})")
plt.axvline(stop_iter, color="gray", linestyle="--", alpha=0.7,
            label=f"early stopping (n_iter_no_change=20, iter={stop_iter})")
plt.xlabel("n_estimators")
plt.ylabel("Log loss")
plt.title("Train keeps falling, validation bottoms out then rises")
plt.legend()
plt.grid(alpha=0.2)
plt.tight_layout()
save("gradient-boosting_early_stopping.svg")

print(f"Lowest validation loss: iter={best_val_iter}, "
      f"{val_losses[best_val_iter - 1]:.3f}")
print(f"Early stopping stopped at: {stop_iter}")
print(f"Validation loss at 500: {val_losses[-1]:.3f}")
print(f"Test loss (early stopped, {stop_iter} trees): "
      f"{log_loss(y_te, es.predict_proba(X_te)):.3f}")
print(f"Test loss (500 trees): {log_loss(y_te, full.predict_proba(X_te)):.3f}")
