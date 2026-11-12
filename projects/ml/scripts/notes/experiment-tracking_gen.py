"""experiment-tracking ノートの実験と図を生成するスクリプト。

本文に載せた実験（MLflow で 1 run を記録する、24 設定の探索を seed を変えて 10 回行い 1 位の
設定の順位を測る、seed の数を増やした時の選び方の当たり具合、データを上書きした時の記録の比較）
を同じ順に実行し、出力を標準出力に、図を Page Bundle に WebP で保存する。

MLflow はプロジェクトの依存に入れていないので、実行時に足す:
    cd projects/ml && uv run --with mlflow==3.18.0 python scripts/notes/experiment-tracking_gen.py
MLflow の記録（mlflow.db と artifacts）は環境変数 EXP_WORK のディレクトリに置く（無ければ一時ディレクトリ）。
確認した版: MLflow 3.18.0、scikit-learn 1.9.1、NumPy 2.5.4
"""
import os
import tempfile
import warnings
from io import BytesIO
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

NOTE_DIR = Path(__file__).resolve().parents[2] / "notes" / "mlops" / "experiment-tracking"
WORK = Path(os.environ.get("EXP_WORK") or tempfile.mkdtemp(prefix="exp-tracking-"))
WORK.mkdir(parents=True, exist_ok=True)
os.chdir(WORK)
os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")
warnings.filterwarnings("ignore")

plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10,
                     "axes.spines.top": False, "axes.spines.right": False})
BLUE, RED, GREEN, INK, GRAY = "#7aa6c2", "#e15759", "#59a14f", "#333333", "#bbbbbb"


def save(fig, name):
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight", facecolor="#ffffff")
    plt.close(fig)
    buf.seek(0)
    Image.open(buf).convert("RGB").save(NOTE_DIR / name, "WEBP", quality=90, method=6)


# ============================================================
# 実験 1: MLflow で 1 run を記録する
# ============================================================
import mlflow
import pandas as pd
from sklearn.datasets import load_breast_cancer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split

mlflow.set_tracking_uri("sqlite:///mlflow.db")
mlflow.set_experiment("breast-cancer-rf")

data = load_breast_cancer(as_frame=True)
df = data.frame                                    # 569 行。30 列の特徴量と target
train_df, valid_df = train_test_split(df, test_size=0.25, random_state=0, stratify=df["target"])
X_train, y_train = train_df.drop(columns="target"), train_df["target"]
X_valid, y_valid = valid_df.drop(columns="target"), valid_df["target"]

with mlflow.start_run(run_name="rf-baseline") as run:
    params = {"n_estimators": 100, "max_depth": 6, "max_features": 0.3,
              "min_samples_leaf": 1, "random_state": 0}
    mlflow.log_params(params)
    mlflow.log_input(mlflow.data.from_pandas(train_df, name="train", targets="target"),
                     context="training")
    model = RandomForestClassifier(**params).fit(X_train, y_train)
    auc = roc_auc_score(y_valid, model.predict_proba(X_valid)[:, 1])
    mlflow.log_metric("val_auc", auc)
    # MLflow 3.18.0 の既定の保存形式 skops に、決定木の型を読み込んでよいと伝える
    mlflow.sklearn.log_model(model, name="model",
                             skops_trusted_types=["sklearn.tree._tree.Tree"])

r = mlflow.get_run(run.info.run_id)
print("run_id:", r.info.run_id)
print("params:", r.data.params)
print("metrics:", {k: round(v, 4) for k, v in r.data.metrics.items()})
print("dataset:", [(d.dataset.name, d.dataset.digest) for d in r.inputs.dataset_inputs])

# skops_trusted_types を外すと保存の時点で止まることを確かめる
try:
    with mlflow.start_run(run_name="no-trusted-types"):
        mlflow.sklearn.log_model(model, name="model")
except Exception as e:  # noqa: BLE001
    print("skops_trusted_types なし:", type(e).__name__, str(e).splitlines()[0][:120])

# ============================================================
# 実験 2: 24 設定の探索を、seed だけ変えて 10 回行う
# ============================================================
rng = np.random.default_rng(0)
settings = [{"n_estimators": int(rng.choice([10, 20, 50, 100, 200])),
             "max_depth": [2, 3, 4, 6, 8, None][rng.integers(6)],
             "max_features": float(rng.choice([0.1, 0.3, 0.5, 1.0])),
             "min_samples_leaf": int(rng.choice([1, 2, 5, 10]))} for _ in range(24)]
