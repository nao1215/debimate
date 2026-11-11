---
title: "相関係数"
date: 2026-05-24
draft: false
series: ["機械学習ノート", "Mathematics"]
tags: ["machine-learning", "math", "statistics"]
weight: 9
topics: ["Mathematics（数学の基礎）"]
---

相関係数は、2 つの変数の関係の強さを -1 から +1 の 1 つの数で要約する指標です。線形関係を測る Pearson 相関係数と、順位の単調関係を見る [Spearman](https://doi.org/10.2307/1412159) / [Kendall](https://doi.org/10.1093/biomet/30.1-2.81) 相関係数があります。[標準化](../../ml/standardization/) や [PCA](../../ml/pca/)、[特徴量選択](../../ml/feature-selection/)、EDA（探索的データ分析）の起点として広く使われます。

ただし、相関係数が高くても予測に役立つとは限らず、因果関係を示すわけでもありません。0 でも無関係とは限りません。

<br>

本記事では、共分散から Pearson 相関係数を導き、形が全く違うのに同じ値になる 4 つのデータと、外れ値 1 点で符号が逆転する例を計算して、相関係数の読み方を説明します。

---

### 共分散から相関係数へ

相関係数の土台となる量が共分散（covariance）です。共分散は [分散](../variance/) を 2 変数に拡張したもので、2 変数を同時に観測した時の [同時分布](../joint-marginal-conditional/) を要約する量と見ることもできます。

- 定義: `cov(X, Y) = E[(X - mu_x)(Y - mu_y)]`
- `mu_x` と `mu_y` はそれぞれ `X` と `Y` の[平均](../mean/)
- 同じ変数どうしの共分散: `cov(X, X) = Var(X)`（1 変数の分散と一致）

共分散は正なら同じ方向、負なら逆方向に動く傾向を表します。ただし、`X` がメートル、`Y` がキログラムなら単位は「メートル × キログラム」になり、他のペアと大きさを比べても意味がありません。

そこで共分散を両者の[標準偏差](../stddev/) で割って正規化したものが Pearson 相関係数です。

- Pearson 相関: `r = cov(X, Y) / (sigma_x * sigma_y)`

正規化により `r` は -1 から +1 の範囲に収まり、単位に依存しない無次元量になります。

---

### Pearson 相関係数

Pearson 相関係数（Pearson correlation, r）は、2 変数の線形な関係の強さを表します。

- `r = +1`: 完全な正の線形関係（散布図が右上がりの直線）
- `r = -1`: 完全な負の線形関係（散布図が右下がりの直線）
- `r = 0`: 線形関係が無い（散布図がランダム、または非線形に並んでいる）

以下は、正の相関・無関係・負の相関の 3 組を 200 点ずつ作り、[NumPy の `corrcoef`](https://numpy.org/doc/stable/reference/generated/numpy.corrcoef.html) で `r` を求めるコードです。

```python
import numpy as np

rng = np.random.default_rng(0)
n = 200
x1 = rng.normal(size=n)
y1 = 0.8 * x1 + rng.normal(scale=0.4, size=n)   # 正の相関
x2 = rng.normal(size=n)
y2 = rng.normal(size=n)                          # 無関係
x3 = rng.normal(size=n)
y3 = -0.8 * x3 + rng.normal(scale=0.4, size=n)  # 負の相関

for name, x, y in [("Positive", x1, y1), ("None", x2, y2), ("Negative", x3, y3)]:
    print(f"{name:<8} r={np.corrcoef(x, y)[0, 1]:+.2f}")
```

```text
Positive r=+0.88
None     r=-0.05
Negative r=-0.87
```

{{< figure src="correlation_scatter.svg" alt="200 点ずつの散布図を 3 枚並べた図。左は右上がりの r = +0.88、中央は形の無い r = -0.05、右は右下がりの r = -0.87" caption="正の相関・無関係・負の相関の散布図" align="center" >}}

無関係に作った組でも、有限のサンプルでは偶然の偏りが残るので `r` はちょうど 0 にならず -0.05 です。

`r` の絶対値は、0.7 以上で強い、0.4〜0.7 で中程度、0.4 未満で弱い相関と慣習的に呼ばれます。ただし、サンプルが大きい（例: n > 1000）と[統計的に有意](../hypothesis-test/)でも実用上は弱い相関があり、少ない（例: n < 30）と高相関でも偶然の可能性があります。本記事の図は [Matplotlib](https://matplotlib.org/) で描いており、[生成コード](https://github.com/nao1215/debimate/blob/main/projects/ml/scripts/notes/correlation_gen.py)は GitHub で確認できます。

---

### 同じ r でも形が違う 4 つのデータ

`r` だけを見て判断すると、データの形を見落とします。統計学者 Frank Anscombe が論文「[Graphs in Statistical Analysis](https://doi.org/10.1080/00031305.1973.10478966)」（1973 年）で示した Anscombe の四つ組（Anscombe's quartet）は、11 点ずつの 4 つのデータで、平均・分散・相関係数・回帰直線がほぼ同じになります。

```python
import numpy as np

x = np.array([10, 8, 13, 9, 11, 14, 6, 4, 12, 7, 5], dtype=float)
x4 = np.array([8, 8, 8, 8, 8, 8, 8, 19, 8, 8, 8], dtype=float)
data = {
    "I": (x, [8.04, 6.95, 7.58, 8.81, 8.33, 9.96, 7.24, 4.26, 10.84, 4.82, 5.68]),
    "II": (x, [9.14, 8.14, 8.74, 8.77, 9.26, 8.10, 6.13, 3.10, 9.13, 7.26, 4.74]),
    "III": (x, [7.46, 6.77, 12.74, 7.11, 7.81, 8.84, 6.08, 5.39, 8.15, 6.42, 5.73]),
    "IV": (x4, [6.58, 5.76, 7.71, 8.84, 8.47, 7.04, 5.25, 12.50, 5.56, 7.91, 6.89]),
}

for name, (xs, ys) in data.items():
    ys = np.array(ys)
    r = np.corrcoef(xs, ys)[0, 1]
    slope, intercept = np.polyfit(xs, ys, 1)
    print(f"{name:<3} mean_y={ys.mean():.2f} var_y={ys.var(ddof=1):.2f} "
          f"r={r:.3f} y={slope:.2f}x+{intercept:.2f}")

# III の外れ値 (x=13, y=12.74) を除く
xs, ys = data["III"][0], np.array(data["III"][1])
keep = ys != 12.74
print(f"III without outlier: r={np.corrcoef(xs[keep], ys[keep])[0, 1]:.4f}")
```

```text
I   mean_y=7.50 var_y=4.13 r=0.816 y=0.50x+3.00
II  mean_y=7.50 var_y=4.13 r=0.816 y=0.50x+3.00
III mean_y=7.50 var_y=4.12 r=0.816 y=0.50x+3.00
IV  mean_y=7.50 var_y=4.12 r=0.817 y=0.50x+3.00
III without outlier: r=1.0000
```

数値の要約はほぼ同じですが、散布図の形は全く違います。赤い破線は回帰直線です。

{{< figure src="correlation_anscombe.svg" alt="Anscombe の四つ組の散布図 4 枚。どれも r ≈ 0.816 で同じ回帰直線（赤い破線）を持つが、I は直線的、II は曲線、III は 1 点だけ外れた直線、IV は x = 8 の縦の並びと 1 点の外れ値" caption="Anscombe の四つ組" align="center" >}}

- I: 素直な線形関係で、`r` を信じてよい
- II: 放物線のような曲線で、直線では表現できない
- III: 10 点が完全な直線に乗り、1 点だけ外れている。外れ値を除くと `r = 1.0000` になる
- IV: x は 1 点を除いてすべて 8 で、残りの 1 点（x = 19）が回帰直線の傾きを決めている。その 1 点を除くと x が一定になり、`r` は計算できない

`r ≈ 0.816` から 4 つの違いは読み取れないので、特徴量を選ぶ時も散布図で形を確認します。

---

### 相関係数の落とし穴

#### 1. 相関係数 ≠ 予測精度

`r = 0.8` の特徴量でも、単独で目的変数を高精度に予測できるとは限りません。切片付きの単回帰（1 つの特徴量による[線形回帰](../../ml/linear-regression/)）を最小二乗法で当てはめた場合、同じデータでの[決定係数](../../ml/regression-metrics/)は `R² = r² = 0.64` で、目的変数の分散の 64% しか説明できません。残り 36% は別の要因です。四つ組の IV のように 1 点が `r` を作っている場合は、予測力はほとんどありません。

<br>

#### 2. 相関係数 ≠ 因果関係

アイスクリームの売上と溺死事故件数、子どもの靴のサイズと読解力は、正の相関が出る例としてよく挙げられます。共通の第三因子（前者は気温、後者は年齢）が両方を動かしているだけなら、片方を増減させても他方は動きません。因果関係を調べるには、介入実験、操作変数法、DAG（Directed Acyclic Graph、有向非巡回グラフ）、傾向スコアマッチングなどの因果推論の枠組みが必要です。

<br>

#### 3. 相関 0 ≠ 関係が無い

Pearson 相関は線形性しか測らないので、`r = 0` でも完全に決まった非線形関係があり得ます。ただし、`r` が 0 になるかは x の分布にも依存します。

```python
import numpy as np

rng = np.random.default_rng(0)
cases = {
    "x^2, x in [-1, 1]": rng.uniform(-1, 1, 10_000),
    "x^2, x in [0, 2]": rng.uniform(0, 2, 10_000),
}
for name, x in cases.items():
    print(f"{name:<20} r={np.corrcoef(x, x ** 2)[0, 1]:+.2f}")
x = rng.uniform(-np.pi, np.pi, 10_000)
print(f"{'cos, x in [-pi, pi]':<20} r={np.corrcoef(x, np.cos(x))[0, 1]:+.2f}")
```

```text
x^2, x in [-1, 1]    r=-0.01
x^2, x in [0, 2]     r=+0.97
cos, x in [-pi, pi]  r=+0.01
```

`y = x²` は x が 0 を中心に左右対称に分布すると `r ≈ 0` になります。左半分の右下がりと右半分の右上がりが打ち消し合うからです。同じ `y = x²` でも x が 0〜2 だけなら単調に増えるので `r = 0.97` になります。`y = cos(x)` も `-π〜π` では `r ≈ 0` です。

非線形の関係を検出したい場合は、Spearman / Kendall（単調性）、[相互情報量](../information-theory/)（mutual information）、距離相関（distance correlation）を併用し、散布図も確認します。

---

### Spearman と Kendall の順位相関

Pearson が「値そのものの線形関係」を見るのに対し、Spearman や Kendall は「順位（ランク）の関係」を見る相関係数です。

- Spearman 相関: 各値を順位に変換してから Pearson を計算する。一直線でなくても、増える／減るが一貫する単調関係なら +1 / -1 に近づく
- Kendall 相関: 2 点の組をすべて取り、x と y の大小の向きが一致する組と食い違う組の数の差から計算する

以下は、単調だが曲がった関係（a）と、直線的な 30 点に外れ値を 1 点だけ足したデータ（b）で、3 つの相関係数を [SciPy](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.pearsonr.html) の `pearsonr`・[`spearmanr`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.spearmanr.html)・[`kendalltau`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.kendalltau.html) で比べるコードです。

```python
import numpy as np
from scipy import stats


def three(x, y):
    return (stats.pearsonr(x, y)[0], stats.spearmanr(x, y)[0],
            stats.kendalltau(x, y)[0])


# (a) 単調に増えるが、直線ではない
rng = np.random.default_rng(0)
xa = rng.normal(size=200)
ya = np.exp(2 * xa)

# (b) 直線的な 30 点に、外れ値を 1 点だけ足す
rng = np.random.default_rng(0)
xb = rng.normal(size=30)
yb = xb + rng.normal(scale=0.5, size=30)
xb_out = np.append(xb, 10.0)
yb_out = np.append(yb, -10.0)

for name, x, y in [("(a) exp(2x)", xa, ya),
                   ("(b) 30 points", xb, yb),
                   ("(b) + outlier", xb_out, yb_out)]:
    p, s, k = three(x, y)
    print(f"{name:<14} Pearson={p:+.2f} Spearman={s:+.2f} Kendall={k:+.2f}")
```

```text
(a) exp(2x)    Pearson=+0.70 Spearman=+1.00 Kendall=+1.00
(b) 30 points  Pearson=+0.83 Spearman=+0.84 Kendall=+0.64
(b) + outlier  Pearson=-0.70 Spearman=+0.67 Kendall=+0.53
```

{{< figure src="correlation_spearman_kendall.svg" alt="左は y = exp(2x) の単調な曲線で Pearson 0.70・Spearman と Kendall 1.00。右は直線的な 30 点に (10, -10) の外れ値を足したデータで、Pearson だけが -0.70 に反転する" caption="曲線と外れ値での 3 つの相関係数" align="center" >}}

（a）は x が増えれば y も必ず増えるので Spearman・Kendall とも 1.00 ですが、曲線なので Pearson は 0.70 に留まります。（b）では、`r = +0.83` の 30 点に右下の外れ値（10, -10）を 1 点足しただけで、Pearson は -0.70 と符号が逆転します。順位相関は外れ値も「x が最大で y が最小の 1 点」としてしか扱わないので、Spearman 0.67・Kendall 0.53 と正の向きを保ちます。

なお、同じデータでも Kendall は Spearman より小さい値になりやすく（b の 30 点で 0.84 と 0.64）、両者を同じ目安で比べることはできません。使い分けの目安は次の通りです。

- 線形関係が前提で、外れ値が少ないなら Pearson
- 単調関係が前提、または外れ値が混ざるなら Spearman
- 大小の向きが一致する組の割合として解釈したい、サンプルが小さいなら Kendall

---

### 相関行列の可視化

特徴量が多い場合は、すべての組の相関を並べた相関行列を作り、ヒートマップにすると相関の強い組を色で確認できます。以下は [scikit-learn の iris データセット](https://scikit-learn.org/stable/modules/generated/sklearn.datasets.load_iris.html)の 4 特徴量（萼片・花弁の長さと幅）で、[pandas の `DataFrame.corr`](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.corr.html) を使って相関行列を求めるコードです。

```python
from sklearn.datasets import load_iris

df = load_iris(as_frame=True).frame.iloc[:, :4]
df.columns = ["sepal_len", "sepal_wid", "petal_len", "petal_wid"]
print(df.corr().round(2))
```

```text
           sepal_len  sepal_wid  petal_len  petal_wid
sepal_len       1.00      -0.12       0.87       0.82
sepal_wid      -0.12       1.00      -0.43      -0.37
petal_len       0.87      -0.43       1.00       0.96
petal_wid       0.82      -0.37       0.96       1.00
```

{{< figure src="correlation_matrix_heatmap.svg" alt="iris データセットの 4 特徴量の相関行列ヒートマップ。赤が正、青が負の相関で、petal_len と petal_wid の 0.96 が最も濃い" caption="iris の相関行列" align="center" >}}

赤が正、青が負の相関で、色の濃さが強さを表します。petal_len と petal_wid の相関は 0.96 と極めて高く、事実上同じ情報です。線形モデルでは [多重共線性](../../ml/regularization/) の原因になるので、片方を落とすか [PCA](../../ml/pca/) で集約する判断材料になります。ヒートマップは [seaborn の `heatmap`](https://seaborn.pydata.org/generated/seaborn.heatmap.html) でも描けます。

---

### 利点と欠点

利点は次の通りです。

- 符号と大きさで関係の方向と強さが分かる
- 計算が軽く、相関行列で多変量の関係を一度に俯瞰できる
- 単位やスケールに依存しない

欠点は次の通りです。

- Pearson は非線形関係を見逃す（落とし穴 3）
- Pearson は外れ値の影響が大きく、1 点で符号が変わることもある（Spearman と Kendall の節の b）
- 因果関係を示すことはできない（落とし穴 2）
- カテゴリ変数には直接使えない（Cramér's V などで代替）。順序尺度なら Spearman / Kendall を使う

---

### 機械学習での使いどころ

- 特徴量どうしの冗長性や多重共線性の確認（線形関係なら Pearson、単調関係なら Spearman / Kendall）
- [PCA](../../ml/pca/) や線形モデルの前処理で、次元削減の必要性を判断する
- EDA での仮説づくり（外れ値や歪みが強い場合は順位相関を使う）
