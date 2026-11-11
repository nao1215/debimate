---
title: "固有値・固有ベクトルと固有値分解（eigenvalue / eigenvector / spectral decomposition）"
date: 2026-05-26
draft: false
series: ["機械学習ノート", "Mathematics"]
tags: ["machine-learning", "math", "linear-algebra"]
weight: 17
topics: ["Mathematics（数学の基礎）"]
---

固有ベクトル（eigenvector）は、ある正方行列 `A` をかけても同じ直線の上にとどまるベクトルのことで、固有値（eigenvalue）はその時に長さが何倍になるかを表すスカラーです。式で書くと、

`A v = λ v`

を満たす `v ≠ 0` と `λ` をそれぞれ固有ベクトル・固有値と呼びます。一般のベクトルは `A` をかけると向きも長さも変わります。一方で、固有ベクトルは `λ` 倍されるだけで、`λ > 0` なら向きはそのまま、`λ < 0` なら真逆を向きます。

[主成分分析（PCA）](../../ml/pca/) では[共分散](../correlation/)行列を固有値分解し、データの「最も伸びている方向」「次に伸びている方向」を順に固有ベクトルが捉えます。[ベクトルと行列の演算](../vector-matrix-ops/) の線形変換の見方と合わせると、変換が各方向をどれだけ伸縮するかを固有値で読めます。

---

### 固有ベクトル: 同じ直線にとどまる方向

