---
title: "四分位点（分位点）"
date: 2026-05-24
draft: false
series: ["機械学習ノート", "Mathematics"]
tags: ["machine-learning", "math", "statistics"]
weight: 4
topics: ["Mathematics（数学の基礎）"]
---

四分位点（quartile）は、データを小さい順に並べて「4 等分する位置」の値を取り出した代表値です。[中央値](../median/) を「2 等分する位置」と捉えると、四分位点はその拡張になっています。

- 第 1 四分位点（Q1）: 下位 25% の位置の値
- 第 2 四分位点（Q2）: 50% の位置の値（[中央値](../median/) と同じ）
- 第 3 四分位点（Q3）: 下位 75% の位置の値

これを任意の割合 `q` に一般化したものが分位点（quantile）です。式では、x 以下の値の割合 `F(x) = P(X <= x)`（分布関数）が `q` 以上になる最小の `x` を q 分位点と呼びます。四分位点は `q = 0.25, 0.5, 0.75` の場合です。

<br>

本記事では、四分位点から作る箱ひげ図、IQR（四分位範囲）による外れ値判定、分位点を予測する分位回帰の 3 つを Python の実行結果で確かめます。

---

### 用語整理: quantile / percentile / quartile

分位点は、データを分ける数で呼び分けます。

| 用語 | 範囲 | 例 |
|---|---|---|
| quartile（四分位点） | 4 等分（25% / 50% / 75%） | Q1, Q2, Q3 |
| quintile（五分位点） | 5 等分（20% / 40% / 60% / 80%） | 上位 20% の境界など |
| decile（十分位点） | 10 等分（10%, 20%, ..., 90%） | 所得分布の比較で頻出 |
| percentile（百分位点） | 100 等分（1%〜99%） | 試験成績の上位何 %、検査値の参照範囲 |
| quantile（分位点） | 任意の比率 `q ∈ [0, 1]` | `q = 0.95` で 95% 点 |

