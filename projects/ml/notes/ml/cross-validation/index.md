---
title: "交差検証（cross validation）"
date: 2026-05-24
draft: false
series: ["機械学習ノート", "Machine Learning"]
tags: ["machine-learning", "scikit-learn", "model-evaluation"]
weight: 9
topics: ["Machine Learning（評価・概念・アルゴリズム）"]
cardImage: "cross_validation_alpha.svg"
---

交差検証（cross validation, CV）は、限られた学習データを「訓練用」と「検証用」に何通りも分け直して評価することで、モデルの性能をより安定して見積もる手法です。  
1 回だけの分割では「たまたま簡単／難しい分割を引いた」せいで結果がブレるので、分割の組み合わせを変えながら平均を取って判断します。

[過学習](../overfitting/)を検出する道具であり、[正則化](../regularization/)の `alpha` のような[ハイパーパラメータ](../hyperparameter/)を安定的に選ぶ道具でもあります。

---

### 最もよく使う K-Fold

[KFold](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.KFold.html) はデータを `k` 等分（fold）し、毎回 1 つを検証用、残り `k-1` 個を訓練用に使います。これを `k` 回繰り返して、各回の検証スコアを平均します。`k=5` または `k=10` が定番です。

{{< figure src="cross_validation_split.svg" alt="横軸をデータの番号 0〜19 とし、fold 1〜5 の 5 行を並べた図。各行で 4 件の赤い検証区間が左から右へ 1 つずつずれ、残りの 16 件が青い訓練データになる" caption="5-fold の分割" align="center" >}}

赤がその回の検証データ、青が訓練データです。検証に回す区間を fold ごとにずらしています。

ポイント:

- データ全体を 1 度ずつ検証側に回せる（評価が安定する）
- 各回でモデルを再学習するので、計算コストは単純評価の `k` 倍
- データの並びに偏りがある場合は事前に `shuffle=True` でシャッフルする
- 分類で各クラスの比率を保ちたい時は [StratifiedKFold](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.StratifiedKFold.html) を使う

---

### CV でハイパーパラメータを選ぶ

[正則化](../regularization/)の `alpha` のように「強さ」を持つハイパーパラメータは、訓練データだけ見て決められません（訓練誤差は `alpha=0` で最小になり常に過学習側を選んでしまう）。CV を使い、各候補で `k` 回の検証スコアを平均し、最も良いものを選びます。

次の図は、特徴量 50 個（予測に効くのはそのうち 10 個）の回帰データで、[Ridge](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.Ridge.html) の `alpha` を 20 通り変えて 5-fold CV の R² を測った結果です。R²（[決定係数](../regression-metrics/)）は 1 で完全一致、0 で平均値を返すだけの予測と同等、負ならそれより悪いことを表します。データの件数だけを 60 件と 300 件で変えています。

{{< figure src="cross_validation_alpha.svg" alt="横軸を Ridge の alpha（0.01〜1000 の対数目盛）、縦軸を 5-fold CV の R² の平均と標準偏差のエラーバーとした 2 本の曲線。60 件の曲線は alpha = 2.34 の縦の点線で最大の山型で、左側ほどエラーバーが長い。300 件の曲線は alpha = 10 付近まで 0.98 で平らで、その先で下がる" caption="Ridge の alpha と 5-fold CV の R²" align="center" >}}

60 件の曲線は山型で、`alpha=2.34`（縦の点線）で最大です。`alpha` が小さすぎると過学習、大きすぎると係数を 0 に寄せすぎた未学習でスコアが下がります。エラーバー（fold 間のばらつき）も `alpha` が小さい側ほど長く、平均だけでなく安定性でも劣ります。

一方で、300 件の曲線は `alpha=10` 付近まで平らです。特徴量に対してデータが十分にあれば、正則化が弱くても過学習しにくいからです。良い `alpha` はデータ量でも変わるので、CV で確かめます。

---

### Python での実例

