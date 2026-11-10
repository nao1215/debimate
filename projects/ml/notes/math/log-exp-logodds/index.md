---
title: "対数・指数関数の性質と log-odds（log / exp / logit）"
date: 2026-05-26
draft: false
series: ["機械学習ノート", "Mathematics"]
tags: ["machine-learning", "math"]
weight: 14
topics: ["Mathematics（数学の基礎）"]
---

対数関数 `log(x)` と指数関数 `exp(x)` は互いに逆関数の関係にあり、機械学習では「積を和に変換する」「桁の違うスケールを揃える」「確率を log-odds に変換する」といった用途で繰り返し登場します。[ロジスティック回帰](../../ml/logistic-regression/)は、`p / (1 - p)` の対数である log-odds（対数オッズ）を特徴量の線形和で表します。

<br>

本記事では、機械学習で出てくる場面に絞って対数・指数の性質を整理します。具体的には、(1) log と exp の対応関係、(2) 「積を和に」変える代数的性質、(3) シグモイドと logit による確率↔log-odds の往復、(4) 浮動小数点で 0 に潰れる確率の積と和を log 空間で計算する方法（`logsumexp`）の 4 点です。

---

### log と exp の対応関係

底 `a > 0, a ≠ 1` に対して、

`a^z = x` ⇔ `log_a(x) = z`

の関係が成り立ちます。`a = e ≈ 2.718` の場合を「自然対数」と呼び、単に `log(x)` あるいは `ln(x)` と書きます。機械学習・統計の文脈で「log」と書いてあれば原則として自然対数で、エントロピーなど[情報理論](/ml/math/information-theory/)の文脈で `log_2`、対数尺度の可視化で `log_10` が使われる程度の区別となります。

