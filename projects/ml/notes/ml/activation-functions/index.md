---
title: "活性化関数 - 学習率が大きいと、ReLU を使うユニットの多くがどの入力にも 0 しか返さなくなる"
date: 2026-05-26
draft: false
series: ["機械学習ノート", "Machine Learning"]
tags: ["machine-learning", "deep-learning"]
weight: 35
topics: ["Machine Learning（評価・概念・アルゴリズム）"]
---

ニューラルネットワークの 1 つのユニットは、入力に重みを掛けて足し、バイアスを足した値 `z = w · x + b` を求め、その値を活性化関数（activation function）に通して次の層へ渡します。よく使われる ReLU（Rectified Linear Unit）は `max(0, z)` で、`z` が負なら 0、正ならそのまま返します。

入力を受け取る層と答えを出す層の間に並ぶユニットの層は、隠れ層と呼びます。[scikit-learn](https://scikit-learn.org/stable/) の [`MLPClassifier`](https://scikit-learn.org/stable/modules/generated/sklearn.neural_network.MLPClassifier.html) も、何も指定しなければ隠れ層に ReLU を使います。

scikit-learn に同梱の [digits](https://scikit-learn.org/stable/modules/generated/sklearn.datasets.load_digits.html) は、0〜9 の手書き数字 1797 枚を 8×8 画素の濃さで表したデータです。64 ユニットの隠れ層を 2 つ持つ `MLPClassifier` で digits を学習し、1 回の更新で重みを動かす大きさを決める[学習率](../../math/gradient-descent-sgd/)の初期値 `learning_rate_init` だけを 0.001 から 0.3 まで変えて、乱数のシードを変えながら 5 回ずつ試しました。

比べる相手は、活性化関数を tanh に変えた同じネットワークです。下の段は、2 層目のユニットのうち、学習に使った全ての行で 0 を返したものを数えた結果です。

{{< figure src="af_cover.webp" alt="2 段のグラフで、横軸は learning_rate_init の 0.001、0.003、0.01、0.03、0.1、0.3。上の段はテストの正解率で、青い tanh は 0.3 まで 0.9 前後を保つ。赤い ReLU は 0.03 まで 0.97 前後だが、0.1 で 0.93、0.3 で中央値 0.22 まで落ちる。下の段は全ての行で 0 を返す 2 層目のユニットの数で、中央値は 0、1、3、7、38、59。上限の 64 個に点線を引いている" caption="学習率を上げた時の正解率（上）と、0 しか返さない 2 層目のユニット（下）" align="center" >}}

学習率が 0.1 になると、2 層目の 64 個のうち[中央値](../../math/median/)で 38 個が、学習に使ったどの画像を入れても 0 しか返さなくなりました。0.3 では 59 個で、テストの正解率は 0.11〜0.30（中央値 0.22）まで落ちます。tanh は同じ 0.3 で 0.86〜0.91 でした。ReLU の学習では、警告は 1 件も出ません。学習データを 1 周する単位をエポックと呼び、0.3 の ReLU は 5 回とも 27〜50 エポックで「収束した」として止まりました。収束の判定は後の節で説明します。

学習が遅いので学習率を上げた、という時に正解率が落ちても、手元に残るのはエラーの無い学習結果と低い点数だけです。学習率を上げた ReLU のユニットが 0 しか返さなくなったかどうかは、ユニットの出力を数えるまで見えません。

<br>

本記事では、scikit-learn の `MLPClassifier` や Python の深層学習ライブラリ [PyTorch](https://pytorch.org/) でニューラルネットワークを組み始めた人に向けて、次の疑問に答えます。

- 活性化関数を外すと、層を重ねた MLP は何になるのか。
- sigmoid・tanh・ReLU・GELU は、形と傾きがどう違うのか。
- sigmoid の MLP が、学習せずに止まるのはなぜか。
- ReLU のユニットが 0 しか返さなくなるのは、いつか。
- 学習に使っていない範囲の入力に、MLP は何を返すのか。
- 出力層には、どの関数を置くのか。

実験は scikit-learn 1.9.1 と [NumPy](https://numpy.org/) 2.5.4 で行い、図は [Matplotlib](https://matplotlib.org/) で描きました。完全なコードは [GitHub](https://github.com/nao1215/debimate/blob/main/projects/ml/scripts/notes/activation-functions_gen.py) にあります。

---

### 活性化関数を外した MLP

MLP（Multi-Layer Perceptron、多層パーセプトロン）は、入力層と出力層の間に隠れ層を重ねたニューラルネットワークです。`MLPClassifier` の `activation` には `"identity"`・`"logistic"`・`"tanh"`・`"relu"` の 4 つを指定でき、`"identity"` は `z` をそのまま返す、つまり活性化関数を外した状態です。

[`make_circles`](https://scikit-learn.org/stable/modules/generated/sklearn.datasets.make_circles.html) で、内側の円と外側の輪に 200 点ずつ並ぶ 2 クラスのデータを作り、16 ユニットの隠れ層を 3 つ重ねた MLP で 4 つの関数を比べました。

```python
Xc, yc = make_circles(n_samples=400, noise=0.1, factor=0.4, random_state=0)
models = {}
for act in ["identity", "logistic", "tanh", "relu"]:
    models[act] = MLPClassifier(hidden_layer_sizes=(16, 16, 16), activation=act,
                                max_iter=3000, random_state=0).fit(Xc, yc)
    print(f"{act:<8} 訓練データの正解率 {models[act].score(Xc, yc):.3f}  エポック {models[act].n_iter_}")
```

```text
identity 訓練データの正解率 0.615  エポック 30
logistic 訓練データの正解率 0.500  エポック 20
tanh     訓練データの正解率 1.000  エポック 342
relu     訓練データの正解率 1.000  エポック 241
```

{{< figure src="af_circles.webp" alt="4 枚の散布図で、MLP が分けた領域に、赤い内側の円と青い外側の輪の点を重ねている。identity は右上がりの直線 1 本で分けて正解率 0.61。logistic は全面が赤で正解率 0.50、20 エポックで停止。tanh は内側の円を囲む滑らかな曲線で正解率 1.00。relu は内側の円を囲む角張った多角形で正解率 1.00" caption="活性化関数ごとに、隠れ層 3 つの MLP が分けた領域" align="center" >}}

`identity` の境界は直線 1 本です。隠れ層が 3 つあると、入力から 1 層目、1 層目から 2 層目、2 層目から 3 層目、3 層目から出力への 4 枚の重みが並びます。行列の積は先にまとめられるので、MLP 全体が 1 枚の重みと 1 つのバイアスで書ける線形のモデルになります。実際にまとめてみると、層を順に通した値との差は、丸めで生じる誤差の大きさに収まりました。

下のコードで使う `coefs_` と `intercepts_` は、scikit-learn が学習した重みとバイアスを持つ属性です。scikit-learn はバイアスを切片と呼びます。

```python
m = models["identity"]
W, b = m.coefs_[0], m.intercepts_[0]
for W_next, b_next in zip(m.coefs_[1:], m.intercepts_[1:]):
    W, b = W @ W_next, b @ W_next + b_next             # 4 枚の重みを 1 枚にまとめる
z_mlp = Xc @ W + b
z_layers = Xc
for W_i, b_i in zip(m.coefs_, m.intercepts_):
    z_layers = z_layers @ W_i + b_i                    # 層を順に通した値
print("まとめた重み", W.ravel().round(4), "切片", b.round(4))
print("層を順に通した値との差の最大", float(np.abs(z_mlp - z_layers).max()))
```

```text
まとめた重み [ 0.0011 -0.011 ] 切片 [0.0082]
層を順に通した値との差の最大 3.9898639947466563e-16
```

円の内外は直線では分けられないので、層をいくら重ねても `identity` では正解率が上がりません。線形変換を重ねると 1 つの行列にまとまる理由は、[ベクトルと行列の演算](../../math/vector-matrix-ops/)で説明しています。tanh と ReLU は円を囲む境界を作り、ReLU の境界は短い直線をつないだ多角形になりました。

ここで比べた正解率は学習に使った点に対する値で、未知のデータでも同じだけ当たるとは限りません。学習データと未知のデータで正解率が離れる現象は、[過学習](../overfitting/)のノートで扱っています。

`logistic` は sigmoid のことで、非線形なのに全面を 1 クラスと答えています。予測が正解からどれだけ外れたかを表す値を[損失](../loss-functions/)と呼び、学習はこれを減らすように重みを動かします。損失がまだ下がり始める前に、scikit-learn が「もう減らない」と判断して 20 エポックで止めたためです。

---

### sigmoid・tanh・ReLU・GELU の形と傾き

[パーセプトロン](../perceptron/)が使う step 関数は、`z` が正なら 1、それ以外は 0 を返します。傾きがほぼ全ての所で 0 なので、勾配を使う学習には使えません。そこで滑らかな関数を使います。

sigmoid は `1 / (1 + exp(-z))` で、どんな `z` も 0〜1 に収まる値に変えます。[ロジスティック回帰](../logistic-regression/)が確率を出す時に使う関数と同じです。tanh は `2 / (1 + exp(-2z)) - 1` で、sigmoid を縦に 2 倍して 1 下げ、横に半分へ縮めた形です。出力の範囲は -1〜1 で、`z = 0` で 0 を返します。

ReLU は、負の `z` に対する傾きがちょうど 0 です。`z = 0` では微分できませんが、scikit-learn はそこでの傾きを 0 として扱います。

負の `z` を ReLU のように 0 で切り捨てない関数として、[Leaky ReLU](https://pytorch.org/docs/stable/generated/torch.nn.LeakyReLU.html) と [GELU](https://arxiv.org/abs/1606.08415)（Gaussian Error Linear Unit）があります。Leaky ReLU は、負の `z` に 0.01 のような小さな係数を掛けて返します。GELU は `z` に `Φ(z)` を掛けた値を返します。`Φ(z)` は、平均 0・[標準偏差](../../math/stddev/) 1 の正規分布で値が `z` 以下になる確率で、累積分布関数と呼びます。累積分布関数は[確率分布](../../math/probability-distributions/)のノートで説明しています。

GELU は `z ≈ -0.75` で最小値の約 -0.17 を取り、ここで傾きがちょうど 0 になります。PyTorch の [`nn.GELU`](https://pytorch.org/docs/stable/generated/torch.nn.GELU.html) は既定でこの定義どおりに計算し、`approximate="tanh"` を指定すると tanh を使った近似式に切り替わります。[BERT](https://arxiv.org/abs/1810.04805) のような言語モデルの隠れ層で使われてきた関数です。

```python
z = np.linspace(-5, 5, 1001)
sig = 1 / (1 + np.exp(-z))
gelu = 0.5 * z * (1 + erf(z / np.sqrt(2)))
phi = np.exp(-z**2 / 2) / np.sqrt(2 * np.pi)
funcs = {
    "sigmoid": (sig, sig * (1 - sig), BLUE, "-"),
    "tanh": (np.tanh(z), 1 - np.tanh(z) ** 2, GREEN, "-"),
    "ReLU": (np.maximum(z, 0), (z > 0).astype(float), RED, "-"),
    "Leaky ReLU 0.1": (np.where(z > 0, z, 0.1 * z), np.where(z > 0, 1, 0.1), ORANGE, "--"),
    "GELU": (gelu, 0.5 * (1 + erf(z / np.sqrt(2))) + z * phi, INK, ":"),
}
for name, (_, g, _, _) in funcs.items():
    print(f"{name:<16} 傾きの最大 {g.max():.3f}  z=-3 の傾き {g[np.argmin(np.abs(z + 3))]:.3f}")
```

```text
sigmoid          傾きの最大 0.250  z=-3 の傾き 0.045
tanh             傾きの最大 1.000  z=-3 の傾き 0.010
ReLU             傾きの最大 1.000  z=-3 の傾き 0.000
Leaky ReLU 0.1   傾きの最大 1.000  z=-3 の傾き 0.100
GELU             傾きの最大 1.129  z=-3 の傾き -0.012
```

{{< figure src="af_shapes.webp" alt="左は 5 つの関数の出力で、sigmoid は 0〜1、tanh は -1〜1 の S 字。ReLU は負で 0、正で直線。Leaky ReLU 0.1 は負の入力でも緩い直線。GELU は負の入力で少し沈んでから ReLU に近づく。右は傾きで、sigmoid は z=0 の 0.25 が最大の山、tanh は z=0 で 1 の山、ReLU は負で 0・正で 1 の段差、Leaky ReLU は負で 0.1、GELU は z=-1.5 付近でわずかに負になり、z=1.5 付近で 1.13 の山を作る" caption="活性化関数の出力（左）と傾き（右）" align="center" >}}

図の Leaky ReLU は、見やすさのため負の入力に対する傾きを 0.1 にしました。PyTorch の `nn.LeakyReLU` では既定が 0.01 です。違いを表にまとめます。

| 関数 | 出力の範囲 | 傾きの最大 | 大きい負の z での傾き | scikit-learn | PyTorch |
|---|---|---|---|---|---|
| sigmoid | 0〜1 | 0.25 | 0 に近づく | `"logistic"` | `nn.Sigmoid` |
| tanh | -1〜1 | 1 | 0 に近づく | `"tanh"` | `nn.Tanh` |
| ReLU | 0 以上 | 1 | ちょうど 0 | `"relu"`（既定） | `nn.ReLU` |
| Leaky ReLU | 全ての実数 | 1 | 係数のまま | 無し | `nn.LeakyReLU` |
| GELU | 約 -0.17 以上 | 約 1.13 | 0 に近づく | 無し | `nn.GELU` |

scikit-learn で選べるのは表の上 3 行と `identity` だけで、Leaky ReLU と GELU を使うなら PyTorch などのライブラリになります。

<br>

#### 層を通るたびに掛かる傾き

学習では、損失から入力側へ向かって、各層で活性化関数の傾きを次々に掛けて[勾配](../../math/partial-derivative-gradient/)を求めます。sigmoid の傾きは最大でも 0.25 なので、勾配に掛かる活性化関数の傾きだけを見ると、層を通るたびに 4 分の 1 以下になります。入力側の層ほど勾配が小さくなるこの現象は、勾配消失（vanishing gradient）と呼ばれます。10 層の MLP で、入力側の層に届く勾配が sigmoid だけ極端に小さくなる様子は、[誤差逆伝播法](../backpropagation/)のノートで層ごとに測っています。

ReLU は正の入力で傾きが 1 なので、活性化関数の傾きでは縮みません。重みを掛ける分は、どの関数でも別に掛かります。

そのため勾配の大きさは、重みの初期値や、層ごとに出力の大きさを揃える正規化、[ResNet](https://arxiv.org/abs/1512.03385) のように層を飛ばして入力を足す残差接続でも変わります。掛かる値が 1 より大きい側に偏ると、逆に勾配が層ごとに膨らむ勾配爆発（exploding gradient）も起きます。

深いネットワークの隠れ層に ReLU が広く使われるようになったのは、[Glorot 氏らの 2011 年の論文](https://proceedings.mlr.press/v15/glorot11a.html)などで学習しやすさが示されてからです。その一方で、負の入力で傾きが 0 になるので、大きな学習率で `z` が負に寄ったユニットは戻りにくくなります。冒頭の実験で起きたことも、この仕組みで説明できます。

---

### sigmoid の MLP が止まる理由

円のデータで `logistic` が 20 エポックで止まったのは、scikit-learn の止め方と関係しています。`MLPClassifier` は既定で、訓練データの損失が `tol`（既定 1e-4）以上減らないエポックが `n_iter_no_change`（既定 10）回続くと、収束したとみなして学習を止めます。止まり方が「収束」なので、上限の `max_iter` まで回った時に出る `ConvergenceWarning` も出ません。

そこで、`n_iter_no_change` を 3000 に増やして学習を続けさせた sigmoid と、既定のまま止まった sigmoid・tanh・ReLU の損失を並べました。

```python
curves = {}
for label, act, patience in [("logistic、既定", "logistic", 10),
                             ("logistic、n_iter_no_change=3000", "logistic", 3000),
                             ("tanh、既定", "tanh", 10), ("relu、既定", "relu", 10)]:
    mdl = MLPClassifier(hidden_layer_sizes=(16, 16, 16), activation=act, max_iter=3000,
                        n_iter_no_change=patience, random_state=0).fit(Xc, yc)
    lc = np.array(mdl.loss_curve_)
    curves[label] = lc
    below = int(np.argmax(lc < 0.6)) + 1 if (lc < 0.6).any() else None
    print(f"停止 {mdl.n_iter_:>4} エポック  正解率 {mdl.score(Xc, yc):.2f}  最初の損失 {lc[0]:.4f}  "
          f"最後の損失 {lc[-1]:.4f}  損失が 0.6 を切った {str(below):>4}  {label}")
```

```text
停止   20 エポック  正解率 0.50  最初の損失 0.6965  最後の損失 0.6932  損失が 0.6 を切った None  logistic、既定
停止 3000 エポック  正解率 1.00  最初の損失 0.6965  最後の損失 0.0006  損失が 0.6 を切った  685  logistic、n_iter_no_change=3000
停止  342 エポック  正解率 1.00  最初の損失 0.6933  最後の損失 0.0118  損失が 0.6 を切った   40  tanh、既定
停止  241 エポック  正解率 1.00  最初の損失 0.6928  最後の損失 0.0071  損失が 0.6 を切った   48  relu、既定
```

{{< figure src="af_sigmoid_stall.webp" alt="横軸が対数のエポック、縦軸が訓練データの損失の折れ線グラフ。どの線も log 2 = 0.693 の点線の付近から始まる。太い青の logistic 既定は 20 エポックで点線の上のまま止まる。青の破線の logistic n_iter_no_change=3000 は 600 エポック付近まで点線に張り付き、700〜800 エポックで急に下がって 0 近くになる。緑の tanh と赤の relu は 40〜50 エポックで 0.6 を切り、relu は 241、tanh は 342 エポックで 0 近くまで下がって止まる" caption="円のデータで学習した時の損失（logistic は既定の止め方と、学習を続けさせた場合）" align="center" >}}

`MLPClassifier` の損失は、交差エントロピーに小さな罰則を足した値です。交差エントロピーは、正解のクラスに付けた確率の対数にマイナスを付け、全ての点で平均した値です。2 値分類でどの点にも確率 0.5 と答えると、損失は `log 2 = 0.693` になります。sigmoid の MLP は 600 エポックほど、この値から動きません。

この平らな区間が長いのは、前の節で見た勾配消失と関係していると考えられます。sigmoid の傾きは最大 0.25 なので、隠れ層 3 つを通る間に掛かる傾きの積は、0.25 の 3 乗、つまり 64 分の 1 以下です。学習を続けさせると、685 エポック目に 0.6 を切り、最後は正解率 1.00 に届きました。

既定の止め方では、この平らな区間を「もう減らない」と見て 20 エポックで止まります。tanh と ReLU は 40〜50 エポックで損失が下がり始めるので、同じ止め方でも最後まで学習が進みました。

<br>

#### 傾きのほかに重なる原因

scikit-learn は重みの初期値を一様分布から選び、その幅を `logistic` の時だけ約 1/√3 に狭めます。同じ `random_state=0` でも、sigmoid の MLP は小さい重みから始まっていて、平らな区間の長さにはこの違いも重なっています。円のデータで比べた結果はシード 1 つだけなので、エポック数の差を関数の優劣として一般化しないでください。

sigmoid の出力が 0 を中心にせず、0.5 を中心に正の値だけを返すことも、学習が遅くなる原因として [LeCun 氏らの Efficient BackProp](http://yann.lecun.com/exdb/publis/pdf/lecun-98b.pdf) で挙げられています。同じ論文は、次の層に渡す値が平均で 0 に近くなるという理由で、0 を中心に対称な tanh のような関数を sigmoid より勧めています。

---

### 0 しか返さない ReLU

冒頭の実験に戻ります。ReLU のユニットに入る `z` が、学習に使う全ての行で負になると、ユニットはどの行にも 0 を返し、傾きも 0 になります。傾きが 0 なので、そのユニットに入る側の重みには勾配が届きません。1 つ手前の層で重みが変わり、`z` が正になる行が出てこない限り、このユニットは 0 を返し続けます。この状態を dying ReLU と呼び、[Lu 氏らの 2019 年の論文](https://arxiv.org/abs/1903.06733)のように、深いネットワークでの起き方を調べた研究もあります。

scikit-learn には死んだユニットを数える機能が無いので、学習した `coefs_` と `intercepts_` から隠れ層の出力を自分で計算して数えました。

```python
X, y = load_digits(return_X_y=True)
X = StandardScaler().fit_transform(X)
X_train, X_test, y_train, y_test = train_test_split(X, y, random_state=0)


def dead_units(model, X):
    """隠れ層ごとに、全ての行で出力が 0 のユニットの数を返す。"""
    a, counts = X, []
    for W, b in zip(model.coefs_[:-1], model.intercepts_[:-1]):
        a = np.maximum(a @ W + b, 0)                   # ReLU の隠れ層を自分で計算する
        counts.append(int((a.max(axis=0) == 0).sum()))
    return counts


lrs = [0.001, 0.003, 0.01, 0.03, 0.1, 0.3]
res = {"relu": [], "tanh": [], "dead": [], "epochs": [], "warns": []}
for lr in lrs:
    acc_r, acc_t, dead, epochs, warns = [], [], [], [], []
    for seed in range(5):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            relu = MLPClassifier(hidden_layer_sizes=(64, 64), learning_rate_init=lr,
                                 random_state=seed).fit(X_train, y_train)
        tanh = MLPClassifier(hidden_layer_sizes=(64, 64), activation="tanh",
                             learning_rate_init=lr, random_state=seed).fit(X_train, y_train)
        acc_r.append(relu.score(X_test, y_test))
        acc_t.append(tanh.score(X_test, y_test))
        dead.append(dead_units(relu, X_train))
        epochs.append(relu.n_iter_)
        warns.append(len(caught))
        if seed == 0:
            print(f"lr={lr:<5} ReLU 0 しか返さないユニット（1 層目, 2 層目）{dead[-1]}  "
                  f"正解率 ReLU {acc_r[-1]:.3f}  tanh {acc_t[-1]:.3f}  "
                  f"エポック {relu.n_iter_}  警告 {len(caught)} 件")
    res["relu"].append(acc_r)
    res["tanh"].append(acc_t)
    res["dead"].append([d[1] for d in dead])
    res["epochs"].append(epochs)
    res["warns"].append(warns)
for lr, a_r, a_t, d, ep, wn in zip(lrs, res["relu"], res["tanh"], res["dead"], res["epochs"], res["warns"]):
    print(f"lr={lr:<5} 5 回の 2 層目 {d}  ReLU のエポック {ep}  警告 {sum(wn)} 件")
    print(f"{'':<9}正解率 ReLU {np.round(a_r, 2)}  tanh {np.round(a_t, 2)}")
```

```text
lr=0.001 ReLU 0 しか返さないユニット（1 層目, 2 層目）[0, 0]  正解率 ReLU 0.978  tanh 0.971  エポック 96  警告 0 件
lr=0.003 ReLU 0 しか返さないユニット（1 層目, 2 層目）[0, 1]  正解率 ReLU 0.980  tanh 0.971  エポック 50  警告 0 件
lr=0.01  ReLU 0 しか返さないユニット（1 層目, 2 層目）[0, 3]  正解率 ReLU 0.980  tanh 0.973  エポック 26  警告 0 件
lr=0.03  ReLU 0 しか返さないユニット（1 層目, 2 層目）[0, 5]  正解率 ReLU 0.969  tanh 0.976  エポック 18  警告 0 件
lr=0.1   ReLU 0 しか返さないユニット（1 層目, 2 層目）[0, 38]  正解率 ReLU 0.929  tanh 0.962  エポック 18  警告 0 件
lr=0.3   ReLU 0 しか返さないユニット（1 層目, 2 層目）[0, 59]  正解率 ReLU 0.300  tanh 0.864  エポック 27  警告 0 件
lr=0.001 5 回の 2 層目 [0, 0, 1, 0, 1]  ReLU のエポック [96, 101, 98, 99, 101]  警告 0 件
         正解率 ReLU [0.98 0.98 0.97 0.98 0.97]  tanh [0.97 0.98 0.97 0.97 0.98]
lr=0.003 5 回の 2 層目 [1, 1, 2, 1, 1]  ReLU のエポック [50, 52, 51, 52, 52]  警告 0 件
         正解率 ReLU [0.98 0.98 0.97 0.97 0.97]  tanh [0.97 0.98 0.97 0.97 0.98]
lr=0.01  5 回の 2 層目 [3, 2, 3, 5, 3]  ReLU のエポック [26, 25, 25, 27, 27]  警告 0 件
         正解率 ReLU [0.98 0.97 0.97 0.98 0.97]  tanh [0.97 0.98 0.97 0.97 0.98]
lr=0.03  5 回の 2 層目 [5, 7, 8, 8, 5]  ReLU のエポック [18, 30, 39, 23, 24]  警告 0 件
         正解率 ReLU [0.97 0.96 0.96 0.98 0.97]  tanh [0.98 0.97 0.97 0.97 0.96]
lr=0.1   5 回の 2 層目 [38, 43, 42, 33, 36]  ReLU のエポック [18, 31, 30, 20, 24]  警告 0 件
         正解率 ReLU [0.93 0.88 0.9  0.93 0.93]  tanh [0.96 0.96 0.97 0.96 0.96]
lr=0.3   5 回の 2 層目 [59, 60, 58, 59, 60]  ReLU のエポック [27, 38, 50, 32, 28]  警告 0 件
         正解率 ReLU [0.3  0.17 0.22 0.23 0.11]  tanh [0.86 0.89 0.9  0.91 0.9 ]
```

最初の 6 行はシード 0 の 1 回分、残りはシード 0〜4 の 5 回分です。冒頭の図に描いた中央値は、5 回分の値から求めました。

学習率 0.3 で 59 個が死んだ時も、1 層目のユニットは 1 個も死んでいません。1 層目の入力は[標準化](../standardization/)した画素の値で、正と負の両方を取ります。1 層目で 0 より大きい値を返す行が一番少ないユニットでも、その割合は 27% でした。

2 層目に入る値は、1 層目で ReLU を通した出力なので、全て 0 以上です。重みが負に寄れば、どの行でも `z` が負になります。死んだユニットに入る `z` の最大は、中央値で -38.1 でした。2 層目だけが死んだのは、入力が 0 以上に偏っているためと考えられます。

<br>

#### 更新ごとに見たユニット

ユニットがいつ死ぬのかを見るため、`partial_fit` で 200 行ずつ 1 回ずつ更新し、2 層目の 64 個のユニットが、学習データのうち何割の行で 0 より大きい値を返すかを更新ごとに並べました。40 回の更新は約 6 エポックにあたります。

{{< figure src="af_dead_steps.webp" alt="2 つの 8×8 のマス目が 1 回目から 40 回目の更新まで動く図で、各マスが 2 層目の 1 ユニット。左の learning_rate_init=0.001 は 40 回目まで全てのマスが青のままで、正解率は 0.14 から 0.80 へ上がる。右の learning_rate_init=0.3 は 1 回目の更新の後に 20 マスが赤になり、5 回目で 36、10 回目で 50、40 回目で 57 マスが赤になる。正解率は 10 回目の 0.42 から下がり、40 回目は 0.35。最後のコマで 3 秒止まる" caption="更新のたびに、2 層目のユニットが 0 しか返さなくなる様子（1 回の更新を 0.25 秒ずつ表示）" align="center" >}}

シード 0 の 1 回では、学習率 0.3 のユニットは数回の更新のうちに死にました。1 回目の更新を終えた時点で既に 20 個が赤になり、10 回目で 50 個、40 回目で 57 個まで増えました。1 つ手前の層で重みが動くので、赤から青に戻ったマスも 40 回で延べ 20 回ありました。ただし多くは 10 回目までで、21 回目より後は 1 つも戻っていません。学習率 0.001 では 40 回の更新で 1 個も死なず、正解率は 0.80 まで上がっています。

動く図の数は、次のコードで数えました。最適化手法は、更新の幅を重みごとに調整する既定の [Adam](https://arxiv.org/abs/1412.6980) のままです。1 回に使う 200 行は既定の `batch_size` と同じで、digits の訓練データ 1347 行を 1 周する 1 エポックは、約 7 回の更新にあたります。

```python
def active_ratio(model, X):
    """最後の隠れ層の各ユニットが、0 より大きい値を返す行の割合。"""
    a = X
    for W, b in zip(model.coefs_[:-1], model.intercepts_[:-1]):
        a = np.maximum(a @ W + b, 0)
    return (a > 0).mean(axis=0)


for lr in [0.001, 0.3]:
    mdl = MLPClassifier(hidden_layer_sizes=(64, 64), learning_rate_init=lr, random_state=0)
    rng = np.random.default_rng(0)
    frames = []
    for step in range(1, 41):
        idx = rng.choice(len(X_train), 200, replace=False)  # 既定の batch_size と同じ 200 行
        mdl.partial_fit(X_train[idx], y_train[idx], classes=np.arange(10))
        frames.append((active_ratio(mdl, X_train), mdl.score(X_test, y_test)))
    for step in (1, 5, 10, 20, 40):
        r, acc = frames[step - 1]
        print(f"lr={lr:<5} {step:>2} 回目の更新の後: 0 しか返さないユニット {int((r == 0).sum()):>2} / 64  "
              f"テストの正解率 {acc:.2f}")
    # 赤（全ての行で 0）から青に戻ったマスを、更新ごとに数える
    back = [int(((frames[s - 1][0] == 0) & (frames[s][0] > 0)).sum()) for s in range(1, 40)]
    print(f"lr={lr:<5} 赤から青に戻ったマス: 計 {sum(back)} 回、"
          f"戻った更新 {[s + 2 for s, n in enumerate(back) if n]}、"
          f"11 回目以降 {sum(back[9:])} 回")
```

```text
lr=0.001  1 回目の更新の後: 0 しか返さないユニット  0 / 64  テストの正解率 0.14
lr=0.001  5 回目の更新の後: 0 しか返さないユニット  0 / 64  テストの正解率 0.18
lr=0.001 10 回目の更新の後: 0 しか返さないユニット  0 / 64  テストの正解率 0.37
lr=0.001 20 回目の更新の後: 0 しか返さないユニット  0 / 64  テストの正解率 0.61
lr=0.001 40 回目の更新の後: 0 しか返さないユニット  0 / 64  テストの正解率 0.80
lr=0.001 赤から青に戻ったマス: 計 0 回、戻った更新 []、11 回目以降 0 回
lr=0.3    1 回目の更新の後: 0 しか返さないユニット 20 / 64  テストの正解率 0.15
lr=0.3    5 回目の更新の後: 0 しか返さないユニット 36 / 64  テストの正解率 0.32
lr=0.3   10 回目の更新の後: 0 しか返さないユニット 50 / 64  テストの正解率 0.42
lr=0.3   20 回目の更新の後: 0 しか返さないユニット 55 / 64  テストの正解率 0.34
lr=0.3   40 回目の更新の後: 0 しか返さないユニット 57 / 64  テストの正解率 0.35
lr=0.3   赤から青に戻ったマス: 計 20 回、戻った更新 [2, 3, 4, 5, 6, 9, 11, 14, 15, 21]、11 回目以降 4 回
```

40 回目の正解率 0.35 は、冒頭の図にあるシード 0 の 0.30 と一致しません。違いは 2 つあり、動く図は学習を途中で止めて測っていることと、更新に使う 200 行を毎回無作為に選ぶので、行を並べ替えて 1 周ずつ使う `fit` とは選び方が違うことです。

<br>

#### 死なせないための選び方

scikit-learn の中で済ませるなら、学習率を既定の 0.001 付近に保つか、`activation="tanh"` に変えます。冒頭の実験では、0.03 までは死んだユニットが 1 桁で、0.1 で急に増えました。

PyTorch では、Leaky ReLU や GELU に替えられます。Leaky ReLU は負の入力でも傾きが係数のまま残るので、一度 `z` が負に寄ったユニットにも勾配が届き、重みが動いて、また正の値を返すようになる可能性があります。

GELU の傾きは `z ≈ -0.75` で 0 になり、大きい負の `z` でも 0 に近づくので、Leaky ReLU ほど確実には勾配が届きません。どの関数を使う時も、学習の後に上の `dead_units` と同じ計算で、全ての行で 0 を返すユニットが無いかを数えます。

---

### 学習に使っていない範囲の予測

ReLU の MLP は、短い直線をつないだ関数になります。円のデータで ReLU の境界が多角形になったのも、このためです。多角形の辺は斜めにも引けるので、[決定木](../decision-tree/)のように座標軸に沿った線だけで区切るわけではありません。この性質は、学習に使っていない範囲の入力に何を返すかに表れます。

`y = x²` の点を `-2 ≦ x ≦ 2` の範囲だけで 300 個作り、[`MLPRegressor`](https://scikit-learn.org/stable/modules/generated/sklearn.neural_network.MLPRegressor.html) を ReLU と tanh で学習させました。比べる相手は、決定木を多数作って予測を平均する[ランダムフォレスト](../random-forest/)です。

```python
rng = np.random.default_rng(0)
x = rng.uniform(-2, 2, 300)
t = x**2 + rng.normal(0, 0.05, 300)                     # 正解は y = x^2
x_new = np.array([[-10.0], [-5.0], [-2.0], [0.0], [2.0], [5.0], [10.0]])
regs = {
    "relu": MLPRegressor(hidden_layer_sizes=(64, 64), max_iter=5000, random_state=0),
    "tanh": MLPRegressor(hidden_layer_sizes=(64, 64), activation="tanh", max_iter=5000,
                         random_state=0),
    "ランダムフォレスト": RandomForestRegressor(random_state=0),
}
print(x_new.ravel(), "x")
print(x_new.ravel() ** 2, "正解")
for name, reg in regs.items():
    reg.fit(x[:, None], t)
    print(reg.predict(x_new).round(1), name)
```

```text
[-10.  -5.  -2.   0.   2.   5.  10.] x
[100.  25.   4.   0.   4.  25. 100.] 正解
[21.1 10.3  3.7  0.   3.8 10.2 20.8] relu
[ 4.8  5.2  3.6 -0.   3.7  5.7  5.5] tanh
[ 4.   4.   4.  -0.   3.9  3.9  3.9] ランダムフォレスト
```

{{< figure src="af_extrapolate.webp" alt="横軸 x が -10〜10、縦軸が予測の折れ線グラフ。灰色の帯の -2〜2 が学習に使った範囲で、3 つのモデルは帯の中では灰色の点線の正解 y = x² に重なる。帯の外では、赤の relu は帯の端から直線で伸び、x=10 で約 21。緑の tanh は 5 前後で平らになる。青のランダムフォレストは帯の端の値 4 のまま水平に伸びる。正解の点線は x=±6 付近で 40 を超えて図の外へ出る" caption="学習に使っていない範囲の予測（正解は y = x²）" align="center" >}}

3 つとも、学習した範囲の中では正解の放物線に重なります。範囲の外では、ReLU は帯の端と同じ傾きのまま直線で伸び、`x = 10` で 20.8 を返しました。tanh の MLP は、隠れ層の出力が -1〜1 で頭打ちになり、出力層はその値に重みを掛けて足すだけなので、このシードでは 5 前後で平らになり、ランダムフォレストは端の値 3.9 のまま動きません。正解は 100 なので、どれも外れています。

価格や需要のように、将来の値が学習データの範囲を超えうる回帰では、この違いが予測の外れ方を決めます。どれが正しいかはデータ次第で、活性化関数を変えても範囲の外を当てられるようにはなりません。

---

### 出力層の関数

ここまでは隠れ層の話でした。出力層の関数は、何を予測するかで決まります。scikit-learn は自動で選び、学習した後の `out_activation_` で確認できます。

| 予測するもの | 出力層の関数 | 損失 | scikit-learn | PyTorch の損失 |
|---|---|---|---|---|
| 2 値分類 | sigmoid | 交差エントロピー | `logistic` | `BCEWithLogitsLoss` |
| 多クラス分類 | softmax | 交差エントロピー | `softmax` | `CrossEntropyLoss` |
| 回帰 | 無し（`identity`） | 二乗誤差 | `identity` | `MSELoss` |
| 0 以上の件数 | exp | ポアソン分布の損失 | `exp` | `PoissonNLLLoss` |
| -1〜1 に揃えた画素 | tanh | 二乗誤差など | 無し | `MSELoss` など |

件数の行は、scikit-learn 1.9.1 では `MLPRegressor(loss="poisson")` を指定した時に選ばれます。回帰の出力層に ReLU を置くと負の値を出せないので、目的変数が負を取るなら出力層は `identity` のままにします。

逆に正の値だけを取る量なら、`log(1 + exp(z))` を返す [softplus](https://docs.pytorch.org/docs/stable/generated/torch.nn.Softplus.html) や exp を出力層に置いて、負の値を出さないようにする手もあります。

softmax は、クラスごとの点数 `z_k` を `exp(z_k) / Σ exp(z_j)` で合計 1 の確率に直す関数です。[MoE（Mixture of Experts）](/notes/generative-ai/mixture-of-experts/)のルーターが専門家への配分を決める所のように、出力層以外でも使われます。

深いネットワークの隠れ層では ReLU 系が多くなった今も、sigmoid と tanh には出力の範囲を活かした使い道があります。文章のような系列を 1 語ずつ読む再帰型のネットワーク [LSTM](https://pytorch.org/docs/stable/generated/torch.nn.LSTM.html) と GRU は、ゲートと呼ぶ部品で、前の状態をどれだけ残すかを 0〜1 の割合として決めます。この割合を出すのに、今も sigmoid を使い、候補の値と隠れ状態には tanh を使います。

画像を -1〜1 の画素で出す生成モデルでは、[DCGAN](https://arxiv.org/abs/1511.06434) の生成器のように出力層に tanh を置きます。一方、[Diffusion Model](/notes/generative-ai/diffusion-model/) で使う UNet というネットワークは、[DDPM](https://arxiv.org/abs/2006.11239) のようにノイズを予測させる形では、画素ではなくノイズの予測を出します。この形では、出力層は回帰と同じく関数を置きません。

<br>

#### softmax を二重に掛けた時の損失

PyTorch では、出力層の関数を損失関数が持ちます。softmax を掛ける前のクラスごとの点数を logits と呼びます。[`CrossEntropyLoss`](https://pytorch.org/docs/stable/generated/torch.nn.CrossEntropyLoss.html) は logits を受け取る前提で、中で softmax を計算します。2 値分類の [`BCEWithLogitsLoss`](https://pytorch.org/docs/stable/generated/torch.nn.BCEWithLogitsLoss.html) も同じで、中で sigmoid を計算します。

モデルの最後に `nn.Softmax` を置いたまま渡すと、softmax が二重に掛かります。損失関数がまとめて計算するのは、確率にしてから対数を取ると、logits が大きい時に損失が `inf` になるからです。この様子は[対数・指数と log-odds](../../math/log-exp-logodds/) で実測しています。

NumPy で同じ計算を書き、二重に掛かった時に何が起きるかを調べました。1 回目で softmax が返す値は 0〜1 なので、2 回目に入る値の差は最大でも 1 です。正解のクラスに 1、他に 0 を完全に返しても、2 回目の softmax は正解に `e / (e + k - 1)` しか割り当てません。

```python
def softmax(z):
    e = np.exp(z - z.max(axis=1, keepdims=True))
    return e / e.sum(axis=1, keepdims=True)


for k in [2, 10, 100]:
    perfect = np.full((1, k), -1e9)
    perfect[0, 0] = 1e9                                 # 正解のクラスにだけ大きい値を返す
    q = softmax(softmax(perfect))
    print(f"{k:>3} クラス: 完全に当てても二重に掛けた損失は {-np.log(q[0, 0]):.3f}"
          f"（式 log(1 + (k - 1) / e) = {np.log(1 + (k - 1) / np.e):.3f}）")
```

```text
  2 クラス: 完全に当てても二重に掛けた損失は 0.313（式 log(1 + (k - 1) / e) = 0.313）
 10 クラス: 完全に当てても二重に掛けた損失は 1.461（式 log(1 + (k - 1) / e) = 1.461）
100 クラス: 完全に当てても二重に掛けた損失は 3.622（式 log(1 + (k - 1) / e) = 3.622）
```

digits の 10 クラスでは、損失は 1.461 より下がりません。digits の 64 画素から 10 クラスの logits を出す 1 層のモデルを作り、正しい損失と二重に掛けた損失で、それぞれ 300 回更新しました。

```python
Y = np.eye(10)[y_train]
loss_hist = {}
for double in [False, True]:
    rng = np.random.default_rng(0)
    Wd = rng.normal(0, 0.01, (64, 10))
    bd = np.zeros(10)
    hist = []
    for epoch in range(300):
        z = X_train @ Wd + bd                            # 出力層の値（logits）
        p = softmax(z)
        if double:
            q = softmax(p)                              # 損失の側でもう一度 softmax が掛かる
            g_p = q - Y
            g = p * (g_p - (p * g_p).sum(axis=1, keepdims=True))
        else:
            q = p
            g = p - Y
        hist.append(-np.log(q[np.arange(len(Y)), y_train]).mean())
        Wd -= 0.5 * X_train.T @ g / len(Y)
        bd -= 0.5 * g.mean(axis=0)
    acc = (np.argmax(X_test @ Wd + bd, axis=1) == y_test).mean()
    loss_hist[double] = hist
    print(f"二重に掛ける={double!s:<5} 300 回後の損失 {hist[-1]:.3f}  テストの正解率 {acc:.3f}")
```

```text
二重に掛ける=False 300 回後の損失 0.062  テストの正解率 0.962
二重に掛ける=True  300 回後の損失 1.520  テストの正解率 0.953
```

{{< figure src="af_double_softmax.webp" alt="横軸が更新の回数 0〜300、縦軸が訓練データの交差エントロピーの折れ線グラフ。青の logits をそのまま損失へ渡した線は 2.3 から急に下がり、300 回で 0.06。赤の softmax を掛けてから損失へ渡した二重の線は 2.3 からゆっくり下がり、1.52 付近で平らになる。赤い点線が二重に掛けた時の下限 1.461 を示す" caption="softmax を二重に掛けた時の損失（digits、10 クラス）" align="center" >}}

テストの正解率は 0.953 と 0.962 で、ほとんど変わりません。一方で損失は 1.52 で平らになり、正しく学習できている時の 0.062 とは桁が違います。正解率だけを見ると間違いに気づかず、損失だけを見ると学習できていないと誤解します。

損失の下限が上がって勾配も縮むので、損失で比べる早期終了や学習率の調整は、正しい損失を前提にした基準からずれます。PyTorch の 10 クラスの分類で損失が 1.46 付近から下がらない時は、モデルの最後に softmax が残っていないかを先に見ます。

---

### 活性化関数を選ぶ・変える時に見ること

scikit-learn の `MLPClassifier` で隠れ層の関数に迷ったら、既定の ReLU から始めます。学習した後は、正解率と一緒に `n_iter_` と `loss_curve_` を見ます。数十エポックで止まり、損失が 2 値分類なら `log 2 = 0.693` のような最初の値から動いていなければ、sigmoid の時のように平らな区間で止まった可能性があります。その時は関数を ReLU か tanh に変えるか、`n_iter_no_change` を増やして学習を続けさせます。

学習率を上げた後は、`dead_units` と同じ計算で 0 しか返さないユニットを数えます。冒頭の実験では、正解率がまだ 0.93 あった 0.1 で、既に 38 個が死んでいました。既定の学習率で学習した時より大きく増えていれば、学習率を戻すか tanh に変えます。PyTorch なら Leaky ReLU や GELU も候補です。

予測する値が学習データの範囲を超えうる回帰では、ReLU は端の傾きで直線を延ばし、tanh は頭打ちになり、ランダムフォレストは端の値に留まることを踏まえて、学習に使っていない範囲の予測をどこまで使うかを決めます。出力層は、scikit-learn では自動で決まり、PyTorch では損失関数に logits をそのまま渡します。

正解率が落ちた時に警告が出なくても、0 しか返さないユニットの数と損失曲線の形は、学習率を上げた ReLU のユニットが死んだのか、平らな区間で止まったのかを見分ける手がかりになります。