SWEEP_SEEDS = range(10)          # 探索に使う seed
TRUTH_SEEDS = range(100, 120)    # 順位の物差しに使う seed（探索には使わない）

mlflow.set_experiment("rf-sweep")
for i, p in enumerate(settings):
    for seed in [*SWEEP_SEEDS, *TRUTH_SEEDS]:
        with mlflow.start_run(run_name=f"setting{i:02d}-seed{seed}"):
            mlflow.log_params({**p, "setting": i, "random_state": seed})
            m = RandomForestClassifier(**p, random_state=seed).fit(X_train, y_train)
            mlflow.log_metric("val_auc", roc_auc_score(y_valid, m.predict_proba(X_valid)[:, 1]))

runs = mlflow.search_runs(experiment_names=["rf-sweep"])
runs["setting"] = runs["params.setting"].astype(int)
runs["seed"] = runs["params.random_state"].astype(int)
auc = runs.pivot(index="setting", columns="seed", values="metrics.val_auc")
truth = auc[list(TRUTH_SEEDS)].mean(axis=1)              # 20 回の平均
true_rank = truth.rank(ascending=False, method="first").astype(int)     # 1 が一番良い

# 1 回の探索 = 24 設定を 1 つの seed で 1 回ずつ。search_runs で val_auc の 1 位を取る
picks = []
for seed in SWEEP_SEEDS:
    top = mlflow.search_runs(experiment_names=["rf-sweep"],
                             filter_string=f"params.random_state = '{seed}'",
                             order_by=["metrics.val_auc DESC"], max_results=1).iloc[0]
    s = int(top["params.setting"])
    picks.append((seed, s, top["metrics.val_auc"], truth[s], true_rank[s]))
    print(f"seed {seed}: 1 位は設定 {s:2d}  val_auc {top['metrics.val_auc']:.4f}"
          f"  20 回の平均 {truth[s]:.4f}  順位 {true_rank[s]:2d} / 24")
print("20 回の平均で 1 位の設定:", int(truth.idxmax()), round(truth.max(), 4),
      " 24 位:", int(truth.idxmin()), round(truth.min(), 4))
for r in (1, 8, 9, 23, 24):
    s = int(true_rank[true_rank == r].index[0])
    print(f"順位 {r:2d}: 設定 {s:2d} {settings[s]}  平均 {truth[s]:.4f}")
print("seed による標準偏差（設定ごとの中央値）:", round(float(auc[list(TRUTH_SEEDS)].std(axis=1).median()), 4))

# 図 1（表紙）: 設定ごとの 10 回分の val_auc と、各探索の 1 位
order = true_rank.sort_values().index          # 同率の設定も true_rank と同じ順に並べる
fig, ax = plt.subplots(figsize=(8, 3.6))
for x, s in enumerate(order):
    ax.scatter([x + 1] * 10, auc.loc[s, list(SWEEP_SEEDS)], s=14, color=GRAY, zorder=2)
    ax.plot([x + 0.65, x + 1.35], [truth[s]] * 2, color=INK, lw=1.6, zorder=3)
for seed, s, v, _, rk in picks:
    ax.scatter(rk, v, s=46, color=RED, zorder=4, edgecolor="white", linewidth=0.6)
ax.set_xticks(range(1, 25))
ax.set_xlabel("設定の順位（別の seed 20 回の平均 val_auc が高い順）")
ax.set_ylabel("val_auc")
ax.set_xlim(0.3, 24.7)
ax.scatter([], [], s=14, color=GRAY, label="探索の 1 run（seed 0〜9）")
ax.plot([], [], color=INK, lw=1.6, label="別の seed 20 回の平均")
ax.scatter([], [], s=46, color=RED, label="その seed の探索で 1 位になった run")
ax.legend(loc="lower left", frameon=False, fontsize=9)
ax.set_title("24 設定の探索を seed だけ変えて 10 回行い、各回の 1 位を赤で示す", fontsize=11, loc="left")
save(fig, "exp_cover.webp")

