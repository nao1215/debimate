---
title: "混同行列 - 閾値を下げて Recall が 1.000 になったのに、悪性の見逃しが 2 件から 14 件に増えた理由"
date: 2026-05-24
draft: false
series: ["機械学習ノート", "Machine Learning"]
tags: ["machine-learning", "scikit-learn", "metrics"]
weight: 1
topics: ["Machine Learning（評価・概念・アルゴリズム）"]
---

混同行列（confusion matrix）は、分類モデルの予測を「正解のクラス」と「予測したクラス」の組ごとに数えた表です。2 クラスなら 2×2 のマスになり、どのマスに何件入ったかを見ると、モデルが何を見逃し、何を誤って拾ったかが分かります。

以下は、[scikit-learn](https://scikit-learn.org/stable/) に同梱の [breast_cancer](https://scikit-learn.org/stable/modules/generated/sklearn.datasets.load_breast_cancer.html) で[ロジスティック回帰](../logistic-regression/)を学習し、テスト用の 285 件を予測した結果です。breast_cancer は、乳房のしこりから採った細胞を画像で測った 30 列の値と、悪性か良性かの正解を 569 件並べたデータで、機械学習のデータを集めた [UCI Machine Learning Repository](https://archive.ics.uci.edu/dataset/17/breast+cancer+wisconsin+diagnostic) で公開されています。学習用に配られている古典的なデータで、本記事の話は診断の判断基準を示すものではありません。

ロジスティック回帰は、1 件ごとに 0〜1 の確率を出し、その確率が境目の値（閾値）以上かどうかで 2 つのクラスに分けます。境目の既定は 0.5 です。悪性の見逃しを減らすつもりで、scikit-learn の解説でよく見る書き方のまま、境目を 0.1 に下げました。

{{< figure src="confusion-matrix_cover.webp" alt="2 つの 2×2 の混同行列。行は正解の悪性 (0) と良性 (1)、列は予測の悪性と良性。左の閾値 0.5 は 104、2、4、175 で、recall_score 0.978、悪性の見逃し 2 件。右の閾値 0.1 は 92、14、0、179 で、recall_score 1.000、悪性の見逃し 14 件。悪性を良性と予測した右上のマスが赤く囲まれている" caption="閾値を 0.5 から 0.1 に下げると、recall_score は 1.000 に上がり、悪性の見逃しは 14 件に増える" align="center" >}}

図の上に書いた `recall_score` は、scikit-learn で「拾うべきものを何割拾えたか」を測る関数で、0.978 から 1.000 に上がりました。数字だけ見れば、取りこぼしが無くなったように見えます。ところが、悪性を良性と判定した右上の赤いマスは 2 件から 14 件に増えました。数字が良くなったのに、見逃しは 7 倍になったわけです。なぜ逆向きに動いたのかは、混同行列のマスと指標を定義した後、「scikit-learn が陽性とみなすラベル」の節で明かします。

手元のデータでも、正解を 0 と 1 の番号で持つと、見つけたい側がどちらの番号になるかはデータ次第です。検品の結果を "NG" と "OK" の文字列で持っていれば、名前の順に並べた結果で NG が 0 になります。不正検知や障害の通知のように、見逃し 1 件の方が誤報 1 件より高くつく場面では、閾値を下げて見逃しを減らそうとします。その前に、どのマスが見逃しで、どの数字で閾値を決めるのかを押さえておく必要があります。

<br>

本記事では、ML を学び始めた人と、scikit-learn の分類器を手元のデータに使う人に向けて、次の疑問に答えます。

- 混同行列のどのマスが見逃しで、どのマスが誤報なのか。
- scikit-learn は、どちらのラベルを陽性として数えるのか。
- 閾値を動かすと、4 つのマスと Precision はどう動くのか。
- 見逃しと誤報のコストが違う時、閾値をどう決めるのか。

実験は scikit-learn 1.9.1 で行いました。図を描く処理も含めた完全なコードは [confusion-matrix_gen.py](https://github.com/nao1215/debimate/blob/main/projects/ml/scripts/notes/confusion-matrix_gen.py) にあります。

---

### 4 つのマスと Precision・Recall

2 クラスの分類では、見つけたい側を陽性（positive）、それ以外を陰性（negative）と呼びます。breast_cancer で見つけたいのは悪性なので、悪性が陽性です。正解と予測の組は 4 通りで、それぞれに名前が付いています。

- TP（True Positive）: 正解が陽性で、陽性と予測した
- FN（False Negative）: 正解が陽性なのに、陰性と予測した（見逃し）
- FP（False Positive）: 正解が陰性なのに、陽性と予測した（誤報）
- TN（True Negative）: 正解が陰性で、陰性と予測した

scikit-learn の [`confusion_matrix`](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.confusion_matrix.html) は、行に正解、列に予測を並べます。ラベルは小さい順に並ぶので、ラベル 0 の悪性が上の行と左の列です。冒頭の図の左の混同行列に、悪性を陽性とした名前を当てると次のようになります。

| | 予測: 悪性 (0) | 予測: 良性 (1) |
| --- | ---: | ---: |
| 正解: 悪性 (0) | TP = 104 | FN = 2 |
| 正解: 良性 (1) | FP = 4 | TN = 175 |

この 4 つのマスから、よく使う指標を計算します。Precision（適合率）は、陽性と予測したもののうち本当に陽性だった割合で、`TP / (TP + FP)` です。Recall（再現率）は、本当の陽性のうち陽性と予測できた割合で、`TP / (TP + FN)` です。F1 は両者の[調和平均](/ml/math/mean/)です。

上の表では、Precision が 104 / 108 = 0.963、Recall が 104 / 106 = 0.981、F1 が 0.972 になります。Recall の分母は正解が悪性の行の合計で、閾値を動かしても 106 件のままです。Precision の分母は予測が悪性の列の合計なので、閾値で一緒に動きます。この違いは、後の閾値の節で効いてきます。

<br>

正解率（Accuracy）は対角の 2 マスの合計を全体で割った値で、(104 + 175) / 285 = 0.979 です。全部を良性と予測するだけでも 179 / 285 = 0.628 になり、陽性が少ないデータほど、この「何もしない」予測の正解率が高くなります。陽性が数 % しかない時の扱いは、[クラス不均衡](../class-imbalance/)で詳しく説明しています。3 クラス以上なら混同行列は 3×3 以上になり、Precision などはクラスごとに求めてから、引数 `average` の指定で 1 つにまとめます。

---

### scikit-learn が陽性とみなすラベル

冒頭の実験のコードです。`train_test_split` で半分を学習用、半分をテスト用に分けます。各列の平均と散らばりを揃える[標準化](../standardization/)とロジスティック回帰は、`make_pipeline` で 1 本の処理につなぎ、まとめて学習します。

```python
data = load_breast_cancer()
X, y = data.data, data.target
print("ラベル:", dict(enumerate(data.target_names)), "件数:", np.bincount(y))
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.5, stratify=y, random_state=0)
model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000)).fit(X_train, y_train)
proba = model.predict_proba(X_test)[:, 1]  # 解説でよく見る書き方。列 1 はラベル 1（良性）の確率
print("テスト:", np.bincount(y_test))
for threshold in [0.5, 0.1]:
    y_pred = (proba >= threshold).astype(int)
    cm = confusion_matrix(y_test, y_pred)
    print(f"閾値 {threshold}: 混同行列 {cm.tolist()}、recall_score {recall_score(y_test, y_pred):.3f}、"
          f"悪性の Recall {recall_score(y_test, y_pred, pos_label=0):.3f}、悪性の見逃し {cm[0, 1]} 件")
```

```text
ラベル: {0: np.str_('malignant'), 1: np.str_('benign')} 件数: [212 357]
テスト: [106 179]
閾値 0.5: 混同行列 [[104, 2], [4, 175]]、recall_score 0.978、悪性の Recall 0.981、悪性の見逃し 2 件
閾値 0.1: 混同行列 [[92, 14], [0, 179]]、recall_score 1.000、悪性の Recall 0.868、悪性の見逃し 14 件
```

出力の 1 行目のとおり、ラベル 0 が malignant（悪性）、1 が benign（良性）です。[`recall_score`](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.recall_score.html) や [`precision_score`](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.precision_score.html) は、引数 `pos_label` で陽性のラベルを決め、その既定値は 1 です。何も指定しないと、良性を陽性として数えます。冒頭の図の上に書いた `recall_score` の 0.978 と 1.000 は、悪性ではなく良性を何割拾えたかの数字でした。

`predict_proba` が返す列も、学習したモデルの `classes_` の順、つまりラベルの小さい順に並びます。列 1 は良性である確率で、`proba >= 0.1` は「良性の確率が 10% あれば良性と判定する」という意味になります。冒頭で下げたのは、悪性ではなく良性と判定する閾値でした。以下は、閾値を 0.95 から 0.05 まで下げながら、既定の `recall_score` と、`pos_label=0` を指定した悪性の Recall を並べた図です。

{{< figure src="confusion-matrix_two_recalls.webp" alt="横軸は predict_proba(X)[:, 1] に掛ける閾値で、右へ行くほど 0.95 から 0.05 へ下がる。灰色の recall_score の既定は右へ行くほど上がり、0.35 付近で 1.000 に達する。赤い pos_label=0 の Recall は 0.5 付近の 0.981 から右へ行くほど下がり、0.05 で 0.840 になる。冒頭の図の閾値 0.5 と 0.1 に名前付きの点線" caption="閾値を下げた時の、既定の recall_score（良性）と悪性の Recall" align="center" >}}

閾値を下げるほど、灰色の線は 1.000 に近づき、赤い線は下がります。良性と判定する件数が増えるので、良性の取りこぼしは減り、悪性まで良性と判定されるようになるからです。灰色の線だけを見ていると、改善したと判断してしまいます。

<br>

直し方は 2 つあります。1 つは、学習の前に `y = 1 - data.target` のように見つけたい側を 1 に付け替えることです。こうすると `predict_proba(X)[:, 1]` も既定の `recall_score` も悪性を指し、後の節の閾値の調整もそのまま書けます。もう 1 つは、ラベルを変えずに `pos_label=0` と `predict_proba(X)[:, 0]` を使うことで、指定を 1 か所でも忘れると冒頭の図と同じことが起きます。

文字列のラベルでも順番の問題は残ります。"NG" と "OK" なら名前の順で NG が上の行に来ます。`recall_score` は `pos_label=1 is not a valid label` という `ValueError` の例外で止まってくれますが、`confusion_matrix` は黙って表を返します。

公式の文書の例にある `tn, fp, fn, tp = confusion_matrix(...).ravel()` にも注意が要ります。`ravel()` は 2×2 の表を左上、右上、左下、右下の順に 1 列に並べるだけです。2 行目と 2 列目が陽性の時、つまり陽性が後に並ぶラベルの時だけ、この 4 つの名前が合います。以下は、NG を見つけたい 5 件で、`labels` で陰性・陽性の順を明示した場合としない場合を比べたコードです。

```python
y_true = ["OK", "NG", "OK", "NG", "NG"]
y_pred = ["OK", "OK", "OK", "NG", "NG"]
tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
print(f"labels 無し: tn={tn} fp={fp} fn={fn} tp={tp}")
tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=["OK", "NG"]).ravel()
print(f"labels 指定: tn={tn} fp={fp} fn={fn} tp={tp}")
```

```text
labels 無し: tn=2 fp=1 fn=0 tp=2
labels 指定: tn=2 fp=0 fn=1 tp=2
```

本当は NG を 1 件見逃しているのに、`labels` 無しでは見逃し 0 件・誤報 1 件と読めてしまいます。次の節の例は陽性が 1 なので、そのまま `ravel()` で取り出せます。

---

### 閾値と 4 つのマスの動き

見つけたい側を陽性に揃えたら、閾値で何が変わるかを見ます。閾値（threshold）は、モデルが出したスコアを陽性と陰性に分ける境目で、0.5 なら 0.5 以上を陽性と判定します。[SVM](../svm/) の `decision_function` のように確率ではないスコアでも、同じように閾値で分けます。

閾値を下げると、各行の件数が「予測: 陰性」の列から「予測: 陽性」の列へ移ります。正解が陽性の行では FN が TP に移り、正解が陰性の行では TN が FP に移ります。行の合計は変わらないので、Recall は閾値を下げると上がるか同じままです。Precision の動きは、8 件の小さな例で確認します。

```python
y_true = [0, 0, 0, 0, 1, 1, 1, 1]
y_score = [0.1, 0.3, 0.4, 0.8, 0.2, 0.6, 0.7, 0.9]
for threshold in [0.3, 0.5, 0.7]:
    y_pred = [int(score >= threshold) for score in y_score]
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
    precision = precision_score(y_true, y_pred, zero_division=0)
    recall = recall_score(y_true, y_pred, zero_division=0)
    print(f"{threshold:.1f}: TN={tn} FP={fp} FN={fn} TP={tp} precision={precision:.2f} recall={recall:.2f}")
```

```text
0.3: TN=1 FP=3 FN=1 TP=3 precision=0.50 recall=0.75
0.5: TN=3 FP=1 FN=1 TP=3 precision=0.75 recall=0.75
0.7: TN=3 FP=1 FN=2 TP=2 precision=0.67 recall=0.50
```

以下は、8 件のスコアを横に並べ、3 つの閾値の位置に破線を引いた図です。

{{< figure src="confusion-matrix_toy.webp" alt="横軸はスコア 0〜1。青い四角の陰性が 0.1、0.3、0.4、0.8、赤い丸の陽性が 0.2、0.6、0.7、0.9 に並ぶ。閾値 0.3 の破線は P 0.50 / R 0.75、閾値 0.5 は P 0.75 / R 0.75、閾値 0.7 は P 0.67 / R 0.50" caption="8 件のスコアと 3 つの閾値。破線の上か右にある点を陽性と判定する" align="center" >}}

0.3 から 0.5 へ上げると、スコア 0.3 と 0.4 の陰性が陰性と判定されるようになり、FP が 3 件から 1 件に減ります。この間に陽性のスコアは無いので、Recall は 0.75 のままです。

0.5 から 0.7 へ上げると、スコア 0.6 の陽性を見逃して Recall が 0.75 から 0.50 に下がり、Precision も 0.75 から 0.67 へ下がります。外れたのはスコア 0.6 の陽性だけで、スコア 0.8 の陰性は陽性のまま残るので、3 / 4 が 2 / 3 になるからです。閾値を上げれば Precision が上がる、とは限りません。

閾値を全て試した時の Precision と Recall の動きを 1 本の曲線にしたのが PR 曲線で、FP の割合と Recall の動きを描いたのが ROC（Receiver Operating Characteristic）曲線です。曲線とその下の面積で閾値に依らずにモデルを比べる方法は、[ROC-AUC / PR-AUC](../roc-pr-auc/) で説明しています。本記事では、その曲線の上のどこで止めるかを決めます。

---

### 見逃しと誤報のコストから閾値を決める

どこで止めるかは、見逃し 1 件と誤報 1 件のどちらが高くつくかで決まります。ここでは、見逃し 1 件のコストを 10、誤報 1 件のコストを 1 と置きます。この 10:1 は説明用の仮の値です。実際の比は使う現場が決める値で、比が変われば、下で求める閾値も `1 / (1 + 比)` で動きます。コストの合計は「見逃しの件数 × 10 ＋ 誤報の件数 × 1」です。

モデルの出す確率が実際の割合と合っていれば、閾値は計算で決まります。悪性の確率が `p` の 1 件を良性と判定すると、確率 `p` で見逃しになります。悪性と判定すると、確率 `1 - p` で誤報になります。2 通りの判定の損失の期待値は次のとおりです。

```text
良性と判定した時の損失の期待値 = 10 × p
悪性と判定した時の損失の期待値 =  1 × (1 - p)
10 × p > 1 × (1 - p) となるのは p > 1 / (1 + 10) = 1/11（約 0.09）の時
```

悪性の確率が 1/11 を超えれば、悪性と判定する方が損失が小さくなります。つまり閾値は約 0.09 です。この導き方は、コストを考えた学習の古典として知られる、Charles Elkan が 2001 年に発表した論文「[The Foundations of Cost-Sensitive Learning](https://cseweb.ucsd.edu/~elkan/rescale.pdf)」にあります。

<br>

確率が実際の割合と合っているかは、モデルによって違います。合っていない時に頼れるのが、scikit-learn 1.5 で入った [`TunedThresholdClassifierCV`](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TunedThresholdClassifierCV.html) です。学習用のデータの中で[交差検証](../cross-validation/)を回し、指定した評価の関数が最も良くなる閾値を選びます。評価の関数の既定は `balanced_accuracy` で、見逃しと誤報のコストの違いは見ません。コストで選ぶなら、評価の関数を自分で渡します。

以下のコードは、図を描く処理を除いた抜粋で、`X` と `y` は前の節と同じです。悪性を 1 に付け替えた上で、学習とテストの分け方の乱数を 20 通りに変え、閾値 0.5、1/11、`TunedThresholdClassifierCV` が選んだ閾値の 3 つについて、テスト用の 285 件でコストを比べます。`StratifiedKFold` は、陽性と陰性の比を各分割で揃える交差検証の分け方です。

```python
C_FN, C_FP = 10, 1


def cost(y_true, y_pred):
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    return C_FN * fn + C_FP * fp


neg_cost = make_scorer(lambda yt, yp: -cost(yt, yp))
fixed, tuned_cost, tuned_thr = {"0.5": [], "1/11": []}, [], []
for seed in range(20):
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.5, stratify=y, random_state=seed)
    y_tr, y_te = 1 - y_tr, 1 - y_te  # 悪性を 1（陽性）に付け替える
    base = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))
    p = base.fit(X_tr, y_tr).predict_proba(X_te)[:, 1]  # 悪性の確率
    fixed["0.5"].append(cost(y_te, (p >= 0.5).astype(int)))
    fixed["1/11"].append(cost(y_te, (p >= 1 / 11).astype(int)))
    tuned = TunedThresholdClassifierCV(base, scoring=neg_cost,
                                       cv=StratifiedKFold(5, shuffle=True, random_state=0)).fit(X_tr, y_tr)
    tuned_thr.append(tuned.best_threshold_)
    tuned_cost.append(cost(y_te, tuned.predict(X_te)))
print(f"20 回の平均コスト: 閾値 0.5 {np.mean(fixed['0.5']):.1f}、閾値 1/11 {np.mean(fixed['1/11']):.1f}、"
      f"TunedThresholdClassifierCV {np.mean(tuned_cost):.1f}（選んだ閾値の中央値 {np.median(tuned_thr):.2f}）")
print(f"TunedThresholdClassifierCV が選んだ閾値: 最小 {min(tuned_thr):.2f}、最大 {max(tuned_thr):.2f}")
print(f"seed 0 だけ: 閾値 0.5 {fixed['0.5'][0]}、閾値 1/11 {fixed['1/11'][0]}")
```

```text
20 回の平均コスト: 閾値 0.5 54.0、閾値 1/11 34.8、TunedThresholdClassifierCV 38.5（選んだ閾値の中央値 0.18）
TunedThresholdClassifierCV が選んだ閾値: 最小 0.03、最大 0.35
seed 0 だけ: 閾値 0.5 24、閾値 1/11 27
```

`make_scorer` は、正解と予測を受け取る自作の関数から、scikit-learn が評価に使える形の関数を作ります。大きいほど良いとみなされるので、コストに負の符号を付けて渡しています。以下は、閾値ごとのコストを 20 通りの分け方それぞれで描き、平均を黒い線で重ねた図です。

{{< figure src="confusion-matrix_cost.webp" alt="横軸は悪性の確率に掛ける閾値 0〜1、縦軸はコスト。灰色の細い線が 20 通りの分け方、黒い線がその平均。平均は 0.05〜0.43 で 35〜43 ほどの平らな谷になり、0.5 を超えると上がり始め、0.9 付近で 150 に達する。縦軸は 160 までで、それより上は切れている。赤い破線の 1/11（約 0.09）は平均 34.8、点線の 0.5 は平均 54.0" caption="見逃し 10、誤報 1 のコストを閾値ごとに計算した結果（breast_cancer、20 通りの分け方。縦軸は 160 で切っている）" align="center" >}}

20 回の平均では、閾値 0.5 のコスト 54.0 に対し、1/11 は 34.8、`TunedThresholdClassifierCV` は 38.5 でした。計算で出した 1/11 は、このデータでは少なくとも 0.5 よりずっと良い出発点でした。ただし、次の段落のとおり谷の底は平らなので、この結果だけでは確率が実際の割合と合っていたとまでは言えません。合っているかを確認して直す方法は、[確率の校正](../probability-calibration/)で扱っています。

<br>

平均の黒い線は、0.05 から 0.43 付近まで平らな谷になっています。閾値の細かい値より、0.5 から谷の中へ下ろすことの方が効くということです。`TunedThresholdClassifierCV` が選んだ閾値が 0.03 から 0.35 まで散らばったのも、谷の底が平らで、どこを選んでもコストが大きく変わらないからと考えられます。

一方で、出力の最後の行のとおり、分け方の乱数が 0 の 1 回だけでは、0.5 の 24 が 1/11 の 27 より小さくなりました。テストの悪性は 106 件しかなく、見逃しが 1 件違うだけでコストが 10 動きます。灰色の線の上下の幅のとおり、1 回の分割の結果だけで閾値を比べると、逆の結論を選ぶことがあります。

---

### 閾値を決める前に確かめること

分類器の閾値を動かす前に、まず見つけたい側がどのラベルかを確認します。`model.classes_` を表示し、`predict_proba` のどの列が見つけたい側の確率か、`recall_score` の `pos_label` がどちらを指しているかを揃えます。迷うなら、見つけたい側を 1 に付け替えてから学習します。

次に、`confusion_matrix` に `labels` を渡して混同行列を出し、見逃しのマスと誤報のマスを指で指せる状態にします。Recall や F1 の 1 つの数字だけを追うと、冒頭の図のように、数字が上がったのに見たいマスが悪くなっていても気付けません。

閾値は、見逃しと誤報のコストの比から決めます。確率が実際の割合と合っていれば `C_FP / (C_FP + C_FN)` が起点になり、合っていなければ `TunedThresholdClassifierCV` にコストを渡して選びます。比べる時は、分け方を変えて何度か測り、1 回の分割の差で決めないようにします。

最後に、本番で陽性が現れる割合がテストのデータと違わないかを考えます。割合が変わると、同じ閾値でも Precision が変わります。その仕組みは[ベイズの定理](../../math/bayes-theorem/)で説明しています。閾値を変えるたびに、冒頭の図で赤く囲んだマスのように、見逃しのマスの件数がどちらへ動いたかを確認します。
