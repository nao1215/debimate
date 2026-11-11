---
title: "PCA - 寄与率 99.8% の第 1 主成分は、なぜ列の単位を変えると入れ替わるのか"
date: 2026-05-24
draft: false
series: ["機械学習ノート", "Machine Learning"]
tags: ["machine-learning", "scikit-learn", "unsupervised"]
weight: 28
topics: ["Machine Learning（評価・概念・アルゴリズム）"]
---

PCA（Principal Component Analysis、主成分分析）は、多くの列を持つデータから、値のばらつきが大きい方向を順に探し、少ない数の軸にまとめる手法です。見つけた方向を主成分と呼び、ばらつきの大きい順に PC1、PC2 と番号を振ります。

以下は、[scikit-learn](https://scikit-learn.org/stable/) に同梱の [wine](https://scikit-learn.org/stable/modules/generated/sklearn.datasets.load_wine.html) に PCA を掛けた結果です。wine は、イタリアの同じ地域で 3 品種のブドウから作ったワイン 178 本について、アルコール度数や proline など 13 項目の化学分析の値を並べたデータで、[UCI Machine Learning Repository](https://archive.ics.uci.edu/dataset/109/wine) で公開されています。

PC1 は、13 列の値にそれぞれ重みを掛けて足した 1 本の軸です。重みは、13 列の重みの二乗を足すと 1 になるように決まります。そのため重みをそのまま足しても 1 にはならず、1 列の重みが 1.00 なら他の列は 0 で、PC1 はその列そのものです。下の図のマス目の数字は、この重みの大きさです。

右端の寄与率は、データ全体のばらつきのうち PC1 の 1 本で表せる割合です。図の列名は、長いものを短くしています。

{{< figure src="pca_cover.webp" alt="3 行 13 列のマス目。1 行目のそのまま PCA を掛けた場合は proline の列だけが 1.00 で濃い赤、他は 0.02 以下で、寄与率 99.8%。2 行目の proline だけ 1000 で割った場合は magnesium の列だけが 1.00 で、寄与率 90.9%。3 行目の標準化してから掛けた場合は flavanoids 0.42、total_phenols 0.39 など多くの列に 0.1〜0.4 の重みが散らばり、寄与率 36.2%" caption="wine の PC1 が各列に掛ける重みの大きさ。1 列の単位を変えるだけで、PC1 が別の列に入れ替わる（列名は一部を短縮。alcalinity は alcalinity_of_ash、nonflav_phenols は nonflavanoid_phenols、od280/od315 は od280/od315_of_diluted_wines）" align="center" >}}

そのまま掛けると、PC1 は proline の 1 列だけでできていて、データ全体のばらつきの 99.8% を 1 本の軸で表せたことになります。ところが proline の列だけを 1000 で割ると、PC1 は magnesium の 1 列に入れ替わります。どちらの PC1 も、ワインの性質ではなく、値の桁が一番大きい列を選んだだけです。

手元の CSV に PCA を掛ける時も、金額は円、割合は 0〜1、件数は個数のように、列ごとに単位も桁も違うのが普通です。寄与率の高さを見て「2 軸で十分」と決める場面があります。PC1 と PC2 を縦横の軸にして各行を点で描き、正解の種類ごとに色を分けた散布図で、色が混ざって見えたので「この列では種類を見分けられない」と決める場面もあります。どちらも、その前に、軸が何でできているかを確かめる必要があります。

<br>

本記事では、ML を学び始めた人と、scikit-learn の PCA を手元のデータに使う人に向けて、次の疑問に答えます。

- PCA は何を求め、寄与率は何を表すのか。
- 列の単位を変えると、なぜ PC1 が入れ替わるのか。
- 標準化すると、分類の精度はどれだけ変わるのか。
- 主成分は何個残せばよいのか。
- 寄与率の高い軸だけを残すと、答えを捨てることはあるのか。

実験は scikit-learn 1.9.1 で行いました。図を描く処理も含めた完全なコードは [pca_gen.py](https://github.com/nao1215/debimate/blob/main/projects/ml/scripts/notes/pca_gen.py) にあります。

---

### 主成分と寄与率

最初に、2 列だけのデータで PCA が何を求めるかを見ます。x2 が x1 のほぼ 0.3 倍になる、右上がりの細長い点の集まりです。以下は、元の点と PCA で見つけた 2 つの向き、その向きを新しい座標の軸にして点を回転した後を並べた図です。矢印の長さは、各主成分の[標準偏差](../../math/stddev/)の 2 倍にしています。

{{< figure src="pca_rotation.webp" alt="左は右上がりの細長い点の集まりに、長い PC1 の矢印と短い PC2 の矢印を重ねた図。右は同じ点を PC1・PC2 の座標へ回転した図で、点は横軸の PC1 に沿って広がり、縦軸の PC2 の方向にはほとんど広がらない" caption="主成分の向きと、その座標へ回転した後の点" align="center" >}}

PC1 は点が最も長く伸びる向きで、PC2 はそれに直交する向きです。回転した後の右の図では、点は横軸の PC1 に沿って広がり、PC2 の方向にはほとんど広がりません。

<br>

PCA の計算は 3 段です。1 段目は中心化で、各列から平均を引き、点の集まりの中心を原点に移します。2 段目で共分散行列を作ります。共分散は 2 つの列が一緒に増減する度合いで、共分散行列は全ての列の組の共分散を並べた表です。対角には、各列の[分散](../../math/variance/)が入ります。

3 段目で、共分散行列を[固有値分解](../../math/eigen-decomposition/)します。共分散行列を `C`、長さ 1 の向きを `v` とすると、点をその向きに落とした値の分散は `v^T C v` で計算できます。この値を最大にする `v` が、固有値の最も大きい固有ベクトルで、その時の分散が固有値そのものです。2 番目以降の主成分も、それまでの向きと直交する中で同じように選びます。

以下のコードは、この 3 段を [NumPy](https://numpy.org/) で書き、さらに 2 つを確かめます。1 つは、点を主成分の座標へ回転した `X_pca` の 2 列の[相関](../../math/correlation/)です。もう 1 つは、PC2 を捨てて PC1 だけで元の 2 列に戻した `X_back` が、元の点からどれだけずれるかです。平均二乗誤差として、各点のずれの二乗の平均を出します。

```python
rng = np.random.RandomState(0)
x1 = rng.randn(200)
x2 = 0.3 * x1 + 0.1 * rng.randn(200)  # x2 は x1 の 0.3 倍に小さなノイズを足しただけ
X = np.column_stack((x1, x2))

X_centered = X - X.mean(axis=0)
eigvals, eigvecs = np.linalg.eigh(np.cov(X_centered, rowvar=False))
idx = np.argsort(eigvals)[::-1]  # 固有値の大きい順に並べる
eigvals, eigvecs = eigvals[idx], eigvecs[:, idx]
eigvecs = eigvecs * np.sign(eigvecs[0])  # 向き（符号）は任意なので x1 の成分を正に揃える

X_pca = X_centered @ eigvecs  # 主成分の座標へ回転する
X_back = X_pca[:, :1] @ eigvecs[:, :1].T  # PC1 だけ残して元の空間へ戻す
print("固有値（各主成分の分散）:", eigvals.round(4))
print("寄与率:", (eigvals / eigvals.sum()).round(4))
print("PC1 の向き:", eigvecs[:, 0].round(3))
print("PC2 を捨てた時の平均二乗誤差:", np.mean(np.sum((X_centered - X_back) ** 2, axis=1)).round(4))
# + 0.0 は、丸めた結果の -0.0 を 0.0 と表示するため
print("回転した後の PC1 と PC2 の相関:", np.corrcoef(X_pca[:, 0], X_pca[:, 1])[0, 1].round(4) + 0.0)
```

```text
固有値（各主成分の分散）: [1.1481 0.0081]
寄与率: [0.993 0.007]
PC1 の向き: [0.955 0.296]
PC2 を捨てた時の平均二乗誤差: 0.0081
回転した後の PC1 と PC2 の相関: 0.0
```

回転は、中心化した点に固有ベクトルを並べた行列を掛ける `X_pca = X_centered @ eigvecs` の 1 行で、詳しくは[行列ベクトル積](../../math/vector-matrix-ops/)で説明しています。出力の最後の行のとおり、回転した後の 2 列の相関は 0 です。

寄与率は、その主成分の分散が全体の分散に占める割合です。PC1 は 0.993 なので、PC2 を捨てて 1 列にしても、ばらつきの 99.3% が残ります。PCA は、ばらつきの量をデータが持つ情報の量とみなす手法です。PC1 だけで元に戻した時の平均二乗誤差 0.0081 は、PC2 の固有値とほぼ同じ値で、捨てた軸の分散が、そのまま戻せない量になります。`np.cov` の分散は点の数から 1 を引いた数で割り、平均二乗誤差は点の数で割るので、小数点以下 5 桁目からは僅かに違います。

scikit-learn の [`PCA`](https://scikit-learn.org/stable/modules/generated/sklearn.decomposition.PCA.html) は、同じ結果を特異値分解（SVD、Singular Value Decomposition）などで求め、寄与率を `explained_variance_ratio_` に入れて返します。

---

### 列の単位で PC1 が入れ替わる理由

PCA が探すのは、分散の大きい向きです。分散は値の 2 乗の平均なので、列を 1000 で割ると分散は 100 万分の 1 になります。以下は、wine の 13 列の標準偏差を対数の軸で並べた図です。

{{< figure src="pca_wine_std.webp" alt="横棒グラフ。proline の標準偏差 314.02 が飛び抜けて大きく、次が magnesium の 14.24、残りの 11 列は 0.12〜3.33。赤い破線は、proline を 1000 で割った時の 0.31 の位置" caption="wine の列ごとの標準偏差（対数の軸）" align="center" >}}

proline の標準偏差は 314.02 で、2 番目の magnesium の 14.24 の 22 倍です。分散にすると約 490 倍の差があり、PC1 の向きはほぼ proline の軸と重なります。proline を 1000 で割ると標準偏差は 0.31 まで下がり、今度は magnesium が飛び抜けて大きい列になります。冒頭の図の 1 段目と 2 段目は、この順位の入れ替わりを写しただけです。

scikit-learn の `PCA` の文書には「入力のデータは列ごとに中心化するが、スケールは揃えない」とあります。標準化したい時は、自分で前に [`StandardScaler`](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.StandardScaler.html) を置きます。以下は、冒頭の図の 3 通りを比べたコードです。主成分の向きは、符号を反転しても同じ軸を表すので、重みは絶対値で比べます。最後の 2 行では、そのまま掛けた時の PC2 がどの列でできているかも出します。

```python
wine = load_wine()
Xw, yw = wine.data, wine.target
names = wine.feature_names


def pc1(data):
    p = PCA().fit(data)
    # 向きは符号を反転しても同じ軸なので、重みは絶対値で比べる
    return p.explained_variance_ratio_[0], np.abs(p.components_[0])


Xw_div = Xw.copy()
Xw_div[:, names.index("proline")] /= 1000  # proline の列だけ 1000 で割る
cases = [("そのまま", Xw), ("proline だけ 1000 で割る", Xw_div),
         ("標準化してから", StandardScaler().fit_transform(Xw))]
for label, data in cases:
    ratio, w = pc1(data)
    top = np.argsort(w)[::-1][:2]
    print(f"{label}: PC1 の寄与率 {ratio:.4f}、重みの大きい列", [(names[i], round(float(w[i]), 3)) for i in top])
pc2_raw = np.abs(PCA().fit(Xw).components_[1])
print("そのまま: PC2 の重みの大きい列", names[pc2_raw.argmax()], round(float(pc2_raw.max()), 3))
```

```text
そのまま: PC1 の寄与率 0.9981、重みの大きい列 [('proline', 1.0), ('magnesium', 0.018)]
proline だけ 1000 で割る: PC1 の寄与率 0.9091、重みの大きい列 [('magnesium', 0.999), ('color_intensity', 0.033)]
標準化してから: PC1 の寄与率 0.3620、重みの大きい列 [('flavanoids', 0.423), ('total_phenols', 0.395)]
そのまま: PC2 の重みの大きい列 magnesium 0.999
```

標準化は、各列から平均を引いて標準偏差で割り、どの列も分散 1 に揃える操作です。標準化すると、PC1 は flavanoids や total_phenols など多くの列に重みを分け、寄与率は 36.2% まで下がりました。

寄与率が下がったのは悪くなったからではありません。どの列の 1 標準偏差も同じ重さで扱った結果で、99.8% の方が 1 列の桁を測っていただけです。scikit-learn の例「[Importance of Feature Scaling](https://scikit-learn.org/stable/auto_examples/preprocessing/plot_scaling_importance.html)」も、同じ wine で proline が PC1 を占めることを示しています。

<br>

ただし、標準化がいつも正しいわけではありません。画像の画素のように全ての列が同じ単位で、分散の大小そのものに意味がある時は、標準化しないこともあります。どちらを選ぶかの考え方は、[標準化のノート](../standardization/)で、モデルごとに標準化が要るかを並べた表の後に書いています。

---

### 標準化の有無で変わる分類の精度

PC1 が 1 列だけでできていると、後に続くモデルの精度にも響きます。PCA で減らした列から[ロジスティック回帰](../logistic-regression/)で wine の 3 品種を当て、その精度を 5 分割の[交差検証](../cross-validation/)で測りました。

標準化と PCA は、`make_pipeline` で分類器と 1 本につなぎます。こうすると、交差検証の分割ごとに学習用のデータだけで平均や主成分を求めるので、検証用のデータの情報が前処理に漏れません。この漏れは[データリーク](../data-leakage/)のノートで扱っています。

```python
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=0)
ks = list(range(1, 14))
acc_raw, acc_std = [], []
for k in ks:
    raw = make_pipeline(PCA(n_components=k), LogisticRegression(max_iter=5000))
    scaled = make_pipeline(StandardScaler(), PCA(n_components=k), LogisticRegression(max_iter=5000))
    acc_raw.append(cross_val_score(raw, Xw, yw, cv=cv).mean())
    acc_std.append(cross_val_score(scaled, Xw, yw, cv=cv).mean())
for k in [1, 2, 3, 5, 10, 13]:
    print(f"主成分 {k:2d} 個: 標準化なし {acc_raw[k - 1]:.3f}、標準化あり {acc_std[k - 1]:.3f}")
```

```text
主成分  1 個: 標準化なし 0.697、標準化あり 0.837
主成分  2 個: 標準化なし 0.674、標準化あり 0.961
主成分  3 個: 標準化なし 0.804、標準化あり 0.966
主成分  5 個: 標準化なし 0.933、標準化あり 0.978
主成分 10 個: 標準化なし 0.955、標準化あり 0.983
主成分 13 個: 標準化なし 0.955、標準化あり 0.983
```

主成分を 2 個残した時の精度は、標準化なしで 67.4%、標準化ありで 96.1% でした。以下は、その 2 個の主成分で点を描き、品種ごとに色を分けた図です。

{{< figure src="pca_wine_scatter.webp" alt="2 つの散布図。左の標準化なしは横軸の PC1 が -400〜900 に広がり、品種 1 と品種 2 の点が左側で混ざっている。右の標準化ありは、品種 0 が右上、品種 1 が下、品種 2 が左上の 3 つの塊に分かれている" caption="wine を 2 個の主成分で描いた散布図（左は標準化なし、右は標準化あり）" align="center" >}}

標準化なしの左の図で品種 1 と品種 2 が混ざるのは、横軸の PC1 が proline の 1 列で、縦軸の PC2 も前の節の出力の最後の行のとおり magnesium の 1 列でできているからです。13 列のうち 2 列だけを見ているのと同じです。

主成分を 1 個から 2 個に増やしても、精度は 69.7% から 67.4% に下がりました。[pca_gen.py](https://github.com/nao1215/debimate/blob/main/projects/ml/scripts/notes/pca_gen.py) で、標準化した 1 列だけから同じロジスティック回帰で品種を当てると、proline だけで 68.0%、magnesium だけで 50.7% でした。PC1 だけの 69.7% と少し違う理由には、PC1 が magnesium などにも僅かな重みを持ち、proline そのものではないことと、PC1 の値は標準化していないので正則化の効き方が変わることが考えられます。どちらが効いているかは確かめていません。magnesium は品種を見分ける手掛かりが少なく、足しても精度は上がらないと考えられます。下がった 2.3 ポイントの理由までは確かめていません。

同じデータでも、標準化した右の図では 3 品種がほぼ分かれます。2 次元の散布図で塊が重なっても、それだけで「この列では分けられない」とは言えないということです。

---

### 残す主成分の数

主成分の数を決める目安として、累積寄与率がよく使われます。PC1 から順に寄与率を足した値で、「80% を超えるまで残す」「95% を超えるまで残す」のように決めます。以下は、残す数ごとに、標準化した wine の累積寄与率と前の節の分類の精度を重ねた図です。

{{< figure src="pca_components.webp" alt="横軸は残す主成分の数 1〜13。灰色の累積寄与率は 0.36 から緩やかに上がり、10 個で 0.95 の破線を超える。青い標準化ありの精度は 1 個で 0.84、2 個で 0.96 に跳ね上がり、その後はほぼ横ばい。赤い標準化なしの精度は 2 個で 0.67 と低く、6 個でやっと 0.95 付近に届く" caption="残す主成分の数ごとの累積寄与率と分類の精度（wine）" align="center" >}}

累積寄与率が 95% を超えるのは 10 個で、scikit-learn 1.9.1 で `PCA(n_components=0.95)` と書いても 10 個が選ばれました。一方で、分類の精度は 2 個の時点で 96.1% に届いていて、その時の累積寄与率は 55.4% しかありません。13 個全部を使っても 98.3% です。

この差は、2 つの目安が別のものを測っているから生まれます。累積寄与率は、最初の節で見たとおり、元のデータをどれだけ復元できるかの目安です。予測に使うなら、残す数は他の[ハイパーパラメータ](../hyperparameter/)と同じく、交差検証の精度で選びます。

前の節の pipeline なら、[`GridSearchCV`](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.GridSearchCV.html) で `pca__n_components` を動かせば選べます。`make_pipeline` は各段にクラス名を小文字にした名前を付けるので、PCA の段は `pca` です。段の名前と引数の名前を `__` でつなぐと、pipeline の中の引数を指定できます。

---

### 分散の小さい軸に答えがある時

wine では、標準化した PC1 だけで 83.7% の精度が出ました。分散の大きい向きが、たまたま品種の違いとも重なっていたからです。PCA は分類のラベルを見ずに向きを決めるので、いつもこうなるとは限りません。

以下は、それを確かめるために作った 2 クラスの人工データです。列 a は標準偏差 3 でクラスと関係なく散らばり、列 b は標準偏差 0.3 と小さいものの、クラスによって値が +0.6 と -0.6 にずれます。図は縦と横の縮尺を揃えているので、a の広がりが b の 10 倍に見えます。

{{< figure src="pca_low_variance.webp" alt="横長の散布図。縦横の縮尺を揃えた図で、横軸の a は -8〜8 に広がり、縦軸の b は -1.5〜1.5 の細い帯になる。赤いクラス 1 は上側、青いクラス 0 は下側に分かれている。PC1 の矢印は横軸と平行で、寄与率 95.1%、PC1 だけで精度 48.5% と書かれている" caption="クラスの違いが分散の小さい列 b にある人工データと、PC1 の向き（縦横の縮尺は同じ）" align="center" >}}

PCA と比べる相手として、LDA（Linear Discriminant Analysis、線形判別分析）も使います。LDA はラベルを使い、クラスの平均同士が、クラスの中のばらつきに比べて最も離れて見える向きを選ぶ手法で、scikit-learn では [`LinearDiscriminantAnalysis`](https://scikit-learn.org/stable/modules/generated/sklearn.discriminant_analysis.LinearDiscriminantAnalysis.html) です。以下のコードは、PC1 だけ、2 列のまま、LDA で 1 軸に減らした場合の精度を測ります。

```python
rng = np.random.RandomState(0)
n = 400
y = rng.randint(0, 2, n)
a = rng.randn(n) * 3  # 分散が大きいが、クラスとは関係ない列
b = rng.randn(n) * 0.3 + np.where(y == 1, 0.6, -0.6)  # 分散は小さいが、クラスで値がずれる列
Xs = np.column_stack((a, b))
ps = PCA().fit(Xs)
acc_pca1 = cross_val_score(make_pipeline(PCA(n_components=1), LogisticRegression()), Xs, y, cv=cv).mean()
acc_all = cross_val_score(LogisticRegression(), Xs, y, cv=cv).mean()
acc_lda = cross_val_score(make_pipeline(LinearDiscriminantAnalysis(n_components=1), LogisticRegression()),
                          Xs, y, cv=cv).mean()
print("寄与率:", ps.explained_variance_ratio_.round(3), "PC1 の向き:", np.abs(ps.components_[0]).round(2))
print(f"PC1 だけ {acc_pca1:.3f}、2 列のまま {acc_all:.3f}、LDA で 1 軸 {acc_lda:.3f}")
```

```text
寄与率: [0.951 0.049] PC1 の向き: [1.   0.01]
PC1 だけ 0.485、2 列のまま 0.980、LDA で 1 軸 0.982
```

PC1 は寄与率 95.1% で、向きはほぼ列 a そのものです。PC1 だけを残すと、精度は 48.5% とコインを投げるのと変わらなくなりました。捨てた 4.9% の PC2 の方に、クラスの違いが全部入っていたからです。

ラベルを使って向きを決める LDA なら、同じ 1 本の軸でも 98.2% の精度が出ます。ラベルとの関係で列を選ぶ方法は、[特徴量選択](../feature-selection/)で扱っています。

---

### PCA を掛ける前に確かめること

PCA を手元のデータに掛ける前に、まず列ごとの標準偏差を並べます。1 列だけ桁が違えば、冒頭の図の 1 段目のように PC1 はその列になり、高い寄与率はデータの構造ではなく単位を写しています。単位の違う列が混ざっていれば標準化し、画素のように同じ単位なら、そのままも候補にします。

次に、PCA の後に何をするかで、残す数の決め方を変えます。データを小さく保存して後で戻すなら累積寄与率で、[k-means](../k-means/) や分類器の前処理なら、標準化と PCA を pipeline に入れて、交差検証の精度で数を選びます。列が多すぎてモデルが不安定になる問題は、[次元の呪い](../curse-of-dimensionality/)のノートで扱っています。

ラベルがあるなら、PC1 だけの精度と、PCA を使わない時や LDA の精度を一度比べます。PC1 だけの精度が低く、PCA を使わない時に高ければ、前の節の人工データのように、答えが分散の小さい向きにあります。

最後に、2 次元の散布図で塊が重なって見えた時です。標準化を忘れていないかを先に確かめ、それでも重なるなら、PCA が直線の向きにしか写せないことを疑います。曲がった構造を保って 2 次元に並べたい時は、[t-SNE / UMAP](../tsne-umap/) が向いています。冒頭の図の 3 段目のように、PC1 の重みが多くの列に散らばっていれば、少なくとも 1 列の単位に振り回されてはいません。
