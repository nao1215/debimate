---
title: "DBSCAN - 塊の間に密度の低い所が無ければ、eps をどう選んでも分かれない"
date: 2026-05-26
draft: false
series: ["機械学習ノート", "Machine Learning"]
tags: ["machine-learning", "scikit-learn", "unsupervised"]
weight: 29
topics: ["Machine Learning（評価・概念・アルゴリズム）"]
---

[DBSCAN](https://cdn.aaai.org/KDD/1996/KDD96-037.pdf)（Density-Based Spatial Clustering of Applications with Noise）は、点が密に集まった所をクラスタにまとめ、まばらな所にある点をノイズとして外すクラスタリングの手法です。学習の前に人が決める[ハイパーパラメータ](../hyperparameter/)は、半径 `eps` と点の数 `min_samples` の 2 つです。

各点から半径 `eps` 以内の範囲をその点の近傍（neighborhood）と呼び、近傍に `min_samples` 個以上の点がある所を「密」とみなし、近傍に入る点がそれより少ない所を本記事では密度の低い所と呼びます。クラスタの数を先に決めない所が、[k-means](../k-means/) との大きな違いです。

DBSCAN は、地図上の位置から店舗の集まりを探す、文章の埋め込みを話題ごとにまとめる、ログの中から[外れた点](../anomaly-detection/)を見つける、といったクラスタの数が分からない場面でよく名前が挙がる手法です。scikit-learn なら 2 行で動きます。ただし `eps` の既定値は 0.5 で、点どうしの距離の大きさを見ずに使うと、全ての点が -1（ノイズ）になったり、全体が 1 つのクラスタになったりします。

DBSCAN の紹介では、k-means と比べた長所として次のような説明をよく見かけます。どれも成り立ちそうですが、実際に試すと条件付きでしか成り立ちませんでした。右の列は、本記事で各説明を試す節です。

| よく見る説明 | 試す節 |
|---|---|
| 1. クラスタの数を決めなくてよい | eps とクラスタの数 |
| 2. `eps` を合わせれば、密度の違う塊も同時に拾える | 密度の違う塊 |
| 3. k-means で分かれるデータなら、形を選ばない DBSCAN でも分かれる | wine が分かれない理由 |
| 4. 近くの点を数えるだけなので、大きいデータでも軽い | 近傍の数とメモリ |

[scikit-learn](https://scikit-learn.org/stable/) に同梱の [wine](https://scikit-learn.org/stable/modules/generated/sklearn.datasets.load_wine.html) で、3 つ目の説明を試しました。wine は、3 品種のブドウから作ったワイン 178 本について、化学分析で得た値を 13 列に並べたデータです。13 列は単位も桁も違うので、各列を平均 0・[標準偏差](../../math/stddev/) 1 にそろえる[標準化](../standardization/)をしてから分けました。

分けた結果が品種とどれだけ合うかは、[ARI](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.adjusted_rand_score.html)（Adjusted Rand Index、調整ランド指数）で測ります。ARI は、2 つの分け方が同じなら 1、でたらめに分けた時と同じ程度なら 0 付近になる値です。

{{< figure src="dbscan_cover.webp" alt="横軸が eps（1.0〜4.0）、縦軸が min_samples（2〜30）のマス目で、色の濃さが品種との ARI。ARI が 0 より大きいのは、左下から右上へ斜めに伸びる帯の中だけで、帯の中も 0.2〜0.5 の薄い青。赤い星の最大は eps=2.55、min_samples=23 の 0.54。右の色の目盛りには、k-means の 0.90 を赤い線で示している" caption="標準化した wine を DBSCAN で分けた 1769 通りの ARI" align="center" >}}

`eps` を 1.0〜4.0、`min_samples` を 2〜30 の範囲で 1769 通り総当たりしても、ARI は最大で 0.54 でした。その時のクラスタは 2 個で、55% の点がノイズです。ARI はノイズの -1 も 1 つのまとまりとして数えて求めたので、0.54 は 55% のノイズを 3 つ目のまとまりとみなした値です。同じデータを k=3 の k-means で分けると、ARI は 0.90 になります。

<br>

本記事では、最初に DBSCAN が何を数えてどの点をクラスタやノイズにするかを説明し、続く節で冒頭の表に並べた 4 つの説明を順に試します。実験は scikit-learn 1.9.1 と、配列の計算に使う [NumPy](https://numpy.org/) 2.5.4 で行い、完全なコードは [dbscan_gen.py](https://github.com/nao1215/debimate/blob/main/projects/ml/scripts/notes/dbscan_gen.py) にあります。

---

### コア点・境界点・ノイズ

DBSCAN は、点を 3 種類に分けます。近傍に、自分を含めて `min_samples` 個以上の点がある点がコア点（core point）です。コア点ではないものの、どれかのコア点の近傍に入っている点が境界点（border point）で、どのコア点の近傍にも入らない点がノイズ（noise）です。scikit-learn は、ノイズのラベルを -1 で返します。

クラスタは、コア点からコア点へ近傍を伝って届く範囲（原論文の density-reachable）です。伝っていけるコア点は全て同じクラスタになり、その周りの境界点も同じクラスタに入ります。29 点の小さなデータで、3 種類を数えました。

```python
toy = np.vstack([
    rng.normal([0.0, 0.0], 0.35, size=(14, 2)),
    rng.normal([2.4, 0.4], 0.35, size=(12, 2)),
    [[1.2, 1.5], [3.6, -1.0], [-1.0, 1.4]],
])
model = DBSCAN(eps=0.5, min_samples=4).fit(toy)
is_core = np.zeros(len(toy), bool)
is_core[model.core_sample_indices_] = True
kind = np.where(is_core, "コア点", np.where(model.labels_ == -1, "ノイズ", "境界点"))
print("実験 1:", {k: int((kind == k).sum()) for k in ["コア点", "境界点", "ノイズ"]})
```

```text
実験 1: {'コア点': 20, '境界点': 3, 'ノイズ': 6}
```

{{< figure src="dbscan_points.webp" alt="29 点の散布図に、半径 0.5 の点線の円を 3 つ描いている。左の青い塊の中心のコア点は近傍に 8 点がある。その左の白抜きの境界点の近傍には自分と 1 つのコア点の 2 点しかないが、コア点の近傍にいるので青のクラスタに入る。下の灰色の x のノイズの近傍には自分の 1 点だけがある。右には橙のクラスタがあり、塊から離れた 6 点が x" caption="コア点・境界点・ノイズ（eps=0.5、min_samples=4）" align="center" >}}

境界点の近傍には 2 点しかありませんが、すぐ右のコア点から半径 `eps` 以内にいるので、青のクラスタに入ります。ノイズの近傍には自分しかいません。

この数え方は、塊の形を選びません。[k-means](https://scikit-learn.org/stable/modules/generated/sklearn.cluster.KMeans.html) はクラスタの中心からの距離で点を分けるので、丸い塊を前提にしています。[`make_moons`](https://scikit-learn.org/stable/modules/generated/sklearn.datasets.make_moons.html) で作った三日月形の 2 つの塊に 20 点のばらばらな点を足して、2 つを比べました。

```python
Xm, ym = make_moons(n_samples=400, noise=0.06, random_state=0)
Xm = np.vstack([Xm, np.random.default_rng(1).uniform([-1.2, -0.7], [2.2, 1.2], size=(20, 2))])
ym = np.r_[ym, np.full(20, -1)]
lab_km = KMeans(n_clusters=2, n_init=10, random_state=0).fit_predict(Xm)
lab_db = DBSCAN(eps=0.15, min_samples=5).fit_predict(Xm)
```

```text
実験 2: k-means の ARI 0.263、DBSCAN の ARI 1.000、DBSCAN のクラスタ 2 個、ノイズ 11 点（足した 20 点のうち 11 点）
```

{{< figure src="dbscan_moons.webp" alt="左右に同じ三日月のデータ。左の k-means は画面を左右に切るように分け、上の三日月の右端と下の三日月の左端が違う色になる。右の DBSCAN は上の三日月が青、下の三日月が橙のクラスタになり、三日月から離れた点は灰色の x のノイズになる" caption="三日月形の 2 つの塊を分けた k-means と DBSCAN" align="center" >}}

三日月の 400 点の ARI は、k-means が 0.263、DBSCAN が 1.000 でした。足した 20 点のうち 11 点はノイズになり、残りの 9 点は三日月の近くに落ちたので、三日月のクラスタに入りました。なお、DBSCAN は k-means のようなクラスタの中心を返しません。中心が要る時は、クラスタごとに点の平均を後から求めます。

---

### eps とクラスタの数

DBSCAN はクラスタの数を受け取りませんが、数は `eps` で決まります。三日月のデータで、`min_samples` を 5 にしたまま `eps` を 0.02 から 0.50 まで 0.01 ずつ動かしました。

```python
eps_list = np.round(np.arange(0.02, 0.501, 0.01), 2)
ks, noise = [], []
for eps in eps_list:
    lab = DBSCAN(eps=eps, min_samples=5).fit_predict(Xm)
    ks.append(n_clusters(lab))         # -1 を除いたラベルの種類
    noise.append(np.mean(lab == -1))
```

```text
実験 3: eps=0.05 クラスタ 28 個、ノイズ 57%
実験 3: eps=0.10 クラスタ  4 個、ノイズ 6%
実験 3: eps=0.15 クラスタ  2 個、ノイズ 3%
実験 3: eps=0.20 クラスタ  2 個、ノイズ 1%
実験 3: eps=0.30 クラスタ  1 個、ノイズ 0%
実験 3: クラスタが 2 個になる eps の範囲 0.12〜0.20
```

`eps` が小さいと近傍に入る点が足りず、ほとんどの点がノイズになり、残ったコア点が小さなクラスタに分かれます。`eps` を広げるとクラスタがつながって数が減り、0.21 以上では 2 つの三日月が 1 つになりました。正しく 2 つに分かれるのは 0.12〜0.20 の幅だけです。

`eps` は距離そのものなので、列の単位で意味が変わります。メートルとキロメートルの列が混ざっていれば、メートルの列だけで距離が決まります。単位の違う列は標準化してから `eps` を選びます。

`eps` を選ぶ目安として、原論文は k-距離グラフ（sorted k-dist graph）を挙げています。各点から k 番目に近い点までの距離を小さい順に並べた線で、[kNN](../knn/) と同じ近傍の探索で求まり、scikit-learn では [`NearestNeighbors`](https://scikit-learn.org/stable/modules/generated/sklearn.neighbors.NearestNeighbors.html) を使います。点の多い所では緩やかに伸び、まばらな点の所で急に立ち上がります。立ち上がる手前の距離を `eps` にすると、手前の点はコア点になり、急に立ち上がった先の点はノイズになります。

```python
# min_samples=5 は自分を含めて 5 点なので、自分以外で 4 番目に近い点までの距離を並べる
kdist = np.sort(NearestNeighbors(n_neighbors=4).fit(Xm).kneighbors()[0][:, -1])
```

```text
実験 3: 4 番目に近い点までの距離 中央値 0.066、95% 点 0.148
```

距離を小さい順に並べた線は、距離の[分位点](../../math/quantile/)を左から並べたものと同じです。95% 点は、95% の点がその距離以内に 4 番目の点を持つ値で、ここでは 0.148 でした。この値はクラスタが 2 個になる帯（0.12〜0.20）に入りますが、目安の 1 つで、決め方の規則ではありません。列の尺度や `min_samples`、どれだけノイズを許すかで候補は変わるので、候補ごとにクラスタ数とノイズを見ます。

{{< figure src="dbscan_eps.webp" alt="左は横軸が eps のグラフで、青の実線がクラスタの数、赤の破線がノイズの割合。eps が 0.06 付近でクラスタの数は 31 個まで増え、そこから減って 0.12〜0.20 の緑の帯で 2 個になり、0.21 から 1 個になる。ノイズの割合は eps=0.02 の 100% 近くから下がり、0.1 で 6%。右は k-距離グラフで、420 点の 4 番目に近い点までの距離を小さい順に並べた線。400 点目あたりまでは 0.15 以下で緩やかに伸び、残りの 20 点で 0.5 まで急に立ち上がる。立ち上がりの手前が、緑のクラスタが 2 個になる eps の帯に重なる" caption="eps とクラスタの数・ノイズの割合（左）と、k-距離グラフ（右）" align="center" >}}

k-距離グラフは、足したばらばらの 20 点の所で急に立ち上がり、その手前の距離はクラスタが 2 個になる `eps` の帯に入っています。原論文は 2 次元のデータで k を 4 に固定し、`min_samples` も 4 にすることを勧めています。

列が多いデータには、原論文の著者らが 2017 年に書いた論文 [DBSCAN Revisited, Revisited](https://doi.org/10.1145/3068335) が紹介する、`min_samples` を列数の 2 倍にする目安があります。同じ論文は、ノイズが多い、データが大きい、重複した点が多いといった時は `min_samples` を増やすと結果が良くなることがあるとしています。

<br>

<details>
<summary>余談: min_samples=1 の DBSCAN は階層的クラスタリングと一致する</summary>

`min_samples` を 1 にすると、全ての点がコア点になってノイズが出ません。

[階層的クラスタリング](../hierarchical-clustering/)は、近いクラスタどうしを順につなぎ、つないだ時の距離を高さにした木を作る手法で、2 つのクラスタの中で最も近い 2 点の距離を使うつなぎ方を single と呼びます。この木を高さ `eps` で横に切ると、`eps` 以内で鎖のようにつながる点が同じクラスタに入ります。三日月の 400 点で、`min_samples=1` の DBSCAN とこの木を比べました。

```python
Z = linkage(Xm[:400], method="single")  # SciPy の single の木
for eps in [0.05, 0.10, 0.15]:
    lab_1 = DBSCAN(eps=eps, min_samples=1).fit_predict(Xm[:400])
    lab_s = fcluster(Z, t=eps, criterion="distance")  # 木を高さ eps で切る
    print(f"実験 3: eps={eps:.2f} min_samples=1 のクラスタ {n_clusters(lab_1)} 個、ノイズ {(lab_1 == -1).sum()}、"
          f"single の木との ARI {adjusted_rand_score(lab_1, lab_s):.3f}")
```

```text
実験 3: eps=0.05 min_samples=1 のクラスタ 128 個、ノイズ 0、single の木との ARI 1.000
実験 3: eps=0.10 min_samples=1 のクラスタ 10 個、ノイズ 0、single の木との ARI 1.000
実験 3: eps=0.15 min_samples=1 のクラスタ 2 個、ノイズ 0、single の木との ARI 1.000
```

どの `eps` でも ARI は 1.000 で、2 つの分け方は一致しました。

</details>

<br>

クラスタの数を決めなくてよい、という冒頭の 1 つ目の説明は、正しくは、数の代わりに `eps` を決める、です。

---

### 密度の違う塊

DBSCAN の密度は、[KDE](../../math/kde/) のように場所ごとに滑らかな値を推定したものではなく、半径 `eps` の近傍に入る点の数です。その `eps` は全ての点に共通の 1 つの値です。原論文も、全てのクラスタに同じ `eps` と `min_samples` を使うので、密度の違う 2 つの塊が近くにあると 1 つにまとめうると書いています。

[`make_blobs`](https://scikit-learn.org/stable/modules/generated/sklearn.datasets.make_blobs.html) で密な 300 点の塊を 2 つ並べ、離れた所にまばらな 200 点の塊を 1 つ置いて、`eps` を 0.05 から 1.50 まで動かしました。

```python
Xd, yd = make_blobs(n_samples=[300, 300], centers=[[0, 0], [1.6, 0]], cluster_std=0.25, random_state=0)
Xs, _ = make_blobs(n_samples=[200], centers=[[5, 4]], cluster_std=1.2, random_state=1)
Xv = np.vstack([Xd, Xs])
yv = np.r_[yd, np.full(200, 2)]
rows = []
for eps in np.round(np.arange(0.05, 1.501, 0.05), 2):
    lab = DBSCAN(eps=eps, min_samples=5).fit_predict(Xv)
    a, b = set(lab[yv == 0]) - {-1}, set(lab[yv == 1]) - {-1}
    dense_split = bool(a) and bool(b) and not (a & b)  # 密な 2 つが同じ塊に入っていない
    rows.append((eps, n_clusters(lab), np.mean(lab[yv == 2] == -1), dense_split))
```

```text
実験 4: eps=0.20 クラスタ  7 個、疎な塊のノイズ 84%、密な 2 つが別のクラスタ True
実験 4: eps=0.35 クラスタ  8 個、疎な塊のノイズ 28%、密な 2 つが別のクラスタ True
実験 4: eps=0.40 クラスタ  3 個、疎な塊のノイズ 22%、密な 2 つが別のクラスタ False
実験 4: eps=0.50 クラスタ  2 個、疎な塊のノイズ 17%、密な 2 つが別のクラスタ False
実験 4: 密な 2 つが別のクラスタになる eps の上限 0.35、その時の疎な塊のノイズ 28%
```

密な 2 つが別のクラスタに分かれるのは `eps` が 0.35 までで、その時、まばらな塊は 28% がノイズになり、残りも小さなクラスタに割れています。`eps` を 0.40 にすると、まばらな塊はまとまり始めますが、密な 2 つが 1 つになります。0.50 ではまばらな塊が 1 つのクラスタにまとまり、クラスタは 2 個です。3 つの塊を 3 つのクラスタとして返す `eps` はありませんでした。

この問題に向けた手法が [HDBSCAN](https://scikit-learn.org/stable/modules/generated/sklearn.cluster.HDBSCAN.html) です。Campello 氏、Moulavi 氏と、DBSCAN の原論文を書いた 1 人でもある Sander 氏が [2013 年に提案](https://doi.org/10.1007/978-3-642-37456-2_14)し、scikit-learn には 1.3 で入りました。HDBSCAN は `eps` を 1 つに決めず、`eps` を動かした時の分かれ方を全て調べてから、クラスタを選びます。決めるのは、クラスタとして認める最小の点数 `min_cluster_size` です。

```python
lab_h = HDBSCAN(min_cluster_size=10, copy=True).fit_predict(Xv)
```

```text
実験 4: HDBSCAN（min_cluster_size=10）クラスタ 3 個、ノイズ 1.4%、ARI 0.983
```

{{< figure src="dbscan_density.webp" alt="3 枚の散布図。左下に密な小さい塊が 2 つ、右上にまばらな大きい塊が 1 つある。左の DBSCAN eps=0.2 は密な 2 つを橙と青に分けるが、右上の塊は 84% が灰色の x のノイズで、残りが 4 つの小さなクラスタに割れる。中央の eps=0.5 は右上の塊を橙の 1 つにまとめるが、密な 2 つが同じ青になる。右の HDBSCAN は密な 2 つを緑と橙、右上を青に分け、ノイズは 1%" caption="密度の違う 3 つの塊を分けた DBSCAN（2 つの eps）と HDBSCAN" align="center" >}}

HDBSCAN は 3 つの塊を 3 つのクラスタとして返し、ノイズは 1.4% でした。HDBSCAN がどう選んだかを次の図で見ます。左は HDBSCAN が作った木で、右は似た考え方の [OPTICS](https://scikit-learn.org/stable/modules/generated/sklearn.cluster.OPTICS.html) で同じ点を並べた結果です。

{{< figure src="dbscan_tree.webp" alt="左は HDBSCAN の木で、縦軸は距離、線の太さはその枝に残っている点の数。一番上の灰色の幹が 1.44 で 2 つに分かれ、右の青い縦線がまばらな塊の 192 点で 0.32 まで続く。左の灰色の枝は 0.38 で橙の密な塊 297 点と緑の密な塊 300 点に分かれ、どちらも 0.07 付近まで続く。赤い破線の eps=0.35 は、橙・緑・青の 3 本を同時に横切る。右は OPTICS が並べた 800 点の棒グラフで、縦軸は到達可能距離。0〜300 番目の橙と 300〜600 番目の緑は 0.1 前後の低い谷で、間の山は 0.38。600〜800 番目の青のまばらな塊は 0.1〜0.4 の高さでぎざぎざに続き、最後の数十点で 0.9 近くまで上がる。赤い横線が eps=0.35 と eps=0.5" caption="HDBSCAN の木（左）と、OPTICS が並べた点の到達可能距離（右）" align="center" >}}

<br>

<details>
<summary>補足: 木・OPTICS と DBSCAN の対応</summary>

木をある高さで横に切ると、同じ `min_samples` の DBSCAN をその `eps` で動かし、境界点をノイズとして扱った時の分け方になります。HDBSCAN の `min_samples` は、指定しなければ `min_cluster_size` と同じ 10 で、左の木はこの値で描いています。

右の OPTICS では、`min_samples` を実験 4 で DBSCAN に渡した値と同じ 5 にしたので、2 本の線は実験 4 の `eps`=0.35 と 0.5 の結果に対応します。左右で `min_samples` が違うので同じ高さで残る点は少し違いますが、密な 2 つが 0.38 付近で分かれる所はどちらも同じです。

</details>

<br>

左の木は、縦軸の距離を `eps` とみなし、上から下へ小さくしていった時に、10 点以上の集まりがどこで 2 つに割れるかを描いたものです。線の太さは、その枝に残っている点の数を表します。

1.44 でまばらな塊の 192 点が分かれ、0.38 で密な 2 つが分かれます。下へ行くほど近傍に入る点が減るので、点はコア点でなくなって少しずつ木から外れます。横に 1 本の線で、色の付いた 3 本の線を同時に切れるのは、0.32〜0.38 の狭い幅だけです。図の赤い破線の 0.35 で切った時に、木に残る点を数えました。

```python
# 自分を含めて 10 点が半径 h に入る点（自分以外で 9 番目に近い点までの距離が h 以下の点）が、高さ h で木に残る
cd10 = NearestNeighbors(n_neighbors=9).fit(Xv).kneighbors()[0][:, -1]
h = 0.35
print(f"実験 4: 木を高さ {h} で切った時に残る点 密な塊 {(cd10[yv < 2] <= h).sum()} / 600、"
      f"まばらな塊 {(cd10[yv == 2] <= h).sum()} / 200")
```

```text
実験 4: 木を高さ 0.35 で切った時に残る点 密な塊 596 / 600、まばらな塊 32 / 200
```

密な塊はほぼ全ての点が残りますが、まばらな塊は 200 点のうち 32 点しか残っていません。HDBSCAN は高さを 1 つに決めず、縦に長く分かれたまま残る枝を枝ごとに違う高さで選ぶので、3 つの塊を両方の密度で拾えます。

右の OPTICS は、近い点が隣に来る順に点を並べ、それまでに並べた点からその点までの到達可能距離（reachability distance）を記録します。到達可能距離は、並べ済みの点のどれかがコア点になり、しかもその近傍にこの点が入る、最小の `eps` です。塊の中は到達可能距離が短いので谷になり、塊の間は山になります。

横に `eps` の線を引き、線より下で続く谷を 1 つのクラスタとすると、その `eps` の DBSCAN とほぼ同じ分け方を後から切り出せます。0.35 の線では密な 2 つが間の山で分かれますが、まばらな塊の谷は線を越える棒で細かく切れます。0.5 の線では、密な 2 つの間の山が線の下に入って 1 つにつながります。

`eps` を合わせれば密度の違う塊も拾える、という冒頭の 2 つ目の説明は、密な塊どうしが、まばらな塊をまとめる `eps` でもつながらないほど離れている時にしか成り立ちません。実験 4 のように密な塊が近くに並んでいると、どの `eps` でも 3 つには分かれないので、密度の違う塊が混ざると分かっていれば、先に HDBSCAN を試す方が早く分けられます。

---

### wine が分かれない理由

冒頭の wine では、HDBSCAN も品種どおりには分けられませんでした。`min_cluster_size` を 5〜30 で動かして、ARI は最大で 0.342 です。総当たりのコードと、その結果の内訳は次の通りです。

```python
wine = load_wine()
Xw = StandardScaler().fit_transform(wine.data)
yw = wine.target
eps_grid = np.round(np.arange(1.0, 4.001, 0.05), 2)
ms_grid = np.arange(2, 31)
ari = np.zeros((len(ms_grid), len(eps_grid)))
k_grid = np.zeros_like(ari, dtype=int)
noise_grid = np.zeros_like(ari)
for i, ms in enumerate(ms_grid):
    for j, eps in enumerate(eps_grid):
        lab = DBSCAN(eps=eps, min_samples=ms).fit_predict(Xw)
        ari[i, j] = adjusted_rand_score(yw, lab)   # ノイズの -1 も 1 つのまとまりとして数える
        k_grid[i, j] = n_clusters(lab)
        noise_grid[i, j] = np.mean(lab == -1)
```

```text
実験 5: 組み合わせ 1769 通り、ARI の最大 0.544（eps=2.55、min_samples=23、クラスタ 2 個、ノイズ 55%）
実験 5: クラスタが 3 個になった 62 通りの ARI の最大 0.467（ノイズ 43%）
実験 5: クラスタが 3 個でノイズ 10% 未満の組み合わせ 9 通り、その ARI の最大 0.001
実験 5: k-means（k=3）の ARI 0.897、HDBSCAN（min_cluster_size 5〜30）の ARI の最大 0.342
```

クラスタがちょうど 3 個になった組み合わせは 62 通りあり、ARI は最大で 0.467、その時のノイズは 43% でした。ノイズを 10% 未満に抑えて 3 個になった 9 通りは、ARI がほぼ 0 です。9 通りとも `min_samples` が 2 で、178 本のうち 158〜168 本が 1 つのクラスタに入り、残りの 2 個は 2〜3 本ずつの小さなクラスタでした。

<br>

#### コア点どうしがつながる eps

DBSCAN で 2 つの品種を分けるには、どちらの品種の点もコア点になり、しかも 2 つの品種のコア点が互いの近傍に入らない `eps` が要ります。そこで `min_samples` を 5 にして、品種ごとにコア点になる点の割合が `eps` でどう増えるかと、違う品種のコア点どうしが初めて近傍でつながる `eps` を求めました。比べるために、make_blobs で作った離れた 3 つの塊でも同じものを求めています。

2 つの点がコア点どうしでつながるには、2 点の距離が `eps` 以内で、しかも 2 点のどちらもコア点でなければなりません。点ごとにコア点になる最小の `eps` を `core_dist` で求めておけば、つながる最小の `eps` は、距離と 2 点の `core_dist` のうち最も大きい値になります。`link_eps` は、品種 a の点と品種 b の点を 1 つずつ選ぶ全ての組でそれを求め、最小を取ります。

```python
def core_dist(X, ms):
    """自分を含めて ms 点が半径に入る最小の eps（自分以外で ms-1 番目に近い点までの距離）。"""
    return NearestNeighbors(n_neighbors=ms - 1).fit(X).kneighbors()[0][:, -1]


def link_eps(X, y, cd, a, b):
    """品種 a と b のコア点どうしが半径 eps でつながる最小の eps。"""
    D = cdist(X[y == a], X[y == b])
    return np.maximum(D, np.maximum(cd[y == a][:, None], cd[y == b][None, :])).min()
```

```text
実験 6: 離れた 3 つの塊（make_blobs）: 最初につながる組 0-1 の eps 0.62、塊ごとに半分がコア点になる eps [0.14, 0.16, 0.14]
実験 6: wine（標準化）: 最初につながる組 0-1 の eps 1.98、品種ごとに半分がコア点になる eps [1.97, 2.43, 2.26]
実験 6: 離れた 3 つの塊を eps=0.3 で分けた結果: クラスタ 3 個、ノイズ 27 点、ARI 0.931
実験 6: 離れた 3 つの塊を eps=0.6 で分けた結果: クラスタ 3 個、ノイズ 2 点、ARI 0.995
```

{{< figure src="dbscan_valley.webp" alt="2 枚のグラフで、横軸は eps、縦軸はコア点になった点の割合。左の離れた 3 つの塊では、3 本の線が eps=0.5 までにほぼ 100% に達し、塊 0 と塊 1 がつながる赤い破線の eps=0.62 はその右にある。右の wine では、3 本の線は eps=1.5 付近から増え始め、品種 0 と品種 1 がつながる赤い破線の eps=1.98 の時点で、品種 0 は 50% ほど、品種 1 と品種 2 は 10% ほどしかコア点になっていない" caption="品種ごとのコア点の割合と、違う品種どうしがつながる eps（min_samples=5）" align="center" >}}

離れた 3 つの塊では、どの塊も `eps` が 0.14〜0.16 で半分の点がコア点になり、塊どうしがつながるのは 0.62 です。その間の `eps` を選べば 3 つの塊は分かれ、0.3 で分けると 600 点のうちノイズは 27 点、0.6 なら 2 点でした。塊の間に密度の低い所があり、そこを越えるには `eps` を大きく広げなければならないからです。

wine では順番が逆でした。品種 0 と品種 1 のコア点どうしは `eps` が 1.98 でつながりますが、品種 1 の半分がコア点になるのは 2.43 です。1.98 より小さい `eps` では品種 1 と品種 2 の点のほとんどがコア点になれず、それより大きい `eps` では品種 0 と品種 1 が同じクラスタになります。品種の間にも、品種の中と同じくらいの間隔で点が並んでいて、密度の低い所がありません。

k-means は点を一番近い中心に割り当てるので、密度の低い所が無くても、3 つの中心の間に境界を引けます。DBSCAN は密度が下がる所を境界にするので、密度の低い所が無ければ境界を引けません。k-means の方が良い手法というわけではなく、前提が違います。k-means が苦手な形の塊は、[k-means のノート](../k-means/)で[混合ガウスモデル](https://scikit-learn.org/stable/modules/mixture.html)と比べています。

wine では、近い点までの距離と遠い点までの距離があまり違いません。標準化した wine と、2 列だけの離れた 3 つの塊で、一番近い点までの距離と、2 点を全ての組で選んだ時の距離とで、[中央値](../../math/median/)を比べました。

```python
for X in [Xb, Xw]:
    nn1 = NearestNeighbors(n_neighbors=1).fit(X).kneighbors()[0][:, 0]
    pair = cdist(X, X)[np.triu_indices(len(X), 1)]
```

```text
実験 6: 離れた 3 つの塊（make_blobs）: 一番近い点までの距離の中央値 0.06、全ての組の距離の中央値 2.64、比 43.8 倍
実験 6: wine（標準化）: 一番近い点までの距離の中央値 1.74、全ての組の距離の中央値 5.00、比 2.9 倍
```

離れた 3 つの塊では 2 つの中央値が 44 倍ほど違うのに、wine では 3 倍ほどしか違いません。コア点の割合を描いた上の図では、右側に描いた wine で、コア点になった点の割合が `eps` の 1.5〜2.5 の狭い幅で 0 から大半まで増えます。距離がこの幅に集まっていることと合っています。

列が多いほど距離の差が縮む現象は、[次元の呪い](../curse-of-dimensionality/)と呼ばれる症状に含まれます。上の比較は列の数だけを変えたものではありませんが、列が多いデータでは、先に [PCA](../pca/) や [UMAP](../tsne-umap/) で列を減らしてから密度で分けることがあります。ただし、列を減らしても塊の間に密度の低い所が無いままなら、DBSCAN では分かれません。

k-means で分かれるデータなら DBSCAN でも分かれる、という冒頭の 3 つ目の説明は、塊の間に密度の低い所がある時に限られます。

---

### 行の順番で変わる境界点

境界点が、違うクラスタに属する 2 つのコア点の近傍に同時に入っていると、どちらに入るかは決まりません。scikit-learn の [DBSCAN](https://scikit-learn.org/stable/modules/generated/sklearn.cluster.DBSCAN.html) は行の順番にコア点を見ていき、先に広がったクラスタが境界点を取ります。[ユーザーガイド](https://scikit-learn.org/stable/modules/clustering.html#dbscan)にも、同じデータでも順番が違えば結果が変わりうると書かれています。

接した 2 つの塊の 400 点で、行の順番を 100 回並べ替えて分けました。クラスタに振る番号も順番で変わるので、番号をそろえてから比べています。

```python
Xo, _ = make_blobs(n_samples=[200, 200], centers=[[0, 0], [1.6, 0]], cluster_std=0.4, random_state=0)
base = DBSCAN(eps=0.25, min_samples=15).fit(Xo)  # 元の順番の結果
ref = canon(base.labels_)  # クラスタの番号を、元の行の番号で一番若いコア点の番号に付け替える
for _ in range(100):
    p = rng.permutation(len(Xo))
    lab = np.empty(len(Xo), int)
    lab[p] = DBSCAN(eps=0.25, min_samples=15).fit(Xo[p]).labels_
    cl = canon(lab)
    changed |= cl != ref
    outcomes.setdefault(tuple(cl), lab)
```

```text
実験 7: クラスタ 2 個、コア点 252、境界点 103、ノイズ 45
実験 7: 100 回並べ替えて、入るクラスタが変わった点 6、違う分け方 2 通り、変わった点はすべて境界点 True
```

入るクラスタが変わったのは 2 つの塊の間にある 6 点だけで、どれも境界点でした。コア点とノイズは、順番によらず同じです。

2 通りの分け方がどう生まれるかは、動く図で見ると分かります。2 通りそれぞれの行の順番で、最初に出てくるコア点から近傍を伝ってクラスタを広げ、1 つ目のクラスタが広がり終わってから 2 つ目を広げました。描いたクラスタは、scikit-learn の結果と一致することをコードで照合しています。

{{< figure src="dbscan_order.webp" alt="接した 2 つの塊の 400 点を 2 枚並べた動く図。最初は全ての点が灰色。左の 1 通り目では右の塊のコア点から青のクラスタが 1 回ずつ近傍を伝って広がり、赤い丸の 6 点も青に入る。その後、左の塊から橙のクラスタが広がるが、6 点はもう青なので取らない。右の 2 通り目では左の塊から橙が先に広がって 6 点を取り、後から広がる青は 6 点を取らない。最後のコマで、残った灰色の点がノイズの x になる" caption="行の順番を並べ替えた 2 通りで、クラスタが広がる様子（近傍を 1 回伝うごとに 0.4 秒で表示）" align="center" >}}

6 点はどちらの塊のコア点からも届くので、先に広がったクラスタが 6 点を取り、後から広がるクラスタには残りません。コア点が先に出てくるのは 1 通り目では右の塊、2 通り目では左の塊なので、6 点がまとめて移ります。

境界点の数が少なければ結果への影響は小さいですが、再現性を求める所では行の順番を固定します。

---

### 近傍の数とメモリ

DBSCAN が時間を使うのは、点ごとに近傍の点を探す所です。scikit-learn の実装は、この探索を全ての点について先にまとめて行い、見つけた点の行番号を点ごとに配列で持ちます。以下では、近傍に入る点の数を近傍数と呼びます。[DBSCAN の文書](https://scikit-learn.org/stable/modules/generated/sklearn.cluster.DBSCAN.html)には、この実装のメモリは「点の数 × 平均の近傍数」に比例し、点の数だけに比例する元の DBSCAN より多いと書かれています。

1 万点の一様乱数で `eps` を広げ、DBSCAN の実行中に増えた最大のメモリを測りました。測る処理は、numpy と scikit-learn だけを読み込んだ別のプロセスで動かしています。

```python
X = np.random.default_rng(0).uniform(0, 1, size=(10_000, 2))
open("/proc/self/clear_refs", "w").write("5")   # 最大のメモリ（VmHWM）を今のメモリに戻す
before = kb("VmRSS")
DBSCAN(eps=float(sys.argv[1]), min_samples=5).fit(X)
print((kb("VmHWM") - before) / 1024)            # 実行中に増えた最大のメモリ（MB）
```

```text
実験 8: eps=0.01 平均の近傍数     4 点、増えたメモリ      3 MB、10000 × 平均の近傍数 × 8 バイト      0 MB
実験 8: eps=0.03 平均の近傍数    29 点、増えたメモリ      6 MB、10000 × 平均の近傍数 × 8 バイト      2 MB
実験 8: eps=0.1  平均の近傍数   290 点、増えたメモリ     40 MB、10000 × 平均の近傍数 × 8 バイト     22 MB
実験 8: eps=0.2  平均の近傍数  1055 点、増えたメモリ    145 MB、10000 × 平均の近傍数 × 8 バイト     80 MB
実験 8: eps=0.3  平均の近傍数  2157 点、増えたメモリ    294 MB、10000 × 平均の近傍数 × 8 バイト    165 MB
実験 8: eps=0.5  平均の近傍数  4867 点、増えたメモリ    628 MB、10000 × 平均の近傍数 × 8 バイト    371 MB
実験 8: eps=1.0  平均の近傍数  9755 点、増えたメモリ   1257 MB、10000 × 平均の近傍数 × 8 バイト    744 MB
実験 8: eps=1.5  平均の近傍数 10000 点、増えたメモリ   1276 MB、10000 × 平均の近傍数 × 8 バイト    763 MB
実験 8: HDBSCAN（min_samples=5）で増えたメモリ 3 MB
```

{{< figure src="dbscan_memory.webp" alt="横軸は平均の近傍数、縦軸はメモリ（MB）。赤の実測の線は eps=0.01 から 1.5 までの 8 点を結び、原点から直線で増える。eps=0.2 で 145 MB、eps=0.5 で 628 MB、ほぼ全ての点が近傍になる eps=1.0 で 1257 MB、全ての点が近傍になる eps=1.5 で 1276 MB。0.1 から 1.5 までの 6 点の横に eps の値を書いている。黒の破線の「点の数 × 平均の近傍数 × 8 バイト」も直線で、実測はその 1.7 倍ほど。青の横線の HDBSCAN は 3 MB" caption="1 万点の一様乱数で eps を広げた時に、DBSCAN が使ったメモリ" align="center" >}}

測るたびに数 MB ずれますが、メモリは平均の近傍数に比例して増え、全ての点が互いの近傍になる `eps` では、1 万点で 1.3GB を使いました。行番号を 8 バイトの整数で持つ分を計算すると 763MB で、実測はその 1.7 倍ほどです。この比例から計算すると、同じ範囲に 10 倍の点を詰めれば近傍数も 10 倍になり、メモリは 100 倍ほどになります。同じ点を分けた HDBSCAN は 3MB でした。

`eps` を大きくしすぎた時だけの話ではありません。データの一部に点が密集していると、そこの点は近傍が多くなり、全体のメモリを押し上げます。[ユーザーガイド](https://scikit-learn.org/stable/modules/clustering.html#dbscan)は、メモリを抑える方法として、OPTICS を使う、近傍の疎な行列を少しずつ作って `metric="precomputed"` で渡す、重複した点をまとめて `sample_weight` で重みを付ける、などを挙げています。

近くの点を数えるだけなので軽い、という冒頭の 4 つ目の説明は、平均の近傍数が小さく収まる時の話です。

---

### DBSCAN を使う前に確認すること

最初に、列の単位をそろえます。`eps` は距離なので、単位や桁の違う列が混ざっていれば標準化してから選びます。[カテゴリ変数](../categorical-encoding/)のように差を距離で測れない列が混ざるなら、[Gower 距離](https://doi.org/10.2307/2528823)のような列の型ごとに差を測る距離を自分で求め、`metric="precomputed"` で渡します。

次に `min_samples` を決めます。2 次元なら 4、列が多ければ列数の 2 倍が目安で、業務の上で何点集まればクラスタと呼ぶかが決まっているなら、その数を下限にします。そして `min_samples - 1` 番目に近い点までの距離で k-距離グラフを描き、急に立ち上がる手前の距離を `eps` の候補にします。候補が決まったら、分けた結果を次の 4 つで見ます。ノイズの割合と一番大きいクラスタの目安は、結果が壊れていないかを見る基準として DBSCAN Revisited, Revisited が挙げた値です。正解のラベルが無いデータでは ARI で比べられないので、この 4 つで判断します。

| 見る所 | 目安 | 外れた時 |
|---|---|---|
| `eps` を前後に動かした時のクラスタ数 | 三日月の 0.12〜0.20 のように一定の幅で変わらない | `eps` の選び方で作った分け方を疑う |
| ノイズの割合 | 1〜30% | 密度の違う塊か、密度の低い所が無いことを疑う |
| 一番大きいクラスタ | クラスタに入った点の 20〜50% 以下 | `eps` を小さくするか、HDBSCAN・OPTICS に替える |
| 平均の近傍数 | 点の数 × 平均の近傍数 × 8 バイトの 2 倍がメモリに収まる | `eps` を小さくするより先に HDBSCAN を試す |

wine で ARI が最大だった組み合わせはノイズが 55% で、ノイズが 10% 未満で 3 個になった組み合わせは、クラスタに入った点の 9 割以上が 1 つのクラスタに集まっていました。どちらも目安から外れます。

<br>

ノイズが多すぎる時は、`eps` を広げる前に、塊ごとの密度が違わないかを疑います。密な塊とまばらな塊が近くにあると、1 つの `eps` では両方を拾えないので、HDBSCAN か OPTICS に替えます。それでも分かれない時は、冒頭に図で示した wine のように、塊の間に密度の低い所が無い可能性があります。その時は密度で分ける手法をやめ、クラスタ数の見当が付くなら、k-means や混合ガウスモデルで中心や分布の形から分けます。

<br>

使い始めた後も、`eps` は距離そのものなので、運用中に[データの分布が変わる](../../mlops/data-drift/)と、同じ `eps` でもノイズの割合が変わります。上の表にあるノイズの割合を定期的に見て、目安から外れたら k-距離グラフを描き直します。ノイズは捨てるものとは限らず、不正の検知や珍しい事例を探す用途では、ノイズになった点の方が見たい点です。
