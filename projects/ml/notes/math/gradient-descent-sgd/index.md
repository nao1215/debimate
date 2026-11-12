---
title: "最急降下法・SGD - 標準化しても SGDRegressor の R² が 10 回とも負になる理由"
date: 2026-05-26
draft: false
series: ["機械学習ノート", "Mathematics"]
tags: ["machine-learning", "math", "optimization"]
weight: 19
topics: ["Mathematics（数学の基礎）"]
---

最急降下法（gradient descent）は、[損失関数](../../ml/loss-functions/)の[勾配](../partial-derivative-gradient/)と反対の向きにパラメータを少しずつ動かし、損失が最小になる所を探す反復の手法です。1 回に動かす量を決める係数を学習率と呼びます。確率的勾配降下法（stochastic gradient descent、SGD）は、勾配を全ての行ではなく、ランダムに選んだ 1 行か数行から計算して更新を繰り返します。[scikit-learn](https://scikit-learn.org/stable/) には、[線形回帰](../../ml/linear-regression/)を SGD で学習する [`SGDRegressor`](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.SGDRegressor.html) があります。線形回帰のパラメータは、各列に掛ける係数と、全ての行に足す切片で、両方をまとめて重みと呼びます。

以下は、scikit-learn に同梱の [California Housing](https://scikit-learn.org/stable/modules/generated/sklearn.datasets.fetch_california_housing.html) で、`SGDRegressor` を既定の設定のまま 10 回ずつ学習した結果です。学習データの行を並べ替える乱数の種だけを 0〜9 に変えました。California Housing は、カリフォルニア州の区画ごとに住宅価格の中央値と所得・人口など 8 列を並べた、20640 行のデータです。

図の 5 段は学習の前の処理の違いです。標準化は、各列から平均を引いて[標準偏差](../stddev/)で割り、平均 0・標準偏差 1 に揃えます。`RobustScaler` は、平均と標準偏差の代わりに中央値と[四分位](../quantile/)範囲を使う、外れ値に強いとされる前処理です。「±3 で切る」は、標準化した後に絶対値が 3 を超える値を ±3 に置き換えます。`eta0` は学習率の初期値で、既定は 0.01 です。

横軸はテストデータの[決定係数](../../ml/regression-metrics/) R² で、1 なら全て当たり、負なら平均値を返すだけの予測より悪い予測です。

{{< figure src="gd_cover.webp" alt="5 段の点の並び。横軸はテストデータの R² で、-1 より左は左ほど桁で縮めた目盛、灰色の実線は R² = 0。そのままは 10 回とも -1.5×10^27〜-6.0×10^30 で中央値 -1.5×10^29。標準化は 10 回とも -368〜-29380 で中央値 -4146。RobustScaler は中央値 -6.8×10^21。標準化と eta0=0.001 は 10 回とも 0.583 前後、標準化して ±3 で切ると 10 回とも 0.642 前後。破線は LinearRegression の 0.594" caption="SGDRegressor を 10 回ずつ学習した時のテストデータの R²。横軸の -1 より左は桁で縮めた目盛（scikit-learn 1.9.1）" align="center" >}}

横軸の -1 より左は左ほど桁で縮めてあり、-1 から 1 の間だけが普通の目盛です。灰色の実線は R² = 0 です。

列の値をそのまま渡すと R² は -10²⁹ ほどで、標準化しても 10 回とも負でした。反復せずに式で解く `LinearRegression` は 0.594 です。標準化して ±3 で切ると 10 回とも 0.642 になり、`eta0` を 0.01 から 0.001 に下げても 0.583 になります。警告はどの学習でも 0 件でした。

原因は、標準化した後も学習用の 16512 行のうち 22 行だけ値が極端に大きく、学習率 0.01 ではその行で 1 回更新するたびに重みが急に大きくなることです。手元の CSV で R² が大きな負の値になった時も、ニューラルネットで学習率や、1 回の更新に使う行の数であるバッチの大きさを変えたら損失が NaN（数値でない値）になった時も、同じ仕組みが関わっています。

<br>

本記事では、最急降下法の式を自分で確認したい人と、`SGDRegressor` を手元のデータに使う人に向けて、次の疑問に答えます。

- 最急降下法は何を繰り返し、学習率はどこまで上げられるのか。
- 列の単位を変えると、なぜ収束までの回数が変わるのか。
- SGD は、1 行で更新すると何が変わるのか。
- バッチの大きさを変えると、なぜ発散したりしなかったりするのか。
- `SGDRegressor` の既定は何をしていて、なぜ標準化しても壊れるのか。

実験は scikit-learn 1.9.1 と [NumPy](https://numpy.org/) 2.5.4 で行い、図を描く処理も含む完全なコードは [gradient-descent-sgd_gen.py](https://github.com/nao1215/debimate/blob/main/projects/ml/scripts/notes/gradient-descent-sgd_gen.py) にあります。

---

### 更新式と学習率の上限

最急降下法の更新は、パラメータを `θ`、学習率を `η`、損失を `L` とすると、次の 1 行です。

`θ_next = θ - η ∇L(θ)`

1 次元の `f(x) = (x - 3)² + 1` で確認します。微分は `f'(x) = 2(x - 3)` なので、更新式に代入すると `x_next - 3 = (1 - 2η)(x - 3)` になります。最小点 3 までの距離が、1 回の更新で `|1 - 2η|` 倍になるということです。

この 2 は `f` の 2 階微分で、関数の曲がり方の強さを表すので曲率と呼びます。曲率を `λ` と書くと、2 次関数なら 1 回で距離が `|1 - ηλ|` 倍になります。以下のコードは、4 つの学習率で 10 回更新し、最小点までの距離を測ります。

```python
lam = 2.0  # f(x) = (x - 3)² + 1 の 2 階微分（曲率）
for eta in [0.05, 0.3, 0.9, 1.05]:
    x = -0.5
    for _ in range(10):
        x = x - eta * 2 * (x - 3)  # f'(x) = 2(x - 3)
    print(f"η={eta}: ηλ={eta * lam:.1f}、1 回で距離が {abs(1 - eta * lam):.1f} 倍、"
          f"10 回後の最小点までの距離 {abs(x - 3):.4f}")
```

```text
η=0.05: ηλ=0.1、1 回で距離が 0.9 倍、10 回後の最小点までの距離 1.2204
η=0.3: ηλ=0.6、1 回で距離が 0.4 倍、10 回後の最小点までの距離 0.0004
η=0.9: ηλ=1.8、1 回で距離が 0.8 倍、10 回後の最小点までの距離 0.3758
η=1.05: ηλ=2.1、1 回で距離が 1.1 倍、10 回後の最小点までの距離 9.0781
```

以下は、学習率と曲率の積 `ηλ` ごとに、1 回で距離が何倍になるかを描いた図です。

{{< figure src="gd_contraction.webp" alt="横軸は学習率と曲率の積 ηλ で 0〜2.4、縦軸は 1 回の更新で最小点までの距離が何倍になるか。V 字の線で、ηλ=1 で 0 倍、0〜1 の緑の帯は同じ側から近づく、1〜2 のオレンジの帯は反対側へ飛び越えながら近づく、2 を超える赤の帯は 1 倍を超えて発散。η=0.05 は 0.9 倍、0.3 は 0.4 倍、0.9 は 0.8 倍、1.05 は 1.1 倍の位置に点がある" caption="学習率 × 曲率と、1 回の更新で最小点までの距離が何倍になるか" align="center" >}}

`ηλ` が 1 なら 1 回で最小点に着き、2 を超えると最小点を飛び越えるたびに遠ざかります。つまり、学習率は `2 / λ` 未満でなければ発散します。上限の近くの 0.9 も、1 回で 0.8 倍にしか縮まないので、0.3 より遅くなります。同じ関数で更新の軌跡を追う実験は、[凸関数](../convex-functions/)で扱っています。

---

### 列の単位と収束までの回数

1 次元では曲率は 1 つでしたが、重みが 2 つ以上になると、重みを動かす向きごとに曲率が違います。損失を重みで 2 回微分した値を並べた行列をヘッセ行列と呼び、これを[固有値分解](../eigen-decomposition/)すると、固有値が各向きの曲率になります。学習率は全ての向きで共通なので、発散しない上限は最も大きい曲率 `λmax` で `2 / λmax` に決まり、最も小さい曲率 `λmin` の向きは、その学習率で少しずつしか進みません。

線形回帰の予測は重みと列の値の積の和なので、二乗誤差を重みで 2 回微分すると、列の値の二乗が出てきます。そのため、ある列を `k` 倍すると、その列の重みに対する曲率は `k²` 倍になります。m で測った列を cm に直すと、その列の曲率は 1 万倍です。以下のコードは、2 列の線形回帰で 2 列目の単位だけを `k` 倍にし、発散しない範囲の学習率で、最小点の 0.1% 以内に入るまでの回数を数えます。

```python
rng = np.random.default_rng(0)
n = 200
x1, x2 = rng.standard_normal(n), rng.standard_normal(n)
y_toy = 1.0 * x1 + 0.5 * x2 + 0.1 * rng.standard_normal(n)

for k in [1, 2, 5, 10, 20, 50, 100]:
    Xk = np.column_stack([x1, k * x2])  # 2 列目の単位だけを k 倍にする（m を cm にするなど）
    H = Xk.T @ Xk / n  # 損失 mean((Xw - y)²) / 2 の曲率をまとめた行列（ヘッセ行列）
    lam_min, lam_max = np.linalg.eigvalsh(H)
    eta = 1.0 / lam_max  # 発散しない上限 2 / λmax の半分
    w_star = np.linalg.lstsq(Xk, y_toy)[0]
    w, steps = np.zeros(2), 0
    while np.linalg.norm(w - w_star) > 1e-3 * np.linalg.norm(w_star):
        w = w - eta * Xk.T @ (Xk @ w - y_toy) / n
        steps += 1
    print(f"k={k:>3}: 曲率 λmin={lam_min:.2f} λmax={lam_max:.1f}、学習率 {eta:.5f}、収束までの回数 {steps}")
```

```text
k=  1: 曲率 λmin=0.90 λmax=1.1、学習率 0.92125、収束までの回数 4
k= 10: 曲率 λmin=0.92 λmax=105.9、学習率 0.00944、収束までの回数 792
k=100: 曲率 λmin=0.92 λmax=10590.4、学習率 0.00009、収束までの回数 79509
```

出力は 7 行のうち 3 行を載せました。以下の図の左 2 つは損失の等高線と 30 回の更新の軌跡で、右は 7 通りの `k` の回数です。

{{< figure src="gd_scale.webp" alt="3 つの図。左は 2 列目が 1 倍の場合で、原点から星印の最小点 (1, 0.5) へほぼ真っ直ぐ進み、数回で着く。中央は 2 列目を 10 倍した場合で、縦軸は 2 列目の重みを 10 倍して元の単位に戻した値。軌跡は最初に縦へ 0.45 まで上がり、その後は横へ 0.23 までしか進まない。右は 2 列目に掛けた倍率 k と、最小点の 0.1% 以内に入るまでの回数の両対数のグラフで、k=1 で 4 回、10 で 792 回、100 で 79,509 回。k² に比例する破線とほぼ平行" caption="2 列目の単位だけを k 倍にした時の、最急降下法の軌跡と収束までの回数" align="center" >}}

中央の図の縦軸は、2 列目の重みを `k` 倍して元の単位に戻した値なので、等高線は左と同じ形です。変わったのは学習率で、2 列目の大きな曲率に合わせて約 100 分の 1 に下げたため、1 列目の向きにはほとんど進みません。回数は `k²` にほぼ比例し、`k = 100` では 8 万回近くになりました。

[標準化](../../ml/standardization/)は、全ての列の標準偏差を 1 に揃えるので、列の単位から来るこの差を消せます。ただし、揃うのは列ごとのばらつきで、1 行の値の大きさまでは揃いません。次の節で見るとおり、SGD ではこれが効きます。

<br>

このように、向きによって曲率の差が大きく、1 つの学習率では全ての向きを速く進められない状態は、悪条件（ill-conditioning）と呼ばれます。過去の更新の向きを足し込む [Momentum](https://doi.org/10.1016/0041-5553%2864%2990137-5) や、パラメータごとに更新の大きさを変える [Adam](https://arxiv.org/abs/1412.6980) は、この差を和らげるための派生手法です。

---

### SGD と 1 行ごとの上限

SGD の考え方は、[Robbins と Monro の確率近似法](https://doi.org/10.1214/aoms/1177729586)（1951 年）にさかのぼります。全ての行で勾配を計算する代わりに、1 行 `x` の損失 `(予測 - y)² / 2` の勾配だけで更新します。この 1 行の損失の曲率は `||x||² + 1` です。切片は、全ての行で値が 1 の列に掛かる重みとみなせるので、その分の 1 を足しています。`||x||²` は、その行の値を全て二乗して足した値です。

1 行での更新は、その行の誤差を 1 回で `|1 - η(||x||² + 1)|` 倍にします。前の節と同じ式で、1 行ごとに上限 `η(||x||² + 1) < 2` があるということです。学習率 0.01 なら、`||x||² + 1` が 200 を超える行で更新すると、その行の誤差は符号が反転して大きくなります。以下のコードは、標準化した California Housing の学習用のデータ 16512 行で、この 1 行の曲率を数えます。

```python
X, y = fetch_california_housing(return_X_y=True)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=0)
scaler = StandardScaler().fit(X_train)
Z_train = scaler.transform(X_train)

row_curv = (Z_train ** 2).sum(axis=1) + 1  # 切片の分の 1 を足す
eta0 = 0.01
clip_curv = (np.clip(Z_train, -3, 3) ** 2).sum(axis=1) + 1
print(f"行の数 {len(row_curv)}、曲率の中央値 {np.median(row_curv):.1f}、最大 {row_curv.max():.0f}")
print(f"学習率 {eta0} で上限 2/η={2 / eta0:.0f} を超える行: {(row_curv > 2 / eta0).sum()}")
print(f"±3 で切った後の曲率の最大 {clip_curv.max():.0f}")
```

```text
行の数 16512、曲率の中央値 5.1、最大 8595
学習率 0.01 で上限 2/η=200 を超える行: 22
±3 で切った後の曲率の最大 33
```

以下は、16512 行の曲率の分布です。オレンジの点線は、後の節で扱う `SGDRegressor` の学習率の下げ方に関わる線で、ここでは赤い破線の上限 200 だけを見ます。

{{< figure src="gd_row_curvature.webp" alt="横軸は 1 行の曲率 ||x||²+1 の対数目盛、縦軸は行の数の対数目盛。標準化した後の青い棒は 5 前後に山があり、右に長い裾が 8595 まで伸びる。赤い破線の学習率 0.01 の上限 200 の右に 22 行、オレンジの点線の 1 周目の最後の上限 2267 の右に 4 行ある。±3 で切った後の緑の線は 33 で終わる" caption="標準化した California Housing の、1 行ごとの曲率の分布" align="center" >}}

中央値は 5.1 で、ほとんどの行は上限の 200 よりずっと小さい所にあります。最大の 8595 の行は、世帯あたりの平均人数 `AveOccup` が 599.7 で、標準化すると 92.6 になります。標準化は列の平均を引いて標準偏差で割るだけなので、こうした行は大きいまま残ります。

<br>

以下のコードは、学習率を 0.01 で固定した 1 行ずつの SGD を NumPy で書き、更新のたびに重みの大きさ `||w||` を記録します。

```python
def sgd_trace(Z, eta, epochs=2, seed=0):
    A = np.column_stack([Z, np.ones(len(Z))])  # 最後の列は切片
    curv = (A ** 2).sum(axis=1)
    rng = np.random.default_rng(seed)
    w = np.zeros(A.shape[1])
    norms, hits, mse = [], [], []
    for _ in range(epochs):
        for i in rng.permutation(len(A)):  # 1 周ごとに行の順番を混ぜる
            if eta * curv[i] > 2:
                hits.append(len(norms))  # 上限を超える行で更新した回
            w = w - eta * (A[i] @ w - y_train[i]) * A[i]  # 損失 (予測 - y)² / 2 の勾配
            norms.append(np.linalg.norm(w))
        mse.append(np.mean((A @ w - y_train) ** 2))
    return np.array(norms), hits, mse


for label, Z in [("標準化した後", Z_train), ("標準化して ±3 で切った後", np.clip(Z_train, -3, 3))]:
    norms, hits, mse = sgd_trace(Z, 0.01)
    print(f"{label}: 1 周ごとの学習データの平均二乗誤差 {[f'{m:.3g}' for m in mse]}、"
          f"上限を超える行での更新 {len(hits)} 回")
    if hits:
        t = hits[0]
        print(f"  最初は {t + 1} 回目の更新で、重みの大きさが {norms[t - 1]:.2f} から {norms[t]:.2f} に")
```

```text
標準化した後: 1 周ごとの学習データの平均二乗誤差 ['1.84', '1.19e+06']、上限を超える行での更新 44 回
  最初は 350 回目の更新で、重みの大きさが 2.27 から 10.14 に
標準化して ±3 で切った後: 1 周ごとの学習データの平均二乗誤差 ['0.472', '0.46']、上限を超える行での更新 0 回
```

以下は、2 周分の重みの大きさです。

{{< figure src="gd_trace.webp" alt="横軸は更新の回数で 0〜約 33000、16512 回目に 2 周目の破線。縦軸は重みの大きさ ||w|| の対数目盛。標準化した後の赤い線は、曲率が上限 200 を超える行で更新した回を示す縦の印の所で 10 や 20 に跳ね、他の行で少しずつ 3 前後へ戻ることを繰り返す。2 周目の 29500 回目付近で 1000 を超えて跳ね、そのまま残る。±3 で切った後の緑の線は 3 前後で落ち着き、縦の印は無い" caption="学習率 0.01 で固定した 1 行ずつの SGD の、更新ごとの重みの大きさ" align="center" >}}

赤い線は、縦の印の所でだけ急に大きくなっています。他の 16000 行余りの更新で重みは少しずつ戻りますが、戻り切る前に次の大きな行に当たると、さらに大きくなります。2 周目の最後には学習データの平均二乗誤差が 119 万になりました。±3 で切った緑の線では、曲率の最大が 33 なので上限を超える行が無く、1 周目で 0.472 まで下がります。

---

### バッチの大きさ

ミニバッチ SGD は、1 行ではなく `B` 行の勾配の平均で更新します。1 回の更新で全ての行を使う場合をバッチ GD と呼び、1 行の場合が狭い意味の SGD です。勾配を平均すると、極端な 1 行が更新に与える影響は `B` 分の 1 になります。以下のコードは、学習率を 0.01 で固定し、`B` だけを変えて学習データを 20 周します。

```python
def minibatch(Z, batch, eta=0.01, epochs=20, seed=0):
    A = np.column_stack([Z, np.ones(len(Z))])
    rng = np.random.default_rng(seed)
    w = np.zeros(A.shape[1])
    mse = []
    for _ in range(epochs):
        idx = rng.permutation(len(A))
        for s in range(0, len(A), batch):
            b = idx[s:s + batch]
            w = w - eta * A[b].T @ (A[b] @ w - y_train[b]) / len(b)  # B 行の勾配の平均
        mse.append(np.mean((A @ w - y_train) ** 2))
        if mse[-1] > 1e6:  # 発散したら打ち切る
            break
    return mse


ols_mse = np.mean((LinearRegression().fit(Z_train, y_train).predict(Z_train) - y_train) ** 2)
print(f"LinearRegression の学習データの平均二乗誤差 {ols_mse:.3f}")
A_full = np.column_stack([Z_train, np.ones(len(Z_train))])
print(f"全ての行で計算した曲率の最大 {np.linalg.eigvalsh(A_full.T @ A_full / len(A_full)).max():.2f}")
batch_mse = {}
for B in [1, 8, 32, 256, len(Z_train)]:
    batch_mse[B] = minibatch(Z_train, B)
    updates = int(np.ceil(len(Z_train) / B))
    last = batch_mse[B][-1]
    state = f"{len(batch_mse[B])} 周目に {last:.3g} になり打ち切り" if last > 1e6 else f"20 周後 {last:.3f}"
    print(f"バッチ {B:>5}: 1 周の更新 {updates:>5} 回、{state}")

full_09 = minibatch(Z_train, len(Z_train), eta=0.9)
print(f"バッチ GD を学習率 0.9 で: 5 周後 {full_09[4]:.3f}、20 周後 {full_09[-1]:.3f}")
```

```text
LinearRegression の学習データの平均二乗誤差 0.523
全ての行で計算した曲率の最大 2.02
バッチ     1: 1 周の更新 16512 回、2 周目に 1.19e+06 になり打ち切り
バッチ     8: 1 周の更新  2064 回、4 周目に 1.31e+07 になり打ち切り
バッチ    32: 1 周の更新   516 回、20 周後 0.565
バッチ   256: 1 周の更新    65 回、20 周後 0.542
バッチ 16512: 1 周の更新     1 回、20 周後 3.975
バッチ GD を学習率 0.9 で: 5 周後 0.588、20 周後 0.532
```

以下は、1 周ごとの学習データの平均二乗誤差です。

{{< figure src="gd_batch.webp" alt="横軸は学習データを何周したかで 1〜20、縦軸は学習データの平均二乗誤差の対数目盛。1 行の赤は 2 周目に 10 の 6 乗へ、8 行のオレンジは 4 周目に 10 の 7 乗へ跳ね上がる。32 行の緑と 256 行の青は数周で 0.5 台に下がり、最小二乗の解の破線 0.523 の近くに並ぶ。全行の紫は 5.5 から 20 周で 4.0 までしか下がらない" caption="学習率 0.01 で固定し、1 回の更新に使う行の数だけを変えた時の学習データの平均二乗誤差" align="center" >}}

学習率は同じでも、1 行と 8 行では発散し、32 行と 256 行では最小二乗の解の 0.523 の近くまで下がりました。全ての行を使うバッチ GD は発散しませんが、1 周で 1 回しか更新しないので、20 周しても 3.975 です。全ての行で計算した曲率の最大は 2.02 なので、バッチ GD なら学習率を 0.9 まで上げられ、出力の最後の行のとおり 5 周で 0.588 まで下がります。

バッチを大きくすると、極端な行に強くなる代わりに、1 周あたりの更新の回数が減ります。そのため、バッチの大きさを変えた時は、学習率も一緒に選び直す必要があります。ニューラルネットの学習率とバッチの大きさは、[ハイパーパラメータ](../../ml/hyperparameter/)として一緒に調整される値です。ニューラルネットの勾配を各層へ配る計算は、[誤差逆伝播法](../../ml/backpropagation/)で扱っています。

---

### SGDRegressor の既定

冒頭の図の `SGDRegressor` は、1 行ずつ更新する SGD です。以下は、scikit-learn 1.9.1 の既定のうち、本記事の結果に関わるものです。

| 引数 | 既定 | 意味 |
|---|---|---|
| `learning_rate` | `'invscaling'` | 学習率を `eta0 / t^power_t` で下げる |
| `eta0`、`power_t` | 0.01、0.25 | 学習率の初期値と、下げる速さ |
| `max_iter` | 1000 | 学習データを何周するかの上限 |
| `tol`、`n_iter_no_change` | 0.001、5 | 最良からの改善が 0.001 未満の周が 5 回続けば止める |
| `penalty`、`alpha` | `'l2'`、0.0001 | 重みを小さく保つ [L2 正則化](../../ml/regularization/)の強さ |
| `random_state` | `None` | 行の順番を混ぜる乱数の種 |

`t` は、学習を始めてから更新した行の数です。学習率は 1 行目の 0.01 から始まり、1 周目の最後の 16512 行目で 0.000882 まで下がります。以下のコードは、前の節の `row_curv` を使って、この学習率の下げ方と上限を比べ、標準化しない時の値も数えます。その後、冒頭の図の 5 通りの前処理で 10 回ずつ学習し、R² と、止まった時の周回 `n_iter_` と、警告の数を数えます。

```python
eta_end = 0.01 / len(Z_train) ** 0.25  # invscaling で 1 周目の最後の行の学習率
print(f"1 周目の最後の学習率 {eta_end:.6f} で上限 {2 / eta_end:.0f} を超える行: {(row_curv > 2 / eta_end).sum()}")
# eta0=0.001 の invscaling で、最大の曲率の行が上限 2/η を超えるのは何回目の更新までか
print(f"eta0=0.001 で曲率 {row_curv.max():.0f} の行が上限を超えるのは t <= {(0.001 * row_curv.max() / 2) ** 4:.0f}")
sd = X_train.std(axis=0)
names_cols = fetch_california_housing().feature_names
print(f"列ごとの標準偏差: 最大 {sd.max():.2f}（{names_cols[sd.argmax()]}）、最小 {sd.min():.2f}（{names_cols[sd.argmin()]}）")
raw_curv = (X_train ** 2).sum(axis=1) + 1
print(f"標準化しない時の曲率: 中央値 {np.median(raw_curv):.3g}、100 万を超える行 {(raw_curv > 1e6).mean():.1%}")

configs = {
    "そのまま": lambda s: SGDRegressor(random_state=s),
    "標準化": lambda s: make_pipeline(StandardScaler(), SGDRegressor(random_state=s)),
    "RobustScaler": lambda s: make_pipeline(RobustScaler(), SGDRegressor(random_state=s)),
    "標準化 + eta0=0.001": lambda s: make_pipeline(StandardScaler(), SGDRegressor(eta0=0.001, random_state=s)),
    "標準化 + ±3 で切る": lambda s: make_pipeline(StandardScaler(), FunctionTransformer(lambda Z: np.clip(Z, -3, 3)),
                                              SGDRegressor(random_state=s)),
}
r2 = {}
for name, make in configs.items():
    scores, n_iters, n_warn = [], [], 0
    for seed in range(10):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            model = make(seed).fit(X_train, y_train)
        n_warn += len(caught)
        scores.append(model.score(X_test, y_test))
        n_iters.append(model[-1].n_iter_ if hasattr(model, "steps") else model.n_iter_)
    r2[name] = scores
    print(f"{name}: R² {min(scores):.4g}〜{max(scores):.4g}（中央値 {np.median(scores):.4g}）、"
          f"周回 {min(n_iters)}〜{max(n_iters)}、警告 {n_warn} 件")
ols_r2 = LinearRegression().fit(X_train, y_train).score(X_test, y_test)
print(f"LinearRegression: R² {ols_r2:.4f}")
clip_ols = make_pipeline(StandardScaler(), FunctionTransformer(lambda Z: np.clip(Z, -3, 3)), LinearRegression())
print(f"標準化 + ±3 で切る + LinearRegression: R² {clip_ols.fit(X_train, y_train).score(X_test, y_test):.4f}")
```

```text
1 周目の最後の学習率 0.000882 で上限 2267 を超える行: 4
eta0=0.001 で曲率 8595 の行が上限を超えるのは t <= 341
列ごとの標準偏差: 最大 1143.03（Population）、最小 0.49（AveBedrms）
標準化しない時の曲率: 中央値 1.38e+06、100 万を超える行 60.8%
そのまま: R² -6.024e+30〜-1.457e+27（中央値 -1.521e+29）、周回 24〜56、警告 0 件
標準化: R² -2.938e+04〜-368（中央値 -4146）、周回 6〜10、警告 0 件
RobustScaler: R² -2.522e+24〜-4.839e+19（中央値 -6.771e+21）、周回 6〜6、警告 0 件
標準化 + eta0=0.001: R² 0.5822〜0.5849（中央値 0.5834）、周回 18〜19、警告 0 件
標準化 + ±3 で切る: R² 0.6414〜0.6429（中央値 0.6421）、周回 9〜9、警告 0 件
LinearRegression: R² 0.5943
標準化 + ±3 で切る + LinearRegression: R² 0.6434
```

出力の 1 行目のとおり、1 周目の最後まで学習率を下げても、上限の 2267 を超える行が 4 つ残ります。壊れた学習も、6〜56 周で止まっています。止める条件は、学習データの損失の 1 周の平均が、それまでの最良より 0.001 以上良くならない周が 5 回続くことで、損失が大きいまま下がらなくなった時も満たされます。scikit-learn が収束しなかったという警告（ConvergenceWarning）を出すのは `max_iter` の 1000 周に届いた時なので、警告は出ません。

<br>

そのままの列では、人口 `Population` の標準偏差が 1143 あり、出力の 4 行目のとおり 1 行の曲率の中央値が 138 万です。[`RobustScaler`](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.RobustScaler.html) も、中央値を引いて四分位範囲で割るだけなので、極端な行の大きさは残り、R² は -10²¹ ほどでした。

直った 2 つは、どちらも前の節の上限を下回るようにしています。±3 で切ると曲率の最大は 33 になり、学習率 0.01 の上限 200 を下回ります。以下は、`eta0` が 0.01 と 0.001 の時に `invscaling` で下がっていく学習率と、最大の曲率 8595 の行の上限を並べた図です。

{{< figure src="gd_invscaling.webp" alt="横軸は更新した行の数 t、縦軸は学習率 eta0 / t^0.25 で、どちらも対数目盛。赤の eta0=0.01 は 0.01 から下がるが、10 周目の終わりでも 0.0005 ほどで、曲率 8595 の行の上限 2/8595 の破線より上にある。緑の eta0=0.001 は 341 回目で破線を下回る。灰色の縦線は 1 周の終わりごと" caption="invscaling の学習率と、曲率が最大の行の上限" align="center" >}}

`eta0=0.001` なら、出力の 2 行目と図のとおり、最大の曲率の行でも上限を超えるのは最初の 341 回の更新の間だけで、その間にこの行に当たらなければ重みは急に大きくなりません。既定の 0.01 では、10 周しても学習率が上限より上にあり、その前に 6〜10 周で止まります。

±3 で切った方の R² が `LinearRegression` の 0.594 より高いのは、SGD のおかげではありません。出力の最後の行のとおり、同じく ±3 で切ってから `LinearRegression` で解くと 0.643 で、値を切ったこと自体がこのテストデータに合っていました。ただ、値を切るのは、その列の大きな値を区別しないという判断でもあります。極端な行が誤りなのか本物なのかは、[異常検知](../../ml/anomaly-detection/)のように別に確認する必要があります。

`random_state` を既定の `None` のままにすると、行の順番が学習のたびに変わるので、R² も学習のたびに変わります。冒頭の図では、種を 0〜9 に固定して 10 回学習しました。

---

### 学習が壊れた時に確かめること

`SGDRegressor` やニューラルネットの学習で、損失が下がらない、R² が大きな負の値になる、損失が数値でない NaN になる、という時は、学習率と曲率の積が 2 を超えていないかを順に確認します。以下は、確認する値と、本記事の California Housing での値です。

| 確認する値 | California Housing |
|---|---|
| 列ごとの標準偏差の最大と最小 | 1143 と 0.49 |
| 標準化した後の 1 行の曲率の最大 | 8595 |
| 学習率の上限 `2 / eta0` | 200 |
| 上限を超える行の数 | 16512 行のうち 22 行 |
| 止まった周回 `n_iter_` | 6〜10 |

最初に、列ごとの標準偏差を並べます。1 列だけ桁が違えば、列の単位の節の図のように収束までの回数が桁で増えるか、発散します。標準化はこれを消しますが、SGD ではそれだけで足りません。標準化した後の各行の `||x||² + 1` を計算し、その最大と `2 / eta0` を比べます。

超える行があれば、その行が誤りかどうかを見てから、値を切るか、[対数](../log-exp-logodds/)を取って大きな値を縮めるか、学習率を下げるかを選びます。ミニバッチで学習する場合は、バッチの大きさを変えたら学習率も選び直します。

学習した後は `n_iter_` と学習データの損失を見ます。警告が無くても、少ない周回で止まっていれば、損失が大きいまま下がらなくなった可能性があります。

<br>

California Housing のような 1 万行台のデータなら、`LinearRegression` は反復せずに式で最小二乗の解を求めます。勾配を使う反復が要るのは、行が多すぎてメモリに載らない時や、データが少しずつ届き、届いた分だけで学習を進める時です。

`SGDRegressor` の R² が冒頭の図の赤い点のようになったら、まず標準化を確認し、次に `||x||²` の最大を見てください。どちらも数行のコードで済み、緑の点の位置に戻せるかがそこで分かります。
