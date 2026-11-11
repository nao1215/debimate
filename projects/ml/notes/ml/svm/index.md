---
title: "SVM - SVC を LinearSVC に替えると、なぜ列の値をずらすだけで正解率が 53% に落ちるのか"
date: 2026-05-26
draft: false
series: ["機械学習ノート", "Machine Learning"]
tags: ["machine-learning", "scikit-learn", "supervised"]
weight: 22
topics: ["Machine Learning（評価・概念・アルゴリズム）"]
---

SVM（Support Vector Machine、サポートベクターマシン）は、2 つのクラスの点を分ける境界のうち、境界に最も近い点までの距離が最も大きくなるものを選ぶ分類器です。[scikit-learn](https://scikit-learn.org/stable/modules/svm.html) には、曲がった境界も引ける [`SVC`](https://scikit-learn.org/stable/modules/generated/sklearn.svm.SVC.html) と、直線の境界だけを速く求める [`LinearSVC`](https://scikit-learn.org/stable/modules/generated/sklearn.svm.LinearSVC.html) が、別のクラスとして用意されています。

以下は、人工的に作った 2 つのクラスの点 400 個について、点の並びは変えずに 2 列とも同じ値を足して原点から離していき、`SVC(kernel="linear")` と `LinearSVC` の正解率を 5 分割の[交差検証](../cross-validation/)で測った結果です。どちらも直線の境界を引く線形 SVM です。

{{< figure src="svm_cover.webp" alt="左は横軸がずらし幅 0〜1000 の対数の軸、縦軸が交差検証の正解率の折れ線グラフ。SVC(kernel='linear') と標準化 + LinearSVC は 0.91 前後で横ばい。LinearSVC は 30 まで同じだが、100 で 0.823、300 で 0.598、1000 で 0.527 に落ちる。右はずらし幅 1000 の点で、SVC の境界は青と赤の塊の間を右下がりに通るが、LinearSVC の境界は右上がりで、2 つの塊をそれぞれ斜めに割っている" caption="同じ点の並びを原点から離すと、LinearSVC だけ正解率が落ちる（scikit-learn 1.9.1）" align="center" >}}

1000 ずらすと、`LinearSVC` の正解率は 0.527 で、コインを投げるのと変わりません。境界は、右の図のとおり 2 つの塊を斜めに割っています。scikit-learn は警告を出さず、[標準化](../standardization/)を前に挟むと 0.918 に戻ります。

`SVC` は行が増えると学習が急に遅くなり、scikit-learn の文書も、数万行を超えたら `LinearSVC` などを勧めています。一方で、手元のデータには、西暦の年、絶対温度、UNIX 時刻のように、平均が標準偏差の数十倍を超える列がよくあります。`LinearSVC` に替えて精度が落ちた時に疑うべきなのが、この性質です。

<br>

本記事では、ML を学び始めた人と、scikit-learn の SVM を手元のデータに使うか迷っている人に向けて、次の疑問に答えます。

- SVM は何を求め、サポートベクターとは何か。
- C と γ は、境界の何を変えるのか。
- 行が増えると、SVC の学習はどれだけ遅くなるのか。
- LinearSVC に替えると、なぜ精度が落ちることがあるのか。
- 確率が欲しい時、probability=True で何が起きるのか。
- ロジスティック回帰や勾配ブースティングと比べ、いつ選ぶのか。

実験は scikit-learn 1.9.1 で行いました。図を描く処理も含めた完全なコードは [svm_gen.py](https://github.com/nao1215/debimate/blob/main/projects/ml/scripts/notes/svm_gen.py) にあり、本文のコードで使う `cv` は `StratifiedKFold(n_splits=5, shuffle=True, random_state=0)` です。

---

### マージンとサポートベクター

最初に、2 つのクラスが離れている 80 点で、SVM が何を選ぶかを見ます。2 つのクラスを分ける直線は無数に引けます。SVM は、境界に最も近い点までの距離が最も大きくなる直線を選びます。この距離をマージンと呼びます。

{{< figure src="svm_linear_margin.webp" alt="青いクラス 0 が上、赤いクラス 1 が下に分かれた散布図。右下がりの実線が決定境界で、その上下に平行な破線が 1 本ずつある。上の破線に青い点が 1 つ、下の破線に赤い点が 1 つ乗っていて、黒い丸で囲まれている" caption="線形 SVM の決定境界（実線）とマージン（破線）、サポートベクター（黒い丸）" align="center" >}}

境界の直線は、係数 `w` と切片 `b` で `w · x + b = 0` と書けます。`w · x` は `w` と点 `x` の内積で、各列の値に係数を掛けて足したものです。`||w||` は `w` の長さです。SVM は、全ての点が境界から正しい側に一定以上離れるという条件の下で、`||w||^2` を最小にします。式で書くと、クラスを `y_i ∈ {-1, +1}` として次の通りで、`s.t.` の行が条件です。

```text
min  (1/2) ||w||^2
s.t. y_i (w · x_i + b) ≥ 1   for all i
```

図の 2 本の破線は `w · x + b = ±1` の線で、その間の幅は `2 / ||w||` です。`||w||` を小さくするほど幅が広がるので、この問題はマージンを最大にすることと同じです。目的の関数は下に凸な 2 次式で、条件は 1 次式なので、[凸関数](../../math/convex-functions/)の最適化として、局所的な最小がそのまま全体の最小になります。

<br>

図で黒い丸を付けた 2 点は、破線の上に乗っています。境界はこの 2 点だけで決まり、この点をサポートベクターと呼びます。以下のコードは、サポートベクター以外の 78 点を捨てて学習し直し、係数を比べます。

```python
X, y = make_blobs(n_samples=80, centers=2, cluster_std=1.1, random_state=6)
model = SVC(kernel="linear", C=1.0).fit(X, y)
print(f"サポートベクター: {len(model.support_)} / {len(X)} 点")

# サポートベクター以外の点を全部捨てて学習し直し、係数を比べる
keep = model.support_
again = SVC(kernel="linear", C=1.0).fit(X[keep], y[keep])
print("全点の係数:", model.coef_.round(4), model.intercept_.round(4))
print("サポートベクターだけの係数:", again.coef_.round(4), again.intercept_.round(4))
```

```text
サポートベクター: 2 / 80 点
全点の係数: [[-0.2626 -0.7618]] [-2.9078]
サポートベクターだけの係数: [[-0.2626 -0.7618]] [-2.9078]
```

2 点だけで学習しても、係数も切片も小数点以下 4 桁まで同じでした。破線の外にいる点は、破線を越えない限りどこへ動かしても境界に影響しません。この性質は、後の節で学習の時間と予測の時間を考える時に関わります。

---

### C と γ が変えるもの

実データでは、2 つのクラスの点が重なって、直線で完全には分けられないことの方が普通です。そこで、罰則を払う代わりに、破線の内側に入る点や反対側に入る点も許します。この形をソフトマージンと呼び、罰則の重さを決めるのが `C` です。

```text
min  (1/2) ||w||^2 + C Σ ξ_i
s.t. y_i (w · x_i + b) ≥ 1 - ξ_i,  ξ_i ≥ 0
```

`ξ_i` は各点が破線をどれだけ越えたかの量で、`C` を大きくすると、越えることを強く罰します。最小にする時、`ξ_i` は条件を満たす一番小さい値の `max(0, 1 - y_i (w · x_i + b))` になります。この形は[損失関数](../loss-functions/)で扱っているヒンジ損失です。端が少し重なる 2 つのクラスで `C` を変えると、次の通りです。

```python
rng = np.random.default_rng(0)
X2 = np.vstack([rng.normal([0, 0], 1.0, (40, 2)), rng.normal([3, 3], 1.0, (40, 2))])
y2 = np.array([0] * 40 + [1] * 40)
for C in [0.05, 1.0, 100.0]:
    m = SVC(kernel="linear", C=C).fit(X2, y2)
    width = 2 / np.linalg.norm(m.coef_[0])  # 破線どうしの間隔
    errors = (m.predict(X2) != y2).sum()
    print(f"C={C:>6}: サポートベクター {len(m.support_):2d} 点、マージンの幅 {width:.2f}、"
          f"学習データの誤り {errors} 点")
```

```text
C=  0.05: サポートベクター 22 点、マージンの幅 2.59、学習データの誤り 3 点
C=   1.0: サポートベクター  9 点、マージンの幅 1.43、学習データの誤り 3 点
C= 100.0: サポートベクター  7 点、マージンの幅 0.98、学習データの誤り 2 点
```

{{< figure src="svm_soft_margin_C.webp" alt="3 つの散布図。C=0.05 は破線の間が広く、22 点が黒い丸で囲まれている。C=1.0 は幅 1.43 で 9 点。C=100 は幅 0.98 と狭く、7 点だけが囲まれている。3 つとも境界の向きはほぼ同じ" caption="C を変えた時のマージンの幅とサポートベクター" align="center" >}}

`C` が小さいと幅は 2.59 と広く、破線の内側に入った 22 点がサポートベクターになります。`C` を 100 にすると幅は 0.98 まで縮み、境界は 7 点で決まります。誤りは 3 点から 2 点に減っただけで、重なった所の点はどの `C` でも分けきれません。`C` は大きいほど罰則の項が重くなるので、[ロジスティック回帰](../logistic-regression/)の `C` と同じく、[正則化](../regularization/)の強さの逆数として働きます。

<br>

#### 曲がった境界を引くカーネル

直線では分けられないデータもあります。以下は、内側の円と外側の円の 2 つのクラスです。左の 2 列のままでは直線を引けませんが、原点からの距離の二乗 `z = x1^2 + x2^2` を 3 つ目の列として足すと、右のように平面で分けられます。

```python
X_c, y_c = make_circles(n_samples=200, factor=0.4, noise=0.08, random_state=0)
z = X_c[:, 0] ** 2 + X_c[:, 1] ** 2  # 3 つ目の列（原点からの距離の二乗）
print(f"内側の円: z の最大 {z[y_c == 1].max():.2f}、外側の円: z の最小 {z[y_c == 0].min():.2f}")
```

```text
内側の円: z の最大 0.34、外側の円: z の最小 0.62
```

{{< figure src="svm_kernel_trick.webp" alt="左は内側の赤い円と外側の青い円の 2 次元の散布図。右は同じ点に z = x1² + x2² の高さを足した 3 次元の散布図で、赤い点は底の方に、青い点は上の方に集まり、その間を z = 0.5 の緑の平面が通っている" caption="列を 1 つ足すと、直線で分けられなかった点が平面で分けられる" align="center" >}}

内側の円の `z` は最大 0.34、外側の円の `z` は最小 0.62 なので、その間の `z = 0.5` の平面で完全に分かれます。

ただし、列を足すたびに点の座標を作るのは、列が増えると重くなります。そこで SVM は、点の座標そのものではなく、2 点の内積だけを使って学習と予測ができることを利用します。境界は最初の節で見たとおりサポートベクターで決まり、決定関数は、サポートベクターと新しい点の内積を重みを付けて足した形に書き直せるからです。

`z` を足した 3 列の内積は `x1 x1' + x2 x2' + z z'` で、`z = x1^2 + x2^2` なので元の 2 列だけから計算できます。以下のコードは、3 列を作って直線の SVM を学習した場合と、元の 2 列のまま、この内積を返す関数を `kernel` に渡した場合を比べます。

```python
X3 = np.column_stack((X_c, z))
lin3 = SVC(kernel="linear").fit(X3, y_c)


def k_z(A, B):
    # 3 列の内積 x1*x1' + x2*x2' + z*z' を、元の 2 列だけから計算する
    return A @ B.T + np.outer((A ** 2).sum(axis=1), (B ** 2).sum(axis=1))


ker = SVC(kernel=k_z).fit(X_c, y_c)
gap = np.abs(lin3.decision_function(X3) - ker.decision_function(X_c)).max()
print(f"3 列の直線の SVM とカーネルの SVM の決定関数の差の最大: {gap:.1e}")
print(f"正解率: 3 列の直線 {lin3.score(X3, y_c):.3f}、カーネル {ker.score(X_c, y_c):.3f}")
```

```text
3 列の直線の SVM とカーネルの SVM の決定関数の差の最大: 4.4e-15
正解率: 3 列の直線 1.000、カーネル 1.000
```

2 つの決定関数は計算の誤差の範囲で一致しました。列を足した先の内積を返す関数をカーネルと呼び、`z` の列を作らずに、3 列で平面を引いたのと同じ境界が元の 2 列の上に円として現れます。`SVC` の既定は RBF（Radial Basis Function、動径基底関数）カーネル `K(x, x') = exp(-γ ||x - x'||^2)` で、2 点が近いほど 1、遠いほど 0 に近づきます。RBF は、足す列を自分で選ばなくても、点の近さで曲がった境界を引けるカーネルです。

<br>

#### γ で決まる 1 点の影響範囲

RBF カーネルの `γ` は、1 つの点が境界に影響する範囲を決めます。`γ` が小さいと遠くの点まで影響して境界は滑らかになり、大きいと影響が点のすぐ近くに限られます。三日月の形の 2 つのクラスで比べました。

```python
X_m, y_m = make_moons(n_samples=300, noise=0.15, random_state=0)
for gamma in [0.1, 1.0, 1000.0]:
    m = SVC(kernel="rbf", gamma=gamma, C=1.0).fit(X_m, y_m)
    test = cross_val_score(SVC(kernel="rbf", gamma=gamma, C=1.0), X_m, y_m, cv=cv).mean()
    print(f"gamma={gamma:>6}: サポートベクター {len(m.support_):3d} 点、"
          f"学習データの正解率 {m.score(X_m, y_m):.3f}、交差検証の正解率 {test:.3f}")
```

```text
gamma=   0.1: サポートベクター 121 点、学習データの正解率 0.853、交差検証の正解率 0.853
gamma=   1.0: サポートベクター  51 点、学習データの正解率 0.987、交差検証の正解率 0.983
gamma=1000.0: サポートベクター 296 点、学習データの正解率 1.000、交差検証の正解率 0.830
```

{{< figure src="svm_rbf_gamma.webp" alt="3 つの散布図。γ=0.1 は境界がほぼ直線で、三日月の端が反対側に入っている。γ=1.0 は境界が三日月の形に沿って曲がる。γ=1000 は青い点の 1 つ 1 つを小さな島で囲み、それ以外の全てが赤のクラスになっている" caption="γ を変えた時の RBF カーネルの境界" align="center" >}}

`γ = 1000` では、学習データの正解率は 1.000 ですが、交差検証では 0.830 まで落ちます。図の右のように青い点を 1 つずつ小さな島で囲み、点の無い所は全て赤と判定するからで、学習データを覚え込んだ[過学習](../overfitting/)の状態です。300 点のうち 296 点がサポートベクターになっている点にも注目してください。

`C` と `γ` はどちらも、値を大きくすると境界を複雑にする向きに効くので、組み合わせを[ハイパーパラメータ](../hyperparameter/)の探索で交差検証にかけて決めます。`γ` の既定の `gamma="scale"` は `1 / (列の数 × X 全体の分散)` で、列の値の大きさに合わせて決まります。

---

### 行の数と学習の時間

前の節の `γ = 1000` のように、サポートベクターが増えるほど、学習も予測も重くなります。scikit-learn の `SVC` の文書には、学習の時間は少なくとも行の数の 2 乗で伸び、数万行を超えると現実的でなくなることがある、と書かれています。20 列の人工データで行の数を変えて、どのくらい伸びるかを測りました。

比べる相手は、`LinearSVC`、[ロジスティック回帰](../logistic-regression/)、[勾配ブースティング](../gradient-boosting/)の `HistGradientBoostingClassifier` です。[`make_classification`](https://scikit-learn.org/stable/modules/generated/sklearn.datasets.make_classification.html) で作った、直線では分けきれない 2 クラスのデータを使い、先頭の行で学習して、後ろの 5000 行で正解率を測りました。

`SVC` の LIBSVM は 1 スレッドで動くので、全てのモデルを [threadpoolctl](https://github.com/joblib/threadpoolctl) の `threadpool_limits(1)` で 1 スレッドに揃えています。以下のコードは抜粋です。

```python
models = {
    "SVC（RBF）": lambda: make_pipeline(StandardScaler(), SVC()),
    "LinearSVC": lambda: make_pipeline(StandardScaler(), LinearSVC()),
    "ロジスティック回帰": lambda: make_pipeline(StandardScaler(), LogisticRegression()),
    "勾配ブースティング": lambda: HistGradientBoostingClassifier(random_state=0),
}
with threadpool_limits(1):
    for n in [1000, 2000, 5000, 10000, 20000, 40000]:
        # 先頭 n 行で学習し、後ろの 5000 行で正解率を測る
        Xt, yt = make_classification(n_samples=n + 5000, n_features=20, n_informative=10,
                                     flip_y=0.05, random_state=0)
        for name, make in models.items():
            ...  # make().fit(Xt[:n], yt[:n]) の時間を 3 回測り、中央値を取る
```

{{< figure src="svm_fit_time.webp" alt="横軸が行の数 1,000〜40,000、縦軸が学習の時間の両対数のグラフ。赤い SVC は 0.03 秒から急な傾きで上がり、40,000 行で 10 秒を超える。緑の勾配ブースティングは 0.18 秒から 1 秒へ緩やかに上がる。青の LinearSVC と灰色のロジスティック回帰は 0.003 秒から緩やかに上がり、40,000 行でも 0.1 秒未満。凡例に 4 万行での正解率があり、SVC 0.944、勾配ブースティング 0.931、LinearSVC とロジスティック回帰は 0.754" caption="行の数を増やした時の学習の時間（両対数、1 スレッド、3 回の中央値）" align="center" >}}

`SVC` の線は、5000 行より先では両対数で傾き 2 前後の直線になり、行を 2 倍にすると時間は約 4 倍になります。4 万行では、同じくらいの正解率の勾配ブースティングの約 20 倍の時間が掛かりました。サポートベクターも 4 万行のうち約 1 万点まで増えていて、予測の時もこの全ての点とのカーネルを計算します。

<br>

<details><summary>計測の条件と出力</summary>

時間は 32 コアの PC で、他の処理と並行して動いている中で測りました。測った時の load average は 15 前後で、同じ 4 万行の `SVC` が回によって 11〜23 秒と揺れました。本文では、他のモデルとの倍率と桁の差だけを使っています。図はこの時の値で描き、時間は小数点以下 3 桁に丸めて生成元の [svm_gen.py](https://github.com/nao1215/debimate/blob/main/projects/ml/scripts/notes/svm_gen.py) に記録しています。

```text
  1000 行: SVC   0.033 / 勾配ブースティング 0.176 / LinearSVC 0.003 / ロジスティック回帰 0.003 秒
  2000 行: SVC   0.054 / 勾配ブースティング 0.230 / LinearSVC 0.004 / ロジスティック回帰 0.003 秒
  5000 行: SVC   0.314 / 勾配ブースティング 0.239 / LinearSVC 0.006 / ロジスティック回帰 0.005 秒
 10000 行: SVC   1.246 / 勾配ブースティング 0.349 / LinearSVC 0.012 / ロジスティック回帰 0.008 秒
 20000 行: SVC   6.323 / 勾配ブースティング 0.746 / LinearSVC 0.037 / ロジスティック回帰 0.023 秒
 40000 行: SVC  20.848 / 勾配ブースティング 1.041 / LinearSVC 0.083 / ロジスティック回帰 0.047 秒
4 万行の正解率: SVC（RBF） 0.944、LinearSVC 0.754、ロジスティック回帰 0.754、勾配ブースティング 0.931
SVC の学習時間の傾き（5000 行以降、両対数）: 2.05
```

丸めたので、ロジスティック回帰の 1000 行と 2000 行はどちらも 0.003 秒で、図の灰色の線はそこで平らに見えます。サポートベクターの数は、1000 行で 600 点、4 万行で 9877 点でした。

</details>

<br>

`LinearSVC` は、1 万行を超えると `SVC` より 2 桁以上速く、文書が勧める理由が分かります。ただし、このデータでは正解率が 0.754 で、境界が曲がったデータでは直線の境界の限界が出ます。速さのために替えると、冒頭の図の性質にも出会います。

---

### LinearSVC で精度が落ちる理由

`SVC(kernel="linear")` と `LinearSVC` は、どちらも線形 SVM ですが、中身の実装が違います。`SVC` は [LIBSVM](https://www.csie.ntu.edu.tw/~cjlin/libsvm/)、`LinearSVC` は [LIBLINEAR](https://www.csie.ntu.edu.tw/~cjlin/liblinear/) を使います。どちらも国立台湾大学で開発された C++ のライブラリで、LIBLINEAR は直線の境界だけに絞った代わりに、行や列が多くても速く解けます。冒頭の図の実験は、次のコードです。どちらの列も標準偏差は約 1.4 なので、ずらし幅 100 は、列の平均が標準偏差の約 70 倍になった状態です。出力の `SVC` は `SVC(kernel="linear")` です。

```python
Xb, yb = make_blobs(n_samples=400, centers=[[0, 0], [2, 2]], cluster_std=1.0, random_state=0)
for s in [0, 1, 3, 10, 30, 100, 300, 1000]:
    Xs = Xb + s  # 2 列とも同じ値 s だけずらす。点の並びは変わらない
    acc_svc = cross_val_score(SVC(kernel="linear"), Xs, yb, cv=cv).mean()
    acc_lin = cross_val_score(LinearSVC(), Xs, yb, cv=cv).mean()
    acc_std = cross_val_score(make_pipeline(StandardScaler(), LinearSVC()), Xs, yb, cv=cv).mean()
    print(f"ずらし幅 {s:4d}: SVC {acc_svc:.3f} / LinearSVC {acc_lin:.3f} / 標準化+LinearSVC {acc_std:.3f}")
X_far = Xb + 1000
svc_far = SVC(kernel="linear").fit(X_far, yb)
lin_far = LinearSVC().fit(X_far, yb)
print("SVC(kernel='linear') の係数:", svc_far.coef_.round(3), "切片:", svc_far.intercept_.round(1))
print("LinearSVC の係数:", lin_far.coef_.round(3), "切片:", lin_far.intercept_.round(2))
```

```text
ずらし幅    0: SVC 0.912 / LinearSVC 0.915 / 標準化+LinearSVC 0.918
ずらし幅    1: SVC 0.912 / LinearSVC 0.915 / 標準化+LinearSVC 0.918
ずらし幅    3: SVC 0.912 / LinearSVC 0.915 / 標準化+LinearSVC 0.918
ずらし幅   10: SVC 0.912 / LinearSVC 0.915 / 標準化+LinearSVC 0.918
ずらし幅   30: SVC 0.912 / LinearSVC 0.910 / 標準化+LinearSVC 0.918
ずらし幅  100: SVC 0.912 / LinearSVC 0.823 / 標準化+LinearSVC 0.918
ずらし幅  300: SVC 0.912 / LinearSVC 0.598 / 標準化+LinearSVC 0.918
ずらし幅 1000: SVC 0.912 / LinearSVC 0.527 / 標準化+LinearSVC 0.918
SVC(kernel='linear') の係数: [[1.349 1.302]] 切片: [-2653.2]
LinearSVC の係数: [[ 0.028 -0.027]] 切片: [-0.74]
```

ずらし幅 1000 では、2 つの塊の中心は (1000, 1000) と (1002, 1002) です。正しく分ける境界は、その中点 (1001, 1001) を通る `x1 + x2 ≒ 2002` の付近で、`SVC` は切片を -2653.2 にしてこの線を引いています。点が原点から遠いほど、境界を点の所まで運ぶために大きな切片が要ります。

`LinearSVC` の文書には、LIBLINEAR は切片を他の係数と同じく罰則に入れる、と書かれています。値が 1 の列を内部で 1 つ足し、その列の係数を切片として扱うからです。すると -2653 の切片は、その 2 乗が `||w||^2` の罰則にそのまま加わります。`LinearSVC` は、それより罰則の小さい係数として、切片 -0.74 と、ほぼ 0 の係数を選びました。冒頭の右の図の、塊を斜めに割る境界がそれです。

<br>

`SVC` の LIBSVM は切片を罰則に入れないので、正解率は 0.912 のままです。`LinearSVC` で直す方法は 2 つあります。

1 つは、前に `StandardScaler` を置くことです。標準化は各列から平均を引くので、点の中心が原点に戻り、大きな切片が要らなくなります。冒頭の図の緑の線のとおり、どのずらし幅でも 0.918 です。

もう 1 つは `intercept_scaling` を大きくして、足す列の値を 1 から大きくすることです。同じ切片を小さな係数で作れます。ずらし幅 1000 で、同じ 5 分割の交差検証で測りました。

```python
lin_scaled = LinearSVC(intercept_scaling=1000, max_iter=100000).fit(X_far, yb)
acc_scaled = cross_val_score(LinearSVC(intercept_scaling=1000, max_iter=100000), X_far, yb, cv=cv).mean()
print(f"LinearSVC(intercept_scaling=1000) の交差検証の正解率: {acc_scaled:.3f}、切片: {lin_scaled.intercept_.round(1)}")
```

```text
LinearSVC(intercept_scaling=1000) の交差検証の正解率: 0.918、切片: [-1219.2]
```

正解率は 0.918 で、標準化した場合と同じ所まで戻りました。`max_iter=100000` は念のため付けたもので、既定の 1000 回のままでも 10 回で収束しました。

`SVC(kernel="linear")` と `LinearSVC` の違いはこれだけではありません。`LinearSVC` の既定の損失はヒンジ損失を 2 乗した `squared_hinge` で、3 クラス以上では 1 クラスと残り全てを分ける one-vs-rest を使います。`SVC` は 2 クラスの組ごとに分ける one-vs-one です。同じ線形 SVM という名前でも解く問題が少しずつ違うので、替えた後は、同じデータで正解率を比べ直す必要があります。

---

### 確率が要る時

`SVC` の `predict` が返すのはクラスで、`decision_function` が返すのは `w · x + b` のような符号付きの値で、境界から離れるほど絶対値が大きくなります。どちらも確率ではありません。「80% 以上の確率で陽性なら通知する」のように確率で判断したい時、scikit-learn 1.9.1 の `SVC` には `probability=True` という引数があります。これを付けると、内部で 5 分割の交差検証をして、決定関数の値を [Platt scaling](https://scikit-learn.org/stable/modules/svm.html#scores-probabilities) で確率に写す曲線を学習します。

以下は、scikit-learn に同梱の乳がんのデータ [breast_cancer](https://scikit-learn.org/stable/modules/generated/sklearn.datasets.load_breast_cancer.html) で、`predict` と `predict_proba` を比べたコードです。クラス 0 が悪性、クラス 1 が良性です。

```python
Xbc, ybc = load_breast_cancer(return_X_y=True)
Xbc_s = StandardScaler().fit_transform(Xbc)
prob_model = SVC(probability=True, random_state=0).fit(Xbc_s, ybc)
dec = prob_model.decision_function(Xbc_s)
p_benign = prob_model.predict_proba(Xbc_s)[:, 1]  # クラス 1（良性）の確率
pred = prob_model.predict(Xbc_s)
A, B = prob_model.probA_[0], prob_model.probB_[0]
odd = np.where(pred != (p_benign > 0.5).astype(int))[0]
print(f"Platt scaling の係数 A={A:.3f}、B={B:.3f}、確率が 0.5 になる決定関数の値 {B / A:.3f}")
print(f"predict と predict_proba が食い違う点: {len(odd)} / {len(ybc)}")
for i in odd:
    print(f"  決定関数 {dec[i]:.3f}、predict {pred[i]}（良性）、良性の確率 {p_benign[i]:.3f}")
```

```text
Platt scaling の係数 A=-3.645、B=-0.242、確率が 0.5 になる決定関数の値 0.066
predict と predict_proba が食い違う点: 1 / 569
  決定関数 0.026、predict 1（良性）、良性の確率 0.463
```

569 件のうち 1 件で、`predict` は良性と答え、`predict_proba` は良性の確率を 0.463 と答えました。確率の大きい方を答えにすると、悪性になります。

{{< figure src="svm_proba.webp" alt="左は横軸が決定関数の値 -3〜3、縦軸が良性の確率の散布図で、点は灰色の S 字の曲線に乗る。決定関数 0 の縦の点線と確率 0.5 の横の点線の交点のすぐ下に、緑の点が 1 つあり赤い丸で囲まれている。右は 0 の付近を拡大した図で、決定関数 0 から 0.066 の帯が赤く塗られ、その中の点は predict が良性なのに確率は 0.5 未満になる" caption="predict は決定関数の 0 で、確率は Platt scaling の曲線の 0.5 で分かれる" align="center" >}}

`predict` は決定関数の値 `f` が 0 より大きいかで決まります。確率の方は、交差検証で学習した S 字の曲線です。

scikit-learn の 2 クラスでは、良性の確率が `1 / (1 + exp(A·f - B))` とほぼ一致しました。決定関数が -0.5〜0.5 の 20 点では差が 0.0002 以下で、差が最大の 0.0025 になったのは確率が 1 に近い端の点でした。端でずれるのは、LIBSVM が 2 クラスでも、確率を多クラス用の反復で合わせ直してから返すからです。[同梱の svm.cpp](https://github.com/scikit-learn/scikit-learn/blob/1.9.1/sklearn/svm/src/libsvm/svm.cpp) の `multiclass_probability` は、0.5 から反復を始め、反復の残差が `0.005 / クラスの数` を下回ると止めます。反復を途中で止めるので、Platt の式の値とは僅かにずれます。生成元でこの反復を Python に写すと、全 569 点で `predict_proba` と 3.3e-16 以内で一致しました。Platt の論文の式 `1 / (1 + exp(A·f + B))` と符号の付き方が違うのは、scikit-learn が 2 クラスの決定関数の符号を反転して返すためで、本文の式は手元の出力に合わせて確かめた形です。

確率が 0.5 になるのは `exp` の中が 0 になる `f = B / A` の所で、出力の A と B から 0.066 です。0 から 0.066 の間に入った点は、2 つの答えが食い違います。scikit-learn の文書も、`predict_proba` は `predict` と一致しないことがあると明記しています。

10 クラスの手書き数字 [digits](https://scikit-learn.org/stable/modules/generated/sklearn.datasets.load_digits.html) でも、5 分割で学習と予測を 5 回行い、各回で学習に使わなかった分を予測して数えました。

```python
Xd, yd = load_digits(return_X_y=True)
odd_d = 0
for tr, te in cv.split(Xd, yd):
    md = SVC(probability=True, random_state=0).fit(Xd[tr], yd[tr])
    odd_d += (md.predict(Xd[te]) != md.predict_proba(Xd[te]).argmax(axis=1)).sum()
print(f"digits（10 クラス）で食い違う点: {odd_d} / {len(yd)}")
```

```text
digits（10 クラス）で食い違う点: 8 / 1797
```

1797 件のうち 8 件で、`predict` の答えと確率の最も大きいクラスが食い違いました。

<br>

`probability` の引数は scikit-learn 1.9 で非推奨になり、1.11 で削除される予定です。1.9.1 で使うと `FutureWarning` が出て、代わりに [`CalibratedClassifierCV`](https://scikit-learn.org/stable/modules/generated/sklearn.calibration.CalibratedClassifierCV.html) で `CalibratedClassifierCV(SVC(), ensemble=False)` と書くよう案内されます。確率の曲線の当てはめ方と、確率が実際の割合に合っているかの確かめ方は、[確率の校正](../probability-calibration/)のノートで扱っています。

確率そのものが欲しいなら、最初から確率を出すロジスティック回帰も候補です。次の節で見るとおり、表のデータでは正解率もほとんど変わりません。

---

### ロジスティック回帰・勾配ブースティングとの比較

最後に、scikit-learn に同梱の 3 つのデータで、`SVC` を他の手法と並べました。正解率は 5 分割の交差検証の平均です。

```python
compare = {
    "SVC（標準化なし）": lambda: SVC(),
    "SVC（標準化あり）": lambda: make_pipeline(StandardScaler(), SVC()),
    "ロジスティック回帰（標準化あり）": lambda: make_pipeline(StandardScaler(), LogisticRegression(max_iter=5000)),
    "勾配ブースティング": lambda: HistGradientBoostingClassifier(random_state=0),
}
for dname, loader in [("breast_cancer", load_breast_cancer), ("wine", load_wine), ("digits", load_digits)]:
    Xc, yc = loader(return_X_y=True)
    print(f"{dname}（{Xc.shape[0]} 行 {Xc.shape[1]} 列）: " +
          "、".join(f"{k} {cross_val_score(f(), Xc, yc, cv=cv).mean():.3f}" for k, f in compare.items()))
```

| データ | 行 × 列 | SVC | SVC（標準化） | ロジスティック回帰 | 勾配ブースティング |
|---|---|---|---|---|---|
| breast_cancer | 569 × 30 | 0.921 | 0.977 | 0.979 | 0.970 |
| wine | 178 × 13 | 0.657 | 0.983 | 0.983 | 0.972 |
| digits | 1797 × 64 | 0.987 | 0.981 | 0.969 | 0.973 |

表の [wine](https://scikit-learn.org/stable/modules/generated/sklearn.datasets.load_wine.html) は、ワインの化学分析の 13 列で、proline の列だけ値の桁が飛び抜けて大きいデータです。標準化しない `SVC` は 0.657 で、標準化すると 0.983 になりました。RBF カーネルは点どうしの距離で決まるので、距離が proline の 1 列でほぼ決まってしまうからです。同じ wine で [PCA](../pca/) の第 1 主成分が proline に乗っ取られる話と、原因は同じです。

breast_cancer と wine では、標準化した `SVC` とロジスティック回帰の差は 0.002 以内でした。digits だけは、標準化しない `SVC` が 0.987 で一番高くなりました。digits の 64 列は 8×8 の画素の濃さで、全ての列が同じ単位です。標準化すると、ほとんど 0 のままの端の画素まで、他の画素と同じ重さに引き上げてしまうからだと考えられます。

<br>

前の節の 4 万行の人工データでは、`SVC` が 0.944、勾配ブースティングが 0.931、直線の境界しか引けないロジスティック回帰と `LinearSVC` は 0.754 でした。`SVC` が勝つのは、境界が曲がっていて、行が数万までに収まる時です。行が増えるほど、近い正解率を 20 分の 1 の時間で出す勾配ブースティングの方が有利になります。

この比較の外に、SVM の得意な使い方も 2 つあります。単語の出現を列にした文書の分類のように列が数万ある疎なデータでは、線形の SVM が速く、よく使われてきました。正常なデータだけから範囲を学ぶ [`OneClassSVM`](https://scikit-learn.org/stable/modules/generated/sklearn.svm.OneClassSVM.html) は、[異常検知](../anomaly-detection/)で使えます。

---

### SVM を選ぶ前に確かめること

SVM を手元のデータに使うか迷っている人は、まずロジスティック回帰と勾配ブースティングを同じ交差検証で並べます。前の節の表のとおり、表のデータでは 3 つの差が小さいことが多く、`SVC` が明確に勝つのは境界が曲がっている時です。並べる時は `StandardScaler` と `SVC` を `make_pipeline` で 1 本にし、検証用のデータの平均や標準偏差が学習に漏れる[データリーク](../data-leakage/)を避けます。

`SVC` を選んだら、行の数を確かめます。学習の時間は行の数のほぼ 2 乗で伸び、4 万行では勾配ブースティングの約 20 倍掛かりました。`C` と `γ` の組み合わせを交差検証で探すと、この時間に組み合わせの数と分割の数が掛かります。

速さのために `LinearSVC` に替えるなら、標準化を pipeline に入れたまま替えます。標準化を外したり、木のモデルの前処理を流用したりすると、冒頭の図の赤い線のとおり、列の平均が標準偏差の数十倍を超えた辺りから、警告も出ずに正解率が落ちます。替えた後に、`SVC(kernel="linear")` と正解率を一度比べれば、この落とし穴には気付けます。

確率が要るなら、`probability=True` は 1.11 で無くなる予定なので使わず、`CalibratedClassifierCV` を通すか、ロジスティック回帰を選びます。
