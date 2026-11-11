---
title: "特徴量選択（feature selection）"
date: 2026-05-26
draft: false
series: ["機械学習ノート", "Machine Learning"]
tags: ["machine-learning", "scikit-learn", "preprocessing"]
weight: 17
topics: ["Machine Learning（評価・概念・アルゴリズム）"]
---

特徴量選択（feature selection）は、使える特徴量の中からモデルにとって有用な部分集合を選び出し、それ以外を捨てる前処理です。目的は (1) [過学習](../overfitting/) の抑制、(2) 学習・推論コストの削減、(3) モデルの説明性向上、(4) [次元の呪い](../curse-of-dimensionality/) の緩和、の 4 点に集約されます。

[特徴量重要度](../feature-importance/) は、各特徴量をモデルがどれだけ利用しているかを調べます。特徴量選択では、その重要度などを手掛かりに、実際に残す列を決めます。

<br>

本記事では、正解の列が分かる人工データで、選択の根拠が異なる 3 系統を比べます。コードは [scikit-learn](https://scikit-learn.org/stable/modules/feature_selection.html) 1.9.1、[NumPy](https://numpy.org/) 2.5.4、[pandas](https://pandas.pydata.org/) 3.1.1 で実行しました。本文のコードは計算部分で、[Matplotlib](https://matplotlib.org/) の描画を含む[図の生成コード](https://github.com/nao1215/debimate/blob/main/projects/ml/scripts/notes/feature-selection_gen.py)は GitHub で公開しています。

---

### 3 系統の使い分け

{{< note-panels caption="選択方法は、何を根拠に残すかと、検証コストで選びます。" >}}
- title: Filter（フィルタ法）
  body: 分散や F 値など、各列の統計量で選びます。
- title: Wrapper（ラッパー法）
  body: 列の組み合わせを変え、モデルを繰り返し評価します。
- title: Embedded（埋め込み法）
  body: 正則化や木の分割など、学習の仕組みを使います。
{{< /note-panels >}}

Filter は候補を手早く減らせますが、列どうしの相互作用を見落とします。Wrapper はモデルの評価を繰り返す分だけ計算コストが増え、Embedded の結果は学習器に依存します。どの手法でも、未知データでの性能は別に確認します。

---

### Filter 法 1: VarianceThreshold

[`VarianceThreshold`](https://scikit-learn.org/stable/modules/generated/sklearn.feature_selection.VarianceThreshold.html) は最も軽量な手法です。[分散](/ml/math/variance/)がほぼゼロ（= 全サンプルでほぼ同じ値）の特徴量はモデルへの寄与が薄いので捨てます。

```python
import numpy as np
from sklearn.feature_selection import VarianceThreshold

# 各列の分散が異なる 5 つの特徴量
rng = np.random.default_rng(0)
n = 1000
X = np.column_stack([
    np.zeros(n) + rng.normal(0, 0.001, n),  # ほぼ定数
    rng.normal(0, 0.01, n),                 # 小分散
    rng.normal(0, 0.1, n),
    rng.normal(0, 1.0, n),
    rng.normal(0, 5.0, n),
])
vt = VarianceThreshold(threshold=0.05)
X_reduced = vt.fit_transform(X)
print(f"shape: {X.shape} -> {X_reduced.shape}")
```

出力:

```text
shape: (1000, 5) -> (1000, 2)
```

{{< figure src="featsel_variance_threshold.svg" alt="5 列の分散を対数軸で並べた横棒グラフ。分散 0.0000、0.0001、0.0096 の 3 列が閾値 0.05 の線より下で赤く除外され、分散 1.0173 と 24.1339 の 2 列が緑で残る" caption="VarianceThreshold で閾値未満の列を除外する" align="center" >}}

赤い棒（分散 < 0.05）が除外される特徴量、緑が保持される特徴量です。3 列目は標準偏差 0.1 なので分散は約 0.01 で、閾値 0.05 で落ちます。

分散は列の単位に依存します。同じ長さでも km で記録した列は m で記録した列の 100 万分の 1 の分散になり、単位だけで捨てられます。[標準化](../standardization/) の後では全列の分散が 1 になり、閾値が意味を失います。そのため VarianceThreshold は標準化の前に当て、閾値は `threshold=0.0`（全く動かない定数列だけ落とす）から試します。

---

### Filter 法 2: SelectKBest（F 検定・相互情報量）

[`SelectKBest`](https://scikit-learn.org/stable/modules/generated/sklearn.feature_selection.SelectKBest.html) は、統計的な指標で「目的変数との関係が強い」上位 `k` 個を残します。代表的なスコアは次の通りです。

- ANOVA F 値（[`f_classif`](https://scikit-learn.org/stable/modules/generated/sklearn.feature_selection.f_classif.html)）: 分類でクラス間とクラス内の平均差を分散比で見る単変量[検定](/ml/math/hypothesis-test/)。特徴量単独での有用性を測る
- 相互情報量（[`mutual_info_classif`](https://scikit-learn.org/stable/modules/generated/sklearn.feature_selection.mutual_info_classif.html)）: 非線形依存も含めた一般的な依存性
- カイ二乗（[`chi2`](https://scikit-learn.org/stable/modules/generated/sklearn.feature_selection.chi2.html)）: 非負特徴量とカテゴリ目的変数（テキスト分類で頻出）

データは [make_classification](https://scikit-learn.org/stable/modules/generated/sklearn.datasets.make_classification.html) で作ります。20 列のうち 5 列が予測に効く informative、2 列が informative の線形結合である redundant、残り 13 列がノイズです。

make_classification は既定で列を並べ替えるので、どの列が informative かは生成コードで `shuffle=False` の同じデータと突き合わせて調べました（informative は 1・7・10・12・17、redundant は 3・13）。

```python
from sklearn.datasets import make_classification
from sklearn.feature_selection import f_classif, mutual_info_classif

X, y = make_classification(n_samples=1500, n_features=20, n_informative=5,
                           n_redundant=2, random_state=0)
f_scores, _ = f_classif(X, y)
mi_scores = mutual_info_classif(X, y, random_state=0)
print(f"top-5 by F-test: {np.argsort(f_scores)[::-1][:5]}")
print(f"top-5 by MI:     {np.argsort(mi_scores)[::-1][:5]}")
print(f"column 1: F = {f_scores[1]:.2f}, MI = {mi_scores[1]:.3f}")
```

出力:

```text
top-5 by F-test: [10  7 17 12  3]
top-5 by MI:     [10  7  3 13 12]
column 1: F = 0.11, MI = 0.000
```

{{< figure src="featsel_filter_scores.svg" alt="20 列の F 検定と相互情報量の正規化スコアを、スコア順に並べた棒グラフ。横軸のラベルの inf が informative、red が redundant。上位は列 10、7、17、12 と redundant の 3、13 で、informative の列 1 はどちらのスコアもほぼ 0" caption="F 検定と相互情報量による列ごとのスコア" align="center" >}}

F 検定（青）と相互情報量（MI、橙）は、どちらも特徴量を 1 列ずつ単独で採点します。上位 5 列には redundant が F で 1 列、MI で 2 列入りました。redundant は informative と同じ情報を持つので、単独で見ると高い点が付きます。

informative の列 1 は F = 0.11、MI = 0 で、単独ではほぼ無関係に見えます。[ランダムフォレスト](../random-forest/)に残りの informative と一緒に渡すと、効き目が分かります。

```python
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score

rf = RandomForestClassifier(n_estimators=200, random_state=0)
for cols in ([7, 10, 12, 17], [1, 7, 10, 12, 17]):
    acc = cross_val_score(rf, X[:, cols], y, cv=5).mean()
    print(f"{cols}: {acc:.3f}")
```

出力:

```text
[7, 10, 12, 17]: 0.889
[1, 7, 10, 12, 17]: 0.914
```

列 1 は他の列と組み合わせて初めて効く列で、足すと 5-fold CV 正解率が 0.025 上がりました。Filter はこの種の列を落とすので、最終的な選択は交差検証で評価します。

`SelectKBest(score_func=f_classif, k=10).fit_transform(X, y)` のように 1 行で上位 `k` 個を取り出せます。

---

### Wrapper 法: RFE（recursive feature elimination）

RFE（[`RFE`](https://scikit-learn.org/stable/modules/generated/sklearn.feature_selection.RFE.html)、[Guyon et al., 2002](https://doi.org/10.1023/A:1012487302797)）は「全特徴量で学習 → 最も重要度の低い特徴量を 1 つ削除 → 残りで再学習」を繰り返し、最終的に指定した数の特徴量に絞ります。[`RFECV`](https://scikit-learn.org/stable/modules/generated/sklearn.feature_selection.RFECV.html) は [交差検証](../cross-validation/)（CV, cross-validation）と組み合わせて「精度が最大になる特徴量数」を自動探索します。

```python
from sklearn.feature_selection import RFECV
from sklearn.linear_model import LogisticRegression

estimator = LogisticRegression(max_iter=2000)
rfecv = RFECV(estimator, step=1, cv=5, scoring="accuracy").fit(X, y)
print(f"optimal n_features: {rfecv.n_features_}")
print(f"selected: {np.flatnonzero(rfecv.support_)}")
```

出力:

```text
optimal n_features: 5
selected: [ 3 10 13 15 17]
```

{{< figure src="featsel_rfe_cv.svg" alt="横軸が残した特徴量数、縦軸が 5-fold CV 正解率の折れ線と標準偏差の帯。1〜3 列では 0.79〜0.80、4 列以上は 0.809〜0.815 でほぼ平らで、最大の 5 列に赤い破線が引かれている" caption="RFECV の特徴量数と CV 正解率" align="center" >}}

横軸が残した特徴量数、縦軸が 5-fold CV 正解率の平均（青の帯は[標準偏差](/ml/math/stddev/)）です。赤い破線は平均が最大の 5 列（0.815）ですが、4 列以上はどれも 0.809〜0.815 で、差は標準偏差（0.015〜0.021）より小さい値でした。5 列が 20 列より確かに良いとは言えません。

選ばれた 5 列も正解と一致しません。informative は 10・17 の 2 列で、redundant の 3・13 とノイズの 15 が入りました。学習器が線形な[ロジスティック回帰](../logistic-regression/)なので、組み合わせで効く列 1 も拾えていません。

RFE は特徴量を減らすたびに学習と評価を繰り返すため、特徴量が増えると計算量も増えます。実行時間と検証スコアを確認して、使うかどうかを判断します。

---

### Embedded 法: Lasso と Tree importance

学習自体が特徴量選択を兼ねるアプローチです。代表は [Lasso](https://doi.org/10.1111/j.2517-6161.1996.tb02080.x)（L1 [正則化](../regularization/)）と木系モデルの組み込み重要度です。

- Lasso: L1 正則化で、効きの弱い特徴量の係数をちょうど 0 にする
- Tree importance: 分割で使われなかった特徴量は重要度 0

分類では、L1 正則化付きのロジスティック回帰を Lasso として使います。データは 30 列で、`shuffle=False` なので列 0〜7 が informative、8〜11 が redundant、12〜29 がノイズです。

```python
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

X, y = make_classification(n_samples=2000, n_features=30, n_informative=8,
                           n_redundant=4, shuffle=False, random_state=0)
for C in (0.5, 0.03):
    lasso = make_pipeline(StandardScaler(),
                          LogisticRegression(l1_ratio=1, solver="liblinear", C=C,
                                             max_iter=5000)).fit(X, y)
    print(f"Lasso C={C}: non-zero {np.flatnonzero(lasso[-1].coef_[0])}")
rf = RandomForestClassifier(n_estimators=200, random_state=0).fit(X, y)
print(f"RF top-12: {np.argsort(rf.feature_importances_)[::-1][:12]}")
```

出力:

```text
Lasso C=0.5: non-zero [ 0  1  3  4  5  7 11 12 14 15 16 17 18 19 20 21 22 24 25 26 27 28 29]
Lasso C=0.03: non-zero [ 0  1  3  4  5  7 11]
RF top-12: [10  0 11  1  4  7  9  8  6  3  5  2]
```

{{< figure src="featsel_embedded_compare.svg" alt="上から 3 段の棒グラフ。C=0.5 の Lasso は 30 列中 23 列に係数が残り、C=0.03 では 7 列だけになる。下段のランダムフォレストの重要度は informative と redundant の列が高く、ノイズ列も小さいがちょうど 0 にはならない。緑が informative、橙が redundant、灰色がノイズ" caption="Lasso の係数とランダムフォレストの重要度" align="center" >}}

C は正則化の強さの逆数で、小さいほど係数を 0 に寄せます。C = 0.5 では 30 列中 23 列が残り、ノイズ 18 列のうち 16 列に小さな係数が付きました。C = 0.03 にするとノイズは全て 0 になり、残りは 7 列です。

ただし informative の列 2・6 は、どちらの C でも 0 でした。残った redundant の列 11 は列 0〜7 の線形結合で、列 2・6 の成分も含みます。相関した列のどれを残すかは Lasso 任せになり、真の列が消えることもあります。

RF の重要度は上位 12 列が informative と redundant で占められ、最上位は redundant の列 10 です。ノイズ 18 列にも 0.008〜0.013 の値が付き、ちょうど 0 になる列はありませんでした。重要度を見れば効く列とノイズは分かれますが、redundant を informative と区別できません。

線形関係が支配的で係数を解釈したいなら Lasso、非線形や相互作用が効くなら木の重要度が向きます。どちらも [`SelectFromModel`](https://scikit-learn.org/stable/modules/generated/sklearn.feature_selection.SelectFromModel.html)`(`[`LassoCV`](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LassoCV.html)`())` や `SelectFromModel(RandomForestClassifier(), threshold="median")` のように包めば、しきい値で自動的に列を切れます。

---

### 多重共線性対策: 相関の強い特徴量を 1 つにまとめる

[相関係数](../../math/correlation/) のノートで触れた通り、相関の強い特徴量は (1) 線形モデルの係数を不安定にする、(2) ツリーの分割で重要度が分散する、という問題を起こします。相関行列を計算して、しきい値（例: `|r| > 0.9`）を超えるペアの片方を捨てるのも有効な特徴量選択になります。

```python
import pandas as pd

corr = pd.DataFrame(X).corr().abs()
upper = corr.where(np.triu(np.ones(corr.shape), k=1).astype(bool))
for th in (0.9, 0.7):
    to_drop = [col for col in upper.columns if any(upper[col] > th)]
    print(f"|r| > {th}: drop {to_drop}")
X_reduced = pd.DataFrame(X).drop(columns=to_drop)
```

出力:

```text
|r| > 0.9: drop []
|r| > 0.7: drop [10, 11]
```

前の節の 30 列のデータに当てると、`|r| > 0.9` では 1 列も落ちません。redundant の列は 8 列の informative の線形結合なので、2 列間の相関は最大でも 0.894（列 9 と 10）に留まります。0.7 まで下げると列 10・11 が落ちますが、redundant の列 8・9 は残ります。相関係数は 2 列ずつしか見ないので、3 列以上にまたがる線形従属は見逃します。

[PCA](../pca/) は相関のある特徴量を線形結合で集約して新しい軸を作ります。一方で、特徴量選択では元の特徴量から代表を 1 つ残します。元の特徴量を残せば、その特徴量の意味で結果を解釈できます。

---

### 数学での使いどころ

- 統計的検定と情報量: ANOVA F、`χ²`、[情報理論](/ml/math/information-theory/)の相互情報量 `I(X; Y) = Σ_xy P(x,y) log(P(x,y) / (P(x) P(y)))`
- L1 正則化の幾何: 制約集合 `|w|_1 ≤ c` は座標軸上に頂点を持ち、頂点では一部の `w_k` が 0 になる
- 部分集合選択の組合せ爆発: `d` 列の部分集合は `2^d` 通りあり、最適な組を探すのは NP 困難なので、RFE のような貪欲法で近似する

---

### 機械学習での使いどころ

- 高次元データ（テキスト、ゲノム）: 入力次元を減らし、[バイアス-バリアンス](../bias-variance-tradeoff/) のバリアンス側を抑える
- 推論のレイテンシやデータ収集のコストを下げる: 効かない列の計算と収集を止める
- 特徴量エンジニアリングの反復: 追加した列が予測に役立つかを評価する

scikit-learn には上記の他に、列を 1 つずつ足す・引く [`SequentialFeatureSelector`](https://scikit-learn.org/stable/modules/generated/sklearn.feature_selection.SequentialFeatureSelector.html) もあります。

---

### 適さないケース / 落とし穴

- データリーク: テストデータも含めて選択すると、テストの情報が訓練に流れ込む（[data leakage](../data-leakage/)）。[`Pipeline`](https://scikit-learn.org/stable/modules/generated/sklearn.pipeline.Pipeline.html) に入れて CV の fold ごとに選択する
- Filter・相関・Lasso の結果をそのまま正解の列と見なす: 本記事の例では、どれも組み合わせで効く列や相関した列を取り違えた
- 木の組み込み重要度を信じすぎる: 値の種類が多い列ほど重要度が高く出る（[特徴量重要度](../feature-importance/) 参照）
- [カテゴリ変数をダミー化](../categorical-encoding/)してから列単位で選ぶ: カテゴリの一部の列だけ残る。グループ単位で扱う
- 特徴量設計の代わりに使う: 元データに情報が無ければ、選択しても精度は上がらない
- PCA と混同する: PCA は新しい軸を作り、特徴量選択は元の列を残す。説明性が目的なら特徴量選択を使う
