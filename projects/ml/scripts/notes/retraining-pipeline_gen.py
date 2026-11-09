"""retraining-pipeline ノート用の図を生成するスクリプト。

実行: cd projects/ml && uv run python scripts/notes/retraining-pipeline_gen.py

実験と費用のモデルは本文のコードと同じです。図の描画だけを足しています。
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from sklearn.linear_model import LogisticRegression

COLOR_GRAY = "#888888"
COLOR_ORANGE = "#d9822b"
COLOR_BLUE = "#4c78a8"
COLOR_BLACK = "#333333"

NOTE_DIR = Path(__file__).resolve().parents[2] / "notes" / "mlops" / "retraining-pipeline"


def save(name: str) -> None:
    plt.savefig(NOTE_DIR / name, bbox_inches="tight")
    plt.close()


# ============================================================
# Fig 1: 再学習の方法ごとの accuracy の推移（本文の実験と同じ）
# ============================================================
rng = np.random.default_rng(0)
DAYS, N_PER_DAY, NOISE = 365, 500, 0.05
DEG_PER_DAY = 0.2  # 正解の境界が 1 日に 0.2 度ずつ回る


def make_day(day):
    x = rng.normal(size=(N_PER_DAY, 2))
    theta = np.deg2rad(DEG_PER_DAY * day)
    w = np.array([np.cos(theta), np.sin(theta)])
    y = (x @ w > 0).astype(int)
    flip = rng.random(N_PER_DAY) < NOISE  # ラベルの 5% は誤り
    y[flip] = 1 - y[flip]
    return x, y


data = [make_day(d) for d in range(DAYS)]


def fit(days):
    x = np.vstack([data[d][0] for d in days])
    y = np.concatenate([data[d][1] for d in days])
    return LogisticRegression().fit(x, y)


def run(policy):
    model = fit(range(30))  # 最初の 30 日分で学習し、30 日目から本番で使う
    acc = []
    for day in range(30, DAYS):
        if policy != "none" and day % 30 == 0 and day > 30:
            past = range(day) if policy == "all" else range(day - 30, day)
            model = fit(past)
        x, y = data[day]
        acc.append(model.score(x, y))
    return np.array(acc)


results = {p: run(p) for p in ["none", "all", "window"]}
for policy, acc in results.items():
    print(f"{policy:6s} 平均 {acc.mean():.3f}  最後の 30 日 {acc[-30:].mean():.3f}"
          f"  0.85 未満の日数 {np.sum(acc < 0.85)}")
print("再学習なしの 1 日あたりの傾き:",
      round(np.polyfit(np.arange(30, DAYS), results["none"], 1)[0], 5))

days = np.arange(30, DAYS)
plt.figure(figsize=(9, 4))
plt.plot(days, results["none"], color=COLOR_GRAY, lw=1.2, label="no retraining")
plt.plot(days, results["all"], color=COLOR_ORANGE, lw=1.2,
         label="retrain every 30 days (all past data)")
plt.plot(days, results["window"], color=COLOR_BLUE, lw=1.2,
         label="retrain every 30 days (last 30 days)")
plt.axhline(0.85, color=COLOR_BLACK, lw=1, ls="--", label="SLO (0.85)")
plt.xlabel("day")
plt.ylabel("accuracy of the day")
plt.ylim(0.5, 1.0)
plt.legend(loc="lower left", fontsize=9)
plt.grid(True, alpha=0.25)
plt.tight_layout()
save("retraining_decay_vs_retrain.svg")


# ============================================================
# Fig 2: 再学習の間隔と 1 か月あたりの費用（本文のコードと同じ）
# ============================================================
C = 2_000   # 再学習 1 回の費用（計算資源と確認の人件費、ドル）
N = 10_000  # 1 日の予測件数
L = 5       # 予測を 1 件誤った時の損失（ドル）
r = 0.001   # 再学習から 1 日経つごとに下がる accuracy（前節の実験）


def monthly_cost(T, C=C):
    retrain = 30 * C / T            # 30 日で 30 / T 回の再学習
    stale = 30 * N * L * r * T / 2  # 周期内の accuracy 低下は平均 r * T / 2
    return retrain, stale


T = np.arange(1, 91)
retrain, stale = monthly_cost(T)
total = retrain + stale
best = T[np.argmin(total)]
print("費用が最小になる間隔:", best, "日")

plt.figure(figsize=(9, 4))
plt.plot(T, retrain, color=COLOR_BLUE, lw=2, label="retraining cost")
plt.plot(T, stale, color=COLOR_ORANGE, lw=2, label="cost of wrong predictions")
plt.plot(T, total, color=COLOR_BLACK, lw=2.5, label="total")
plt.axvline(best, color=COLOR_GRAY, ls="--", lw=1, label=f"minimum: {best} days")
plt.xscale("log")
plt.ylim(0, 80_000)
plt.xlabel("retraining interval T (days, log scale)")
plt.ylabel("cost per 30 days (USD)")
plt.legend(loc="upper center", fontsize=9)
plt.grid(True, alpha=0.25)
plt.tight_layout()
save("retraining_cost_tradeoff.svg")