行列 `A = [[2, 1], [0, 3]]` を例に取ります。[NumPy](https://numpy.org/) 2.5.4 の [`np.linalg.eig`](https://numpy.org/doc/stable/reference/generated/numpy.linalg.eig.html) で固有値と固有ベクトルを求め、`A v` と比べます。

```python
import numpy as np

A = np.array([[2.0, 1.0], [0.0, 3.0]])
eigvals, eigvecs = np.linalg.eig(A)
for lam, v in zip(eigvals.real, eigvecs.real.T):
    print(f"λ={lam:.1f}  v={np.round(v, 3)}  Av={np.round(A @ v, 3)}")
```

```text
λ=2.0  v=[1. 0.]  Av=[2. 0.]
λ=3.0  v=[0.707 0.707]  Av=[2.121 2.121]
```

どちらの `v` も向きを保ったまま 2 倍・3 倍になります。手で計算しても `A (1, 1) = (3, 3)` です。手元の NumPy 2.5.4 では虚部が 0 でも complex128 で返ってきたので、`.real` で実部を取っています。

次の図は、単位円の上半分に並べた 18 本のベクトルに `A` をかけた結果です。図は[生成コード](https://github.com/nao1215/debimate/blob/main/projects/ml/scripts/notes/eigen-decomposition_gen.py)で描きました。

{{< figure src="eigen_action.svg" alt="左は単位円の上半分に並べた 18 本のベクトル、右は行列 A = [[2, 1], [0, 3]] をかけた後。青いベクトルの大半は向きが変わり、赤い固有ベクトル (1, 0) と (1, 1) 方向だけが同じ直線上で 2 倍・3 倍に伸びる" caption="A をかける前後のベクトル" align="center" >}}

左が `A` をかける前、右がかけた後です。青いベクトルの大半は向きが変わり、赤い固有ベクトルだけが同じ方向のまま伸びます。

固有値の符号と大きさには次の意味があります。

- `λ > 1`: その方向に拡大
- `0 < λ < 1`: その方向に縮小
- `λ < 0`: 方向反転 + 拡大/縮小
- `λ = 0`: その方向は潰れる（行列が特異）
- 複素固有値: 2 次元の回転成分を含む（実数の世界では「向きが変わらない」が成り立たない）

---

### 固有値分解（spectral decomposition）

正方行列 `A` が `n` 個の線形独立な固有ベクトルを持つ時、

`A = Q Λ Q^-1`

の形に分解できます。ここで `Q` は固有ベクトルを列に並べた行列、`Λ` は固有値を対角に並べた対角行列です。

対称行列の場合は `Q` が直交行列となり `Q^-1 = Q^T`、

`A = Q Λ Q^T`

と書けます。共分散行列は対称なので、機械学習ではこの形が標準です。対称行列向けの [`np.linalg.eigh`](https://numpy.org/doc/stable/reference/generated/numpy.linalg.eigh.html) で分解し、戻すと `A` に一致するかを確かめます。

```python
import numpy as np

A = np.array([[3.0, 1.0], [1.0, 2.0]])  # 対称行列
eigvals, Q = np.linalg.eigh(A)          # 固有値の昇順で返る
eigvals, Q = eigvals[::-1], Q[:, ::-1]  # 大きい順に並べ替える
Q = Q * np.sign(Q[0])                   # 各列の第 1 成分を正にそろえる
if np.linalg.det(Q) < 0:                # 行列式が -1 なら鏡映を含むので、
    Q[:, 1] *= -1                       # 2 列目の符号を反転して回転にする
Lam = np.diag(eigvals)

print("λ =", np.round(eigvals, 3))
print("Q =", np.round(Q, 3).tolist())
print("det(Q) =", round(np.linalg.det(Q), 3))
print("Q Λ Q^T == A:", np.allclose(Q @ Lam @ Q.T, A))
```

```text
λ = [3.618 1.382]
Q = [[0.851, -0.526], [0.526, 0.851]]
det(Q) = 1.0
Q Λ Q^T == A: True
```

固有ベクトルは符号を反転しても固有ベクトルなので、`eigh` が返す `Q` は回転（行列式 1）とは限らず、鏡映（行列式 -1）を含むことがあります。上記のコードは符号をそろえて回転にしました。

すると `A` の作用は「`Q^T` で回転して固有ベクトルを座標軸に合わせる → 各軸を固有値倍に伸縮する → `Q` で戻す」の 3 段階に分けられます。

{{< figure src="diagonalization_steps.svg" alt="単位円と赤の q1・緑の q2 を 4 枚で追う図。Q^T で回転して q1・q2 を座標軸に合わせ、3.62 倍・1.38 倍に伸縮して楕円にし、Q で元の向きに戻す" caption="固有値分解の回転・伸縮・逆回転" align="center" >}}

単位円は回転しても円のままなので、赤の `q1`・緑の `q2` で回転を追います。2 枚目で 2 本が座標軸に乗り、3 枚目で 3.62 倍・1.38 倍に伸びて楕円になり、4 枚目で元の向きに戻ります。この楕円は `A x` を直接計算した形と一致します。

非対称な行列や長方形の行列には、特異値分解（SVD, singular value decomposition）`A = U Σ V^T` を使います。`U` と `V` は別々の直交行列です。

---

### 共分散行列の固有値分解 = PCA

機械学習で固有値分解が最も使われるのは、中心化したデータ `X` の共分散行列 `Σ = X^T X / (n-1)` の分解です（`n` で割っても固有ベクトルは同じ）。これがそのまま [PCA](../../ml/pca/) で、主成分は共分散行列の固有ベクトル、各主成分の分散は対応する固有値になります。

```python
import numpy as np

rng = np.random.default_rng(0)
data = rng.multivariate_normal([0, 0], [[3.0, 1.4], [1.4, 1.2]], size=400)
cov_emp = np.cov(data.T)  # n-1 で割る標本共分散
eigvals2, eigvecs2 = np.linalg.eigh(cov_emp)
order = np.argsort(eigvals2)[::-1]
for i in order:
    print(f"λ={eigvals2[i]:.2f}  v={np.round(eigvecs2[:, i], 3)}")
```

```text
λ=3.79  v=[-0.879 -0.477]
λ=0.43  v=[ 0.477 -0.879]
```

{{< figure src="cov_eigen_pca.png" alt="400 点の 2 次元正規分布の散布図に、共分散行列の固有ベクトルを重ねた図。赤が λ = 3.79 の第 1 主成分でデータが最も伸びる方向、緑が λ = 0.43 の第 2 主成分で直交する方向" caption="共分散行列の固有ベクトルと主軸" align="center" >}}

赤い矢印（第 1 主成分、`λ=3.79`）はデータが最も伸びる方向、緑の矢印（第 2 主成分、`λ=0.43`）はそれに直交する方向です。固有値はその方向の[分散](../variance/)なので、矢印の長さは[標準偏差](../stddev/) `√λ` の 2 倍に取りました。図と `v` の符号が逆でも、主軸としては同じ直線です。

固有値の配列（スペクトル）を大きい順に並べて合計で割ると、各主成分が全分散の何割を説明するか（寄与率）が分かります。次の例は、5 本の軸の標準偏差を 3.0・2.0・1.2・0.6・0.2 にした合成データです。

```python
import numpy as np

rng = np.random.default_rng(0)
scales = np.diag([3.0, 2.0, 1.2, 0.6, 0.2])  # 各軸の標準偏差
X = rng.standard_normal((600, 5)) @ scales     # 600 サンプル × 5 次元
eigvals5 = np.sort(np.linalg.eigh(np.cov(X.T))[0])[::-1]
ratio = eigvals5 / eigvals5.sum()
print("λ       :", np.round(eigvals5, 2))
print("寄与率  :", np.round(ratio, 3))
print("累積    :", np.round(np.cumsum(ratio), 3))
```

```text
λ       : [9.59 3.75 1.29 0.37 0.04]
寄与率  : [0.637 0.249 0.086 0.025 0.003]
累積    : [0.637 0.887 0.973 0.997 1.   ]
```

{{< figure src="eigen_spectrum.svg" alt="5 次元の合成データの固有値を大きい順に並べた棒グラフと、寄与率・累積寄与率のグラフ。上位 2 成分で約 89%、上位 3 成分で約 97%" caption="固有値スペクトルと累積寄与率" align="center" >}}

左の棒グラフがスペクトル、右が各成分の寄与率（explained variance ratio）と累積寄与率（cumulative ratio）です。固有値は標準偏差の 2 乗（9、4、1.44、0.36、0.04）に近く、上位 2 成分で全分散の約 89%、上位 3 成分で約 97% を説明します。削減後の次元数は、累積寄与率 90%・95% などを目安に決めます。

---

### 数学での使いどころ

- 線形微分方程式系 `dx/dt = A x` の解析解（固有値で振動・減衰の様子が決まる）
- 2 次形式 `x^T A x` の符号判定（対称な `A` の正定値・負定値は固有値の符号で決まる）
- 主軸変換（楕円・楕円体の標準形への変換）
- マルコフ連鎖の定常分布（遷移行列の固有値 1 に対応する固有ベクトル）
- グラフラプラシアンの固有値分解（[スペクトラルクラスタリング](https://proceedings.neurips.cc/paper/2001/hash/801272ee79cfde7fa5960571fee36b9b-Abstract.html)の基盤）

---

### 機械学習での使いどころ

- [PCA](../../ml/pca/): 共分散行列の固有値分解で次元削減
- スペクトラルクラスタリング: グラフラプラシアンの小さい固有値に対応する固有ベクトルでクラスタリング
- [カーネル PCA](https://doi.org/10.1162/089976698300017467): カーネル行列の固有値分解で非線形な主成分を抽出
- SVD による低ランク近似: レコメンドのユーザー × アイテム行列、画像の圧縮、LSI（潜在意味解析）の文書 × 単語行列。生成 AI の追加学習で使う [LoRA](/notes/generative-ai/lora/) も、重みの差分を低ランクの 2 つの行列の積で表す
- PageRank（Web ページの重要度）: リンク行列の最大固有値に対応する固有ベクトル

---

### 適さないケース / 落とし穴

- 対角化できない行列がある: 同じ固有値を複数持つと、線形独立な固有ベクトルが足りなくなることがある（下記の例）
- 大規模疎行列での全固有値計算は重い: 上位 k 個だけが必要なら、対称行列には [`scipy.sparse.linalg.eigsh`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html)、一般の行列には [`eigs`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigs.html) を使う
- `X^T X` を作ると誤差が増える: 条件数が 2 乗になる。[scikit-learn の PCA](https://scikit-learn.org/stable/modules/generated/sklearn.decomposition.PCA.html) は共分散行列を作らず、中心化した `X` を直接 SVD する
- スケールの違う特徴量での PCA: 分散の大きい特徴量が共分散行列を支配するので、PCA の前に [標準化](../../ml/standardization/) するのが基本

対角化できない行列の代表は `[[1, 1], [0, 1]]` です。固有値は 1 が重複し、固有ベクトルは `(1, 0)` 方向の 1 本しかありません。

```python
import numpy as np

J = np.array([[1.0, 1.0], [0.0, 1.0]])
eigvals, V = np.linalg.eig(J)
print("λ =", eigvals.real)
print("V =", V.real.tolist())
print("cond(V) =", f"{np.linalg.cond(V):.1e}")
```

```text
λ = [1. 1.]
V = [[1.0, -1.0], [0.0, 2.220446049250313e-16]]
cond(V) = 9.0e+15
```

`eig` はエラーを出さずに 2 本の列を返しますが、2 本目は `(-1, 2.2e-16)` で 1 本目とほぼ平行です。`V` の条件数は 9.0e+15 なので、`V^-1` を使う再構成は信用できません。固有値が重複したら `V` の条件数を確認します。
