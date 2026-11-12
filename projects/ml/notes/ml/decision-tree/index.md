---
title: "決定木（decision tree） - breast_cancer で深さ 3 の木を学習すると、train_test_split の乱数だけで根の質問が 5 通りに変わる"
date: 2026-05-26
draft: false
series: ["機械学習ノート", "Machine Learning"]
tags: ["machine-learning", "scikit-learn", "supervised"]
weight: 21
topics: ["Machine Learning（評価・概念・アルゴリズム）"]
---

決定木（decision tree）は、「列 `x` の値が閾値 `t` 以下か」という質問を繰り返して行を分け、たどり着いた葉で答えを返すモデルです。一番上の質問を根、根から葉までに並ぶ質問の段数を木の深さと呼びます。分類なら、葉に入った学習データで一番多いクラスを返します。回帰なら、それらの値の平均を返します。質問の並びをそのまま図に描けるので、モデルがなぜその答えを出したかを人に見せたい時によく選ばれます。

[scikit-learn](https://scikit-learn.org/stable/) に同梱の [breast_cancer](https://scikit-learn.org/stable/modules/generated/sklearn.datasets.load_breast_cancer.html) は、乳房の腫瘍 569 件について、細胞核の画像から測った半径・周長・凹みなどを 30 列に並べ、悪性か良性かを付けたデータです。学習用とテスト用に 7:3 で分ける [`train_test_split`](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.train_test_split.html) の乱数 `random_state` だけを 0〜99 に変えて、深さ 3 の決定木を 100 本学習しました。

{{< figure src="dt_cover.webp" alt="左は横棒グラフで、100 本の木で根の質問に選ばれた列の回数。worst perimeter が 46 回、worst concave points が 23 回、worst radius と worst area が 11 回ずつ、mean concave points が 9 回。右は同じ 5 つの列ごとに、その列が根になった木のテスト 171 行の正解率を点で並べた図で、どの列も 0.87〜0.97 の間に散らばり、中央値の縦線は 0.92〜0.94 に並ぶ" caption="分け方の乱数だけを変えた深さ 3 の決定木 100 本で、根に選ばれた列とテストの正解率" align="center" >}}

根の質問に選ばれた列は 5 通りに分かれました。木の中で使った列の組まで見ると、100 本で 96 通りあります。一方で、テストの正解率はどの列が根でも[中央値](../../math/median/)が 0.92〜0.94 に並びました。100 本はそれぞれ違うテストの行で測っているので、根の列による差ははっきりしません。

決定木を選んだ理由が「判断の根拠を見せられる」ことなら、この結果は困ります。ある日の木を見せて「腫瘍の周長が一番重要な列です」と説明しても、データを分け直すと、凹みの数を根で聞く木が、同じくらいの正解率で出てきます。どちらの木も間違いではなく、エラーも警告も出ません。

<br>

本記事では、ML を学び始めたエンジニアと、scikit-learn の [`DecisionTreeClassifier`](https://scikit-learn.org/stable/modules/generated/sklearn.tree.DecisionTreeClassifier.html) を手元のデータに使う人に向けて、次の疑問に答えます。

- 決定木は、質問の列と閾値をどう選ぶのか。
- 分け方の乱数だけで、なぜ根の列が入れ替わるのか。
- 木の深さは、どこまで許せばよいのか。
- 学習したデータより外の範囲では、何を返すのか。
- 斜めの境界を持つデータは、どう分けるのか。

実験は scikit-learn 1.9.1 と [NumPy](https://numpy.org/) 2.5.4 で行いました。図を描く処理も含めた完全なコードは [decision-tree_gen.py](https://github.com/nao1215/debimate/blob/main/projects/ml/scripts/notes/decision-tree_gen.py) にあります。

---

### 質問の選び方

決定木は、根から順に「どの列をどの値で切るか」を 1 つずつ決めます。候補は全ての列と、各列の値を小さい順に並べた時の隣り合う 2 つの値の中点です。切る前のグループを親、切った後にできる 2 つのグループを子と呼びます。候補の全てを試し、子が一番「混ざっていない」状態になる分割を選びます。

混ざり具合は、scikit-learn の既定では Gini 不純度で測ります。グループに占める各クラスの割合を `p_k` とすると、Gini 不純度は `1 - Σ p_k^2` です。全部が同じクラスなら 0、悪性と良性が半々なら 0.5 になります。分割の良さは「親の Gini 不純度 - 子の Gini 不純度を行数で重み付けした平均」で測り、この減少が一番大きい分割を選びます。

木を作る質問と葉は、どれもノードと呼ばれる箱です。全 569 行で深さ 2 の木を学習し、質問を持つノードごとに列・閾値・行数を出しました。

```python
data = load_breast_cancer()
X, y = data.data, data.target                     # 569 行 × 30 列、0 が悪性・1 が良性
names = np.array(data.feature_names)


def gini(labels):
    p = np.bincount(labels, minlength=2) / len(labels)
    return 1 - np.sum(p ** 2)


root = DecisionTreeClassifier(max_depth=2, random_state=0).fit(X, y)
t = root.tree_
print("全行の Gini:", round(gini(y), 3), " 悪性・良性:", np.bincount(y))
for node in range(t.node_count):
    if t.feature[node] >= 0:
        print(f"ノード {node}: {names[t.feature[node]]} <= {t.threshold[node]:.3f}  行数 {t.n_node_samples[node]}")
```

```text
全行の Gini: 0.468  悪性・良性: [212 357]
ノード 0: worst radius <= 16.795  行数 569
ノード 1: worst concave points <= 0.136  行数 379
ノード 4: worst texture <= 19.910  行数 190
```

番号が 0・1・4 と飛ぶのは、2・3・5・6 が質問を持たない葉だからです。

{{< figure src="dt_tree.webp" alt="深さ 2 の決定木。根は worst radius ≤ 16.8 で、悪性 212 : 良性 357、Gini 0.468。はいの枝は worst concave points ≤ 0.136 で 33 : 346、その下の葉は 5 : 328 と 28 : 18。いいえの枝は worst texture ≤ 19.9 で 179 : 11、その下の葉は 8 : 9 と 171 : 2。悪性の方が多い箱は赤、良性の方が多い箱は青" caption="全 569 行で学習した深さ 2 の決定木" align="center" >}}

scikit-learn では [`plot_tree`](https://scikit-learn.org/stable/modules/generated/sklearn.tree.plot_tree.html) でも同じ木を描けます。列名が mean で始まる列は画像に写った細胞核全体で平均した値、worst で始まる列は値が大きい方から 3 つの細胞核で平均した値です。根の worst radius ≤ 16.8 は、大きい方から 3 つの細胞核で半径を平均し、その値で切る質問です。悪性 212 件と良性 357 件が混ざった Gini 0.468 の集まりが、良性の多い 379 行と、悪性の多い 190 行に分かれます。葉の 5 : 328 や 171 : 2 は、ほぼ 1 つのクラスだけになっています。

質問に当てはまる行は、左の「はい」の子へ進みます。例えば worst radius が 16.8 以下で、worst concave points が 0.136 以下の行は、良性が 328 件ある左端の葉に入り、良性と答えます。

この選び方は、今の 1 回で一番減る分割を選び、後から選び直しません。[Breiman 氏らの CART](https://doi.org/10.1201/9781315139470)（Classification and Regression Trees）をはじめ、多くの実装はこの貪欲な選び方で決定木を作ります。全体で最適な木を探す問題は [NP 完全だと示されている](https://doi.org/10.1016/0020-0190%2876%2990095-8)ので、1 段ずつ決めて計算を現実的な量に抑えています。scikit-learn は CART を最適化した実装を使っていると[ユーザーガイド](https://scikit-learn.org/stable/modules/tree.html#tree-algorithms-id3-c4-5-c5-0-and-cart)に書かれています。

---

### 根の列が入れ替わる仕組み

冒頭の 100 本は、次のコードで学習しました。前の節で作った `X`・`y`・`names` をそのまま使います。決定木の中にも乱数があるので、木の `random_state` は 0 に固定し、変えるのは `train_test_split` の乱数だけにしました。

```python
roots, accs, used = [], [], []
preds = []
for seed in range(100):
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.3, random_state=seed, stratify=y)
    tree = DecisionTreeClassifier(max_depth=3, random_state=0).fit(X_tr, y_tr)   # 木の中の乱数は固定
    f = tree.tree_.feature
    roots.append(str(names[f[0]]))                # 根の質問に使った列
    used.append(frozenset(names[f[f >= 0]]))      # 木の中で使った列の組
    accs.append(tree.score(X_te, y_te))           # テスト 171 行の正解率
    preds.append(tree.predict(X))                 # 全 569 行への予測
print("根に選ばれた列:", Counter(roots).most_common())
print("使った列の組の種類:", len(set(used)), "/ 100")
print("テストの正解率 最小・中央値・最大:", np.round([min(accs), np.median(accs), max(accs)], 3))
```

```text
根に選ばれた列: [('worst perimeter', 46), ('worst concave points', 23), ('worst radius', 11), ('worst area', 11), ('mean concave points', 9)]
使った列の組の種類: 96 / 100
テストの正解率 最小・中央値・最大: [0.871 0.93  0.971]
```

根が入れ替わったのは、上位に並ぶ候補の減少がほぼ同じだからです。全 569 行で、30 列それぞれの一番よい閾値での Gini 不純度の減少を計算し、大きい順に並べました。

```python
def gain_curve(x, labels):
    """x の値で並べ、左の行数ごとに Gini 不純度の減少（親 - 子の重み付き平均）を返す。"""
    o = np.argsort(x, kind="stable")
    xs, ys = x[o], labels[o]
    n = len(ys)
    left_pos = np.cumsum(ys)[:-1]
    nl = np.arange(1, n)
    nr = n - nl
    pl = left_pos / nl
    pr = (ys.sum() - left_pos) / nr
    # 2 クラスでは 1 - (p^2 + (1-p)^2) = 2p(1-p) なので、gini() と同じ値になる
    child = (nl * 2 * pl * (1 - pl) + nr * 2 * pr * (1 - pr)) / n
    gain = gini(labels) - child
    gain[xs[1:] == xs[:-1]] = np.nan              # 同じ値の間では切れない
    return nl / n, gain, (xs[:-1] + xs[1:]) / 2


best = []
for j in range(X.shape[1]):
    frac, g, thr = gain_curve(X[:, j], y)
    k = np.nanargmax(g)
    best.append((g[k], names[j], thr[k]))
best.sort(reverse=True)
for g, n_, thr in best[:6]:
    print(f"{n_:<22} 閾値 {thr:9.3f}  Gini の減少 {g:.4f}")
```

```text
worst radius           閾値    16.795  Gini の減少 0.3252
worst area             閾値   884.550  Gini の減少 0.3231
worst perimeter        閾値   105.950  Gini の減少 0.3220
worst concave points   閾値     0.142  Gini の減少 0.3192
mean concave points    閾値     0.051  Gini の減少 0.3154
mean area              閾値   696.250  Gini の減少 0.2808
```

1 位の worst radius の閾値 16.795 は、前の節で scikit-learn が根に選んだ値と同じです。5 位の mean concave points との差は 0.01 しかなく、6 位の mean area は、1 位より 0.04 以上低くなります。冒頭で根になった 5 列は、この上位 5 列とちょうど一致しました。

次に、冒頭と同じ 100 通りの分け方で、学習用の 398 行だけを使って 30 列の減少を計算し直し、1 位と 2 位の差を見ました。

```python
gaps, same = [], 0
for seed in range(100):
    X_tr, _, y_tr, _ = train_test_split(X, y, test_size=0.3, random_state=seed, stratify=y)
    g = np.array([np.nanmax(gain_curve(X_tr[:, j], y_tr)[1]) for j in range(X.shape[1])])
    first, second = np.argsort(g, kind="stable")[::-1][:2]
    gaps.append(g[first] - g[second])
    same += names[first] == roots[seed]
gaps = np.array(gaps)
print("学習 398 行で減少が 1 位の列が、木の根と同じ:", same, "/ 100")
print(f"1 位と 2 位の差 中央値 {np.median(gaps):.4f}  0.01 未満 {(gaps < 0.01).sum()} / 100  最大 {gaps.max():.4f}")
```

```text
学習 398 行で減少が 1 位の列が、木の根と同じ: 99 / 100
1 位と 2 位の差 中央値 0.0039  0.01 未満 83 / 100  最大 0.0268
```

{{< figure src="dt_gain.webp" alt="左は横軸が左の子に入る行の割合、縦軸が Gini 不純度の減少のグラフで、worst radius・worst area・worst perimeter・worst concave points・mean concave points の 5 本の曲線が 0.6〜0.7 の所でほぼ同じ高さ 0.32 前後の山になり、点線の mean area だけが 0.28 と低い。右は分け方を変えた 100 回で、学習 398 行での 1 位と 2 位の列の減少の差を数えたヒストグラムで、0.002 未満が 32 回、0.002〜0.004 が 20 回と 0 の近くに集まり、中央値は 0.0039、一番大きい回でも 0.027" caption="根の候補になる 5 列は Gini 不純度の減少がほぼ同じ高さで、分け方を変えても 1 位と 2 位の差は中央値 0.0039" align="center" >}}

100 回中 99 回は、学習用の行で減少が 1 位の列が、そのまま木の根になりました。1 位と 2 位の差は中央値で 0.0039 しかなく、83 回は 0.01 未満です。学習用の行が少し変わるだけで 1 位が入れ替わる近さなので、根の列が分け方で変わります。

<br>

<details><summary>根が減少 1 位の列にならなかった 1 回</summary>

分け方の乱数が 22 の時で、worst concave points と worst perimeter の減少がぴったり同じでした。scikit-learn の決定木は、分割を探すたびに列を調べる順番を木の乱数で並べ替え、減少が同じ分割が複数あると、その順番で 1 つを選びます。木の `random_state` を固定したのは、この選び方を毎回同じにするためです。

</details>

<br>

5 列の減少がほぼ同じになるのは、どれも腫瘍の大きさか凹みを別の形で測った列だからです。5 列から 2 列を選ぶ 10 組の[相関係数](../../math/correlation/)を計算しました。

```python
top5 = [n_ for _, n_, _ in best[:5]]
cols = [int(np.where(names == n_)[0][0]) for n_ in top5]
corr = np.corrcoef(X[:, cols], rowvar=False)
i, j = np.triu_indices(5, k=1)                     # 2 列を選ぶ 10 組
print("上位 5 列の相関係数 10 組の最小:", round(corr[i, j].min(), 3))
```

```text
上位 5 列の相関係数 10 組の最小: 0.747
```

一番低い組でも 0.747 で、半径・周長・面積の 3 列は互いに 0.978〜0.994 あります。どの列で切っても、ほぼ同じ行が同じ子に入ります。

<br>

#### 2 段目から下も変わる

貪欲に選ぶので、根の列が変わると、その下の 2 つのグループに入る行が変わり、2 段目以降の質問も選び直しになります。根が同じでも、学習用の行が違えば 2 段目以降は変わり得ます。冒頭で根は 5 通りなのに、使った列の組は 96 通りありました。根が worst perimeter だった 46 本だけで数えても、組は 44 通りです。

木の予測は、形ほどには変わりません。100 本から 2 本を選ぶ全ての組で、`preds` に入れた全 569 行への予測を比べました。

```python
same_root_sets = {u for u, r in zip(used, roots) if r == "worst perimeter"}
print("根が worst perimeter の", roots.count("worst perimeter"), "本で、使った列の組の種類:", len(same_root_sets))
P = np.array(preds)
disagree = [(P[i] != P[j]).mean() for i in range(100) for j in range(i + 1, 100)]
print(f"2 本の木で答えが違う行の割合の平均: {np.mean(disagree):.3f}")
```

```text
根が worst perimeter の 46 本で、使った列の組の種類: 44
2 本の木で答えが違う行の割合の平均: 0.047
```

答えが違う行は平均で 4.7% でした。似た意味の列で似た所を切っているためです。

<br>

#### 測り方やモデルを替えた時

不純度の測り方は `criterion` で選べ、Gini 不純度の他に、[情報理論](../../math/information-theory/)のエントロピー `-Σ p_k log_2 p_k` を使う `"entropy"` もあります。エントロピーの減少は情報利得と呼ばれ、分割の結果とクラスの相互情報量に等しくなります。[ID3](https://doi.org/10.1007/BF00116251) などの決定木で使われてきた測り方です。

どちらも、全部が同じクラスで 0、半々で最大になる山形の曲線です。違いは、エントロピーが 0 の近くで急に立ち上がり、少しだけ混ざったグループを重く数える点です。Gini 不純度は対数を計算しない分だけ軽い測り方です。scikit-learn では `criterion` を指定しないと `"gini"` になります。

この測り方や、モデルそのものを替えた時に、1 位の列が 1 つに決まるかも見ました。RandomForest は、データを少しずつ変えて多数の木を学習し、それらの予測を平均するモデルです。その重要度には、不純度の減少を列ごとに足した `feature_importances_` を使います。同じ 100 通りの分け方で、次の 3 つを数えます。

- `criterion="entropy"` で学習した木で、根に選ばれた列
- 200 本の木で学習した RandomForest で、重要度が 1 位の列
- 標準化したロジスティック回帰で、係数の絶対値が 1 位の列

```python
top_entropy, top_forest, top_logreg = [], [], []
same_root, ent_accs = 0, []
for seed in range(100):
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.3, random_state=seed, stratify=y)
    ent = DecisionTreeClassifier(max_depth=3, criterion="entropy", random_state=0).fit(X_tr, y_tr)
    top_entropy.append(str(names[ent.tree_.feature[0]]))
    same_root += top_entropy[-1] == roots[seed]
    ent_accs.append(ent.score(X_te, y_te))         # entropy の木のテスト正解率
    forest = RandomForestClassifier(n_estimators=200, random_state=0).fit(X_tr, y_tr)
    top_forest.append(str(names[np.argmax(forest.feature_importances_)]))
    logreg = make_pipeline(StandardScaler(), LogisticRegression(max_iter=5000)).fit(X_tr, y_tr)
    top_logreg.append(str(names[np.argmax(np.abs(logreg[-1].coef_[0]))]))
print("entropy の根:", Counter(top_entropy).most_common(), " Gini と同じ根:", same_root, "/ 100")
print("テストの正解率の中央値 Gini:", round(np.median(accs), 3), " entropy:", round(np.median(ent_accs), 3))
print("RandomForest の重要度 1 位:", Counter(top_forest).most_common())
print("ロジスティック回帰の係数の絶対値 1 位:", Counter(top_logreg).most_common())
```

```text
entropy の根: [('worst perimeter', 63), ('worst concave points', 19), ('mean concave points', 7), ('worst radius', 6), ('worst area', 5)]  Gini と同じ根: 80 / 100
テストの正解率の中央値 Gini: 0.93  entropy: 0.93
RandomForest の重要度 1 位: [('worst perimeter', 43), ('worst concave points', 43), ('worst radius', 13), ('worst area', 1)]
ロジスティック回帰の係数の絶対値 1 位: [('radius error', 50), ('worst texture', 47), ('fractal dimension error', 1), ('worst symmetry', 1), ('worst smoothness', 1)]
```

entropy でも根は同じ 5 列に分かれ、Gini の木と根が一致したのは 100 回中 80 回でした。中央値で比べたテストの正解率はどちらも 0.93 で、測り方を替えても精度はほとんど変わりません。

RandomForest は多数の木で予測を平均しますが、重要度の 1 位は worst perimeter と worst concave points が 43 回ずつで並び、残る 14 回は worst radius が 13 回、worst area が 1 回でした。

ロジスティック回帰でも、係数の 1 位は radius error が 50 回、worst texture が 47 回で、残る 3 回は別の 3 列でした。列名が error で終わる列は、細胞核ごとに測った値の標準誤差です。

ロジスティック回帰の係数は、他の 29 列を入れた上で、その列が予測をどれだけ動かすかを表します。そのため、1 列だけで一番よく分ける列、つまり木の根と一致するとは限らず、今回も根の候補 5 列とは別の列が 1 位でした。

このデータでは、決定木の根が 5 列に分かれ、RandomForest とロジスティック回帰では、上位 2 列が 1 位の大半をほぼ半々に分けました。木と RandomForest で割れたのは、上で相関を見た大きさと凹みの列どうしです。似た列があると重要度が何本かに分かれる様子や、列を崩して測る [permutation importance](https://scikit-learn.org/stable/modules/permutation_importance.html) との違いは、[特徴量重要度](../feature-importance/)のノートで扱っています。

---

### 木の深さ

`max_depth` の既定は `None` で、葉の中が 1 つのクラスだけになるまで分け続けます。深さを 1〜12 と `None` に変え、5 分割の[交差検証](../cross-validation/)で正解率を測りました。

```python
for d in list(range(1, 13)) + [None]:
    m = DecisionTreeClassifier(max_depth=d, random_state=0)
    s = cross_val_score(m, X, y, cv=5)
    m.fit(X, y)
    print(f"max_depth={str(d):<4} 交差検証 {s.mean():.3f}（±{s.std():.3f}）  学習データ {m.score(X, y):.3f}"
          f"  葉 {m.get_n_leaves()}  根 {names[m.tree_.feature[0]]}")
```

```text
max_depth=1    交差検証 0.900（±0.016）  学習データ 0.923  葉 2  根 worst radius
max_depth=2    交差検証 0.928（±0.010）  学習データ 0.942  葉 4  根 worst radius
max_depth=3    交差検証 0.917（±0.022）  学習データ 0.979  葉 8  根 worst radius
max_depth=5    交差検証 0.916（±0.016）  学習データ 0.995  葉 18  根 worst radius
max_depth=7    交差検証 0.914（±0.010）  学習データ 1.000  葉 22  根 worst radius
max_depth=None 交差検証 0.917（±0.016）  学習データ 1.000  葉 22  根 worst radius
```

出力は一部の深さだけを抜き出しています。

{{< figure src="dt_depth.webp" alt="左は横軸が max_depth の 1〜12 と None、縦軸が正解率の折れ線。灰色の学習に使った 569 行の正解率は深さ 1 の 0.923 から上がり、深さ 7 以降は 1.000。赤い 5 分割の交差検証の正解率は深さ 2 の 0.928 が一番高く、深さ 3 以降は 0.914〜0.917 で横ばい。右は同じ横軸で葉の数の棒グラフで、2、4、8、12、18、21 と増え、深さ 7 以降は 22 で止まる" caption="breast_cancer で、木の深さと正解率・葉の数" align="center" >}}

学習に使った行では深さ 7 で全問正解になり、葉は 22 枚で止まりました。交差検証の正解率は深さ 2 の 0.928 が一番高く、深さ 3 以降は学習データの正解率が上がり続けるのに、交差検証は 0.914〜0.917 のまま上がりません。[過学習](../overfitting/)で説明している「学習データでは良く、未知のデータでは良くならない」状態に近づいています。

ただし、深さ 2 と `None` の差 0.011 は、交差検証 5 回で出た[標準偏差](../../math/stddev/) 0.010〜0.016 と同じくらいです。深い木の方がはっきり悪いとまでは言えません。

学習データで 1.000 になったことだけでは、過学習とは判断できません。ノイズの少ない三日月型のデータ [`make_moons`](https://scikit-learn.org/stable/modules/generated/sklearn.datasets.make_moons.html) で、同じように深さを変えました。

```python
X_m, y_m = make_moons(n_samples=300, noise=0.15, random_state=0)
for d in [2, 5, None]:
    m = DecisionTreeClassifier(max_depth=d, random_state=0)
    s = cross_val_score(m, X_m, y_m, cv=5)
    m.fit(X_m, y_m)
    print(f"make_moons max_depth={str(d):<4} 交差検証 {s.mean():.3f}（±{s.std():.3f}）"
          f"  学習データ {m.score(X_m, y_m):.3f}  葉 {m.get_n_leaves()}")
```

```text
make_moons max_depth=2    交差検証 0.900（±0.035）  学習データ 0.913  葉 4
make_moons max_depth=5    交差検証 0.947（±0.048）  学習データ 0.990  葉 15
make_moons max_depth=None 交差検証 0.977（±0.008）  学習データ 1.000  葉 20
```

make_moons では制限なしの木が 0.977 で一番高くなりました。2 つの月がほとんど重ならないので、学習データを全て当てても葉は 20 枚で済みます。適した深さはデータで変わるので、学習データと交差検証の正解率を並べて決めます。

深さの他に、分ける前のグループに最低何行あれば分けるかの `min_samples_split`、葉 1 枚に最低何行を残すかの `min_samples_leaf`、葉が増えるほど罰を足して効果の小さい枝を落とす `ccp_alpha` でも、木を小さくできます。どれを使っても値は交差検証で選びます。選び方は[ハイパーパラメータ](../hyperparameter/)のノートにまとめています。

出力の右端のとおり、深さを変えても根の列は worst radius のままです。根は深さに関係なく最初に決まるので、浅くしても前の節で見た入れ替わりは止まりません。

---

### 学習した範囲の外

回帰の決定木 [`DecisionTreeRegressor`](https://scikit-learn.org/stable/modules/generated/sklearn.tree.DecisionTreeRegressor.html) は、既定では、子ごとに求めた二乗誤差の合計が一番小さくなる分割を選び、葉に入った学習データの[平均](../../math/mean/)を返します。平均は二乗誤差を一番小さくする定数なので、これは分散が一番減る分割を選ぶことと同じです。入力が 1 列だけなら、学習した範囲の外へ出た入力はどの質問でも同じ向きに進み、端にある葉の平均を返し続けます。

ハワイの Mauna Loa 観測所で 1958 年から測っている大気の CO2 濃度を使い、この様子を見ました。データは [OpenML](https://www.openml.org/d/41187) で公開されている 2001 年までの週ごとの値で、scikit-learn が[ガウス過程回帰を説明する例](https://scikit-learn.org/stable/auto_examples/gaussian_process/plot_gpr_co2.html)でも使われています。年だけを入力にして 1990 年までで学習し、1991〜2001 年を予測させます。

```python
co2 = fetch_openml(data_id=41187, as_frame=True).frame
year = (co2.year + (co2.month - 1) / 12 + (co2.day - 1) / 365).to_numpy()
ppm = co2.co2.to_numpy()
train = year < 1991                                  # 1958〜1990 年で学習、1991〜2001 年を予測
T = year.reshape(-1, 1)
models = {
    "決定木（max_depth=6）": DecisionTreeRegressor(max_depth=6, random_state=0),
    "RandomForest": RandomForestRegressor(n_estimators=200, random_state=0),
    "HistGradientBoosting": HistGradientBoostingRegressor(random_state=0),
    "線形回帰": LinearRegression(),
}
for label, m in models.items():
    m.fit(T[train], ppm[train])
    p = m.predict(T[~train])
    print(f"{label:<22} 1991 年以降の平均絶対誤差 {np.abs(p - ppm[~train]).mean():5.2f} ppm"
          f"  予測の範囲 {p.min():.1f}〜{p.max():.1f}")
```

```text
決定木（max_depth=6）       1991 年以降の平均絶対誤差 10.34 ppm  予測の範囲 352.4〜352.4
RandomForest           1991 年以降の平均絶対誤差  8.30 ppm  予測の範囲 354.6〜354.6
HistGradientBoosting   1991 年以降の平均絶対誤差 10.03 ppm  予測の範囲 352.7〜352.7
線形回帰                   1991 年以降の平均絶対誤差  4.00 ppm  予測の範囲 352.1〜365.7
```

{{< figure src="dt_co2.webp" alt="横軸が 1958〜2001 年、縦軸が CO2 濃度の折れ線。灰色の実測は 315 ppm 付近から季節の波を描きながら 374 ppm まで上がる。1990 年までは決定木、RandomForest、HistGradientBoosting が実測の波に沿って階段状に上がる。1991 年以降の網掛けの期間では、赤い決定木が 352.4、橙の RandomForest が 354.6、HistGradientBoosting が 352.7 から動かない直線になり、青い線形回帰だけが 365.7 まで上がり続ける" caption="1990 年までで学習したモデルが、1991〜2001 年の CO2 濃度を予測した結果" align="center" >}}

決定木は 1991 年から 11 年間、ずっと 352.4 ppm を返しました。実測は 2001 年に 373.9 ppm まで上がっています。1990 年までは、決定木も階段状ながら実測に沿って上がっていたのに、範囲を出た所からは、どの木のモデルも 1 つの値を返し続けました。

RandomForest や、[勾配ブースティング](../gradient-boosting/)を scikit-learn で実装した HistGradientBoosting も、中身は回帰の木です。入力が年の 1 列だけなので、範囲の外ではどの木も端にある葉の値を返し、木の値を平均しても足しても予測は一定のままです。入力に比例して伸びる[線形回帰](../linear-regression/)は、季節の波は追えなくても、平均絶対誤差は 4.00 ppm で、決定木の半分以下でした。

売上や利用者数のように、増え続ける量を時刻から予測する時はこの性質が問題になります。傾向を線形のモデルで取り除いた残りや、1 つ前の時点からの差を木に学習させる手があります。そうすれば、木は学習した範囲に収まる値を予測するだけで済みます。傾向を取り出す方法は、[時系列予測](../time-series-forecasting/)のノートで扱っています。

---

### 斜めの境界

木の質問は 1 つの列だけを見るので、境界は必ず軸に平行な線の組み合わせになります。同じ 400 個の点に、境界が縦の直線になるラベルと、45 度の直線になるラベルを付けて比べました。

```python
rng = np.random.default_rng(0)
Z = rng.uniform(-1, 1, (400, 2))
for deg in [0, 45]:
    w = np.array([np.cos(np.radians(deg)), np.sin(np.radians(deg))])
    label = (Z @ w > 0).astype(int)                  # 境界は w に直交する直線
    tree = DecisionTreeClassifier(random_state=0)
    logreg = LogisticRegression()
    print(f"{deg:>2} 度: 決定木 交差検証 {cross_val_score(tree, Z, label, cv=5).mean():.3f}"
          f"  葉 {tree.fit(Z, label).get_n_leaves()}"
          f"  ロジスティック回帰 交差検証 {cross_val_score(logreg, Z, label, cv=5).mean():.3f}")
```

```text
 0 度: 決定木 交差検証 0.997  葉 2  ロジスティック回帰 交差検証 0.982
45 度: 決定木 交差検証 0.945  葉 22  ロジスティック回帰 交差検証 0.978
```

{{< figure src="dt_rotate.webp" alt="3 枚の散布図。左は境界が縦の直線のデータに決定木を当てた図で、葉 2 枚の 1 本の縦線で赤と青が分かれる。中央は境界が 45 度のデータに決定木を当てた図で、葉 22 枚の階段状の境界になり、ところどころで点の色と塗りがずれる。右は同じ 45 度のデータにロジスティック回帰を当てた図で、1 本の斜めの直線で分かれる" caption="境界が軸に沿うデータと 45 度のデータで、決定木とロジスティック回帰の境界" align="center" >}}

境界が縦なら、決定木は葉 2 枚、つまり 1 つの質問で分けられます。同じ点で境界を 45 度に回しただけで、葉は 22 枚の階段になり、交差検証の正解率は 0.997 から 0.945 に下がりました。ロジスティック回帰は境界を斜めの直線で引けるので、向きに関係なく 0.98 前後です。

斜めの境界を持つデータでは、手が 2 つあります。1 つは、ロジスティック回帰や [SVM](../svm/)（サポートベクターマシン）のように斜めの境界を引けるモデルに替えることです。もう 1 つは、2 つの列の差や比を列として足しておくことで、木はその列への 1 つの質問で切れるようになります。データの点を回す [PCA](../pca/) を前処理に入れても木の結果は変わりますが、PCA は正解のラベルを見ないので、主軸が境界の向きに揃うとは限りません。

---

### 決定木を使う前に

決定木を使うかを判断する材料として、ここまでの実験を RandomForest とロジスティック回帰と並べると次のとおりです。最後の行だけは実験ではなく、後の「前処理と列の型」で説明する性質です。

| 知りたいこと | 決定木 | RandomForest | ロジスティック回帰 |
|---|---|---|---|
| 判断の根拠を見せる | 木の図で見せられる | 木が 200 本あり見せにくい | 係数で見せられる |
| 分け方を変えた時の 1 位の列 | 根の列が 5 通り | 重要度 1 位は 43 回ずつの 2 列が大半 | 係数 1 位は 50 回と 47 回の 2 列が大半 |
| 学習した範囲の外 | 端にある葉の値のまま | 端の値のまま | 直線で伸びる |
| 斜めの境界 | 葉 22 枚の階段 | 測っていない | 1 本の直線 |
| 列ごとにスケールが違う | 影響しない | 影響しない | 標準化した方がよい |

決定木を説明に使うなら、まず `train_test_split` の乱数や交差検証の分割を変えて何本か学習し、根の列が変わるかを数えます。冒頭の図のように数通りに分かれるなら、根の 1 列を「一番重要な列」と報告せず、減少がほぼ同じ列をまとめて「腫瘍の大きさか凹みを測る列のどれか」のように伝えます。[特徴量選択](../feature-selection/)で似た列を 1 つに絞ってから学習する手もあります。

breast_cancer では、RandomForest やロジスティック回帰に替えても 1 位は 1 列に決まらず、上位 2 列が占めたのは RandomForest で 100 回中 86 回、ロジスティック回帰で 97 回でした。

<br>

#### 前処理と列の型

質問は「閾値以下か」だけなので、木は値が大きいか小さいかしか使いません。列を[標準化](../standardization/)しても、並び順は同じなので学習用の行は同じ側に分かれ、閾値の数字だけが変わります。[kNN](../knn/) や[ロジスティック回帰](../logistic-regression/)のように、列の大きさをそろえる前処理を決定木は要しません。

<br>

<details><summary>対数のように値の間隔まで変える変換の場合</summary>

並び順は変わらないので、学習用の行は同じように分かれます。ただ、閾値は隣り合う 2 つの値の中点に置かれるので、その間に入る新しい行の行き先は変わることがあります。

</details>

<br>

[欠損値](../missing-values/)は、scikit-learn [1.3](https://scikit-learn.org/stable/auto_examples/release_highlights/plot_release_highlights_1_3_0.html) からは、既定の `splitter="best"` で欠損の行を左右どちらに送るかを学習します。勾配ブースティングの [XGBoost](https://xgboost.readthedocs.io/en/stable/faq.html) と [LightGBM](https://lightgbm.readthedocs.io/en/stable/Advanced-Topics.html) も送る向きを学習します。[CatBoost](https://catboost.ai/docs/en/concepts/algorithm-missing-values-processing) は、既定では欠損を一番小さい値として扱います。

一方で、文字列で書かれたカテゴリの列は、本記事で使った scikit-learn 1.9.1 の決定木に渡すと、数値へ変換できないというエラーになります。数値への[エンコーディング](../categorical-encoding/)が要ります。LightGBM は整数か pandas の category 型にした列なら、CatBoost は文字列のままの列でも、カテゴリとして内部で扱えます。

悪性と良性のように件数の違うクラスでは、`class_weight="balanced"` を指定すると、少ないクラスの行を重く数えて不純度を計算します。件数が偏った時の扱いは[クラス不均衡](../class-imbalance/)のノートにまとめています。

<br>

#### 精度や深さを決める時

予測の精度が目的なら、木を[アンサンブル学習](../ensemble-learning/)の部品にする手があります。[RandomForest のノート](../random-forest/)では、学習データから 24 通りの標本を作り、単体の深い木と RandomForest で、テストの正解率を比べました。そのデータでは、24 通りの全てで RandomForest が上回っています。

ただし、CO2 の実験のように学習した範囲の外を予測するなら、どちらも木なので、予測したい値が学習データの範囲に収まるかを先に見ます。

深さは、交差検証で浅い方から試します。breast_cancer では深さ 2 の 4 枚の葉が、深い木と同じくらいの正解率で、人に見せるにも十分な大きさでした。make_moons のように制限なしの木が一番良いデータもあります。冒頭の図で 100 本の正解率がどれも 0.87〜0.97 に収まったように、見せる 1 本を選ぶ時は、正解率ではなく、分け方を変えても残る質問かどうかで選ぶのが 1 つの手です。この選び方や、特徴量選択で列を絞る手で説明が安定するかは、本記事では試していません。
