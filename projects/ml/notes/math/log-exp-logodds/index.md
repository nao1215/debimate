---
title: "対数・指数と log-odds - 確率を掛けただけの Naive Bayes が、digits で正解率 10% に落ちる理由"
date: 2026-05-26
draft: false
series: ["機械学習ノート", "Mathematics"]
tags: ["machine-learning", "math"]
weight: 14
topics: ["Mathematics（数学の基礎）"]
---

対数 `log(x)` は、ある数を何乗すれば `x` になるかを返す関数で、指数関数 `exp(x)` の逆関数です。機械学習では、確率の掛け算を足し算に変える時と、0〜1 に収まる確率を実数全体に広げる時に使います。後者で使う値が log-odds（対数オッズ）で、[ロジスティック回帰](../../ml/logistic-regression/)の出力の土台になっています。

以下は、[scikit-learn](https://scikit-learn.org/stable/) に同梱の [digits](https://scikit-learn.org/stable/modules/generated/sklearn.datasets.load_digits.html) を Naive Bayes で分類した結果です。digits は、0〜9 の手書き数字 1797 枚を 8×8 画素の濃さで表したデータです。Naive Bayes は、数字ごとに「その数字である確率」から始め、各画素について「その数字なら、インクがその画素に落ちる割合」を濃さの回数だけ掛け、値が最も大きい数字を答える分類器です。1 枚で 300 回ほど、1 未満の数を掛けることになります。

同じ確率について、そのまま掛けて比べる計算と、log を取って足して比べる計算で、学習に使わなかった 540 枚の正解率を測りました。log は増える関数なので、数学の上では 2 つの答えは同じになるはずです。

{{< figure src="le_cover.webp" alt="横軸は計算に使った画素の数 1〜64、縦軸はテストの正解率。画素 28 個ほどまでは、青い実線の log の和と赤い破線の確率の積が重なって上がる。30 個前後から灰色の棒で示した、10 個の確率が全て 0.0 になった画像の割合が増え始め、赤い破線は 35 個付近の 0.55 から下がり、64 個で 10.4% になる。青い実線は上がり続けて 64 個で 89.6%。10% の位置に、全て「0」と答えた時の正解率の点線がある" caption="digits を Naive Bayes で分類した時のテストの正解率（確率を掛ける計算と、log を足す計算）" align="center" >}}

64 画素を全て使うと、log を足す計算は 89.6% で、確率を掛ける計算は 10.4% でした。掛ける計算では、テストの 99.6% の画像で 10 個の数字の値が全て `0.0` になりました。全部が `0.0` では区別できないので、1 番目の「0」を答えていました。エラーも警告も出ません。

Naive Bayes の式を教科書どおりに書いた時や、分類の確率を自分で計算したら、数ではない値の `nan` や無限大の `inf` が返った時は、コンピュータの小数が表せる範囲の外に出ています。ロジスティック回帰の係数を「確率が何 % 下がる」と読む誤りも、log-odds と確率の関係を知ると避けられます。

<br>

本記事では、ML の説明に出てくる log・exp・log-odds を自分で計算して確認したい人と、scikit-learn の結果を読む人に向けて、次の疑問に答えます。

- log と exp は何が対応し、ML の log の底は何か。
- 確率をそのまま掛けると、どこで 0 になるのか。
- 確率を足す softmax では、何が壊れるのか。
- 1 に近い確率の log は、なぜ損失を inf にするのか。
- ロジスティック回帰の係数は、確率の何を表すのか。

実験は scikit-learn 1.9.1 と、Python の数値計算のライブラリの [NumPy](https://numpy.org/) 2.5.4・[SciPy](https://scipy.org/) 1.18.1 で行いました。図を描く処理も含めた完全なコードは [log-exp-logodds_gen.py](https://github.com/nao1215/debimate/blob/main/projects/ml/scripts/notes/log-exp-logodds_gen.py) にあります。

---

### log と exp、積が和になる性質

底 `a` に対して、`a^z = x` と `log_a(x) = z` は同じ関係を表します。`a = e ≈ 2.718` の対数を自然対数と呼び、機械学習と統計で底を書かずに `log` とあれば自然対数です。[情報理論](../information-theory/)でビットを単位にする時は `log_2` を使います。

{{< figure src="le_curves.webp" alt="左は log(x)、log2(x)、log10(x) の 3 本の曲線で、どれも x = 1 で 0 を通る。右は exp(x) と log(x) を同じ座標に描いた図で、点線の y = x を挟んで鏡に映した形になる" caption="底だけが違う 3 つの対数と、exp と log の関係" align="center" >}}

左の 3 本は形が同じで、`log_2(x) = log(x) / log(2)` のように定数倍だけ違います。右の図のとおり、`exp` と `log` は直線 `y = x` を挟んで鏡に映した形で、`exp(log(x)) = x` が成り立ちます。`log` が受け付けるのは正の数だけで、`log(0)` は `-inf` です。

<br>

機械学習で一番使う性質は、積が和になることです。

`log(x y) = log(x) + log(y)`、`log(x / y) = log(x) - log(y)`、`log(x^k) = k log(x)`

モデルのパラメータは、学習データ 1 件ずつに付けた確率の積が最大になるように決めることがあり、この積を尤度と呼びます。尤度 `Π_i p_i` を最大にする時は、代わりに `Σ_i log(p_i)` を最大にします。log は増える関数なので、最大になるパラメータは変わりません。和にすると、[勾配](../partial-derivative-gradient/)も 1 件ずつの勾配の和で求まります。

底は、ツールを移る時に取り違えやすい所です。NumPy の `np.log` と Python の [`math.log`](https://docs.python.org/3/library/math.html#math.log) は、底を省くと自然対数です。一方で、Excel の [`LOG` 関数](https://support.microsoft.com/en-us/office/log-function-4e82f196-1ca9-4747-8fb0-6c4a3abb3280)は底を省くと 10 になります。Python で計算した値を Excel で確認すると、`log(10) ≈ 2.303` 倍ずれます。

---

### 確率を掛けると 0 になる所

冒頭の実験では、scikit-learn の [`MultinomialNB`](https://scikit-learn.org/stable/modules/generated/sklearn.naive_bayes.MultinomialNB.html) で学習した確率を取り出し、比べる所だけを自分で書きました。`MultinomialNB` は、画素の濃さ 0〜16 をその画素に落ちたインクの量とみなします。数字 c の値は、`P(c)` に、各画素について `P(画素 j | c)` を濃さの回数だけ掛けたものです。Naive Bayes が確率を掛け合わせてよい理由は、[ベイズの定理](../bayes-theorem/)で説明しています。

`P(画素 j | c)` は、数字 c の画像のインクのうち、画素 j に落ちる割合です。既定の `alpha=1` で、各画素の回数に 1 を足して均してから割合にしています。テストの 1 枚のインクの合計は中央値で 311 なので、1 未満の数を 300 回ほど掛けることになります。以下のコードの `predict_product` は確率を先頭の k 画素まで順に掛け、`predict_log` は同じ計算を log の和で行います。

```python
X, y = load_digits(return_X_y=True)
X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.3, random_state=0, stratify=y)
nb = MultinomialNB().fit(X_tr, y_tr)
prior = np.exp(nb.class_log_prior_)   # P(数字)、10 個
theta = np.exp(nb.feature_log_prob_)  # P(画素 | 数字)、10 × 64


def predict_product(X, k, dtype=np.float64):
    """先頭の k 画素について、確率をそのまま掛けて一番大きい数字を選ぶ"""
    score = np.tile(prior.astype(dtype), (len(X), 1))
    for j in range(k):
        score = score * theta[:, j].astype(dtype) ** X[:, j:j + 1].astype(dtype)
    return score.argmax(axis=1), (score.max(axis=1) == 0).mean()


def predict_log(X, k):
    """同じ計算を log の和で行う"""
    score = nb.class_log_prior_ + X[:, :k] @ nb.feature_log_prob_[:, :k].T
    return score.argmax(axis=1), score.max(axis=1)


pred_prod, zero_share = predict_product(X_te, 64)
pred_log, best_log = predict_log(X_te, 64)
print(f"確率を掛ける: 正解率 {(pred_prod == y_te).mean():.3f}、10 個とも 0.0 の画像 {zero_share:.1%}")
print(f"log を足す:   正解率 {(pred_log == y_te).mean():.3f}（MultinomialNB.score は {nb.score(X_te, y_te):.3f}）")
print("一番大きい log の和: 最大", best_log.max().round(1), " 中央値", np.median(best_log).round(1))
for dtype in [np.float64, np.float32]:
    smallest = np.nextafter(dtype(0), dtype(1))  # 0 より大きい最小の数
    print(f"{dtype.__name__}: 0 より大きい最小の数 {smallest:.3g}、その log {np.log(np.float64(smallest)):.1f}")
pred32, zero32 = predict_product(X_te, 64, np.float32)
print(f"float32 で掛ける: 正解率 {(pred32 == y_te).mean():.3f}、10 個とも 0.0 の画像 {zero32:.1%}")
```

```text
確率を掛ける: 正解率 0.104、10 個とも 0.0 の画像 99.6%
log を足す:   正解率 0.896（MultinomialNB.score は 0.896）
一番大きい log の和: 最大 -600.6  中央値 -1096.3
float64: 0 より大きい最小の数 4.94e-324、その log -744.4
float32: 0 より大きい最小の数 1.4e-45、その log -103.3
float32 で掛ける: 正解率 0.100、10 個とも 0.0 の画像 100.0%
```

10 個の数字のうち一番大きい log の和は、中央値で -1096.3 です。float64 で表せる 0 より大きい最小の数は約 `4.94 × 10^-324` で、その log は -744.4 なので、`exp(-1096.3)` は表せずに `0.0` へ丸められます。10 個とも `0.0` になると、`argmax` は同点の先頭を返すので、答えは「0」になります。テストに占める「0」は 10.0% で、正解率の 10.4% はほぼこの値です。

<br>

冒頭の図の 32 画素では、全て `0.0` になった画像はまだ 4.1% ですが、正解率は 44.4% と 47.4% に離れています。正解の数字の値が先に `0.0` に落ち、残った別の数字を答えた画像があるためと考えられます。ニューラルネットの学習でよく使う float32 は、最小の数の log が -103.3 しかなく、64 画素では 100% の画像が `0.0` になりました。

scikit-learn の `MultinomialNB` 自身は、学習した確率を log のまま `feature_log_prob_` に持ち、log の和で比べます。そのため `nb.score` の 89.6% は、上の `predict_log` の正解率と一致します。

---

### 確率を足す所: log-sum-exp と softmax

log で分解できるのは積だけで、確率の和は分解できません。和が要るのは、クラスごとの値を合計 1 の確率に揃える時です。Naive Bayes の値を確率にする時や、[損失関数](../../ml/loss-functions/)で使う softmax の分母では、log のまま持っている値 `a_k = log p_k` から `log(Σ_k exp(a_k))` を求めます。この計算を log-sum-exp と呼びます。

`a_k` が -1000 ほどだと、`exp(a_k)` は全て `0.0` になり、和の log は `-inf` になります。SciPy の [`scipy.special.logsumexp`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.special.logsumexp.html) は、最大値 `m` を括り出して `m + log(Σ_k exp(a_k - m))` と計算します。最大の項は `exp(0) = 1` になるので、和が `0.0` になりません。

```python
a = np.array([-1000.0, -1001.0, -1002.0])  # log p_k
print("確率に戻してから足す:", np.log(np.sum(np.exp(a))))
m = a.max()
print("最大値を括り出す:", m + np.log(np.sum(np.exp(a - m))), " logsumexp:", logsumexp(a))
print("softmax:", np.exp(a - logsumexp(a)))
```

```text
確率に戻してから足す: -inf
最大値を括り出す: -999.5923940355556  logsumexp: -999.5923940355556
softmax: [0.66524096 0.24472847 0.09003057]
```

最後の行の `exp(a - logsumexp(a))` が softmax です。softmax は、各クラスの値を `exp` で正の数にし、その合計で割って合計 1 にする関数です。式は `exp(z_k) / Σ_j exp(z_j)` で、モデルが出した実数のスコアであるロジットを合計 1 の確率に変えます。全てのロジットに同じ数 `c` を足しても、分子と分母に同じ `exp(c)` が掛かって消えるので、答えは変わらないはずです。

<br>

そこで、ロジット `[2, 1, 0]` に `c` を足しながら、式どおりに書いた素朴な softmax が `[0.665, 0.245, 0.090]` を返すかを確認しました。

```python
def softmax_naive(z):
    e = np.exp(z)
    return e / e.sum()


z = np.array([2.0, 1.0, 0.0])
shifts = np.arange(-1200, 1201)
for dtype in [np.float32, np.float64]:
    ok = np.array([np.isfinite(softmax_naive((z + c).astype(dtype))).all() for c in shifts])
    print(f"{dtype.__name__}: 素朴な softmax が数を返す c の範囲 {shifts[ok].min()}〜{shifts[ok].max()}")
print("c = 0:", softmax_naive(z).round(4), " c = 88（float32）:", softmax_naive((z + 88).astype(np.float32)))
print("c = 88 で最大値を引く版:", softmax((z + 88).astype(np.float32)).round(4))
```

```text
float32: 素朴な softmax が数を返す c の範囲 -105〜86
float64: 素朴な softmax が数を返す c の範囲 -747〜707
c = 0: [0.6652 0.2447 0.09  ]  c = 88（float32）: [nan nan  0.]
c = 88 で最大値を引く版: [0.6652 0.2447 0.09  ]
```

{{< figure src="le_softmax.webp" alt="3 本の横帯。上の素朴な softmax（float32）は c が -105〜86 の狭い範囲だけ濃い赤で、外側は nan。中央の素朴な softmax（float64）は -747〜707 が濃い灰色で、外側は nan。下の最大値を引く softmax は -1200〜1200 の全体が青で、全てで正しい答えと書かれている" caption="ロジット [2, 1, 0] に c を足した時、softmax が正しい答えを返した範囲" align="center" >}}

float32 では、最大のロジットが 88 を超えると `exp` がオーバーフローして `inf` になり、`inf / inf` で `nan` になります。逆に最大のロジットが -104 ほどより小さいと、`exp` が全て `0.0` になり、`0 / 0` でやはり `nan` です。最大値を引いて計算する SciPy の [`softmax`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.special.softmax.html) は、どの `c` でも同じ答えを返しました。

<br>

ロジットが 88 を超える場面は、大規模言語モデル（LLM）の [temperature](/notes/generative-ai/sampling/) で起きます。temperature はロジットを T で割ってから softmax に渡す値で、T を小さくすると割った後のロジットが大きくなります。以下は、ロジット `[12, 11, 9.5, 7]` を float32 で T で割った結果です。

```python
logits = np.array([12.0, 11.0, 9.5, 7.0], dtype=np.float32)
for T in [1.0, 0.2, 0.13]:
    t = np.float32(T)
    print(f"temperature {T}: 素朴 {softmax_naive(logits / t).round(4)}、最大値を引く {softmax(logits / t).round(4)}")
```

```text
temperature 1.0: 素朴 [0.6865 0.2525 0.0563 0.0046]、最大値を引く [0.6865 0.2525 0.0563 0.0046]
temperature 0.2: 素朴 [0.9933 0.0067 0.     0.    ]、最大値を引く [0.9933 0.0067 0.     0.    ]
temperature 0.13: 素朴 [nan  0.  0.  0.]、最大値を引く [9.995e-01 5.000e-04 0.000e+00 0.000e+00]
```

T = 0.13 では最大のロジットが `12 / 0.13 ≈ 92` になり、素朴な softmax は一番選ばれるべきトークンの確率を `nan` にしました。トークンは、LLM が文章を扱う単位の断片です。T を 0 に近付けて「毎回同じ答え」にしたい時ほど、この `nan` に近付きます。

---

### 1 に近い確率の log: log1p と交差エントロピー

float64 で 1 の次に大きい数は `1 + 2.2 × 10^-16` ほどで、その間の数は表せません。そのため `1 + 1e-16` は `1.0` に丸められ、`log(1 + 1e-16)` は 0 になります。NumPy の [`np.log1p(x)`](https://numpy.org/doc/stable/reference/generated/numpy.log1p.html) は、`1 + x` を作らずに `log(1 + x)` を求める関数です。

```python
for x in [1e-4, 1e-8, 1e-12, 1e-16]:
    naive, exact = np.log(1 + x), np.log1p(x)
    print(f"x = {x:g}: log(1 + x) = {naive:.6e}、log1p(x) = {exact:.6e}、相対誤差 {abs(naive - exact) / exact:.1e}")
```

```text
x = 0.0001: log(1 + x) = 9.999500e-05、log1p(x) = 9.999500e-05、相対誤差 1.1e-13
x = 1e-08: log(1 + x) = 1.000000e-08、log1p(x) = 1.000000e-08、相対誤差 6.1e-09
x = 1e-12: log(1 + x) = 1.000089e-12、log1p(x) = 1.000000e-12、相対誤差 8.9e-05
x = 1e-16: log(1 + x) = 0.000000e+00、log1p(x) = 1.000000e-16、相対誤差 1.0e+00
```

[歪度](../skewness/)を抑える前処理で件数や金額に `log1p` を使う時は、`x` が 0 以上の整数や大きな値なので、この誤差は問題になりません。効いてくるのは、`log(1 - p)` の `p` のように、1 との差が小さい値を扱う時です。

<br>

2 値分類の交差エントロピーは、正解が 0 の時 `-log(1 - p)` です。p は、ロジット z を [sigmoid](../../ml/activation-functions/) `1 / (1 + exp(-z))` で確率にした値です。z が大きいと p が `1.0` に丸められ、`1 - p` が 0 になって、損失が `inf` になります。

`-log(1 - p)` を `-log1p(-p)` に書き換えても直りません。log1p が守れるのは `1 + x` を作る時の丸めで、p が `1.0` に丸められた時点で、1 との小さな差は失われているからです。直すには、p を作らずに z から計算します。式は次の 3 行で変形できます。2 行目は分子と分母に `exp(z)` を掛け、3 行目は両辺の log を取って符号を反転しています。

```text
1 - sigmoid(z)       = 1 - 1 / (1 + exp(-z)) = exp(-z) / (1 + exp(-z))
1 - sigmoid(z)       = 1 / (1 + exp(z))
-log(1 - sigmoid(z)) = log(1 + exp(z))
```

右辺は `log(exp(0) + exp(z))` なので、前の節の log-sum-exp で値が 0 と z の 2 つの場合です。NumPy の [`np.logaddexp(0, z)`](https://numpy.org/doc/stable/reference/generated/numpy.logaddexp.html) は、これを計算する関数です。

z > 0 なら、大きい方の z を括り出して次の形で計算します。

```text
log(1 + exp(z)) = z + log(1 + exp(-z))
```

`exp(-z)` は 1 より小さい数になるのでオーバーフローしません。残った `log(1 + exp(-z))` は、z が大きいほど `exp(-z)` が小さくなるので、ここで log1p が効きます。以下のコードは、確率から計算した場合と z から計算した場合を比べます。

```python
zs64 = np.arange(0, 60, 0.01)
for dtype in [np.float32, np.float64]:
    zz = zs64.astype(dtype)
    p = 1 / (1 + np.exp(-zz))     # sigmoid で確率にしてから
    loss = -np.log(1 - p)         # 正解が 0 の時の交差エントロピー
    print(f"{dtype.__name__}: 確率にしてから log を取ると、z = {float(zz[np.isinf(loss)][0]):.2f} で inf")
p40 = 1 / (1 + np.exp(-40.0))
print("z = 40: p =", p40, " 確率から log1p で計算:", -np.log1p(-p40))
print("z = 40 をロジットのまま計算:", np.logaddexp(0, 40.0), " z + log1p(exp(-z)):", 40.0 + np.log1p(np.exp(-40.0)))
```

```text
float32: 確率にしてから log を取ると、z = 16.64 で inf
float64: 確率にしてから log を取ると、z = 36.74 で inf
z = 40: p = 1.0  確率から log1p で計算: inf
z = 40 をロジットのまま計算: 40.0  z + log1p(exp(-z)): 40.0
```

{{< figure src="le_log1p.webp" alt="左は x = 1e-4、1e-8、1e-12、1e-16 の 4 本の棒で、log(1 + x) の相対誤差は 1.1e-13、6.1e-09、8.9e-05 と x が小さいほど大きくなり、1e-16 では答えが 0.0 になって 100%。右は横軸がロジット z、縦軸が交差エントロピーで、青いロジットのまま計算した線は 45 まで真っ直ぐ伸びる。赤い破線の float32 は z = 16.64 で、灰色の float64 は z = 36.74 で線が途切れて inf になる" caption="log(1 + x) の誤差と、確率に戻してから計算した交差エントロピー" align="center" >}}

float32 では z = 16.64 で損失が `inf` になります。学習が進んで自信を持った予測が外れると、ロジットはこの程度の大きさになり得ると考えられます。この式のまま勾配を求めると、各段の微分を掛け合わせる連鎖律で、`1 / (1 - p)` の `inf` に sigmoid の微分の `0` を掛けることになり、勾配は `nan` です。

ニューラルネットのライブラリ [PyTorch](https://pytorch.org/) の [`BCELoss`](https://docs.pytorch.org/docs/stable/generated/torch.nn.BCELoss.html) は確率を受け取る損失で、文書によると log の値を -100 で止めるので、損失は `inf` ではなく 100 に張り付きます。ロジットを受け取る [`BCEWithLogitsLoss`](https://docs.pytorch.org/docs/stable/generated/torch.nn.BCEWithLogitsLoss.html) は、文書に log-sum-exp の工夫で数値的に安定させているとあります。本記事では PyTorch を動かして確認していません。

---

### log-odds とロジスティック回帰の係数

確率 p のオッズは `p / (1 - p)` で、`p = 0.5` で 1、`p = 0.9` で 9、`p = 0.99` で 99 です。オッズの log の `log(p / (1 - p))` を log-odds、またはロジット（logit）と呼びます。p は 0〜1 に収まりますが、log-odds は実数全体を動きます。log-odds から p に戻す関数が、前の節の sigmoid です。2 値分類でモデルが出すロジットは、この log-odds そのもので、softmax に渡すロジットと同じ呼び名なのはそのためです。

ロジスティック回帰は、特徴量の重み付き和 `z = w · x + b` を log-odds として扱います。特徴量 `x_j` が 1 増えると log-odds が `w_j` 増え、オッズは `exp(w_j)` 倍になります。確率が何ポイント動くかは、係数だけでは決まりません。

<br>

scikit-learn に同梱の [breast_cancer](https://scikit-learn.org/stable/modules/generated/sklearn.datasets.load_breast_cancer.html) で、この関係を確認しました。乳がんの細胞核の画像から測った 30 項目で、腫瘍が良性か悪性かを当てるデータで、`target = 1` が良性です。[標準化](../../ml/standardization/)してから学習したので、係数は各列を 1 標準偏差増やした時の log-odds の増え方です。

```python
bc = load_breast_cancer()
Xb_tr, Xb_te, yb_tr, yb_te = train_test_split(bc.data, bc.target, test_size=0.3, random_state=0, stratify=bc.target)
scaler = StandardScaler().fit(Xb_tr)
Xb_tr, Xb_te = scaler.transform(Xb_tr), scaler.transform(Xb_te)
clf = LogisticRegression(max_iter=5000).fit(Xb_tr, yb_tr)
j = np.abs(clf.coef_[0]).argmax()    # 係数の絶対値が最大の列
b = clf.coef_[0][j]
p_before = clf.predict_proba(Xb_te)[:, 1]   # 良性（target = 1）の確率
X_plus = Xb_te.copy()
X_plus[:, j] += 1                            # その列だけ 1 標準偏差増やす
p_after = clf.predict_proba(X_plus)[:, 1]
odds_ratio = (p_after / (1 - p_after)) / (p_before / (1 - p_before))
dp = p_after - p_before
print(f"列 {bc.feature_names[j]}: 係数 {b:.3f}、exp(係数) {np.exp(b):.3f}、テストの正解率 {clf.score(Xb_te, yb_te):.3f}")
print(f"オッズの比: {odds_ratio.min():.4f}〜{odds_ratio.max():.4f}（{len(dp)} 件）")
print(f"確率の変化: {dp.min() * 100:.1f}〜{dp.max() * 100:.1f} ポイント、"
      f"1 ポイント未満 {(np.abs(dp) < 0.01).sum()} 件、10 ポイント超 {(np.abs(dp) > 0.1).sum()} 件")
```

```text
列 radius error: 係数 -1.078、exp(係数) 0.340、テストの正解率 0.959
オッズの比: 0.3403〜0.3403（171 件）
確率の変化: -26.2〜-0.0 ポイント、1 ポイント未満 114 件、10 ポイント超 23 件
```

係数の絶対値が最大だったのは、細胞核の半径のばらつきを表す radius error で、係数は -1.078 でした。この列を 1 標準偏差増やすと、テストの 171 件全てで、良性のオッズがちょうど 0.34 倍になります。ところが、良性の確率の下がり方は 0 から 26.2 ポイントまで散らばり、171 件のうち 114 件は 1 ポイントも動きませんでした。

{{< figure src="le_odds.webp" alt="横軸がもとの良性の確率 0〜1、縦軸が確率の変化（ポイント）の図。灰色の理論の線は、確率 0 と 1 の両端で 0、0.6 付近で最も深い -26 ほどの谷になる U 字形。赤い点のテストの 171 件は全てこの線の上に乗り、多くは確率 0 付近と 1 付近に固まって、変化はほぼ 0" caption="radius error を 1 標準偏差増やした時の良性の確率の変化（オッズは全件 0.34 倍）" align="center" >}}

点が全て 1 本の線に乗るのは、どの件でもオッズが同じ 0.34 倍だからです。もとの確率が 0.5 なら 25.4% へ 24.6 ポイント下がり、0.99 なら 97.1% へ 1.9 ポイントしか下がりません。テストの多くの件は、モデルが良性か悪性かを確信している両端にあるので、確率がほとんど動きません。

「係数 -1.078 は、良性の確率を 66% 下げる」とは読めず、言えるのは「良性のオッズを 0.34 倍にする」までです。

<br>

log が係数の読み方を変える例は、もう 1 つあります。[線形回帰](../../ml/linear-regression/)で列に log を取ると、`log(売上)` の係数 0.3 は「売上が 1% 増えると目的変数が約 0.003 動く」と読みます。目的変数にも log を取った時だけ、「売上が 1% 増えると目的変数が約 0.3% 動く」と読めます。

---

### 確率を log で扱う前に確かめること

確率を掛ける計算を自分で書いたら、同じ計算を log の和でも書き、答えが一致するかを比べます。冒頭の図のとおり、値が `0.0` になっても `argmax` はエラーを出さずに先頭のクラスを返すので、正解率を見ただけでは原因に気付きにくいからです。掛けた値が `0.0` になった行を数えれば、すぐに分かります。

確率を足す所は、`logsumexp` と最大値を引く softmax を使います。自分で書く時は、ロジットから最大値を引いてから `exp` に渡します。float32 では最大のロジットが 88 を超えると壊れるので、temperature を小さくする時は特に確認します。

損失が `inf` や `nan` になったら、確率を経由して log を取っていないかを先に見ます。2 値の交差エントロピーは、ロジットのまま `np.logaddexp` や PyTorch の `BCEWithLogitsLoss` で計算します。

ロジスティック回帰の係数を説明する時は、`exp(係数)` をオッズの比として伝えます。確率の変化で伝えたいなら、もとの確率を決めてから計算します。前の節の図のとおり、同じ係数でも、もとの確率が 0.6 なら 26 ポイント、0.99 なら 2 ポイントです。
