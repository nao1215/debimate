---
title: "モデルレジストリとバージョニング（model registry）"
date: 2026-05-26
draft: false
series: ["機械学習ノート", "MLOps"]
tags: ["machine-learning", "mlops"]
weight: 2
topics: ["MLOps"]
---

モデルレジストリ（model registry）は、学習済みモデルに名前とバージョンを付け、学習時の条件や評価結果と結び付けて管理する仕組みです。新しいモデルを本番へ出す時や、問題が起きて以前のモデルへ戻す時に、どのモデルを使うか指定できます。

例えば、解約率を予測するモデルを毎週学習し直すと、同じ用途のモデルが増えていきます。`best_model.pkl` という名前だけでは、どのデータで学習し、何を基準に選んだか分かりません。モデルレジストリでは「解約予測のバージョン 4」と、その学習記録を対応付けます。

<br>

本記事では [MLflow Model Registry](https://mlflow.org/docs/latest/ml/model-registry/) を使い、モデルの登録、参照先の変更、推論側の読み込みを順に確認します。

---

### 実験記録と本番で使うモデル

[実験管理](../experiment-tracking/)は、学習条件を変えた試行と結果を記録します。モデルレジストリは、名前を付けたモデルの各バージョンを管理します。本番候補を選んで登録する運用にすると、全ての試行は実験管理で検索し、配信するモデルはレジストリで選べます。登録しただけで本番利用が承認されるわけではありません。

{{< note-panels caption="同じモデルについて、記録する内容と確認する場所が異なります。" >}}
- title: 実験管理
  body: どの条件で学習したか
  items:
  - 学習データ、パラメータ、評価結果
  - 学習の 1 回の試行を識別する ID（run ID）
- title: モデルレジストリ
  body: どのバージョンを選ぶか
  items:
  - モデル名、バージョン、元の run
  - 検証結果のタグ、参照用の別名
- title: 推論サービス
  body: 何を読み込んで応答したか
  items:
  - 実際に読み込んだバージョン
  - デプロイ時刻、予測ログ
{{< /note-panels >}}

レジストリで本番用として選んだバージョンと、稼働中のサービスが実際に読み込んだバージョンは、別々に管理されます。「バージョン 4 を選んだ」というレジストリの情報だけでは、全ての推論サーバーがバージョン 4 へ切り替わったとは判断できません。

---

### バージョン、別名、タグ

MLflow では、同じモデル名へ登録するたびにバージョン番号が増えます。バージョン番号は登録したモデルを指定するための番号であり、数字が大きいほど精度が高いという意味ではありません。

別名（alias）は、あるバージョンを指す変更可能な名前です。例えば `champion` を現在選んでいるモデル、`challenger` を比較する候補の名前として使えます。この呼び名は運用側で決めます。

| 指定 | 意味 |
|---|---|
| `models:/churn-classifier/4` | バージョン 4 を読み込む |
| `models:/churn-classifier@champion` | 読み込み時点で `champion` が指すバージョンを読み込む |
| `validation_status=passed` | バージョンに付けた検証結果のタグ |

タグは検索や判断のための属性です。`passed` と書いただけでテストが実行されたり、未承認モデルの配信が禁止されたりはしません。検証・承認を行う処理と、その結果をタグへ記録する処理を接続します。

以前の MLflow には `Staging`、`Production` などの固定ステージがありましたが、2.9.0 から非推奨です。[移行ガイド](https://mlflow.org/docs/latest/ml/model-registry/workflow/#migrating-from-stages)では、状態の記録にはタグ、参照先の指定には別名を使い、開発・本番の権限分離は環境ごとの登録モデルなどで扱います。別名に `production` と名付けるだけではアクセス制御になりません。

---

### 別名を変えても、読み込み済みのモデルは変わらない

ローカル環境で、出力の異なるモデルを 2 つ登録します。バージョン 1 は `y=x`、バージョン 2 は `y=2x` のデータで学習した[線形回帰](/ml/ml/linear-regression/)です。入力を `x=4` に固定すると、モデルを読み替えたかどうかが予測値の 4 と 8 で分かります。精度を比較する実験ではありません。

[実験コード](./lab/run.py)は、DB（データベース）に [SQLite](https://www.sqlite.org/) を使い、モデルファイルも一時ディレクトリへ保存します。[scikit-learn](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LinearRegression.html) で学習したモデルを実験記録へ保存し、レジストリへ登録した後、別名と読み込み済みのモデルを操作します。外部の MLflow サーバーは使いません。

[依存ファイル](./lab/requirements.txt)と実験コードを同じディレクトリへ保存し、Python 3.12 で実行します。検証に使った MLflow は 3.17.2、scikit-learn は 1.7.2 です。

`requirements.txt` の内容は次の通りです。

```text
mlflow==3.17.2
scikit-learn==1.7.2
numpy==2.5.4
cloudpickle==3.1.2
SQLAlchemy==2.0.43
```

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python run.py
```

以下が `run.py` の全体です。`resident` は、推論サービスがメモリへ読み込んだモデルに相当します。

```python
"""Run a local registry experiment; remove the temporary DB/artifacts on exit."""
import os
os.environ.setdefault("MLFLOW_ENABLE_TELEMETRY", "false")
os.environ.setdefault("MLFLOW_ENABLE_ARTIFACTS_PROGRESS_BAR", "false")

from pathlib import Path
from tempfile import TemporaryDirectory

import mlflow
import mlflow.sklearn
import numpy as np
from mlflow import MlflowClient
from mlflow.models import infer_signature
from sklearn.linear_model import LinearRegression


def main():
    with TemporaryDirectory(prefix="registry-lab-") as directory:
        root = Path(directory)
        mlflow.set_tracking_uri(f"sqlite:///{root / 'registry.db'}")
        mlflow.set_registry_uri(mlflow.get_tracking_uri())
        experiment = mlflow.create_experiment(
            "alias-and-reload", artifact_location=(root / "artifacts").as_uri()
        )
        client = MlflowClient()
        name = "toy-linear"
        train_x = np.array([[0.0], [1.0], [2.0], [3.0]])
        test_x = np.array([[4.0]])
        versions = []
        for slope in (1.0, 2.0):
            model = LinearRegression().fit(train_x, slope * train_x[:, 0])
            with mlflow.start_run(experiment_id=experiment):
                mlflow.log_param("slope", slope)
                mlflow.set_tag("dataset", f"toy-y-{slope:g}x")
                info = mlflow.sklearn.log_model(
                    model, name="linear-model",
                    signature=infer_signature(train_x, model.predict(train_x)),
                    input_example=train_x[:1],
                    pip_requirements=["scikit-learn==1.7.2", "numpy==2.5.4",
                                      "cloudpickle==3.1.2"],
                )
                version = str(mlflow.register_model(info.model_uri, name).version)
                versions.append(version)
                client.set_model_version_tag(name, version, "purpose", "alias-reload-demo")
        first, second = versions
        assert (first, second) == ("1", "2")
        client.set_registered_model_alias(name, "champion", first)
        resident = mlflow.pyfunc.load_model(f"models:/{name}@champion")

        def report(label, model, expected_version, expected_prediction):
            version = str(client.get_model_version_by_alias(name, "champion").version)
            prediction = float(model.predict(test_x)[0])
            assert version == expected_version
            assert np.isclose(prediction, expected_prediction)
            print(f"{label}: alias=v{version}, prediction={prediction:.1f}")

        report("initial load", resident, first, 4.0)
        client.set_registered_model_alias(name, "champion", second)
        report("alias changed only", resident, second, 4.0)
        resident = mlflow.pyfunc.load_model(f"models:/{name}@champion")
        report("after reload", resident, second, 8.0)
        client.set_registered_model_alias(name, "champion", first)
        report("rollback alias only", resident, first, 8.0)
        resident = mlflow.pyfunc.load_model(f"models:/{name}@champion")
        report("after rollback reload", resident, first, 4.0)
        mlflow.end_run()


if __name__ == "__main__":
    main()
```

コードの後半では、別名をバージョン 1 に戻す操作も行います。以下が実行結果です。MLflow の登録ログを除き、実験が出力した行を載せています。

```text
initial load: alias=v1, prediction=4.0
alias changed only: alias=v2, prediction=4.0
after reload: alias=v2, prediction=8.0
rollback alias only: alias=v1, prediction=8.0
after rollback reload: alias=v1, prediction=4.0
```

出力を手順ごとに並べると次の図になります。青い線が `champion` の指すバージョン、赤い破線が予測値から分かる `resident` のバージョンで、両者がずれた手順を赤く塗っています。

{{< figure src="model-registry_alias_vs_loaded.svg" alt="横軸が実験の 5 つの手順、縦軸がバージョン 1 と 2。青い線は champion の指すバージョン、赤い破線は予測値から分かる resident のバージョンで、別名だけを変えた 2 番目と 4 番目の手順で両者がずれ、その手順が赤く塗られている" caption="別名の参照先と読み込み済みモデルのバージョンの推移" align="center" >}}

別名を戻しただけでは、バージョン 2 を読み込んでいた `resident` は 8 を返します。再ロード後に初めて 4 へ戻ります。[MLflow のモデル読み込み API](https://mlflow.org/docs/latest/api_reference/python_api/mlflow.pyfunc.html#mlflow.pyfunc.load_model) は、指定先のモデルを読み込んで返します。そのオブジェクトが以後の別名変更を監視するわけではありません。

実際の推論サービスでは、起動時に読み込む、変更を検知して再ロードする、新しいバージョンのプロセスへ通信を切り替える、といった更新方法を決めます。この実験は 1 プロセスでの読み替えを確認したものであり、複数サーバーへの無停止デプロイを再現したものではありません。

---

### 切り替えと切り戻し

新旧モデルを比較する場合、現在使っているモデルを champion、候補を challenger と呼びます。候補へ同じ入力を渡して結果だけ記録する shadow test や、[通信の一部を候補へ振り分ける](/notes/software-architecture/feature-flag/) canary deployment は、[推論サービング](../inference-serving/)側で実装します。レジストリの別名は、その対象モデルを指定するために使います。

{{< note-steps caption="一例です。新旧モデルの比較や通信の切り替えには、レジストリ以外の処理も必要です。" >}}
- title: 候補を検証
  body: 候補のバージョンを固定し、入力形式・予測品質・遅延を確認。
- title: 配信側を更新
  body: 新モデルを読み込んだプロセスを準備し、通信を段階的に切り替える。
- title: 稼働状態を確認
  body: 応答したバージョンと指標を記録。問題があれば旧モデルへ通信を戻す。
{{< /note-steps >}}

切り戻す速さは、旧モデルのプロセスを残しているか、再ロードが必要か、モデルを取得する時間などに依存します。戻すモデルの入力形式が現在の前処理に合うことも必要です。

また、別名は後から変更できます。過去の予測を調べるためには、予測ログやデプロイ記録へ、その時点で読み込んだ具体的なバージョンを残します。`champion` という文字列だけでは、後から同じモデルを特定できません。複数サーバーがある場合は、それぞれが読み込んだバージョンを確認します。

---

### モデルと結び付ける記録

モデルファイルに加え、再現・比較・切り戻しに必要な情報を記録します。評価指標は数値だけでなく、評価データと計算条件も残します。

| 目的 | 記録する内容の例 |
|---|---|
| 学習の再現 | 元の run、コードのコミット、データのバージョン、依存ライブラリ |
| 比較 | 評価データ、指標、前処理、判定基準 |
| 利用判断 | 想定する入力、既知の限界、責任者、承認記録 |
| 配信の追跡 | 読み込んだバージョン、配置先、切り替え時刻 |

入出力の形や既知の限界を文章で説明した[モデルカード](https://arxiv.org/abs/1810.03993)も、利用判断に役立ちます。詳細な評価レポートやデプロイ履歴を別の場所へ保存する場合は、レジストリから対応する記録を参照できるようにします。タグに情報を全て詰め込む必要はありません。

バージョン番号とは別に、入力形式の変更や学習データのバージョンを記録すると、互換性を判断しやすくなります。[Semantic Versioning](https://semver.org/) の番号を採用する場合も、何を互換性と呼ぶか決める必要があります。予測の品質は単調に改善するとは限らないため、新しい番号だけを採用理由にはできません。

---

### 適さないケースと落とし穴

1 回だけ学習して手元で分析する段階なら、モデルファイルと学習条件の保存で足りる場合があります。複数の候補を比較し、配信や再学習を繰り返す段階で、名前とバージョンを共通の API で扱う利点が増えます。

- 登録と承認を混同しないようにします。登録権限、検証基準、配信を承認する担当を決め、配信処理でも確認します。
- レジストリの DB とモデルファイルは保存先が異なる場合があります。メタデータだけ復元できても、参照先のファイルが失われていればモデルを読み込めません。
- 容量削減で古いモデルを消すと、切り戻しや過去の予測の調査ができなくなります。残す期間と、そのモデルを参照するサービスや記録を確認します。
- 別名を複数の処理が同時に更新すると、意図した候補と異なるモデルを読み込む可能性があります。配信処理では対象バージョンを固定して検証し、実際に使ったバージョンを記録します。

[再学習パイプライン](../retraining-pipeline/)から登録を自動化する場合も、学習の完了、評価の合格、配信の完了を別々に確認します。
