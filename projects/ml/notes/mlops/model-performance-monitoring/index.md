---
title: "モデル性能劣化の監視（model performance monitoring）"
date: 2026-05-26
draft: false
series: ["機械学習ノート", "MLOps"]
tags: ["machine-learning", "mlops", "monitoring"]
weight: 5
---

モデル性能劣化の監視（model performance monitoring）は、本番運用しているモデルの予測品質を継続的に観測し、劣化を早期に検知する仕組みです。学習時の精度は本番でずっと維持されるわけではなく、[データドリフト](../data-drift/)や仕様変更で低下する場合があります。予測品質の低下は、ユーザー体験やビジネス指標にも影響します。

監視対象を複数の層（infra → data → model → business）に分け、それぞれ指標を決めます。検知後の対応として、[再学習パイプライン](../retraining-pipeline/)を自動で起動する設計もあります。

---

### 4 つの監視レイヤ

監視対象は粒度の違う 4 つのレイヤに整理できます。それぞれ「気づきたい問題」「責任者」「使う指標」が違います。

{{< note-panels caption="4 つの監視対象。それぞれ指標と担当を決めます。" >}}
- title: ビジネス KPI
  body: エンドツーエンドの効果
  items:
  - 指標：revenue / conversion / NPS
  - 担当：プロダクト / ビジネス
- title: モデル性能
  body: 予測品質そのもの
  items:
  - 指標：accuracy / F1 / 回帰誤差 / PR-AUC
  - 担当：ML エンジニア
- title: データ品質
  body: 入力データの健全性
  items:
  - 指標：schema / range / null 率 / drift
  - 担当：データエンジニア
- title: インフラ
  body: 配信基盤の健全性
  items:
  - 指標：latency / error rate / CPU / メモリ
  - 担当：SRE / DevOps
{{< /note-panels >}}

「モデルの精度が落ちた」と一口に言っても、原因がモデル本体か、入力データか、配信基盤か、上位のビジネス事情かで対処が違います。4 層を別々に観測し、どこで問題が起きたかを確認します。

---

### モデル性能指標の時系列監視