[scikit-learn](https://scikit-learn.org/stable/modules/cross_validation.html) は [cross_val_score](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.cross_val_score.html) と [GridSearchCV](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.GridSearchCV.html) が主要 API です。次のコードは、図の 60 件のデータで同じ計算をします。

```python
import numpy as np
from sklearn.datasets import make_regression
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold, cross_val_score, GridSearchCV

# 60 件のデータに対して特徴量が 50 個ある（データが少ない）回帰問題
X, y = make_regression(n_samples=60, n_features=50, n_informative=10,
                       noise=20, random_state=0)

cv = KFold(n_splits=5, shuffle=True, random_state=0)

# 1) alpha を固定したモデルを CV で評価し、fold ごとのスコアも見る
for alpha in (0.01, 1.0):
    scores = cross_val_score(Ridge(alpha=alpha), X, y, cv=cv, scoring="r2")
    print(f"alpha={alpha}: folds={np.round(scores, 3)}  "
          f"mean={scores.mean():.3f}  std={scores.std():.3f}")

# 2) GridSearchCV で alpha の候補 20 個を同じ CV で比べる
grid = GridSearchCV(
    Ridge(),
    param_grid={"alpha": np.logspace(-2, 3, 20)},
    cv=cv,
    scoring="r2",
).fit(X, y)
print(f"best alpha: {grid.best_params_['alpha']:.3f}")
print(f"best CV R^2: {grid.best_score_:.3f}")
```

実行結果:

```text
alpha=0.01: folds=[-0.974  0.364  0.658  0.613  0.826]  mean=0.298  std=0.653
alpha=1.0: folds=[0.714 0.935 0.817 0.836 0.957]  mean=0.852  std=0.088
best alpha: 2.336
best CV R^2: 0.860
```

`alpha=0.01` の fold 1 は R² が -0.974 で、平均値を返すだけの予測にも負けています。残りの fold は 0.364〜0.826 なので、1 回の分割だけで評価すると、どの fold を引いたかで結論が変わります。5 つの平均と[標準偏差](../../math/stddev/)を並べると、平均が低く不安定だと分かります。`GridSearchCV` が選んだ 2.336 は、図の点線と同じ値です。

---

### CV と train/validation/test の関係

データを 3 つに分ける場合の役割整理:

- 訓練 (train): モデルのパラメータを学習する
- 検証 (validation): ハイパーパラメータを選ぶ。CV はこれを内部で複数回繰り返す仕組み
- テスト (test): 最終的なモデルの性能を見積もる。最後に 1 回だけ使う

CV を使うと検証データを明示的に分けなくて済みます。ただし、テストデータは必ず別に確保しておきます（CV 内で何度もスコアを見て選んだモデルは、CV スコア自体も少し楽観的に出るため）。

---

### 機械学習での使いどころ

- ハイパーパラメータの選定（[正則化](../regularization/)の `alpha`、[RandomForest](../random-forest/) の `max_depth`、[kNN](../knn/) の `k`、[GradientBoosting](../gradient-boosting/) の学習率など）
- モデル間の比較（同じ CV で複数モデルを評価して平均スコアで選ぶ）
- 評価指標の安定した見積もり（[ROC-AUC / PR-AUC](../roc-pr-auc/) を CV で平均すると 1 分割よりブレが減る）
- データ数が少ない案件（テスト用に大きく取れない時、CV で全データを評価に回せるのが効く）

---

### 適さないケース

- データが極端に多い場合: 1 回の評価で十分安定するので、CV のコスト（k 倍）が見合わない
- 時系列データに普通の KFold を使う: 未来のデータで訓練して過去を当てることになり、汎化性能を過大評価しやすい。[TimeSeriesSplit](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html) を使う（walk-forward CV の詳細は[時系列予測](../time-series-forecasting/)のノート）
- グループ構造のあるデータ（同じユーザー・同じ患者の複数記録など）にランダム分割を使う: 同じグループが訓練と検証両方に入ると評価が楽観的に出る。[GroupKFold](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.GroupKFold.html) を使う
- 「CV をやれば過学習しない」と思い込むこと: CV はあくまで評価方法。モデル側で[正則化](../regularization/)などの対策を打って初めて[過学習](../overfitting/)が抑えられる