以下のコードは、[生成コード](https://github.com/nao1215/debimate/blob/main/projects/ml/scripts/notes/log-exp-logodds_gen.py)から描画部分を抜き出したものです。[NumPy](https://numpy.org/) と [Matplotlib](https://matplotlib.org/) を使い、軸ラベル・凡例・補助線の設定と保存先の指定を省いています。後のコードも、このコードの import をそのまま使います。

```python
import numpy as np
import matplotlib.pyplot as plt

x_pos = np.linspace(0.05, 4, 200)
x_all = np.linspace(-3, 4, 200)

fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
axes[0].plot(x_pos, np.log(x_pos), color="#7aa6c2", lw=2, label="log(x)")
axes[0].plot(x_pos, np.log2(x_pos), color="#e15759", lw=1.5, ls="--", label="log_2(x)")
axes[0].plot(x_pos, np.log10(x_pos), color="#59a14f", lw=1.5, ls=":", label="log_10(x)")
axes[1].plot(x_all, np.exp(x_all), color="#7aa6c2", lw=2, label="exp(x)")
axes[1].plot(x_all, x_all, color="#999999", lw=1, ls=":", label="y = x")
axes[1].plot(np.linspace(0.05, np.exp(2.5), 200),
             np.log(np.linspace(0.05, np.exp(2.5), 200)),
             color="#e15759", lw=2, label="log(x)")
plt.savefig("log_exp_curves.svg", bbox_inches="tight")
```

{{< figure src="log_exp_curves.svg" alt="左は log(x)、log_2(x)、log_10(x) の 3 本で、どれも x = 1 で 0 を通る。右は exp(x) と log(x) を同じ座標に描き、直線 y = x に対して鏡像になる" caption="log と exp のグラフ" align="center" >}}

左の図は底だけ違う 3 種類の対数曲線で、いずれも `x = 1` で 0 を通り、形は同じです（互いに定数倍の関係）。右の図は `exp(x)` と `log(x)` を同じ座標に描いたもので、直線 `y = x` に対して鏡像になっています。互いに逆関数なので、`exp(log(x)) = x` と `log(exp(x)) = x` が成り立ちます。

定義域・値域の対応関係も重要で、`log` は正の数 `(0, ∞)` から実数全体 `(-∞, ∞)` へ、`exp` は実数全体から正の数 `(0, ∞)` へ、それぞれ全単射に写ります。

---

### 代数的性質: 積を和に、冪を倍に

対数の最重要性質は次の 3 式です。

- `log(x y) = log(x) + log(y)`（積→和）
- `log(x / y) = log(x) - log(y)`（商→差）
- `log(x^k) = k log(x)`（冪→倍数）

可視化すると次のようになります。

```python
xs = np.linspace(0.5, 50, 200)
fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
axes[0].plot(xs, xs * 5, color="#7aa6c2", lw=2, label="5x")
axes[0].plot(xs, xs * 10, color="#e15759", lw=2, label="10x")
axes[0].plot(xs, xs * 50, color="#59a14f", lw=2, label="50x")
axes[0].set_title("Linear scale: scaling is multiplicative")
axes[1].plot(xs, np.log(xs * 5), color="#7aa6c2", lw=2)
axes[1].plot(xs, np.log(xs * 10), color="#e15759", lw=2)
axes[1].plot(xs, np.log(xs * 50), color="#59a14f", lw=2)
axes[1].set_title("Log scale: scaling becomes additive (parallel lines)")
plt.savefig("log_products_to_sums.svg", bbox_inches="tight")
```

{{< figure src="log_products_to_sums.svg" alt="左の線形スケールでは 5x、10x、50x の 3 本の傾きが違って開いていき、右で log を取ると 3 本が同じ形のまま縦に平行にずれる" caption="対数を取ると倍率の違いが平行移動に変わる" align="center" >}}

左の線形スケールでは「5 倍」「10 倍」「50 倍」が傾きの違いとして発散していくのに対し、右の log スケールでは 3 本が同じ形を保ったまま縦方向に平行にずれています。これは `log(k x) = log(k) + log(x)` の式そのもので、倍率が平行移動に変わります。

対数の性質は、次の 3 つの処理に使います。

- 大きく桁が違う特徴量の前処理: 収入・売上・人口など正値で右に裾の長い分布は `log1p(x)` を取ると左右対称に近づくことが多く、線形モデルが扱いやすくなる（[歪度](../skewness/) のノート参照）
- 尤度の最大化を log-likelihood の最大化に置き換える: `Π_i p_i` を最大化する代わりに `Σ_i log(p_i)` を最大化する。積は和になり、最適化が安定化する
- 情報量・エントロピーの定義: `-log(p)` がイベントの「驚き」を表す自然な単位として現れる

---

### log-odds（対数オッズ）と logit / sigmoid

確率 `p ∈ (0, 1)` のオッズ（odds）を `p / (1 - p)` で定義します。`p = 0.5` でオッズは 1、`p = 0.9` でオッズは 9、`p = 0.99` でオッズは 99 となります。オッズの対数を取った `log(p / (1 - p))` を log-odds または logit と呼びます。

`logit(p) = log(p / (1 - p))`

逆向きに、log-odds `z` から確率 `p` を取り戻す関数がシグモイド（sigmoid, logistic function）です。

`sigmoid(z) = 1 / (1 + exp(-z))`

両者は互いに逆関数の関係にあり、合わせると「`logit` で `(0, 1)` を `(-∞, ∞)` に伸ばし、`sigmoid` で `(-∞, ∞)` を `(0, 1)` に押し戻す」変換となります。

```python
z = np.linspace(-6, 6, 400)
p = 1.0 / (1.0 + np.exp(-z))
p_grid = np.linspace(0.001, 0.999, 400)
logodds = np.log(p_grid / (1 - p_grid))

fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
axes[0].plot(z, p, color="#7aa6c2", lw=2)
axes[0].set_title("Sigmoid: maps log-odds z to probability p\np = 1 / (1 + exp(-z))")
axes[1].plot(p_grid, logodds, color="#e15759", lw=2)
axes[1].set_title("Logit: maps probability p back to log-odds\nz = log(p / (1 - p))")
plt.savefig("sigmoid_logit.svg", bbox_inches="tight")
```

{{< figure src="sigmoid_logit.svg" alt="左はシグモイドの S 字曲線で z = 0 で p = 0.5 を通る。右は logit で p = 0.5 で 0 を通り、p が 0 や 1 に近づくと発散する" caption="シグモイドと logit の対応" align="center" >}}

左のシグモイドは `z = 0` で `p = 0.5` を通り、`z` が大きくなると `p` は 1 に飽和、`z` が小さくなると 0 に飽和する S 字形となります。右の logit は `p = 0.5` で 0 を通り、`p` が 0 や 1 に近づくと急激に発散します。同じ「確率を 0.1 動かす」操作でも、`0.4` から `0.5` への変化は log-odds で約 +0.41、`0.8` から `0.9` への変化は約 +0.81 であり、`p = 0.5` 付近の方が動かしやすい性質が読み取れます。

ロジスティック回帰は、特徴量の線形和 `z = w · x + b` を log-odds として扱い、シグモイド関数で確率に変換します。確率を直接線形和でモデル化すると `(0, 1)` の制約があるため扱いにくくなります。log-odds なら値域が実数全体になるので、線形和と素直につながります。

---

### log 空間で計算する: 数値安定性

確率は 0〜1 の間の値で、これを多数掛け合わせると浮動小数点で 0 に潰れます（underflow）。`0.99^800 ≈ 3.2 × 10^-4` はまだ問題ありません。一方で `0.5` を掛け続けると、1023 回目で float64 の最小正規化数（約 2.2 × 10^-308）を下回ります。そこから精度の落ちた subnormal（非正規化数）を経て、1075 回目で `0.0` になります。

対数を取ると、積 `Π_i p_i` は和 `Σ_i log(p_i)` に変わります。和の絶対値はサンプル数 `n` に比例して増える程度なので、float64 で扱える範囲に収まります。

```python
n_steps = np.arange(1, 1800)
p_each = 0.5
prod = np.cumprod(np.full_like(n_steps, p_each, dtype=float))
log_sum = np.cumsum(np.full_like(n_steps, np.log(p_each), dtype=float))

fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
axes[0].plot(n_steps, prod, color="#e15759", lw=2)
axes[0].set_yscale("symlog", linthresh=1e-100)
axes[0].set_title("Direct product: underflows to 0 for many samples")
axes[1].plot(n_steps, log_sum, color="#7aa6c2", lw=2)
axes[1].set_title("Log-sum: stays representable even for huge n")
plt.savefig("log_numerical_stability.svg", bbox_inches="tight")
```

{{< figure src="log_numerical_stability.svg" alt="左は 0.5 の累積積で、1075 個目で 0.0 に落ちる。右は log(0.5) の累積和で、1800 個近くまで直線的に下がり続ける" caption="確率の積と log の和の比較" align="center" >}}

左の図では、確率の累積積が 1075 個目で `0.0` になります。一方で右の図の累積和は線形に下がり、1500 個でも `1500 × log(0.5) ≈ -1039.7` です。この値は float64 で表せるので、尤度の比較や最大化は log のまま行います。ただし、ここから `exp` で確率に戻すと、元の積と同じく `0.0` になります。

<br>

log の性質で分解できるのは積だけで、確率の和は分解できません。混合モデルの周辺尤度 `p(x) = Σ_k p(x, z_k)` や softmax の分母では、log 空間で持っている値 `a_k = log p_k` から `log(Σ_k exp(a_k))` を求めます。`a_k` が -1000 程度だと、`exp(a_k)` が全て `0.0` になり、和の log は `-inf` になります。

[SciPy](https://scipy.org/) の [`scipy.special.logsumexp`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.special.logsumexp.html) や [`torch.logsumexp`](https://docs.pytorch.org/docs/stable/generated/torch.logsumexp.html) は、この計算を数値安定に行う関数です。考え方は、最大値 `m` を括り出して `log(Σ_k exp(a_k)) = m + log(Σ_k exp(a_k - m))` とすることです。`exp` の引数が 0 以下になり、最大の項は `exp(0) = 1` なので、和が 0 に潰れません。

```python
from scipy.special import logsumexp

print(np.exp(1500 * np.log(0.5)))  # log の和を確率に戻す

a = np.array([-1000.0, -1001.0, -1002.0])  # log p_k
print(np.log(np.sum(np.exp(a))))   # 確率に戻してから足す
m = a.max()
print(m + np.log(np.sum(np.exp(a - m))))  # 最大値を括り出す
print(logsumexp(a))
print(np.exp(a - logsumexp(a)))    # softmax
```

```text
0.0
-inf
-999.5923940355556
-999.5923940355556
[0.66524096 0.24472847 0.09003057]
```

2 行目では `RuntimeWarning: divide by zero encountered in log` の警告も出ます。最大値を括り出した計算と `logsumexp` は同じ値で、`exp(a - logsumexp(a))` は softmax の確率になります。1 つ目の確率は約 0.665 で、log 空間の差 1 が確率の比 `e ≈ 2.72` 倍に対応します。以上は NumPy 2.5.4、SciPy 1.18.1 で実行した結果です。

最尤推定、[EM アルゴリズム](https://doi.org/10.1111/j.2517-6161.1977.tb01600.x)（Expectation-Maximization、期待値最大化法）、隠れマルコフモデル、[ナイーブベイズ](https://scikit-learn.org/stable/modules/naive_bayes.html)、交差エントロピー損失は、いずれも「log を取ってから足し算」で実装され、確率の和が必要な所で `logsumexp` を使います。

---

### 数学での使いどころ

- 微積分の道具: `log` の微分は `1/x`、`exp` の微分は `exp(x)` 自身（極めて扱いやすい）
- 連続複利の極限: `lim (1 + x/n)^n = exp(x)`
- 情報理論: エントロピー `H(X) = -Σ p(x) log p(x)`、相互情報量、KL ダイバージェンス
- 微分方程式: `dy/dx = ky` の解は `y = C exp(kx)`（指数成長・崩壊の原型）
- 対数尺度: 桁が大きく変動する量（地震マグニチュード、pH、音圧、log-fold change）

---

### 機械学習での使いどころ

- 多クラス分類の softmax: クラスごとの線形和 `z_k` を `exp` で正に、和で割って確率にする
- 最尤推定 / [損失関数](/ml/ml/loss-functions/): 交差エントロピー `-Σ y log(p)`（log-loss）や対数尤度は、すべて log を経由する
- 学習率スケジュール: 指数減衰 `lr_t = lr_0 × γ^t` で学習率を時間とともに下げる
- 大規模言語モデルの損失: トークン列の同時確率を `Σ log p(token_t | ...)` で計算

---

### 適さないケース / 落とし穴

- 0 や負の値に log を取れない: `log(0)` は `-∞`、負の値の log は実数で定義されない。`p = 0` の確率を扱う時は `log(p + ε)` のように小さな値 ε を足す
- 解釈が直感的でない: log-odds や対数スコアの値そのものを読み解くのは慣れが必要。提示する時は exp で戻して確率にする方が伝わる
- 単位の意味が変わる: log で変換した特徴量は元の単位を持たない（`log(売上)` の係数 `0.3` は「売上が 1% 増えると目的変数が約 0.003 動く」という意味で、目的変数も log を取った場合に限り「1% 増えると 0.3% 動く」という弾力性の解釈になる）
- log 変換は値の差を圧縮する: 外れ値の影響を抑える効果がある一方で、本当に大事な差を見えにくくすることもある。回帰の残差プロットを確認して変換の要否を判断する
- 底の取り違え: `np.log` は自然対数、`np.log10` は底 10 で、[`math.log`](https://docs.python.org/3/library/math.html#math.log) は底を省略すると自然対数になる。一方で、Excel の [`LOG` 関数](https://support.microsoft.com/en-us/office/log-function-4e82f196-1ca9-4747-8fb0-6c4a3abb3280)は底を省略すると 10 になるので、計算式を移す時に値が変わる
