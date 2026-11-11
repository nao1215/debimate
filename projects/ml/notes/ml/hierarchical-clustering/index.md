---
title: "階層的クラスタリング - 1〜5 の回答は、行の順番を変えるだけで分け方が変わる"
date: 2026-05-26
draft: false
series: ["機械学習ノート", "Machine Learning"]
tags: ["machine-learning", "scikit-learn", "unsupervised"]
weight: 30
topics: ["Machine Learning（評価・概念・アルゴリズム）"]
---

階層的クラスタリング（hierarchical clustering）は、似た点を 2 つずつつないで、データを入れ子のグループに分ける教師なし学習の手法です。グループをクラスタと呼びます。最初は 1 点が 1 つのクラスタで、全体が 1 つになるまで、最も近い 2 つのクラスタをつなぐ操作を繰り返します。つないだ順番は樹形図（dendrogram）という木の形の図に残るので、後から好きな粒度で切って使えます。

以下は、[scikit-learn](https://scikit-learn.org/stable/) の [`AgglomerativeClustering`](https://scikit-learn.org/stable/modules/generated/sklearn.cluster.AgglomerativeClustering.html) で、10 問のアンケートに答えた 300 人を 3 つに分けた結果です。回答は乱数で作った人工のデータで、左は丸める前の連続値、右は同じ値を 1〜5 の整数に丸めたものです。中身は変えずに行の順番だけを並べ替えて 20 回分け、1 行に 1 回分の結果を色で描きました。

{{< figure src="hc_cover.webp" alt="2 つの帯の図。どちらも縦が行の順番を変えた 20 回、横が正解のグループ順に並べた 300 人で、色は分けた先のクラスタ。左の連続値のままでは 20 行とも同じ縦縞で、分け方が変わった回は 0/20。右の 1〜5 に丸めた回答では行ごとに色の混ざり方が違い、分け方が変わった回は 20/20" caption="行の順番だけ変えて、同じ 300 人の回答を 20 回分けた結果" align="center" >}}

連続値のままなら、行の順番をどう変えても 20 回とも同じ分け方でした。左にも違う色の縦の筋が混ざるのは、正解のグループと違う所に分けられた人で、20 回とも同じ人です。1〜5 に丸めると、20 回とも分け方が変わります。

実際のデータでは、「とてもそう思う」から「全くそう思わない」までを 1〜5 で答えるリッカート尺度のアンケートが、この形になります。商品の星の数や 0 と 1 のフラグも同じです。こうしたデータで顧客を分け、DB から読み直したら行の順番が変わっていて、前回と違うセグメントになった、ということが起こり得ます。

<br>

本記事では、つなぐ順番が結果をどう決めるかを中心に、階層的クラスタリングを手元のデータに使う前に知っておきたい次の 5 つを実験で確かめます。

- 点をつなぐ手順と、樹形図の読み方は。
- クラスタ同士の近さの測り方で、何が変わるのか。
- 行の順番を変えるだけで、なぜ分け方が変わるのか。
- 樹形図の形を一番よく再現する測り方を選べばよいのか。
- 何行のデータまで使えるのか。

実験に使ったバージョンは scikit-learn 1.9.1、SciPy 1.18.1、NumPy 2.5.4 で、図を描く処理も含めた完全なコードは [hierarchical-clustering_gen.py](https://github.com/nao1215/debimate/blob/main/projects/ml/scripts/notes/hierarchical-clustering_gen.py) にあります。

---

### 点をつなぐ手順と樹形図

最初に、7 点で手順を追います。以下のコードは、科学計算のライブラリ [SciPy](https://scipy.org/) の [`linkage`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.cluster.hierarchy.linkage.html) で 7 点を全てつなぎ、つないだ順に表示します。`method="single"` は、2 つのクラスタの中で最も近い 2 点の距離が、そのままクラスタ同士の距離になる指定です。他の測り方は次の節で比べます。

```python
import numpy as np
from scipy.cluster.hierarchy import linkage

points = np.array([[0.5, 1.0], [0.7, 0.9], [3.0, 3.0], [3.2, 2.8],
                   [3.1, 3.2], [1.5, 3.5], [1.7, 3.3]])
Z = linkage(points, method="single")
for a, b, dist, size in Z:
    print(f"{int(a)} + {int(b)}: 距離 {dist:.3f}, 点の数 {int(size)}")
```

```text
0 + 1: 距離 0.224, 点の数 2
2 + 4: 距離 0.224, 点の数 2
5 + 6: 距離 0.283, 点の数 2
3 + 8: 距離 0.283, 点の数 3
9 + 10: 距離 1.334, 点の数 5
7 + 11: 距離 2.594, 点の数 7
```

戻り値 `Z` の 1 行が 1 回の結合です。つないだ 2 つのクラスタの番号、その時の距離、つないだ後の点の数が入ります。7 以降の番号は結合で作ったクラスタで、7 は 1 回目に作った {0, 1}、8 は 2 回目に作った {2, 4} です。

{{< figure src="hc_steps.webp" alt="左は 7 点の散布図で、0・1 の青、5・6 の赤、2・3・4 の緑の 3 組。破線は 5 回目と 6 回目の結合で、5 回目は赤と緑、6 回目は赤と青を結ぶ。右は同じ結合を描いた樹形図で、1〜4 回目の結合は高さ 0.3 以下、5 回目は 1.334、6 回目は 2.594。高さ 1.0 の赤い破線で切ると 3 つに分かれる" caption="7 点をつないだ順番と、それを描いた樹形図" align="center" >}}

右の樹形図の横棒が 1 回の結合で、棒の高さがつないだ時の距離です。どこかの高さで横に切ると、切った線より下でつながっている塊が 1 つのクラスタになります。高さ 1.0 で切れば 3 つ、2.0 で切れば 2 つです。

5 回目の 1.334 は、4 回目までの 0.3 以下から大きく跳んでいます。結合の高さが大きく跳ぶ所は、離れた塊同士を無理につないだ所なので、その手前で切るのが自然な分け方の候補になります。樹形図の左右の並びには意味が無く、0 と 1 の枝を入れ替えても同じ木です。

<br>

ここで説明したのは、1 点ずつから始めてつなぐ凝集型（agglomerative）です。全体を 1 つから始めて割っていく分割型もありますが、scikit-learn と SciPy の階層的クラスタリングは凝集型です。

---

### クラスタ同士の近さの測り方

1 点同士なら距離は 1 つに決まりますが、何点かを含むクラスタ同士の距離には決め方がいくつかあります。この決め方を linkage と呼びます。前の節の関数 `linkage` の `method` 引数で選んでいたのがこれで、よく使われるのは次の 4 つです。

{{< figure src="hc_linkage.webp" alt="青と赤の 2 つのクラスタを 4 回並べた図。single は最も近い青と赤の 2 点を太い線で結ぶ。complete は最も遠い 2 点を結ぶ。average は青と赤の全ての組を細い線で結ぶ。ward は青と赤それぞれの中心と、2 つをまとめた時の中心に × を描き、各点からまとめた中心へ点線を引く" caption="4 つの linkage が、2 つのクラスタの距離として使うもの" align="center" >}}

ward は、2 つのクラスタをまとめた時に、各点から中心までの距離の 2 乗の和がどれだけ増えるかをもとに距離を決めます。[Ward の 1963 年の論文](https://doi.org/10.1080/01621459.1963.10500845)に由来し、増え方の小さい組からつなぐので、大きさの近い丸い塊を作りやすい方法です。scikit-learn の `AgglomerativeClustering` は、`linkage` を指定しなければ ward を使います。冒頭の実験も ward です。

SciPy と scikit-learn が樹形図の高さとして返すのは、増えた量そのものではなく、増えた量を 2 倍した値の平方根です。後の節の wine の ward の樹形図で、縦軸の 20 や 35 として読む高さも、この値です。

| linkage | クラスタ同士の距離 | 作りやすい形 |
|---|---|---|
| single | 最も近い 2 点の距離 | 細長くつながった塊 |
| complete | 最も遠い 2 点の距離 | 直径の小さい塊 |
| average | 全ての組の距離の平均 | single と complete の中間 |
| ward | まとめた時の 2 乗和の増え方 | 大きさの近い丸い塊 |

<br>

single は、1 組でも近い点があればつなぐので、離れた塊の間に点が並んでいると、塊同士を 1 つにしてしまいます。以下のコードは、100 点ずつの 2 つの塊の間に橋渡しの 8 点を一列に足し、2 つに分けた結果を比べます。足した 8 点は全体の 4% です。ARI（Adjusted Rand Index、調整ランド指数）は 2 つの分け方の一致を測る値で、同じなら 1、でたらめと同じ程度なら 0 付近になります。クラスタの番号の付け方には左右されません。

```python
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics import adjusted_rand_score

rng = np.random.RandomState(0)
A = rng.randn(100, 2) * 0.5
B = rng.randn(100, 2) * 0.5 + [6, 0]
X2 = np.vstack([A, B])
y2 = np.r_[[0] * 100, [1] * 100]
bridge = np.column_stack([np.linspace(1.5, 4.5, 8), np.zeros(8)])  # 塊の間に一列に並べた 8 点
X2b = np.vstack([X2, bridge])
for title, data, method in [("橋渡しなし single", X2, "single"),
                            ("橋渡しあり single", X2b, "single"),
                            ("橋渡しあり ward", X2b, "ward")]:
    lab = AgglomerativeClustering(n_clusters=2, linkage=method).fit_predict(data)
    print(f"{title}: 点の数 {sorted(np.bincount(lab).tolist(), reverse=True)}、"
          f"塊の 200 点の ARI {adjusted_rand_score(y2, lab[:200]):.2f}")
```

```text
橋渡しなし single: 点の数 [100, 100]、塊の 200 点の ARI 1.00
橋渡しあり single: 点の数 [207, 1]、塊の 200 点の ARI 0.00
橋渡しあり ward: 点の数 [106, 102]、塊の 200 点の ARI 1.00
```

{{< figure src="hc_chain.webp" alt="3 つの散布図。左の橋渡しなし single は、左右の塊が赤と青に分かれる。中央の橋渡しあり single は、左右の塊と間の 8 点が全て青の 1 つのクラスタになり、右下の離れた 1 点だけが赤い星の別のクラスタ。右の橋渡しあり ward は、左右の塊が青と赤に分かれ、間の 8 点は近い方の塊に入る" caption="2 つの塊の間に 8 点を足した時の、single と ward の分け方" align="center" >}}

橋渡しの 8 点を足すと、single は 2 つの塊と間の点を全て 1 つにまとめ、もう 1 つのクラスタは右の塊の下に離れた 1 点だけになりました。8 点の間隔は約 0.43 で、鎖の中で一番長いのは左の塊と鎖の端の 0.564 です。右下の 1 点は、一番近い点まで 0.586 離れていて、鎖のどの間隔よりも遠い点でした。single から見ると、2 つの塊は 1 本の鎖でつながった 1 つの塊で、最後まで残るのはこの 1 点です。ward は、同じデータを左右の塊で分けました。

---

### 行の順番で分け方が変わる理由

ここで冒頭の実験に戻ります。以下は、その実験のコードです。3 つのグループごとに 10 問の平均的な答えを決め、乱数を足して 300 人の回答を作り、1〜5 に丸めます。分けた後に行の順番を元に戻し、並べ替える前の分け方と ARI で比べます。

```python
from scipy.spatial.distance import pdist

rng = np.random.RandomState(0)
profiles = rng.uniform(1.5, 4.5, size=(3, 10))  # 3 つのグループの、10 問の平均的な回答
group = rng.randint(0, 3, 300)  # 300 人がどのグループか
X_cont = profiles[group] + rng.randn(300, 10) * 0.8  # 丸める前の連続値
X_int = np.clip(np.rint(X_cont), 1, 5)  # 1〜5 の整数に丸めた回答

for name, X in [("連続値のまま", X_cont), ("1〜5 に丸めた回答", X_int)]:
    base = AgglomerativeClustering(n_clusters=3, linkage="ward").fit_predict(X)
    changed, aris = 0, []
    for s in range(20):
        order = np.random.RandomState(s).permutation(len(X))  # 行の順番を並べ替える
        lab = AgglomerativeClustering(n_clusters=3, linkage="ward").fit_predict(X[order])
        back = np.empty_like(lab)
        back[order] = lab  # 元の行の順番に戻して比べる
        changed += adjusted_rand_score(base, back) < 0.999
        aris.append(adjusted_rand_score(group, back))
    print(f"{name}: 違う距離の値 {len(np.unique(pdist(X)))} 種類、"
          f"並べ替える前と分け方が変わった回 {changed}/20、"
          f"正解との ARI {min(aris):.3f}〜{max(aris):.3f}")
```

```text
連続値のまま: 違う距離の値 44850 種類、並べ替える前と分け方が変わった回 0/20、正解との ARI 0.539〜0.539
1〜5 に丸めた回答: 違う距離の値 64 種類、並べ替える前と分け方が変わった回 20/20、正解との ARI 0.423〜0.673
```

`pdist` は、全ての 2 人の組の距離を並べる SciPy の関数で、300 人なら 44,850 組です。連続値では 44,850 組の距離が全て違う値でした。1〜5 に丸めると、距離の値は 64 種類しかありません。平均すると、1 つの距離の値を 700 組ほどが共有しています。

<br>

#### 同じ距離の組がある時

最初の節で見たとおり、階層的クラスタリングは毎回「最も近い組」を 1 つ選んでつなぎます。最も近い組が 2 つ以上あると、どちらを先につなぐかはデータの中には書かれていないので、実装は行の順番で決めます。以下は、0・1・2 の 3 点を一直線に間隔 1 で並べ、complete で 2 つに分けた結果です。上は 0, 1, 2 の順に、下は 2, 1, 0 の順に入力しました。

{{< figure src="hc_ties.webp" alt="一直線に間隔 1 で並ぶ点 0・1・2 を 2 行描いた図。入力の順番が 0, 1, 2 の上の行では 0 と 1 が青の同じクラスタで 2 が赤。入力の順番が 2, 1, 0 の下の行では 1 と 2 が青の同じクラスタで 0 が赤" caption="同じ 3 点でも、入力の順番で 2 つの分け方が入れ替わる" align="center" >}}

0 と 1、1 と 2 の距離はどちらも 1 です。上では {0, 1} を先につなぎ、下では {1, 2} を先につなぎました。complete で測ると、どちらの場合も残りの 1 点までの距離は 2 なので、2 つに分けた時点では先につないだ組がそのまま残ります。一度つないだ組は後で離さないので、同点の選び方の違いは、その後の全ての結合に引き継がれます。

[k-means](../k-means/) の結果が実行のたびに変わるのは、初期の中心を乱数で選ぶからでした。階層的クラスタリングには乱数がありません。ここで結果を変えているのは、同点の組と行の順番です。

<br>

#### 同梱の digits で確かめる

scikit-learn に同梱の [digits](https://scikit-learn.org/stable/modules/generated/sklearn.datasets.load_digits.html) でも同じことを試しました。digits は、手書きの数字 1,797 枚を 8×8 の画素に縮め、各画素の濃さを 0〜16 の整数で表したデータです。161 万組の距離のうち、違う値は 5,166 種類でした。4 つの linkage で 10 個に分け、行の順番を変えて 20 回ずつ比べた結果は次のとおりです。

| linkage | 分け方が変わった回 | 正解の数字との ARI |
|---|---|---|
| single | 0/20 | 0.000 |
| complete | 19/20 | 0.386〜0.436 |
| average | 0/20 | 0.514 |
| ward | 0/20 | 0.794 |

digits では complete だけが 20 回中 19 回変わり、ward は 1 回も変わりませんでした。冒頭の 1〜5 の回答で変わったのは ward です。

<br>

#### 結合のたびの同点を数える

点同士の距離が同点でも、ward がつなぐ時に比べるのは、まとめた時の 2 乗和の増え方です。そこで、結合のたびに、その時点で最も近い組が同点だったかを数えました。

ward では、クラスタ A と B をまとめるたびに、まとめたクラスタと他のクラスタ C の距離を計算し直します。使うのは、A と B の距離、A と C の距離、B と C の距離の 3 つと、各クラスタの点の数です。

この計算の形は [Lance と Williams の 1967 年の論文](https://doi.org/10.1093/comjnl/9.4.373)の漸化式で、それを ward に当てはめたのは [Wishart の 1969 年の論文](https://doi.org/10.2307/2528688)です。この経緯は、[Murtagh と Legendre の 2014 年の論文](https://arxiv.org/abs/1111.6285)が整理しています。

同点の数え方は、この式で結合を 1 回ずつ進め、毎回の最小の距離に等しい組が 2 つ以上あった回を数えるというものです。同点の時は番号の小さい組をつなぐ、1 通りの進め方で数えました。

<br>

<details><summary>同点を数えたコード</summary>

```python
from scipy.spatial.distance import squareform


def count_ties(X, method):
    """最も近い組が同点だった結合の番号を返す。"""
    D = squareform(pdist(X))
    np.fill_diagonal(D, np.inf)
    size = np.ones(len(X))
    alive = np.ones(len(X), bool)
    tied, heights = [], []
    for step in range(1, len(X)):
        m = D.min()
        cand = np.argwhere(D <= m * (1 + 1e-12))  # 丸め誤差の範囲で最小と等しい組
        cand = cand[cand[:, 0] < cand[:, 1]]
        if len(cand) > 1:
            tied.append(step)
        i, j = cand[0]
        heights.append(m)
        di, dj, dij = D[i].copy(), D[j].copy(), D[i, j]
        if method == "ward":  # Lance-Williams の更新式で、まとめたクラスタと他の距離を計算し直す
            T = size[i] + size[j] + size
            new = np.sqrt(np.maximum(((size[i] + size) * di**2 + (size[j] + size) * dj**2 - size * dij**2) / T, 0))
        else:  # complete: 2 つの距離の大きい方
            new = np.maximum(di, dj)
        new[~alive] = np.inf
        D[i, :] = new
        D[:, i] = new
        D[i, i] = np.inf
        D[j, :] = np.inf
        D[:, j] = np.inf
        alive[j] = False
        size[i] += size[j]
    return tied, np.array(heights)
```

</details>

<br>

同点の無い連続値で、このコードの ward の高さと SciPy の `linkage` の高さを比べると、差は最大でも 7×10⁻¹⁵ で、同じ計算になっていました。以下は、1〜5 の回答の ward と、digits の ward・complete で、同点だった結合の位置を描いた図です。横軸はその結合の後に残るクラスタの数で、右へ進むほど木の上の方の結合です。

{{< figure src="hc_tie_steps.webp" alt="3 段の図。横軸はその結合の後に残るクラスタの数で、左が 1,000 以上、右が 1。赤い縦線が同点だった結合。1〜5 の回答の ward は、299 回の結合のうち 170 回が同点で、残り 300 個から 65 個まで同点が続く。digits の ward は 1,796 回のうち 460 回が同点で、同点は残り 526 個までで止まる。digits の complete は 1,796 回のうち 875 回が同点で、残り 73 個まで同点が続く。黒い破線は切る数の 3 と 10" caption="結合のたびに、最も近い組が同点だった位置（赤い線）" align="center" >}}

1〜5 の回答の ward では、299 回の結合のうち 170 回が同点で、1 回目の同点は、全く同じ回答をした人同士の距離 0 でした。同点はクラスタが残り 65 個になるまで続きます。digits の ward では、同点は残り 526 個までの下の方で止まり、complete では残り 73 個まで続きました。

complete のクラスタ同士の距離は、常に元の点同士の距離のどれか 1 つなので、値の種類は 5,166 種類から増えません。ward の距離は点の数を使って計算し直すので、結合が進むと値の種類が増え、同点が出にくくなります。digits の ward で同点が下の方で止まったのは、このためと考えられます。1〜5 の回答では元の距離が 64 種類しかなく、ward でも木の上の方まで同点が残りました。

今回の 3 つでは、分け方が変わった 2 つで、同点が残り数十個のクラスタまで続いていました。同点が木の下の方だけで止まった digits の ward は、20 回とも同じ分け方です。同点がどこまで上に残ると切った結果まで変わるかは、データと切る数によるので、本記事で確かめたのはこの 3 つの範囲です。

---

### 樹形図の形を再現する linkage を選ぶと

linkage を選ぶ指標として、コフェネティック相関係数（cophenetic correlation coefficient）がよく紹介されます。[Sokal と Rohlf の 1962 年の論文](https://doi.org/10.2307/1217208)で提案された値です。樹形図の上で 2 点が初めて同じクラスタに入る高さは、その 2 点のコフェネティック距離と呼ばれます。全ての組について、元の距離とコフェネティック距離の[相関係数](../../math/correlation/)を計算し、1 に近いほど、樹形図が元の距離の関係を保っていると考えます。

scikit-learn に同梱の [wine](https://scikit-learn.org/stable/modules/generated/sklearn.datasets.load_wine.html) で、4 つの linkage を比べました。wine は、3 品種のブドウから作ったワイン 178 本の化学分析の値を 13 列に並べたデータです。列ごとに単位と桁が違うので、各列から平均を引いて標準偏差で割る[標準化](../standardization/)をしてから掛けます。標準化の効果は、同じ wine を使った [k-means のノート](../k-means/)と [PCA のノート](../pca/)で図にしているので、ここでは linkage の選び方だけを見ます。

```python
from scipy.cluster.hierarchy import cophenet, fcluster, linkage
from sklearn.datasets import load_wine
from sklearn.preprocessing import StandardScaler

wine = load_wine()
Xw = StandardScaler().fit_transform(wine.data)
yw = wine.target
dist_w = pdist(Xw)
for method in ["single", "complete", "average", "ward"]:
    Z = linkage(Xw, method=method)
    c, _ = cophenet(Z, dist_w)  # コフェネティック相関係数
    lab = fcluster(Z, t=3, criterion="maxclust")  # 樹形図を 3 つに分かれる高さで切る
    sizes = sorted(np.bincount(lab)[1:].tolist(), reverse=True)
    print(f"{method:8s} コフェネティック相関 {c:.3f}  k=3 の点の数 {sizes}  ARI {adjusted_rand_score(yw, lab):.3f}")
```

```text
single   コフェネティック相関 0.544  k=3 の点の数 [174, 3, 1]  ARI -0.007
complete コフェネティック相関 0.592  k=3 の点の数 [69, 58, 51]  ARI 0.577
average  コフェネティック相関 0.759  k=3 の点の数 [174, 3, 1]  ARI -0.005
ward     コフェネティック相関 0.662  k=3 の点の数 [64, 58, 56]  ARI 0.790
```

コフェネティック相関係数が最も高いのは average の 0.759 でした。ところが average の樹形図を 3 つに切ると、178 本が 174 本・3 本・1 本に分かれ、品種との ARI は -0.005 です。品種の分け方とは全く関係ありません。average より低い 0.662 の ward は、64 本・58 本・56 本に分け、ARI は 0.790 でした。

{{< figure src="hc_wine.webp" alt="標準化した wine の樹形図が 2 つ。左の average はコフェネティック相関 0.759 で、樹形図の左端の 4 本ほどが高い所で最後につながり、k=3 で切る赤い破線は高さ 6.2 付近にあって、174・3・1 本に分かれ ARI -0.01。上の結合の高さは 5.66〜6.78 で詰まっている。右の ward はコフェネティック相関 0.662 で、高さ 12 付近までに 3 つの大きな枝がまとまり、27.65 と 35.4 で最後につながる。k=3 で切る破線は高さ 20 付近で、64・58・56 本に分かれ ARI 0.79" caption="標準化した wine の average と ward の樹形図と、3 つに分かれる高さ" align="center" >}}

average の樹形図では、他から離れた数本のワインが、最後の方の高い所でつながります。他の点との距離が大きい点ほど遅くつながるので、樹形図にもその大きな距離がそのまま残り、コフェネティック相関係数は高くなります。その代わり、上から 3 つに切ると、離れた数本だけが別のクラスタになります。

average を 8 つに切ると、58 本・55 本・52 本の 3 つの大きなクラスタと、合わせて 13 本の 5 つの小さなクラスタに分かれ、ARI は 0.793 でした。average も品種の構造は木の中に持っていて、3 で切ったのが合わなかったということです。コフェネティック相関係数は、樹形図が元の距離の関係をどれだけ保っているかを測る値で、ある高さで切った分け方が使えるかは測りません。

同じ標準化した wine を k-means で 3 つに分けた ARI は 0.897 で、品種に合わせるだけなら k-means の方が近い分け方でした。それでも、どの linkage を選ぶかで 0.79 から 0 付近まで変わるのが、階層的クラスタリングの特徴です。

---

### 点の数と時間・メモリ

ここまでの実験は数百〜2,000 点ほどでした。階層的クラスタリングは、毎回「最も近い組」を探すために全ての組の距離を持つので、点の数が増えると時間もメモリも急に増えます。以下は、10 列の 5 つの塊から作った 1,000〜20,000 点で、ward・[k-means](../k-means/)・Birch の `fit` に掛かった時間と、プロセスのピークのメモリを測ったコードの要所です。

[Birch](https://scikit-learn.org/stable/modules/generated/sklearn.cluster.Birch.html) は、[Zhang らの 1996 年の論文](https://doi.org/10.1145/233269.233324)の手法で、近い点を半径 `threshold` 以内の小さな塊にまとめてから、塊の中心を ward で分けます。大きなデータで階層的クラスタリングの代わりに挙げられることの多い手法です。各条件は別のプロセスで 3 回動かし、時間は一番短い回を使いました。

```python
import resource
import time

from sklearn.cluster import AgglomerativeClustering, Birch, KMeans
from sklearn.datasets import make_blobs

X, _ = make_blobs(n_samples=n, centers=5, n_features=10, random_state=0)
t = time.perf_counter()
if algo == "ward":
    AgglomerativeClustering(n_clusters=5).fit(X)
elif algo == "kmeans":
    KMeans(n_clusters=5, n_init=10, random_state=0).fit(X)
elif algo == "birch":
    m = Birch(n_clusters=5).fit(X)  # threshold は既定の 0.5
else:
    m = Birch(n_clusters=5, threshold=3.0).fit(X)
sec = time.perf_counter() - t
peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss  # プロセスのピークのメモリ（KB）
```

{{< figure src="hc_scale.webp" alt="2 つの折れ線グラフ。横軸は点の数 1,000〜20,000。左の時間では、ward と Birch（既定）が 20,000 点で 10 秒台まで増え、k-means は 1 秒ほど、Birch（threshold=3.0）は 1 秒未満。右のピークのメモリでは、ward と Birch（既定）が重なって 10,000 点で約 0.9 GB、20,000 点で約 3.1 GB まで増え、k-means と Birch（threshold=3.0）は 0.26 GB のまま横ばい" caption="点の数ごとの、fit の時間とプロセスのピークのメモリ" align="center" >}}

ward は 20,000 点で 10 秒を超え、k-means より 1 桁、threshold を合わせた Birch より 2 桁ほど遅くなりました。プロセスのピークのメモリは 3,211 MB でした。fit の前は 266 MB なので、2.9 GB ほどを fit の間に使っています。20,000 点の全ての組の距離を 8 バイトの浮動小数点数で持つと 1.6 GB で、その 2 倍近くです。

点の数を 2 倍にするたびに、時間は数倍に増えました。

意外だったのは Birch の既定です。20,000 点で時間は ward と同じ桁、ピークのメモリは 3,190 MB と、ward とほとんど変わりません。まとめた後の小さな塊は 19,892 個で、ほぼ 1 点が 1 つの塊のままでした。この 10 列のデータでは、各点から最も近い点までの距離の中央値が 1.54 あり、半径 0.5 の塊にはほとんど点が入らないからです。

`threshold=3.0` にすると塊は 38 個になって 1 秒未満で終わり、5 つの塊は正解と完全に一致しました。

threshold の適した値は、列の数と値の広がりで変わります。Birch に替える時は、`subcluster_centers_` の行の数を見て、点の数より十分に少なくなっているかを確かめる必要があります。

<br>

<details><summary>計測した時間とメモリの値（20,000 点、3 回のうち最も短い回）</summary>

| 手法 | 時間 | ピークのメモリ |
|---|---|---|
| ward | 17.25 秒 | 3,211 MB |
| k-means | 1.04 秒 | 266 MB |
| Birch（既定） | 13.08 秒 | 3,190 MB |
| Birch（threshold=3.0） | 0.22 秒 | 266 MB |

この回の fit の前のメモリは、どの手法も 266 MB です。時間は同じ機械で他の処理と並べて測ったので揺れがあり、別の回では ward が 9 秒ほどでした。図の k-means の 2,000 点と 20,000 点の跳ねも、この揺れの範囲です。点の数を 2 倍にした時の時間の倍率も回ごとに入れ替わり、別の回では 7 倍と 3 倍でした。fit の前のメモリも環境で変わり、別の回では 290 MB でしたが、fit の間に増えた量は同じでした。時間の桁とメモリは、どの回でもほぼ同じでした。全ての点の数の値は、[生成元](https://github.com/nao1215/debimate/blob/main/projects/ml/scripts/notes/hierarchical-clustering_gen.py)を実行すると出力されます。

</details>

<br>

---

### 分け方が変わった時に確かめる順

前回と分け方が変わった時や、これから階層的クラスタリングで分ける時は、次の順に見ると、本記事の実験で起きたことを避けられます。

1. `np.unique(pdist(X))` で、違う距離の値が何種類かを数える。
2. 少なければ、行の順番を変えて何回か分け、ARI で比べる。
3. 切った後の各クラスタの点の数を見て、数本だけの塊を疑う。
4. 点の数が 1 万を超えるなら、距離の表のメモリを見積もる。

1 と 2 は冒頭の実験の話です。回ごとにクラスタが変わる人は、データだけでは所属が決まらない人なので、クラスタの境界にいる人として扱う方が安全と考えられます。値の種類を増やせるなら、1〜5 に丸める前の値を使うのが一番確かです。

3 は wine の average の話で、コフェネティック相関係数が一番高くても、3 つに切ると 174 本・3 本・1 本でした。数本だけのクラスタができていれば、外れた点を先に調べるか、切る数を増やします。

4 は、全ての組の距離だけで `n * (n - 1) / 2 * 8` バイト、実験ではその 2 倍近くを使いました。入れ子の構造が要らないなら k-means で済み、Birch に替えるなら threshold を合わせます。塊の形が丸くない時は [DBSCAN](../dbscan/) も候補です。

<br>

樹形図を人に見せる時は、左右の並びに意味が無く、近さは 2 点が初めてつながる横棒の高さで読むことを添えます。そして冒頭の図の右のように、同じ回答でも行の並べ方次第で違う木になることがあると、受け取る人に伝えておく必要があります。
