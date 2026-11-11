---
title: "交差検証 - cv=3 で正解率 97% の iris が、KFold(3) と書くと 0% になる理由"
date: 2026-05-24
draft: false
series: ["機械学習ノート", "Machine Learning"]
tags: ["machine-learning", "scikit-learn", "model-evaluation"]
weight: 9
topics: ["Machine Learning（評価・概念・アルゴリズム）"]
---

交差検証（cross validation、CV）は、手元のデータを学習用と検証用に何通りも分け直し、それぞれで測ったスコアを平均してモデルの性能を見積もる手法です。1 回だけ分けて測ると、どの行が検証側に入ったかの運でスコアが大きく動くので、分け方を変えながら平均を取ります。

以下は、[scikit-learn](https://scikit-learn.org/stable/) に同梱の [iris](https://archive.ics.uci.edu/dataset/53/iris) を 3 通りの書き方で 3 分割し、[ロジスティック回帰](../logistic-regression/)で品種を当てた結果です。iris は 3 品種のアヤメ 150 本について、がく片と花びらの長さと幅を並べたデータです。図の 1 行が 1 回分の分け方で、濃いマスが検証に使う行、薄いマスが学習に使う行を表します。

{{< figure src="cv_cover.webp" alt="3 段の図。1 段目の KFold(3) は、1 回目は setosa の 50 行、2 回目は versicolor の 50 行、3 回目は virginica の 50 行がそのまま検証になり、正解率の平均は 0.00。2 段目の KFold(3, shuffle=True) は、検証の行が 3 品種に散らばり、平均 0.97。3 段目の cv=3 は、各品種の 3 分の 1 ずつが検証になり、平均 0.97" caption="iris を 3 通りの書き方で 3 分割した時の、検証に回る行と正解率（scikit-learn 1.9.1）" align="center" >}}

scikit-learn で交差検証を回す関数 `cross_val_score` に `cv=3` と書くと正解率は 97% で、`cv=KFold(3)` と書くと 0% になりました。iris の行は品種の順に 50 行ずつ並んでいて、`KFold` は既定では行を混ぜずに前から切るので、1 回目は setosa だけを検証に回し、学習側には setosa が 1 行もありません。見たことのない品種を当てる問題になり、3 回とも 1 行も当たりませんでした。

手元の CSV で交差検証を書く時も、行は日付順・ユーザー順・地域順のように何かの順に並んでいるのが普通です。`cv=5` を `KFold(5, shuffle=True)` に書き換えたらスコアが上がった、あるいは本番の精度が交差検証のスコアより低かった、という場面では、どの分け方の数字を信じるかを決める必要があります。

<br>

本記事では、ML を学び始めた人と、scikit-learn の交差検証を手元のデータに使う人に向けて、次の疑問に答えます。

- 交差検証は、1 回の分割と比べて何が良いのか。
- `cv=3` と `KFold(3)` は、なぜ結果が分かれるのか。
- shuffle で上がったスコアは、信じてよいのか。
- 交差検証で選んだハイパーパラメータのスコアは、本番の目安になるのか。
- 分け方は、どの順に選べばよいのか。

実験は scikit-learn 1.9.1 で行いました。図を描く処理も含めた完全なコードは [cross-validation_gen.py](https://github.com/nao1215/debimate/blob/main/projects/ml/scripts/notes/cross-validation_gen.py) にあります。

---

### 1 回の分割と K 分割

最もよく使う交差検証は、K 分割交差検証（K-Fold）です。データを `k` 個に分け、1 つを検証用、残りの `k-1` 個を学習用にしてモデルを学習し、検証用のスコアを測ります。これを検証に回す 1 つを変えながら `k` 回繰り返し、`k` 個のスコアを平均します。分けた 1 つずつを fold と呼びます。

{{< figure src="cv_split.webp" alt="20 件のデータを 4 件ずつ 5 つに分けた図。1 回目から 5 回目の 5 行で、赤い検証の 4 件が左から右へ 1 つずつずれ、残りの 16 件が薄い青の学習になる" caption="5 分割の分け方。どの行も 1 回ずつ検証に回る" align="center" >}}

どの行も 1 回ずつ検証に回るので、全ての行を評価に使えます。代わりに、モデルの学習は `k` 回になります。scikit-learn では [`KFold`](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.KFold.html) が分け方を決め、[`cross_val_score`](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.cross_val_score.html) が学習と検証を `k` 回繰り返します。

1 回の分割のスコアがどれだけ運で変わるかを確かめるために、`make_regression` で作った 60 件・特徴量 50 個の回帰の人工データを使います。50 個の特徴量のうち、答えに効くのは 10 個だけです。

モデルは [Ridge](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.Ridge.html) 回帰です。Ridge は、係数が大きくなりすぎないように抑える[正則化](../regularization/)を入れた線形回帰で、`alpha` がその強さです。コードの `train_test_split` は、8 割で学習して 2 割で測る 1 回の分割を作る関数です。分け方の乱数を変えながら、この 1 回の分割と 5 分割の平均を 200 回ずつ求めます。

```python
X, y = make_regression(n_samples=60, n_features=50, n_informative=10, noise=20, random_state=0)

holdout, cv_mean = [], []
for seed in range(200):
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=seed)
    holdout.append(Ridge(alpha=1.0).fit(X_tr, y_tr).score(X_te, y_te))
    cv = KFold(n_splits=5, shuffle=True, random_state=seed)
    cv_mean.append(cross_val_score(Ridge(alpha=1.0), X, y, cv=cv).mean())
holdout, cv_mean = np.array(holdout), np.array(cv_mean)
print(f"1 回の分割: 最小 {holdout.min():.3f}、最大 {holdout.max():.3f}、標準偏差 {holdout.std():.3f}")
print(f"5 分割の平均: 最小 {cv_mean.min():.3f}、最大 {cv_mean.max():.3f}、標準偏差 {cv_mean.std():.3f}")
```

```text
1 回の分割: 最小 0.280、最大 0.958、標準偏差 0.099
5 分割の平均: 最小 0.646、最大 0.893、標準偏差 0.043
```

スコアは[決定係数](../regression-metrics/)の R² で、1 なら完全に当たり、0 なら平均値を返すだけの予測と同じです。以下は、200 回分の R² の分布です。

{{< figure src="cv_holdout_spread.webp" alt="ヒストグラム。灰色の 1 回の分割は R² が 0.28 から 0.96 まで広がり、0.9 付近と 0.6 以下にも山の裾がある。青い 5 分割の平均は 0.65〜0.89 に収まり、0.8〜0.85 に集まる" caption="分け方の乱数だけ変えて、同じモデルで 200 回評価した時の R²" align="center" >}}

同じモデルなのに、1 回の分割の R² は 0.280 から 0.958 まで動きました。5 分割の平均にすると、ばらつきの[標準偏差](../../math/stddev/)は 0.099 から 0.043 と半分以下になります。検証に使う行が 12 件から 60 件に増え、たまたま当てやすい行や外れ値を引いた影響が薄まるからです。

ただし、5 分割の平均も 0.646〜0.893 の幅で動いています。2 つのモデルの差が 0.01 しかないなら、分け方の乱数を変えても同じ順位になるかを確かめた方が安全と言えます。

---

### cv=3 と KFold(3) の違い

冒頭の 0% は、分け方の運ではなく既定値の違いから起きています。以下は、冒頭の図の 3 通りを比べたコードです。

```python
iris = load_iris()
Xi, yi = iris.data, iris.target
print("iris の y の並び:", yi[:3], "…", yi[48:53], "…", yi[-3:])
clf = LogisticRegression(max_iter=1000)
cases = [("KFold(3)", KFold(n_splits=3)),
         ("KFold(3, shuffle=True)", KFold(n_splits=3, shuffle=True, random_state=0)),
         ("cv=3", 3)]
for label, cv in cases:
    scores = cross_val_score(clf, Xi, yi, cv=cv)
    print(f"{label}: 各回 {scores.round(2)}、平均 {scores.mean():.3f}")
```

```text
iris の y の並び: [0 0 0] … [0 0 1 1 1] … [2 2 2]
KFold(3): 各回 [0. 0. 0.]、平均 0.000
KFold(3, shuffle=True): 各回 [0.98 0.96 0.96]、平均 0.967
cv=3: 各回 [0.98 0.96 0.98]、平均 0.973
```

`KFold` の `shuffle` の既定は `False` で、行を前から順に `k` 個に切ります。iris は品種の番号 0・1・2 の順に 50 行ずつ並んでいるので、3 分割すると、各回の検証が 1 品種そのものになります。

`cv=3` のように数を渡した時は、`cross_val_score` が分け方を選びます。[`cross_val_score` の文書](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.cross_val_score.html)によると、モデルが分類器で、正解が 2 値か多クラスなら [`StratifiedKFold`](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.StratifiedKFold.html)、それ以外は `KFold` を使い、どちらも shuffle しません。

`StratifiedKFold` は、各 fold のクラスの比率を全体と同じに揃える分け方です。冒頭の図の 3 段目のとおり、行を混ぜなくても、各品種の 3 分の 1 ずつを検証に回すので、学習側に 3 品種が揃います。1 回の分割で同じように比率を揃える `train_test_split` の `stratify=y` は、[不均衡データ](../class-imbalance/)のノートの実験で使っています。

<br>

自分で `KFold(5)` と書くと、分類器でもこの置き換えは起きません。回帰のモデルに `cv=5` と書いた時も、中身は shuffle しない `KFold(5)` です。どちらも、行の並びがそのまま fold の切れ目になります。次の節では、回帰で shuffle の有無がスコアを変える例を見ます。

---

### shuffle で上がったスコア

scikit-learn に同梱の [California Housing](https://scikit-learn.org/stable/modules/generated/sklearn.datasets.fetch_california_housing.html) は、1990 年のアメリカの国勢調査から、カリフォルニア州の区画ごとに住宅価格の中央値と、所得・築年数・部屋数・緯度・経度など 8 列を並べた 20640 行のデータです。この住宅価格を[勾配ブースティング](../gradient-boosting/)の [`HistGradientBoostingRegressor`](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.HistGradientBoostingRegressor.html) で当て、5 分割の R² を 3 通りの分け方で測りました。

3 つ目の [`GroupKFold`](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.GroupKFold.html) は、同じグループの行を必ず同じ fold に入れる分け方です。ここでは緯度と経度を 0.5 度、南北でおよそ 55km ごとのマス目に切り、同じマスの区画を 1 つのグループにしました。グループは 176 個です。

最後のループでは、検証の各区画のすぐ近くに学習側の区画があるかを見るために、学習側で一番近い区画までの距離を求めます。その距離が 0 の行、つまり同じ地点の区画が学習側にある行の割合と、0.3 度以上離れた行の割合を出します。緯度の 0.3 度は、南北でおよそ 33km です。

```python
housing = fetch_california_housing()
Xh, yh = housing.data, housing.target
lat, lon = Xh[:, 6], Xh[:, 7]
# 緯度と経度を 0.5 度ごとのマス目に切り、同じマスの区画を 1 つのグループにする
groups = np.floor(lat / 0.5).astype(int) * 1000 + np.floor(lon / 0.5).astype(int)
reg = HistGradientBoostingRegressor(random_state=0)
house_cases = [("cv=5（KFold、shuffle なし）", KFold(n_splits=5), None),
               ("KFold(5, shuffle=True)", KFold(n_splits=5, shuffle=True, random_state=0), None),
               ("GroupKFold(5)、0.5 度のマス目", GroupKFold(n_splits=5), groups)]
nn_coords = np.column_stack((lat, lon))
for label, cv, g in house_cases:
    scores = cross_val_score(reg, Xh, yh, cv=cv, groups=g)
    # 検証の各区画から、学習側で一番近い区画までの距離（度）
    dists = []
    folds = list(cv.split(Xh, yh, g))
    for tr, te in folds:
        nn = NearestNeighbors(n_neighbors=1).fit(nn_coords[tr])
        dists.append(nn.kneighbors(nn_coords[te])[0].ravel())
    d = np.concatenate(dists)
    same, far = (d == 0).mean(), (d >= 0.3).mean()  # 同じ地点が学習側にある割合、0.3 度以上離れた割合
    print(f"{label}: R² の平均 {scores.mean():.3f}、同じ地点が学習側にある {same:.1%}、最寄りが 0.3 度以上先 {far:.1%}")
```

```text
cv=5（KFold、shuffle なし）: R² の平均 0.690、同じ地点が学習側にある 1.5%、最寄りが 0.3 度以上先 17.9%
KFold(5, shuffle=True): R² の平均 0.836、同じ地点が学習側にある 54.9%、最寄りが 0.3 度以上先 0.1%
GroupKFold(5)、0.5 度のマス目: R² の平均 0.730、同じ地点が学習側にある 0.0%、最寄りが 0.3 度以上先 1.1%
```

同じモデル・同じデータで、R² の平均は 0.690、0.836、0.730 と分かれました。以下は、各区画を地図の位置に置き、何回目の検証に回ったかで色を分けた図です。

{{< figure src="cv_california.webp" alt="カリフォルニア州の形に並んだ 3 枚の点の地図。左の cv=5 は、同じ色の点が地域ごとに大きな塊になり、R² の平均 0.69、同じ地点が学習側にある割合 1%。中央の KFold(5, shuffle=True) は 5 色の点が全域で細かく混ざり、R² の平均 0.84、同じ地点 55%。右の GroupKFold(5) は、0.5 度のマス目ごとに同じ色の塊になり、R² の平均 0.73、同じ地点 0%" caption="California Housing の各区画が何回目の検証に回ったか（色）と、5 分割の R² の平均" align="center" >}}

左の図のとおり、このデータの行は地域ごとにまとまって並んでいて、shuffle しない `cv=5` は地域の塊ごとに検証へ回します。shuffle すると、中央の図のように検証の区画が全域に散らばり、すぐ隣の区画が学習側に入ります。

shuffle した時、検証の行の 54.9% は、同じ地点の区画が学習側にある状態で当てています。このデータでは、20640 行のうち 60% の行が、緯度と経度が完全に同じ別の行を持つからです。マス目ごとに分けた `GroupKFold` では、同じ地点の区画は必ず同じ fold に入るので、この割合は 0% です。以下は、出力の 2 つの割合を分け方ごとに並べた図です。

{{< figure src="cv_california_nearby.webp" alt="3 組の横棒。cv=5 は同じ地点が学習側にある割合 1.5%、最寄りが 0.3 度以上先の割合 17.9%、R² 0.690。KFold(5, shuffle=True) は 54.9% と 0.1%、R² 0.836。GroupKFold(5) は 0.0% と 1.1%、R² 0.730" caption="検証の行の近くに学習側の区画が残る割合と、5 分割の R² の平均" align="center" >}}

一方で、shuffle しない `cv=5` が `GroupKFold` より低いのは、もう 1 つの数字で説明できます。`cv=5` は地域の大きな塊を丸ごと外すので、検証の行の 17.9% は、学習側の最寄りの区画が 0.3 度以上先にあります。`GroupKFold` のマス目は小さく散らばっているので、隣のマス目の区画が学習側に残り、その割合は 1.1% です。同じ地点の割合が最も高い shuffle の R² が最も高く、0.3 度以上先の割合が最も高い `cv=5` の R² が最も低い、という対応です。

<br>

どの数字を信じるかは、モデルを何に使うかで決まります。既に学習データがある地域の中で、欠けた区画の価格を埋めるなら、shuffle した 0.836 が使い方に近い評価です。学習データの無い地域へ広げて使うなら、マス目ごとに分けた 0.730 の方が近く、0.836 は 0.1 ほど楽観的です。緯度と経度だけで近さを測る [kNN](../knn/) では、この差がさらに開き、行を混ぜた 0.801 が地域ごとに外すと 0.237 まで落ちます。近くに学習データの無い区画が多い使い方なら、遠い行の割合が 17.9% と最も多い `cv=5` の 0.690 も参考になると考えられます。

同じことは、同じユーザーや同じ患者の記録が複数の行にあるデータでも起きます。同じ人の行が学習側と検証側に分かれると、モデルはその人の癖を覚えて当てられるので、新しい人に使う時より高く出ます。人の ID をグループにして `GroupKFold` で分けます。

行が日付の順に並ぶ時系列では、shuffle すると未来の行で学習して過去を当てることになります。時間の順を保つ [`TimeSeriesSplit`](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html) と、その実験は[時系列予測](../time-series-forecasting/)のノートで扱っています。

---

### 選んだ後のスコアは楽観的になる

交差検証は、モデルの性能を測るだけでなく、[ハイパーパラメータ](../hyperparameter/)を選ぶ時にも使います。最初の節の 60 件の人工データで、Ridge の `alpha` を 0.01 から 1000 まで 20 通り変え、5 分割の R² を測りました。比べるために、同じ作り方の 300 件のデータでも測っています。

{{< figure src="cv_alpha.webp" alt="横軸は Ridge の alpha（0.01〜1000 の対数目盛）、縦軸は 5 分割の R² の平均と標準偏差。60 件の曲線は alpha = 2.34 の縦の点線で最大の山型で、左側ほど標準偏差の線が長い。300 件の曲線は alpha = 10 付近まで 0.98 で平らで、その先で下がる" caption="Ridge の alpha と 5 分割の R²" align="center" >}}

60 件の曲線は山型で、`alpha=2.34` で最大になります。`alpha` が小さすぎると[過学習](../overfitting/)で、学習データの雑音まで覚えて検証のスコアが下がります。大きすぎると係数を 0 に寄せすぎて、何も当てられなくなります。300 件の曲線は `alpha=10` 付近まで平らで、特徴量の数に対してデータが十分にあれば、正則化が弱くても過学習しにくいことが分かります。

学習データだけで `alpha` を決めることはできません。学習データのスコアは正則化が弱いほど高くなるので、いつも一番小さい `alpha` を選んでしまうからです。

<br>

以下のコードは、最初に `alpha` を 2 つ固定して fold ごとのスコアを見ます。次に [`GridSearchCV`](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.GridSearchCV.html) で 20 通りを比べて選び、最後に、選ぶ処理ごと外側の 5 分割で改めて測ります。この最後の測り方を nested CV と呼びます。

nested CV は、外側の各回で、学習側のデータだけを使って内側の 5 分割で `alpha` を選び、外側の検証で測ります。外側の検証の行は、`alpha` を選ぶ時に一度も見ていません。コードでは、`alpha` を選ぶ `GridSearchCV` を 1 つのモデルとみなし、`cross_val_score` に渡すことでこの形にしています。

```python
alphas = np.logspace(-2, 3, 20)
cv = KFold(n_splits=5, shuffle=True, random_state=0)
for alpha in (0.01, 1.0):
    scores = cross_val_score(Ridge(alpha=alpha), X, y, cv=cv)
    print(f"alpha={alpha}: 各回 {scores.round(3)}、平均 {scores.mean():.3f}、標準偏差 {scores.std():.3f}")
grid = GridSearchCV(Ridge(), param_grid={"alpha": alphas}, cv=cv).fit(X, y)
print(f"選んだ alpha: {grid.best_params_['alpha']:.3f}、その時の 5 分割の R²: {grid.best_score_:.3f}")
outer = KFold(n_splits=5, shuffle=True, random_state=1)
nested = cross_val_score(GridSearchCV(Ridge(), param_grid={"alpha": alphas}, cv=cv), X, y, cv=outer)
print(f"nested CV の R²: 各回 {nested.round(3)}、平均 {nested.mean():.3f}")
```

```text
alpha=0.01: 各回 [-0.974  0.364  0.658  0.613  0.826]、平均 0.298、標準偏差 0.653
alpha=1.0: 各回 [0.714 0.935 0.817 0.836 0.957]、平均 0.852、標準偏差 0.088
選んだ alpha: 2.336、その時の 5 分割の R²: 0.860
nested CV の R²: 各回 [0.923 0.792 0.806 0.769 0.756]、平均 0.809
```

`alpha=0.01` の 1 回目の fold は R² が -0.974 で、平均値を返すだけの予測にも負けています。残りの fold は 0.364〜0.826 なので、1 回の分割で評価していたら、どの fold を引いたかで結論が変わったはずです。

`GridSearchCV` が選んだ 2.336 は、図の点線と同じ値です。その時の 5 分割の R² は 0.860 ですが、nested CV で改めて測ると 0.809 でした。20 通りの中から、同じ 5 分割で一番良く見えたものを選んだので、0.860 にはその分割にたまたま合った分が含まれています。

scikit-learn の例「[Nested versus non-nested cross-validation](https://scikit-learn.org/stable/auto_examples/model_selection/plot_nested_cross_validation_iris.html)」も iris で同じ差を示しています。選ぶ処理による楽観は、Cawley と Talbot の論文「[On Over-fitting in Model Selection and Subsequent Selection Bias in Performance Evaluation](https://jmlr.org/papers/v11/cawley10a.html)」で詳しく調べられています。

標準化のような前処理も、選ぶ処理と同じく、交差検証の外で全データに当てると検証の行の情報が学習側に漏れます。scikit-learn の pipeline で前処理とモデルを 1 つのモデルのようにつなぐと、分割ごとに学習側だけで前処理を当てられます。その書き方は、[データリーク](../data-leakage/)のノートで扱っています。

---

### 分け方を選ぶ順

交差検証を書く前に、まずデータの行が何の順に並んでいるかを見ます。冒頭の iris のように正解の順に並んでいれば、shuffle しない `KFold` は見たことのないクラスを当てる問題になります。分類なら `StratifiedKFold`、回帰なら `KFold(shuffle=True)` を明示し、`cv=5` のような数だけの指定に任せない方が、何で分けたかが読み返して分かります。

以下は、本記事で使った分け方と、検証に回る行、実験の結果を並べた表です。住宅は California Housing の R² で、iris は正解率です。

| 分け方 | 検証に回る行 | 本記事の結果 |
|---|---|---|
| `KFold`（shuffle なし） | 並びの前から順に切った塊 | iris 0.000、住宅 0.690 |
| `KFold(shuffle=True)` | 全体から散らばった行 | iris 0.967、住宅 0.836 |
| `StratifiedKFold` | 各クラスから同じ比率 | iris 0.973 |
| `GroupKFold` | グループごとの塊 | 住宅 0.730 |
| `TimeSeriesSplit` | 学習より後の期間 | [時系列予測](../time-series-forecasting/)で扱う |

次に、同じ人・同じ地点・同じ時期のように、互いに似た行のまとまりがあるかを考えます。あれば、本番でモデルが当てる相手が、学習に使ったまとまりの中か外かを決めます。外なら `GroupKFold` でまとまりごとに分け、時間の順があれば `TimeSeriesSplit` を使います。California Housing の 0.836 と 0.730 の差が、この選び方で動く大きさの一例です。

<br>

ハイパーパラメータを交差検証で選んだなら、選んだ時のスコアをそのまま報告しません。nested CV で改めて測るか、最初に取り分けて一度も見ていないテスト用のデータで 1 回だけ測ります。前の節では 0.860 が 0.809 に下がりました。

最後に、モデルの差がスコアの揺れより大きいかを確かめます。1 回の分割の R² は、同じモデルでも 0.280 から 0.958 まで動きました。5 分割の平均にしても標準偏差 0.043 の揺れが残るので、比べるモデルの差がそれより小さければ、分け方の乱数を変えて何度か測ります。

交差検証のスコアが本番より高く出た時は、冒頭の図のように、どの行が検証に回っていたかを描いてみると、分け方の問題かどうかが見えてきます。
