---
title: "混同行列・偽陽性/偽陰性・閾値調整"
date: 2026-05-24
draft: false
series: ["機械学習ノート", "Machine Learning"]
tags: ["machine-learning", "scikit-learn", "metrics"]
weight: 1
---

混同行列（confusion matrix）は、分類結果を「正解/不正解」と「陽性/陰性」の組み合わせで整理した 2×2 の表です。偽陽性（False Positive, FP）と偽陰性（False Negative, FN）のバランスを見ることで、誤りの種類を把握できます。

陽性が極端に少ない [クラス不均衡](../class-imbalance/) のデータでは、Accuracy だけを見ると「全部陰性と予測するだけのモデル」が高スコアを取ってしまいます。そのため、混同行列の各セルから計算する Precision・Recall・F1 も併用します。閾値ごとの真陽性率と偽陽性率は ROC 曲線、Precision と Recall は PR 曲線で確認できます（[ROC-AUC / PR-AUC](../roc-pr-auc/)）。

---

### 用語

- TP（True Positive）: 実際に陽性で、予測も陽性
- FP（False Positive）: 実際は陰性、予測は陽性（誤検知）
- TN（True Negative）: 実際に陰性で、予測も陰性
- FN（False Negative）: 実際は陽性、予測は陰性（見逃し）

---

### 閾値調整の考え方

多くの分類モデルは「陽性である確率（スコア）」を出力します。このスコアに対してしきい値を動かすと、FP と FN のバランスが変わります。確率そのものではなく順位だけを返すモデルでも、同じように境界値を決めて陽性・陰性へ分けます。

しきい値は「陽性/陰性に分ける境界値」で、例えば 0.5 ならスコアが 0.5 以上を陽性と判定します。しきい値を変えることで、誤検知（FP）と見逃し（FN）のどちらを重視するかを調整できます。

- しきい値を下げる: 陽性と判定しやすくなり、FN は減るが FP は増える
- しきい値を上げる: 陽性と判定しづらくなり、FP は減るが FN は増える

---

## Python での実例

同じ 8 件のスコアを 3 つのしきい値で比べます。表はコードの出力から作るため、数値と説明を別々に直す必要がありません。

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

各行で混同行列の行は正解、列は予測です。例えば 0.5 の `[[3, 1], [1, 3]]` では、左上が TN、右上が FP、左下が FN、右下が TP です。実務ではしきい値を 1 つだけ選ばず、同じ `y_true` と `y_score` から複数のしきい値で Precision と Recall を並べ、偽陽性・偽陰性のコストで決めます。

| 閾値 | TN | FP | FN | TP | Precision | Recall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.3 | 1 | 3 | 1 | 3 | 0.50 | 0.75 |
| 0.5 | 3 | 1 | 1 | 3 | 0.75 | 0.75 |
| 0.7 | 3 | 1 | 2 | 2 | 0.67 | 0.50 |

この例では 0.3 から 0.5 へ上げると FP が 3 件から 1 件に減り、Precision は 0.50 から 0.75 に上がります。一方、Recall はどちらも 0.75 のままです。0.7 まで上げると FN が 1 件から 2 件に増え、Recall は 0.50 へ下がります。一般にしきい値を下げれば FN が増えない、上げれば FP が増えないという単調さはありますが、Precision や Recall が毎回変化するとは限りません。どの行を選ぶかは、誤検知と見逃しのコストで決めます。

---

### 数学での使いどころ

- 二値分類の誤りを構造的に把握する
- 指標（Accuracy, Precision, Recall）の分解

---

### 機械学習での使いどころ

- 偽陽性/偽陰性のどちらを重視するか判断する
- 業務コストに応じたしきい値の設定

---

### 適さないケース

- ラベルが未定義・曖昧なデータ
- 多クラスでは集約方法（macro/micro）を設計する必要がある
