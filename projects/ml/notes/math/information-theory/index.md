---
title: "情報理論 - 目的変数と無関係な ID の列でも、相互情報量は上限の H(Y) に届く"
date: 2026-05-26
draft: false
series: ["機械学習ノート", "Mathematics"]
tags: ["machine-learning", "math", "statistics", "information-theory"]
weight: 15
topics: ["Mathematics（数学の基礎）"]
---

情報理論（information theory）は、Claude Shannon が 1948 年の論文 [A Mathematical Theory of Communication](https://doi.org/10.1002/j.1538-7305.1948.tb01338.x) で築いた、不確かさや情報の量を数える枠組みです。機械学習では、分類の損失、決定木の分割の基準、[特徴量の選択](../../ml/feature-selection/)、データの分布の比較に出てきます。

特徴量の選択で使う相互情報量は、ある列の値を知ると、目的変数がどれだけ当てられるようになるかを数える量です。値が大きい列ほど、目的変数について多くの情報を持つと読みます。

目的変数との相互情報量が大きい順に列を並べたとします。上位に顧客 ID・郵便番号・商品コードのような値の種類が多い列が来たら、その列で目的変数を予測できるのでしょうか。目的変数と無関係な列を足して計算すると分かります。

以下は、[scikit-learn](https://scikit-learn.org/stable/) に同梱の [breast_cancer](https://scikit-learn.org/stable/modules/generated/sklearn.datasets.load_breast_cancer.html) で、目的変数と各列の相互情報量を [`mutual_info_score`](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.mutual_info_score.html) で計算した結果です。breast_cancer は、乳がんの細胞核の画像から測った 30 列で、569 件の腫瘍が良性か悪性かを当てるデータです。

`mutual_info_score` は、同じ値を持つ行を数えて計算します。連続の値をそのまま渡すとほぼ全ての行が別の値になるので、breast_cancer の 30 列は件数が同じになるように 10 個の区間に区切りました。そこに目的変数と無関係な乱数の列を足し、その列のカテゴリの数を 2 から 569 まで変えています。

{{< figure src="it_cover.webp" alt="横軸は乱数の列のカテゴリ数 2〜569（対数目盛）、縦軸は目的変数との相互情報量。灰色の横線は breast_cancer の 30 列の値で、最大は worst perimeter の 0.475。赤い線の乱数の列は、カテゴリ数 100 で 0.092、200 で 0.223、400 で 0.475 と上がり、569 では上限の H(Y) = 0.660 に届く。青い線の AMI は、どのカテゴリ数でも 0 付近で水平" caption="目的変数と無関係な乱数の列の相互情報量（breast_cancer、カテゴリ数ごとに 20 回の平均）" align="center" >}}

乱数の列は、カテゴリが 200 個で breast_cancer の 30 列のうち 17 列を上回りました。569 個、つまり行ごとに違う ID になると、どの列より大きい 0.660 になります。0.660 は目的変数のエントロピー `H(Y)` で、相互情報量はこれより大きくなりません。

上位に来た列で目的変数を予測できるとは限りません。値の種類が多い列は、目的変数と無関係でも相互情報量が偶然で大きく出ます。この分を引いた AMI という値では、乱数の列はどのカテゴリ数でも 0 付近のままでした。

<br>

本記事では、ML の説明に出てくるエントロピー・KL ダイバージェンス・相互情報量を自分で計算して確認したい人と、scikit-learn で特徴量の選択や分布の比較に使う人に向けて、次の疑問に答えます。

- エントロピーは何を数え、nat と bit は何が違うのか。
- KL ダイバージェンスは、なぜ向きで値が変わり、inf になるのか。
- 交差エントロピーを下げると、何が下がるのか。
- 相互情報量は、ID の列でなぜ上限に届くのか。
- 独立な列でも、相互情報量はどれだけ出るのか。
- 偶然の分は、どう取り除けばよいのか。
- 分布の比較に使う PSI では、何が起きるのか。

実験は scikit-learn 1.9.1、[NumPy](https://numpy.org/) 2.5.4、[SciPy](https://scipy.org/) 1.18.1、[pandas](https://pandas.pydata.org/) 3.1.1 で行いました。図を描く処理も含めた完全なコードは [information-theory_gen.py](https://github.com/nao1215/debimate/blob/main/projects/ml/scripts/notes/information-theory_gen.py) にあります。

---

### エントロピー: 驚きの大きさの平均

確率 `p` で起きる事象を観測した時の驚きの大きさは、自己情報量 `-log p` で表します。確実に起きる事象では 0 で、珍しい事象ほど大きくなります。log の底を 2 にすると単位は bit、自然対数にすると nat で、1 nat は約 1.443 bit です。底の取り違えやすさは[対数・指数と log-odds](../log-exp-logodds/) で取り上げています。

エントロピーは、自己情報量を確率で重み付けした平均です。

`H(X) = -Σ_x P(x) log P(x)`

値の出方が偏っていて次の値を当てられるほど小さく、どの値も同じくらい出て予測しづらいほど大きくなります。底を 2 にした値は、`X` の値を 0 と 1 の並びで表す時に、1 回あたり平均で何 bit 要るかの下限にもなります。Shannon の論文が示した、情報源符号化定理です。

冒頭の目的変数のエントロピーを計算します。

```python
import numpy as np
from scipy.stats import entropy
from sklearn.datasets import load_breast_cancer

bc = load_breast_cancer()
X, y = bc.data, bc.target
p = np.bincount(y) / len(y)
print("クラスの割合（悪性, 良性）:", p.round(3))
print("H(Y) =", (-(p * np.log(p)).sum()).round(3), "nat =", (-(p * np.log2(p)).sum()).round(3), "bit")
print("scipy.stats.entropy:", entropy(p).round(3))
```

```text
クラスの割合（悪性, 良性）: [0.373 0.627]
H(Y) = 0.66 nat = 0.953 bit
scipy.stats.entropy: 0.66
```

{{< figure src="it_entropy.webp" alt="左は横軸が事象の確率 p、縦軸が自己情報量 -log2 p の曲線で、p = 1 で 0 bit、0.5 で 1 bit、1/8 で 3 bit と、p が小さいほど急に大きくなる。右は 2 クラスのうち一方の割合を横軸にしたエントロピーの山形の曲線で、半々で最大の 0.693 nat（1 bit）。breast_cancer の目的変数は良性 0.627 の位置で 0.660 nat" caption="自己情報量と、2 クラスのエントロピー" align="center" >}}

目的変数は良性が 62.7% で、エントロピーは 0.660 nat です。半々なら上限の `log 2 = 0.693` nat、つまり 1 bit で、良性に偏っている分だけ少し下がっています。SciPy の [`entropy`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.entropy.html) と scikit-learn の情報量の関数は、既定で自然対数を使うので、本記事の値は全て nat です。

[決定木](../../ml/decision-tree/)で `criterion="entropy"` を指定すると、分割の前後でこのエントロピーがどれだけ下がるかで分割を選びます。下がった量を情報利得と呼び、後の節の相互情報量と同じものです。

---

### KL ダイバージェンス: 向きのある分布の差

2 つの分布 `P` と `Q` の差を測る量が、[KL ダイバージェンス](https://doi.org/10.1214/aoms/1177729694)（Kullback-Leibler divergence）です。

`KL(P || Q) = Σ_x P(x) log(P(x) / Q(x))`

`P` に従って出る値について、`Q` に従うと思って作った符号で表すと、1 回あたり平均でこれだけ余分に長くなる、と読めます。`P` と `Q` が同じなら 0 で、違うほど大きくなり、負にはなりません。

式の重みは `P(x)` だけなので、`P` と `Q` を入れ替えると値が変わります。また、`Q(x) = 0` なのに `P(x) > 0` の値があると、`log(P(x) / 0)` が無限大になります。SciPy の `entropy` は、2 つ目の分布を渡すと KL を返します。

```python
P = np.array([0.25, 0.25, 0.25, 0.25])
Q = np.array([0.4, 0.3, 0.2, 0.1])
R = np.array([0.5, 0.3, 0.2, 0.0])  # 4 つ目の値が一度も出ていない分布
for a, b, la, lb in [(P, Q, "P", "Q"), (P, R, "P", "R")]:
    print(f"KL({la} || {lb}) = {entropy(a, b):.3f}   KL({lb} || {la}) = {entropy(b, a):.3f}  （nat）")
```

```text
KL(P || Q) = 0.122   KL(Q || P) = 0.106  （nat）
KL(P || R) = inf   KL(R || P) = 0.357  （nat）
```

{{< figure src="it_kl.webp" alt="2 枚の棒グラフ。左は一様な P と偏った Q で、KL(P || Q) = 0.122、KL(Q || P) = 0.106。右は一様な P と、値 4 の確率が 0 の R で、KL(P || R) = inf、KL(R || P) = 0.357" caption="向きを入れ替えた KL ダイバージェンス" align="center" >}}

`Q` との比較では、向きを入れ替えても 0.122 と 0.106 で近い値です。`R` では片方の向きだけが inf になりました。`R` は、値 4 が手元のデータに一度も出なかった時に、値ごとの件数を全体の件数で割って作った分布です。件数が少ないと、この割合に 0 が出ることは珍しくありません。この 0 が分布の比較でどんな問題になるかは、後の PSI の節で扱います。

<br>

#### 交差エントロピーとの関係

分類の損失に使う交差エントロピーは、エントロピーと KL の和に分かれます。

`H(P, Q) = -Σ_x P(x) log Q(x) = H(P) + KL(P || Q)`

`P` は正解の分布、`Q` はモデルが出した確率です。`H(P)` はモデルを変えても動かないので、交差エントロピーを下げることは `KL(P || Q)` を下げることと同じです。正解のクラスだけ確率 1 にした one-hot の分布では `H(P) = 0` なので、交差エントロピーは KL と一致し、1 件ごとの損失は `-log Q(正解のクラス)` です。正解のクラスに 0.9 を出しても、損失は 0.105 nat 残ります。

[損失関数](../../ml/loss-functions/)の交差エントロピーが下げているのは、正解率ではなく、出した確率と正解の分布の差です。`Q` が 0 に丸められて損失が inf になる問題と、その避け方は[対数・指数と log-odds](../log-exp-logodds/) の実験で確認しています。

---

### 相互情報量: 列を知ると減るエントロピー

2 つの変数 `X` と `Y` の相互情報量（mutual information）は、次の式です。

`I(X; Y) = H(Y) - H(Y | X)`

`H(Y | X)` は条件付きエントロピーで、`X` の値ごとに `Y` のエントロピーを計算し、`X` の各値が出る割合で平均したものです。`X` を知った後でも `Y` がどれだけ予測しづらいかを表し、相互情報量はそこまでに減った分です。同じ量は、[同時分布](../joint-marginal-conditional/)と、独立だと仮定した周辺分布の積の KL としても書けます。

`I(X; Y) = KL(P(x, y) || P(x) P(y))`

KL なので 0 以上で、`X` と `Y` が独立な時だけ 0 になります。Pearson の[相関係数](../correlation/)は直線的な関係しか測れませんが、相互情報量は曲がった関係も数えます。以下のコードは、値の組ごとの件数を数えて相互情報量を計算し、`mutual_info_score` と比べます。

```python
import pandas as pd
from sklearn.metrics import mutual_info_score

rng = np.random.default_rng(0)
names = list(bc.feature_names)
wp = pd.qcut(X[:, names.index("worst perimeter")], 10, labels=False)  # 10 個に区切った列
row_id = rng.permutation(len(y))                                     # 行ごとに違う ID


def mi_by_hand(y, x):
    joint = pd.crosstab(y, x).to_numpy() / len(y)  # 同時分布 P(y, x)
    py, px = joint.sum(axis=1), joint.sum(axis=0)  # 周辺分布
    nz = joint > 0
    return (joint[nz] * np.log(joint[nz] / np.outer(py, px)[nz])).sum()


for name, col in [("worst perimeter（10 区間）", wp), ("行ごとの ID", row_id)]:
    print(f"{name}: 手で計算 {mi_by_hand(y, col):.3f}、mutual_info_score {mutual_info_score(y, col):.3f}、"
          f"H(X) {entropy(np.bincount(col)):.3f}")
```

```text
worst perimeter（10 区間）: 手で計算 0.475、mutual_info_score 0.475、H(X) 2.303
行ごとの ID: 手で計算 0.660、mutual_info_score 0.660、H(X) 6.344
```

{{< figure src="it_venn.webp" alt="2 組の円の図。左の worst perimeter（10 区間）では、赤い H(Y) = 0.660 の円と青い H(X) = 2.303 の円が重なり、重なりが I = 0.475、赤い円の残りが H(Y|X) = 0.185。右の行ごとの ID（569 通り）では、赤い H(Y) の円が青い H(X) = 6.344 の円の内側に収まり、I = 0.660、H(Y|X) = 0.000" caption="目的変数のエントロピーのうち、列を知ると減る分が相互情報量" align="center" >}}

worst perimeter は、画像に写った細胞核の外周の長さのうち、大きい方から 3 つの平均です。10 区間に区切ると、目的変数のエントロピー 0.660 のうち 0.475 を減らし、0.185 が残ります。行ごとの ID では、ID の 1 つの値に 1 行しかありません。そのため ID を知れば目的変数が 1 つに決まり、`H(Y | X) = 0` です。相互情報量は `H(Y)` の 0.660 に届き、上の図の右のように、目的変数の円が丸ごと重なります。

<br>

この計算は、手元の 569 行の中では正しい値です。手元の行に限れば、ID から目的変数を全て当てられます。ただし、新しい行の ID は手元に無いので、何も当てられません。件数を数えて計算する相互情報量は、手元の行でどれだけ当てられるかを表す値で、新しい行で当たるかは表しません。学習データでだけ当たる[過学習](../../ml/overfitting/)と同じ形です。

---

### 独立な列でも 0 にならない量

冒頭の図の実験は、次のコードです。乱数の列は目的変数と独立なので、本当の相互情報量は 0 です。AMI は次の節で説明します。

```python
from sklearn.metrics import adjusted_mutual_info_score

rng = np.random.default_rng(1)
real = np.array([mutual_info_score(y, pd.qcut(X[:, j], 10, labels=False, duplicates="drop"))
                 for j in range(X.shape[1])])
ks = [2, 5, 10, 20, 50, 100, 200, 300, 400, len(y)]
mi_rand, ami_rand = [], []
for k in ks:
    v, a = [], []
    for _ in range(20):
        col = rng.permutation(len(y)) % k  # 0〜k-1 をほぼ同じ数ずつ、無作為に並べた列
        v.append(mutual_info_score(y, col))
        a.append(adjusted_mutual_info_score(y, col))
    mi_rand.append(np.mean(v))
    ami_rand.append(np.mean(a))
    print(f"カテゴリ {k:3d}: 相互情報量 {np.mean(v):.3f}、AMI {np.mean(a):+.3f}、"
          f"これより低い 30 列 {(real < np.mean(v)).sum()} / 30")
```

```text
カテゴリ   2: 相互情報量 0.000、AMI -0.001、これより低い 30 列 0 / 30
カテゴリ   5: 相互情報量 0.004、AMI +0.001、これより低い 30 列 0 / 30
カテゴリ  10: 相互情報量 0.009、AMI +0.001、これより低い 30 列 0 / 30
カテゴリ  20: 相互情報量 0.015、AMI -0.001、これより低い 30 列 3 / 30
カテゴリ  50: 相互情報量 0.044、AMI -0.001、これより低い 30 列 5 / 30
カテゴリ 100: 相互情報量 0.092、AMI -0.003、これより低い 30 列 9 / 30
カテゴリ 200: 相互情報量 0.223、AMI -0.001、これより低い 30 列 17 / 30
カテゴリ 300: 相互情報量 0.356、AMI +0.001、これより低い 30 列 21 / 30
カテゴリ 400: 相互情報量 0.475、AMI +0.002、これより低い 30 列 29 / 30
カテゴリ 569: 相互情報量 0.660、AMI -0.000、これより低い 30 列 30 / 30
```

569 行を 200 個のカテゴリに分けると、1 つのカテゴリは 2〜3 行です。2〜3 行の中の良性の割合は、全体の 62.7% から偶然大きくずれ、0% や 100% にもなります。そのずれの分だけ `H(Y | X)` が `H(Y)` より小さくなり、相互情報量が出ます。相互情報量は KL なので負にならず、偶然のずれは打ち消し合わずに全て正の値として足されます。

<br>

このずれの大きさは、件数とカテゴリの数で決まります。以下は、独立な 2 クラスの目的変数と k カテゴリの列を件数 n で作り、相互情報量の平均を測ったコードです。描画の行は省いています。

```python
rng = np.random.default_rng(2)
ns = [50, 100, 200, 500, 1000, 2000, 5000]
for k in [2, 10, 50]:
    means = []
    for n in ns:
        v = [mutual_info_score(rng.integers(0, 2, n), rng.integers(0, k, n)) for _ in range(300)]
        means.append(np.mean(v))
    print(f"カテゴリ {k:2d}: " + "、".join(f"n={n} {m:.4f}（式 {(k - 1) / (2 * n):.4f}）" for n, m in zip(ns, means)))
```

```text
カテゴリ  2: n=50 0.0096（式 0.0100）、n=100 0.0051（式 0.0050）、n=200 0.0026（式 0.0025）、n=500 0.0009（式 0.0010）、n=1000 0.0005（式 0.0005）、n=2000 0.0002（式 0.0003）、n=5000 0.0001（式 0.0001）
カテゴリ 10: n=50 0.1095（式 0.0900）、n=100 0.0500（式 0.0450）、n=200 0.0233（式 0.0225）、n=500 0.0091（式 0.0090）、n=1000 0.0046（式 0.0045）、n=2000 0.0023（式 0.0022）、n=5000 0.0009（式 0.0009）
カテゴリ 50: n=50 0.4208（式 0.4900）、n=100 0.2828（式 0.2450）、n=200 0.1485（式 0.1225）、n=500 0.0516（式 0.0490）、n=1000 0.0252（式 0.0245）、n=2000 0.0123（式 0.0123）、n=5000 0.0048（式 0.0049）
```

{{< figure src="it_bias.webp" alt="両対数の図。横軸は件数 n の 50〜5000、縦軸は独立な列の相互情報量の平均。2・10・50 カテゴリの 3 本の実線は、どれも件数に反比例して右下がりの直線になり、破線の式 (k - 1)(c - 1) / (2n) とほぼ重なる。50 カテゴリでは件数 50〜200 で実線が破線から少し離れる" caption="独立な列の相互情報量は、カテゴリの数に比例し、件数に反比例する" align="center" >}}

実線は、破線の式 `(k - 1)(c - 1) / (2n)` にほぼ重なります。`c` は目的変数のクラスの数で、ここでは 2 です。カテゴリの数を 10 倍にすると相互情報量もほぼ 10 倍に、件数を 10 倍にすると 10 分の 1 になります。

式の出どころは、[仮説検定](../hypothesis-test/)の 1 つである G 検定です。G 検定は、値の組ごとの件数を並べた表から、2 つの変数が独立かどうかを調べる検定です。その統計量 G は、`2n × I` と同じ値になります。

独立な時、G は自由度 `(k - 1)(c - 1)` の [χ² 分布](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.chi2.html)に近づきます。自由度は、表の行と列の合計を固定した時に自由に決められるマスの数です。χ² 分布の平均は自由度に等しいので、G を `2n` で割った `I` の平均は、上の式のとおりになります。SciPy の [`chi2_contingency`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.chi2_contingency.html) に `lambda_="log-likelihood"` を渡すと G を返すので、同じ値になるかを確認しました。

```python
from scipy.stats import chi2_contingency

n = len(y)
rng = np.random.default_rng(3)
r200 = rng.permutation(n) % 200
g, _, dof, _ = chi2_contingency(pd.crosstab(y, r200), lambda_="log-likelihood")
print(f"200 カテゴリの乱数の列: 2n × 相互情報量 = {2 * n * mutual_info_score(y, r200):.1f}、G = {g:.1f}、自由度 {dof}")
```

```text
200 カテゴリの乱数の列: 2n × 相互情報量 = 251.6、G = 251.6、自由度 199
```

χ² 分布に近づくのは、1 つのカテゴリに十分な行がある時です。上の図の 50 カテゴリ・50 件のように 1 カテゴリが 1 行ほどになると、式から離れます。冒頭の 200 カテゴリも 1 カテゴリが 2〜3 行で、式の 0.175 より大きい 0.223 でした。

---

### 偶然の分を引く: AMI と NMI

scikit-learn には、相互情報量を補正した値が 2 つあります。[`normalized_mutual_info_score`](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.normalized_mutual_info_score.html) の NMI は、相互情報量を `H(X)` と `H(Y)` の平均で割った値です。

[`adjusted_mutual_info_score`](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.adjusted_mutual_info_score.html) の AMI は、各カテゴリの行数を保ったまま値を無作為に並べ替えた時の相互情報量の[期待値](../expectation/)を先に引き、上限が 1 になるように割った値です。割る数は、`H(X)` と `H(Y)` の平均から同じ期待値を引いた値です。

以下のコードは、これまでに作った 3 つの列で 3 つの値を並べ、30 列の NMI とも比べます。`r200` は G 検定のコードで作った 200 カテゴリの乱数の列です。

```python
from sklearn.metrics import normalized_mutual_info_score

for name, col in [("worst perimeter（10 区間）", wp), ("200 カテゴリの乱数", r200), ("行ごとの ID", row_id)]:
    print(f"{name}: MI {mutual_info_score(y, col):.3f}、NMI {normalized_mutual_info_score(y, col):.3f}、"
          f"AMI {adjusted_mutual_info_score(y, col):+.3f}")
real_nmi = np.array([normalized_mutual_info_score(y, pd.qcut(X[:, j], 10, labels=False, duplicates="drop"))
                     for j in range(X.shape[1])])
print(f"NMI が行ごとの ID より低い 30 列: {(real_nmi < normalized_mutual_info_score(y, row_id)).sum()} / 30")
```

```text
worst perimeter（10 区間）: MI 0.475、NMI 0.321、AMI +0.317
200 カテゴリの乱数: MI 0.221、NMI 0.074、AMI -0.002
行ごとの ID: MI 0.660、NMI 0.189、AMI -0.000
NMI が行ごとの ID より低い 30 列: 19 / 30
```

NMI では、行ごとの ID は `H(X)` が 6.344 と大きいので 0.189 まで下がります。それでも、30 列のうち 19 列の NMI より上でした。割るだけでは、偶然の分は消えません。

AMI は乱数の列も ID も 0 になり、worst perimeter は 0.317 残ります。worst perimeter の期待値は 0.008 なので、0.317 は `(0.475 - 0.008) / (1.481 - 0.008)` で、1.481 は `H(X)` の 2.303 と `H(Y)` の 0.660 の平均です。MI から引いた分は小さく、値を下げたのは割った方です。

[階層的クラスタリング](../../ml/hierarchical-clustering/)で 2 つの分け方の一致を測る ARI（Adjusted Rand Index）も、同じ考え方で補正した値です。

<br>

特徴量の選択でよく使う [`mutual_info_classif`](https://scikit-learn.org/stable/modules/generated/sklearn.feature_selection.mutual_info_classif.html) は、既定では列を連続の値として扱います。その場合は件数を数える方法ではなく、[k 近傍法](../../ml/knn/)の距離から推定する方法を使います。Kraskov らの [KSG 推定量](https://doi.org/10.1103/PhysRevE.69.066138)に基づく方法です。`discrete_features=True` を渡すと、件数を数える計算に戻ります。

```python
from sklearn.feature_selection import mutual_info_classif

for name, kw in [("連続の値として（既定）", {}), ("離散の値として", {"discrete_features": True})]:
    v = mutual_info_classif(row_id.reshape(-1, 1), y, random_state=0, **kw)[0]
    print(f"mutual_info_classif、行ごとの ID を{name}: {v:.3f}")
```

```text
mutual_info_classif、行ごとの ID を連続の値として（既定）: 0.000
mutual_info_classif、行ごとの ID を離散の値として: 0.660
```

既定では 0.000 で、離散の値として渡すと 0.660 に戻りました。カテゴリの列を整数に置き換えて離散の値として渡すと、冒頭の図の赤い線と同じ偏りが出ます。

<br>

<details><summary>余談: 並べ替えない行番号には情報がある</summary>

上のコードの ID は、行番号を無作為に並べ替えたものです。並べ替えない行番号 `np.arange(569)` を連続の値として渡すと、`mutual_info_classif` は 0.104 を返しました。breast_cancer の行は、目的変数について均等に並んでいません。57 行ずつ区切って良性の割合を見ると、先頭の区切りは 0.19、最後の区切りは 0.77 でした。行番号から目的変数が少し分かるのは本当で、行の順番に意味がある CSV では、行番号の列が[データリーク](../../ml/data-leakage/)の原因になります。

</details>

<br>

値の種類が多い列が有利になるのは、相互情報量だけではありません。ID3 という決定木を提案した [Quinlan の 1986 年の論文](https://doi.org/10.1007/BF00116251)は、値の種類が多い属性ほど情報利得が大きく出る偏りを取り上げ、それを補正する gain ratio を提案しています。scikit-learn のランダムフォレストの `feature_importances_` が値の種類が多い列を高く出す偏りは、[特徴量の重要度](../../ml/feature-importance/)で検証しています。

---

### 分布の比較: PSI でも同じことが起きる

PSI（Population Stability Index）は、学習時のデータと運用中のデータの分布の変化、つまり[データドリフト](../../mlops/data-drift/)を監視する指標です。値を同じ区間に分け、学習時の割合 `b_i` と運用中の割合 `q_i` から次の式で計算します。

`PSI = Σ_i (q_i - b_i) log(q_i / b_i)`

学習時の分布を `B`、運用中の分布を `Q` とすると、この式は `KL(Q || B) + KL(B || Q)` と同じで、両方の向きの KL を足したものです。[モデル性能の監視](../../mlops/model-performance-monitoring/)では、0.1 と 0.25 を目安に分布の変化を判断しています。

PSI も区間ごとの件数から計算するので、分布が同じでも、相互情報量と同じ偶然のずれで値が出るはずです。

breast_cancer の mean area（細胞核の面積の平均）について、学習用の 398 件を 10 分位で 10 個の区間に分けました。そして同じ 398 件から m 件を取り出して比べる計算を 3000 回繰り返しました。同じ分布から取り出しているので、分布の変化はありません。区間が空の時の 0 は、モデル性能の監視の実験と同じく小さな値 ε に置き換えています。描画の行は省いています。

```python
from sklearn.model_selection import train_test_split

x_tr, _ = train_test_split(X[:, names.index("mean area")], test_size=0.3, random_state=0, stratify=y)
edges = np.quantile(x_tr, np.linspace(0, 1, 11))
edges[0], edges[-1] = -np.inf, np.inf
b = np.histogram(x_tr, edges)[0] / len(x_tr)  # 学習時の 10 区間の割合（どれも約 0.1）
rng = np.random.default_rng(4)


def psi(q, b, eps):
    q, b = np.clip(q, eps, 1), np.clip(b, eps, 1)
    return ((q - b) * np.log(q / b)).sum()


for m in [30, 50, 100, 200, 500, 1000]:
    vals, empty = {e: [] for e in [1e-6, 1e-4, 1e-2]}, []
    for _ in range(3000):
        live = rng.choice(x_tr, m, replace=True)  # 学習時と同じ分布から m 件
        q = np.histogram(live, edges)[0] / m
        empty.append((q == 0).any())
        for e in vals:
            vals[e].append(psi(q, b, e))
    empty, v = np.array(empty), np.array(vals[1e-6])
    print(f"m={m:4d}: 空の区間がある回 {empty.mean():.1%}、空の無い回の PSI の平均 {v[~empty].mean():.3f}"
          f"（(10 - 1) / m = {9 / m:.3f}）、0.1 を超えた回 {(v > 0.1).mean():.1%}")
    if m == 30:
        print("  空の区間がある回の PSI の中央値:",
              "、".join(f"ε={e:g} で {np.median(np.array(x)[empty]):.2f}" for e, x in vals.items()))
```

```text
m=  30: 空の区間がある回 37.4%、空の無い回の PSI の平均 0.261（(10 - 1) / m = 0.300）、0.1 を超えた回 97.6%
  空の区間がある回の PSI の中央値: ε=1e-06 で 1.41、ε=0.0001 で 0.94、ε=0.01 で 0.46
m=  50: 空の区間がある回 5.3%、空の無い回の PSI の平均 0.189（(10 - 1) / m = 0.180）、0.1 を超えた回 85.5%
m= 100: 空の区間がある回 0.0%、空の無い回の PSI の平均 0.095（(10 - 1) / m = 0.090）、0.1 を超えた回 37.9%
m= 200: 空の区間がある回 0.0%、空の無い回の PSI の平均 0.046（(10 - 1) / m = 0.045）、0.1 を超えた回 2.5%
m= 500: 空の区間がある回 0.0%、空の無い回の PSI の平均 0.018（(10 - 1) / m = 0.018）、0.1 を超えた回 0.0%
m=1000: 空の区間がある回 0.0%、空の無い回の PSI の平均 0.009（(10 - 1) / m = 0.009）、0.1 を超えた回 0.0%
```

{{< figure src="it_psi.webp" alt="左は両対数の図で、横軸は比べる側の件数 30〜1000、縦軸は分布が同じ時の PSI の平均。赤い線は (区間の数 - 1) / 件数 の破線にほぼ重なって右下がりになり、0.1 の点線を超えた回の割合は 50 件で 85.5%、100 件で 37.9%、200 件で 2.5%。右は 30 件で空の区間が出た回の PSI の中央値の棒グラフで、0 を置き換える ε が 1e-06 で 1.41、0.0001 で 0.94、0.01 で 0.46" caption="分布が同じ時の PSI と、空の区間が出た時の PSI" align="center" >}}

分布が変わっていないのに、PSI の平均は `(区間の数 - 1) / 件数` にほぼ一致しました。50 件で比べると 85.5% の回で 0.1 を超え、0.1 を目安にすると、変化が無くても 10 回のうち 8 回以上で警告が出ます。0.1 を超える回が 2.5% まで減るのは 200 件からでした。

この式になるのは、独立な列の節の G と同じく、`m × PSI` が自由度 `区間の数 - 1` の χ² 分布に近づくためです。30 件の点が線より下にあるのは、空の区間が出た 37.4% の回を除いて平均したことが効いていると考えられます。空の区間が出る回は PSI が大きく出やすく、その回を外すと平均が下がります。

<br>

30 件では、37.4% の回で空の区間が出ました。空の区間があると運用中の `Q` に 0 ができ、`KL(B || Q)` が inf になります。KL の節で、0 を含む `R` を後ろに置いた `KL(P || R)` が inf になったのと同じです。そのため PSI の値は、0 を置き換える ε でほぼ決まります。上の図の右のとおり、同じデータでも ε が 1e-6 なら 1.41、1e-2 なら 0.46 です。ε は計算のために決めた値で、分布の変化とは関係がありません。

---

### 情報量の値を使う前に確認すること

相互情報量で列を並べたら、上位の列のカテゴリの数と件数を見ます。カテゴリの数 k、クラスの数 c、件数 n から `(k - 1)(c - 1) / (2n)` を計算し、その列の値と比べます。値が式と同じくらいなら、その列の相互情報量は偶然の値でしかない可能性があります。1 カテゴリの行数が少なく式が当てにならない時は、AMI を使うか、目的変数を並べ替えて同じ計算を何度か行い、その値と比べます。

`mutual_info_classif` を使うなら、`discrete_features` の指定を確認します。カテゴリの列を離散の値として渡すと件数を数える計算になり、値の種類が多い列ほど高く出ます。顧客 ID のような識別子は、特徴量に入れるかを先に考えます。[カテゴリ変数のエンコーディング](../../ml/categorical-encoding/)では、ID を集約した特徴量に変える方法を扱っています。

PSI や KL で分布を監視するなら、比べる件数と区間の数から `(区間の数 - 1) / 件数` を出し、目安の値より十分小さいかを調べます。小さくなければ、件数を溜めてから比べるか、区間を減らします。0 を置き換える ε は、値を記録と一緒に残しておくと、後で値を比べられます。

冒頭の図で赤い線が上がったのは、全て偶然の分でした。青い AMI の線が 0 に張り付いたままなのは、その分を引けば、乱数の列には目的変数の情報が何も無いことを示しています。
