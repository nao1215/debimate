---
title: "正則化 - Lasso が残す列は、なぜ行を選び直すだけで 27 通りに分かれるのか"
date: 2026-05-24
draft: false
series: ["機械学習ノート", "Machine Learning"]
tags: ["machine-learning", "scikit-learn", "model-evaluation"]
weight: 8
topics: ["Machine Learning（評価・概念・アルゴリズム）"]
---

線形のモデルは、データの列ごとに係数を掛けて足し、予測を作ります。学習は、予測の外れ具合を表す[損失関数](../loss-functions/)が小さくなるように係数を決める作業です。

正則化（regularization）は、この損失に、係数の大きさに応じたペナルティを足す仕組みです。係数を大きくして学習データに合わせ込むほどペナルティが増えるので、学習データにだけ合う[過学習](../overfitting/)を抑えられます。係数の 2 乗をペナルティにする方式を L2、絶対値をペナルティにする方式を L1 と呼びます。線形回帰に L2 を足したものが Ridge、L1 を足したものが Lasso で、Lasso は効きの弱い列の係数をちょうど 0 にします。

以下は、[scikit-learn](https://scikit-learn.org/stable/) に同梱の [diabetes](https://scikit-learn.org/stable/datasets/toy_dataset.html#diabetes-dataset) に Lasso を掛けた結果です。diabetes は、糖尿病の患者 442 人について、年齢・性別・BMI・血圧と 6 つの血液検査の値の計 10 列から、1 年後の病気の進み具合を表す数値を当てるデータです。442 行から、同じ行が何度出てもよい形で 442 行を選び直し、その度に Lasso を学習し直すことを 200 回繰り返しました。左の図は、ほぼ同じ動きをする 2 列 s1・s2 について、Lasso が 0 にしなかった回を赤いマスで示し、200 回を残り方で並べ替えたものです。

{{< figure src="regularization_cover.webp" alt="左は s1 と s2 の 2 行、200 回分のマス目で、残り方で並べ替えてある。s1 だけが赤い回が 164 回、s2 だけが赤い回が 20 回、両方が赤い回が 7 回、どちらも空白の回が 9 回。右は 10 列が残った割合の横棒で、sex・bmi・bp・s5 は 100%、s3 は 98%、s1 は 86%、s6 は 82%、age は 68%、s4 は 46%、s2 は 14%" caption="行を選び直した 200 回で、Lasso が 0 にしなかった回（diabetes、左は s1 と s2 を残り方で並べ替えたもの）" align="center" >}}

s1 は総コレステロール、s2 は LDL（低比重リポタンパク）コレステロールです。200 回のうち 164 回は s1 だけが残りましたが、20 回は s1 が 0 になり、代わりに s2 だけが残りました。2 列が両方残ったのは 7 回です。s1 が 0 になった回だけを見れば、「総コレステロールは病気の進み具合に効かない」と言えてしまいます。それはデータの性質ではなく、たまたま選んだ行の結果です。

右の図のとおり、sex・bmi・bp・s5 は 200 回とも残り、age や s4 は半分前後から 7 割の回でだけ残りました。10 列の残り方の組み合わせは 27 通りです。

Lasso で列を絞り、残った列を「効く要因」として説明する場面があります。scikit-learn の LogisticRegression のように、何も指定しなくても正則化が掛かるモデルで学習し、係数の大きさから列の重要さを読む場面もあります。どちらも、その前に、係数がデータの何を写しているかを確認する必要があります。

<br>

本記事では、ML を学び始めた人と、scikit-learn の Ridge・Lasso を手元のデータに使う人に向けて、次の疑問に答えます。

- 正則化は損失に何を足し、alpha で何が変わるのか。
- L1 と L2 は、係数をどう違う形で縮めるのか。
- Lasso が 0 にした列は、効かない列と言えるのか。
- 同じ alpha を別のデータに使い回してよいのか。
- alpha は、どう選べばよいのか。

実験は scikit-learn 1.9.1 で行いました。図を描く処理も含めた完全なコードは [regularization_gen.py](https://github.com/nao1215/debimate/blob/main/projects/ml/scripts/notes/regularization_gen.py) にあります。

---

### 損失に足すペナルティと alpha

[線形回帰](../linear-regression/)の損失は、予測と正解の差の 2 乗を足した値です。正則化は、ここに係数 `w_i` の大きさを足します。

- L2（Ridge）: `損失 = 誤差の二乗の和 + alpha * sum(w_i ^ 2)`
- L1（Lasso）: `損失 = 誤差の二乗の和 + alpha * sum(|w_i|)`

`alpha` はペナルティの重さを決める[ハイパーパラメータ](../hyperparameter/)で、0 なら正則化なし、大きいほど係数は 0 に近づきます。誤差の書き方は、scikit-learn の Ridge と Lasso で少し違います。この違いは後の節で効いてきます。

最初に、alpha で何が変わるかを見ます。真の関数 `sin(x) + 0.3x` にノイズを足した 30 個の点に、x の 1〜15 乗を列にした次数 15 の多項式を当てはめ、Ridge の alpha を 3 通りに変えました。学習に使わない 1000 個の点でも誤差を測ります。

```python
rng = np.random.default_rng(3)
truth = lambda v: np.sin(v) + 0.3 * v  # データを作った真の関数
x = np.sort(rng.uniform(-3, 3, 30))
y = truth(x) + rng.normal(0, 0.3, x.size)
x_new = rng.uniform(-3, 3, 1000)  # 学習に使わない新しい点
y_new = truth(x_new) + rng.normal(0, 0.3, x_new.size)

for alpha in [0, 0.1, 100]:
    reg = LinearRegression() if alpha == 0 else Ridge(alpha=alpha)
    model = make_pipeline(PolynomialFeatures(15, include_bias=False), StandardScaler(), reg)
    model.fit(x[:, None], y)
    mse_train = np.mean((model.predict(x[:, None]) - y) ** 2)
    mse_new = np.mean((model.predict(x_new[:, None]) - y_new) ** 2)
    w = model[-1].coef_
    print(f"alpha={alpha:>5}: 学習の誤差 {mse_train:.3f}、新しい点の誤差 {mse_new:.3f}、"
          f"係数の絶対値の最大 {np.abs(w).max():.1f}")
```

```text
alpha=    0: 学習の誤差 0.028、新しい点の誤差 8.919、係数の絶対値の最大 10459.2
alpha=  0.1: 学習の誤差 0.063、新しい点の誤差 0.135、係数の絶対値の最大 2.2
alpha=  100: 学習の誤差 0.874、新しい点の誤差 0.852、係数の絶対値の最大 0.2
```

{{< figure src="regularization_curves.webp" alt="3 つの散布図に曲線を重ねた図。alpha=0 の赤いモデルの曲線は学習の点をなぞって大きく上下に暴れ、両端で破線の真の関数から大きく外れる。alpha=0.1 は両端を除いて真の関数にほぼ沿う。alpha=100 は曲線が平らに潰れ、点の山と谷を捉えていない" caption="次数 15 の多項式に Ridge を掛け、alpha を変えた 3 通り" align="center" >}}

正則化なしでは係数が 1 万を超え、学習の点をなぞる代わりに、新しい点の誤差は 8.919 まで膨らみました。alpha=0.1 では係数が 2.2 以下に収まり、新しい点の誤差は 0.135 です。alpha=100 はペナルティが重すぎて曲線が潰れ、学習の誤差も新しい点の誤差も 0.85 前後に揃って高くなります。

alpha を強めるほど予測のばらつきは減り、代わりに偏りが増えます。この関係は[バイアス-バリアンス分解](../bias-variance-tradeoff/)で式として扱っています。

---

### L1 と L2 の縮め方

ここからは diabetes を使います。各列を標準化し、平均 0・標準偏差 1 に揃えてから学習します。10 列のうち s1 と s2 は、[相関係数](../../math/correlation/)が 0.90 とほぼ同じ動きをする列です。

```python
d = load_diabetes()
X, y = d.data, d.target
names = d.feature_names
Xs = StandardScaler().fit_transform(X)
i1, i2 = names.index("s1"), names.index("s2")
print("s1 と s2 の相関:", np.corrcoef(Xs[:, i1], Xs[:, i2])[0, 1].round(2))
print("正則化なしの係数:", dict(zip(names, LinearRegression().fit(Xs, y).coef_.round(1))))
```

```text
s1 と s2 の相関: 0.9
正則化なしの係数: {'age': -0.5, 'sex': -11.4, 'bmi': 24.7, 'bp': 15.4, 's1': -37.7, 's2': 22.7, 's3': 4.8, 's4': 8.4, 's5': 35.7, 's6': 3.2}
```

出力は `np.float64(...)` の表記を省いています。正則化なしでは、s1 が -37.7、s2 が +22.7 と、符号の違う大きな係数を持ちました。ほぼ同じ動きの 2 列に逆向きの大きな係数を付け、差し引きで小さな違いを使っている形です。

以下は、alpha を変えた時の 10 列の係数の動きを Lasso と Ridge で並べた図です。横軸の範囲が左右で違うのは、scikit-learn の Lasso と Ridge で alpha の効き方が違うためで、理由は後の節で説明します。左右の alpha の値をそのまま見比べることはできません。

{{< figure src="regularization_paths.webp" alt="2 つの折れ線グラフ。横軸は対数の alpha、縦軸は係数。左の Lasso では、赤い破線の s2 が alpha 0.26 付近でちょうど 0 になって以後 0 のまま、赤い実線の s1 は -36 から 0 へ近づき、alpha 3 付近で 0 になる。灰色の他の列も順に 0 で止まる。右の Ridge では、どの線も 0 に近づくが 0 では止まらず、s2 は alpha 14 付近で正から負へ 0 を横切り、alpha 840 付近でもう一度 0 を横切って正に戻る" caption="alpha を変えた時の diabetes の係数の動き（左が Lasso、右が Ridge）" align="center" >}}

Lasso では、s2 が alpha 0.26 付近でちょうど 0 になり、そのまま 0 に留まります。Ridge では、どの係数も 0 に近づくだけで 0 にはならず、s2 は正から負へ 0 を横切ります。

<br>

この違いは、ペナルティの傾きから来ます。以下は、alpha=1 の時の 2 つのペナルティを係数 w の値ごとに描いた図です。

{{< figure src="regularization_penalty.webp" alt="2 つのグラフ。左の L2 の w^2 は 0 を底にした放物線で、0 の近くでは平らになる。右の L1 の |w| は 0 を底にした V 字で、0 のすぐ横でも同じ傾きで上がる" caption="0 の近くでのペナルティの形（左が L2、右が L1）" align="center" >}}

L2 の `w^2` は、係数が 0 に近づくほど傾きも 0 に近づくので、0 の手前で縮める力が弱まります。L1 の `|w|` は、0 のすぐ横でも傾きが alpha のままです。係数を 0 から少し動かした時に誤差が減る量が、このペナルティの増える量より小さい列は、0 に置いた方が損失が小さくなるので、0 に留まります。傾きの意味は[偏微分と勾配](../../math/partial-derivative-gradient/)で説明しています。

Lasso の性質は、Tibshirani 氏の 1996 年の論文「[Regression Shrinkage and Selection via the Lasso](https://doi.org/10.1111/j.2517-6161.1996.tb02080.x)」で示されたものです。0 になった列を外せば、学習しながら列を選んだことになり、[特徴量選択](../feature-selection/)の Embedded 法として使われます。

---

### 行の選び直しで変わる Lasso の列

前の節の図では、alpha を上げると s2 が 0.26 付近で先に 0 になり、s1 は alpha 3 付近まで残りました。s1 と s2 はほぼ同じ動きをするので、どちらを残すかは 2 列のわずかな違いで決まると考えられます。行を少し入れ替えれば、その違いが逆転することもあります。

それを確認するのが、冒頭の図を作った実験です。ブートストラップ（bootstrap）は、手元の行から同じ行が何度出てもよい形で同じ数の行を選び直し、学習をやり直して結果のばらつきを調べる手順です。ここでは 442 行から 442 行を選び直すことを 200 回繰り返し、Lasso・Elastic Net・Ridge を学習し直しました。Elastic Net は L1 と L2 のペナルティを混ぜた手法で、ここでは半分ずつにしています。

<br>

alpha は、どれも全ての行で[交差検証](../cross-validation/)をして選び、200 回の間は固定しました。標準化とモデルは `make_pipeline` で 1 本の pipeline につなぎます。pipeline にすると、学習の度に、その回に学習へ使う行だけで平均と標準偏差を求め直します。そのため、alpha を選ぶ交差検証で、検証用の行の情報が前処理に漏れません。この漏れは[データリーク](../data-leakage/)のノートで扱っています。200 回の選び直しでも、各回に選んだ行だけで標準化からやり直します。

```python
cv = KFold(n_splits=5, shuffle=True, random_state=0)
# 標準化を pipeline の中に入れ、交差検証の分割ごとに学習用の行だけで平均と標準偏差を求める
models = {"Lasso": make_pipeline(StandardScaler(), Lasso()),
          "Elastic Net": make_pipeline(StandardScaler(), ElasticNet(l1_ratio=0.5)),
          "Ridge": make_pipeline(StandardScaler(), Ridge())}
grids = {"Lasso": {"lasso__alpha": np.logspace(-2, 1, 31)},
         "Elastic Net": {"elasticnet__alpha": np.logspace(-3, 0, 31)},
         "Ridge": {"ridge__alpha": np.logspace(-3, 4, 71)}}
for label, pipe in models.items():
    search = GridSearchCV(pipe, grids[label], cv=cv).fit(X, y)
    pipe.set_params(**search.best_params_)
    print(f"{label}: 交差検証で選んだ alpha {list(search.best_params_.values())[0]:.3f}")
```

```text
Lasso: 交差検証で選んだ alpha 1.000
Elastic Net: 交差検証で選んだ alpha 0.008
Ridge: 交差検証で選んだ alpha 1.585
```

上のコードで alpha の候補を試しているのは [`GridSearchCV`](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.GridSearchCV.html) で、候補ごとに交差検証をして最も良い値を返します。`make_pipeline` は段にクラス名を小文字にした名前を付けるので、Lasso の段の alpha は `lasso__alpha` のように、段の名前と引数の名前を `__` でつないで指定します。

次のコードで、選んだ alpha のまま行を 200 回選び直します。

```python
rng = np.random.RandomState(0)
B = 200
coefs = {label: np.zeros((B, 10)) for label in models}
for b in range(B):
    idx = rng.choice(len(y), size=len(y), replace=True)  # 442 行から 442 行を選び直す
    for label, pipe in models.items():
        coefs[label][b] = pipe.fit(X[idx], y[idx])[-1].coef_  # 選び直した行で標準化から学習し直す

kept = coefs["Lasso"] != 0
print("Lasso が残した割合:", dict(zip(names, kept.mean(axis=0).round(2))))
print("Lasso が残した列の組み合わせ:", len({tuple(r) for r in kept}), "通り")
groups = [("s1 だけ", kept[:, i1] & ~kept[:, i2]), ("s2 だけ", ~kept[:, i1] & kept[:, i2]),
          ("両方", kept[:, i1] & kept[:, i2]), ("どちらも無し", ~kept[:, i1] & ~kept[:, i2])]
print("s1・s2 の残り方:", {g: int(m.sum()) for g, m in groups})
for label, C in coefs.items():
    print(f"{label}: s2 を残した割合 {(C[:, i2] != 0).mean():.2f}、s2 の係数が正の割合 {(C[:, i2] > 0).mean():.2f}")
```

```text
Lasso が残した割合: {'age': 0.68, 'sex': 1.0, 'bmi': 1.0, 'bp': 1.0, 's1': 0.86, 's2': 0.14, 's3': 0.98, 's4': 0.46, 's5': 1.0, 's6': 0.82}
Lasso が残した列の組み合わせ: 27 通り
s1・s2 の残り方: {'s1 だけ': 164, 's2 だけ': 20, '両方': 7, 'どちらも無し': 9}
Lasso: s2 を残した割合 0.14、s2 の係数が正の割合 0.01
Elastic Net: s2 を残した割合 1.00、s2 の係数が正の割合 0.91
Ridge: s2 を残した割合 1.00、s2 の係数が正の割合 0.91
```

出力の 164・20・7・9 回が、冒頭の左の図の 4 つの区切りです。以下は、200 回の s1 と s2 の係数を 1 回 1 点で描いた図です。

{{< figure src="regularization_s1_s2.webp" alt="3 つの散布図。横軸は s1 の係数、縦軸は s2 の係数。Lasso の点は横軸か縦軸の上に乗り、どちらか片方が 0。Elastic Net と Ridge の点はほぼ同じ形で、左上の s1 -65・s2 +38 から右下の s1 +17・s2 -23 まで、右下がりの帯に長く伸びる" caption="行を選び直した 200 回の、s1 と s2 の係数（左から Lasso、Elastic Net、Ridge）" align="center" >}}

<br>

3 つの手法の違いは、点の並び方に出ています。s1 と s2 はほぼ同じ情報を持つので、片方を増やしてもう片方を減らしても、予測はあまり変わりません。データはこの 2 列の分け方を決められず、決め方はペナルティの形に任されると考えられます。

Lasso は、2 列のうち片方を 0 にする方を選ぶので、点が軸の上に乗ります。縦軸の上の点、つまり s2 だけが残った 20 回のうち 17 回は、s2 の係数が負でした。正則化なしの +22.7 は s1 の -37.7 と差し引きするために付いた値で、片方だけを残すと、その列が 2 列を合わせた負の効き目を引き継ぐと考えられます。

Ridge は 2 列とも残す代わりに、右下がりの帯に沿って大きく揺れ、s2 の符号は 9% の回で負になりました。

Elastic Net は、Zou 氏と Hastie 氏が論文「[Regularization and Variable Selection via the Elastic Net](https://doi.org/10.1111/j.1467-9868.2005.00503.x)」で、相関の強い列を一緒に残す手法として示したものです。

ただし、交差検証で選んだ alpha は 0.008 とペナルティがほとんど掛からない値でした。s2 は 200 回とも残ったものの、点は Ridge とほぼ同じ帯に広がりました。予測の良さで選んだ alpha では、2 列の分け方は安定しないということです。

列を選んだ結果を説明に使うなら、この実験のように行を選び直し、残った割合で列を見る方が確かです。Meinshausen 氏と Bühlmann 氏の「[Stability Selection](https://doi.org/10.1111/j.1467-9868.2010.00740.x)」は、この割合を使って列を選ぶ手法です。

---

### 同じ alpha でも変わる効き目

ここまでは標準化した列を使いました。実は、`load_diabetes` が返す列は、最初から平均 0 で、各列の二乗の和が 1 になるように割られています。[文書](https://scikit-learn.org/stable/datasets/toy_dataset.html#diabetes-dataset)にもそう書かれており、どの列も標準偏差 0.0476 に揃っています。列は揃っているので、標準化しなくてもよさそうに見えます。

```python
for label, model in [("同梱のまま", make_pipeline(Lasso(alpha=1.0))),
                     ("標準化してから", make_pipeline(StandardScaler(), Lasso(alpha=1.0)))]:
    r2 = cross_val_score(model, X, y, cv=cv).mean()
    coef = model.fit(X, y)[-1].coef_
    print(f"{label}: Lasso(alpha=1.0) が残した列 {[names[j] for j in np.flatnonzero(coef)]}、R^2 {r2:.3f}")
r2_ols = cross_val_score(LinearRegression(), X, y, cv=cv).mean()
print(f"正則化なし: R^2 {r2_ols:.3f}")
```

```text
同梱のまま: Lasso(alpha=1.0) が残した列 ['bmi', 'bp', 's5']、R^2 0.345
標準化してから: Lasso(alpha=1.0) が残した列 ['sex', 'bmi', 'bp', 's1', 's3', 's5', 's6']、R^2 0.490
正則化なし: R^2 0.489
```

同じ既定の `alpha=1.0` でも、同梱のままでは 3 列しか残らず、交差検証の [R^2](../regression-metrics/) は 0.345 まで落ちました。標準化した後は 7 列が残り、正則化なしの 0.489 と同じ水準です。

<br>

原因は、列の大きさとペナルティの関係です。標準化した列の標準偏差は 1、同梱の列は 0.0476 なので、同梱の列は標準化した列の約 1/21 の大きさです。21 は 1/0.0476 で、442 の平方根でもあります。

列の値が 1/21 なら、同じ予測をするには係数を 21 倍にする必要があります。L1 のペナルティは係数の絶対値なので 21 倍に、L2 は係数の 2 乗なので 21 の 2 乗の 442 倍に増えます。同じ alpha でも、同梱の列では Lasso のペナルティが 21 倍、Ridge のペナルティが 442 倍重く効くということです。

列の大きさで結果が変わる点は、[PCA](../pca/) の第 1 主成分が列の単位で入れ替わるのと同じ形です。標準化の要るモデルと要らないモデルは、[標準化のノート](../standardization/)で表にしています。

もう 1 つ、行の数でも効き目が変わります。scikit-learn の [Ridge](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.Ridge.html) は誤差の二乗の和にペナルティを足し、[Lasso](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.Lasso.html) は誤差の二乗の平均を半分にした値にペナルティを足します。Ridge では、行が増えるほど誤差の和が大きくなり、ペナルティの比重が下がります。同じ 442 行を 10 回並べて、確認しました。

```python
X10, y10 = np.tile(Xs, (10, 1)), np.tile(y, 10)  # 同じ 442 行を 10 回並べる
for cls, a in [(Ridge, 100.0), (Lasso, 1.0)]:
    w1 = cls(alpha=a).fit(Xs, y).coef_[[i1, i2]]
    w10 = cls(alpha=a).fit(X10, y10).coef_[[i1, i2]]
    print(f"{cls.__name__}(alpha={a}): s1, s2 の係数 442 行 {w1.round(2)} → 4420 行 {w10.round(2)}")
```

```text
Ridge(alpha=100.0): s1, s2 の係数 442 行 [-2.07 -3.71] → 4420 行 [-11.3    1.81]
Lasso(alpha=1.0): s1, s2 の係数 442 行 [-4.84 -0.  ] → 4420 行 [-4.84 -0.  ]
```

データの中身は同じなのに、Ridge の係数は変わり、Lasso の係数は小数第 2 位まで同じでした。以下は、3 つのデータで alpha ごとの交差検証の R^2 を並べた図です。

{{< figure src="regularization_alpha_scale.webp" alt="2 つの折れ線グラフ。横軸は対数の alpha、縦軸は交差検証の R^2。左の Lasso では、青い同梱のままの線が alpha 0.1 付近から下がり始め、alpha 1 で 0.35、2 付近で 0 に落ちる。赤い標準化してからの線と緑の点線の 10 回並べた線は重なり、alpha 2 付近から下がって 40〜50 で 0 になる。右の Ridge では、青い線が alpha 0.1 付近から下がり、alpha 1 で 0.42。赤い線は alpha 100 付近から下がり、緑の点線はさらに右へずれて alpha 1000 でも 0.48 を保つ" caption="alpha ごとの交差検証の R^2（左が Lasso、右が Ridge）" align="center" >}}

R^2 が最大になる alpha は、Lasso では同梱のままが 0.042、標準化した後が 1.0 で、約 24 倍の開きです。Ridge では 0.0032 と 1.33 で、約 420 倍です。試した alpha の候補が飛び飛びなので、先の計算の 21 倍と 442 倍に近い値になりました。Ridge は 10 回並べると、最大の位置が 1.33 の 10 倍の 13.3 に移りました。Lasso の 10 回並べた線は、標準化した後の線と重なっています。

ある alpha が良かったという結果は、その列の大きさと行の数でだけ成り立ちます。記事やサンプル数の違う実験で良かった値は、そのまま使えません。

---

### alpha の選び方

alpha は、使うデータで交差検証をして選びます。選び直しの節の実験と同じく、標準化と Lasso を pipeline でつなぎ、GridSearchCV で alpha を動かします。下のコードの後半では、選んだ値の前後の alpha でも R^2 と 0 にした列を確認しています。

```python
pipe = make_pipeline(StandardScaler(), Lasso())
search = GridSearchCV(pipe, {"lasso__alpha": np.logspace(-3, 2, 26)}, cv=cv).fit(X, y)
best = search.best_params_["lasso__alpha"]
coef = search.best_estimator_[-1].coef_
print(f"選んだ alpha {best:.3f}、交差検証の R^2 {search.best_score_:.3f}、"
      f"0 にした列 {[names[j] for j in np.flatnonzero(coef == 0)]}")
for a in [0.1, 0.3, 1.0, 3.0]:
    pipe = make_pipeline(StandardScaler(), Lasso(alpha=a))
    r2 = cross_val_score(pipe, X, y, cv=cv).mean()
    coef = pipe.fit(X, y)[-1].coef_
    print(f"alpha={a}: 交差検証の R^2 {r2:.3f}、0 にした列 {[names[j] for j in np.flatnonzero(coef == 0)]}")
```

```text
選んだ alpha 1.000、交差検証の R^2 0.490、0 にした列 ['age', 's2', 's4']
alpha=0.1: 交差検証の R^2 0.489、0 にした列 ['s3']
alpha=0.3: 交差検証の R^2 0.489、0 にした列 ['age', 's2']
alpha=1.0: 交差検証の R^2 0.490、0 にした列 ['age', 's2', 's4']
alpha=3.0: 交差検証の R^2 0.483、0 にした列 ['age', 's2', 's4']
```

alpha だけを探すなら、[`LassoCV`](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LassoCV.html) や `RidgeCV` の方が速く求まります。

出力のとおり、alpha を 0.1 から 1.0 まで動かしても R^2 は 0.489〜0.490 でほぼ変わりません。前の節の図でも、Lasso の赤い線は alpha 0.0001 から 1 付近まで平らでした。予測の良さで選んだ alpha は、平らな範囲の 1 点にすぎません。

それなのに、0 にした列は alpha 0.1 では s3 だけ、0.3 では age と s2、1.0 では age・s2・s4 と変わりました。どの alpha を選んでも予測は同じなので、0 にした列の違いは予測の良さでは決まりません。この 3 列は、冒頭の図でも残った割合が 68%・14%・46% と低く、行の選び直しにも alpha にも左右される列です。

<br>

#### 名前の違う正則化

alpha と書かれていない引数も、正則化の強さを決めていることがあります。以下は、scikit-learn 1.9.1 で既定の値を確認したものです。

| クラス | 引数と既定の値 | 強める向き |
|---|---|---|
| Ridge・Lasso・ElasticNet | `alpha=1.0` | 大きく |
| LogisticRegression | `C=1.0`（L2） | 小さく |
| SVC・LinearSVC | `C=1.0` | 小さく |
| MLPClassifier | `alpha=0.0001`（L2） | 大きく |
| HistGradientBoostingClassifier | `l2_regularization=0.0` | 大きく |

[ロジスティック回帰](../logistic-regression/)と [SVM](../svm/) の `C` は、alpha の逆数のように働き、小さいほどペナルティが重くなります。LogisticRegression は何も指定しなくても L2 で正則化されているので、係数を読む時は `C` も報告します。

[決定木](../decision-tree/)は、学習中に小さくする損失にペナルティの項を持ちません。その代わり、`max_depth` を小さくする、`min_samples_leaf` を大きくするといった木の成長の制限が、同じ役割を果たします。学習の後で葉の数にペナルティを掛けて枝を刈る `ccp_alpha` もあり、既定は 0.0 です。[勾配ブースティング](../gradient-boosting/)の [XGBoost](https://xgboost.readthedocs.io/en/stable/parameter.html) と [LightGBM](https://lightgbm.readthedocs.io/en/stable/Parameters.html) は、葉の値に L1 と L2 のペナルティを掛ける引数を持っています。

---

### 正則化を掛ける前に確かめること

正則化付きのモデルを手元のデータに使う前に、まず各列の標準偏差を並べます。単位の違う列が混ざっていれば、ペナルティは値の幅が小さい列に重く掛かります。diabetes のように揃って見える列でも、その大きさが標準化した列と違えば、既定の alpha の効き目は何十倍も変わります。標準化は、モデルと一緒に pipeline に入れます。

alpha は、他のデータや記事の値を持ち込まず、使うデータで交差検証をして選びます。Ridge は行の数でも効き目が変わるので、一部の行で選んだ alpha を全ての行での学習に使う時は、選び直します。過学習の原因がデータリークや評価の方法にあるなら、正則化を強めても直りません。

<br>

Lasso が残した列を説明に使う前には、行を選び直して何回残るかを数えます。冒頭の図の s2 のように 14% の回でしか残らない列があれば、相関の強い相手の列が無いかを確認します。見つかったら、2 列をまとめて「どちらかが効いている」と説明します。Elastic Net で両方を残しても、選び直しの節の実験のように 2 列の係数の分け方は揺れます。

係数の大きさから列の重要さを読むなら、Ridge や LogisticRegression でも、行を選び直した時に係数の符号が保たれるかを見ます。選び直しの節の Ridge のように、相関の強い 2 列の係数が逆向きに大きく揺れていれば、列ごとの係数には意味が無く、2 列を合わせた効き目だけが安定していると考えられます。冒頭の図で 200 回とも残った sex・bmi・bp・s5 のような列が、説明に使いやすい列です。
