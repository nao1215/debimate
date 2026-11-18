---
title: "クラス不均衡 - 重み付けやリサンプリングの効果は、閾値を下げただけのモデルと比べて測る"
date: 2026-05-26
draft: false
series: ["機械学習ノート", "Machine Learning"]
tags: ["machine-learning", "scikit-learn", "imbalance"]
weight: 12
topics: ["Machine Learning（評価・概念・アルゴリズム）"]
---

クラス不均衡（class imbalance）は、分類で見つけたいクラスが全体のごく一部しかない状態です。カードの不正利用、製品の不良、病気の検出がその代表で、見つけたい側を陽性、それ以外を陰性と呼びます。陽性が 2% しかなければ、全てを陰性と答えるだけで正解率は 98% になります。

不正検知や不良品検出のモデルで、正解率は 98% を超えるのに、陽性をほとんど見つけないという場面があります。検索すると、[scikit-learn](https://scikit-learn.org/stable/) の `class_weight="balanced"` と、少ない側の行を人工的に増やす [SMOTE](https://doi.org/10.1613/jair.953) がよく紹介されています。`class_weight="balanced"` は、学習の時に陽性の誤りを陰性より重く数える設定です。どちらも足すと、陽性のうち陽性と判定できた割合である再現率が一気に上がり、問題が解決したように見えます。

先に結論を書くと、本記事の実験では、これらで陽性と陰性を見分ける力は上がりませんでした。大きく動いたのは、モデルが出した確率を陽性・陰性に分ける境目（閾値）と、確率そのものです。

乳房 X 線写真から切り出した 11,183 か所のうち、260 か所（2.3%）だけが微小石灰化で陽性という mammography のデータで、ロジスティック回帰を使って比べました。SMOTE の原論文が実験に使ったデータです。再現率と並べて見る適合率は、陽性と判定した中で本当に陽性だった割合です。

何も対処しないモデルは、以下「そのまま」と呼びます。図に描いた曲線は、閾値を 1 から 0 へ動かしながら、各閾値での再現率と適合率を結んだ線で、曲線上の点 1 つが閾値 1 つに当たります。

{{< figure src="ci_cover.webp" alt="横軸が再現率、縦軸が適合率のグラフに 2 本の曲線がある。濃い青のそのままのロジスティック回帰は PR-AUC 0.615、赤の class_weight=balanced は PR-AUC 0.534 で、赤い曲線はほぼ全域で青い曲線より下にある。青い丸は閾値 0.5 の点で再現率 0.40、適合率 0.78。赤い丸は class_weight の閾値 0.5 の点で再現率 0.85、適合率 0.17。青いひし形は、そのままで閾値を 0.039 まで下げた点で、再現率は赤い丸と同じ 0.85、適合率は 0.22" caption="class_weight の閾値 0.5（赤い丸）と、そのままで閾値を下げた点（青いひし形）" align="center" >}}

ロジスティック回帰に `class_weight="balanced"` を付けると、閾値 0.5 の再現率は 0.40 から 0.85 に上がります。ただ、そのままで閾値を 0.039 に下げても、再現率は同じ 0.85 になり、適合率は 0.17 より高い 0.22 でした。曲線のほぼ全体で、重みを付けた赤い曲線の方が下にあり、曲線より下の面積である PR-AUC は 0.615 から 0.534 に下がりました。

<br>

本記事では、ML を学び始めたエンジニアと、scikit-learn で手元の偏ったデータを扱う人に向けて、次の疑問に答えます。

- 正解率が高いのに、陽性をほとんど見つけないのはなぜか。
- 重み付けと 3 つのリサンプリングで、何の数字が変わるのか。
- 閾値を下げるだけのモデルと比べて、何が違うのか。
- 重みを付けたモデルが出す確率は、そのまま使えるのか。
- 交差検証の前に SMOTE をかけると、何が起きるのか。
- 閾値は、何を基準に決めればよいのか。

実験は scikit-learn 1.9.1 と [imbalanced-learn](https://imbalanced-learn.org/stable/) 0.14.2 で行いました。mammography は imbalanced-learn の [`fetch_datasets`](https://imbalanced-learn.org/stable/references/generated/imblearn.datasets.fetch_datasets.html) が、研究データを公開するサービス [Zenodo](https://zenodo.org/record/61452) から取得します。図を描く処理も含めた完全なコードは [class-imbalance_gen.py](https://github.com/nao1215/debimate/blob/main/projects/ml/scripts/notes/class-imbalance_gen.py) にあります。

---

### 正解率 98% のモデルが見落とす陽性

mammography の 6 列を[標準化](../standardization/)し、[ロジスティック回帰](../logistic-regression/)で陽性の確率を出します。標準化とロジスティック回帰は、前処理とモデルを 1 つにまとめる scikit-learn の `make_pipeline` でつなぎます。

確率は、各行を学習に使わなかったモデルから得るために、データを 5 つに分けて回す[交差検証](../cross-validation/)の関数 [`cross_val_predict`](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.cross_val_predict.html) で求めました。分け方の `StratifiedKFold` は、陽性の割合を分割ごとに揃えます。

```python
import numpy as np
from imblearn.datasets import fetch_datasets
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

data = fetch_datasets(filter_data=("mammography",))["mammography"]
X, y = data.data, (data.target == 1).astype(int)   # 元のラベルは -1 と 1
print(X.shape, "陽性", y.sum(), "件、陽性の割合", round(y.mean(), 4))
print("全部を陰性と答えた時の正解率:", round(1 - y.mean(), 4))

cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=0)


def lr(weight=None):
    return LogisticRegression(class_weight=weight, max_iter=1000)


p_plain = cross_val_predict(make_pipeline(StandardScaler(), lr()), X, y,
                            cv=cv, method="predict_proba")[:, 1]
tn, fp, fn, tp = confusion_matrix(y, p_plain >= 0.5).ravel()
print(f"閾値 0.5: 正解率 {(tn + tp) / len(y):.4f}、陽性と判定 {tp + fp} 件、"
      f"見つけた陽性 {tp} / {tp + fn} 件")
print("陽性の確率の中央値:", round(float(np.median(p_plain[y == 1])), 3),
      " 陰性の確率の中央値:", round(float(np.median(p_plain[y == 0])), 4))
```

```text
(11183, 6) 陽性 260 件、陽性の割合 0.0232
全部を陰性と答えた時の正解率: 0.9768
閾値 0.5: 正解率 0.9835、陽性と判定 134 件、見つけた陽性 105 / 260 件
陽性の確率の中央値: 0.328  陰性の確率の中央値: 0.0017
```

閾値 0.5 の正解率は 0.9835 で、全てを陰性と答えた時の 0.9768 より 0.7 ポイント高いだけです。見つけた陽性は 260 件中 105 件で、再現率は 0.40 でした。予測と正解の組み合わせを 4 つのマスに数える表と、正解率・適合率・再現率の関係は、[混同行列](../confusion-matrix/)で詳しく説明しています。

次の図は、モデルが出した確率を陽性と陰性に分けて数えたものです。件数の差が 42 倍あるので、両方の軸を対数目盛にしています。

{{< figure src="ci_scores.webp" alt="横軸が陽性の確率、縦軸が件数で、どちらも対数目盛のヒストグラム。青い陰性 10923 件は 1e-5 から 1 近くまで広がり、0.002 付近に山がある。赤い陽性 260 件の多くは 0.03 から 1 の間にあり、閾値 0.5 の破線より左にも半分以上が残る。陰性は陽性の割合 0.023 の点線より右で減っていき、閾値 0.5 より右には数十件だけ残る" caption="そのままのロジスティック回帰が出した確率（陽性と陰性）" align="center" >}}

確率の[中央値](../../math/median/)は陽性で 0.328、陰性で 0.0017 で、陽性は陰性よりおよそ 200 倍高い確率をもらっています。ただ、陽性の 6 割は 0.5 に届きません。モデルは陽性を上位に並べられていて、閾値 0.5 がその並びのかなり上の方を切っている、という状態です。このデータでは、クラスに偏りがあっても陽性を見分けられています。

陽性の割合が 2.3% のデータで、確率が 0.5 を超えるのは「陽性の方が陰性より多そうだ」と言える行だけです。陽性と陰性のどちらを外しても同じ痛手だと見るなら、この切り方は正しい判断です。陽性の見落としの方が痛いなら、閾値を下げる必要があります。

---

### 重み付けと 3 つのリサンプリング

偏りへの対処は、学習の時に陽性を重く扱う重み付けと、学習に使う行を増減するリサンプリング（resampling）に分かれます。ここでは次の 4 つを比べます。

| 対処 | 学習の時に起きること |
|---|---|
| `class_weight="balanced"` | 陽性の誤りに、陰性の 42 倍の重みを掛ける |
| ランダムオーバーサンプリング | 重複を許して、陽性の行を陰性と同じ数まで複製する |
| SMOTE | 近くにある陽性 2 件の間に、新しい行を作る |
| ランダムアンダーサンプリング | 陽性と同じ数になるまで、陰性の行を間引く |

`class_weight` は、[損失関数](../loss-functions/)で行ごとの誤りに掛ける重みです。`"balanced"` は、[`LogisticRegression` の文書](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LogisticRegression.html)にあるとおり、各クラスの重みを「全体の行数 ÷ (クラスの数 × そのクラスの行数)」にします。陽性は 11183 ÷ (2 × 260) で 21.5、陰性は 11183 ÷ (2 × 10923) で 0.51 になり、その比が 42 です。

SMOTE（Synthetic Minority Over-sampling Technique）は、陽性の行ごとに、[k 近傍法](../knn/)の考え方で近くの陽性を 5 件選び、そのうちの 1 件と結んだ線分の上に新しい行を作ります。単に複製するより、陽性の領域が広がるという考え方です。ただし、2 件の間に作った行が実際にありうる入力かは、列の意味によります。カテゴリを数値にした列では中間の値に意味が無く、列が多いと[近さの意味そのものが弱まり](../curse-of-dimensionality/)ます。

3 つのリサンプリングは imbalanced-learn の実装を使い、imbalanced-learn の `Pipeline` に入れました。この `Pipeline` は、`make_pipeline` と同じく前処理とモデルをまとめるもので、リサンプリングを学習（`fit`）の時だけ行い、予測の時は何もしません。交差検証の評価に回る行は、元のままです。

```python
from imblearn.over_sampling import SMOTE, RandomOverSampler
from imblearn.pipeline import make_pipeline as make_imb_pipeline
from imblearn.under_sampling import RandomUnderSampler
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import average_precision_score, precision_score, recall_score, roc_auc_score


def hgb(weight=None):
    return HistGradientBoostingClassifier(class_weight=weight, random_state=0)


rows = {}
for model_name, base in [("ロジスティック回帰", lr), ("勾配ブースティング", hgb)]:
    candidates = {
        "そのまま": make_pipeline(StandardScaler(), base()),
        "class_weight": make_pipeline(StandardScaler(), base("balanced")),
        "ランダムオーバー": make_imb_pipeline(StandardScaler(), RandomOverSampler(random_state=0), base()),
        "SMOTE": make_imb_pipeline(StandardScaler(), SMOTE(random_state=0), base()),
        "ランダムアンダー": make_imb_pipeline(StandardScaler(), RandomUnderSampler(random_state=0), base()),
    }
    for name, model in candidates.items():
        p = cross_val_predict(model, X, y, cv=cv, method="predict_proba")[:, 1]
        rows[(model_name, name)] = p
        print(f"{model_name} {name:<10} ROC-AUC {roc_auc_score(y, p):.3f}  "
              f"PR-AUC {average_precision_score(y, p):.3f}  "
              f"閾値 0.5 の再現率 {recall_score(y, p >= 0.5):.3f}  "
              f"適合率 {precision_score(y, p >= 0.5):.3f}  確率の平均 {p.mean():.3f}")
```

ROC-AUC と PR-AUC は、閾値を 1 つに決めずに、陽性を陰性より上に並べられたかを測る指標です。PR-AUC は冒頭の図で曲線より下の面積に当たる値で、でたらめに並べると陽性の割合と同じ 0.023 になります。

PR-AUC は scikit-learn の [`average_precision_score`](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.average_precision_score.html) で計算しました。曲線を台形で区切って面積を求める方法とは値が少し違い、その違いは [ROC-AUC / PR-AUC](../roc-pr-auc/) で扱っています。出力を表にまとめると、次のとおりです。

| モデル | 対処 | ROC-AUC | PR-AUC | 閾値 0.5 の再現率 | 適合率 | 確率の平均 |
|---|---|---|---|---|---|---|
| ロジスティック回帰 | そのまま | 0.919 | 0.615 | 0.404 | 0.784 | 0.023 |
| | class_weight | 0.920 | 0.534 | 0.850 | 0.166 | 0.214 |
| | ランダムオーバー | 0.921 | 0.535 | 0.850 | 0.166 | 0.214 |
| | SMOTE | 0.919 | 0.512 | 0.846 | 0.168 | 0.207 |
| | ランダムアンダー | 0.923 | 0.526 | 0.838 | 0.170 | 0.217 |
| 勾配ブースティング | そのまま | 0.936 | 0.736 | 0.588 | 0.832 | 0.019 |
| | class_weight | 0.919 | 0.720 | 0.708 | 0.667 | 0.053 |
| | ランダムオーバー | 0.917 | 0.712 | 0.708 | 0.634 | 0.053 |
| | SMOTE | 0.927 | 0.730 | 0.769 | 0.541 | 0.064 |
| | ランダムアンダー | 0.944 | 0.601 | 0.892 | 0.216 | 0.146 |

ロジスティック回帰では、4 つの対処のどれでも ROC-AUC は 0.919〜0.923 でほぼ動きません。PR-AUC は 0.615 から 0.51〜0.54 に下がりました。大きく動いたのは閾値 0.5 の再現率と、確率の平均です。

[勾配ブースティング](../gradient-boosting/)の `HistGradientBoostingClassifier` でも、PR-AUC が上がった対処はありません。ランダムアンダーサンプリングは、交差検証の各回で学習側に入る陰性約 8,700 件のうち、陽性と同じ約 210 件、2.4% しか学習に使いません。ROC-AUC は 0.944 に上がった一方で、PR-AUC は 0.601 まで下がりました。

ROC-AUC は、陰性の大半を占める確率の低い行を正しく下に並べるだけで高くなります。陽性と判定した中に陰性が何件混ざるかは PR-AUC に出るので、陽性が少ないデータで上位に並べる力を比べる時、2 つが食い違ったら PR-AUC の方を見ます。

---

### 閾値を下げただけのモデルとの比較

冒頭の図にある青いひし形は、再現率が `class_weight` と並ぶまで、そのままで閾値を 0.0001 ずつ下げて見つけた点です。同じ再現率で、陽性と判定する件数が何件違うかを数えました。

```python
p_bal = rows[("ロジスティック回帰", "class_weight")]
r_bal, q_bal = recall_score(y, p_bal >= 0.5), precision_score(y, p_bal >= 0.5)
for t in np.round(np.arange(0.100, 0.0, -0.0001), 4):     # 再現率が並ぶまで閾値を下げる
    if recall_score(y, p_plain >= t) >= r_bal:
        break
r_low, q_low = recall_score(y, p_plain >= t), precision_score(y, p_plain >= t)
print(f"class_weight、閾値 0.5   : 再現率 {r_bal:.3f}  適合率 {q_bal:.3f}  陽性と判定 {(p_bal >= 0.5).sum()} 件")
print(f"そのまま、閾値 {t:.4f}  : 再現率 {r_low:.3f}  適合率 {q_low:.3f}  陽性と判定 {(p_plain >= t).sum()} 件")
```

```text
class_weight、閾値 0.5   : 再現率 0.850  適合率 0.166  陽性と判定 1330 件
そのまま、閾値 0.0391  : 再現率 0.850  適合率 0.219  陽性と判定 1008 件
```

どちらも陽性を 221 件見つけますが、`class_weight` は 1,330 件を陽性と判定し、そのままで閾値を下げると 1,008 件で済みます。陽性と判定した行を人が 1 件ずつ見る運用なら、`class_weight` の方が 322 件多く、陽性でない行を見ることになります。

<br>

#### 重みは切片をずらす

ロジスティック回帰は、列ごとの係数を掛けて足した値に切片を加え、それを確率に変えます。この足した値は、陽性の確率を[対数オッズ](../../math/log-exp-logodds/)に直したものです。全データで学習し直して、陽性の重みを 42 倍にした時に切片と係数がどう変わったかを比べました。

```python
m_plain = make_pipeline(StandardScaler(), lr()).fit(X, y)
m_bal = make_pipeline(StandardScaler(), lr("balanced")).fit(X, y)
w = (y == 0).sum() / (y == 1).sum()
print(f"陽性の重み ÷ 陰性の重み: {w:.1f}、その対数: {np.log(w):.2f}")
print("切片:", round(float(m_plain[-1].intercept_[0]), 2), "→", round(float(m_bal[-1].intercept_[0]), 2))
print("係数（そのまま）    :", m_plain[-1].coef_[0].round(2))
print("係数（class_weight）:", m_bal[-1].coef_[0].round(2))
```

```text
陽性の重み ÷ 陰性の重み: 42.0、その対数: 3.74
切片: -5.85 → -1.74
係数（そのまま）    : [ 0.28 -0.96 -1.69  1.04  0.65  0.64]
係数（class_weight）: [ 0.61 -0.83 -1.27  0.93  0.7   0.09]
```

切片は -5.85 から -1.74 へ、約 4.1 上がりました。陽性を 42 倍に数えることは、陽性のオッズを 42 倍にすること、つまり対数オッズに log 42 = 3.74 を足すことに近く、切片の変化はそれに近い大きさです。

重みを付けたモデルが確率 0.5 と言う行は、オッズが 1 です。重みで 42 倍になった分を割って戻すと、そのままでのオッズは 1/42 で、確率に直すと 1/(1 + 42) = 0.023 になります。つまり `class_weight` の閾値 0.5 は、そのままで閾値を 0.023 にするのに近く、これは陽性の割合とほぼ同じ値です。

ただし、係数も変わっています。6 列目の係数は 0.64 から 0.09 に縮みました。重みを付けると、陽性と陰性が混ざる辺りの誤りを減らすように、直線の当て方そのものが変わるためと考えられます。その結果として上位の並び順が少し崩れ、PR-AUC が 0.615 から 0.534 に下がったと見られます。

---

### 平均で実際の 9 倍になる確率

表の右端にあるとおり、`class_weight` を付けたロジスティック回帰では確率の平均が 0.214 で、陽性が実際に占める 0.023 の 9 倍です。確率を「この行が陽性である見込み」として使うなら、ここが一番困ります。次の図は、確率を大きさの順に区間へ分け、区間ごとに確率の平均と、実際に陽性だった割合を並べたものです。

{{< figure src="ci_reliability.webp" alt="両対数のグラフで、横軸がモデルの確率の区間平均、縦軸がその区間で実際に陽性だった割合。灰色の破線は確率どおりの線。濃い青のそのままと、緑の補正した class_weight は 0.03 より上でほぼ破線に沿う。赤の class_weight は破線の大きく右にあり、確率 0.63 の区間で実際の陽性は 0.047、確率 0.83 で 0.16 しかない" caption="区間ごとの確率と、実際に陽性だった割合" align="center" >}}

破線より右にある点は、モデルが出した確率が、実際に陽性だった割合より高すぎることを表します。そのまま（濃い青）は、確率 0.03 より上でほぼ破線に沿い、確率 0.13 の区間では 14% が陽性でした。`class_weight`（赤）は、確率 0.63 と言った区間で陽性が 4.7%、0.83 と言った区間でも 16% しかいません。この図の読み方と、ずれた確率を後から直す方法は、[確率の校正](../probability-calibration/)で扱っています。

重みの分が対数オッズのずれなら、確率をオッズに直して 42 で割れば戻せるはずです。これを補正と呼んで、確率の平均と ROC-AUC を比べました。

```python
odds = p_bal / (1 - p_bal)
p_fix = (odds / w) / (1 + odds / w)        # オッズを陽性の重みの倍率 w で割って戻す
for name, p in [("そのまま", p_plain), ("class_weight", p_bal), ("class_weight を補正", p_fix)]:
    print(f"{name:<18} 確率の平均 {p.mean():.4f}  ROC-AUC {roc_auc_score(y, p):.3f}")
print("実際の陽性の割合:", round(y.mean(), 4))
```

```text
そのまま               確率の平均 0.0233  ROC-AUC 0.919
class_weight       確率の平均 0.2138  ROC-AUC 0.920
class_weight を補正   確率の平均 0.0220  ROC-AUC 0.920
実際の陽性の割合: 0.0232
```

補正した確率（緑）の平均は 0.0220 で、実際の割合に戻りました。補正しても確率の大小は入れ替わらないので、ROC-AUC は 0.920 のままです。つまり、`class_weight` で得たのは、閾値を下げたのと近い判定と、実際より高い確率でした。学習した時と本番とで陽性の割合が違う時も、[ベイズの定理](../../math/bayes-theorem/)から同じ形の補正が出てきます。学習時と本番とで陽性の割合をそれぞれオッズにして、その比をオッズに掛けます。

医療の予測モデルでも同じ結果が報告されています。van den Goorbergh 氏らの [2022 年の論文](https://doi.org/10.1093/jamia/ocac093)は、ロジスティック回帰にランダムアンダー・ランダムオーバー・SMOTE をかけると、少数派のクラスに属する確率が大きく過大になり、ROC-AUC は上がらなかったと報告しています。再現率と特異度の釣り合いは良くなりましたが、閾値をずらすだけでも同じ結果が得られた、と結論付けています。

---

### 交差検証より先にかけた SMOTE

リサンプリングを使う時は、かける場所を誤ると評価が実際より大幅に高く出ます。学習用の 70% を取り分けた後、次の 3 つの PR-AUC を比べました。モデルは[ランダムフォレスト](../random-forest/)で、fold は交差検証が分けた 1 つ 1 つの組のことです。

1. 70% 全体に SMOTE をかけてから交差検証する
2. `Pipeline` の中で、各 fold の学習側だけに SMOTE をかけて交差検証する
3. 2 と同じモデルを 70% で学習し、残した 30% で評価する

```python
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score, train_test_split

X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.3, stratify=y, random_state=0)


def rf():
    return RandomForestClassifier(n_estimators=300, random_state=0, n_jobs=4)


X_sm, y_sm = SMOTE(random_state=0).fit_resample(X_tr, y_tr)   # 分ける前に全体へ SMOTE
before = cross_val_score(rf(), X_sm, y_sm, cv=cv, scoring="average_precision").mean()
inside = cross_val_score(make_imb_pipeline(SMOTE(random_state=0), rf()), X_tr, y_tr,
                         cv=cv, scoring="average_precision").mean()   # fold の学習側だけに SMOTE
model = make_imb_pipeline(SMOTE(random_state=0), rf()).fit(X_tr, y_tr)
test = average_precision_score(y_te, model.predict_proba(X_te)[:, 1])
print(f"SMOTE の後に交差検証   : PR-AUC {before:.3f}")
print(f"Pipeline の中で SMOTE  : PR-AUC {inside:.3f}")
print(f"使っていない 30% で評価: PR-AUC {test:.3f}")
```

```text
SMOTE の後に交差検証   : PR-AUC 0.990
Pipeline の中で SMOTE  : PR-AUC 0.728
使っていない 30% で評価: PR-AUC 0.716
```

{{< figure src="ci_leak.webp" alt="横棒グラフ。SMOTE をかけてから交差検証した PR-AUC は 0.990、Pipeline の中で SMOTE して交差検証した PR-AUC は 0.728、学習に使っていない 30% で評価した PR-AUC は 0.716" caption="SMOTE をかける場所と、ランダムフォレストの PR-AUC" align="center" >}}

先に SMOTE をかけた交差検証は 0.990 で、使っていない 30% での 0.716 を大きく上回りました。`Pipeline` の中でかけた 0.728 は、30% での値とほぼ一致します。

0.990 には 2 つの理由が重なっていると考えられます。1 つは、SMOTE が作った行は本物の陽性 2 件の間にあるので、評価に回った人工の行のすぐ近くに、学習に使った本物の陽性がいることです。ランダムフォレストは学習した行の近くをよく覚えるので、ほぼ正解できます。もう 1 つは、評価に回る行も陽性と陰性が半々になり、でたらめに並べた時の PR-AUC が 0.023 から 0.5 に上がることです。

正解を使う前処理を交差検証の外でかけると評価が高く出る仕組みは、[データリーク](../data-leakage/)で列の選択や標準化の例と一緒に扱っています。リサンプリングも同じで、評価に回る行には手を付けないことが前提です。imbalanced-learn の文書も、[よくある落とし穴](https://imbalanced-learn.org/stable/common_pitfalls.html)としてこの順序を挙げています。

---

### 見逃しのコストから閾値を決める

閾値を下げると決めても、どこまで下げるかが残ります。基準になるのは、陽性の見逃し 1 件が誤報 1 件の何倍痛いかです。この倍率を `C` とすると、確率が実際の割合と合っているモデルでは、閾値 `1 / (1 + C)` でコストが最小になります。この式の導き方は、[混同行列](../confusion-matrix/)の「見逃しと誤報のコストから閾値を決める」の節にあります。

見逃し 1 件を誤報 10 件分と数え、そのままで閾値を動かした時のコストと、`class_weight` の閾値 0.5 でのコストを比べました。

```python
from sklearn.metrics import make_scorer
from sklearn.model_selection import TunedThresholdClassifierCV

C = 10                       # 見逃し 1 件のコスト ÷ 誤報 1 件のコスト


def cost(y_true, y_pred):
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
    return fp + C * fn


t_star = 1 / (1 + C)
print(f"そのまま、閾値 0.5      : コスト {cost(y, p_plain >= 0.5)}")
print(f"class_weight、閾値 0.5  : コスト {cost(y, p_bal >= 0.5)}")
print(f"そのまま、閾値 1/(1+C) = {t_star:.3f}: コスト {cost(y, p_plain >= t_star)}")

tuned = TunedThresholdClassifierCV(make_pipeline(StandardScaler(), lr()),
                                   scoring=make_scorer(lambda a, b: -cost(a, b)), cv=5)
print("TunedThresholdClassifierCV の交差検証でのコスト:", cost(y, cross_val_predict(tuned, X, y, cv=cv)))
print("全データで選んだ閾値:", round(float(tuned.fit(X, y).best_threshold_), 3))
```

```text
そのまま、閾値 0.5      : コスト 1579
class_weight、閾値 0.5  : コスト 1499
そのまま、閾値 1/(1+C) = 0.091: コスト 1001
TunedThresholdClassifierCV の交差検証でのコスト: 1045
全データで選んだ閾値: 0.091
```

{{< figure src="ci_cost.webp" alt="横軸がそのままでの閾値（対数目盛）、縦軸が誤報の件数 + 10 × 見逃しの件数のグラフ。青い曲線は閾値 0.01 で 3000 近くあり、0.05〜0.15 付近で 1000 前後の谷になり、閾値 0.5 で 1579 に上がる。閾値 1/(1+10) = 0.091 の点はコスト 1001。赤い破線の class_weight・閾値 0.5 は 1499 で、谷より 500 ほど高い" caption="見逃しを誤報 10 件分と数えた時のコストと閾値" align="center" >}}

`class_weight` の 1,499 は、閾値 0.5 のままの 1,579 よりは低いものの、閾値を 0.091 に下げた 1,001 より 500 ほど高くなりました。切片のずれだけで考えると、`class_weight` の閾値 0.5 はそのままで言う閾値 0.023 に当たり、見逃しを誤報 42 件分と数えた時の位置だからです。重みの倍率は陽性と陰性の行数だけから決まり、見逃しのコストとは関係がありません。

scikit-learn 1.5 で入った [`TunedThresholdClassifierCV`](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TunedThresholdClassifierCV.html) は、学習用に渡したデータの中で交差検証を回し、渡したコストの関数が最も良くなる閾値を選びます。交差検証で測ったコストは 1,045 でした。データ全体で選ばせた閾値は 0.091 で、`1 / (1 + C)` の計算と同じ所に着きました。ここではデータ全体で比べましたが、実際に使う時は、閾値を選ぶデータとは別に残したテスト用のデータで最後の評価をします。閾値を選んだデータで評価すると、そのデータに合わせ込んだ分だけ良く見えるからです。

---

### 重み付けやリサンプリングを使う場面

ここまでの結果は、重み付けやリサンプリングが無駄だという意味ではありません。予測で陽性・陰性のラベルだけを返し、閾値を変えられない仕組みに組み込むなら、重みは閾値を動かす手段になります。学習の損失そのものを陽性側に傾けたい時も同じです。その場合は `"balanced"` ではなく、`class_weight={0: 1, 1: 10}` のように見逃しのコストに合わせた倍率を渡す方が、行数の比で決まる 42 倍より意味のある値になります。

Elor 氏と Averbuch-Elor 氏の [2022 年の論文](https://arxiv.org/abs/2201.08528)は、多数のデータセットでリサンプリングを比べ、弱い分類器では効くことがある一方で、勾配ブースティングのような強い分類器では予測の性能が上がらなかったと報告しています。上の表で、勾配ブースティングの PR-AUC がどの対処でも上がらなかったのは、この報告と合います。ただ、ロジスティック回帰でも PR-AUC は上がっていないので、どの分類器なら効くかまでは、このデータからは分かりません。

ランダムアンダーサンプリングは、陰性が多すぎて学習が終わらない時に、学習の時間を減らす手段として使えます。その場合も、間引いた分だけ確率が高く出るので、前の節と同じようにオッズを直します。陰性を 100 件に 1 件残したなら、オッズに 1/100 を掛けます。mammography のように陽性が 260 件しかないデータで陰性を陽性と同じ数まで減らすと、表のとおり PR-AUC が下がります。

---

### 対処を選ぶ前に決めること

最初に決めるのは、モデルの出力を確率として使うか、陽性・陰性の判定だけに使うかです。確率を件数の見込みや優先度の計算に使うなら、重み付けやリサンプリングをかけず、かけたなら重みの倍率でオッズを割って戻します。判定だけに使うなら、次に見逃し 1 件が誤報何件分かを決め、閾値を `1 / (1 + C)` から始めて `TunedThresholdClassifierCV` で合わせます。

閾値を決める前のモデルは、閾値 0.5 の正解率や再現率ではなく PR-AUC で比べ、閾値を決めた後はコストで比べます。PR-AUC を書く時は陽性の割合を一緒に書き、リサンプリングは `Pipeline` の中に入れて、評価に回る行には触れないようにします。陽性の取りこぼしやラベルの誤りが多いデータなら、モデルで手当てする前に、集め方と付け方を見直します。

冒頭の図で `class_weight` の赤い丸は、そのままとは別の、少し下にある曲線に乗っていました。陽性を見つけたいなら、曲線を乗り換えるのではなく、同じ青い曲線に沿って、コストで決めた所まで動くことから始めます。