# ============================================================
# 実験 3: seed を k 個回して平均すると、1 位の選び方はどこまで当たるか
# ============================================================
sweep = auc[list(SWEEP_SEEDS)].to_numpy()
rng = np.random.default_rng(1)
ks = [1, 2, 3, 5, 10]
stats = {}
for k in ks:
    ranks, gaps = [], []
    for _ in range(500):
        cols = rng.choice(10, size=k, replace=False)
        mean_k = sweep[:, cols].mean(axis=1)
        s = int(np.argmax(mean_k))
        ranks.append(true_rank.iloc[s])
        gaps.append(mean_k[s] - truth.iloc[s])            # 見えた値と 20 回の平均の差
    ranks = np.array(ranks)
    stats[k] = (np.mean(ranks >= 9), np.median(ranks), np.mean(gaps))
    print(f"k={k:2d}: 9 位以下を選ぶ割合 {stats[k][0]:.2f}  順位の中央値 {stats[k][1]:.0f}"
          f"  選んだ値と 20 回の平均の差 {stats[k][2]:+.4f}")

fig, axes = plt.subplots(1, 2, figsize=(8, 3))
axes[0].plot(ks, [stats[k][0] for k in ks], "o-", color=RED)
axes[0].set_ylim(0, 0.5)
axes[0].set_xlabel("1 設定あたりの seed の数")
axes[0].set_ylabel("9 位以下の設定を選ぶ割合")
axes[1].plot(ks, [stats[k][2] for k in ks], "o-", color=BLUE)
axes[1].set_ylim(bottom=0)
axes[1].set_xlabel("1 設定あたりの seed の数")
axes[1].set_ylabel("選んだ val_auc と 20 回の平均の差")
for a in axes:
    a.set_xticks(ks)
fig.tight_layout()
save(fig, "exp_seeds.webp")

# ============================================================
# 実験 4: 同じパスのデータを上書きして、同じ params で回し直す
# ============================================================
mlflow.set_experiment("overwrite")
first = train_df.iloc[:320]                      # 最初に届いた 320 行
first.to_csv("train.csv", index=False)


def train_from_csv(run_name):
    with mlflow.start_run(run_name=run_name) as run:
        params = {"n_estimators": 100, "max_depth": 6, "max_features": 0.3,
                  "min_samples_leaf": 1, "random_state": 0, "data_path": "train.csv"}
        mlflow.log_params(params)
        train = pd.read_csv("train.csv")
        mlflow.log_input(mlflow.data.from_pandas(train, source="train.csv", name="train",
                                                 targets="target"), context="training")
        m = RandomForestClassifier(**{k: v for k, v in params.items() if k != "data_path"})
        m.fit(train.drop(columns="target"), train["target"])
        mlflow.log_metric("val_auc", roc_auc_score(y_valid, m.predict_proba(X_valid)[:, 1]))
    return run.info.run_id


run_a = train_from_csv("before")
train_df.to_csv("train.csv", index=False)       # 後から届いた 106 行を足して同じパスに上書き
run_b = train_from_csv("after")

a, b = mlflow.get_run(run_a), mlflow.get_run(run_b)
print("params が同じ:", a.data.params == b.data.params)
for r in (a, b):
    d = r.inputs.dataset_inputs[0].dataset
    print(f"{r.info.run_name:6s} val_auc {r.data.metrics['val_auc']:.4f}  digest {d.digest}"
          f"  profile {d.profile}")

# ============================================================
# 実験 5: 10000 行より後ろの値を直しても digest は変わらない
# ============================================================
import hashlib

from sklearn.datasets import make_classification

Xb, yb = make_classification(n_samples=20000, n_features=5, random_state=0)
big = pd.DataFrame(Xb, columns=[f"x{i}" for i in range(5)]).assign(target=yb)


def digest(frame):
    return mlflow.data.from_pandas(frame, targets="target").digest


def sha256(frame):
    return hashlib.sha256(frame.to_csv(index=False).encode()).hexdigest()[:8]


for row in [50, 15000]:
    fixed = big.copy()
    fixed.loc[row, "target"] = 1 - fixed.loc[row, "target"]   # 1 行のラベルを直す
    print(f"{row:5d} 行目を直す: digest {digest(big)} → {digest(fixed)}"
          f"  sha256 {sha256(big)} → {sha256(fixed)}")
