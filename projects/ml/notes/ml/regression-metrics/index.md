---
title: "回帰の評価指標（RMSE / MAE / R²）- 誤差が一番小さい地域で R² が一番低くなる"
date: 2026-05-26
draft: false
series: ["機械学習ノート", "Machine Learning"]
tags: ["machine-learning", "scikit-learn", "metrics"]
weight: 3
topics: ["Machine Learning（評価・概念・アルゴリズム）"]
---

回帰の評価指標は、数値を当てるモデルの予測と正解のずれを 1 つの数にまとめた値です。よく使われるのは RMSE（Root Mean Squared Error、二乗平均平方根誤差）、MAE（Mean Absolute Error、平均絶対誤差）、R²（決定係数）の 3 つです。RMSE と MAE はずれの大きさの目安で、予測する値と同じ単位を持ち、小さいほど良い値です。R² は単位を持たず、1 に近いほど良い値です。

[scikit-learn](https://scikit-learn.org/stable/) で取得できる [California Housing](https://scikit-learn.org/stable/modules/generated/sklearn.datasets.fetch_california_housing.html) は、1990 年に米国で行われた国勢調査から、カリフォルニア州の 20,640 地区について、住宅価格の中央値と、所得・築年数・緯度・経度などの 8 列を並べたデータです。住宅価格の単位は 10 万ドルです。地区の 75% で[勾配ブースティング](../gradient-boosting/)のモデルを学習し、残り 25% の地区で、緯度と経度から 3 つの地域に分けて RMSE を出しました。

```python
X, y = fetch_california_housing(return_X_y=True, as_frame=True)  # y の単位は 10 万ドル
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=0)
model = HistGradientBoostingRegressor(random_state=0).fit(X_train, y_train)
pred = model.predict(X_test)

lat, lon = X_test["Latitude"], X_test["Longitude"]
regions = {
    "ベイエリア": (37.2 < lat) & (lat < 38.3) & (lon < -121.5),
    "ロサンゼルス": (33.6 < lat) & (lat < 34.4) & (-118.7 < lon) & (lon < -117.6),
    "セントラルバレー": (35.0 < lat) & (lat < 38.5) & (-121.5 < lon) & (lon < -118.5),
}
for name, mask in regions.items():
    rmse = root_mean_squared_error(y_test[mask], pred[mask])
    print(f"{name:<8} {mask.sum():>5} 件  RMSE {rmse:.3f}")
```

```text
ベイエリア     1005 件  RMSE 0.514
ロサンゼルス    1834 件  RMSE 0.493
セントラルバレー   643 件  RMSE 0.337
```

セントラルバレーの RMSE は 0.337、金額にすると 3.4 万ドルで、他の 2 つの地域の 5 万ドル前後より小さい値です。では、同じ 3 つの地域で R² を出すと、一番高いのはどの地域でしょうか。

{{< figure src="rm_cover.webp" alt="3 枚の散布図。横軸は正解の住宅価格、縦軸は予測で、どちらも 0〜5.6（10 万ドル）。左のベイエリアは RMSE 0.51・R² 0.80、中央のロサンゼルスは RMSE 0.49・R² 0.80 で、点は 0.5〜5 まで対角線に沿って広く並ぶ。右の赤いセントラルバレーは RMSE 0.34・R² 0.63 で、点は 0.5〜3 の狭い範囲に集まる" caption="同じモデルを地域ごとに測った RMSE と R²" align="center" >}}

答えは、RMSE が一番小さいセントラルバレーが、R² では一番低い 0.631 でした。ベイエリアは RMSE 0.514 で、R² は 0.804 です。同じモデル、同じ関数で、エラーも警告も出ていません。散布図を見ると、セントラルバレーの点は、正解が 0.5〜3 の狭い範囲に集まっています。

地域・店舗・月ごとにモデルの性能を表にまとめる時、R² だけを並べると「セントラルバレーの予測が一番弱い」と読めてしまいます。外れる金額で見れば、一番当たっているのはセントラルバレーです。

<br>

本記事では、ML を学び始めたエンジニアと、scikit-learn で手元のデータに回帰モデルを当てはめる人に向けて、次の疑問に答えます。

- RMSE・MAE・R² は、それぞれ何を何と比べた値か。
- 誤差の小さい地域で、R² が低くなるのはなぜか。
- RMSE と MAE で、良いモデルの順位は入れ替わるか。
- 割合で外れを測る MAPE は、どんな予測を高く評価するか。
- scikit-learn で出す時に、どの関数と符号に気を付けるか。

実験は scikit-learn 1.9.1 と [NumPy](https://numpy.org/) 2.5.4 で行いました。図を描く処理も含めた完全なコードは [regression-metrics_gen.py](https://github.com/nao1215/debimate/blob/main/projects/ml/scripts/notes/regression-metrics_gen.py) にあります。

---

### 3 つの指標の式

`n` 件の正解を `y_i`、予測を `ŷ_i` とすると、3 つの指標は次の式です。

- MAE: `mean(|y_i − ŷ_i|)`。ずれを絶対値にして平均した値。
- MSE: `mean((y_i − ŷ_i)^2)`。ずれを 2 乗して平均した値で、平均二乗誤差と呼ぶ。
- RMSE: `sqrt(MSE)`。MSE の平方根で、単位を `y` に戻した値。
- R²: `1 − MSE / mean((y_i − ȳ)^2)`。`ȳ` は評価に使った正解の平均。

R² の分母は、評価データにある正解の分散です。分散は、全ての行に正解の平均 `ȳ` を予測として返した時の MSE とも読めます。

R² は、平均を返すだけの予測と比べてモデルの MSE がどこまで減ったかを表す値で、`MSE / 分散` を 1 から引いて求めます。最大は 1 で、0 なら平均を返すだけの予測と同じ、平均より外れるモデルでは負になります。[分散](../../math/variance/)の定義と、分散が外れ値に引っ張られる性質は数学のノートで扱っています。

冒頭の 3 つの地域とテスト全体で、MSE と分散を別々に計算し、`1 − MSE / 分散` が `r2_score` と一致するかを見ます。

```python
rows = list(regions.items()) + [("テスト全体", np.ones(len(y_test), dtype=bool))]
for name, mask in rows:
    yt, yp = y_test[mask].to_numpy(), pred[mask]
    mse = np.mean((yt - yp) ** 2)
    var = np.mean((yt - yt.mean()) ** 2)  # 評価データ自身の平均を当てた時の MSE
    print(f"{name:<8} MSE {mse:.3f}  分散 {var:.3f}  1 - MSE/分散 {1 - mse / var:.3f}"
          f"  r2_score {r2_score(yt, yp):.3f}")
```

```text
ベイエリア    MSE 0.264  分散 1.346  1 - MSE/分散 0.804  r2_score 0.804
ロサンゼルス   MSE 0.243  分散 1.210  1 - MSE/分散 0.799  r2_score 0.799
セントラルバレー MSE 0.114  分散 0.308  1 - MSE/分散 0.631  r2_score 0.631
テスト全体    MSE 0.219  分散 1.322  1 - MSE/分散 0.835  r2_score 0.835
```

---

### R² の分母は評価データの広がり

{{< figure src="rm_r2_ratio.webp" alt="左はテストデータの地区を緯度と経度で描いた地図で、価格の高い地区ほど濃い。青い枠のベイエリアとロサンゼルスには濃い点と薄い点が混ざり、赤い枠のセントラルバレーは薄い点がほとんど。右は地域ごとに、灰色の正解の分散と赤いモデルの MSE を並べた横棒で、ベイエリアは 1.346 と 0.264 で R² 0.804、ロサンゼルスは 1.210 と 0.243 で 0.799、セントラルバレーは 0.308 と 0.114 で 0.631、テスト全体は 1.322 と 0.219 で 0.835" caption="R² は、モデルの MSE を正解の分散で割って 1 から引いた値" align="center" >}}

右の図で、赤い棒は、セントラルバレーが一番短く、モデルは 3 つの地域の中で一番小さく外れています。ところが灰色の棒、つまり正解の分散も 0.308 と、ベイエリアの 4 分の 1 以下です。左の地図のとおり、セントラルバレーは安い地区がほとんどで、価格が狭い範囲に集まっています。平均を返すだけの予測でもあまり外れないので、モデルが減らせる割合が小さくなり、R² は 0.631 に留まりました。

R² は、評価データの広がりを物差しにした値です。広がりの違う評価データの間で R² を比べると、モデルの良し悪しと、データの広がりの違いが混ざります。scikit-learn の[文書](https://scikit-learn.org/stable/modules/model_evaluation.html#r2-score-the-coefficient-of-determination)も、R² はデータに依存するので、別のデータで測った値は比べられないと注意しています。正解の範囲で絞った評価では、この影響がはっきり出ます。

```python
band = (y_test >= 1.5) & (y_test < 2.5)  # 正解が 15 万〜25 万ドルの地区
print(f"正解が 1.5〜2.5 の {band.sum()} 件  RMSE {root_mean_squared_error(y_test[band], pred[band]):.3f}"
      f"  R² {r2_score(y_test[band], pred[band]):.3f}")
```

```text
正解が 1.5〜2.5 の 1790 件  RMSE 0.375  R² -0.673
```

テスト全体の RMSE は、前の出力にある MSE 0.219 から平方根を取った 0.467 です。正解が 15 万〜25 万ドルの地区だけで測ると、RMSE はそれより小さい 0.375 なのに、R² は負になりました。この範囲では正解の分散が小さく、平均を返すだけの予測の方が MSE が小さいためです。

逆に、同じ評価データと同じサンプル重みで 2 つのモデルを比べるなら、分母は共通なので、MSE の小さいモデルほど R² は大きくなり、順位は MSE や RMSE と必ず一致します。[交差検証](../cross-validation/)のスコアに R² を使っても問題が無いのは、同じ分割で比べているからです。

R² は、学習に使わなかったテストデータか交差検証で測ります。学習データで測る R² は、特徴量を足すほど上がり、[過学習](../overfitting/)を見落とします。訓練データと検証データの RMSE を並べ、その差から過学習を読む見方は[バイアス-バリアンス分解](../bias-variance-tradeoff/)で扱っています。

特徴量の数で補正した自由度調整済み決定係数（adjusted R²）もありますが、テストデータで測るなら補正は要りません。テストデータの R² が負になったら、評価の範囲を絞った以外に、モデルがデータの形に合っていないこと、過学習、[学習時と分布が変わること](../../mlops/data-drift/)、学習データに無い範囲への予測、特徴量の不足を疑います。

<br>

#### R² は相関係数の 2 乗とは別の値

R² を「予測と正解から求めた[相関係数](../../math/correlation/)を 2 乗した値」と覚えていると、もう 1 つ食い違いに出会います。全ての予測に同じ値を足して、2 つを比べました。

```python
for shift in [0.0, 0.3, 0.6]:
    q = pred + shift
    print(f"+{shift:.1f}  R² {r2_score(y_test, q):.3f}  相関の 2 乗 {np.corrcoef(y_test, q)[0, 1] ** 2:.3f}")
```

```text
+0.0  R² 0.835  相関の 2 乗 0.835
+0.3  R² 0.760  相関の 2 乗 0.835
+0.6  R² 0.549  相関の 2 乗 0.835
```

相関係数は、予測が正解と一緒に増減するかだけを見るので、全体が 6 万ドル高くずれても 0.835 のままです。R² はずれた分だけ MSE が増えるので、0.549 まで下がります。

+0.0 の行で 2 つが揃ったのは、このモデルの予測に全体のずれがほとんど無く、たまたま近い値になったためです。必ず一致するのは、[線形回帰](../linear-regression/)の最小二乗法で切片を含めて当てはめ、その学習データで評価した時です。この条件では、R² は正解の変動のうち予測で説明できた割合とも読めます。

---

### RMSE と MAE で入れ替わる順位

RMSE と MAE は、どちらもずれを正解と同じ単位で表しますが、大きく外した行の数え方が違います。RMSE はずれを 2 乗してから平均するので、ずれが 2 倍の行は 4 倍、10 倍の行は 100 倍の重みで MSE に入ります。

この違いは、全ての行に同じ 1 つの値を返す、一番単純な予測で見えます。MSE を一番小さくする定数は正解の[平均](../../math/mean/)で、MAE を一番小さくする定数は[中央値](../../math/median/)です。住宅価格は高い側に長く裾を引く分布で、平均 2.07 は中央値 1.80 より大きくなります。

学習で小さくする量を[損失関数](../loss-functions/)と呼びます。次に、勾配ブースティングの損失関数として、MSE に当たる `loss="squared_error"`（既定）と MAE に当たる `loss="absolute_error"` で学習したモデルを比べました。データを 5 つに分け、1 つをテスト、残りを学習に使う組を 5 回繰り返しています。

```python
Xa, ya = X.to_numpy(), y.to_numpy()
names = ["平均を返す", "中央値を返す", "squared_error", "absolute_error"]
scores = {n: [] for n in names}
for tr, te in KFold(5, shuffle=True, random_state=0).split(Xa):
    preds = {"平均を返す": np.full(len(te), ya[tr].mean()),
             "中央値を返す": np.full(len(te), np.median(ya[tr]))}
    for loss in ["squared_error", "absolute_error"]:
        m = HistGradientBoostingRegressor(loss=loss, random_state=0).fit(Xa[tr], ya[tr])
        preds[loss] = m.predict(Xa[te])
    for n in names:
        scores[n].append([root_mean_squared_error(ya[te], preds[n]),
                          mean_absolute_error(ya[te], preds[n]),
                          mean_absolute_percentage_error(ya[te], preds[n])])
```

| 予測 | RMSE | MAE | MAPE |
|---|---|---|---|
| 全ての行に平均を返す | 1.154 | 0.912 | 0.621 |
| 全ての行に中央値を返す | 1.185 | 0.884 | 0.527 |
| `loss="squared_error"` で学習 | 0.467 | 0.312 | 0.177 |
| `loss="absolute_error"` で学習 | 0.495 | 0.314 | 0.168 |

表の値は 5 回の平均で、MAPE は次の節で説明する割合の指標です。定数の 2 行は、RMSE では平均を返す方が、MAE では中央値を返す方が良く、順位が入れ替わります。

学習したモデルの 2 行では、`absolute_error` で学習しても MAE は 0.314 で、`squared_error` の 0.312 とほぼ同じでした。RMSE は 6% ほど悪くなり、MAPE は 5% ほど良くなっています。5 回の 1 回ずつで、`absolute_error` の値を `squared_error` の値で割りました。

{{< figure src="rm_loss_folds.webp" alt="横軸に RMSE・MAE・MAPE の 3 列、縦軸は absolute_error の値を squared_error の値で割った比で、1.0 に点線。RMSE の 5 点は全て 1.05〜1.07 で赤、平均 1.061。MAE の 5 点は 0.99〜1.02 で点線をまたぐ灰色、平均 1.005。MAPE の 5 点は全て 0.93〜0.95 で緑、平均 0.947" caption="absolute_error で学習したモデルの値 ÷ squared_error で学習したモデルの値（5 分割）" align="center" >}}

5 回の全てで、RMSE は `squared_error` が、MAPE は `absolute_error` が良く、MAE は回によってどちらが良いかが変わりました。報告に RMSE を使うなら `squared_error` のモデルが、MAPE を使うなら `absolute_error` のモデルが選ばれます。学習で小さくした量と同じ指標で勝つとは限らない点は、損失関数の選び方にも関わります。`absolute_error` は、定数の時と同じく、中央値に寄せた予測を返すように学習する損失です。

<br>

#### 大きく外した 5% が RMSE を決める

RMSE が大きな外れにどれだけ引っ張られるかを見るため、冒頭のテストデータで誤差の大きい順に行を並べ、上位の行が 2 乗誤差の和と絶対誤差の和のうち何割を占めるかを数えました。

```python
err = np.abs(y_test.to_numpy() - pred)
order = np.argsort(err)[::-1]
share_sq = np.cumsum(err[order] ** 2) / np.sum(err ** 2)
share_ab = np.cumsum(err[order]) / np.sum(err)
k = int(len(err) * 0.05)
print(f"誤差の大きい 5% の行が占める割合: 2 乗誤差の和 {share_sq[k - 1]:.3f}  絶対誤差の和 {share_ab[k - 1]:.3f}")
```

```text
誤差の大きい 5% の行が占める割合: 2 乗誤差の和 0.517  絶対誤差の和 0.228
```

{{< figure src="rm_error_share.webp" alt="横軸は誤差の大きい順に並べた行の上位何 %、縦軸は合計に占める割合。赤い 2 乗誤差の和の曲線は急に立ち上がり、上位 5% で 52%、上位 20% で 80% を超える。青い絶対誤差の和の曲線は緩やかで、上位 5% で 23%。灰色の点線はどの行も同じ誤差の場合の対角線" caption="誤差の大きい行が、2 乗誤差の和と絶対誤差の和に占める割合" align="center" >}}

上位 5% の 258 行が、2 乗誤差の和では 52% を占めました。絶対誤差の和では 23% です。RMSE は、テストデータの 5% の行でほぼ半分が決まる指標だということです。

このテストデータでは RMSE が 0.4675、MAE が 0.3126 で、比は約 1.5 です。誤差が[正規分布](../../math/probability-distributions/)に従うなら、比は `sqrt(π / 2)`、約 1.25 になります。

比が 1.25 より大きいことは、一部に大きな外れがあると疑う材料になります。ただし、誤差の分布で裾が重い時や、予測の難しさが行によって違う時、一部の地域だけで予測が外れている時にも比は大きくなるので、比だけで外れ値があるとは言えません。

RMSE は `y` と同じ単位なので、幅としても使えます。誤差が平均 0 の正規分布に近いなら、正解のおよそ 95% が「予測 ± 2 × RMSE」の中に入ります。この幅から外れた値に印を付けるのは、[異常検知](../anomaly-detection/)でよく使われる形です。

<br>

このデータには、住宅価格が 5.0 以上の地区が 992 件あり、そのうち 965 件はちょうど 5.00001 に揃っています。50 万ドルを上限に、それより高い値を切ったように見えます。冒頭の散布図で、右端に縦に並んだ点です。

テストデータでは、5.0 以上の地区は 241 件で行の 4.7% ですが、2 乗誤差の和では 18%、絶対誤差の和では 9% を占めていました。上限に揃った地区で、本当の価格は 50 万ドルより高いかもしれず、その行の外れをどこまで重く見るかで、RMSE と MAE のどちらを主に見るかが変わります。

---

### MAPE は低い予測を高く評価する

MAPE（Mean Absolute Percentage Error、平均絶対パーセント誤差）は、ずれを正解で割ってから平均した値です。式は `mean(|y_i − ŷ_i| / |y_i|)` で、単位の違う対象をまたいで「何割外れたか」で比べられます。同じ 0.3 の外れでも、正解が 1 の地区では 30%、正解が 4 の地区では 7.5% と数えられ、安い地区の外れが重く数えられます。

学習したモデルの予測を一律に `c` 倍して、3 つの指標がどう動くかを見ました。

```python
cs = np.round(np.arange(0.80, 1.101, 0.01), 2)
curves = {"RMSE": [], "MAE": [], "MAPE": []}
for c in cs:
    q = pred * c
    curves["RMSE"].append(root_mean_squared_error(y_test, q))
    curves["MAE"].append(mean_absolute_error(y_test, q))
    curves["MAPE"].append(mean_absolute_percentage_error(y_test, q))
```

```text
c=0.95  RMSE 0.4789  MAE 0.3169  MAPE 0.1725
c=1.00  RMSE 0.4675  MAE 0.3126  MAPE 0.1822
RMSE が最小になる c: 1.00
MAE が最小になる c: 0.98
MAPE が最小になる c: 0.94
```

{{< figure src="rm_mape_scale.webp" alt="横軸は予測に掛ける倍率 c で 0.80〜1.10、縦軸は c = 1 の時の値との比。赤い RMSE は c = 1.00 で最小、青い MAE は 0.98 でわずかに 1 を下回り、緑の MAPE は 0.94 で最小になり 1 より 5% ほど低い。c が 1 より大きい側では 3 本とも上がり、MAPE が一番急に上がる" caption="予測を一律に c 倍した時の RMSE・MAE・MAPE（c = 1 との比）" align="center" >}}

予測を 5% 下げると、RMSE と MAE は悪くなるのに、MAPE は 0.1822 から 0.1725 に良くなりました。MAPE が一番小さくなるのは 0.94 倍で、学習したままの予測ではありません。

理由は割り算にあります。正の値を予測する時、低く外した行の MAPE は、予測が 0 まで下がっても 100% で止まります。高く外した行には上限がありません。正解 100 を 50 と予測すると 50% ですが、正解 50 を 100 と予測すると 100% です。そのため MAPE は、全体を低く予測するモデルを高く評価します。前の節で `absolute_error` のモデルが MAPE で勝ったのも、中央値に寄せた予測が平均に寄せた予測より低くなるためと考えられます。

<br>

#### 正解に 0 があると MAPE は使えない

MAPE は正解で割るので、正解が 0 の行があると計算できません。scikit-learn の [`mean_absolute_percentage_error`](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.mean_absolute_percentage_error.html) は、無限大の代わりに、とても大きい値を返します。

```python
print(mean_absolute_percentage_error([0.0, 1.0], [0.1, 1.0]))
print(mean_absolute_percentage_error([1.0, 1.0], [1.1, 1.0]))
```

```text
225179981368524.8
0.050000000000000044
```

2 件のうち 1 件を 0.1 外しただけで、2.25e14 になりました。正解が 0 の時は、0 の代わりに float64 の機械イプシロンで割るためです。機械イプシロンは、1 と、1 の次に表せる数との差で、約 2.2e-16 です。2 行目のとおり、返り値は 5% ではなく 0.05 で、100 を掛けた百分率ではありません。

売上や来店数のように 0 の日がある値では、MAPE の代わりに、絶対誤差の和を正解の和で割った WAPE（Weighted Absolute Percentage Error）を使えます。全体で割るので、0 の行があっても計算できます。ほかに、正解と予測それぞれの絶対値を平均して分母にする SMAPE（symmetric MAPE）もあります。

[時系列予測](../time-series-forecasting/)で使われる MASE（Mean Absolute Scaled Error）は、予測の MAE を素朴な予測の MAE で割った値です。素朴な予測は、1 つ前の時点で観測した値をそのまま次の予測にします。1 より小さければ素朴な予測より良く、正解に 0 があっても計算できます。どの場面でどれを使うかは、Hyndman 氏と Athanasopoulos 氏の教科書 [Forecasting: Principles and Practice](https://otexts.com/fpp3/accuracy.html) にまとまっています。

割合で見たい理由が、価格のように高い側へ裾の長い値を比率で扱いたいことなら、正解と予測を両方 `log1p` で変換してから RMSE を取る RMSLE（Root Mean Squared Log Error）も使えます。[歪度と log1p](../../math/skewness/) で、変換すると分布の形がどう変わるかを扱っています。

---

### scikit-learn で出す時の関数と符号

scikit-learn 1.9.1 で、[回帰の指標](https://scikit-learn.org/stable/modules/model_evaluation.html#regression-metrics)を出す関数と、[`cross_val_score`](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.cross_val_score.html) などに渡す `scoring` の名前は次のとおりです。

| 指標 | 関数 | `scoring` の名前 |
|---|---|---|
| MAE | `mean_absolute_error` | `"neg_mean_absolute_error"` |
| MSE | `mean_squared_error` | `"neg_mean_squared_error"` |
| RMSE | `root_mean_squared_error` | `"neg_root_mean_squared_error"` |
| MAPE | `mean_absolute_percentage_error` | `"neg_mean_absolute_percentage_error"` |
| R² | `r2_score` | `"r2"` |

`scoring` の名前に `neg_` が付く指標は、値の符号を反転して返ります。scikit-learn の[文書](https://scikit-learn.org/stable/modules/model_evaluation.html#scoring-parameter)にあるとおり、スコアは大きいほど良いものに揃えているためで、RMSE が 0.47 なら -0.47 が返ります。[ハイパーパラメータ](../hyperparameter/)を探索した結果をそのまま表に貼ると、負の誤差が並ぶので、符号を戻してから報告します。

RMSE の関数 [`root_mean_squared_error`](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.root_mean_squared_error.html) は 1.4 で入りました。それより前に書かれたコードでは `mean_squared_error(y, pred, squared=False)` で RMSE を出していましたが、[1.4 の変更履歴](https://scikit-learn.org/stable/whats_new/v1.4.html)で `squared` は非推奨になり、1.6 で削除されています。1.6 以降で古いコードを動かすと、`squared` という引数は無いというエラーになります。

---

### 報告に出す指標を選ぶ順

最初に決めるのは、外れた時の損がずれの大きさにどう比例するかです。在庫切れが致命的な需要予測のように、大きく外した 1 件が高くつくなら、主な指標は RMSE です。ずれの分だけ損をするなら MAE にします。住宅価格のように高い側へ裾を引く値では、2 つの順位が入れ替わることがあり、RMSE は外れの大きい 5% の行でほぼ半分が決まりました。どちらを選んでも、もう片方を並べて書いておくと、大きな外れがどれだけあるかが読み手に伝わります。

R² は、同じ評価データで複数のモデルを比べる時に使います。R² が 0.8 なら良い、0.5 なら悪いという決まった線は無く、同じデータで平均を返すだけの予測や今のモデルと比べて、どれだけ良くなったかで読みます。地域・期間・顧客層のように評価データを分けて並べる時は、R² の横に RMSE か MAE と、正解の[標準偏差](../../math/stddev/)を書きます。冒頭の図で見たセントラルバレーのように、R² が低くても外れた金額は一番小さい、ということが表から読めるようになります。

MAPE は、割合で外れを見たい理由がはっきりある時だけ使います。代表は、店舗や商品のように規模の違う系列を 1 つの表に並べて比べたい時です。その時は予測の平均と正解の平均を並べ、予測が全体に低く寄っていないかを見ます。正解に 0 があれば WAPE、時系列なら MASE で比べます。報告に使う指標が決まったら、学習の損失をその指標に合わせるかを考えます。冒頭の 3 枚の散布図のように、点の並びを指標と一緒に見ておくと、数字が何を数えているかを取り違えずに済みます。
