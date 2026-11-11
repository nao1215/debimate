---
title: "混同行列・偽陽性/偽陰性・閾値調整"
date: 2026-05-24
draft: false
series: ["機械学習ノート", "Machine Learning"]
tags: ["machine-learning", "scikit-learn", "metrics"]
weight: 1
topics: ["Machine Learning（評価・概念・アルゴリズム）"]
---

混同行列（confusion matrix）は、分類結果を「正解/不正解」と「陽性/陰性」の組み合わせで整理した 2×2 の表です。偽陽性（False Positive, FP）と偽陰性（False Negative, FN）のバランスを見ることで、誤りの種類を把握できます。

陽性が極端に少ない [クラス不均衡](../class-imbalance/) のデータでは、Accuracy だけを見ると「全部陰性と予測するだけのモデル」が高スコアを取ってしまいます。そのため、混同行列の各セルから計算する Precision・Recall・F1 も併用します。閾値ごとの真陽性率と偽陽性率は ROC 曲線、Precision と Recall は PR 曲線で確認できます（[ROC-AUC / PR-AUC](../roc-pr-auc/)）。

---

### 用語

- TP（True Positive）: 実際に陽性で、予測も陽性
- FP（False Positive）: 実際は陰性、予測は陽性（誤検知）
- TN（True Negative）: 実際に陰性で、予測も陰性
- FN（False Negative）: 実際は陽性、予測は陰性（見逃し）

scikit-learn の [`confusion_matrix`](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.confusion_matrix.html) は行を正解、列を予測として並べるため、二値分類では次の配置になります。数値は後の実例で閾値を 0.5 にした場合です。

| | 予測: 陰性 | 予測: 陽性 |
| --- | ---: | ---: |
| 正解: 陰性 | TN = 3 | FP = 1 |
| 正解: 陽性 | FN = 1 | TP = 3 |

Precision・Recall・F1 は、この 4 つのセルから計算します。scikit-learn では [`precision_score`](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.precision_score.html)、[`recall_score`](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.recall_score.html)、[`f1_score`](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.f1_score.html) で求めます。

- Precision（適合率）= TP / (TP + FP): 陽性と予測したうち、本当に陽性だった割合
- Recall（再現率）= TP / (TP + FN): 実際の陽性のうち、陽性と予測できた割合
- F1 = 2 × Precision × Recall / (Precision + Recall): Precision と Recall の調和平均

上の表では、Precision と Recall がどちらも 3 / 4 = 0.75 で、F1 も 0.75 です。

---

### 閾値調整の考え方

多くの分類モデルは「陽性である確率（スコア）」を出力します。閾値（threshold）は陽性/陰性に分ける境界値で、例えば 0.5 ならスコアが 0.5 以上を陽性と判定します。[SVM](../svm/) の `decision_function` のように確率ではないスコアを返すモデルでも、同じように閾値を決めて分けます。

閾値を動かすと、誤検知（FP）と見逃し（FN）のどちらを重視するかを調整できます。

- 閾値を下げる: 陽性と判定しやすくなり、FN は減るか変わらず、FP は増えるか変わらない
- 閾値を上げる: 陽性と判定しづらくなり、FP は減るか変わらず、FN は増えるか変わらない

陽性が約 10% の合成データ 4000 件を半分に分け、[ロジスティック回帰](../logistic-regression/)を学習させて確かめます。左が閾値 0.5、右が 0.2 の時のテストデータ 2000 件（陽性 213 件）の混同行列で、色の濃さは件数の対数です。

{{< figure src="confusion-matrix_heatmaps.svg" alt="2 つの 2×2 の混同行列を並べた図。閾値 0.5 は TN 1787、FP 0、FN 173、TP 40 で Precision 1.00・Recall 0.19、閾値 0.2 は TN 1699、FP 88、FN 121、TP 92 で Precision 0.51・Recall 0.43" caption="閾値 0.5 と 0.2 の混同行列" align="center" >}}

閾値 0.5 の Accuracy は 0.913 で、全部を陰性と予測した場合の 0.893 とほとんど変わりません。陽性 213 件のうち 173 件を見逃しており、Recall は 0.19 です。閾値を 0.2 へ下げると FN は 121 件に減り、FP は 0 件から 88 件に増えます。

閾値を 0.1 から 0.9 まで動かすと、FP と FN は次のように逆向きに動きます。

{{< figure src="confusion-matrix_threshold_sweep.svg" alt="横軸を閾値 0.1〜0.9、縦軸をテストデータ 2000 件での件数とした 2 本の折れ線。閾値を下げるほど FP（誤検知）が増え、FN（見逃し）が減り、2 本は逆向きに動く" caption="閾値ごとの FP と FN の件数" align="center" >}}

どこで止めるかは、誤検知と見逃しのどちらのコストが高いかで決めます。スコアを「この確率以上なら陽性」の意味で使うなら、スコアと実際の陽性の割合が合っているかを[確率の校正](../probability-calibration/)で確かめます。

---

## Python での実例

同じ 8 件のスコアを 3 つの閾値で比べます。

```python
from sklearn.metrics import confusion_matrix, precision_score, recall_score

y_true = [0, 0, 0, 0, 1, 1, 1, 1]
y_score = [0.1, 0.3, 0.4, 0.8, 0.2, 0.6, 0.7, 0.9]
for threshold in [0.3, 0.5, 0.7]:
    y_pred = [int(score >= threshold) for score in y_score]
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
    precision = precision_score(y_true, y_pred, zero_division=0)
    recall = recall_score(y_true, y_pred, zero_division=0)
    print(
        f"{threshold:.1f}: TN={tn} FP={fp} FN={fn} TP={tp} "
        f"precision={precision:.2f} recall={recall:.2f}"
    )
```

出力:

```text
0.3: TN=1 FP=3 FN=1 TP=3 precision=0.50 recall=0.75
0.5: TN=3 FP=1 FN=1 TP=3 precision=0.75 recall=0.75
0.7: TN=3 FP=1 FN=2 TP=2 precision=0.67 recall=0.50
```

`ravel()` は 2×2 の行列を行ごとに平らにするため、用語の節の配置から TN, FP, FN, TP の順で取り出せます。

0.3 から 0.5 へ上げると、スコア 0.3 と 0.4 の陰性が陰性と判定され、FP が 3 件から 1 件に減ります。この範囲に陽性のスコアは無いので、FN は 1 件のまま、Recall も 0.75 のままです。0.7 まで上げるとスコア 0.6 の陽性が見逃され、FN が 2 件、Recall は 0.50 に下がります。

<br>

意外なのは、0.5 から 0.7 へ上げると Precision も 0.75 から 0.67 へ下がることです。陰性なのにスコア 0.8 を持つ 1 件は陽性のまま残り、外れたのは TP だけなので、3 / 4 から 2 / 3 になります。

Recall は分母が実際の陽性の件数で固定されているため、閾値を上げると下がるか同じままです。一方で、Precision は分母の TP + FP も一緒に動くため、閾値を上げれば上がるとは限りません。

---

### 数学での使いどころ

- 二値分類の誤りを構造的に把握する
- 指標（Accuracy, Precision, Recall）の分解

---

### 機械学習での使いどころ

- 偽陽性/偽陰性のどちらを重視するか判断する
- 業務コストに応じた閾値の設定

---

### 適さないケース

- ラベルが未定義・曖昧なデータ
- 多クラスでは集約方法（macro/micro）を設計する必要がある
