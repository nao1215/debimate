---
title: "kNN - 緯度と経度を度から m に書き直すだけで、R² が 0.15 から 0.80 に変わる理由"
date: 2026-05-24
draft: false
series: ["機械学習ノート", "Machine Learning"]
tags: ["machine-learning", "scikit-learn", "supervised"]
weight: 20
topics: ["Machine Learning（評価・概念・アルゴリズム）"]
---

kNN（k-Nearest Neighbors、k 近傍法）は、予測したい点から距離の近い k 個の学習データを探し、分類ならそのラベルの多数決、回帰なら値の平均を答えにする手法です。学習の時にパラメータを求めず、学習データをそのまま覚えておき、予測のたびに近い点を探します。

以下は、[scikit-learn](https://scikit-learn.org/stable/) に同梱の [California Housing](https://scikit-learn.org/stable/modules/generated/sklearn.datasets.fetch_california_housing.html) で、区画ごとの住宅価格の中央値を kNN で当てた結果です。California Housing は、1990 年のアメリカの国勢調査から、カリフォルニア州の 20640 区画について所得・築年数・部屋数・人口・緯度・経度など 8 列を並べたデータです。

R² は予測の精度を表す指標で、1 なら完全に当たり、0 なら平均値を返すだけの予測と同じです。図は、Berkeley 付近の 1 区画（星）に対して、kNN が近いと判断した 5 区画（赤）を地図に置いたものです。

{{< figure src="knn_cover.webp" alt="カリフォルニア州の形に並んだ 3 枚の点の地図。左のそのまま（度）は、星の区画から近傍 5 区画への線が南のロサンゼルス付近まで伸び、R² 0.15、近傍までの距離の中央値 102km。中央の標準化は、近傍 5 区画が星から数十 km の範囲に集まり、R² 0.69、中央値 21km。右の緯度・経度を m に は、近傍 5 区画が星にほぼ重なり、R² 0.80、中央値 0.9km。各図の右上に、星の周り 30km 四方の拡大がある" caption="同じ kNN に 3 通りの単位で列を渡した時の、1 区画の近傍 5 区画と R²" align="center" >}}

8 列をそのまま渡すと、近傍の 5 区画には 532km 離れた区画まで入り、R² は 0.15 でした。緯度と経度の 2 列だけを度から m に書き直すと、近傍は全て 3km 以内に入り、R² は 0.80 まで上がって、全ての列の幅を揃える標準化をした 0.69 も超えます。kNN の予測は、どの列の単位で距離を測るかで決まります。

手元の CSV に kNN を使う時も、金額・件数・座標のように列の単位はばらばらです。スコアが低かった、標準化したら上がった、という場面で、どの列が近さを決めているかを確認しないと、0.80 のような数字をそのまま信じてしまいます。実はこの 0.80 は、学習データの無い地域の区画を当てさせると 0.24 まで下がります。

<br>

本記事では、ML を学び始めた人と、scikit-learn の kNN を手元のデータに使う人に向けて、次の疑問に答えます。

- kNN は何を覚え、予測をどう決めるのか。
- 列の単位を変えると、なぜ近傍が入れ替わるのか。
- 標準化すれば、それで十分なのか。
- k は、どう選べばよいのか。
- データや列が多い時、近傍の検索はどう速くするのか。

実験は scikit-learn 1.9.1 で行いました。図を描く処理も含めた完全なコードは [knn_gen.py](https://github.com/nao1215/debimate/blob/main/projects/ml/scripts/notes/knn_gen.py) にあります。

---

### 近傍の多数決と平均

最初に、2 列だけの小さなデータで、kNN が予測をどう決めるかを見ます。クラス A の 30 点を (0, 0) の周りに、クラス B の 30 点を (3, 3) の周りに置き、その間の (1.5, 1.5) を予測します。距離には、各列の差の 2 乗を足して平方根を取るユークリッド距離 `d(x, x_i) = sqrt(sum((x - x_i)^2))` を使います。scikit-learn の [`KNeighborsClassifier`](https://scikit-learn.org/stable/modules/generated/sklearn.neighbors.KNeighborsClassifier.html) の既定の距離もこれです。

```python
rng = np.random.default_rng(0)
X_a = rng.standard_normal((30, 2)) + [0, 0]  # クラス A は (0, 0) の周り
X_b = rng.standard_normal((30, 2)) + [3, 3]  # クラス B は (3, 3) の周り
X_toy = np.vstack([X_a, X_b])
y_toy = np.array(["A"] * 30 + ["B"] * 30)
query = np.array([[1.5, 1.5]])

for k in (1, 5):
    clf = KNeighborsClassifier(n_neighbors=k).fit(X_toy, y_toy)
    dist, idx = clf.kneighbors(query)
    print(f"k={k}: 近い順のラベル {[str(c) for c in y_toy[idx[0]]]}、距離 {dist[0].round(3)}、予測 {clf.predict(query)[0]}")
```

```text
k=1: 近い順のラベル ['B']、距離 [0.187]、予測 B
k=5: 近い順のラベル ['B', 'A', 'A', 'A', 'A']、距離 [0.187 0.354 0.462 0.587 0.716]、予測 A
```

{{< figure src="knn_concept.webp" alt="2 枚の散布図。青いクラス A が左下、赤いクラス B が右上に集まり、その間に緑の星の予測したい点がある。左の k=1 は、星のすぐ右の赤い 1 点だけを丸で囲み、予測は B。右の k=5 は、その赤い 1 点と周りの青い 4 点を丸で囲み、票は A 4・B 1 で予測は A" caption="同じ点でも、k=1 なら B、k=5 なら A と答えが変わる" align="center" >}}

最も近い 1 点は距離 0.187 のクラス B なので、k=1 なら答えは B です。5 点まで広げると票は A が 4、B が 1 になり、答えは A に変わります。回帰の [`KNeighborsRegressor`](https://scikit-learn.org/stable/modules/generated/sklearn.neighbors.KNeighborsRegressor.html) は、票の代わりに近傍の値の平均を返します。

`fit` は点を覚えるだけで、距離の計算は全て予測の時に行います。そのため kNN は、怠惰学習（lazy learning）とも呼ばれます。距離を測るので、列は全て数値でなければなりません。文字列のカテゴリを持つ列は、[カテゴリ変数のエンコーディング](../categorical-encoding/)で数値にしてから渡します。

kNN の考え方は 1950 年代からあり、1967 年の Cover と Hart の論文「[Nearest neighbor pattern classification](https://ieeexplore.ieee.org/document/1053964)」が、k=1 の誤り率は、データが十分に多ければ理論上の最小の誤り率の 2 倍を超えないと示したことでよく知られています。[異常検知](../anomaly-detection/)では、近傍までの距離そのものを「周りから離れている度合い」として使うこともあります。

---

### 列の単位で近傍が入れ替わる理由

ユークリッド距離は、列ごとの差の 2 乗を足すので、値の幅が大きい列ほど距離の大部分を占めます。California Housing の 8 列の[標準偏差](../../math/stddev/)を並べると、Population（区画の人口）が 1132.43 で飛び抜けて大きく、次の HouseAge（築年数の中央値）の 12.59 の 90 倍です。緯度は 2.14、経度は 2.00 しかありません。

以下のコードは、4 通りの列の渡し方で R² を測ります。R² は 5 分割の[交差検証](../cross-validation/)の平均です。`latlon_scaled` は、緯度と経度の 2 列を度から距離の単位に書き直す関数です。緯度 1 度はおよそ 111km です。経度 1 度の長さは北へ行くほど短くなるので、データの中心の緯度およそ 35.6 度の cos を経度に掛けます。州の中の距離なら、この近似で足ります。

標準化では、`make_pipeline` で標準化と kNN を 1 つのモデルにつなぎます。こうすると、交差検証の分割ごとに、学習側のデータだけで平均と標準偏差を求めます。

さらに、各区画の近傍 5 区画を [`NearestNeighbors`](https://scikit-learn.org/stable/modules/generated/sklearn.neighbors.NearestNeighbors.html) で探します。予測はせずに近傍だけを返すクラスです。見つけた近傍について、地表の距離と、所得・人口の差を測ります。地表の距離は、補助関数 `km_between` が 2 つの区画の緯度と経度から求めます。この関数は、冒頭で案内した全体のコードにあります。

```python
housing = fetch_california_housing()
Xh, yh = housing.data, housing.target
lat, lon = Xh[:, 6], Xh[:, 7]


def latlon_scaled(X, meters_per_degree):
    # 緯度と経度の 2 列を、度から距離の単位に書き直す。経度 1 度の長さは緯度で変わるので、
    # データの中心の緯度（およそ 35.6 度）の cos を経度に掛ける。州の中では、この近似で足りる
    X = X.copy()
    lat0 = np.radians(X[:, 6].mean())
    X[:, 6] = X[:, 6] * meters_per_degree
    X[:, 7] = X[:, 7] * meters_per_degree * np.cos(lat0)
    return X


cv = KFold(n_splits=5, shuffle=True, random_state=0)
knn = KNeighborsRegressor()  # 既定は n_neighbors=5、距離はユークリッド距離
# (名前, kNN に渡す値, モデル, kNN が距離を測る値)。標準化だけは、モデルの中で値が変わる
cases = [("そのまま（度）", Xh, knn, Xh),
         ("緯度・経度を km に", latlon_scaled(Xh, 111.0), knn, latlon_scaled(Xh, 111.0)),  # 緯度 1 度はおよそ 111km
         ("標準化", Xh, make_pipeline(StandardScaler(), knn), StandardScaler().fit_transform(Xh)),
         ("緯度・経度を m に", latlon_scaled(Xh, 111_000.0), knn, latlon_scaled(Xh, 111_000.0))]
for label, data, model, seen in cases:
    r2 = cross_val_score(model, data, yh, cv=cv).mean()
    # 全ての区画について、自分を除いた近傍 5 区画を探し、地表の距離と、所得・人口の差を測る
    _, idx = NearestNeighbors(n_neighbors=5).fit(seen).kneighbors()
    i, j = np.repeat(np.arange(len(yh)), 5), idx.ravel()
    km = np.median(km_between(i, j))
    inc = np.median(np.abs(Xh[i, 0] - Xh[j, 0]))  # MedInc（所得の中央値）の差
    pop = np.median(np.abs(Xh[i, 4] - Xh[j, 4]))  # Population（人口）の差
    print(f"{label}: R² {r2:.3f}、近傍 5 区画との差の中央値は 距離 {km:.1f}km・所得 {inc:.2f}・人口 {pop:.0f}")
Xk_nopop = np.delete(latlon_scaled(Xh, 111.0), 4, axis=1)  # km にした上で Population の列を外す
print(f"緯度・経度を km にし、人口を外す: R² {cross_val_score(knn, Xk_nopop, yh, cv=cv).mean():.3f}")
```

```text
そのまま（度）: R² 0.151、近傍 5 区画との差の中央値は 距離 102.4km・所得 1.10・人口 2
緯度・経度を km に: R² 0.461、近傍 5 区画との差の中央値は 距離 10.0km・所得 1.13・人口 8
標準化: R² 0.688、近傍 5 区画との差の中央値は 距離 20.6km・所得 0.20・人口 120
緯度・経度を m に: R² 0.801、近傍 5 区画との差の中央値は 距離 0.9km・所得 0.78・人口 369
緯度・経度を km にし、人口を外す: R² 0.816
```

そのまま渡した時、kNN は人口がほぼ同じ区画を探しています。冒頭の図の Berkeley 付近の区画の人口は 322 人で、近傍 5 区画の人口は 319・324・320・323・317 人でした。その中に 532km 先の区画も入り、近傍までの距離の中央値は 102km になります。

緯度と経度を km にすると、近傍までの距離の中央値は 10.0km で、標準化の 20.6km より近くなります。それでも R² は 0.461 で、標準化の 0.688 に届きません。km にした位置の差は数 km〜数百 km で、人口の差と同じ桁なので、kNN は 10km ほどの範囲から人口の近い区画を選びます。近傍との人口の差の中央値は 8 人で、所得の差は 1.13 と、そのまま渡した時の 1.10 と変わりません。

以下は、出力の R²、近傍までの距離、近傍との所得の差を並べた図です。

{{< figure src="knn_units.webp" alt="3 つの横棒グラフ。左の 5 分割の R² は、そのまま（度）0.151、緯度・経度を km に 0.461、標準化 0.688、緯度・経度を m に 0.801。中央の近傍 5 区画までの距離の中央値は、対数の軸で 102.4km、10.0km、20.6km、0.9km。右の近傍 5 区画との所得の差の中央値は、1.10、1.13、0.20、0.78" caption="列の渡し方ごとの R² と、近傍 5 区画までの距離・所得の差" align="center" >}}

所得の標準偏差は 1.9 しかなく、km にしても m にしても距離にはほとんど効きません。標準化では所得も他の列と同じ重さになり、近傍との所得の差は 0.20 まで縮みました。km のまま人口の列だけを外すと R² は 0.816 になるので、km にした時の R² を下げていたのは人口の列だったと考えられます。

m にすると位置の差は数千〜数十万の値になり、人口を含む他の 6 列はほとんど距離に効かなくなります。このとき kNN は、地図の上ですぐ隣の区画を探す手法になり、近傍までの距離の中央値は 0.9km です。

<br>

[標準化](../standardization/)は、各列から平均を引いて標準偏差で割り、どの列も分散 1 に揃える操作です。8 列を同じ重さで扱うので、人口だけが距離を決めることは無くなり、R² は 0.688 まで上がりました。

標準化の効果を人工データで確認する実験は、標準化のノートにあります。ここで分かるのは、もう 1 つのことです。標準化は 8 列を同じ重さにするだけで、どの列で近いと見なすべきかまでは決めません。m に直した緯度と経度も、人口を外した km も、標準化より高い R² を出しました。

人口を外した km の 0.816 は m の 0.801 も上回りますが、どちらも行を混ぜた分け方の数字です。距離の測り方を変えるだけで R² が 0.15 から 0.8 前後まで動く点はどちらも同じで、次の節で見るとおり、この高さは分け方を変えると崩れます。

---

### 標準化の次に決める列の重み

m に直した 0.80 が標準化の 0.69 を超えたのは、緯度と経度だけで近さを測ると、すぐ隣の区画の価格をそのまま使えるからです。ここまでの交差検証は、行を混ぜてから 5 つに分ける `KFold(shuffle=True)` です。検証に回った区画のすぐ隣の区画は、学習側に残っています。

このデータで行を混ぜると何が起きるかは、交差検証のノートの「[shuffle で上がったスコア](../cross-validation/#shuffle-で上がったスコア)」で確認しています。60% の行は緯度と経度が完全に同じ別の行を持ち、勾配ブースティングの R² は、行を混ぜると 0.836、地域ごとに外すと 0.730 でした。本記事でも、緯度と経度を 0.5 度、南北でおよそ 55km ごとのマス目に切り、同じマスの区画をまとめて検証に回す [`GroupKFold`](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.GroupKFold.html) を使います。学習データの無い地域の区画を当てさせる測り方です。

以下のコードは、標準化した後に緯度と経度の 2 列だけを `w` 倍して、距離の中でどれだけ重く見るかを変えます。`w` を掛ける処理は [`FunctionTransformer`](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.FunctionTransformer.html) で pipeline に入れ、2 つの分け方で R² を測ります。

```python
# 緯度と経度を 0.5 度ごとのマス目に切り、同じマスの区画を 1 つのグループにする
groups = np.floor(lat / 0.5).astype(int) * 1000 + np.floor(lon / 0.5).astype(int)
gcv = GroupKFold(n_splits=5)
weights = [0.25, 0.5, 1, 2, 4, 8, 16]
for w in weights:
    col_w = np.array([1, 1, 1, 1, 1, 1, w, w])  # 緯度と経度の 2 列だけを w 倍して、距離の中で重く見る
    model = make_pipeline(StandardScaler(), FunctionTransformer(lambda Z, c=col_w: Z * c), knn)
    r2_shuffle = cross_val_score(model, Xh, yh, cv=cv).mean()
    r2_group = cross_val_score(model, Xh, yh, cv=gcv, groups=groups).mean()
    print(f"重み {w:5}: KFold(shuffle) の R² {r2_shuffle:.3f}、GroupKFold の R² {r2_group:.3f}")
Xm = latlon_scaled(Xh, 111_000.0)
print(f"緯度・経度を m に: GroupKFold の R² {cross_val_score(knn, Xm, yh, cv=gcv, groups=groups).mean():.3f}")
```

```text
重み  0.25: KFold(shuffle) の R² 0.622、GroupKFold の R² 0.530
重み   0.5: KFold(shuffle) の R² 0.651、GroupKFold の R² 0.557
重み     1: KFold(shuffle) の R² 0.688、GroupKFold の R² 0.583
重み     2: KFold(shuffle) の R² 0.722、GroupKFold の R² 0.584
重み     4: KFold(shuffle) の R² 0.759、GroupKFold の R² 0.568
重み     8: KFold(shuffle) の R² 0.792、GroupKFold の R² 0.571
重み    16: KFold(shuffle) の R² 0.819、GroupKFold の R² 0.554
緯度・経度を m に: GroupKFold の R² 0.237
```

{{< figure src="knn_weight.webp" alt="横軸は標準化した後に緯度と経度の 2 列に掛ける重み 0.25〜16、縦軸は 5 分割の R²。赤い KFold(shuffle=True) の線は 0.622 から重みと共に上がり続け、重み 1 で 0.688、16 で 0.819。青い GroupKFold の線は重み 1〜2 の 0.583 付近が最も高く、16 では 0.554 に下がる" caption="緯度と経度の重みと R²。分け方によって、重みを上げた時の向きが逆になる" align="center" >}}

行を混ぜた分け方では、緯度と経度を重く見るほど R² が上がり、重み 16 で 0.819 になりました。マス目ごとに外す `GroupKFold` では、重み 1〜2 の 0.58 付近が最も高く、その先は下がります。緯度と経度を m に直した冒頭の 0.801 は、`GroupKFold` では 0.237 まで落ちました。

すぐ隣の区画が学習データに無ければ、位置だけで近さを測っても、似た区画は見つかりません。その時に頼れるのは、所得や部屋数のように、地域が違っても価格と結び付く列です。重み 16 の 0.819 は、隣の区画を覚えているだけの数字と言えます。

<br>

どの分け方の数字を信じるかは、交差検証のノートと同じく使い方で決まります。kNN では、その選択がそのまま距離の測り方の選択になります。学習データがある地域の中で欠けた区画を埋めるなら、行を混ぜた分け方で選んだ重みが使い方に近く、学習データの無い地域へ広げて使うなら、`GroupKFold` で重みを選び、この例では標準化のままの重み 1 がほぼ最良でした。

列の重みを細かく動かす代わりに、価格と関係の薄い列を外す方法もあります。ラベルとの関係で列を選ぶ方法は、[特徴量選択](../feature-selection/)で扱っています。

---

### k の選び方

ここまでは、scikit-learn の既定の k=5 で測ってきました。以下のコードは、標準化した 8 列のまま、k を 1 から 200 まで変えて 5 分割の R² を測ります。分け方は、行を混ぜた `KFold(shuffle=True)` です。

```python
ks = [1, 2, 3, 5, 8, 12, 20, 30, 50, 80, 120, 200]
valid_r2 = []
for k in ks:
    model = make_pipeline(StandardScaler(), KNeighborsRegressor(n_neighbors=k))
    valid_r2.append(cross_val_score(model, Xh, yh, cv=cv).mean())
best = ks[int(np.argmax(valid_r2))]
print("5 分割の R²:", {k: round(float(v), 3) for k, v in zip(ks, valid_r2)})
print(f"最大は k={best}")
```

```text
5 分割の R²: {1: 0.524, 2: 0.631, 3: 0.664, 5: 0.688, 8: 0.696, 12: 0.697, 20: 0.693, 30: 0.686, 50: 0.676, 80: 0.663, 120: 0.652, 200: 0.633}
最大は k=12
```

{{< figure src="knn_k.webp" alt="横軸は近傍の数 k（1〜200 の対数の軸）、縦軸は 5 分割の R²。k=1 の 0.524 から急に上がり、k=12 の 0.697 で最大になり、その先は緩やかに下がって k=200 で 0.633" caption="近傍の数 k と 5 分割の R²（California Housing、標準化した 8 列）" align="center" >}}

k=1 は、最も近い 1 区画の価格をそのまま返すので、その区画の価格に混じった雑音まで予測に入り、R² は 0.524 でした。k を増やすと雑音が平均で薄まり、k=12 の 0.697 で最大になります。k=200 まで広げると、遠く離れた似ていない区画まで平均に入り、予測は全体の平均に近づいて 0.633 まで下がります。

この形は、モデルの複雑さを変えた時の[過学習](../overfitting/)と同じで、k が小さいほど学習データに敏感になります。その釣り合いは、[バイアスとバリアンス](../bias-variance-tradeoff/)のノートで扱っています。

<br>

k を学習データで測ったスコアで選ぶことはできません。学習データの点を予測すると、最も近い点はその点自身なので、k=1 ならほぼ必ず当たってしまうからです。他の[ハイパーパラメータ](../hyperparameter/)と同じく、交差検証のスコアで選びます。

既定の k=5 と最良の k=12 の差は 0.009 です。差が小さいので、既定のままでも結果は大きく変わりません。前の節で緯度と経度の重みを変えた時は、行を混ぜた分け方で 0.622〜0.819 と 0.2 近く動いたので、k を細かく選ぶより、何で近さを測るかを決める方が先です。

分類で 2 クラスなら、k を奇数にすると票が同数になりません。クラスの数が偏ったデータでは、多い方のクラスが近傍の票を占めやすくなります。その扱いは[不均衡データ](../class-imbalance/)のノートで扱っています。

---

### 近傍の検索を速くする索引

kNN は予測のたびに近傍を探すので、学習データが増えるほど予測が重くなります。素朴な方法は、全ての学習データとの距離を計算する総当たり（brute force）です。`||x - x_i||^2 = ||x||^2 - 2 x · x_i + ||x_i||^2` と展開すると、真ん中の項は全ての点との内積なので、[行列とベクトルの積](../../math/vector-matrix-ops/)の 1 回でまとめて計算できます。

総当たりを避ける方法として、scikit-learn は 2 つの木を持っています。[`KDTree`](https://scikit-learn.org/stable/modules/generated/sklearn.neighbors.KDTree.html) は、空間を値の広がりが最も大きい列で半分に割ることを繰り返し、[`BallTree`](https://scikit-learn.org/stable/modules/generated/sklearn.neighbors.BallTree.html) は点を入れ子の球で囲みます。どちらも、予測したい点から遠い箱や球の中の点は、距離の計算を省きます。

<br>

scikit-learn の[近傍法の文書](https://scikit-learn.org/stable/modules/neighbors.html#choice-of-nearest-neighbors-algorithm)によると、既定の `algorithm="auto"` は、列の数が 15 を超える時や、k が学習データの半分以上の時に総当たりを選び、それ以外は kd-tree を選びます。以下のコードは、10 万件の乱数のデータから 1,000 件の近傍 5 点を探し、列の数を変えながら 3 つの方法で時間を測ります。行列の積は複数の CPU のスレッドで速くなるので、全て 1 スレッドに絞って比べます。

```python
rng = np.random.RandomState(0)
N, Q = 100_000, 1_000
dims = [2, 4, 8, 16, 32, 64]
timings = {"kd_tree": [], "ball_tree": [], "brute": []}
with threadpool_limits(1):  # 行列積も含め、全て 1 スレッドで比べる
    for d in dims:
        X = rng.randn(N, d)
        q = rng.randn(Q, d)
        for alg in timings:
            nn = NearestNeighbors(n_neighbors=5, algorithm=alg).fit(X)
            t = time.perf_counter()
            nn.kneighbors(q)
            timings[alg].append(time.perf_counter() - t)
        print(f"{d:2d} 次元: " + "、".join(f"{a} {timings[a][-1]:.3f} 秒" for a in timings))
```

```text
 2 次元: kd_tree 0.002 秒、ball_tree 0.014 秒、brute 0.173 秒
 4 次元: kd_tree 0.005 秒、ball_tree 0.071 秒、brute 0.204 秒
 8 次元: kd_tree 0.071 秒、ball_tree 0.424 秒、brute 0.422 秒
16 次元: kd_tree 1.050 秒、ball_tree 0.850 秒、brute 0.192 秒
32 次元: kd_tree 3.972 秒、ball_tree 3.123 秒、brute 0.235 秒
64 次元: kd_tree 19.737 秒、ball_tree 22.432 秒、brute 0.473 秒
```

2 次元では kd-tree が 0.002 秒で、総当たりの 80 倍ほど速く終わりました。列が増えるほど木の時間は急に伸び、64 次元では kd-tree が 19.7 秒、総当たりは 0.47 秒で、木の方が数十倍遅くなりました。時間は CPU や他の処理で変わりますが、測り直しても桁の違いは同じでした。

木が遅くなるのは、列が増えると、どの点も同じくらいの距離に並び、遠い箱や球の計算を省けなくなるからです。この距離の集中は、[次元の呪い](../curse-of-dimensionality/)のノートで実験しています。ここで使ったのは全ての列が独立な乱数で、木にとって最も不利なデータです。

<br>

#### 近似の検索で速くする

文書の意味を数百〜数千の数値の並びに変えたものは、埋め込み（embedding）と呼ばれます。[RAG](/notes/generative-ai/rag/) で質問に近い文書の断片を探す処理は、この埋め込みの近傍の検索です。

列がこれだけ多く、件数も多いと、総当たりも重くなります。そこで、厳密な近傍を諦める代わりに速く返す、近似最近傍探索（ANN、Approximate Nearest Neighbor）を使います。代表的な方法に、点をグラフでつないで近い方へたどる [HNSW](https://arxiv.org/abs/1603.09320) があります。

以下は、[UMAP](../tsne-umap/) の実装も近傍の計算に使う [PyNNDescent](https://github.com/lmcinnes/pynndescent) 0.7.0 で、64 列のデータから近傍 5 点を探した結果です。PyNNDescent は、近い点同士をつないだグラフを作り、予測したい点から近い方へたどって探します。

`epsilon` は、たどる範囲の広さで、大きいほど正確で遅くなります。図では ε と書いています。再現率は、総当たりで求めた正しい近傍 5 点のうち、近似が当てた割合です。データは 2 通りで、全ての列が独立な乱数のものと、8 列の乱数に 8×64 の行列を掛けて 64 列に写したものを使いました。後者は、見かけは 64 列でも、点は 8 次元の平らな面の上にしかありません。

```python
def ann_recall(X, q, label):
    # 総当たりの答えを正解にして、PyNNDescent の近似が近傍 5 点のうち何点を当てたかを測る
    with threadpool_limits(1):
        nn = NearestNeighbors(n_neighbors=5, algorithm="brute").fit(X)
        t = time.perf_counter()
        _, truth = nn.kneighbors(q)
        brute_sec = time.perf_counter() - t
    index = pynndescent.NNDescent(X, n_neighbors=30, random_state=0, n_jobs=1)
    index.prepare()
    index.query(q[:10], k=5)  # 初回の呼び出しで JIT コンパイルが走るので、測る前に 1 回呼ぶ
    rows = []
    for eps in (0.0, 0.1, 0.2, 0.4):
        t = time.perf_counter()
        found, _ = index.query(q, k=5, epsilon=eps)
        sec = time.perf_counter() - t
        recall = np.mean([len(set(a) & set(b)) / 5 for a, b in zip(found, truth)])
        rows.append((eps, sec, recall))
        print(f"{label} epsilon={eps}: {sec:.3f} 秒、再現率 {recall:.3f}（総当たり {brute_sec:.3f} 秒）")
    return brute_sec, rows


X64 = rng.randn(N + Q, 64).astype(np.float32)  # 64 列が全て独立な乱数
X8in64 = (rng.randn(N + Q, 8) @ rng.randn(8, 64)).astype(np.float32)  # 中身は 8 次元、見かけは 64 列
ann_recall(X64[:N], X64[N:], "独立な 64 列")
ann_recall(X8in64[:N], X8in64[N:], "中身は 8 次元")
```

```text
独立な 64 列 epsilon=0.0: 0.023 秒、再現率 0.167（総当たり 0.492 秒）
独立な 64 列 epsilon=0.4: 0.248 秒、再現率 0.787（総当たり 0.492 秒）
中身は 8 次元 epsilon=0.0: 0.010 秒、再現率 0.799（総当たり 0.563 秒）
中身は 8 次元 epsilon=0.4: 0.021 秒、再現率 0.987（総当たり 0.563 秒）
```

出力は `epsilon` が 0.0 と 0.4 の行だけを抜き出しています。以下の図の右は、0.1 と 0.2 も含めた全ての結果で、左は前のコードの木と総当たりの時間です。

{{< figure src="knn_search.webp" alt="2 つのグラフ。左は横軸が列の数 2〜64、縦軸が 1,000 件の近傍を探す時間（対数の軸）。kd_tree と ball_tree は 2 次元の 0.002 秒と 0.014 秒から列と共に伸び、64 次元で 20 秒前後になる。brute は 0.2〜0.5 秒でほぼ平ら。16 列以上の範囲は灰色で、15 列を超えると auto は brute を選ぶ。右は横軸が時間、縦軸が再現率で、ε は epsilon。8 次元のデータを 64 列に写したものは、ε=0.0 で再現率 0.80、ε=0.4 で 0.99 と、全て 0.03 秒以内。64 列が全て独立な乱数は、ε=0.0 で 0.17、ε=0.4 で 0.79 まで上がる。2 本の縦の破線は、それぞれのデータの総当たりの時間 0.49 秒と 0.56 秒" caption="木の索引と総当たりの時間（左）と、近似の検索の時間と再現率（右、ε は epsilon）" align="center" >}}

同じ 64 列でも、中身が 8 次元のデータでは、`epsilon=0.0` で正しい近傍の 80% を当て、0.4 で 98.7% まで当てました。それでも 0.021 秒で、総当たりの 0.563 秒より 25 倍ほど速く終わります。独立な 64 列では、`epsilon=0.0` で当てたのは 16.7% だけで、近傍 5 点のうち 4 点は別の点でした。

近似の検索の誤りは、データの中身で大きく変わります。文書の埋め込みは列の数ほどには散らばっていないので、近似がよく効くと考えられます。ただし、手元のデータでどれだけ当たるかは、一部の点で総当たりの答えと比べないと分かりません。

---

### kNN を使う前に確かめること

kNN を手元のデータに使う前に、まず列ごとの標準偏差を並べます。1 列だけ桁が違えば、冒頭の図の左のように、その列が近さを決めています。California Housing では、住宅価格を当てるはずの kNN が、人口の近い区画を探していました。

次に、標準化した後で、どの列で近いと見なしたいかは、kNN を何に使うかで決めます。学習データの無い地域・新しいユーザー・新しい期間に使うなら、交差検証を `GroupKFold` などで分けてから重みや列を選びます。行を混ぜた分け方の 0.80 が、地域ごとに外すと 0.24 になったように、近さを位置だけで測るモデルは、隣の点を覚えているだけのことがあります。

<br>

k は交差検証で選びますが、この例では既定の k=5 と最良の差は 0.009 でした。列の単位や重みで動く幅の方が 1 桁大きいので、先に距離の測り方を決めます。

予測が遅い時は、列の数を見ます。15 列以下なら scikit-learn の既定のままで木が使われ、それを超えるなら総当たりの方が速いことが多いです。近似の検索を使うなら、一部の点で総当たりの答えと比べて、再現率を測ってから採用します。

迷ったら、冒頭の図のように、1 つの点の近傍を元の列のまま並べてみると、kNN が何を近いと判断しているかが見えます。
