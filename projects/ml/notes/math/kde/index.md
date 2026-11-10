---
title: "カーネル密度推定（KDE）"
date: 2026-05-24
draft: false
series: ["機械学習ノート", "Mathematics"]
tags: ["machine-learning", "math", "statistics"]
weight: 8
topics: ["Mathematics（数学の基礎）"]
---

カーネル密度推定（Kernel Density Estimation, KDE）は、データ点の集まりから滑らかな分布曲線を推定するノンパラメトリックな手法です。各データ点に小さな山（カーネル）を置き、全点の山を足し合わせて全体の形を作ります。曲線の面積は 1 になるように正規化されるので、出力は確率密度関数として読めます。

ヒストグラムはビン幅と区切りの位置で形が変わります。KDE はビンを使わず、バンド幅という連続的なパラメータで滑らかさを調整します。EDA（探索的データ分析）で分布の山の数や偏りを掴む時によく使います。

<br>

本記事では、KDE の式を 1 点ずつのカーネルの和として確かめた後、バンド幅の選び方、クラスごとの分布の比較、適さないケースを説明します。コードは図の計算部分です。描画を含む[生成コード](https://github.com/nao1215/debimate/blob/main/projects/ml/scripts/notes/kde_gen.py)も保存しています。

---

### 数式と直感

KDE の式は次の通りです。

```text
f(x) = (1 / (n * h)) * Σ K((x - x_i) / h)
```

- `n`: データ点の数
- `x_i`: 各データ点
- `h`: バンド幅（bandwidth）。個々のカーネルの広がり
- `K`: カーネル関数。面積が 1 の山で、ガウス関数が最も一般的

ガウスカーネルなら、各データ点 `x_i` に中心が `x_i`、標準偏差が `h` の正規分布を置き、それらを全部足してから `n` で割る操作です。サンプル 15 点、`h = 0.5` で計算します。

```python
import numpy as np

sample = np.random.default_rng(5).normal(0, 1, 15)
xs = np.linspace(-4, 4, 400)
h = 0.5
kde = np.zeros_like(xs)
for xi in sample:
    k = np.exp(-0.5 * ((xs - xi) / h) ** 2) / (h * np.sqrt(2 * np.pi))
    kde += k / len(sample)  # 1 点分のカーネルを n で割って足す
print(f"面積: {np.trapezoid(kde, xs):.3f}")
```

```text
面積: 1.000
```

{{< figure src="kde_per_point_intuition.svg" alt="黒い点が 15 個のデータ点、青い細い曲線が各点のガウスカーネル（n で割った後）、赤い曲線がその総和の KDE。点が密集した所で赤い曲線が高い" caption="1 点ごとのカーネルと、その総和の KDE 曲線" align="center" >}}

黒い点がデータ点、青い細い曲線が各点のカーネル（`n` で割った後）で、その総和が赤い曲線です。点が密集している所では青いカーネルが重なるため、赤い曲線が高くなります。

同じ計算を標準正規分布の 500 点に `h = 0.4` で当て、ヒストグラムと重ねると次の通りです。

{{< figure src="kde_example.svg" alt="標準正規分布から引いた 500 点のヒストグラムに、h = 0.4 の KDE 曲線を重ねた図" caption="500 点のヒストグラムと KDE（h = 0.4）" align="center" >}}

---

### バンド幅の選び方

KDE の見え方を最も大きく変えるのはバンド幅 `h` です。2 峰性のデータ（中心 -2 と 2 に 200 点ずつ）で、`h` を 3 通りに変え、曲線の山の数を [scipy.signal.find_peaks](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.find_peaks.html) で数えます。[scipy.stats.gaussian_kde](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.gaussian_kde.html) の `bw_method` はデータの標準偏差に掛ける倍率なので、`h` を標準偏差で割って渡します。

```python
import numpy as np
from scipy import stats
from scipy.signal import find_peaks

rng = np.random.default_rng(0)
data = np.concatenate([rng.normal(-2.0, 0.8, 200), rng.normal(2.0, 0.8, 200)])
xs = np.linspace(-5, 5, 400)
for h in [0.1, 0.5, 2.0]:
    kde = stats.gaussian_kde(data, bw_method=h / data.std())
    peaks, _ = find_peaks(kde(xs))
    print(f"h={h}: 山の数 {len(peaks)}")
```

```text
h=0.1: 山の数 15
h=0.5: 山の数 2
h=2.0: 山の数 1
```

{{< figure src="kde_bandwidth.svg" alt="2 峰性のデータに h = 0.1、0.5、2.0 の KDE を重ねた図。h = 0.1 は小さな山が多数残り、h = 0.5 は 2 つの山、h = 2.0 は 1 つの山に潰れる" caption="バンド幅 h による KDE の形の違い" align="center" >}}

- `h=0.1`: 個々の点の小山が残り、元の分布に無い山が 15 個現れる（過小平滑、under-smoothing）
- `h=0.5`: 2 つの山が分かれて見える
- `h=2.0`: 山が 1 つに潰れ、2 峰性が分からない（過剰平滑、over-smoothing）

<br>

`h` を決める代表的な方法は次の通りです。

- Scott の規則: `h = σ * n^(-1/(d+4))`（`σ` はデータの標準偏差、`d` は次元数）。`gaussian_kde` の既定
- 正規分布を仮定した目安: 1 次元で `h = 1.06 * σ * n^(-1/5)`。`gaussian_kde` の `"silverman"` は 1 次元でこの値になる。Silverman が勧める `0.9 * min(σ, IQR / 1.34) * n^(-1/5)`（IQR は四分位範囲）とは別物
- [交差検証](../../ml/cross-validation/): 学習に使わなかったデータの対数尤度が最も大きくなる `h` を選ぶ

同じ 2 峰性データで、規則による値と、[scikit-learn の KernelDensity](https://scikit-learn.org/stable/modules/generated/sklearn.neighbors.KernelDensity.html) を 5 分割の交差検証（[GridSearchCV](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.GridSearchCV.html)）で選んだ値を比べます（上のコードの続き）。

```python
from sklearn.model_selection import GridSearchCV, KFold
from sklearn.neighbors import KernelDensity

for rule in ["scott", "silverman"]:
    kde = stats.gaussian_kde(data, bw_method=rule)
    h = kde.factor * data.std(ddof=1)
    print(f"{rule}: h={h:.2f}, 山の数 {len(find_peaks(kde(xs))[0])}")

grid = GridSearchCV(
    KernelDensity(),
    {"bandwidth": np.arange(0.05, 2.01, 0.05)},
    cv=KFold(5, shuffle=True, random_state=0),
).fit(data[:, None])
print(f"交差検証: h={grid.best_params_['bandwidth']:.2f}")
```

```text
scott: h=0.64, 山の数 2
silverman: h=0.68, 山の数 2
交差検証: h=0.25
```

規則の値は交差検証の約 2.5 倍です。規則が使う σ には 2 つの山の間の距離も含まれるからです。scipy のドキュメントも、自動の選び方は単峰の分布向けで、多峰の分布は平滑しすぎる傾向があると書いています。今回は規則の値でも山は 2 つ残りました。交差検証の値も分割で変わり、`random_state` を 0〜2 にすると 0.20〜0.30 でした。

既定値もライブラリで異なり、`KernelDensity` は `bandwidth=1.0` の固定値、[seaborn の kdeplot](https://seaborn.pydata.org/generated/seaborn.kdeplot.html) は Scott の規則です。1 枚だけ描いて判断せず、複数の `h` で山の数と位置を比べます。

---

### カーネル関数の選び方

カーネル `K(u)` には複数の選択肢があります。

| カーネル | 特徴 |
|---|---|
| ガウス（Gaussian） | 最も標準的。滑らかで微分可能 |
| Epanechnikov | 平均積分二乗誤差の意味で最適。範囲が有限なので遠い点を計算から外せる |
| Tophat（uniform） | 箱型。距離 `h` 未満の点だけを等しい重みで数える |
| Triangular（linear） | 三角形。距離に比例して重みが減る |

scipy のドキュメントにも、推定結果への影響はカーネルの形よりバンド幅の方がはるかに大きいとあります。特別な理由が無ければガウスカーネルで十分です。

---

### クラスごとの KDE

クラスごとに KDE を重ね描きすると、ある特徴量がクラスをどの程度分けているかが分かります。非解約 420 人（平均 35 歳）と解約 180 人（平均 48 歳）の年齢を作り、2 本の曲線が交わる年齢を求めます。

```python
import numpy as np
from scipy import stats

rng = np.random.default_rng(2)
class0 = rng.normal(35, 8, 420)   # 非解約
class1 = rng.normal(48, 10, 180)  # 解約
kde0, kde1 = stats.gaussian_kde(class0), stats.gaussian_kde(class1)
ages = np.linspace(10, 80, 701)
diff_density = kde1(ages) - kde0(ages)
diff_count = len(class1) * kde1(ages) - len(class0) * kde0(ages)
print("密度が逆転する年齢:", ages[np.flatnonzero(np.diff(np.sign(diff_density)))])
print("人数が逆転する年齢:", ages[np.flatnonzero(np.diff(np.sign(diff_count)))])
```

```text
密度が逆転する年齢: [40.5]
人数が逆転する年齢: [46.8]
```

{{< figure src="kde_class_conditional.svg" alt="非解約（青、平均 35 歳）と解約（赤、平均 48 歳）の年齢の KDE を重ねた図。2 本の曲線は大きく重なり、40.5 歳付近で交わる" caption="クラスごとの年齢の分布を KDE で重ねた図" align="center" >}}

解約者の分布は高齢側に寄っていますが、重なりも大きく、年齢だけではクラスを分けられません。

2 本の曲線は、それぞれのクラスの中で面積を 1 にしています。赤が青を上回るのは 40.5 歳からですが、解約者の人数が上回るのは 46.8 歳からでした。解約者が全体の 3 割だからです。曲線はクラスを条件とした密度 `P(x | y)` で、解約する確率 `P(y | x)` を読むにはクラスの比率 `P(y)` を掛けます（[ベイズの定理](../bayes-theorem/)）。

---

### 機械学習での使いどころ

- EDA: 特徴量や回帰の目的変数の分布を見て、多峰性や[歪度](../skewness/)から対数変換などの前処理を検討する。[平均](../mean/)や[標準偏差](../stddev/)だけでは多峰性は見えない
- [異常検知](/ml/ml/anomaly-detection/): 正常データの密度を推定し、密度の低い点を異常とする。平均 ± 3σ より分布の形を反映できる
- サンプルの生成: 推定した密度から新しいデータを引く。[scikit-learn の例](https://scikit-learn.org/stable/auto_examples/neighbors/plot_digits_kde_sampling.html)は、64 次元の手書き数字を [PCA](../../ml/pca/) で 15 次元にしてから KDE を当てている

---

### 適さないケース

- サンプル数が少ない（数十件以下）: 曲線の形もバンド幅の選び方も不安定になる
- 下限がある値（金額など `x ≥ 0` のもの）: カーネルが 0 未満にはみ出し、境界付近の密度が低く出る。境界で折り返す反射法などで補正する
- 次元に対してサンプルが少ないデータ: 次元が増えると各点の近くに入る点が急に減り（[次元の呪い](/ml/ml/curse-of-dimensionality/)）、同じ精度に必要なサンプル数が急増する。PCA などで次元を減らしてから当てる
- 大規模データの高速な評価: 素朴な実装では 1 点の評価に全データ点との計算が要る。scikit-learn は木構造と許容誤差で計算を減らしている
