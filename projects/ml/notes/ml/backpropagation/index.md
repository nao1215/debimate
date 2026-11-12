---
title: "誤差逆伝播法 - backward の 1 行を消しても、正解率 96% まで学習が進む理由"
date: 2026-05-26
draft: false
series: ["機械学習ノート", "Machine Learning"]
tags: ["machine-learning", "deep-learning"]
weight: 36
topics: ["Machine Learning（評価・概念・アルゴリズム）"]
---

誤差逆伝播法（backpropagation、backprop）は、ニューラルネット（neural network、NN）の全ての重みについて、その重みを少し動かした時に[損失](../loss-functions/)がどれだけ変わるかを表す勾配を求める手続きです。入力から損失までを順に計算する向きを forward、その逆に損失から入力側へ勾配を求めていく向きを backward と呼びます。求めた勾配は、[確率的勾配降下法（SGD）](../../math/gradient-descent-sgd/)などの更新の手法に渡して重みを動かします。

以下は、[scikit-learn](https://scikit-learn.org/stable/) に同梱の [digits](https://scikit-learn.org/stable/modules/generated/sklearn.datasets.load_digits.html) を重みの層が 3 つあるニューラルネットで学習した結果です。digits は、0〜9 の手書き数字 1797 枚を 8×8 画素の濃さで表したデータです。forward と backward は Python の数値計算のライブラリ [NumPy](https://numpy.org/) で自分で書きました。比べたのは、正しい backward と、そこから[活性化関数](../activation-functions/)の微分を掛ける 1 行を消した backward です。

画像の 7 割で学習し、学習に使わなかった残りの 540 枚で正解率を測りました。これを以下ではテストの正解率と呼びます。横軸のエポックは、学習用の画像を一巡した回数です。

{{< figure src="bp_cover.webp" alt="横軸がエポック 0〜100、縦軸がテストの正解率 0.8〜1.0 の折れ線グラフ。青い実線の正しい backward は 10 エポック付近から上がり、100 エポックで 97.2%。赤い破線の活性化関数の微分を掛け忘れた backward は、序盤は青より早く上がり、28 エポック付近で青に追い抜かれ、100 エポックで 96.1%" caption="digits を 3 層のニューラルネットで学習した時のテストの正解率（正しい backward と、1 行を消した backward）" align="center" >}}

正しい backward のテストの正解率は 97.2% で、1 行を消した backward も 96.1% まで上がりました。序盤は、消した backward の方が早く上がっています。エラーは出ず、学習も進むので、正解率を見ているだけでは backward の間違いに気付けません。

backprop を理解するために backward を自分で書いてみた時や、ニューラルネットのライブラリ [PyTorch](https://pytorch.org/) で独自の演算の backward を書いた時に、「学習が進んだから合っている」と判断する場面があります。逆に、層を深くしたら学習が進まなくなった時は、backward が入力側の層へどれだけの勾配を届けているかを見ないと、原因が分かりません。

<br>

本記事では、ML を学び始めた人と、ニューラルネットを手元のデータで学習する人に向けて、次の疑問に答えます。

- backprop は何を計算し、なぜ出力側から逆向きに進むのか。
- backward を間違えても学習が進むのは、なぜか。
- その間違いは、どう見つけるのか。
- 数値微分で勾配が求まるなら、なぜ backprop が要るのか。
- 層を深くすると、なぜ学習が止まって見えるのか。
- 学習では、なぜ推論よりメモリが要るのか。

実験は scikit-learn 1.9.1、NumPy 2.5.4 で行いました。図を描く処理も含めた完全なコードは [backpropagation_gen.py](https://github.com/nao1215/debimate/blob/main/projects/ml/scripts/notes/backpropagation_gen.py) にあります。

---

### 2 層の手計算

最初に、重みの層が 2 つの小さな[多層パーセプトロン](../perceptron/)で、入力 1 つ分の forward と backward を全て書き出します。式は次の 4 行です。ReLU は、負の値を 0 にし、正の値はそのまま通す活性化関数です。

`z1 = w1 x + b1`、`a1 = ReLU(z1)`、`z2 = w2 a1 + b2`、`L = (z2 - y)^2`

値は `x=2, w1=3, b1=-1, w2=0.5, b2=2, y=5` とします。backward では連鎖律を使います。連鎖律は、関数を何段か重ねた式の微分が、各段の微分の掛け算になるという規則で、[偏微分と勾配](../../math/partial-derivative-gradient/)で扱っています。この規則を損失から 1 段ずつ当てはめます。最後に、各パラメータを `±1e-6` だけ動かして損失の差を測る数値微分と比べます。

```python
x, w1, b1, w2, b2, y = 2.0, 3.0, -1.0, 0.5, 2.0, 5.0


def tiny_loss(w1, b1, w2, b2):
    a1 = max(0.0, w1 * x + b1)
    return (w2 * a1 + b2 - y) ** 2


# forward
z1 = w1 * x + b1             # 5
a1 = max(0.0, z1)            # 5（ReLU）
z2 = w2 * a1 + b2            # 4.5
L = (z2 - y) ** 2            # 0.25

# backward（出力側から連鎖律）
dL_dz2 = 2 * (z2 - y)        # -1
dL_dw2 = dL_dz2 * a1         # -5
dL_db2 = dL_dz2 * 1          # -1
dL_da1 = dL_dz2 * w2         # -0.5
dL_dz1 = dL_da1 * (1 if z1 > 0 else 0)  # -0.5
dL_dw1 = dL_dz1 * x          # -1
dL_db1 = dL_dz1 * 1          # -0.5

# 数値微分: 1 つのパラメータだけを ±eps 動かして損失の差を測る
eps = 1e-6
params = {"w1": w1, "b1": b1, "w2": w2, "b2": b2}
numeric = {}
for name in params:
    plus, minus = dict(params), dict(params)
    plus[name] += eps
    minus[name] -= eps
    numeric[name] = (tiny_loss(**plus) - tiny_loss(**minus)) / (2 * eps)

print(f"L = {L}")
print("backward:", {"w1": dL_dw1, "b1": dL_db1, "w2": dL_dw2, "b2": dL_db2})
print("数値微分:", {k: round(v, 6) for k, v in numeric.items()})
```

```text
L = 0.25
backward: {'w1': -1.0, 'b1': -0.5, 'w2': -5.0, 'b2': -1.0}
数値微分: {'w1': -1.0, 'b1': -0.5, 'w2': -5.0, 'b2': -1.0}
```

`dL_dz1` の行で掛けている `(1 if z1 > 0 else 0)` は、ReLU の微分です。冒頭の実験で消したのは、これと同じ役割の 1 行です。

以下は、同じ計算をノードと矢印で描いた図です。各ノードの中の青い数字が forward の値、赤い数字がそのノードの勾配で、赤い破線の矢印が backward で勾配を渡す向きです。

{{< figure src="bp_tiny_network.webp" alt="x=2、w1=3、b1=-1 から z1=5、a1=5、z2=4.5、L=0.25 へ左から右に青い矢印で進む計算の図。各ノードの外に赤で勾配があり、∂L/∂z2 = -1、∂L/∂w2 = -5、∂L/∂b2 = -1、∂L/∂a1 = -0.5、∂L/∂z1 = -0.5、∂L/∂w1 = -1、∂L/∂b1 = -0.5、∂L/∂L = 1。赤い破線の矢印が L から z2 へ、z2 から w2・a1・b2 の 3 つへ戻り、∂L/∂z2 = -1 を 3 つで使い回すと書かれている" caption="2 層のニューラルネットの forward と backward" align="center" >}}

`∂L/∂w2`、`∂L/∂b2`、`∂L/∂a1` は、どれも 1 つ右の `∂L/∂z2 = -1` に掛け算をするだけで求まります。z2 より右の計算は、3 つで共有します。出力側から逆向きに進めば、ある段の勾配を 1 回求めるだけで、その左にある全てのパラメータに使い回せます。これが、backward を損失から始める理由です。

連鎖律そのものは古くからある微分の規則です。多層のニューラルネットの学習に使い、隠れ層が役に立つ表現を学べることを示して広めたのは、Rumelhart・Hinton・Williams の 1986 年の論文「[Learning representations by back-propagating errors](https://www.nature.com/articles/323533a0)」です。

---

### backward の 1 行を消した実験

冒頭の実験のネットワークは、digits の 64 画素を入力にし、64 個のユニットを持つ隠れ層を 2 つ挟んで、10 個の数字それぞれの確率を出します。重みの層は 3 つです。完全なコードは生成元の [backpropagation_gen.py](https://github.com/nao1215/debimate/blob/main/projects/ml/scripts/notes/backpropagation_gen.py) にあり、以下では準備と初期化、forward と損失、backward、学習の順に分けて載せます。

<br>

#### 準備と初期化

隠れ層の活性化関数には sigmoid を使います。sigmoid は `1 / (1 + e^(-z))` で、どんな値も 0〜1 に押し込む関数です。その微分は、sigmoid の出力 h を使って `h (1 - h)` と書け、最大でも `z = 0` の時の 0.25 です。

重みの初期値は、平均 0、標準偏差 `1/√n` の正規分布から取ります。n は、その重みに入ってくる側の層のユニット数です。入力の画素は、[標準化](../standardization/)して平均 0、分散 1 に揃えます。ReLU 用の設定は、層を深くする節で使います。

```python
X, y_all = load_digits(return_X_y=True)
X_tr, X_te, y_tr, y_te = train_test_split(X, y_all, test_size=0.3, random_state=0, stratify=y_all)
scaler = StandardScaler().fit(X_tr)
X_tr, X_te = scaler.transform(X_tr), scaler.transform(X_te)

ACTS = {  # 活性化関数と、その微分（h は活性化した後の値）
    "sigmoid": (lambda z: 1 / (1 + np.exp(-z)), lambda z, h: h * (1 - h)),
    "relu": (lambda z: np.maximum(z, 0), lambda z, h: (z > 0).astype(float)),
}


def init(act, n_layers, rng, width=64):
    dims = [64] + [width] * (n_layers - 1) + [10]  # 入力 64 画素、出力 10 クラス
    # sigmoid は標準偏差 1/√n、ReLU は He の初期化の √(2/n)
    std = (lambda n: np.sqrt(2 / n)) if act == "relu" else (lambda n: 1 / np.sqrt(n))
    Ws = [rng.normal(0, std(dims[i]), (dims[i], dims[i + 1])) for i in range(n_layers)]
    bs = [np.zeros(dims[i + 1]) for i in range(n_layers)]
    return Ws, bs
```

<br>

#### forward と損失

forward は、各層で `z = h W + b` を計算し、隠れ層では sigmoid を通します。backward で使うので、各層の入力 `h` と活性化する前の `z` をリストに残します。

最後の層の 10 個の値は、softmax で確率に変えます。softmax は、値の大小の順を保ったまま、全てが 0 以上で合計が 1 になるように変換する関数です。損失は交差エントロピーで、正解の数字に付けた確率の対数にマイナスを付け、ミニバッチの件数で平均します。

```python
def forward(Ws, bs, x, act):
    f, _ = ACTS[act]
    hs, zs = [x], []  # 各層の入力 h と、活性化する前の z を残す
    for i, (W, b) in enumerate(zip(Ws, bs)):
        zs.append(hs[-1] @ W + b)
        if i < len(Ws) - 1:
            hs.append(f(zs[-1]))  # 最後の層は活性化せず、softmax に渡す
    return hs, zs


def softmax(z):
    e = np.exp(z - z.max(axis=1, keepdims=True))
    return e / e.sum(axis=1, keepdims=True)


def loss_only(Ws, bs, x, y, act):
    p = softmax(forward(Ws, bs, x, act)[1][-1])
    return -np.log(p[np.arange(len(y)), y]).mean()  # 交差エントロピー
```

<br>

#### backward

backward は、最後の層の `∂L/∂z` から始めます。softmax と交差エントロピーを組み合わせると、`∂L/∂z` は「softmax の確率から、正解の位置だけ 1 を引いた値」になります。損失をミニバッチの件数 N で平均したので、勾配も N で割ります。下のコードの `g` がこの値です。

そこから入力側へ、1 層ずつ 3 つの計算を繰り返します。隠れ層では、まず `g` に活性化関数の微分を掛けて、その層の `∂L/∂z` にします。最初の節の手計算で ReLU の微分 `(1 if z1 > 0 else 0)` を掛けた行と同じ役割で、`bug=True` の時に飛ばすのはこの 1 行です。

次に、層の入力 `h` と `g` から重みの勾配 `h^T g` とバイアスの勾配を求めます。最後に `g` に重みの転置 `W^T` を掛け、1 つ入力側の層へ渡します。

```python
def loss_and_grads(Ws, bs, x, y, act, bug=False):
    _, df = ACTS[act]
    hs, zs = forward(Ws, bs, x, act)
    p = softmax(zs[-1])
    loss = -np.log(p[np.arange(len(y)), y]).mean()  # 交差エントロピー
    g = p.copy()
    g[np.arange(len(y)), y] -= 1
    g /= len(y)  # ∂L/∂z（最後の層）
    gWs, gbs = [None] * len(Ws), [None] * len(Ws)
    for i in reversed(range(len(Ws))):
        if i < len(Ws) - 1 and not bug:
            g = g * df(zs[i], hs[i + 1])  # 活性化関数の微分を掛ける（bug=True はこの 1 行を飛ばす）
        gWs[i] = hs[i].T @ g  # ∂L/∂W_i
        gbs[i] = g.sum(axis=0)  # ∂L/∂b_i
        g = g @ Ws[i].T  # 1 つ入力側の層へ渡す
    return loss, gWs, gbs
```

<br>

#### 学習

学習は、学習用の画像を 32 件ずつに分けたミニバッチごとに backward で勾配を求め、学習率 0.1 の SGD で重みを更新します。これを 100 エポック繰り返し、エポックごとにテストの正解率と、1 層目の重みの勾配の大きさを記録します。最後のループでは、初期値と乱数の種（seed）を 5 通りに変え、正しい backward と 1 行を消した backward で学習します。

```python
def accuracy(Ws, bs, x, y, act):
    return (forward(Ws, bs, x, act)[1][-1].argmax(axis=1) == y).mean()


def train(act, n_layers, epochs=100, lr=0.1, seed=0, bug=False):
    rng = np.random.default_rng(seed)
    Ws, bs = init(act, n_layers, rng)
    history = []  # エポックごとの (テストの正解率, 1 層目の勾配の大きさ)
    for _ in range(epochs):
        idx = rng.permutation(len(X_tr))
        for s in range(0, len(X_tr), 32):  # 32 件ずつのミニバッチで SGD
            b = idx[s:s + 32]
            _, gWs, gbs = loss_and_grads(Ws, bs, X_tr[b], y_tr[b], act, bug)
            for i in range(n_layers):
                Ws[i] -= lr * gWs[i]
                bs[i] -= lr * gbs[i]
        g1 = loss_and_grads(Ws, bs, X_tr, y_tr, act)[1][0]
        history.append((accuracy(Ws, bs, X_te, y_te, act), np.linalg.norm(g1)))
    return np.array(history)


runs = {}
for bug in [False, True]:
    accs = []
    for seed in range(5):
        h = train("sigmoid", n_layers=3, seed=seed, bug=bug)
        accs.append(h[-1, 0])
        if seed == 0:
            runs[bug] = h  # 冒頭の図に描いた seed 0 の学習曲線
    label = "微分を掛け忘れた backward" if bug else "正しい backward"
    print(f"{label}: テストの正解率 seed 0 {accs[0]:.3f}、seed 0〜4 {min(accs):.3f}〜{max(accs):.3f}")
```

```text
正しい backward: テストの正解率 seed 0 0.972、seed 0〜4 0.963〜0.974
微分を掛け忘れた backward: テストの正解率 seed 0 0.961、seed 0〜4 0.946〜0.961
```

seed を 5 通りに変えても、1 行を消した backward は 94.6〜96.1% まで学習しました。正しい backward との差は 1〜2 ポイントです。なぜ学習が進むのかは、次の節で勾配そのものを比べてから確認します。

---

### 勾配の照合で間違いを見つける

backward の間違いは、最初の節の手計算と同じように、数値微分と比べれば見つかります。これを勾配の照合（gradient check）と呼びます。ここでは 32 件のミニバッチで、1 層目の重み 4096 個の勾配を 1 つずつ数値微分で求め、backward の値と比べました。

```python
rng = np.random.default_rng(0)
Ws, bs = init("sigmoid", 3, rng)
xb, yb = X_tr[:32], y_tr[:32]


def numeric_grad(W, eps=1e-5):
    num = np.zeros_like(W)
    for idx in np.ndindex(W.shape):  # 1 要素ずつ ±eps 動かして損失を 2 回測る
        old = W[idx]
        W[idx] = old + eps
        lp = loss_only(Ws, bs, xb, yb, "sigmoid")
        W[idx] = old - eps
        lm = loss_only(Ws, bs, xb, yb, "sigmoid")
        W[idx] = old
        num[idx] = (lp - lm) / (2 * eps)
    return num


num_W1 = numeric_grad(Ws[0])
for bug in [False, True]:
    g = loss_and_grads(Ws, bs, xb, yb, "sigmoid", bug)[1][0]
    rel = np.linalg.norm(g - num_W1) / (np.linalg.norm(g) + np.linalg.norm(num_W1))
    cos = (g * num_W1).sum() / (np.linalg.norm(g) * np.linalg.norm(num_W1))
    ratio = np.linalg.norm(g) / np.linalg.norm(num_W1)
    label = "微分を掛け忘れた backward" if bug else "正しい backward"
    print(f"{label}: 相対誤差 {rel:.1e}、コサイン類似度 {cos:.3f}、大きさの比 {ratio:.1f}")
```

```text
正しい backward: 相対誤差 4.5e-09、コサイン類似度 1.000、大きさの比 1.0
微分を掛け忘れた backward: 相対誤差 9.1e-01、コサイン類似度 0.955、大きさの比 20.7
```

出力の 3 つの値は、4096 個の勾配を 1 本のベクトルとみなして比べたものです。

- 相対誤差: 差の大きさを 2 つの大きさの和で割った値。一致すれば 0
- コサイン類似度: 向きの近さ。同じ向きなら 1、直交すれば 0
- 大きさの比: backward の勾配の大きさ ÷ 数値微分の勾配の大きさ

相対誤差は勾配の大きさの桁に左右されずに比べられ、全く違えば 1 に近づきます。以下は、4096 個の重みについて、横軸に数値微分の勾配、縦軸に backward の勾配を取った図です。

{{< figure src="bp_gradcheck.webp" alt="2 つの散布図。左の正しい backward は、4096 個の点が全て、数値微分と一致する点線の上に並び、相対誤差 4.5e-09。右の活性化関数の微分を掛け忘れた backward は、点が右上がりの帯になるが、縦軸は -0.15〜0.15 と左の 20 倍ほどの範囲に広がり、一致する点線から大きく外れ、相対誤差 9.1e-01" caption="1 層目の重みの勾配を数値微分と backward で比べた結果（左右で縦軸の範囲が 20 倍ほど違う）" align="center" >}}

正しい backward は、数値微分と 8 桁以上一致しました。1 行を消した backward は、点が右上がりに並ぶので向きはおおむね合っていますが、縦軸の範囲が 20 倍ほど広く、相対誤差は 0.91 です。右の図の点線がほぼ水平に見えるのは、縦軸だけ範囲を広げたためで、点線は左と同じく縦と横が等しい所を表します。正解率では 1 ポイントの差だった間違いが、ここでは 8 桁の差になります。

<br>

#### 間違えた勾配でも損失が下がる理由

学習が進むのは、間違えた勾配でも、正しい勾配と近い向きを向いているからです。上の出力のとおり、1 層目の重みの勾配のコサイン類似度は 0.955 で、角度にして約 17 度しかずれていません。

勾配降下法では、更新に使う向きと正しい勾配の角度が 90 度未満なら、十分小さく進めば損失は下がります。以下は、重みが 2 つの時の損失の等高線に、3 つの向きを描いた図です。

{{< figure src="bp_descent.webp" alt="楕円の等高線の上の 1 点から 3 本の矢印が出ている図。青い正しい勾配の逆向きは等高線に直交して内側を向く（最小の点の方向からは約 28 度ずれる）。赤い間違えた勾配の逆向きは青から約 17 度ずれているが、やはり内側の等高線へ向かう。灰色の 90 度を超えてずれた向きは、点を通る接線の点線を越えて外側の等高線へ向かう" caption="損失の等高線と、更新に使う向き（重みが 2 つの場合の模式図）" align="center" >}}

点を通る点線は、その点で損失が変わらない向きです。正しい勾配の逆向きとの角度が 90 度未満の向きは全て点線の内側を向くので、小さく進めば損失は下がります。90 度を超えると、点線の外側へ出て損失が増えます。

sigmoid の微分は 0〜0.25 の正の値なので、掛け忘れた層では各ユニットの値の符号は変わらず、大きさの比が崩れるだけです。そこから重みの転置で混ぜた先の層では符号が変わり得ますが、全体としては上の 0.955 のとおり近い向きに留まりました。また、出力に一番近い 3 層目の重みの勾配は、微分を掛ける前に求まるので、間違えた backward でも正しいままです。

序盤に間違えた backward の方が早く上がったのは、0.25 以下の値を掛けない分だけ勾配が大きくなり、学習率を上げたのと同じ効果が出たからと考えられます。上の出力の大きさの比のとおり、1 層目の勾配は正しい値の 20.7 倍でした。

backward が正確でなくても学習が進むことは、研究でも知られています。Lillicrap らの「[Random synaptic feedback weights support error backpropagation for deep learning](https://www.nature.com/articles/ncomms13276)」（2016 年）は、backward で重みの転置の代わりに固定した乱数の行列を使っても、ネットワークが学習できることを示しました。学習が進んだことは、backward が正しいことの証拠になりません。

<br>

#### 照合のやり方

照合は、64 ビットの浮動小数点数で行います。数値微分の `eps` を小さくしすぎると、損失の差が丸めの誤差に埋もれるからです。数値微分は重み 1 つにつき損失を 2 回計算するので、ミニバッチは少ない件数にして時間を抑えます。照合は勾配の式を確認するためのものなので、件数が少なくても目的は果たせます。PyTorch で独自の演算の backward を書いた時は、[`torch.autograd.gradcheck`](https://docs.pytorch.org/docs/stable/generated/torch.autograd.gradcheck.gradcheck.html) が同じ照合をしてくれます。文書にも、既定の許容誤差は 64 ビットの入力を想定していると書かれています。

---

### 数値微分との速さ

数値微分で正しい勾配が求まるなら、backprop は要らないようにも見えます。ただし、数値微分はパラメータを 1 つずつ `±eps` 動かして損失を 2 回ずつ計算するので、パラメータが P 個なら損失の計算は 2P 回です。前の節のネットワークで、全パラメータの勾配を 1 回求める時間を `numeric_grad` と backward で比べました。

```python
n_params = sum(W.size + b.size for W, b in zip(Ws, bs))
t = time.perf_counter()
for _ in range(1000):
    loss_and_grads(Ws, bs, xb, yb, "sigmoid")
t_backprop = (time.perf_counter() - t) / 1000
t = time.perf_counter()
for W, b in zip(Ws, bs):
    numeric_grad(W)
    numeric_grad(b)
t_numeric = time.perf_counter() - t
print(f"パラメータ {n_params} 個: forward と backward {t_backprop * 1e3:.3f} ms、"
      f"数値微分 {t_numeric:.2f} s（損失の計算 {2 * n_params} 回）、{t_numeric / t_backprop:,.0f} 倍")
```

```text
パラメータ 8970 個: forward と backward 0.155 ms、数値微分 1.70 s（損失の計算 17940 回）、10,976 倍
```

{{< figure src="bp_cost.webp" alt="対数の横軸の横棒グラフ。上の青い forward と backward 1 回ずつは 0.155 ms、下の灰色の数値微分（損失を 17,940 回計算）は 1,705 ms" caption="全パラメータの勾配を 1 回求める時間（パラメータ 8970 個、32 件のミニバッチ）" align="center" >}}

パラメータが 8970 個しかない小さなネットワークでも、数値微分には forward と backward の約 1 万倍の時間が掛かりました。並行して他の処理が動く PC で測ったので倍率は回ごとに動き、上の出力を含めて 8 回測ると 6100〜11000 倍でした。パラメータが増えるほど、この差は比例して開きます。

backward は、forward で残した途中の値を使い、各段で行列の掛け算を 1〜2 回するだけなので、forward の数倍の時間で全ての勾配が揃います。勾配全体を元の関数の計算量の定数倍で求められることは、[Baur と Strassen（1983）](https://doi.org/10.1016/0304-3975(83)90110-X)が示しています。PyTorch の [autograd](https://docs.pytorch.org/docs/stable/autograd.html) は、forward の計算を記録しておき、`loss.backward()` の 1 行でこの backward を自動で行います。

---

### 層を深くすると学習が止まる

backward は、出力側から入力側へ 1 層進むたびに、その層の重みの転置と活性化関数の微分を掛けます。掛ける値が 1 より小さいと、入力側の層ほど勾配が小さくなります。これが勾配消失（vanishing gradient）です。冒頭と同じ digits のネットワークを重みの層 10 個まで深くし、初期化の直後に各層の重みに届く勾配の大きさを測りました。

```python
for act in ["sigmoid", "relu"]:
    Ws10, bs10 = init(act, 10, np.random.default_rng(0))
    norms = np.array([np.linalg.norm(gW) for gW in loss_and_grads(Ws10, bs10, X_tr, y_tr, act)[1]])
    print(f"{act} 10 層、初期化の直後: 1 層目の勾配は 10 層目の {norms[0] / norms[-1]:.1e} 倍")
```

```text
sigmoid 10 層、初期化の直後: 1 層目の勾配は 10 層目の 4.2e-06 倍
relu 10 層、初期化の直後: 1 層目の勾配は 10 層目の 5.5e-01 倍
```

{{< figure src="bp_layer_grad.webp" alt="横軸が層の番号 1〜10（1 が入力側）、縦軸が対数の軸で 10 層目の勾配に対する比の折れ線グラフ。赤い sigmoid は 10 層目の 1 から入力側へ直線的に下がり、1 層目で約 4e-06。青い ReLU は全ての層で 0.5〜1.5 の間に留まる" caption="10 層のニューラルネットの初期化の直後に、各層の重みに届く勾配の大きさ" align="center" >}}

sigmoid では、1 層目の勾配は 10 層目の 0.0000042 倍でした。1 層あたりに直すと約 0.25 倍で、sigmoid の微分の最大値 0.25 とほぼ同じです。重みの標準偏差を `1/√n` にした初期化では、重みを掛けても大きさがほぼ保たれるので、縮む分の多くは活性化関数の微分から来ていると考えられます。

ReLU の微分は正の値に対してちょうど 1 なので、縮みません。ReLU と組み合わせる [He の初期化](https://arxiv.org/abs/1502.01852)は、重みの標準偏差を `√(2/n)` に増やし、ReLU が負の値を 0 にして信号が半分になる分を補います。

<br>

#### 止まっている時に起きていること

勾配が小さいと、学習はどう見えるのか。sigmoid で重みの層を 4・6・8・10 個にしたネットワークと、ReLU で 10 個にしたネットワークを同じ設定で 600 エポック学習しました。右の図は、各エポックの後に学習用のデータ全体で求めた、1 層目の重みの勾配の大きさです。

{{< figure src="bp_depth.webp" alt="2 つの折れ線グラフ。左はテストの正解率で、ReLU 10 層は 3 エポック目、sigmoid 4 層は 44 エポック目で 0.9 を超える。sigmoid 6 層は 180 エポック付近まで 0.1 のまま止まり、200〜300 エポックで 0.92 まで上がる。sigmoid 8 層と 10 層は 600 エポックまで 0.1 のまま。右は 1 層目の重みに届く勾配の大きさで、sigmoid 6 層は 0.001 付近から徐々に増え、180 エポック付近で 0.01 を超えて跳ね上がる。sigmoid 8 層は 1e-05 前後、sigmoid 10 層は 1e-06 前後で横ばい" caption="層の数ごとのテストの正解率（左）と、1 層目の重みに届く勾配の大きさ（右）" align="center" >}}

```text
sigmoid 4 層: 100 エポック 0.946、300 エポック 0.957、600 エポック 0.957
sigmoid 6 層: 100 エポック 0.102、300 エポック 0.922、600 エポック 0.924
sigmoid 8 層: 100 エポック 0.102、300 エポック 0.100、600 エポック 0.102
sigmoid 10 層: 100 エポック 0.100、300 エポック 0.100、600 エポック 0.102
ReLU 10 層: 100 エポック 0.959、600 エポック 0.963
```

正解率 0.10 は、10 クラスを当てずっぽうに答えるのと同じ値です。100 エポックの時点で 6・8・10 層のネットワークの予測を数えると、テストの 540 枚全てに同じ数字を答えていて、学習用のデータの損失も、10 クラスに同じ確率を付けた時の `ln 10 ≈ 2.303` とほぼ同じ 2.30 でした。

6 層は 180 エポック付近まで止まって見えますが、右の図では、その間も 1 層目の勾配が少しずつ大きくなり、0.01 を超えた辺りで正解率が跳ね上がりました。なぜその時点で急に動き出すのかまでは、確認していません。8 層と 10 層の勾配は、1 層目で 6 層より 1〜3 桁小さく、600 エポックでも動き出しませんでした。

右の図で、ReLU の 10 層の勾配も 1e-05 付近まで下がっています。ReLU の 10 層は学習用の画像をほぼ全て当てるようになり、損失そのものが小さくなったからで、止まった sigmoid の 8 層とは理由が違います。勾配の大きさは、正解率と並べて読む必要があります。

止まって見える時にエポック数を増やせば抜けることもありますが、何エポック待てばよいかは事前に分かりません。ReLU と He の初期化にした 10 層は、3 エポック目で 9 割を超えました。深いネットワークで入力側まで勾配を届ける方法には、この他に次のものがあります。

- [ResNet](https://arxiv.org/abs/1512.03385) の残差接続: 層を飛ばす経路で勾配を直接届ける
- [Batch Normalization](https://arxiv.org/abs/1502.03167): 各層の入力の分布を揃える
- [Xavier の初期化](https://proceedings.mlr.press/v9/glorot10a.html): sigmoid や tanh に合わせて重みの大きさを決める

tanh は sigmoid と同じ S 字の形で、-1〜1 の値を取る活性化関数です。

---

### 学習で増えるメモリ

backward は、forward で求めた途中の値を使います。本記事のコードでも、`loss_and_grads` の backward は、`forward` が返した各層の `hs` と `zs` をそのまま読んでいます。そのため学習では、全ての層の途中の値を backward が終わるまで残しておく必要があります。以下の表の N は層の数です。

| 量 | 推論（forward だけ） | 学習（forward と backward） |
|---|---|---|
| 計算量 | `O(N)` | `O(N)`、forward の数倍 |
| 途中の値のメモリ | 直前の層の分だけ | 全ての層の分 |

途中の値は、ミニバッチの件数と層の幅に比例して増えます。大きなモデルでメモリが足りない時は、途中の値を一部だけ残し、backward の時に計算し直す [gradient checkpointing](https://docs.pytorch.org/docs/stable/checkpoint.html) で、計算を増やす代わりにメモリを減らします。学習中は勾配と更新の手法の状態も持つので、学習する重みを絞る [LoRA](/notes/generative-ai/lora/) のような方法も、メモリを減らすために使われます。

---

### backward を書いた後に確かめること

backward を自分で書いたら、学習を回す前に、小さなミニバッチで数値微分と照合します。冒頭の図のとおり、正解率は 97.2% と 96.1% で 1 ポイントしか違わず、学習の結果から間違いに気付くのは難しいからです。照合なら、相対誤差 4.5e-09 と 0.91 で、桁から違います。PyTorch の独自の演算なら、`torch.autograd.gradcheck` を 64 ビットの入力で回します。

autograd に backward を任せる場合の注意は、本記事では実行して確認していないので、PyTorch の文書を挙げるだけにします。[`Tensor.backward` の文書](https://docs.pytorch.org/docs/stable/generated/torch.Tensor.backward.html)によると、勾配は `.grad` に足し込まれるので、呼ぶ前に `.grad` を 0 にするか None にする必要があります。学習のループでは、更新のたびに [`optimizer.zero_grad()`](https://docs.pytorch.org/docs/stable/generated/torch.optim.Optimizer.zero_grad.html) で消すのが普通で、既定では 0 ではなく None にします。[autograd の文書](https://docs.pytorch.org/docs/stable/notes/autograd.html)には、backward に要る途中の値をその場で書き換えると、`backward()` の時点でエラーになるとも書かれています。

層を深くして正解率が当てずっぽうの値から動かない時は、エポック数を増やす前に、層ごとの勾配の大きさを出します。入力側へ 1 層ごとに一定の比で小さくなっていれば、前の節の sigmoid と同じ勾配消失で、活性化関数と初期化を見直します。

backward が勾配を正しく求めていることと、その勾配が入力側まで届いていることは、どちらも学習の正解率だけでは分かりません。前者は数値微分との照合で、後者は層ごとの勾配の大きさで確認します。