機械学習や統計では quantile が一般的な呼び方で、[NumPy](https://numpy.org/) の [`np.quantile(data, 0.25)`](https://numpy.org/doc/stable/reference/generated/numpy.quantile.html) も任意の比率を取ります。

---

### 右に長い分布で四分位点を見る

対数正規分布から 500 点を作り、四分位点を [Matplotlib](https://matplotlib.org/) で描きます。

```python
import numpy as np
import matplotlib.pyplot as plt

# 右に長い分布を作る（対数正規分布）
rng = np.random.default_rng(0)
values = rng.lognormal(mean=1.0, sigma=0.6, size=500)

q1, q2, q3 = np.quantile(values, [0.25, 0.5, 0.75])
print(f"Q1={q1:.2f} Q2={q2:.2f} Q3={q3:.2f} mean={values.mean():.2f}")

# ヒストグラム + 四分位点
plt.figure(figsize=(6, 4))
plt.hist(values, bins=30, color="#7aa6c2", edgecolor="white")
for q, label, color in [(q1, "Q1", "#f28e2b"), (q2, "Q2 (median)", "#e15759"), (q3, "Q3", "#59a14f")]:
    plt.axvline(q, color=color, linestyle="--", linewidth=2)
    plt.text(q, plt.ylim()[1] * 0.9, label, rotation=90, va="top", ha="right", color=color)
plt.title("Histogram with Quartiles")
plt.xlabel("Value")
plt.ylabel("Count")
plt.tight_layout()
plt.show()

# 箱ひげ図（showmeans=True で平均を三角で描く）
plt.figure(figsize=(6, 2.5))
plt.boxplot(values, orientation="horizontal", showmeans=True)
plt.title("Boxplot (Q1, median, Q3)")
plt.xlabel("Value")
plt.tight_layout()
plt.show()
```

出力:

```text
Q1=1.78 Q2=2.64 Q3=4.10 mean=3.20
```

{{< figure src="quartile_hist.svg" alt="対数正規分布から作った 500 点のヒストグラムに、Q1 = 1.78、Q2（中央値）= 2.64、Q3 = 4.10 の破線を重ねた図。Q2 から Q3 までの間隔が Q1 から Q2 までより広い" caption="四分位点を重ねたヒストグラム" align="center" >}}

{{< figure src="quartile_box.svg" alt="同じ 500 点の横向きの箱ひげ図。箱の両端が Q1 と Q3、中のオレンジの線が中央値、緑の三角が平均で、右のひげの外に外れ値の候補の丸が並ぶ" caption="同じデータの箱ひげ図" align="center" >}}

Q1〜Q2 は 0.86、Q2〜Q3 は 1.46 で、上側の方が広く散らばっています。四分位点の間隔から分布の偏りが分かります。平均（3.20）が中央値（2.64）より大きいのは、右側の大きな値に平均が引っ張られるためです。

箱ひげ図（boxplot）は四分位点を 1 本にまとめた図で、[`boxplot`](https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.boxplot.html) の既定では次のように描きます。

- 箱の両端 = Q1・Q3（箱の長さが次節の IQR）
- 箱の中のオレンジの線 = 中央値、緑の三角 = 平均
- ひげ = `Q1 - 1.5 * IQR` 以上の最小値から `Q3 + 1.5 * IQR` 以下の最大値まで
- ひげの外の丸 = 外れ値の候補

中央値・散らばり・外れ値が 1 枚で分かるので、A/B やカテゴリ別の分布を並べて比べる時に使います。山が 2 つある分布でも箱は 1 つなので、形はヒストグラムで確かめます。

---

### IQR（四分位範囲）と外れ値判定

IQR（Interquartile Range、四分位範囲）は、中央 50% のデータが収まる幅です。

```text
IQR = Q3 - Q1
```

[標準偏差](../stddev/) と並ぶ散らばりの指標で、順位で決まるので外れ値の影響を受けにくい特徴があります。ただし影響が無いわけではなく、極端な値が加わると順位がずれて Q1・Q3 も少し動きます。

IQR を物差しにした外れ値判定が Tukey の方法（IQR ルール）です。Q1・Q3 から IQR の 1.5 倍外側に境界（フェンス）を引き、その外を外れ値とみなします。

- 下側の外れ値: `x < Q1 - 1.5 * IQR`
- 上側の外れ値: `x > Q3 + 1.5 * IQR`

正規分布の 200 点に極端な値を 5 個混ぜ、標準偏差と IQR の変化と、係数 1.5・3.0 の判定を比べます。前のコードの `rng` と `values` を続けて使います。

```python
base = rng.normal(50, 8, 200)
data = np.concatenate([base, [10, 15, 95, 110, 130]])

for name, d in [("before", base), ("after", data)]:
    a, b = np.quantile(d, [0.25, 0.75])
    print(f"{name}: IQR={b - a:.2f} std={d.std():.2f}")

q1, q3 = np.quantile(data, [0.25, 0.75])
iqr = q3 - q1
for k in (1.5, 3.0):
    lo, hi = q1 - k * iqr, q3 + k * iqr
    flagged = data[(data < lo) | (data > hi)]
    print(f"k={k}: fence=[{lo:.1f}, {hi:.1f}] flagged={np.sort(flagged).tolist()}")

# 右に長い values に同じルールを当てる
v1, v3 = np.quantile(values, [0.25, 0.75])
v_iqr = v3 - v1
print(f"lognormal: lower={(values < v1 - 1.5 * v_iqr).sum()} "
      f"upper={(values > v3 + 1.5 * v_iqr).sum()} of {len(values)}")
```

出力:

```text
before: IQR=10.61 std=7.63
after: IQR=11.26 std=11.35
k=1.5: fence=[27.6, 72.7] flagged=[10.0, 15.0, 95.0, 110.0, 130.0]
k=3.0: fence=[10.7, 89.5] flagged=[10.0, 95.0, 110.0, 130.0]
lognormal: lower=0 upper=19 of 500
```

{{< figure src="quantile_iqr_outliers.svg" alt="正規分布の 200 点に 5 個の極端な値を混ぜたデータ。緑の帯が IQR、赤い破線が係数 1.5 のフェンスで、フェンスの外の 10・15・95・110・130 の 5 点が × で示されている" caption="IQR ルールで上下の外れ値を検出した結果" align="center" >}}

緑の帯が IQR、赤い破線が係数 1.5 のフェンスで、外側の 5 点が × です。出力から次の 3 点が読み取れます。

- 5 個を混ぜると標準偏差は 7.63 から 11.35 へ約 1.5 倍になった。IQR は 10.61 から 11.26 で、約 6% の変化に留まる
- 係数 3.0 ではフェンスが広がり、15 が外れ値から外れた。係数を大きくするほど判定は緩くなる。1.5 は経験則で、理論上の根拠がある値ではない
- 対数正規分布では 19 点が全て上側で判定された。歪んだ分布では、外れ値ではなく裾そのものに印が付く。箱ひげ図のひげの右に並ぶ丸が、この 19 点にあたる

正規分布では係数 1.5 のフェンスが平均から約 2.7σ の位置に来るので、外れ値の無いデータでも約 0.7% に印が付きます。平均 ± 3σ を境界にする 3σ ルール（0.27%）より多い割合です。3σ ルールは外れ値で膨らんだ標準偏差を使うので、外れ値が多いほど境界ごと広がります。一方で IQR ルールも、上記の対数正規分布の例の通り、分布の形を問わず使える基準ではありません。

---

### 分位回帰で「予測区間」を作る

分位回帰（quantile regression）は、平均ではなく特定の分位点（10%、50%、90% など）を予測する回帰手法です。予測が実測を下回った誤差に `q`、上回った誤差に `1 - q` の重みを掛けた損失（pinball loss）を最小にします。`q = 0.9` なら下回る罰が 9 倍重く、9 割の点が予測値より下に来る位置で釣り合います。`q = 0.5` は誤差の絶対値に比例する損失で、[中央値](../median/) を予測します。

低分位と高分位の予測を上下に並べると、予測区間（prediction interval）として読めます。`x` が大きいほどノイズが大きいデータ（不均一分散）に、[scikit-learn](https://scikit-learn.org/) の [`GradientBoostingRegressor`](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.GradientBoostingRegressor.html)（[勾配ブースティング](../../ml/gradient-boosting/)）で `q = 0.1, 0.5, 0.9` を当てはめ、学習データと、同じ式で新しく作った 5000 点で 80% 区間に収まる割合を数えます。

```python
from sklearn.ensemble import GradientBoostingRegressor

rng2 = np.random.default_rng(7)
x = np.linspace(0, 10, 200)
y = np.sin(x) * 3 + 0.5 * x + rng2.normal(0, 0.2 + 0.3 * x, 200)
X = x.reshape(-1, 1)

def fit(q):
    return GradientBoostingRegressor(loss="quantile", alpha=q, n_estimators=100,
                                     max_depth=3, random_state=0).fit(X, y)

q_low, q_med, q_high = fit(0.1), fit(0.5), fit(0.9)

inside = (q_low.predict(X) <= y) & (y <= q_high.predict(X))
print(f"train coverage: {inside.mean():.0%}")

rng3 = np.random.default_rng(99)
x_new = rng3.uniform(0, 10, 5000)
y_new = np.sin(x_new) * 3 + 0.5 * x_new + rng3.normal(0, 0.2 + 0.3 * x_new)
X_new = x_new.reshape(-1, 1)
inside_new = (q_low.predict(X_new) <= y_new) & (y_new <= q_high.predict(X_new))
print(f"new data coverage: {inside_new.mean():.0%}")
```

出力:

```text
train coverage: 79%
new data coverage: 64%
```

{{< figure src="quantile_regression_bands.svg" alt="x が大きいほどノイズが大きい 200 点に、分位回帰の中央値の予測（赤い線）と q = 0.1 から q = 0.9 の 80% 予測区間（緑の帯）を重ねた図。帯は右ほど広く、右端では個々の点を追って尖る" caption="分位回帰で得た中央値と 80% 予測区間" align="center" >}}

赤い線が中央値の予測、緑の帯が `q = 0.1` 〜 `q = 0.9` の 80% 予測区間で、ノイズに合わせて右ほど広がっています。

ところが学習データでは狙い通り 79% が帯に収まったのに、新しいデータでは 64% でした。図の右端で帯が個々の点を追って尖っているように、200 点に合わせ込んだ境界は新しいデータには狭すぎます。区間が本当に 80% を含むかは、学習に使っていないデータで確かめます。

在庫計画・需要予測・SLA（Service Level Agreement、サービス品質の合意）設計では、`q = 0.95` のような片側の予測値を安全マージンに使います。この場合も検証データで 95% を満たすかを確認します。

---

### 機械学習での使いどころ

- データの把握: EDA（Exploratory Data Analysis、探索的データ分析）で [pandas の `describe()`](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.describe.html) が出す 25% / 50% / 75% を見る
- 外れ値の除外・クリッピング: フェンスの外を除くか、フェンスの値に切り詰める
- ロバストな[標準化](../../ml/standardization/): [`RobustScaler`](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.RobustScaler.html) は中央値を引いて IQR で割る
- 異常スコアの閾値: スコアの 99% 点などを閾値に使う
- 評価の報告: 予測誤差や A/B テストの結果を Q1・Q3 でも示し、典型的な幅や分布の変化を伝える

---

### 注意点

- データは小さい順に並べられる必要がある（順序尺度以上）
- 点数が少ないと計算方法で値が変わる。`[1, 2, ..., 8]` の Q1 は、`np.quantile` の既定 `method="linear"` で 2.75、`lower` で 2、`midpoint` で 2.5 になる。ツール間で比べる時は方法を揃える
- 四分位点だけでは、山の数など分布の形は分からない
- 並べ替えた要約なので時系列の変化は消える。時間ごとに分けて計算する
