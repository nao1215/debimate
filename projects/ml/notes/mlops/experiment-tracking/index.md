---
title: "実験管理（experiment tracking） - MLflow で 1 位の run は、seed を変えても 1 位か"
date: 2026-05-26
draft: false
series: ["機械学習ノート", "MLOps"]
tags: ["machine-learning", "mlops"]
weight: 1
topics: ["MLOps"]
---

実験管理（experiment tracking）は、モデルを 1 回学習させるたびに、使った設定とデータ、出てきた評価の値を 1 組にして残す仕組みです。この 1 組を run と呼びます。代表的なツールの [MLflow](https://mlflow.org/) では、Python のコードから run を記録し、後から評価の値が高い順に並べたり、2 つの run を見比べたりできます。

よくある使い方は、[ハイパーパラメータ](../../ml/hyperparameter/)の候補を変えて何十回も学習させ、記録した run を評価の値が高い順に並べて、1 位になったハイパーパラメータの組み合わせを選ぶことです。以下では、この組み合わせを設定と呼びます。モデルの多くは学習の途中で乱数を使い、その乱数の出発点を seed と呼びます。scikit-learn では、seed を `random_state` で渡します。では、seed だけを変えて同じ探索をやり直しても、1 位の設定は 1 位のままでしょうか。

これを調べるために、[scikit-learn](https://scikit-learn.org/stable/) に同梱の [breast_cancer](https://scikit-learn.org/stable/modules/generated/sklearn.datasets.load_breast_cancer.html)（乳がんの診断データ、569 行）を学習用 426 行と検証用 143 行に分け、[ランダムフォレスト](../../ml/random-forest/)の設定を 24 通り用意しました。評価の値には、検証用のデータで測った [ROC-AUC](../../ml/roc-pr-auc/) を使い、以下では val_auc と書きます。ROC-AUC は高いほど良く、0.5 なら当てずっぽうと同じ、1 なら陽性と陰性を完全に分けられることを表します。

24 設定を 1 回ずつ学習させる探索は、seed を 0 から 9 まで変えて 10 回行い、全ての run を MLflow に記録しました。各設定の順位は、探索に使っていない別の seed 20 回の val_auc の平均で決めます。

{{< figure src="exp_cover.webp" alt="横軸は 24 設定を別の seed 20 回の平均 val_auc が高い順に並べた順位、縦軸は val_auc。各設定に灰色の点が 10 個ずつあり、seed 0〜9 の探索で出た値を表す。黒い横線は 20 回の平均で、1 位の 0.978 から 24 位の 0.970 まで右へ下がり、8 位と 9 位の間で一段下がる。各回の探索で 1 位になった run の赤い点は 10 個で、1 位に 2 個、2 位に 2 個、3 位に 1 個、5 位と同率の 6 位に 3 個、14 位に 1 個、23 位に 1 個ある" caption="24 設定の探索を seed だけ変えて 10 回行った時の、各回の 1 位（赤）" align="center" >}}

赤い点が、各回の探索で 1 位になった run です。灰色の点は val_auc が 0.963 から 0.985、20 回の平均は 0.970 から 0.978 の間に入るので、比べているのは 0.001 前後の小さな差です。10 回の探索のうち、20 回の平均で 1 位の設定を選べたのは 2 回だけでした。seed 2 の探索で 1 位になったのは、木が 20 本で深さ 2 までの小さなフォレストで、20 回の平均では 24 設定中 23 位です。

MLflow の記録に誤りはなく、この run の val_auc 0.9816 は実際に出た値です。1 つの設定を 1 回しか学習させないと、記録された値には設定そのものの差と seed による揺れが混ざり、並べても区別できません。

<br>

本記事では、ML を学び始めたエンジニアと、scikit-learn で学習させた結果を MLflow などに記録し始めた人に向けて、次の疑問に答えます。

- 実験管理のツールは、1 回の学習の何を記録するのか。
- 探索の 1 位は、seed を変えるとなぜ入れ替わるのか。
- seed を何個使えば、下位の設定を 1 位に選ばずに済むか。
- 同じ設定で結果が変わった時、記録から原因を追えるか。
- MLflow 以外のツールは何が違うのか。

実験は MLflow 3.18.0 と scikit-learn 1.9.1 で行いました。図を描く処理も含めた完全なコードは [experiment-tracking_gen.py](https://github.com/nao1215/debimate/blob/main/projects/ml/scripts/notes/experiment-tracking_gen.py) にあります。

---

### MLflow で 1 回の学習を記録する

MLflow では、`with mlflow.start_run()` の中で記録の関数を呼ぶと、呼んだ分が 1 つの run にまとまります。設定は `log_params`、評価の値は `log_metric`、学習に使ったデータは `log_input`、学習済みのモデルは `log_model` で記録します。次のコードは、冒頭の探索と同じデータで 1 回学習させ、記録した run を読み出します。

```python
import mlflow
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
print("params:", r.data.params)
print("metrics:", {k: round(v, 4) for k, v in r.data.metrics.items()})
print("dataset:", [(d.dataset.name, d.dataset.digest) for d in r.inputs.dataset_inputs])
```

```text
params: {'n_estimators': '100', 'max_depth': '6', 'max_features': '0.3', 'min_samples_leaf': '1', 'random_state': '0'}
metrics: {'val_auc': 0.9765}
dataset: [('train', '7a02f1b5')]
```

記録先の `sqlite:///mlflow.db` は、カレントディレクトリに作られる、ファイル 1 つで動く DB の SQLite です。読み出した params の値は、数値で渡しても全て文字列になります。`mlflow.data.from_pandas` は pandas の表である DataFrame から [dataset](https://mlflow.org/docs/latest/ml/dataset/) を作り、`log_input` がそれを run に結び付けます。dataset にはデータの中身から計算した 8 文字の digest が付き、後の節でデータの上書きを見つけるのに使います。

<br>

<details>
<summary>log_model に skops_trusted_types を渡している理由</summary>

`skops_trusted_types` は、MLflow 3.18.0 がモデルの保存に既定で使う [skops](https://skops.readthedocs.io/) の形式に、読み込んでよい型を伝える引数です。外すと、ランダムフォレストの中の[決定木](../../ml/decision-tree/)の型を信頼できないとして、保存の時点で MlflowException になりました。

</details>

<br>

MLflow で記録できるものと、本記事で使う関数は次のとおりです。

| 記録するもの | MLflow の関数 | 例 |
|---|---|---|
| 設定（params） | `log_params` | `n_estimators`、`random_state` |
| 評価の値（metrics） | `log_metric` | `val_auc` |
| 学習に使ったデータ | `log_input` | dataset の名前と digest |
| 成果物（artifacts） | `log_model`、`log_artifact` | 学習済みモデル、図 |
| 環境とコードのバージョン | `log_model`、`set_tag` | requirements.txt、Git の commit |

冒頭の探索は、この表のうち設定と評価の値を全ての run で記録していました。それでも seed 2 の探索で 23 位の設定を 1 位に選んだのは、記録が足りなかったからではありません。1 回ずつの値を並べて、一番高い run をそのまま選んだからです。

---

### 探索の 1 位を再実行する

冒頭の探索のコードです。前の節のコードの続きで、`X_train` などの変数をそのまま使います。24 設定は、木の数・深さ・1 回の分岐で見る列の割合・葉に残す最小の行数を乱数で組み合わせて作りました。探索に使う seed 0〜9 に加え、順位を決める seed 100〜119 でも全ての設定を学習させ、同じ実験の中に記録します。

```python
import numpy as np

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
true_rank = truth.rank(ascending=False, method="first").astype(int)

# 1 回の探索 = 24 設定を 1 つの seed で 1 回ずつ。search_runs で val_auc の 1 位を取る
for seed in SWEEP_SEEDS:
    top = mlflow.search_runs(experiment_names=["rf-sweep"],
                             filter_string=f"params.random_state = '{seed}'",
                             order_by=["metrics.val_auc DESC"], max_results=1).iloc[0]
    s = int(top["params.setting"])
    print(f"seed {seed}: 1 位は設定 {s:2d}  val_auc {top['metrics.val_auc']:.4f}"
          f"  20 回の平均 {truth[s]:.4f}  順位 {true_rank[s]:2d} / 24")
```

[`mlflow.search_runs`](https://mlflow.org/docs/latest/api_reference/python_api/mlflow.html#mlflow.search_runs) は、記録した run を pandas の DataFrame で返します。`filter_string` で 1 つの seed の run だけに絞り、`order_by` で val_auc の高い順に並べた先頭が、その回の探索の 1 位です。params は文字列で記録されるので、`random_state` は `'0'` のように引用符で比べます。

```text
seed 0: 1 位は設定  7  val_auc 0.9799  20 回の平均 0.9779  順位  3 / 24
seed 1: 1 位は設定  6  val_auc 0.9788  20 回の平均 0.9778  順位  6 / 24
seed 2: 1 位は設定  1  val_auc 0.9816  20 回の平均 0.9715  順位 23 / 24
seed 3: 1 位は設定 20  val_auc 0.9846  20 回の平均 0.9783  順位  1 / 24
seed 4: 1 位は設定  6  val_auc 0.9805  20 回の平均 0.9778  順位  6 / 24
seed 5: 1 位は設定 21  val_auc 0.9783  20 回の平均 0.9781  順位  2 / 24
seed 6: 1 位は設定 18  val_auc 0.9799  20 回の平均 0.9744  順位 14 / 24
seed 7: 1 位は設定  6  val_auc 0.9814  20 回の平均 0.9778  順位  6 / 24
seed 8: 1 位は設定 21  val_auc 0.9826  20 回の平均 0.9781  順位  2 / 24
seed 9: 1 位は設定 20  val_auc 0.9816  20 回の平均 0.9783  順位  1 / 24
```

seed 1・4・7 で 1 位になった設定 6 は、深さの上限が無い（None）点だけが設定 5（上限 8）と違います。このデータでは木の深さが 8 を超えないので、2 つは同じモデルになり、20 回の平均も同じ値です。順位は 5 位と同率で、番号の小さい設定 5 を 5 位にしています。

同じ設定でも、seed を変えると val_auc は動きます。20 回の val_auc の[標準偏差](../../math/stddev/)を設定ごとに出すと、その[中央値](../../math/median/)は 0.0028 でした。一方で、20 回の平均は 1 位の 0.9783 から 8 位の 0.9775 まで、0.0008 しか違いません。seed による揺れが設定の差の 3 倍以上あるので、1 回ずつの比較では、上位 8 設定の中の順位はほぼ seed で決まります。冒頭の図では、灰色の点の縦の広がりが seed による揺れ、黒い横線の段差が設定の差に当たり、左の 8 設定では点の広がりに比べて横線がほとんど平らです。

9 位から下は平均が 0.9752 以下に下がり、冒頭の図でも横線が一段下がります。それでも seed 2 の 23 位や seed 6 の 14 位のように、下の設定が 1 位を取る回がありました。24 設定もあれば、どれか 1 つは seed のおかげで高い値が出るからです。

<br>

#### 1 位の値は高く出る

出力の val_auc と 20 回の平均を比べると、1 位に選ばれた run の val_auc は、10 回とも、その設定の 20 回の平均より高く出ています。24 個の中から一番高い値を選ぶと、seed で高く出た run が選ばれやすいからです。seed 2 の 1 位の 0.9816 は、その設定の平均 0.9715 より 0.0101 高い値でした。

1 位の run の val_auc を「このモデルの性能」として報告すると、実際より高い値を伝えることになります。検証用の 143 行で何十回も選ぶほど、選んだ値はその 143 行に合わせて高く出ます。性能として伝える値は、別の seed で測り直した平均か、最初に取り分けておき、設定を選ぶのには一度も使っていないテスト用のデータで測った値にします。[交差検証](../../ml/cross-validation/)のノートには、選んだ時のスコア 0.860 が、選ぶのに使っていない分割で測り直す nested CV では 0.809 に下がった例があります。

この実験は検証用の 143 行の分け方を 1 通りに固定し、seed だけを変えています。分け方を変えた時に評価の値がどれだけ動くかも、同じ交差検証のノートで扱っています。

---

### seed を何個使うか

1 つの設定を複数の seed で学習させ、val_auc の平均で比べれば、seed による揺れは小さくなります。seed を何個使えば下位の設定を選ばずに済むかは、記録済みの run から数えられます。探索に使った seed 0〜9 の 10 個から k 個を選び、24 設定それぞれで k 個の val_auc の平均を取って、一番高い設定を選びます。

k 個の選び方を乱数で 500 回引き、2 つの値を出しました。1 つ目は、選んだ設定が 20 回の平均で 9 位以下だった割合です。9 位以下は、冒頭の図で横線が一段下がった後の設定です。2 つ目は、選んだ設定の k 個の平均から 20 回の平均を引いた差で、500 回分を平均しています。

10 個から k 個を選ぶ組み合わせは、k が 1 なら 10 通りしかないので、500 回の中には同じ選び方が何度も出ます。出力の順位の中央値は、選んだ設定の 20 回の平均での順位について、500 回分の真ん中の値です。

```python
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
```

```text
k= 1: 9 位以下を選ぶ割合 0.20  順位の中央値 5  選んだ値と 20 回の平均の差 +0.0040
k= 2: 9 位以下を選ぶ割合 0.13  順位の中央値 2  選んだ値と 20 回の平均の差 +0.0023
k= 3: 9 位以下を選ぶ割合 0.06  順位の中央値 2  選んだ値と 20 回の平均の差 +0.0015
k= 5: 9 位以下を選ぶ割合 0.03  順位の中央値 2  選んだ値と 20 回の平均の差 +0.0009
k=10: 9 位以下を選ぶ割合 0.00  順位の中央値 2  選んだ値と 20 回の平均の差 +0.0006
```

{{< figure src="exp_seeds.webp" alt="横軸はどちらも 1 設定あたりの seed の数で、1、2、3、5、10。左は 9 位以下の設定を選ぶ割合で、0.20、0.13、0.06、0.03、0.00 と下がる。右は選んだ val_auc と 20 回の平均の差で、0.0040、0.0023、0.0015、0.0009、0.0006 と下がる" caption="1 設定あたりの seed の数と、9 位以下を選ぶ割合（左）・選んだ値の高さ（右）" align="center" >}}

seed が 1 個だと 5 回に 1 回は 9 位以下の設定を選び、選んだ値は平均で 0.0040 高く出ます。3 個にすると 9 位以下を選ぶ割合は 0.06、5 個で 0.03 まで下がりました。k が 10 の時は 10 個全てを使うので選び方は 1 通りしかなく、毎回 2 位の設定を選びます。2 位の平均は 1 位より 0.0002 低いだけなので、外れの設定を選んだとは言えません。

seed を k 個使うと、学習の回数も k 倍になります。24 設定を 5 個ずつなら 120 回です。全ての設定を 1 個ずつ学習させてから、上位の数設定にだけ seed を足して平均で比べると、回数を抑えつつ、冒頭の図の 23 位のような設定を 1 位に選ぶことは避けられると考えられます。どちらにしても、`random_state` を params に記録しておけば、`search_runs` の結果を設定ごとにまとめて平均できます。

---

### 同じ設定で結果が変わる時

seed を記録していても、同じ設定・同じ seed の run で結果が変わることがあります。よくあるのは、学習用のデータが同じパスのファイルに上書きされる場合です。最初の節のコードの続きで、最初に届いた 320 行を `train.csv` に書いて学習させ、後から届いた 106 行を足した 426 行で同じパスに上書きし、同じ設定で学習させ直しました。

```python
import pandas as pd

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
```

```text
params が同じ: True
before val_auc 0.9791  digest bf8ce65b  profile {"num_rows": 320, "num_elements": 9920}
after  val_auc 0.9765  digest 5f3bcb17  profile {"num_rows": 426, "num_elements": 13206}
```

2 つの run の記録を並べると、次のようになります。

| 記録 | before | after |
|---|---|---|
| params の 6 項目 | 同じ | 同じ |
| val_auc | 0.9791 | 0.9765 |
| dataset の digest | bf8ce65b | 5f3bcb17 |
| dataset の行数 | 320 | 426 |

params には `data_path` としてファイルのパスも記録しましたが、パスは同じなので違いが出ません。違いが見えるのは、`log_input` で記録した digest と行数だけです。val_auc の差の 0.0026 は、前の節の seed による揺れと同じくらいなので、値だけを見ても設定のせいかデータのせいかは分かりません。digest が違えば、データが変わったと分かります。

<br>

#### digest が見分けない変更

MLflow 3.18.0 の [digest の計算](https://github.com/mlflow/mlflow/blob/v3.18.0/mlflow/data/digest_utils.py)は、DataFrame の先頭 10000 行の中身と、行数、列名から作られます。20000 行のデータで 1 行だけラベルを直し、digest と、CSV 全体からハッシュ関数の [SHA-256](/notes/security/sha-256/) で計算した値の先頭 8 文字を比べました。

```python
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
```

```text
   50 行目を直す: digest d2c11937 → 92bbfeed  sha256 2df62e76 → f6392947
15000 行目を直す: digest d2c11937 → d2c11937  sha256 2df62e76 → 5996be93
```

50 行目を直すと digest は変わりますが、15000 行目を直しても d2c11937 のままでした。行数を変えずに 10000 行より後ろだけを直すと、MLflow の digest では見分けられません。1 万行を超えるデータでは、ファイル全体のハッシュを自分で計算して `set_tag` で残すか、[DVC](https://dvc.org/) のようなデータのバージョン管理のツールで付けたバージョンを記録します。

---

### MLflow 以外のツール

実験管理のツールは、記録する中身より、記録をどこに置くかで分かれます。

| ツール | 記録の置き場所 |
|---|---|
| [MLflow](https://mlflow.org/docs/latest/ml/tracking/) | OSS（Open Source Software）。手元の SQLite から、自分で立てるサーバーまで |
| [Weights & Biases](https://wandb.ai/)（W&B）、[Comet](https://www.comet.com/) | 各社のサービス |
| [TensorBoard](https://www.tensorflow.org/tensorboard) | 手元のログのファイル。学習曲線などの可視化が中心 |
| [ClearML](https://clear.ml/) | OSS のサーバーか、ClearML のサービス |
| クラウドの ML 基盤 | Vertex AI、SageMaker AI、Azure ML、Databricks |

クラウドの ML 基盤のうち、[SageMaker AI](https://docs.aws.amazon.com/sagemaker/latest/dg/mlflow.html)、[Azure Machine Learning](https://learn.microsoft.com/en-us/azure/machine-learning/how-to-track-experiments-mlflow)、[Databricks](https://docs.databricks.com/aws/en/mlflow/) は MLflow の仕組みで記録を受け取ります。Google Cloud は [Vertex AI Experiments](https://cloud.google.com/vertex-ai/docs/experiments/intro-vertex-ai-experiments) という独自の仕組みです。AWS は以前の SageMaker Experiments を Studio Classic 向けの機能とし、MLflow への移行を案内しています（2026 年 11 月時点）。

サービスが終わった例もあります。以前よく名前の挙がった Neptune は、OpenAI による買収に伴い、2026 年 3 月にクラウドのサービスを[終了](https://docs.neptune.ai/transition_hub)しました。

どのツールを選んでも、seed とデータの識別子を記録するかどうかは、コードを書く側が決めます。本記事の 2 つの問題は、ツールを変えても同じように起きます。

---

### 1 位を選ぶ前に見ること

探索の結果を val_auc の高い順に並べたら、1 位の設定を選ぶ前に、1 位と下の設定との差を見ます。その差が、同じ設定で seed を変えた時の揺れより小さければ、並びは seed で決まっています。冒頭の図の上位 8 設定は、平均の差が 0.0008 で、seed による揺れの 0.0028 より小さい範囲でした。

その場合は、上位の数設定に seed を足して平均で比べます。この実験では、seed 1 個ずつの探索で 5 回に 1 回は 9 位以下を選び、5 個の平均で 3% まで下がりました。選んだ後に伝える性能は、1 位の run の値ではなく、テスト用のデータか、別の seed で測り直した値にします。

記録には、`random_state` を params として、学習に使ったデータを `log_input` で残します。1 万行を超えるデータは、digest に加えてファイル全体のハッシュかデータのバージョンも残します。選んだモデルは、[モデルレジストリ](../model-registry/)で本番の候補として管理します。

冒頭の図の seed 2 の探索は、23 位の小さなフォレストを 1 位に選びました。MLflow の画面でこの run だけを見ていれば、0.9816 という値に疑う理由はありません。並んだ run の 1 位が本当に 1 位かは、同じ設定の run が seed を変えて何個あるかを見れば分かります。