精度を時系列で記録し、移動平均（moving average, MA）と閾値を使って変化を確認します。日々の変動を平滑化すると、継続的な低下が見やすくなります。次のコードは 120 日分の精度を合成し、7 日移動平均が閾値を下回る日を求めます。[NumPy](https://numpy.org/) 2.5.4 で実行した計算部分で、描画を含むコード全体は[図の生成コード](https://github.com/nao1215/debimate/blob/main/projects/ml/scripts/notes/model-performance-monitoring_gen.py)にあります。

```python
import numpy as np

rng = np.random.default_rng(0)
days = np.arange(0, 120)
# 緩やかなドリフト + 75 日目に外的要因でジャンプ
true_acc = 0.92 - 0.0008 * days
true_acc[75:] -= 0.05
observed = true_acc + rng.normal(0, 0.006, len(days))

# 7 日移動平均
ma = np.array([observed[max(0, i - 7 + 1):i + 1].mean() for i in range(len(days))])
print("warning (0.88) を下回った日:", np.argmax(ma < 0.88))
print("critical (0.85) を下回った日:", np.argmax(ma < 0.85))
```

```text
warning (0.88) を下回った日: 55
critical (0.85) を下回った日: 76
```

![Accuracy の時系列と warning/critical 閾値](./monitoring_accuracy_alert.svg)

灰色の点が日次の生値、青線が 7 日移動平均です。橙の破線（warning, 0.88）と赤の破線（critical, 0.85）が SLO（Service Level Objective、満たすべき品質目標）の閾値で、移動平均が critical を下回った時点で on-call にページが飛びます。

移動平均が warning を下回ったのは 55 日目、critical を下回ったのは 76 日目でした。76 日目は、外的要因（例: 新キャンペーンによるユーザー層変化）で精度が 0.05 落ちた翌日です。warning から 21 日あるので、その間に再学習や原因調査を始めれば、critical に達する前に手が打てます。

---

### Ground truth が遅れる問題と proxy metrics

精度を測るには ground truth（実際の正解）が必要です。ただし、現実には数時間〜数週間遅れて到着することが多いです。例として、レコメンドの「クリックの有無」は数秒で分かります。一方、「購入したかどうか」は数日後、「リテンションに寄与したか」は数週間後にしか確定しません。

![Ground truth lag と proxy metrics](./monitoring_ground_truth_lag.svg)

ground truth を待っていたら検知が遅すぎるので、proxy metrics（代理指標）で「劣化の兆候」を早期に捉える設計にします。

- 即時に取れる指標: 予測スコアの分布、予測値の偏り（全部 1 クラスに寄っていないか）
- 数時間で取れる指標: クリック率、エラー率、ユーザーフィードバック
- 数日で取れる指標: 部分的な ground truth（早期に確定するもの）
- 最終的な指標: 完全な ground truth（最終評価）

複数の proxy metrics を監視し、いずれかが通知条件を満たしたらアラートを出します。

---

### 入力ドリフト検知: KS 検定と PSI

ground truth がほぼ取れないケースでも、入力データの分布変化は即時検知できます。ここでは KS 検定（Kolmogorov-Smirnov test）と PSI（Population Stability Index）を使います。

- KS 検定: 訓練分布と本番分布の累積分布関数の最大差を測る。`0` で完全一致、`1` で完全不一致
- PSI: 分布を 10 ビンに分けて、訓練分布と本番分布の KL ダイバージェンスを両方向で計算して足し合わせる。`< 0.1` で安定、`0.1〜0.25` でやや変化、`> 0.25` で大きく変化

次のコードは、訓練分布 5,000 件と 1 日 200 件の本番データを 120 日分比べます。60 日目から平均と標準偏差が少しずつずれる設定です。KS 統計量は [SciPy の ks_2samp](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.ks_2samp.html)（SciPy 1.18.1）で求め、描画は[図の生成コード](https://github.com/nao1215/debimate/blob/main/projects/ml/scripts/notes/model-performance-monitoring_gen.py)にあります。

```python
import numpy as np
from scipy import stats

rng = np.random.default_rng(1)
ref = rng.normal(50, 10, 5000)  # 訓練分布
bins = np.quantile(ref, np.linspace(0, 1, 11))  # 訓練分布の 10 分位でビンを切る
bins[0] -= 1; bins[-1] += 1
ref_pct = np.clip(np.histogram(ref, bins=bins)[0] / len(ref), 1e-6, 1)

ks_stats, psi_values = [], []
for d in range(120):
    if d < 60:
        live = rng.normal(50, 10, 200)  # 1 日 200 件
    else:
        shift = (d - 60) * 0.15  # 60 日目から徐々にずれる
        live = rng.normal(50 + shift, 10 + shift * 0.1, 200)
    ks_stats.append(stats.ks_2samp(ref, live).statistic)
    live_pct = np.clip(np.histogram(live, bins=bins)[0] / len(live), 1e-6, 1)
    psi_values.append(((live_pct - ref_pct) * np.log(live_pct / ref_pct)).sum())

ks, psi = np.array(ks_stats), np.array(psi_values)
print(f"0〜59 日目の最大: KS {ks[:60].max():.3f}, PSI {psi[:60].max():.3f}")
print(f"KS > 0.2 の初日: {np.argmax(ks > 0.2)}, PSI > 0.25 の初日: {np.argmax(psi > 0.25)}")
print(f"119 日目: KS {ks[-1]:.3f}, PSI {psi[-1]:.3f}")
```

```text
0〜59 日目の最大: KS 0.123, PSI 0.132
KS > 0.2 の初日: 88, PSI > 0.25 の初日: 84
119 日目: KS 0.331, PSI 0.659
```

![KS と PSI の時系列。60 日目から徐々に上昇](./monitoring_input_drift.svg)

KS 統計量と PSI は 60 日目あたりから上昇します。ただし分布が変わっていない 0〜59 日目でも KS は 0.123、PSI は 0.132 まで振れ、0.1 の線を KS で 2 日、PSI で 4 日超えました。1 日 200 件では標本のばらつきだけでこの程度動くので、0.1 で通知すると誤警報になります。件数に合わせて閾値を決めるか、後述の連続違反数と組み合わせます。

この図は accuracy の図とは別の模式データなので、ドリフト検知が精度低下より何日早いかは読み取れません。実運用では同じ時系列で、ドリフト検知から性能悪化までの遅れを評価します。

ただし入力ドリフトと精度劣化は必ずしも 1:1 対応しません。`P(x)` が変わっても `P(y|x)` が安定なら精度は維持されます（covariate shift, 詳細は [データドリフト](../data-drift/) 参照）。入力ドリフトを検知したら、予測精度への影響も確認します。

---

### コード例: Prometheus + Grafana で監視メトリクスを公開

推論サーバー側で predict のたびにメトリクスを記録し、[Prometheus](https://prometheus.io/) がスクレイプして [Grafana](https://grafana.com/) で可視化する標準パターンです。次のコードは [prometheus_client](https://github.com/prometheus/client_python)（0.26.0）を使った推論関数の例で、`model`、`model_version`、`feature_names` は推論サーバー側で定義済みの前提です。

```python
from prometheus_client import Counter, Histogram, Summary
import time

PREDICTIONS_TOTAL = Counter("predictions_total", "Total predictions", ["model_version"])
PREDICTION_LATENCY = Histogram("prediction_latency_seconds", "Latency",
                                buckets=[0.01, 0.05, 0.1, 0.2, 0.5, 1.0])
PREDICTION_SCORE = Histogram("prediction_score", "Output score distribution",
                              buckets=[0.0, 0.1, 0.2, 0.5, 0.8, 0.9, 1.0])
INPUT_FEATURE = Summary("input_feature", "Input feature value", ["feature_name"])

def predict_with_metrics(req):
    start = time.time()
    pred = model.predict([req.features])[0]
    elapsed = time.time() - start

    PREDICTIONS_TOTAL.labels(model_version=model_version).inc()
    PREDICTION_LATENCY.observe(elapsed)
    PREDICTION_SCORE.observe(pred)
    for name, val in zip(feature_names, req.features):
        INPUT_FEATURE.labels(feature_name=name).observe(val)

    return {"prediction": pred}
```

入力特徴量を Gauge（最後に `set()` した値だけを持つメトリクス）で記録すると、平均の推移は見られません。Prometheus は設定した間隔（[既定は 1 分](https://prometheus.io/docs/prometheus/latest/configuration/configuration/)）でスクレイプするので、その間の要求のうち最後の 1 件の値しか残りません。Gauge を時刻窓で平均しても、要求ごとの入力値の平均にはなりません。

そこで上のコードは [Summary](https://prometheus.io/docs/concepts/metric_types/#summary) に `observe()` します。Summary は観測値の合計 `_sum` と件数 `_count` を持ちます。常に 0.7 を返すダミーのモデルに年齢 20、30、40、90 の要求を 4 件流すと、age の `_count` は 4.0、`_sum` は 180.0 になり、平均 45 が求まります。Gauge なら残るのは最後の 90 だけです。

時間帯ごとの平均は [`rate(input_feature_sum[1h]) / rate(input_feature_count[1h])`](https://prometheus.io/docs/practices/histograms/) で求めます。分布の形まで見たい特徴量は Histogram で記録します。

Grafana のダッシュボードで「過去 24 時間の P99 latency」「予測スコアの分布の変化」「入力特徴量の平均推移」を並べておけば、各指標の変化を比較できます。アラートルール（PromQL: `histogram_quantile(0.99, sum by (le) (rate(prediction_latency_seconds_bucket[5m]))) > 0.2`）を設定すると、自動通知できます。

---

### Alert の二段階設計

監視で「常にアラートが鳴っている」状態は実質「鳴っていない」のと同じになります。閾値とアラート設計は次のように二段階にします。

| レベル | 閾値 | 通知先 | 期待される対応 |
|---|---|---|---|
| Warning | Critical に達する前に通知する値 | Slack channel | 1 営業日以内に調査 |
| Critical | SLO そのもの | PagerDuty / 電話 | 1 時間以内に対処 |

例えば、accuracy SLO = 0.85 のモデルに、warning = 0.88、critical = 0.85 を設定します。warning でじわじわ落ちる兆候を早めに捉え、critical で即時対応します。

誤警報が続くと、当番の担当者が通知を確認しなくなるおそれがあります。閾値・移動平均ウィンドウ・連続違反数（例: 「3 連続で閾値を下回ったらアラート」）の調整で false alarm を抑えます。

---

### Observability の 3 本柱: metrics / logs / traces

指標の変化を検知した後に原因を調べられるよう、ログとトレースも記録します。

- Metrics: 数値の時系列（accuracy、latency、throughput）。トレンドの俯瞰に強い
- Logs: 個別イベントの詳細（特定の予測の入力・出力・モデル version）。原因究明に強い
- Traces: 1 リクエストが複数サービスを通る軌跡（特徴量取得 → 推論 → DB 書き込み）。ボトルネック特定に強い

予測の根拠を後から確認する場合は、logs にリクエスト ID、モデル version、入力特徴量、予測値、確率を記録します。サンプリングする場合は、記録されない予測があることを踏まえ、調査に必要な範囲を決めます。

---

### 数学での使いどころ

- CUSUM（Cumulative Sum control chart）: 累積偏差で変化点検出
- ベイズ的変化検出: 事後確率の変化で検出（[ベイズの定理](../../math/bayes-theorem/)）
- 移動統計（rolling mean, rolling std）: ノイズを抑えてトレンドを見る
- [仮説検定](../../math/hypothesis-test/): KS 検定、`χ²` 検定、Mann-Whitney U 検定
- [情報理論](../../math/information-theory/): KL ダイバージェンス、Jensen-Shannon ダイバージェンスで分布距離

---

### 機械学習での使いどころ

- 推論精度の時系列監視（日次・週次レポート）
- model fairness の継続監視（属性別の精度差）
- データパイプライン健全性（schema check、null rate、duplicate）
- A/B test と組み合わせた champion-challenger の継続評価
- セグメント別監視（ユーザー層 / 地域 / デバイス別の精度）
- 異常入力の検知（外れ値、未知カテゴリ）
- predict-then-trace: 個別予測が後でクレームになったときに辿れる仕組み

ツール選び:

- 汎用: Prometheus + Grafana（自前運用）、Datadog、New Relic
- ML 特化: Evidently AI、WhyLabs、Arize AI、Fiddler、Vertex AI Model Monitoring、SageMaker Model Monitor
- ログ基盤: Elastic Stack（ELK）、Loki、Splunk、BigQuery

---

### 適さないケース / 落とし穴

- 集約指標だけ見て segment 別を見ない: 全体精度は維持されていても、特定セグメント（新規ユーザー、特定地域）での精度低下を見落とす
- ログを sampling せず全件保存: 保存量と保存コストが増える。必要な記録を残せるようにサンプリング率を決める
- モデルのバージョンを予測結果に紐付けない: 後から予測に使ったバージョンを確認できない。logs にバージョンを記録する
- 監視対象が増えすぎる: 担当者が確認しきれない。障害の検知や対応に必要な指標を選ぶ
- alert 受信者の負担を考えない: 全アラートが同じ重さで PagerDuty に行くと on-call が疲弊。重要度別ルーティング
- runbook が無いアラート: 「鳴ったがどう対処するか分からない」と意味が無い。アラートと対処手順をセットで作る
- 監視自身の monitoring を忘れる: 監視システムが落ちていてもアラートが鳴らない。canary metric（常に true を返す）を 1 つ用意して、それが消えたら監視が止まったと検知
- 学習データを忘れる: 学習データ自体に偏りや問題があれば、いくら監視しても根本解決しない。データ品質の上流監視も併せて
