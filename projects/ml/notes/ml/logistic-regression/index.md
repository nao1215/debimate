---
title: "ロジスティック回帰 - Pima の糖尿病データを元の単位のまま liblinear に渡すと、年齢の係数が 3.5% に縮む"
date: 2026-05-24
draft: false
series: ["機械学習ノート", "Machine Learning"]
tags: ["machine-learning", "scikit-learn", "supervised"]
weight: 19
topics: ["Machine Learning（評価・概念・アルゴリズム）"]
---

ロジスティック回帰（logistic regression）は、特徴量に重みを掛けて足した値をシグモイド関数に通し、0〜1 の確率を出す分類のモデルです。重みは係数と呼ばれ、どの特徴量が確率をどちらへ動かすかを表すので、予測に加えて「何が効いているか」の説明にも使われます。

[scikit-learn](https://scikit-learn.org/stable/) の [`LogisticRegression`](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LogisticRegression.html) には `solver` という引数があり、既定の `"lbfgs"` や `"liblinear"` などから、係数を求める計算の方法を選びます。係数は、正解とモデルが出す確率の食い違いを表す損失が最小になるように決まるので、solver が違っても同じ係数になるはずです。そうなるかを実データで比べました。

データは、データセットを公開している [OpenML](https://www.openml.org/d/37) の Pima Indians Diabetes です。米国アリゾナ州に住むピマ族の 21 歳以上の女性について、妊娠回数・血糖値・BMI などと、糖尿病の検査が陽性だったかを並べたデータです。欠損を除いた 752 人について、5 列を元の単位のまま使いました。比べる基準は、データに最もよく当てはまる係数で、これを最尤推定と呼びます。

ただし scikit-learn は、何も指定しないと、係数を小さく抑えるペナルティを損失に足します。これを正則化と呼び、強さは引数 `C` で決めます。既定は `C=1.0` で、小さいほどペナルティが重くなります。次の図は、最尤推定を 100% として、同じ `C=1.0` で solver だけを変えた係数です。

{{< figure src="lr_cover.webp" alt="横向きの棒グラフ。妊娠回数・血糖値・BMI・家族歴の指標・年齢・切片の 6 つについて、係数が最尤推定の何 % かを 2 本ずつ並べている。青い既定の lbfgs は 99.4%、99.9%、100.2%、91.7%、100.6%、99.6% で、100% の点線にほぼ届く。赤い liblinear は 93.2%、79.4%、54.5%、71.3%、3.5%、69.4% で、年齢はほぼ 0" caption="元の単位のままの 5 列と C=1.0 で、既定の lbfgs と liblinear が返した係数（正則化なしの最尤推定 = 100%）" align="center" >}}

liblinear は、年齢の係数が 3.5%、BMI が 54.5%、切片が 69.4% まで縮みました。既定の lbfgs は、家族歴の指標を除けば 99〜101% で、最尤推定とほぼ同じです。どちらも警告は出さず、学習データの正解率も 0.774 と 0.769 でほとんど変わりません。

`solver` の既定は 0.21 まで `"liblinear"` で、2019 年 12 月の [0.22](https://scikit-learn.org/stable/whats_new/v0.22.html) から `"lbfgs"` です。古いコードで liblinear のまま学習した係数から「年齢の効果はほぼ 0」と報告すると、最尤推定とは大きく違う値を伝えることになります。

縮んだ原因は solver そのものではなく、liblinear が切片にもペナルティを掛けることにあります。単位を変えていない列は平均が 0 から遠く、切片が大きいので、切片が縮められた分を他の係数が縮んで埋め合わせます。

<br>

本記事では、ロジスティック回帰を scikit-learn で使い始めた人と、係数を読んで要因を説明したい人に向けて、次の疑問に答えます。

- ロジスティック回帰は、何を出して、何を最小にするのか。
- 正則化なしの係数は、どう求めて、どう読むのか。
- 既定の `C=1.0` は、どの係数をどれだけ縮めるのか。
- liblinear で切片と係数が縮むのは、どう防げるのか。
- 列の単位と正則化の強さで、予測と確率はどう変わるのか。
- 正則化を外すと、何が起きるのか。

実験は scikit-learn 1.9.1 と NumPy 2.5.4 で行いました。図を描く処理も含めた完全なコードは [logistic-regression_gen.py](https://github.com/nao1215/debimate/blob/main/projects/ml/scripts/notes/logistic-regression_gen.py) にあります。

---

### 確率を出す線形モデル

ロジスティック回帰は、特徴量 `x` と係数 `w`、切片 `b` から、まず `z = w · x + b` を計算します。ここまでは[線形回帰](../linear-regression/)と同じです。次に `z` を[シグモイド関数](../activation-functions/) `p = 1 / (1 + exp(-z))` に通し、どんな `z` も 0〜1 の確率 `p` に変えます。

`z` は、確率 `p` から求めた log-odds（対数オッズ）`log(p / (1 - p))` に当たります。確率は 0〜1 に収まる必要があるので、重みを掛けて足した値で直接表すと範囲を外れます。log-odds はマイナスからプラスまでどんな値も取れるので、足した値をそのまま当てられます。log-odds と確率の行き来は、[対数・指数と log-odds](../../math/log-exp-logodds/) で図と一緒に説明しています。

<br>

<details><summary>Pima の列と、除いた 16 行</summary>

列名は OpenML の表記のままで、preg が妊娠回数、plas が血糖値、mass が BMI、pedi が家族歴の指標、age が年齢です。

家族歴の指標は、元のデータで Diabetes Pedigree Function と呼ばれる列で、血縁者に糖尿病の人がどれだけいるかを 1 つの数にした値です。血糖値は、ブドウ糖を飲んで 2 時間後に測った値です。元の 768 人にはどちらかが 0 の人が 16 人いますが、生きている人の血糖値や BMI が 0 になることは無いので、[欠損値](../missing-values/)として除きました。本記事の数字は、診断の基準ではありません。

</details>

<br>

次のコードは、血糖値の列だけを使って、正則化なしで学習します。`C=np.inf` は、ペナルティを 0 にして正則化を外す指定です。

```python
pima = fetch_openml(data_id=37, as_frame=True).frame
pima = pima[(pima["plas"] > 0) & (pima["mass"] > 0)]  # 血糖値か BMI が 0 の 16 行は欠損なので除く
cols = ["preg", "plas", "mass", "pedi", "age"]
X = pima[cols].to_numpy(dtype=float)
y = (pima["class"] == "tested_positive").to_numpy(dtype=int)
print(f"{len(y)} 人、陽性 {y.sum()} 人（{y.mean():.4f}）")

one = LogisticRegression(C=np.inf).fit(X[:, [1]], y)  # 列は血糖値だけ、正則化なし
w, b = one.coef_[0, 0], one.intercept_[0]
print(f"w = {w:.4f}、b = {b:.3f}、p = 0.5 になる血糖値 {-b / w:.1f} mg/dL")
for g in [100, 140, 180]:
    z = w * g + b
    print(f"血糖値 {g}: z = {z:+.2f}、p = {1 / (1 + np.exp(-z)):.3f}")
```

```text
752 人、陽性 264 人（0.3511）
w = 0.0405、b = -5.690、p = 0.5 になる血糖値 140.6 mg/dL
血糖値 100: z = -1.64、p = 0.162
血糖値 140: z = -0.03、p = 0.493
血糖値 180: z = +1.59、p = 0.831
```

{{< figure src="lr_sigmoid.webp" alt="横軸が血糖値 40〜205 mg/dL、縦軸が陽性の確率 p の図。陰性の人の点は 0 の付近、陽性の人の点は 1 の付近に横へ散らばり、血糖値 80〜200 の範囲で大きく重なっている。学習した p の曲線は左下から S 字に上がり、血糖値 141 付近で 0.5 の点線と交わる" caption="血糖値だけで学習した p と、752 人の陽性・陰性" align="center" >}}

血糖値 140.6 mg/dL で `z` が 0、`p` が 0.5 になり、そこから離れるほど `p` は 0 か 1 に近づきます。陽性と陰性の人は血糖値の範囲で大きく重なっていて、曲線はその重なり方を確率で表しています。

0.5 を境に陽性か陰性かを返すのが `predict` で、確率そのものは `predict_proba` が返します。見逃しを減らしたい時は、`predict_proba` の確率を 0.3 など低い[閾値](../confusion-matrix/)で区切ります。

列が 2 つなら `p = 0.5` の境目は直線、3 つなら平面、それ以上なら超平面になり、この形からロジスティック回帰は線形分類器と呼ばれます。次の図は、血糖値と BMI の 2 列で学習した結果です。

{{< figure src="lr_boundary.webp" alt="横軸が血糖値 40〜205 mg/dL、縦軸が BMI 15〜70 の散布図。青い陰性の人は左下に、赤い陽性の人は右上に多く、中央で重なっている。p = 0.1、0.3、0.5、0.7、0.9 の等高線は全て右下がりの平行な直線で、太い p = 0.5 の線は 血糖値 = 215.2 - 2.23 × BMI を通る" caption="血糖値と BMI の 2 列で学習した確率の等高線" align="center" >}}

確率が同じになる所は全て平行な直線で、`p = 0.5` の線は 血糖値 = 215.2 - 2.23 × BMI です。BMI が 1 増えると、同じ確率になる血糖値は 2.23 mg/dL 下がります。

円や XOR のように曲がった境目が要るデータは苦手で、列の 2 乗や、列どうしを掛け合わせた特徴量を自分で足すか、[RandomForest](../random-forest/) や[勾配ブースティング](../gradient-boosting/)、[SVM](../svm/) の RBF カーネル、[ニューラルネットワーク](../perceptron/)に切り替えます。

<br>

係数は、モデルの確率が学習データの正解をどれだけ言い当てられるかで決めます。陽性の人には `p`、陰性の人には `1 - p` を割り当て、全員分を掛けた値を尤度（likelihood）と呼びます。尤度が最大になる係数を選ぶのが最尤推定で、log を取って符号を反転した負の対数尤度を最小にしても同じです。負の対数尤度を人数で割った値は、分類の評価に使う log loss、つまり[交差エントロピー](../loss-functions/)と一致します。

正解 `y` が 1 か 0 かで、1 人分の値は `-y log p - (1 - y) log (1 - p)` と書けます。陽性の人に `p = 0.9` を出せば `-log 0.9` で 0.105、`p = 0.5` なら 0.693、`p = 0.01` なら 4.61 です。外れた向きに 0 や 1 へ近い確率を出すほど、1 人分の値は大きくなります。

---

### 最尤推定とニュートン法

負の対数尤度は、係数について下に凸な[凸関数](../../math/convex-functions/)です。切片の列 1 も含め、どの列も残りの列を定数倍して足した値で作れなければ、最小の点はあっても 1 つだけです。線形回帰と違って係数を 1 つの式では求められないので、少しずつ係数を動かす反復で求めます。損失を各係数で微分した勾配は、切片の列 1 を足した `X` で `X^T (p - y)` と短く書け、導き方は[偏微分と勾配](../../math/partial-derivative-gradient/)で扱っています。勾配の逆向きに少しずつ進むのが[勾配降下法](../../math/gradient-descent-sgd/)です。

ニュートン法は、今いる点で損失を 2 次関数で近似し、その 2 次関数が最小になる点へ一度に移る反復です。近似には勾配に加えて、もう 1 回微分した行列 `X^T diag(p(1 - p)) X` を使います。この行列をヘッセ行列と呼び、損失がどれだけ曲がっているかを表します。損失が 2 次関数に近い形をしていれば、数回の反復で最小の点に届きます。5 列全てで、NumPy だけで書いてみました。

```python
Xa = np.column_stack([np.ones(len(X)), X])  # 先頭に切片の列 1 を足す
beta = np.zeros(Xa.shape[1])
for step in range(8):
    p = 1 / (1 + np.exp(-Xa @ beta))
    grad = Xa.T @ (p - y)                       # 負の対数尤度の勾配
    H = (Xa * (p * (1 - p))[:, None]).T @ Xa    # 2 回微分した行列（ヘッセ行列）
    beta -= np.linalg.solve(H, grad)
    nll = -np.sum(y * np.log(p) + (1 - y) * np.log(1 - p))
    print(f"{step + 1} 回目: 負の対数尤度 {nll:.4f}、勾配の大きさ {np.linalg.norm(grad):.1e}")
se = np.sqrt(np.diag(np.linalg.inv(H)))         # 係数の標準誤差

mle = LogisticRegression(C=np.inf, max_iter=10000).fit(X, y)  # 正則化なし
print("ニュートン法      :", beta.round(4))
print("C=np.inf の sklearn:", np.r_[mle.intercept_, mle.coef_[0]].round(4))
print("標準誤差          :", se.round(4))
```

```text
1 回目: 負の対数尤度 521.2467、勾配の大きさ 9.1e+03
2 回目: 負の対数尤度 363.4132、勾配の大きさ 1.6e+03
3 回目: 負の対数尤度 352.0787、勾配の大きさ 2.4e+02
4 回目: 負の対数尤度 351.6218、勾配の大きさ 1.1e+01
5 回目: 負の対数尤度 351.6206、勾配の大きさ 2.7e-02
6 回目: 負の対数尤度 351.6206、勾配の大きさ 2.0e-07
7 回目: 負の対数尤度 351.6206、勾配の大きさ 4.5e-12
8 回目: 負の対数尤度 351.6206、勾配の大きさ 6.5e-12
ニュートン法      : [-9.3228  0.1151  0.0359  0.0875  0.9206  0.0114]
C=np.inf の sklearn: [-9.3228  0.1151  0.0359  0.0875  0.9206  0.0114]
標準誤差          : [0.7373 0.0323 0.0036 0.0147 0.3008 0.0093]
```

5 回目で負の対数尤度は 351.6206 になり、6 回目には勾配の大きさが 2.0e-07 まで下がりました。求めた係数は、scikit-learn に `C=np.inf` を渡した結果と小数第 4 位まで一致します。統計の分野でよく使われる [statsmodels](https://www.statsmodels.org/stable/generated/statsmodels.discrete.discrete_model.Logit.html) の `Logit` も、`fit` は正則化を掛けない最尤推定で、正則化は `fit_regularized` という別のメソッドです。

<br>

#### 係数をオッズ比で読む

係数 `w_j` は、`x_j` が 1 増えた時に log-odds が増える量です。log-odds が `w_j` 増えると、オッズ `p / (1 - p)` は `exp(w_j)` 倍になり、この倍率をオッズ比と呼びます。血糖値の係数 0.0359 は 1 mg/dL あたりなので、10 mg/dL あたりに直すと `exp(0.359)` で 1.43 倍です。

最尤推定の係数は、同じ人数のデータを取り直せば少し違う値になります。そのばらつきの目安が標準誤差で、ヘッセ行列の逆行列を求め、対角成分の平方根を取ると得られます。係数 ± 1.96 × 標準誤差が 95% 信頼区間で、区間が 0 をまたぐ係数は、[仮説検定](../../math/hypothesis-test/)の 5% の水準で 0 と区別できません。

次のコードは、読みやすい単位ごとのオッズ比と区間を出し、liblinear の値と並べます。`JP` は列名を日本語に直す辞書で、図を描く行は省いています。

```python
units = {"preg": 1, "plas": 10, "mass": 5, "pedi": 0.5, "age": 10}
unit_label = {"preg": "1 回あたり", "plas": "10 mg/dL あたり", "mass": "5 あたり", "pedi": "0.5 あたり",
              "age": "10 歳あたり"}
lib = LogisticRegression(solver="liblinear").fit(X, y)
for k, c in enumerate(cols):
    u = units[c]
    lo, mid, hi = np.exp((beta[k + 1] + np.array([-1.96, 0, 1.96]) * se[k + 1]) * u)
    lib_or = np.exp(lib.coef_[0, k] * u)
    print(f"{JP[c]}（{unit_label[c]}）のオッズ比 {mid:.2f}（{lo:.2f}〜{hi:.2f}）、liblinear {lib_or:.2f}")
```

```text
妊娠回数（1 回あたり）のオッズ比 1.12（1.05〜1.20）、liblinear 1.11
血糖値（10 mg/dL あたり）のオッズ比 1.43（1.34〜1.54）、liblinear 1.33
BMI（5 あたり）のオッズ比 1.55（1.34〜1.79）、liblinear 1.27
家族歴の指標（0.5 あたり）のオッズ比 1.58（1.18〜2.13）、liblinear 1.39
年齢（10 歳あたり）のオッズ比 1.12（0.93〜1.34）、liblinear 1.00
```

{{< figure src="lr_odds.webp" alt="5 行の横向きの図。黒い丸が最尤推定のオッズ比、黒い横線が 95% 信頼区間、赤いひし形が liblinear のオッズ比。妊娠回数は 1.12 で区間は 1.05〜1.20、ひし形は 1.11 で区間の中。血糖値は 1.43 で区間 1.34〜1.54、ひし形 1.33 は区間の下限のすぐ外。BMI は 1.55 で区間 1.34〜1.79、ひし形 1.27 は区間の左外。家族歴の指標は 1.58 で区間 1.18〜2.13、ひし形 1.39 は区間の中。年齢は 1.12 で区間 0.93〜1.34 が 1 をまたぎ、ひし形は 1.00。右の欄に、各行の区間と liblinear の値を小数第 3 位まで書き、区間の中か外かを添えている" caption="最尤推定のオッズ比と 95% 信頼区間（黒）と、liblinear のオッズ比（赤）" align="center" >}}

年齢の区間は 0.93〜1.34 で 1 をまたいでいるので、このデータだけでは、年齢がオッズを増やすか減らすかを言い切れません。一方で liblinear の 1.00 だけを区間を添えずに報告すると、「年齢は効かない」と読まれます。

BMI では、liblinear のひし形は 95% 信頼区間の外にあり、血糖値も区間の下限のすぐ外です。

オッズ比は、確率の比ではありません。オッズが 1.43 倍になっても、確率が何ポイント動くかは元の確率で変わります。その様子は、[対数・指数と log-odds](../../math/log-exp-logodds/) で breast_cancer を使って図にしています。

---

### 既定の C=1.0 が縮める係数

scikit-learn の `LogisticRegression` は、何も指定しないと L2 正則化を掛けます。L2 正則化は、係数の 2 乗の和をペナルティとして損失に足し、係数を小さく抑える方法です。係数を 0 に向けて縮めますが、ちょうど 0 にはしません。係数の絶対値を足した値をペナルティにして、効かない係数をちょうど 0 にする L1 正則化もあります。0 になった列を外せば[特徴量選択](../feature-selection/)にもなり、2 つの違いは[正則化](../regularization/)で説明しています。最小にする値は `0.5 * (係数の 2 乗の和) + C * (全員分の負の対数尤度)` で、`C` が小さいほどペナルティが重くなります。切片 `b` はペナルティに入りません。

`C=1.0` という既定値そのものにも、データに合わせた根拠はありません。2019 年の記事 [Scikit-Learn's Defaults Are Wrong](https://ryxcommar.com/2019/08/30/scikit-learns-defaults-are-wrong/) は、名前どおりのロジスティック回帰なら正則化なしが自然で、`C=1.0` は根拠の無い数だと批判しました。予測に使うなら、`C` は[交差検証](../cross-validation/)で選びます。

`C` を 1e-4 から 100 まで動かし、元の単位のままの列と、平均 0・分散 1 に[標準化](../standardization/)した列で係数を比べました。標準化した方は、係数を元の単位に戻して比べています。

```python
Cs = np.logspace(-4, 2, 25)
paths = {"元の単位のまま": [], "標準化してから": []}
for C in Cs:
    raw = LogisticRegression(C=C, max_iter=10000).fit(X, y)
    paths["元の単位のまま"].append(raw.coef_[0] / mle.coef_[0])
    std = make_pipeline(StandardScaler(), LogisticRegression(C=C, max_iter=10000)).fit(X, y)
    coef = std[-1].coef_[0] / std[0].scale_           # 元の単位の係数に戻す
    paths["標準化してから"].append(coef / mle.coef_[0])
for C in [1.0, 0.01]:
    raw = LogisticRegression(C=C, max_iter=10000).fit(X, y)
    print(f"C={C}: 元の単位のまま / 最尤推定（%）", (raw.coef_[0] / mle.coef_[0] * 100).round(1))
print("列の標準偏差:", X.std(axis=0).round(2))
it_raw = LogisticRegression(max_iter=10000).fit(X, y).n_iter_[0]
it_std = make_pipeline(StandardScaler(), LogisticRegression(max_iter=10000)).fit(X, y)[-1].n_iter_[0]
print(f"C=1.0 で lbfgs が反復した回数: 元の単位のまま {it_raw} 回、標準化してから {it_std} 回")
```

```text
C=1.0: 元の単位のまま / 最尤推定（%） [ 99.4  99.9 100.2  91.7 100.6]
C=0.01: 元の単位のまま / 最尤推定（%） [ 86.6 100.  101.1  10.3 116.8]
列の標準偏差: [ 3.37 30.58  6.92  0.33 11.7 ]
C=1.0 で lbfgs が反復した回数: 元の単位のまま 74 回、標準化してから 7 回
```

{{< figure src="lr_cpath.webp" alt="2 枚の折れ線グラフ。横軸は対数目盛の C で、左ほど正則化が強い。縦軸は係数が最尤推定の何 % か。左の元の単位のままでは、オレンジの家族歴の指標が C=1 で約 92%、C=0.01 で約 10% と最初に縮み、青の妊娠回数は C=0.1 付近から、緑の BMI は C=0.003 付近から縮み始める。赤の血糖値は C=1e-4 でも 93% を保つ。灰色の年齢は C が小さくなるほど 100% を超えて最大 167% まで上がる。右の標準化してからでは、年齢以外の 4 本が重なって同じ速さで縮み、年齢は一度 126% まで上がってから縮む" caption="C を動かした時の係数（左は元の単位のまま、右は標準化してから）" align="center" >}}

元の単位のままでは、既定の `C=1.0` で縮んだのは家族歴の指標だけで、`C=0.01` では 10.3% まで縮みました。家族歴の指標は[標準偏差](../../math/stddev/)が 0.33 と小さく、同じだけ log-odds を動かすには係数を 0.92 と大きくする必要があります。L2 のペナルティは係数の 2 乗なので、大きな係数ほど重く掛かります。

反対に、血糖値は標準偏差が 30.58 と大きく、係数は 0.0359 と小さいので、2 乗してもペナルティはほとんど増えません。そのため `C=1e-4` まで強めても 93% を保ちます。

家族歴の指標が 0.92、血糖値が 0.0359 という係数を並べても、家族歴の方が 25 倍効くとは読めません。効き方を比べるなら、標準化してからの係数か、前の節で求めた読みやすい単位ごとのオッズ比を使います。

<br>

単位の違いは計算の手間にも出ます。列ごとに値の幅が大きく違うと損失の形が細長くなり、lbfgs の反復は元の単位のままで 74 回、標準化してからは 7 回でした。反復の上限 `max_iter` は既定で 100 なので、本記事のコードは `max_iter=10000` を付けて、途中で打ち切られないようにしています。

<br>

#### 年齢の係数が伸びる

左の図で一番目立つのは、年齢の線が 100% より上へ伸び、`C` が 5.6e-4 の辺りで 167% に達する動きです。年齢も標準偏差 11.7 に対して係数が 0.0114 と小さく、ペナルティをほとんど受けません。一方で、同じ範囲で妊娠回数は 36% まで縮んでいます。

年齢は妊娠回数との[相関係数](../../math/correlation/)が 0.55 で、年齢が高い人ほど妊娠回数も多い傾向があります。縮んだ妊娠回数が説明していた分は、ペナルティの軽い年齢の係数が大きくなって補っています。相関の強い列があると、片方が縮んだ分をもう片方が補うので、係数の大きさは `C` の選び方でも変わります。

右の標準化してからでは、年齢以外の 4 本がほぼ同じ速さで縮みます。年齢はここでも一度 126% まで上がり、妊娠回数の分を補ってから縮みます。

---

### liblinear と切片

`solver="liblinear"` は、台湾大学のグループが公開している [LIBLINEAR](https://www.csie.ntu.edu.tw/~cjlin/liblinear/) を呼び出します。liblinear が今も選ばれるのは、L1 正則化を使える solver が liblinear と saga だけで、文書も小さいデータには liblinear を勧めているからです。

scikit-learn が呼ぶ LIBLINEAR は、切片を他の係数と別に持たず、値が一定の列を `X` に 1 本足して、その列の係数から切片を求めます。scikit-learn は、足す列の値 `s` を `intercept_scaling` で決め、既定は 1 です。

{{< figure src="lr_intercept_col.webp" alt="左右 2 枚の図。左の lbfgs などでは、X の 5 列に係数 w1〜w5 が対応し、切片 b は列とは別に持つので、ペナルティは 0.5 ×（w1² + … + w5²）で b は入らない。右の liblinear では、X の右に値が一定の列 s を足し、その係数 w0 から切片 b = s × w0 を求める。ペナルティは 0.5 ×（w1² + … + w5² + w0²）で w0 も入る。s = 1 なら w0 = b で、最尤推定の b = -9.32 では切片だけで 0.5 × (-9.32)² = 43.5 になる" caption="liblinear は値が一定の列を足し、その係数で切片を表す" align="center" >}}

[文書](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LogisticRegression.html)で `intercept_scaling` を説明しているとおり、この足した列の係数 `w0` も、他の係数と同じくペナルティを受けます。lbfgs ではペナルティに入らない切片が、liblinear では縮められるということです。

冒頭の図は、次のコードで作りました。

```python
fits = {
    "正則化なし（C=np.inf）": LogisticRegression(C=np.inf, max_iter=10000),
    "既定（lbfgs、C=1.0）": LogisticRegression(max_iter=10000),
    "liblinear（C=1.0）": LogisticRegression(solver="liblinear"),
}
ratio = {}
for name, model in fits.items():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        model.fit(X, y)
    params = np.r_[model.coef_[0], model.intercept_]
    ratio[name] = params / np.r_[mle.coef_[0], mle.intercept_]
    print(f"{name:<20} 係数 {model.coef_[0].round(4)}、切片 {model.intercept_[0]:.3f}、"
          f"正解率 {model.score(X, y):.3f}、警告 {len(caught)} 件")
for name in list(fits)[1:]:
    print(f"{name} / 最尤推定（%）:", (ratio[name] * 100).round(1))
```

```text
正則化なし（C=np.inf）      係数 [0.1151 0.0359 0.0875 0.9206 0.0114]、切片 -9.323、正解率 0.773、警告 0 件
既定（lbfgs、C=1.0）      係数 [0.1144 0.0359 0.0877 0.8444 0.0114]、切片 -9.286、正解率 0.774、警告 0 件
liblinear（C=1.0）     係数 [1.073e-01 2.850e-02 4.770e-02 6.561e-01 4.000e-04]、切片 -6.467、正解率 0.769、警告 0 件
既定（lbfgs、C=1.0） / 最尤推定（%）: [ 99.4  99.9 100.2  91.7 100.6  99.6]
liblinear（C=1.0） / 最尤推定（%）: [93.2 79.4 54.5 71.3  3.5 69.4]
```

正解率は学習に使った 752 人で測った値です。元の単位のままの列は平均が 0 から遠く、血糖値は平均 122 mg/dL、年齢は平均 33 歳です。そのため最尤推定の切片は -9.32 と大きくなり、ペナルティの大半を切片が占めます。

<br>

#### 切片が縮んだ分を補う係数

liblinear は、ペナルティを減らすために切片を -9.32 から -6.47 へ 0 に近づけました。これで全員の `z` が 2.86 上がるので、何もしなければ全員の確率が上がります。そうならないのは、他の係数が縮んで `z` を下げたからです。

```python
lib = LogisticRegression(solver="liblinear").fit(X, y)
shift = (mle.coef_[0] - lib.coef_[0]) * X.mean(axis=0)  # 係数が縮んで下がった z（全員の平均）
print(f"切片が上がった量: {lib.intercept_[0] - mle.intercept_[0]:.3f}")
print("係数が縮んで下がった z:", dict(zip(cols, shift.round(2).tolist())), f"合計 {shift.sum():.2f}")
for name, m in [("最尤推定", mle), ("liblinear", lib)]:
    print(f"{name}: 0.5 * (切片^2 + 係数^2 の和) = {0.5 * (m.intercept_[0] ** 2 + np.sum(m.coef_ ** 2)):.1f}")
```

```text
切片が上がった量: 2.856
係数が縮んで下がった z: {'preg': 0.03, 'plas': 0.9, 'mass': 1.29, 'pedi': 0.13, 'age': 0.37} 合計 2.71
最尤推定: 0.5 * (切片^2 + 係数^2 の和) = 43.9
liblinear: 0.5 * (切片^2 + 係数^2 の和) = 21.1
```

係数が縮んで下がった `z` は、BMI で 1.29、血糖値で 0.90、年齢で 0.37、合計 2.71 で、切片が上がった 2.86 とほぼ同じです。ペナルティは 43.9 から 21.1 へ半分以下になりました。縮み方が年齢で特に大きいのは、年齢の区間が 1 をまたぐほど不確かで、0 近くまで下げても尤度があまり落ちないからだと考えられます。尤度の落ち幅そのものは測っていません。

<br>

#### intercept_scaling と標準化

文書は、切片へのペナルティを弱めるには `intercept_scaling` を大きくするよう書いています。`s` を 10 倍にすれば、同じ切片を表す `w0` は 10 分の 1 で済み、切片に掛かるペナルティは 100 分の 1 になります。`intercept_scaling` を 1・10・100 にした場合と、標準化してから使った場合を比べ、ペナルティを切片に掛かる分と係数に掛かる分に分けて出しました。

```python
settings = {}
for s in [1, 10, 100]:
    m = LogisticRegression(solver="liblinear", intercept_scaling=s).fit(X, y)
    settings[f"intercept_scaling={s}"] = np.r_[m.coef_[0], m.intercept_]
m = make_pipeline(StandardScaler(), LogisticRegression(solver="liblinear")).fit(X, y)
sc, lr = m[0], m[-1]
coef = lr.coef_[0] / sc.scale_                                  # 元の単位に戻す
icpt = lr.intercept_[0] - np.sum(lr.coef_[0] * sc.mean_ / sc.scale_)
settings["標準化してから"] = np.r_[coef, icpt]
base = np.r_[mle.coef_[0], mle.intercept_]
for name, v in settings.items():
    print(f"liblinear {name:<20} / 最尤推定（%）:", (v / base * 100).round(1))
for s in [1, 10, 100]:
    m = LogisticRegression(solver="liblinear", intercept_scaling=s).fit(X, y)
    w0 = m.intercept_[0] / s                                         # 足した列の係数
    print(f"intercept_scaling={s:<3}: 足した列の係数 {w0:8.4f}、切片に掛かる分 {0.5 * w0 ** 2:.4f}、"
          f"係数に掛かる分 {0.5 * np.sum(m.coef_ ** 2):.4f}")
```

```text
liblinear intercept_scaling=1  / 最尤推定（%）: [93.2 79.4 54.5 71.3  3.5 69.4]
liblinear intercept_scaling=10 / 最尤推定（%）: [99.3 99.5 99.3 91.3 98.9 99.1]
liblinear intercept_scaling=100 / 最尤推定（%）: [ 99.4  99.9 100.2  91.6 100.6  99.6]
liblinear 標準化してから              / 最尤推定（%）: [ 98.4  98.7  98.7  98.8 101.4  98.8]
intercept_scaling=1  : 足した列の係数  -6.4670、切片に掛かる分 20.9108、係数に掛かる分 0.2225
intercept_scaling=10 : 足した列の係数  -0.9235、切片に掛かる分 0.4264、係数に掛かる分 0.3643
intercept_scaling=100: 足した列の係数  -0.0928、切片に掛かる分 0.0043、係数に掛かる分 0.3662
```

{{< figure src="lr_scaling.webp" alt="縦軸が対数目盛の棒グラフ。intercept_scaling を 1・10・100 にした liblinear で、ペナルティのうち切片に掛かる分（赤）と 5 列の係数に掛かる分（青）を並べる。1 では切片に掛かる分 20.9 に対して係数に掛かる分 0.22 で、切片が 100 倍近く大きく、年齢の係数は 3.5%。10 では 0.426 と 0.36 でほぼ同じになり、年齢は 98.9%。100 では切片に掛かる分が 0.00431 まで下がり、係数に掛かる分は 0.37、年齢は 100.6%" caption="intercept_scaling ごとに、切片と係数に掛かるペナルティ" align="center" >}}

既定の `intercept_scaling=1` では、ペナルティのほとんどが切片に掛かる 20.9 で、係数に掛かる分は 0.22 しかありません。

`intercept_scaling=10` で切片に掛かる分は 0.43 まで下がり、年齢は 98.9% に戻り、100 では、家族歴の指標が 0.1 ポイント違うだけで、既定の lbfgs とほぼ同じ値になりました。家族歴の指標が約 91% に残るのは、前の節で見た `C=1.0` の縮みで、切片とは関係ありません。標準化してから使うと、列の平均が 0 になって切片が小さくなり、liblinear でも全て 98〜101% に収まります。

以下は、ここまでに比べた実装が何にペナルティを掛けるかの比較です。scikit-learn 1.9.1 と statsmodels 0.15 の文書を元にしています。

| 実装 | 係数のペナルティ | 切片のペナルティ | 標準誤差 |
|---|---|---|---|
| statsmodels の `Logit(...).fit()` | なし | なし | 出す |
| `LogisticRegression(C=np.inf)` | なし | なし | 出さない |
| `LogisticRegression()`（lbfgs） | L2、`C=1.0` | なし | 出さない |
| `LogisticRegression(solver="liblinear")` | L2、`C=1.0` | あり | 出さない |

---

### 予測と確率への影響

#### 単位を変えると予測も落ちる

ここまでの縮み方は係数の読み方に響くだけで、予測の性能はほとんど変わりませんでした。ところが、`C` を固定したまま、予測によく効く列の標準偏差を小さくすると、性能まで落ちます。血糖値を mg/dL から g/dL に直すと、値は 1000 分の 1 になり、標準偏差は 0.03 になります。同じ確率を出すには係数を 1000 倍にする必要があり、L2 のペナルティは 100 万倍に効きます。

単位だけを変えたデータで、5 分割で交差検証した ROC-AUC と log loss を比べました。[ROC-AUC](../roc-pr-auc/) は確率の順位が正解をどれだけ並べ分けるかを表し、1 に近いほど良い値です。後半では、`C` を 1e-4〜100 の 25 個から交差検証で選んでいます。

```python
Xg = X.copy()
Xg[:, 1] /= 1000  # 血糖値を mg/dL から g/dL に直す（1 g/dL = 1000 mg/dL）
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=0)
for unit, data in [("mg/dL", X), ("g/dL", Xg)]:
    for name, model in [("元の単位のまま", make_pipeline(LogisticRegression(max_iter=10000))),
                        ("標準化してから", make_pipeline(StandardScaler(), LogisticRegression(max_iter=10000)))]:
        r = cross_validate(model, data, y, cv=cv, scoring=["roc_auc", "neg_log_loss"])
        model.fit(data, y)
        scale = model[0].scale_[1] if len(model) == 2 else 1.0
        ratio_plas = model[-1].coef_[0, 1] / scale / (mle.coef_[0, 1] * (1000 if unit == "g/dL" else 1))
        print(f"{unit:<5} {name}: 血糖値の係数 / 最尤推定 {ratio_plas * 100:5.1f}%、"
              f"交差検証の ROC-AUC {r['test_roc_auc'].mean():.3f}、log loss {-r['test_neg_log_loss'].mean():.3f}")
for label, data, std_on in [("mg/dL・元の単位のまま", X, False), ("g/dL・元の単位のまま", Xg, False),
                            ("標準化してから（どちらの単位も同じ）", Xg, True)]:
    steps = [StandardScaler()] if std_on else []
    search = GridSearchCV(make_pipeline(*steps, LogisticRegression(max_iter=10000)),
                          {"logisticregression__C": Cs}, cv=cv, scoring="neg_log_loss").fit(data, y)
    print(f"{label}: 交差検証で選んだ C {search.best_params_['logisticregression__C']:.3g}、"
          f"log loss {-search.best_score_:.3f}")
```

```text
mg/dL 元の単位のまま: 血糖値の係数 / 最尤推定  99.9%、交差検証の ROC-AUC 0.839、log loss 0.476
mg/dL 標準化してから: 血糖値の係数 / 最尤推定  98.8%、交差検証の ROC-AUC 0.839、log loss 0.476
g/dL  元の単位のまま: 血糖値の係数 / 最尤推定   9.7%、交差検証の ROC-AUC 0.770、log loss 0.545
g/dL  標準化してから: 血糖値の係数 / 最尤推定  98.8%、交差検証の ROC-AUC 0.839、log loss 0.476
mg/dL・元の単位のまま: 交差検証で選んだ C 0.316、log loss 0.475
g/dL・元の単位のまま: 交差検証で選んだ C 100、log loss 0.477
標準化してから（どちらの単位も同じ）: 交差検証で選んだ C 0.178、log loss 0.476
```

g/dL のまま既定の `C=1.0` で学習すると、血糖値の係数は最尤推定の 9.7% まで縮み、ROC-AUC は 0.839 から 0.770 に、log loss は 0.476 から 0.545 に悪くなりました。標準化してから学習すると、どちらの単位でも 0.839 と 0.476 で、単位を変える前と同じです。

{{< figure src="lr_unit.webp" alt="横軸が対数目盛の C、縦軸が 5 分割の交差検証の log loss の図。青の mg/dL・元の単位のままは、C=0.1 より右で 0.476 前後に平らで、左端の 1e-4 でも 0.498。赤の g/dL・元の単位のままは、既定の C=1.0 で 0.545 と高く、C を大きくするほど下がって、右端の C=100 でようやく 0.477 に届く。黒の破線の標準化してからは、C=0.1 より右で青と重なり、左端では 0.642 まで上がる" caption="血糖値の単位と標準化の有無で変わる、交差検証の log loss" align="center" >}}

`C` を交差検証で選ぶと、g/dL のままでも log loss は 0.477 まで戻ります。ただし選ばれた `C` は 100 で、探した範囲の右端です。範囲を狭く取っていれば、戻りきらない `C` が選ばれます。図の左端で標準化した方の log loss が悪いのは、全ての列を同じ速さで縮めるからで、交差検証が選ぶ `C` の付近では mg/dL のままと同じ値です。

<br>

#### 学習データで確率の平均を見る

切片がペナルティに入らない時は、学習データで確率 `p` の平均が陽性の割合に一致します。負の対数尤度を切片で微分すると `Σ(p - y)` で、最小の点ではこれが 0 になるからです。この性質は、他の係数にペナルティがあっても成り立ちます。

```python
models = {
    "正則化なし（C=np.inf）": LogisticRegression(C=np.inf, max_iter=10000),
    "既定（lbfgs、C=1.0）": LogisticRegression(max_iter=10000),
    "lbfgs、C=0.01": LogisticRegression(C=0.01, max_iter=10000),
    "liblinear（C=1.0）": LogisticRegression(solver="liblinear"),
    "class_weight=\"balanced\"": LogisticRegression(class_weight="balanced", max_iter=10000),
}
print(f"陽性の割合                 : {y.mean():.4f}")
for name, model in models.items():
    p = model.fit(X, y).predict_proba(X)[:, 1]
    print(f"{name:<26} : 確率の平均 {p.mean():.4f}、正解率 {model.score(X, y):.3f}")
```

```text
陽性の割合                 : 0.3511
正則化なし（C=np.inf）            : 確率の平均 0.3511、正解率 0.773
既定（lbfgs、C=1.0）            : 確率の平均 0.3511、正解率 0.774
lbfgs、C=0.01               : 確率の平均 0.3511、正解率 0.771
liblinear（C=1.0）           : 確率の平均 0.3597、正解率 0.769
class_weight="balanced"    : 確率の平均 0.4481、正解率 0.761
```

lbfgs は `C` に関係なく 0.3511 で、陽性の割合と小数第 4 位まで一致しました。liblinear は切片を縮められた分だけ 0.3597 にずれています。

`class_weight="balanced"` は、各クラスの損失に、全員の人数 ÷ (2 × そのクラスの人数) の重みを掛けます。陽性は 752 ÷ (2 × 264) で 1.42 倍、陰性は 752 ÷ (2 × 488) で 0.77 倍になり、人数の少ない陽性が重く扱われるので、確率の平均は 0.4481 まで上がります。重み付けの使いどころは[クラス不均衡への対処](../class-imbalance/)で、ずれた確率を直す方法は[確率の校正](../probability-calibration/)で説明しています。陽性が少ないデータを評価する時は、正解率に加えて、確率の順位だけで評価する ROC-AUC や PR-AUC も使います。

<br>

#### 平均が合っても確率はずれる

確率の平均が陽性の割合と一致しても、一人一人の確率が合っているとは限りません。`C` を小さくすると、確率は陽性の割合 0.3511 に向かって縮みます。元の単位のままの列では、`C=0.01` でも主に縮むのは家族歴の指標だけなので、年齢以外の 4 列が同じ速さで縮む標準化した列で、`C=1.0` と `C=0.01` を比べました。

scikit-learn の [`calibration_curve`](https://scikit-learn.org/stable/modules/generated/sklearn.calibration.calibration_curve.html) は、区間ごとに確率の平均と、実際に陽性だった割合を返します。

既定の `strategy="uniform"` は確率の幅で区間を等分しますが、ここでは `strategy="quantile"` を指定して、確率の低い順に人を 5 等分しました。確率は、まず学習に使った 752 人で求め、次に 5 分割の交差検証で、学習に使っていない人について求めました。

```python
for C in [1.0, 0.01]:
    m = make_pipeline(StandardScaler(), LogisticRegression(C=C)).fit(X, y)
    p = m.predict_proba(X)[:, 1]
    frac, mean_p = calibration_curve(y, p, n_bins=5, strategy="quantile")  # 確率の低い順に 5 等分
    print(f"標準化、C={C}: 確率の平均 {p.mean():.4f}、正解率 {m.score(X, y):.3f}、"
          f"ROC-AUC {roc_auc_score(y, p):.3f}、log loss {log_loss(y, p):.3f}")
    print("  区間ごとの確率の平均:", mean_p.round(2), "/ 実際に陽性の割合:", frac.round(2))
    q = cross_val_predict(m, X, y, cv=cv, method="predict_proba")[:, 1]  # 学習に使っていない人の確率
    frac_cv, mean_cv = calibration_curve(y, q, n_bins=5, strategy="quantile")
    print("  交差検証の確率の平均:", mean_cv.round(2), "/ 実際に陽性の割合:", frac_cv.round(2),
          f"/ log loss {log_loss(y, q):.3f}")
```

```text
標準化、C=1.0: 確率の平均 0.3511、正解率 0.773、ROC-AUC 0.843、log loss 0.468
  区間ごとの確率の平均: [0.06 0.14 0.27 0.48 0.8 ] / 実際に陽性の割合: [0.01 0.15 0.31 0.48 0.8 ]
  交差検証の確率の平均: [0.06 0.14 0.27 0.47 0.8 ] / 実際に陽性の割合: [0.02 0.15 0.32 0.45 0.81] / log loss 0.476
標準化、C=0.01: 確率の平均 0.3511、正解率 0.777、ROC-AUC 0.842、log loss 0.494
  区間ごとの確率の平均: [0.14 0.22 0.31 0.43 0.65] / 実際に陽性の割合: [0.01 0.14 0.35 0.46 0.79]
  交差検証の確率の平均: [0.15 0.23 0.32 0.43 0.63] / 実際に陽性の割合: [0.02 0.15 0.36 0.45 0.77] / log loss 0.504
```

{{< figure src="lr_calib.webp" alt="横軸が区間ごとの確率の平均、縦軸が区間で実際に陽性だった割合の図。点線の対角線に乗れば確率と実際の割合が一致する。青の C=1.0 は 0.06→0.01、0.14→0.15、0.27→0.31、0.48→0.48、0.80→0.80 で対角線に沿う。赤の C=0.01 は 0.14→0.01、0.22→0.14、0.31→0.35、0.43→0.46、0.65→0.79 で、横に縮んで対角線より急な線になり、両端の区間に確率 0.14・実際 0.01 と確率 0.65・実際 0.79 の注記がある" caption="標準化した列で、C=1.0 と C=0.01 の区間ごとの確率と実際に陽性の割合（学習に使った 752 人で測定）" align="center" >}}

`C=0.01` でも確率の平均は 0.3511 のままで、正解率 0.777 と ROC-AUC 0.842 も `C=1.0` とほとんど変わりません。一方で、確率が最も低い区間は確率 0.14 に対して実際の陽性は約 1%、最も高い区間は確率 0.65 に対して 79% で、両端の確率が真ん中へ寄っています。log loss は 0.468 から 0.494 に悪くなりました。

図は学習に使った 752 人で測った値ですが、交差検証で学習に使っていない人の確率を見ても、`C=0.01` の両端は 0.15 に対して 2%、0.63 に対して 77% で、同じように真ん中へ寄ります。確率そのものを使う時は、平均ではなく区間ごとに、学習に使っていないデータで比べます。

---

### 正則化を外した時の係数

ペナルティが係数を縮めるなら、`C=np.inf` で最尤推定を求めればよさそうです。ところが、学習データの陽性と陰性を 1 本の直線や 1 枚の平面で完全に分けられる時は、最尤推定が存在しません。係数を大きくするほど、陽性の `p` は 1 に、陰性の `p` は 0 に近づき、負の対数尤度はいくらでも 0 に近づくからです。この状態を完全分離と呼びます。

完全分離は、列の数に対して行が少ない時に起きやすくなります。scikit-learn に同梱の [breast_cancer](https://scikit-learn.org/stable/modules/generated/sklearn.datasets.load_breast_cancer.html) は、乳房のしこりから採った細胞を画像で測った 30 列と、良性か悪性かの正解を 569 件並べたデータです。7 割の 398 件で学習すると、30 列で完全に分けられました。引数 `tol` は、勾配がどこまで小さくなれば反復を止めるかを決める値です。この `tol` を変えながら、`C=np.inf` で学習しました。

```python
bc = load_breast_cancer()
X_tr, X_te, y_tr, y_te = train_test_split(bc.data, bc.target, test_size=0.3,
                                          random_state=0, stratify=bc.target)
scaler = StandardScaler().fit(X_tr)
X_tr, X_te = scaler.transform(X_tr), scaler.transform(X_te)
tols = [1e-4, 1e-6, 1e-8, 1e-10, 1e-12]
norm = {"lbfgs": [], "newton-cg": []}
for solver in norm:
    for tol in tols:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            m = LogisticRegression(C=np.inf, solver=solver, tol=tol, max_iter=100000).fit(X_tr, y_tr)
        norm[solver].append(np.linalg.norm(m.coef_))
        print(f"{solver:<9} tol={tol:.0e}: 係数の長さ {norm[solver][-1]:7.1f}、学習の正解率 {m.score(X_tr, y_tr):.3f}、"
              f"テストの正解率 {m.score(X_te, y_te):.3f}、テストの log loss {log_loss(y_te, m.predict_proba(X_te)):.3f}、"
              f"警告 {len(caught)} 件")
m1 = LogisticRegression().fit(X_tr, y_tr)
print(f"既定の C=1.0    : 係数の長さ {np.linalg.norm(m1.coef_):7.1f}、学習の正解率 {m1.score(X_tr, y_tr):.3f}、"
      f"テストの正解率 {m1.score(X_te, y_te):.3f}、テストの log loss {log_loss(y_te, m1.predict_proba(X_te)):.3f}")
```

```text
lbfgs     tol=1e-04: 係数の長さ   429.5、学習の正解率 1.000、テストの正解率 0.953、テストの log loss 1.488、警告 0 件
lbfgs     tol=1e-12: 係数の長さ  1811.1、学習の正解率 1.000、テストの正解率 0.953、テストの log loss 1.591、警告 0 件
newton-cg tol=1e-04: 係数の長さ   113.7、学習の正解率 1.000、テストの正解率 0.942、テストの log loss 0.939、警告 0 件
newton-cg tol=1e-12: 係数の長さ   592.9、学習の正解率 1.000、テストの正解率 0.936、テストの log loss 2.024、警告 0 件
既定の C=1.0    : 係数の長さ     3.5、学習の正解率 0.992、テストの正解率 0.959、テストの log loss 0.085
```

出力は、tol が両端の行だけを載せています。中間の 3 つの tol でも、テストの正解率と log loss は下の範囲に収まりました。係数の長さは、30 個ある係数を 2 乗して足した値の平方根です。

{{< figure src="lr_separation.webp" alt="横軸が tol で、左の 1e-4 から右の 1e-12 へ厳しくなる。縦軸は係数の長さで対数目盛。赤の lbfgs は 429、856、1162、1511、1811 と右へ行くほど伸びる。オレンジの newton-cg は 114、239、340、466、593 と伸びる。青の既定の C=1.0 は 3.5 の横線" caption="breast_cancer を C=np.inf で学習した時の tol と、係数の長さ" align="center" >}}

`C=np.inf` で学習した係数の長さは、lbfgs では tol を厳しくするほど 429.5 から 1811.1 まで伸び、newton-cg では 113.7 から 592.9 でした。完全分離したデータを正則化なしで学習すると、係数の大きさはデータではなく、tol と solver で決まります。どの設定でも警告は 0 件で、学習の正解率は 1.000 です。

テストの正解率は 0.936〜0.953 で、既定の `C=1.0` で得た 0.959 と大差ありません。一方で、テストの log loss は 0.939〜2.024 で、`C=1.0` で得た 0.085 と比べて 11〜24 倍です。係数が大きいと、テストで外した件にも 0 や 1 にごく近い確率を出すので、その件の log loss が大きくなります。学習データには完全に合うのに、テストでは確率が大きく外れるので、これも[過学習](../overfitting/)の 1 つの形です。

<br>

#### 行が少ない時に大きく出る係数

完全には分けられなくても、行が少ないと最尤推定の係数は大きく、ばらつきます。標準化した Pima の 5 列で、752 人から 40〜320 人を選んで学習する操作を 300 回ずつ繰り返しました。係数の長さは、752 人全員で求めた最尤推定を 1 として表します。

```python
Xs = StandardScaler().fit_transform(X)
full = np.linalg.norm(LogisticRegression(C=np.inf).fit(Xs, y).coef_)
rng = np.random.default_rng(0)
sizes = [40, 80, 160, 320]
res = {"正則化なし（C=np.inf）": [], "既定（C=1.0）": []}
for n in sizes:
    r = {k: [] for k in res}
    for _ in range(300):
        i = rng.choice(len(y), n, replace=False)       # 752 人から n 人を選ぶ
        for name, C in [("正則化なし（C=np.inf）", np.inf), ("既定（C=1.0）", 1.0)]:
            coef = LogisticRegression(C=C, max_iter=1000).fit(Xs[i], y[i]).coef_
            r[name].append(np.linalg.norm(coef) / full)
    for name in res:
        res[name].append(np.percentile(r[name], [10, 50, 90]))
        print(f"{n:>3} 人、{name:<14}: 係数の長さ / 752 人の最尤推定 "
              f"中央値 {np.median(r[name]):.2f}、90% 点 {np.percentile(r[name], 90):.2f}")
```

```text
 40 人、正則化なし（C=np.inf）: 係数の長さ / 752 人の最尤推定 中央値 1.59、90% 点 2.93
 40 人、既定（C=1.0）     : 係数の長さ / 752 人の最尤推定 中央値 1.09、90% 点 1.44
 80 人、正則化なし（C=np.inf）: 係数の長さ / 752 人の最尤推定 中央値 1.22、90% 点 1.71
320 人、正則化なし（C=np.inf）: 係数の長さ / 752 人の最尤推定 中央値 1.02、90% 点 1.17
320 人、既定（C=1.0）     : 係数の長さ / 752 人の最尤推定 中央値 0.99、90% 点 1.13
```

出力は一部の行だけを載せています。

{{< figure src="lr_small_n.webp" alt="横軸が学習に使った人数 40、80、160、320、縦軸が、752 人の最尤推定を 1 とした係数の長さの図。赤の正則化なしの中央値は 1.59、1.22、1.09、1.02 と人数が増えるほど 1 に近づき、40 人での 10〜90% 点の帯は 0.9〜2.9 と広い。青の既定の C=1.0 の中央値は 1.09、1.05、1.03、0.99 で、帯も赤より狭い。点線は 752 人の最尤推定の 1" caption="学習に使った人数と、752 人の最尤推定を 1 とした係数の長さ" align="center" >}}

40 人では、正則化なしの係数の長さが[中央値](../../math/median/)で 1.59 倍、10 回に 1 回は 2.93 倍以上になりました。320 人では 1.02 倍まで戻ります。既定の `C=1.0` は、人数が少ないほどペナルティの比重が上がるので、40 人でも中央値 1.09 倍に収まりました。

ペナルティは人数に関係なく 1 つで、負の対数尤度は全員分の和なので、`C` でどれだけ縮むかは行の数で変わります。[正則化](../regularization/)のノートでは、同じ行を 10 回並べるだけで、L2 正則化を掛けた線形回帰である Ridge の係数が変わる様子を実験しています。

本記事の実験は係数の長さを見ているだけで、ばらつきで長くなった分と、推定そのものの偏りを分けていません。

最尤推定の係数が絶対値で大きめに偏り、行の数に対して列の数が多いほど強くなることは、Sur 氏と Candès 氏の [2019 年の論文](https://doi.org/10.1073/pnas.1810420116)が示しています。日本語では[ロジスティック回帰の最尤推定量にはバイアスがある](https://hoxo-m.hatenablog.com/entry/2024/01/23/014147)が、列が 300 個の例でこの偏りを実験しています。偏りを小さくする推定の方法には、[Firth 氏の 1993 年の方法](https://doi.org/10.1093/biomet/80.1.27)があります。

---

### ロジスティック回帰を選ぶ時

学習が速く、確率と係数がそのまま出るので、二値分類ではまずロジスティック回帰で基準の性能を測り、木を使うモデルなどと比べます。予測の精度は RandomForest や勾配ブースティングに劣ることが多い一方、クリック率や信用スコアのように、確率と「何が効いたか」の説明の両方が要る場面では今も使われます。画像や音声のように、生の値から特徴を作る必要があるデータには向きません。

---

### 係数を読む前に決めること

予測に使うだけでも、列を標準化してから既定の lbfgs と `C=1.0` で始め、`C` は交差検証で選びます。元の単位のまま `C` を固定すると、標準偏差の小さい列から先に縮み、その列が予測によく効く時は性能も落ちます。

確率をそのまま使う時は、学習データで確率の平均が陽性の割合と一致しても、根拠にしません。lbfgs なら `C` に関係なく一致するからです。学習データで平均がずれていれば、liblinear で切片が縮められているか、`class_weight` などで重みが掛かっている可能性があります。

係数を説明に使うなら、どの値を報告するかを先に決めます。最尤推定のオッズ比を報告するなら、`C=np.inf` か statsmodels で求め、信頼区間も添えます。その前に、学習の正解率が 1.000 になっていないかを見ます。1.000 なら完全分離で、係数の大きさは tol と solver の都合なので、`C` を有限にするか列を減らします。

<br>

古いコードや記事を動かす時は、`solver` が明示されているかを見ます。明示が無ければ、0.21 までは liblinear、0.22 からは lbfgs で学習されています。liblinear を使うなら、列を標準化してから渡すか、`intercept_scaling` を大きくします。

<br>

<details><summary>1.8 以降で変わった引数の書き換え</summary>

正則化の種類を選ぶ引数 `penalty` は 1.8 で非推奨になり、1.10 で消える予定です。古いコードは次のように書き換えます。

| 古い書き方 | 1.9.1 での書き方 |
|---|---|
| `penalty=None` | `C=np.inf` |
| `penalty="l1"` | `l1_ratio=1`、solver は liblinear か saga |
| `penalty="elasticnet"`（L1 と L2 を混ぜた Elastic Net） | `l1_ratio` を 0 と 1 の間にし、solver は saga |
| `multi_class="ovr"` など | 指定するとエラーなので、引数ごと消す |
| liblinear に 3 クラス以上を渡す | エラーになるので、[`OneVsRestClassifier`](https://scikit-learn.org/stable/modules/generated/sklearn.multiclass.OneVsRestClassifier.html) で包む |

3 クラス以上を分ける時、liblinear 以外の solver は、ソフトマックス関数で全クラスの確率を一度に出す多項ロジスティック回帰を学習します。

</details>

<br>

係数やオッズ比を報告する時は、`solver`・`C`・標準化の有無を一緒に書きます。
