---
title: "異常検知（anomaly detection）: Isolation Forest / LOF / One-Class SVM"
date: 2026-05-26
draft: false
series: ["機械学習ノート", "Machine Learning"]
tags: ["machine-learning", "scikit-learn", "unsupervised"]
weight: 32
topics: ["Machine Learning（評価・概念・アルゴリズム）"]
---

異常検知（anomaly detection、outlier detection）は、大多数の正常データから外れた点を見つける手法です。クレジットカードの不正利用、設備の故障の予兆、ネットワークへの侵入のように、見つけたい側のサンプルが極端に少なく、事前にラベルを付けられない場面で使います。

[クラス不均衡](../class-imbalance/)の極端なケースとも見なせます。ただし、不均衡分類は正例と負例の両方にラベルがある状況で、異常検知は正常データだけ（または僅かな異常ラベル）から学ぶ状況です。

<br>

本記事では、[scikit-learn](https://scikit-learn.org/stable/modules/outlier_detection.html) の 4 つの手法を同じデータに当てて、次の疑問を順に扱います。

- 4 つの手法は、どんな異常を見つけ、どんな異常を見逃すか
- Isolation Forest は、なぜ分割の回数で異常を判定できるのか
- 異常と判定する割合（contamination）は、どう決めるか
- 時系列の異常検知で、季節変動をどう扱うか

コードは scikit-learn 1.9.1、[NumPy](https://numpy.org/) 2.5.4、[pandas](https://pandas.pydata.org/) 3.1.1 で実行しました。本文のコードは計算部分で、[Matplotlib](https://matplotlib.org/) の描画を含む[図の生成コード](https://github.com/nao1215/debimate/blob/main/projects/ml/scripts/notes/anomaly-detection_gen.py)は GitHub で公開しています。

---

### 4 つの代表的な手法

| 手法 | 仕組み | 強み | 弱み |
|---|---|---|---|
| [Isolation Forest](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.IsolationForest.html) | ランダムな分割で、少ない回数で孤立する点を異常とする | 木を最大 256 点の部分標本で作るので、データが多くても軽い | 分割が軸に平行なので、境界が角ばる |
| [LOF](https://scikit-learn.org/stable/modules/generated/sklearn.neighbors.LocalOutlierFactor.html)（Local Outlier Factor） | [近傍](../knn/)の点と比べて、局所的な密度が低い点を異常とする | 密度の違うクラスタが混ざっていても使える | 近傍探索が重い。新しいデータの判定には `novelty=True` が要る |
| [One-Class SVM](https://scikit-learn.org/stable/modules/generated/sklearn.svm.OneClassSVM.html) | 正常データを囲む境界を[カーネル](../svm/)で学ぶ | 非線形な境界を引ける | 特徴量のスケールと `gamma` に敏感 |
| [Elliptic Envelope](https://scikit-learn.org/stable/modules/generated/sklearn.covariance.EllipticEnvelope.html) | 正常データを 1 つの多変量[正規分布](/ml/math/probability-distributions/)とみなし、楕円の外を異常とする | 外れ値の混入に強い共分散推定（MCD）を使う | クラスタが複数あるデータや、正規分布から遠いデータに合わない |

次のコードは、正常データ 300 点（2 つのクラスタ）と、広い範囲に一様乱数で置いた異常データ 20 点に、4 つの手法を当てます。異常の割合は全て 7% に揃えました。

```python
import numpy as np
from sklearn.datasets import make_blobs
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor, NearestNeighbors
from sklearn.svm import OneClassSVM
from sklearn.covariance import EllipticEnvelope

rng = np.random.default_rng(0)
# 正常: 2 つのクラスタに 300 点。異常: 広い範囲に一様乱数で 20 点
X_normal, _ = make_blobs(n_samples=300, centers=[(0, 0), (3, 3)],
                         cluster_std=0.6, random_state=0)
X_anom = rng.uniform([-3, -3], [6, 6], (20, 2))
X = np.vstack([X_normal, X_anom])
y_true = np.r_[np.ones(300), -np.ones(20)]  # 1 = 正常、-1 = 異常

algorithms = {
    "Isolation Forest": IsolationForest(contamination=0.07, random_state=0),
    "LOF": LocalOutlierFactor(n_neighbors=20, contamination=0.07),
    "One-Class SVM": OneClassSVM(nu=0.07, kernel="rbf", gamma=0.5),
    "Elliptic Envelope": EllipticEnvelope(contamination=0.07, random_state=0),
}
for name, clf in algorithms.items():
    pred = clf.fit_predict(X)  # 1 = 正常、-1 = 異常
    hit = ((pred == -1) & (y_true == -1)).sum()
    false_alarm = ((pred == -1) & (y_true == 1)).sum()
    print(f"{name}: 異常と判定 {(pred == -1).sum()} 点"
          f"（本物の異常 {hit} 点、誤検知 {false_alarm} 点）")

# 正常点のすぐ近くに落ちた異常点を数える
dist, _ = NearestNeighbors(n_neighbors=1).fit(X_normal).kneighbors(X_anom)
print("最寄りの正常点まで 0.15 未満の異常点:", (dist.ravel() < 0.15).sum())
```

実行結果:

```text
Isolation Forest: 異常と判定 23 点（本物の異常 14 点、誤検知 9 点）
LOF: 異常と判定 23 点（本物の異常 16 点、誤検知 7 点）
One-Class SVM: 異常と判定 30 点（本物の異常 10 点、誤検知 20 点）
Elliptic Envelope: 異常と判定 23 点（本物の異常 12 点、誤検知 11 点）
最寄りの正常点まで 0.15 未満の異常点: 4
```

{{< figure src="anomaly_methods_compare.png" alt="2 つの正常クラスタと散らばった異常 20 点に 4 手法を当てた 2×2 の散布図。Isolation Forest は 2 つのクラスタを角ばった 1 つの領域で囲み、LOF は点ごとに判定するので領域が無く、One-Class SVM はクラスタの間や右下の異常点の周りにも正常の領域を作り、Elliptic Envelope は 2 つのクラスタを 1 つの細長い楕円で囲んで両端の異常を取りこぼす" caption="4 つの異常検知手法の判定結果" align="center" >}}

緑の丸が本物の異常、赤い × が異常と判定した点、薄い青が正常と判定する領域です（LOF は点ごとの判定なので領域なし）。

同じ 7% でも結果は手法ごとに違います。LOF は密度を近傍で測るので、2 つのクラスタを別々に扱えて、本物の異常を最も多い 16 点見つけました。Elliptic Envelope は 2 つのクラスタを 1 つの細長い楕円で囲み、楕円の両端にある異常を正常と判定します。

One-Class SVM は `nu=0.07` でも 30 点を異常とし、右下の異常点 2 つの周りにも正常の領域を作りました。[`nu`](https://scikit-learn.org/stable/modules/generated/sklearn.svm.OneClassSVM.html) は境界の外に出る点が占める割合に上限を与える目安で、判定の数をそのまま決める値ではありません。手元で数えると、30 点のうち 20 点は境界の上に乗った点でした。`gamma` が大きいほど、境界は個々の点に合わせて細かく曲がります。

逆に、20 点のうち 4 点は正常クラスタの中（最寄りの正常点まで 0.15 未満）に落ちていて、4 つの手法が全て正常と判定しました。特徴量の上で正常と区別できない異常は、手法を変えても見つかりません。

---

### Isolation Forest の考え方

[Isolation Forest](https://doi.org/10.1109/ICDM.2008.17)（iForest）は、特徴量と閾値をランダムに選んでデータを 2 つに分け、点が 1 つになるまで分割を繰り返します。離れた異常点は少ない分割で孤立し、密集した正常点は何度も分けないと孤立しません。

{{< figure src="anomaly_isolation_concept.svg" alt="原点付近に集まった正常点と、右上に 1 つだけ離れた異常点（赤い星）の散布図。x1 = 1.5 の縦線 1 本で異常点だけが片側に分かれる" caption="分割 1 本で孤立する異常点" align="center" >}}

上の図では、x1 = 1.5 の分割 1 本で異常点（赤い星）が孤立します。この線は手で選んだ一例なので、実際の木で分割の回数を数えます。

```python
import numpy as np
from sklearn.ensemble import IsolationForest

rng = np.random.default_rng(0)
# 原点付近に正常点 50 個、(3, 3) に異常点 1 個
X_small = np.vstack([rng.normal([0, 0], 0.5, (50, 2)), [[3, 3]]])
clf = IsolationForest(random_state=0).fit(X_small)  # 木は 100 本

depths = []
for tree, features in zip(clf.estimators_, clf.estimators_features_):
    path = tree.decision_path(X_small[:, features])
    depths.append(np.asarray(path.sum(axis=1)).ravel() - 1)  # 通ったノード数 - 1 = 分割回数
depth = np.mean(depths, axis=0)
print(f"異常点の平均の深さ: {depth[-1]:.2f}")
print(f"正常点 50 個の平均の深さ: {depth[:-1].mean():.2f}")
print(f"木の高さの上限: {clf.estimators_[0].max_depth}")
```

実行結果:

```text
異常点の平均の深さ: 1.59
正常点 50 個の平均の深さ: 5.78
木の高さの上限: 6
```

異常点は平均 1.59 回の分割で孤立し、正常点は 5.78 回かかりました。正常点の値は、木の高さの上限 6 にほぼ張り付いています。scikit-learn は木を作る点の数（ここでは 51）の log2 を切り上げた高さで分割を打ち切り、葉に残った点の数から残りの深さを推定します。異常かどうかは浅い所で分かるので、深くまで木を伸ばしません。

---

### 異常と判定する割合（contamination）

`contamination` は、学習データのうち何割を異常と判定するかを決める[ハイパーパラメータ](../hyperparameter/)です。scikit-learn の Isolation Forest では、この値で変わるのはしきい値（`offset_`）だけなので、1 回学習したスコアに線を引き直せば比べられます。次のコードは、前節の `X` と `y_true` を使います。

```python
clf = IsolationForest(contamination="auto", random_state=0).fit(X)
scores = clf.decision_function(X)  # 0 未満を異常と判定する。低いほど異常
flagged = scores < 0
print(f'"auto": offset_={clf.offset_}、異常と判定 {flagged.sum()} 点'
      f"（本物の異常 {(flagged & (y_true == -1)).sum()} 点）")

for contam in [0.03, 0.07, 0.15]:
    thr = np.percentile(scores, contam * 100)  # 下から contam の割合で線を引く
    flagged = scores < thr
    hit = (flagged & (y_true == -1)).sum()
    print(f"contamination={contam}: 異常と判定 {flagged.sum()} 点"
          f"（本物の異常 {hit} 点、誤検知 {flagged.sum() - hit} 点）")
```

実行結果:

```text
"auto": offset_=-0.5、異常と判定 40 点（本物の異常 16 点）
contamination=0.03: 異常と判定 10 点（本物の異常 10 点、誤検知 0 点）
contamination=0.07: 異常と判定 23 点（本物の異常 14 点、誤検知 9 点）
contamination=0.15: 異常と判定 48 点（本物の異常 16 点、誤検知 32 点）
```

{{< figure src="anomaly_threshold_tuning.svg" alt="横軸を Isolation Forest のスコア（高いほど正常）とした 2 つのヒストグラム。正常点の分布は右側に集まり、本物の異常は左側に広がる。contamination 0.03、0.07、0.15 に対応する 3 本の縦線が左から順に並び、右の線ほど正常点の分布に食い込む" caption="スコアの分布と 3 つのしきい値" align="center" >}}

青が正常、赤が本物の異常のスコアの分布で、縦線より左を異常と判定します。

0.03 では判定した 10 点が全て本物の異常ですが、残り 10 点を見逃します。0.15 まで緩めると本物の異常は 16 点に増え、[誤検知](../confusion-matrix/)も 32 点に増えます。0.15 でも残る 4 点は、前節で正常クラスタの中に落ちていた 4 点です。

`contamination="auto"` は、異常の割合をデータから推定する設定ではありません。原論文のしきい値（`offset_ = -0.5`）を使う設定で、異常が 6.25%（20/320）のこのデータでは 40 点（12.5%）を異常と判定しました。誤検知と見逃しのどちらが高くつくかは業務で決まるので、ラベルの付いた少数の事例で上のように数えるか、[PR 曲線](../roc-pr-auc/)を見て決めます。

---

### 時系列の異常検知

時系列では、直前の一定区間（窓）の平均と[標準偏差](../../math/stddev/)で現在値を標準化し、|z| が 3 を超えたら異常とする rolling z-score がよく使われます。ただし、季節変動のある系列にそのまま当てると、変動そのものが標準偏差を膨らませます。

次のコードは、周期 50 の季節変動と右肩上がりのトレンドを持つ系列に +8 の異常を 4 か所足し、元の系列と、トレンドと季節変動を引いた残差の両方で |z| を計算します。

```python
import numpy as np
import pandas as pd

rng = np.random.default_rng(0)
t = np.arange(500)
# トレンド + 周期 50 の季節変動 + ノイズに、+8 の異常を 4 か所足す
y = 10 + 0.02 * t + 5 * np.sin(2 * np.pi * t / 50) + rng.normal(0, 0.8, 500)
anomalies = [120, 200, 320, 420]
y[anomalies] += 8
s = pd.Series(y)


def rolling_z(x, window=30):
    past = x.shift(1).rolling(window)  # 現在値を含まない直前 30 点
    return ((x - past.mean()) / past.std()).abs()


# 周期 50 の移動中央値でトレンドを、位相ごとの中央値で季節変動を推定して引く
trend = s.rolling(50, center=True, min_periods=1).median()
season = (s - trend).groupby(t % 50).transform("median")
resid = s - trend - season

is_normal = ~np.isin(t, anomalies)
for name, z in [("元の系列", rolling_z(s)), ("残差", rolling_z(resid))]:
    print(f"{name}: 異常 4 点の |z| = {z[anomalies].round(2).tolist()}")
    print(f"  正常点の |z| の最大 = {z[is_normal].max():.2f}")
    print(f"  |z| > 3 の時刻 = {np.where(z > 3)[0].tolist()}")
```

実行結果:

```text
元の系列: 異常 4 点の |z| = [2.83, 3.97, 2.74, 2.4]
  正常点の |z| の最大 = 3.49
  |z| > 3 の時刻 = [200, 478]
残差: 異常 4 点の |z| = [11.12, 11.79, 10.15, 6.73]
  正常点の |z| の最大 = 4.34
  |z| > 3 の時刻 = [120, 159, 200, 303, 320, 403, 420, 470, 481]
```

{{< figure src="anomaly_time_series.svg" alt="上段は右肩上がりで周期 50 の波を持つ系列と、+8 を足した 4 か所、元の系列で |z| > 3 になった点。下段は元の系列の |z| と残差の |z| を重ねた折れ線で、残差の |z| だけが 4 か所の異常で 6 を超えて大きく跳ねる" caption="元の系列と残差の rolling z-score" align="center" >}}

上段は元の系列と |z| > 3 になった点、下段は 2 通りの |z| で、緑の点線が異常を足した時刻です。

元の系列で見つかった異常は時刻 200 の 1 点だけで、時刻 478 の正常点を誤検知しました。窓の 30 点に振幅 5 の季節変動が入って標準偏差が大きくなり、+8 の異常でも |z| は 2.4〜3.97 です。正常点の最大 3.49 より小さい異常が 3 点あるので、しきい値をどう動かしても分けられません。

残差では、異常 4 点の |z| が 6.73〜11.79 まで上がり、正常点の最大 4.34 との間に差が開きます。|z| > 3 のままでは正常点も 5 点拾うので、しきい値を 5 程度に上げると 4 点だけが残ります。

上のコードは、移動平均と周期ごとの平均で分ける[古典的な分解](https://www.statsmodels.org/stable/generated/statsmodels.tsa.seasonal.seasonal_decompose.html)を中央値に置き換えたものです。LOESS を繰り返し当てて分ける [STL 分解](https://www.statsmodels.org/stable/generated/statsmodels.tsa.seasonal.STL.html)もあります。他にも次の手法があります。

- ARIMA などの予測モデルの残差を見る（[時系列予測](../time-series-forecasting/)）
- [Matrix Profile](https://www.cs.ucr.edu/~eamonn/MatrixProfile.html): 部分列同士の距離を総当たりで求め、似た部分列が他に無い区間を異常とする
- [Spectral Residual](https://arxiv.org/abs/1906.03821): Microsoft の異常検知サービスの論文で提案された手法。[Azure AI Anomaly Detector](https://learn.microsoft.com/azure/ai-services/anomaly-detector/) は 2026 年 10 月 1 日に提供を終えた
- LSTM の autoencoder で、再構成誤差の大きい区間を異常とする

---

### 関連する統計の道具とライブラリ

- 四分位範囲（IQR）で外れ値を決める Tukey のルール（[四分位点](../../math/quantile/)）
- 外れ値に引きずられにくい[中央値](../../math/median/)や MCD。Elliptic Envelope は MCD の平均と共分散からマハラノビス距離を測る
- [カーネル密度推定](../../math/kde/)や混合ガウス分布で、密度の低い点を異常とする
- [KL ダイバージェンス](../../math/information-theory/)で、点ではなく分布全体の変化を検出する

scikit-learn 以外では、[PyOD](https://github.com/yzhao062/pyod) が PyOD 3 の時点で 60 を超える検出器を同じ API で提供しています。画像の異常検知には [Anomalib](https://github.com/open-edge-platform/anomalib)、時系列には [tsod](https://github.com/DHI/tsod) があります。

---

### 適さないケース / 落とし穴

- 異常の定義が決まっていない: 何を見つけたいかを業務側と擦り合わせないと、検出しても使われない
- 異常のラベルが十分にある: [不均衡分類](../class-imbalance/)として教師あり学習で解いた方が精度が出ることが多い
- 特徴量のスケールが揃っていない: LOF・One-Class SVM・Elliptic Envelope が単位の大きい特徴量に引きずられる。先に[標準化](../standardization/)する
- 高次元で Elliptic Envelope を使う: 共分散行列の推定が不安定になる。scikit-learn はサンプル数を特徴量の数の 2 乗より多くするよう勧めている
- accuracy で評価する: 異常が 6.25% のデータでは、全て正常と答えても accuracy は 93.75% になる。Precision@k や [PR-AUC](../roc-pr-auc/) を使う
- 異常の傾向が変わる: 不正の手口や故障の起き方は変わるので、[定期的に再学習する](/ml/mlops/retraining-pipeline/)
- アラートを出しすぎる: 誤検知が多いと現場が通知を見なくなる。誤検知の数を数えてからしきい値を決める
- データ品質の問題と混同する: NULL の混入や[欠損](../missing-values/)は、異常検知より前のデータ品質チェックで扱う
