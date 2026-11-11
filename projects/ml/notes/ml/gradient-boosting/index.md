---
title: "Gradient Boosting - 10,000 行では毎回同じ結果が、1 行足すと学習のたびに変わる理由"
date: 2026-05-24
draft: false
series: ["機械学習ノート", "Machine Learning"]
tags: ["machine-learning", "scikit-learn", "supervised"]
weight: 24
topics: ["Machine Learning（評価・概念・アルゴリズム）"]
---

勾配ブースティング（gradient boosting）は、浅い[決定木](../decision-tree/)を 1 本ずつ足し、それまでの予測が外した分を次の木に当てさせる教師あり学習の手法です。Friedman の論文「[Greedy function approximation: A gradient boosting machine](https://doi.org/10.1214/aos/1013203451)」（2001 年）で提案されました。表の形のデータでよく使われ、[scikit-learn](https://scikit-learn.org/stable/) には、素直に実装した [`GradientBoostingRegressor`](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.GradientBoostingRegressor.html) と、計算を速くした [`HistGradientBoostingRegressor`](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.HistGradientBoostingRegressor.html) があります。分類なら、名前の Regressor を Classifier に変えたものです。

以下は、scikit-learn に同梱の [California Housing](https://scikit-learn.org/stable/modules/generated/sklearn.datasets.fetch_california_housing.html) で、学習に使う行数を変えながら `HistGradientBoostingRegressor` を既定の設定のまま 10 回ずつ学習した結果です。California Housing は、1990 年のアメリカの国勢調査から、カリフォルニア州の区画ごとに住宅価格の中央値と、所得・築年数・緯度・経度など 8 列を並べた 20640 行のデータです。

縦軸は、学習に使わずに取り分けたテストデータで測った[決定係数](../regression-metrics/) R² です。1 なら全て当たり、0 なら平均値を返すだけの予測と同じです。

{{< figure src="gradient-boosting_cover.webp" alt="横軸は学習に使った行数で、8,000、9,000、10,000、10,001、11,000、12,000、14,000、16,000 の 8 つ。縦軸はテストデータの R²。10,000 行までは 10 回の点が 1 つに重なり、R² は 0.827 前後。10,001 行からは 10 回の点が縦にばらけ、10,001 行では 0.825〜0.830 に散らばる" caption="既定の設定のまま 10 回ずつ学習した時のテストデータの R²（scikit-learn 1.9.1）" align="center" >}}

10,000 行までは 10 回とも同じ R² で、1 行足した 10,001 行からは 10 回とも違う値になりました。`HistGradientBoostingRegressor` は、渡された行が 10,000 を超えると、その 10% を学習に使わずに取り分けます。取り分けた行は、木を 1 本足すごとに予測の誤差を測るためだけに使い、誤差が下がらなくなった所で木を足すのを止めます。取り分ける行は、学習のたびに乱数で選ばれます。

手元の CSV で試す時も、数千行のサンプルで試した時は何度学習しても同じスコアだったのに、全データで学習し直したら実行のたびに小数点以下 3 桁目が動く、という場面があります。木の本数の上限を `max_iter=1000` と書いたのに、学習した木が数百本しかないこともあります。どちらもバグではなく、既定値どおりの動きです。

<br>

本記事では、ML を学び始めた人と、scikit-learn の勾配ブースティングを手元のデータに使う人に向けて、次の疑問に答えます。

- 勾配ブースティングは、何を順に足していくのか。
- learning_rate と木の本数は、どう関係するのか。
- 学習を途中で止める仕組みは、どの時点のモデルを返すのか。
- RandomForest と比べ、速さと精度はどう違うのか。
- 10,000 行を超えると、なぜ結果が学習のたびに変わるのか。

実験は scikit-learn 1.9.1 で行いました。図を描く処理も含めた完全なコードは [gradient-boosting_gen.py](https://github.com/nao1215/debimate/blob/main/projects/ml/scripts/notes/gradient-boosting_gen.py) にあります。

---

### 残差に木を足していく仕組み

勾配ブースティングの最初の予測は、全ての行で同じ値です。回帰なら正解 `y` の平均を使います。次に、正解から今の予測を引いた残差を求め、その残差を当てる浅い決定木を 1 本学習します。その木の予測をそのまま足さず、`learning_rate` という係数を掛けてから今の予測に足します。0.5 なら、木が当てた残差の半分だけ予測を動かします。以下は、1 次元の人工データでこの手順の最初の 1 回を描いた図です。

{{< figure src="gradient-boosting_residual.webp" alt="3 つの図。左は青い点のデータに、y の平均 0.6 ほどの水平な赤い線が重なる。中央はオレンジの点の残差（y − 平均）に、1 本目の木の予測が階段で重なり、残差の上下を追う。右はデータに、平均だけの灰色の破線と、平均に 0.5 倍した 1 本目の予測を足した赤い階段を重ね、赤い方がデータに近い" caption="最初の予測（平均）の残差を 1 本目の木が当て、0.5 倍して足す（learning_rate=0.5、深さ 3 の木）" align="center" >}}

木の入力は元の `x` のままで、当てる相手だけが `y` から残差に変わります。右の図のように、平均に 0.5 倍した木の予測を足すと、元のデータに少し近づきます。2 本目の木は、この新しい予測の残差を当てます。これを繰り返し、最終的な予測は、平均に全ての木の出力を `learning_rate` 倍して足した和になります。

<br>

以下のコードは、この手順を 10 行ほどのループで書き、scikit-learn の `GradientBoostingRegressor` と同じ予測になるかを確かめます。

```python
rng = np.random.default_rng(0)
x = np.linspace(-3, 3, 200).reshape(-1, 1)
y_true = np.sin(x.ravel()) * 1.5 + 0.2 * x.ravel() ** 2
y = y_true + 0.3 * rng.standard_normal(200)

learning_rate = 0.5
F = np.full(len(y), y.mean())  # 最初の予測は、全ての行で y の平均
for i in range(50):
    residual = y - F  # ここまでの予測が外した分
    tree = DecisionTreeRegressor(max_depth=3, random_state=0).fit(x, residual)
    F = F + learning_rate * tree.predict(x)  # 残差を当てた木の予測に learning_rate を掛けて足す

gbr = GradientBoostingRegressor(n_estimators=50, learning_rate=0.5, max_depth=3, random_state=0).fit(x, y)
print("手書きのループと GradientBoostingRegressor の予測の差の最大:", np.abs(F - gbr.predict(x)).max())
```

```text
手書きのループと GradientBoostingRegressor の予測の差の最大: 0.0
```

差は 0 で、二乗誤差の回帰では、`GradientBoostingRegressor` の中身はこのループそのものです。

勾配という名前は、[損失関数](../loss-functions/)の[勾配](../../math/partial-derivative-gradient/)から来ています。1 行の損失を `(y - F)² / 2` とすると、予測 `F` で微分した勾配は `-(y - F)` で、符号を反転すると残差 `y - F` そのものになります。つまり残差を当てる木は、損失が減る向きを当てる木です。分類では損失関数が交差エントロピーに変わるので、その勾配の符号を反転した値が残差の代わりになります。

以下は、同じループで足した木の本数ごとの予測です。

{{< figure src="gradient-boosting_progressive_fit.webp" alt="4 つの図。灰色の点のデータと、データを作った関数の緑の破線に、赤い予測を重ねる。木 1 本では粗い階段、3 本で関数に沿い始め、10 本でほぼ重なる。50 本では予測が細かく上下に揺れ、点の雑音まで追っている" caption="足した木の本数ごとの予測（learning_rate=0.5、深さ 3）" align="center" >}}

10 本でデータを作った関数にほぼ重なり、50 本では雑音の点まで追って予測が細かく揺れます。足し続けると学習データにだけ合う[過学習](../overfitting/)になるので、何本で止めるかが次の問題になります。

<br>

同じく決定木を何本も使う [RandomForest](../random-forest/) は、深い木を互いに独立に作って予測を平均します。勾配ブースティングは、前の木の結果を見て次の木を作るので、木を並べて同時に作れません。複数のモデルをまとめる手法の全体は、[アンサンブル学習](../ensemble-learning/)で扱っています。

---

### learning_rate と木の本数

`learning_rate` を小さくすると、1 本の木で動かす量が減るので、同じ所まで届くのに要る木の本数が増えます。ここからは California Housing を使い、テストデータとは別に、学習用のデータから検証データを取り分けます。誤差は平均二乗誤差で測ります。予測と正解の差を二乗して平均した値で、小さいほど当たっています。

検証データは、学習に使わずに本数などの設定を選ぶためのデータで、テストデータは選び終えた後の評価に 1 回だけ使います。テストデータで本数を選ぶと、その分だけ未知のデータでの性能を楽観的に見積もるからです。

<br>

以降の実験は、速い方の `HistGradientBoostingRegressor` を使います。2 つの実装の違いは後の節で比べます。以下のコードは、`learning_rate` を 4 通りに変えて木を 1000 本まで足し、1 本足すごとに検証データの平均二乗誤差を測ります。`early_stopping=False` は、次の節で扱う、学習を途中で止める仕組みを切る指定です。

```python
X, y = fetch_california_housing(return_X_y=True)
# テスト用の 2 割は、最後の評価にだけ使う
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=0)
# 学習用の残りから、さらに 2 割を検証用に取り分け、本数や learning_rate の比較に使う
X_fit, X_val, y_fit, y_val = train_test_split(X_train, y_train, test_size=0.2, random_state=0)

curves = {}
for lr in [1.0, 0.5, 0.1, 0.01]:
    model = HistGradientBoostingRegressor(learning_rate=lr, max_iter=1000, early_stopping=False,
                                          random_state=0).fit(X_fit, y_fit)
    # staged_predict は、木を 1 本足すごとの予測を順に返す
    mse = np.array([mean_squared_error(y_val, p) for p in model.staged_predict(X_val)])
    curves[lr] = mse
    print(f"learning_rate={lr}: 最小は {mse.argmin() + 1} 本で {mse.min():.4f}、"
          f"100 本で {mse[99]:.4f}、1000 本で {mse[-1]:.4f}")
```

```text
learning_rate=1.0: 最小は 13 本で 0.3137、100 本で 0.3614、1000 本で 0.3855
learning_rate=0.5: 最小は 87 本で 0.2472、100 本で 0.2514、1000 本で 0.2667
learning_rate=0.1: 最小は 761 本で 0.2039、100 本で 0.2253、1000 本で 0.2043
learning_rate=0.01: 最小は 1000 本で 0.2236、100 本で 0.5303、1000 本で 0.2236
```

以下は、この 4 本の曲線です。

{{< figure src="gradient-boosting_learning_rate.webp" alt="横軸は足した木の本数で 1〜1000 の対数目盛、縦軸は検証データの平均二乗誤差。learning_rate 1.0 の赤は 13 本で 0.31 の底を打って上がり続け、0.5 のオレンジは 87 本で 0.25 の底から緩やかに上がる。0.1 の緑は 761 本で 0.204 まで下がり、0.01 の青は 1000 本でもまだ下がっていて 0.224" caption="learning_rate ごとの、足した木の本数と検証データの平均二乗誤差（点は各曲線の最小）" align="center" >}}

`learning_rate=1.0` は 13 本で底を打ち、その後は木を足すほど検証データの誤差が増えます。0.1 は 761 本まで下がり、底の値も 0.2039 と 4 つの中で最も低くなりました。0.01 は 1000 本でもまだ下がり続けています。

小さい `learning_rate` ほど底は低くなりやすい一方で、底に届くまでの木の本数と学習の時間が増えます。そのため、`learning_rate` は 0.05〜0.1 ほどに固定し、本数は検証データの誤差を見て決めるやり方がよく使われます。その本数を自動で決めるのが、次の節の仕組みです。

---

### 学習を途中で止める early stopping

early stopping（早期停止）は、木を 1 本足すごとに検証データの誤差を測り、決めた本数だけ続けて良くならなければ、その時点で学習を止める仕組みです。`HistGradientBoostingRegressor` では、何本続けて良くならなければ止めるかを `n_iter_no_change` で決め、既定は 10 本です。

検証データは、学習用のデータから `validation_fraction` の割合で自動で取り分けます。既定は 10% です。以下のコードでは、前の節と比べられるように、前の節と同じ検証データを `X_val` と `y_val` で渡しています。

止めるかの判定に使った誤差は `validation_score_` に入っていますが、損失として二乗誤差の半分を使い、大きいほど良い値にするため負号を付けています。そのため、コードでは -2 倍して平均二乗誤差に戻しています。

```python
es = HistGradientBoostingRegressor(max_iter=1000, early_stopping=True, n_iter_no_change=10,
                                   random_state=0).fit(X_fit, y_fit, X_val=X_val, y_val=y_val)
# validation_score_ は、0 本目からの検証データの損失に負号を付けた値
val_mse = -2 * es.validation_score_
best = int(val_mse.argmin())
print(f"止まった本数（n_iter_）: {es.n_iter_}、検証データの誤差が最小だった本数: {best}")
print(f"止まった時点の検証データの平均二乗誤差: {val_mse[es.n_iter_]:.4f}、"
      f"1000 本まで足した時の最小: {curves[0.1].min():.4f}（{curves[0.1].argmin() + 1} 本）")
full = HistGradientBoostingRegressor(max_iter=1000, early_stopping=False, random_state=0).fit(X_fit, y_fit)
print(f"テストデータの平均二乗誤差: {es.n_iter_} 本で止めたモデル "
      f"{mean_squared_error(y_test, es.predict(X_test)):.4f}、"
      f"1000 本のモデル {mean_squared_error(y_test, full.predict(X_test)):.4f}")
```

```text
止まった本数（n_iter_）: 345、検証データの誤差が最小だった本数: 335
止まった時点の検証データの平均二乗誤差: 0.2088、1000 本まで足した時の最小: 0.2039（761 本）
テストデータの平均二乗誤差: 345 本で止めたモデル 0.1977、1000 本のモデル 0.1971
```

以下は、前の節の `learning_rate=0.1` の曲線に、early stopping で止めた所を重ねた図です。

{{< figure src="gradient-boosting_early_stopping.webp" alt="横軸は足した木の本数 0〜1000、縦軸は検証データの平均二乗誤差。緑の線は early stopping で止めた場合で、345 本の赤い破線で終わる。灰色の線は 1000 本まで足した場合で、345 本の先も 0.209 から緩やかに下がり、761 本で最小の 0.204 になる" caption="early stopping が止めた本数と、1000 本まで足した場合の検証データの平均二乗誤差（learning_rate=0.1）" align="center" >}}

`n_iter_` は、学習した木の本数です。検証データの誤差は 335 本で最小になり、その後 10 本続けて下がらなかったので、345 本で止まりました。scikit-learn は最小だった 335 本に戻さず、止まった時点の 345 本のモデルをそのまま返します。

灰色の線のとおり、345 本の先でも誤差は 761 本まで緩やかに下がります。それでも、テストデータの平均二乗誤差は 345 本で 0.1977、1000 本で 0.1971 と、ほとんど変わりませんでした。このデータでは、木の本数を 3 分の 1 にしても精度はほぼ同じで、学習と予測の時間が減ります。

---

### RandomForest と 2 つの実装の比較

`HistGradientBoostingRegressor` は、各列の値を最大 255 個の区間に分け、分岐の候補を区間の境目だけに絞ります。区間ごとの行の数を数えた表をヒストグラムと呼ぶのが、名前の由来です。`GradientBoostingRegressor` は、全ての値を分岐の候補として調べます。

以下のコードは、California Housing の学習用のデータ全体で 3 つのモデルを既定値のまま学習し、テストデータの R²・保存した時の大きさ・学習の時間を測ります。学習は全て 1 スレッドに揃え、時間は 3 回学習した中央値を取りました。最後の行の `do_early_stopping_` は、その学習で early stopping を使ったかを表す属性です。

```python
models = {
    "RandomForestRegressor": lambda: RandomForestRegressor(random_state=0),
    "GradientBoostingRegressor": lambda: GradientBoostingRegressor(random_state=0),
    "HistGradientBoostingRegressor": lambda: HistGradientBoostingRegressor(random_state=0),
}
results, seconds = {}, {}
for name, make in models.items():
    times = []
    for _ in range(3):  # 3 回学習した時間の中央値を取る
        model = make()
        start = time.perf_counter()
        model.fit(X_train, y_train)
        times.append(time.perf_counter() - start)
    seconds[name] = np.median(times)
    size_mb = len(pickle.dumps(model)) / 1e6  # 保存した時の大きさ
    results[name] = (model.score(X_test, y_test), size_mb)
    print(f"{name}: テストの R² {model.score(X_test, y_test):.3f}、大きさ {size_mb:.2f} MB")
hgb = model
print("HistGradientBoostingRegressor の early stopping:", hgb.do_early_stopping_, "、木の本数:", hgb.n_iter_)
for name, sec in seconds.items():
    print(f"{name}: 学習 {sec:.2f} 秒")
```

```text
RandomForestRegressor: テストの R² 0.798、大きさ 144.77 MB
GradientBoostingRegressor: テストの R² 0.777、大きさ 0.14 MB
HistGradientBoostingRegressor: テストの R² 0.837、大きさ 0.37 MB
HistGradientBoostingRegressor の early stopping: True 、木の本数: 100
```

出力の残りの 3 行は学習の時間で、下の折り畳みに置きました。

{{< figure src="gradient-boosting_models.webp" alt="2 つの横棒グラフ。テストデータの R² は RandomForest 0.798、GradientBoosting 0.777、HistGradientBoosting 0.837。保存した大きさは 144.77 MB、0.14 MB、0.37 MB" caption="California Housing で、3 つのモデルを既定値のまま学習した時の R² と大きさ" align="center" >}}

3 つの中で R² が最も高かったのは `HistGradientBoostingRegressor` で、学習の時間も、何度測っても他の 2 つより 1 桁以上短くなりました。RandomForest は R² 0.798 で、保存すると 145MB ありました。深さを制限しない木を 100 本持つので、`HistGradientBoostingRegressor` の約 400 倍の大きさです。

<br>

<details><summary>学習の時間の測定値と条件</summary>

32 スレッドの機械で、学習を 1 スレッドに制限し、3 回学習した中央値を取りました。同じ機械では他の重い処理も同時に動いていたので、秒数は流し直すたびに大きく動きます。以下は、最後に流した時の出力です。

```text
RandomForestRegressor: 学習 12.41 秒
GradientBoostingRegressor: 学習 3.94 秒
HistGradientBoostingRegressor: 学習 0.29 秒
```

6 回流した範囲は、RandomForest が 6.64〜12.41 秒、GradientBoosting が 2.22〜5.68 秒、HistGradientBoosting が 0.12〜0.35 秒でした。同じ回の中で比べると、HistGradientBoosting は GradientBoosting の 13〜22 分の 1、RandomForest の 19 分の 1 以下の時間でした。

</details>

<br>

R² の差には、既定値の違いも入っています。以下は、3 つの既定値を並べた表です。

| | RandomForest | GradientBoosting | HistGradientBoosting |
|---|---|---|---|
| 木の数 | 100 本を平均 | 100 本を足す | 最大 100 本を足す |
| 1 本の木の大きさ | 制限なし | 深さ 3 | 葉 31 枚 |
| early stopping | なし | なし | 10,000 行を超えると入る |

葉は、決定木の分岐の先にある、予測値を持つ末端です。`GradientBoostingRegressor` の深さ 3 の木は、葉が最大 8 枚です。`HistGradientBoostingRegressor` の木は葉が 31 枚まで育つので、1 本で表せる形が多く、同じ 100 本でも R² が高くなったと考えられます。

表の最後の行が、冒頭の図の境目です。学習用のデータは 16512 行なので、出力の最後の行のとおり、この比較の `HistGradientBoostingRegressor` でも early stopping が入っていました。100 本の上限に先に届いたので止まってはいませんが、学習に使ったのは 16512 行の 90% です。

---

### 10,000 行の境目で変わること

`HistGradientBoostingRegressor` の `early_stopping` の既定は `'auto'` で、[scikit-learn 1.9.1 の文書](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.HistGradientBoostingRegressor.html)には「行数が 10,000 より多ければ early stopping を使う」とあります。検証データは `validation_fraction` の既定の 10% で、どの行を選ぶかは `random_state` で決まります。`random_state` の既定は `None` で、学習のたびに違う乱数を使います。

<br>

以下は、冒頭の図を作ったコードです。学習用のデータから同じ順に `n` 行を取り、既定の設定で 10 回学習します。同じ行で `max_iter=1000` も 10 回学習し、木の本数を数えます。

最初の `np.random.seed(0)` は、本記事の数字を再現できるようにするためだけの行です。`random_state` を渡さない学習は NumPy の大域の乱数を順に使うので、10 回の学習は互いに違う乱数を使い、スクリプト全体を流し直した時だけ同じ結果になります。

```python
np.random.seed(0)
order = np.random.RandomState(0).permutation(len(X_train))
sizes = [8000, 9000, 10000, 10001, 11000, 12000, 14000, 16000]
r2_default, n_iter_1000 = {}, {}
for n in sizes:
    rows = order[:n]  # 学習用のデータから、同じ順に n 行を使う
    fits = [HistGradientBoostingRegressor().fit(X_train[rows], y_train[rows]) for _ in range(10)]
    r2_default[n] = [m.score(X_test, y_test) for m in fits]
    long_fits = [HistGradientBoostingRegressor(max_iter=1000).fit(X_train[rows], y_train[rows])
                 for _ in range(10)]
    n_iter_1000[n] = [m.n_iter_ for m in long_fits]
    print(f"{n:>5} 行: early stopping {fits[0].do_early_stopping_}、"
          f"R² {min(r2_default[n]):.4f}〜{max(r2_default[n]):.4f}、"
          f"max_iter=1000 の木の本数 {min(n_iter_1000[n])}〜{max(n_iter_1000[n])}")
```

```text
 8000 行: early stopping False、R² 0.8272〜0.8272、max_iter=1000 の木の本数 1000〜1000
 9000 行: early stopping False、R² 0.8267〜0.8267、max_iter=1000 の木の本数 1000〜1000
10000 行: early stopping False、R² 0.8273〜0.8273、max_iter=1000 の木の本数 1000〜1000
10001 行: early stopping True、R² 0.8253〜0.8295、max_iter=1000 の木の本数 100〜249
11000 行: early stopping True、R² 0.8264〜0.8331、max_iter=1000 の木の本数 99〜216
12000 行: early stopping True、R² 0.8260〜0.8332、max_iter=1000 の木の本数 140〜281
14000 行: early stopping True、R² 0.8315〜0.8370、max_iter=1000 の木の本数 129〜280
16000 行: early stopping True、R² 0.8331〜0.8366、max_iter=1000 の木の本数 125〜334
```

10,000 行までは `do_early_stopping_` が `False` で、R² の最小と最大が一致し、`max_iter=1000` の木は 10 回とも 1000 本です。10,001 行からは `True` になり、R² は 10 回とも違い、木の本数は 99〜334 本に散らばりました。以下は、その木の本数を並べた図です。

{{< figure src="gradient-boosting_n_iter.webp" alt="横軸は学習に使った行数で、冒頭の図と同じ 8 つ。縦軸は max_iter=1000 で学習した木の本数。10,000 行までは 10 回とも 1000 本で点が重なる。10,001 行からは 99〜334 本に 10 個の点が散らばる" caption="max_iter=1000 で 10 回ずつ学習した時の木の本数" align="center" >}}

10,001 行では、1 行足しただけで、学習する木が 1000 本から 100〜249 本に減り、学習に使う行は 10,001 行から 9,000 行ほどに減ります。R² が学習のたびに変わるのは、検証データに回る 1,000 行ほどが毎回入れ替わり、学習に使う行と止まる本数が変わるからです。

<br>

10,001 行のまま、`random_state` を固定した場合と、early stopping を切った場合も 10 回ずつ学習しました。

```python
rows = order[:10001]
for label, params in [("random_state=0", {"random_state": 0}), ("early_stopping=False", {"early_stopping": False})]:
    scores = [HistGradientBoostingRegressor(**params).fit(X_train[rows], y_train[rows]).score(X_test, y_test)
              for _ in range(10)]
    print(f"10001 行、{label}: R² {min(scores):.4f}〜{max(scores):.4f}")
```

```text
10001 行、random_state=0: R² 0.8286〜0.8286
10001 行、early_stopping=False: R² 0.8272〜0.8272
```

どちらでも 10 回とも同じ R² になりました。`random_state=0` は検証データの選び方を固定し、`early_stopping=False` は検証データを取り分けずに全ての行で 100 本を学習します。どちらが良いかは、このデータでは決められないほどの差です。

<br>

この境目は、[交差検証](../cross-validation/)でも効きます。データ全体が 12,000 行でも、5 分割の学習側は 9,600 行で、early stopping は入りません。同じ設定で全データを学習し直した本番のモデルだけが、10% を検証に回して途中で止まります。交差検証で測ったモデルと本番のモデルの作り方を揃えるなら、`early_stopping` を `True` か `False` に明示します。

---

### 表のデータで最初に試す時に確かめること

勾配ブースティングを手元の表のデータに使う時は、まず `HistGradientBoostingRegressor` か `HistGradientBoostingClassifier` から始めます。前の節の比較のとおり、California Housing では `GradientBoostingRegressor` より 1 桁以上短い時間で学習し、既定値のままで最も高い R² でした。比べる相手として、[線形回帰](../linear-regression/)か[ロジスティック回帰](../logistic-regression/)、RandomForest のスコアも同じ分け方で測っておきます。数百行ほどの小さいデータでは、木を何百本も足す前にデータが足りなくなるので、これらの方が安定することがあります。

次に、`early_stopping` と `random_state` を明示します。冒頭の図のように、書かなければ行数が 10,000 を超えたかどうかで、検証用に 10% を取り分けるか、学習のたびに結果が変わるかが黙って切り替わります。以下は、本記事の実験と scikit-learn 1.9.1 の文書から、書き方ごとの振る舞いを並べた表です。

| 書き方 | 10,000 行以下 | 10,001 行以上 |
|---|---|---|
| 何も書かない | 全ての行で学習し、毎回同じ | 10% を検証に回し、毎回変わる |
| `early_stopping=False` | 全ての行で学習し、毎回同じ | 全ての行で学習し、毎回同じ |
| `random_state=0` だけ | 全ての行で学習し、毎回同じ | 10% を検証に回し、毎回同じ |

学習の後には `n_iter_` を見て、`max_iter` の上限まで学習したのか、途中で止まったのかを確かめます。

<br>

`learning_rate` は 0.05〜0.1 ほどに固定し、`max_iter` を大きめにして early stopping に本数を決めさせると、調整する値を減らせます。葉の数のような残りの[ハイパーパラメータ](../hyperparameter/)は、交差検証のスコアで選びます。

列の前処理は、他のモデルより少なく済みます。`HistGradientBoostingClassifier` は欠損値をそのまま受け取れるので、[欠損値](../missing-values/)を補完する前に試せます。カテゴリの列の扱いは[カテゴリ変数のエンコーディング](../categorical-encoding/)で、日付の順に並ぶデータで前の時点の値を列として足す作り方は[時系列予測](../time-series-forecasting/)で扱っています。

学習した後に、どの列が効いたかを見るなら[特徴量重要度](../feature-importance/)を使います。分類で出した確率をそのまま判断に使うなら、その確率が実際の割合と合っているかを[確率の校正](../probability-calibration/)で確かめます。

同じ設定で 2 回学習してスコアが変わったら、冒頭の図のように、学習に渡した行数が 10,000 を超えていないかを最初に見てください。
