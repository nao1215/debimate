---
title: "Quantization - 重みを 8 bit・4 bit に詰めて小さく速くする"
date: 2026-11-10
draft: false
series: ["技術ノート", "Generative AI"]
tags: ["generative-ai", "llm", "quantization"]
weight: 40
wrapTables: true
topics: ["LLM"]
---

LLM（大規模言語モデル）の中身の大半は、学習で決めた大量の数値で、これを重みと呼びます。量子化（quantization）は、この重みを FP16（16 bit の浮動小数点数）などから、8 bit や 4 bit の小さな整数に丸めて保存する手法です。丸めた整数と、整数を元の大きさに戻すための係数（スケール）だけを持つので、ファイルもメモリも小さくなります。その代わり、元の値との間に丸めの誤差が入ります。

例えば、[Ollama](https://ollama.com/)（手元で LLM を動かす OSS）で配られている [Qwen3](https://github.com/QwenLM/Qwen3) の 1.7B の[モデル](https://ollama.com/library/qwen3)は、重みの数値（1 つ 1 つをパラメータと呼びます）が 17 億個あります。

同じモデルが FP16・8 bit・4 bit の 3 種類で配られており、ファイルの大きさは 4.07 GB・2.22 GB・1.36 GB です（2026 年 11 月 10 日時点。ライブラリの表示では 4.1・2.2・1.4 GB。Ollama のタグは fp16・q8_0・q4_K_M で、読み方は後の節で説明します）。

以下は、このモデルの実際の重みから 8 個を取り出し、16・8・4 bit で持った時の図です。左は重み 1 個が使うビットの幅、右は元の値（白丸）と、丸めてから戻した値（色付きの丸）の位置です。

{{< figure src="images/quantization_concept.webp" alt="左に、重み 1 個の幅として 16 個・8 個・4 個のマスが並ぶ。右は数直線の上に同じ 8 個の重みの元の値を白丸で、丸めて戻した値を色付きの丸で置き、線で結んでいる。FP16 では白丸の真下に丸がある。8 bit では細かい目盛りに乗り、ずれは見えない。4 bit では目盛りが粗く、丸は最寄りの目盛りに移って線が斜めになり、2 組は同じ目盛りに重なる" caption="同じ 8 個の重みを 16・8・4 bit で持った時の幅と丸め" align="center" >}}

4 bit では表せる値（図の目盛り。図の範囲にはその一部が見えています）が 16 個しかないので、近い 2 つの重みが同じ値に潰れることがあります。8 bit では目盛りが 16 倍細かく、ずれは図では見えないほど小さくなります。

<br>

本記事では、手元の Ollama のモデルで確認しながら、LLM の推論（学習済みのモデルで文章を生成すること）で使われる量子化の仕組みを説明します。次の 3 つの疑問に、この順で答えます。

- 重みを何 bit の整数に、どう丸めるのか。実際のファイルでは重み 1 個が何 bit になっているのか。
- 丸めると何が失われるのか。重みの誤差と、答えの正しさはどれだけ変わるのか。
- 小さくすると何が得られるのか。なぜファイルとメモリだけでなく、生成も速くなるのか。

学習しながら量子化する手法（量子化を意識した学習）や、[GPTQ](https://arxiv.org/abs/2210.17323) のように少量のサンプルデータで丸め方を最適化する手法の細部は説明しません。生成の速さが何で決まるかは、[ローカル LLM の速さのノート](/notes/generative-ai/local-llm-speed/)で詳しく扱っています。


---

### 重みと bit 数

LLM の計算の大半は、入力（後で見る埋め込みで作るベクトル）に[重み行列を掛ける](/ml/math/vector-matrix-ops/)ことです。qwen3:1.7b で重み行列がどこに何個あるかを描くと、次のようになります。図の英字は、後で見るファイルの中での行列の名前です。

{{< figure src="images/quantization_structure.webp" alt="左から、入力の埋め込み（token_embd）、同じ形を 28 段重ねた層、出力の層（output）が矢印でつながる。層の中には、注意機構の 4 つの行列（attn_q、attn_k、attn_v、attn_output）と、FFN（全結合のネットワーク）の 3 つの行列（ffn_gate、ffn_up、ffn_down）がある" caption="qwen3:1.7b の重み行列の並び" align="center" >}}

入力の埋め込み（token_embd）は、トークン（単語や単語の一部。[トークナイザーのノート](/notes/generative-ai/tokenizer/)を参照）の番号から、そのトークンを表すベクトルを引く表です。

各層は、注意機構と FFN（Feed-Forward Network）の 2 つの部分を持ちます。注意機構は、各トークンがそれより前のトークンを参照する部分で、仕組みは [KV キャッシュのノート](/notes/generative-ai/kv-cache/)の前提の節にあります。FFN は、各トークンのベクトルに行列を掛けて変換する部分です。最後の出力の層（output）は、次のトークンの候補ごとの点数を出し、この点数を確率に直して次のトークンを選びます。

<br>

これらの行列の値を全部合わせると、qwen3:1.7b では約 17 億個です。FP16 なら 1 個 2 バイトなので、重みだけで 3〜4 GB になります。

重みを 4 bit に詰めると、FP16 の約 4 分の 1 になります（後で見る通り、実際は少し大きくなります）。小さくなって助かる場面は 3 つあります。

- ダウンロードとディスクの量が減ります。
- GPU（行列の計算を並列に行う装置）のメモリに載せる量が減り、より大きなモデルを同じ機材で扱えます。
- 生成が速くなります。文章は 1 トークンずつ生成され、1 トークンごとにほぼ全ての重みを GPU のメモリから演算器へ読み直すので、読む量が減るほど速くなります。

---

### 32 個ずつスケールを決めて丸める

整数に丸めるには、まず「整数の 1 目盛りが元の値でいくつか」を決める必要があります。この 1 目盛りの大きさがスケールです。本記事で扱う [llama.cpp](https://github.com/ggml-org/llama.cpp)（手元で LLM を動かす OSS）の Q8_0・Q4_0・Q4_K では、スケールを 32 個の重みごとに決めます。行列全体で 1 つにしない理由は、後で実際の重みで確認します。

Ollama は qwen3 を自前のエンジンで動かしますが、重みの形式と計算のライブラリ（ggml）は llama.cpp と共通です。

llama.cpp では、重みをどう丸めてどう並べるかの決まりを「型」と呼び、Q8_0 や Q4_K のように名前を付けています。Ollama のタグの q8_0 は、ほぼ全ての行列を Q8_0 の型で持つモデルで、q4_K_M は Q4_K を中心に複数の型を混ぜたモデルです（後で説明します）。

8 bit の型 Q8_0 は、重みを 32 個ずつのブロックに分け、ブロックごとに次の計算をします。

```text
d   = (ブロック内の |x| の最大値) / 127      ← スケール。FP16 で 1 個持つ
q_i = round(x_i / d)                        ← -127〜127 の整数。int8 で 32 個持つ
x_i ≈ d × q_i                               ← 使う時に戻す
```

1 ブロックは FP16 のスケール 2 バイトと整数 32 バイトで 34 バイトなので、重み 1 個あたり 8.5 bit です。絶対値が最大の値がちょうど ±127 に乗るようにスケールを選ぶので、ブロック内のどの値もはみ出しません。

4 bit の型 Q4_0 も形は同じで、整数が -8〜7 の 16 段になります。絶対値が最大の値が、その端の -8 に乗るように `d` を決めます。最大の値が正なら `d` を負にして、符号を反転させて -8 に乗せます。1 ブロックは 2 + 16 = 18 バイト、重み 1 個あたり 4.5 bit です。

<br>

#### 実際の重みで丸める

qwen3:1.7b の FP16 のファイルから、1 層目の FFN の行列（`blk.0.ffn_gate.weight`）の最初のブロックを取り出し、自分で丸めてみます。

[lab/block_error.py](https://github.com/nao1215/debimate/blob/main/content/notes/generative-ai/quantization/lab/block_error.py) の丸める部分は次の通りで、[NumPy](https://numpy.org/)（Python の数値計算ライブラリ）で上の式を書いています。コメントにある llama.cpp の関数名や FP32 の扱いの理由は、後の折りたたみに書きました。

```python
# lab/block_error.py から抜粋
def roundf(x):
    """C の roundf と同じく、ちょうど 0.5 は 0 から遠い側に丸める（np.round は偶数側）。"""
    t = np.trunc(x)
    return t + np.where(np.abs(x - t) >= 0.5, np.sign(x), 0)


def quant_q8_0(x):
    """32 個ごとに d = max|x| / 127 を求め、x / d を -127〜127 の整数に丸める。
    llama.cpp の quantize_row_q8_0_ref と同じく、丸めには FP32 の d の逆数を使い、
    d を FP16 にするのはファイルに書く時だけ。"""
    b = x.reshape(-1, 32)
    d32 = np.abs(b).max(axis=1) / np.float32(127)
    inv = np.divide(np.float32(1), d32, out=np.zeros_like(d32), where=d32 != 0)
    q = roundf(b * inv[:, None]).astype(np.int8)
    d = d32.astype(np.float16)                                 # ファイルには FP16 で入る
    return q, d, (q * d.astype(np.float32)[:, None]).reshape(-1)


def quant_q4_0(x):
    """32 個ごとに、絶対値が最大の値を -8 に合わせた d を持ち、-8〜7 の整数に丸める。"""
    b = x.reshape(-1, 32)
    idx = np.abs(b).argmax(axis=1)
    mx = b[np.arange(len(b)), idx]                           # 符号付きの最大値
    d32 = mx / np.float32(-8)
    inv = np.divide(np.float32(1), d32, out=np.zeros_like(d32), where=d32 != 0)
    q = np.clip(np.floor(b * inv[:, None] + 8.5), 0, 15).astype(np.int8) - 8   # (int8_t)(x + 8.5f)
    d = d32.astype(np.float16)                                 # Q8_0 と同じく FP16 は保存用
    return q, d, (q * d.astype(np.float32)[:, None]).reshape(-1)
```

ファイルを読む関数や誤差を集計する部分を含む全体（168 行）は、上のリンク先にあります。最初のブロックの後ろの 8 個を丸めた結果は次の通りです（[lab/output_block.txt](https://github.com/nao1215/debimate/blob/main/content/notes/generative-ai/quantization/lab/output_block.txt) の抜粋）。

```text
  FP16        : [-0.0034  0.0422 -0.0659 -0.0288 -0.0198  0.0025 -0.0334 -0.0898]
  Q8_0  d=0.000708  ints: [-5, 60, -93, -41, -28, 4, -47, -127]
        restored: [-0.0035  0.0425 -0.0658 -0.0290 -0.0198  0.0028 -0.0333 -0.0899]
  Q4_0  d=0.011230  ints: [0, 4, -6, -3, -2, 0, -3, -8]
        restored: [ 0.0000  0.0449 -0.0674 -0.0337 -0.0225  0.0000 -0.0337 -0.0898]
```

最後の -0.0898 がこのブロックで絶対値が最大の値で、Q8_0 では -127、Q4_0 では -8 になります。Q4_0 では目盛りの幅が 0.0112 もあるので、-0.0034 と 0.0025 はどちらも 0 に、-0.0288 と -0.0334 はどちらも -0.0337 に潰れます。冒頭の図は、この 8 個を描いたものです。

<br>

#### ブロックを小さく切る理由

ブロックを 32 個と小さく切るのは、大きな値の影響をそのブロックの中に閉じ込めたいからです。スケールは絶対値が最大の値に合わせるので、同じスケールを使う組に大きな値が 1 個あるだけで、目盛りが粗くなります。

以下は、上と同じブロックの 32 個の重みを 4 bit に丸めた図です。上の段は 32 個だけでスケールを決めた場合、下の段は、仮に 10 倍の大きさの重み（0.9。説明のために置いた値）を含む組と同じスケールを使った場合です。

{{< figure src="images/quantization_block.webp" alt="同じ 32 個の重みを 4 bit に丸めた 2 段の散布図。上の段は 32 個ごとのスケール（d = 0.0112）で、丸めて戻した値は元の値のすぐ近くにあり、0 に潰れた重みは 7 個。下の段は 0.9 の重みと同じスケール（d = 0.1125）で、ほとんどの値が 0 に、大きめの 5 個が ±0.1125 に移り、0 に潰れた重みは 27 個" caption="スケールを 32 個ごとに持つ場合と、大きな値と共有する場合の 4 bit の丸め" align="center" >}}

下の段では目盛りの幅が 0.1125 になり、32 個のうち 27 個が 0 に潰れます。行列全体で 1 つのスケールにすると、この状態がどこかの大きな値 1 個のせいで行列全体に起きます。32 個ごとなら、粗くなるのはその値を含むブロックだけです。

---

### Q4_K と Q4_K_M

Ollama で 4 bit のモデルとして配られている q4_K_M は、Q4_0 ではなく Q4_K という型を中心に使います。Q4_K は、2023 年に [llama.cpp に入った k-quants](https://github.com/ggml-org/llama.cpp/pull/1684) と呼ばれる型の 1 つです。

Q4_0 は 0 を中心に正負へ目盛りを並べるので、ブロックの値が正の側に偏っていると、負の側の目盛りが使われずに余ります。Q4_K は、ブロックの最小値を引いてから 0〜15 に丸めることで、偏ったブロックでも 16 段を無駄なく使います。

Q4_K は、256 個の重みを 1 つの大ブロックにし、その中を 32 個ずつ 8 つの小ブロックに分けます。スケールと最小値は 2 段で持ちます。大ブロックに FP16 の基準の値 `d` と `dmin` を 1 個ずつ置き、小ブロックごとには、その何倍かを表す 6 bit の倍率（スケールは `sc_j`、最小値は `m_j`）だけを持ちます。重みは次の形で戻します。

```text
x ≈ (d × sc_j) × q − (dmin × m_j)    q: 0〜15、sc_j と m_j: 小ブロック j の 6 bit の値
                                     d と dmin: 大ブロックに 1 個ずつの FP16
```

[ggml-common.h の block_q4_K](https://github.com/ggml-org/llama.cpp/blob/3837bf0bc02ea5d08f8ee3585fc8c7784a81bce8/ggml/src/ggml-common.h#L323-L338) は、FP16 が 2 個（4 バイト）、6 bit の値 16 個（8 個の `sc_j` と 8 個の `m_j`、12 バイト）、4 bit の整数 256 個（128 バイト）の計 144 バイトで、重み 1 個あたり 4.5 bit です。256 個の重みで Q8_0・Q4_0 と並べると、次のようになります。帯の長さはバイト数に比例し、整数の領域は 32 個ずつの小ブロックごとに区切っています。

{{< figure src="images/quantization_layout.webp" alt="256 個の重みを持つのに使うバイトの帯が 3 本並ぶ。Q8_0 は 34 バイトの区切りが 8 つで 272 バイト、1 個 8.5 bit。Q4_0 は 18 バイトの区切りが 8 つで 144 バイト、1 個 4.5 bit。Q4_K は先頭に FP16 の d と dmin、続けて 6 bit の値の領域、残りが小ブロック 8 つ分の整数の帯で、同じ 144 バイト、1 個 4.5 bit" caption="256 個の重みのバイト配置（Q8_0・Q4_0・Q4_K）" align="center" >}}

Q4_K は Q4_0 と同じ 144 バイトのまま、小ブロックごとに最小値も持っています。スケールを FP16 から 6 bit に縮めた分で、最小値の領域を賄っている形です。

<br>

#### 層によって型を混ぜる「M」

Q4_K_M は、Q4_K を中心に層ごとに型を混ぜる組み合わせの名前です（[llama.h](https://github.com/ggml-org/llama.cpp/blob/3837bf0bc02ea5d08f8ee3585fc8c7784a81bce8/include/llama.h#L130-L134) のファイルの種類 `llama_ftype` の一覧に載っています）。末尾の S や M は、混ぜ方の違う版を表します。

llama.cpp の [llama-quant.cpp](https://github.com/ggml-org/llama.cpp/blob/3837bf0bc02ea5d08f8ee3585fc8c7784a81bce8/src/llama-quant.cpp)では、Q4_K_M を選ぶと大半の行列を Q4_K にし、一部の行列だけを 6 bit の Q6_K にします。

Q6_K にするのは、出力の層（`output.weight`）、FFN の出口の行列（`ffn_down`）の半分ほどの層、注意機構の `attn_v` の一部の層です。誤差が答えに響きやすい行列にだけビットを足す考え方です。

---

### 実際のファイルでは何 bit か

Ollama のモデルは、llama.cpp の [GGUF](https://github.com/ggml-org/ggml/blob/master/docs/gguf.md) 形式のファイルとして保存されています。GGUF は、先頭のヘッダーにメタデータ（キーと値）とテンソル（重みの配列）の一覧を置き、その後ろに重みのデータを並べた形式です。テンソルの一覧には、名前・形・型（Q4_K や F16 など）が入っています。

そのため、ヘッダーだけを読めば、4 GB のファイルでも中身を読まずに、型ごとの重みの個数とバイト数を数えられます。型ごとの 1 ブロックの要素数とバイト数が分かれば、テンソルのバイト数は「要素数 ÷ ブロックの要素数 × ブロックのバイト数」です。

```python
# lab/gguf_header.py から抜粋
# ggml の型番号 -> (名前, 1 ブロックの要素数, 1 ブロックのバイト数)
# 値は llama.cpp の ggml/src/ggml.c の type_traits と ggml-common.h の構造体の大きさ
GGML_TYPES = {
    0: ("F32", 1, 4),
    1: ("F16", 1, 2),
    2: ("Q4_0", 32, 18),
    8: ("Q8_0", 32, 34),
    12: ("Q4_K", 256, 144),
    14: ("Q6_K", 256, 210),
    # ほかの型は全体を参照
}


def tensor_bytes(t):
    _, block, nbytes = GGML_TYPES[t["type"]]
    n = 1
    for d in t["shape"]:
        n *= d
    return n, n // block * nbytes
```

ヘッダーを読む部分を含む全体（136 行、Python の標準ライブラリだけで動きます）は [lab/gguf_header.py](https://github.com/nao1215/debimate/blob/main/content/notes/generative-ai/quantization/lab/gguf_header.py) にあります。Ollama が保存している q4_K_M のファイルを渡した結果は次の通りです（[lab/output_gguf.txt](https://github.com/nao1215/debimate/blob/main/content/notes/generative-ai/quantization/lab/output_gguf.txt) の抜粋。q8_0 と fp16 の結果も同じファイルにあります）。

```text
[q4_K_M]
  file size        : 1,359,279,776 bytes
  params           : 2,031,739,904
  weight bytes     : 1,353,328,640 (5.33 bits/param)
  header + padding : 5,951,136 bytes
    Q4_K  tensors  155  params 1,485,570,048  bytes   835,633,152  (4.5000 bits/param)
    Q6_K  tensors   15  params   487,325,696  bytes   399,759,360  (6.5625 bits/param)
    F16   tensors   28  params    58,720,256  bytes   117,440,512  (16.0000 bits/param)
    F32   tensors  113  params       123,904  bytes       495,616  (32.0000 bits/param)
```

トークナイザーの語彙などが入ったヘッダー（出力の header + padding。padding はデータの開始位置を揃える詰め物で、合わせて約 6 MB）と重みのバイト数を足すと、ファイルの大きさとぴったり一致しました。

F32（32 bit の浮動小数点数）の 113 個は、層の途中で値の大きさを揃える正規化の係数などの小さなテンソルで、合計しても 0.5 MB です。params（パラメータ数）が 1.7B と合わない理由は、後の折りたたみに書きました。3 つのファイルで、型ごとのバイト数を積み上げると次の通りです。

{{< figure src="images/quantization_size.webp" alt="3 本の横棒グラフ。q4_K_M は 1.36 GB で Q4_K・Q6_K・F16 が混ざり、重み 1 個 5.33 bit。q8_0 は 2.22 GB でほぼ Q8_0、重み 1 個 8.72 bit。fp16 は 4.07 GB で全て F16、重み 1 個 16 bit" caption="qwen3:1.7b の 3 つの型のファイルの大きさと中身の型" align="center" >}}

q4_K_M は「4 bit」と呼ばれますが、重み全体では 1 個あたり 5.33 bit でした（出力の bits/param）。Q4_K の 4.5 bit に、Q6_K の層（出力の層と、28 層のうち 14 層の `ffn_down`）と、F16 のまま残った `attn_v`（注意機構の行列の 1 つ）が足されているからです。q8_0 も、F16 のまま残った `attn_v` の分だけ、8.5 bit より少し大きい 8.72 bit です。

前の節で見た規則では、`attn_v` の一部の層は Q6_K になる筈ですが、このファイルでは全て F16 のままでした。理由は分かっておらず、調べた内容は下の折りたたみに書きました。

<br>

<details>
<summary>パラメータ数が 20.3 億個になる理由と、attn_v が F16 のまま残っている点</summary>

パラメータ数は 1.7B ではなく 20.3 億個と出ました。[Qwen3-1.7B の config.json](https://huggingface.co/Qwen/Qwen3-1.7B/blob/main/config.json) は `tie_word_embeddings: true` で、入力の埋め込み（`token_embd`）と出力の層で同じ行列を共有しています。GGUF では 2 つが別のテンソルとして入っているので、語彙の数 × 埋め込みの次元の 151,936 × 2,048 個を 2 回数えています。1 回分を差し引くと、モデル名と合います。

```text
2,031,739,904 − 151,936 × 2,048 = 1,720,574,976 ≈ 17.2 億個
```

`attn_v` は、q8_0 でも F16 のままでした。2026 年 11 月 10 日時点の llama.cpp の master では、Q4_K_M なら `attn_v` の一部の層を Q6_K にします（[llama-quant.cpp の該当行](https://github.com/ggml-org/llama.cpp/blob/3837bf0bc02ea5d08f8ee3585fc8c7784a81bce8/src/llama-quant.cpp#L659-L660)）。Ollama も llama.cpp の規則を Go に移した自前の量子化のコード（[Ollama 0.22.1 の server/quantization.go](https://github.com/ollama/ollama/blob/v0.22.1/server/quantization.go#L173-L176)）を持っており、その規則も同じです。

このファイルを作った時の規則は、どちらとも違うことになります。理由はファイルからは分かりません。

どの blob（Ollama がモデルのファイルを保存する時の、ダイジェストを名前にしたファイル）が本体かの調べ方と、各モデルの digest は [lab/README.txt](https://github.com/nao1215/debimate/blob/main/content/notes/generative-ai/quantization/lab/README.txt) に記録しています。実験は全て 2026 年 11 月 10 日に Ollama 0.22.1 で行いました。

</details>

<br>

---

### 失われるもの: 重みの誤差

ここからは、丸めると何が失われるかを見ます。まず重みそのものの誤差です。block_error.py で、先ほどの `blk.0.ffn_gate.weight`（2,048 × 6,144、約 1,258 万個）全体を Q8_0 と Q4_0 に丸めて戻しました。

Q4_K と同じく最小値も持つ 4 bit の形（32 個ごとに最小値と幅を持ち、0〜15 に丸める）も自分で作りました。あわせて、Ollama の q8_0 と q4_K_M のファイルに入っている同じ行列も、llama.cpp と同じ計算で戻して並べます。

誤差は相対値（relative RMSE）で比べます。FP16 との差の[二乗平均の平方根（RMSE）](/ml/ml/regression-metrics/)を重みの二乗平均の平方根で割った値で、重みの大きさに対して何 % ずれたかを表します。8 bit と 4 bit で何倍違うかを見るのが目的です。

以下の図の左の棒がこの相対値、右の線が、戻した値と元の値の差ごとの重みの割合（Ollama のファイルの 2 つ）です。

{{< figure src="images/quantization_error.webp" alt="左は 5 本の横棒で、誤差の相対値。Q8_0 は自作も Ollama のファイルも 0.55%。4 bit は Q4_0 の自作が 8.80%、最小値付きの自作が 7.94%、Ollama の Q4_K が 7.25%。右は戻した値と元の値の差の分布で、Q8_0 は 0 の位置に細く高い山、Q4_K は ±0.005 ほどまで広がった低い山" caption="丸めた重みの誤差（相対値と、差の分布）" align="center" >}}

8 bit の誤差は重みの大きさの 0.55% で、4 bit では 7〜9% になりました。4 bit の中では、Q4_K と同じく最小値を持つ形（図の「4 bit 最小値付き」）が Q4_0 より小さく、Ollama の Q4_K が最も小さくなっています。

Q4_K は小ブロックのスケールを 6 bit に丸める分だけ不利な筈ですが、llama.cpp は候補をいくつも試し、誤差（大きい値ほど重く数える二乗誤差）が小さくなるスケールと最小値を選びます。単純に最大と最小から決めた自分の計算より良い値になったのは、そのためと考えられます。

自分で丸めた Q8_0 は、Ollama の q8_0 のファイルと 12,582,912 個の全ての重みで同じ値になりました。この行列では、上の式の通りに丸めれば llama.cpp と同じ値が作れるということです。

<br>

<details>
<summary>自作の Q8_0 が llama.cpp と全ての重みで一致するまで</summary>

最初に書いたコードでは、一致は 99.2% でした。FP16 に丸めた後のスケールの逆数で割り、ちょうど 0.5 を偶数側に丸める NumPy の `np.round` を使っていたからです。

```python
# 最初の版の丸め（要点だけ）: FP16 に丸めた d の逆数で掛け、np.round で丸めていた
d = (np.abs(b).max(axis=1) / 127).astype(np.float16).astype(np.float32)
q = np.round(b * (1 / d)[:, None])
```

llama.cpp の [quantize_row_q8_0_ref](https://github.com/ggml-org/llama.cpp/blob/3837bf0bc02ea5d08f8ee3585fc8c7784a81bce8/ggml/src/ggml-quants.c#L273-L296) と同じく、FP32 のままのスケールで割り、0.5 を 0 から遠い側に丸める C の `roundf` に合わせると、全て一致しました。抜粋の `roundf` と、`d` を FP16 にするのはファイルに書く時だけ、という注釈はこのためです。Q4_0 も [quantize_row_q4_0_ref](https://github.com/ggml-org/llama.cpp/blob/3837bf0bc02ea5d08f8ee3585fc8c7784a81bce8/ggml/src/ggml-quants.c#L110-L145) と同じく FP32 のスケールで丸めています。

</details>

<br>

---

### 失われるもの: 答えの正しさ

重みの誤差が 7% でも、答えが変わらなければ困りません。そこで、答えが 1 つに決まる問題を本記事のために 100 問作り、3 つのモデルに解かせました。算数 40 問（3 桁の足し算、4 桁の引き算、2 桁の掛け算、箱とりんごの文章題を 10 問ずつ）は乱数の seed を固定して生成し、常識 60 問（首都、元素記号、作曲者など）は手で書いています。問題文は英語です。

Qwen3 は、答える前に考えを書き出す思考モード（thinking）を持っています。思考モードのままだと、答えの前に長い考えが出力され、比べたい答えの部分が埋もれます。

そこで、Ollama の API に `"think": false` を渡して思考モードを無効にし、system のメッセージで答えだけを出すよう指示しました。[温度](/notes/generative-ai/sampling/)（出力のばらつきを決める値。0 なら常に最も確率の高いトークンを選ぶ）は 0、seed は 1 に固定しています。

```python
# lab/eval_accuracy.py から抜粋
SYSTEM = "Answer with only the final answer. Do not explain."


def chat(model, question):
    body = {
        "model": model,
        "messages": [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": question}],
        "think": False,                       # qwen3 の思考モードを無効にする
        "stream": False,
        "options": {"temperature": 0, "seed": 1, "num_predict": 128, "num_ctx": 4096},
    }
    req = urllib.request.Request(BASE + "/api/chat", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        res = json.load(r)
    return res["message"]["content"], res["message"].get("thinking", "")


def is_correct(kind, reply, answers):
    text = reply.lower().replace(",", "")
    if kind == "math":
        nums = re.findall(r"-?\d+", text)
        return bool(nums) and nums[-1] == answers[0]       # 最後に出た整数で判定する
    return any(re.search(r"(?<![a-z0-9])" + re.escape(a) + r"(?![a-z0-9])", text)
               for a in answers)
```

問題を作る [lab/make_problems.py](https://github.com/nao1215/debimate/blob/main/content/notes/generative-ai/quantization/lab/make_problems.py)（100 問の一覧を含む）と、採点して集計する [lab/eval_accuracy.py](https://github.com/nao1215/debimate/blob/main/content/notes/generative-ai/quantization/lab/eval_accuracy.py) の全体はリンク先にあります。結果は次の通りです。

{{< figure src="images/quantization_accuracy.webp" alt="3 本の横棒グラフ。正答は q4_K_M が 89 問（算数 36、常識 53）、q8_0 が 95 問（算数 36、常識 59）、fp16 が 96 問（算数 37、常識 59）" caption="100 問（算数・常識）の正答の数" align="center" >}}

q8_0 は、正答の数が FP16 と 1 問しか違わず、返答の文字列も 95 問で FP16 と完全に一致しました。q4_K_M は、返答が FP16 と一致した問題が 79 問に減り、常識の問題で 6 問を落としています。出力は [lab/output_accuracy.txt](https://github.com/nao1215/debimate/blob/main/content/notes/generative-ai/quantization/lab/output_accuracy.txt)、各問の返答と採点は [lab/accuracy.json](https://github.com/nao1215/debimate/blob/main/content/notes/generative-ai/quantization/lab/accuracy.json) にあります。

FP16 と q8_0 が正しく答え、q4_K_M だけが外した問題のうち、常識の 6 問は次の通りです（残りの 2 問は算数の文章題で、後の折りたたみに書きました）。

| 問題 | q4_K_M の答え | 正解 |
|---|---|---|
| ブラジルの首都 | São Paulo | Brasília |
| ペルーの首都 | Cusco | Lima |
| モロッコの首都 | Tangier | Rabat |
| 光合成で植物が取り込む気体 | Oxygen | Carbon dioxide |
| うるう年の日数 | 69 | 366 |
| 最小の素数 | 3 | 2 |

首都の 3 問は、どれも同じ国の別の有名な都市を答えています。サンパウロはブラジル最大の都市で、Cusco はペルーの古都です。LLM は、次に出すトークンを候補ごとの確率から選びます。重みの小さなずれが積み重なり、僅差で並んでいた候補の順位が入れ替わったと考えられます（推測です。各候補の確率までは測っていません）。

<br>

算数は 3 つとも 36〜37 問で、差が出ませんでした。1.7B のモデルは思考モードなしでは文章題が安定せず、どの文章題を外すかがモデルごとにばらばらで、量子化による差として読める大きさではありません。100 問では 1〜2 問の差は誤差の範囲で、6 問の差も、別の問題集で同じ大きさになるとは限りません。

<br>

<details>
<summary>算数の内訳</summary>

4 種類の 10 問ずつの正答は次の通りです。

| モデル | 足し算 | 引き算 | 掛け算 | 文章題 |
|---|---|---|---|---|
| q4_K_M | 10 | 10 | 9 | 7 |
| q8_0 | 10 | 10 | 9 | 7 |
| fp16 | 10 | 10 | 9 | 8 |

正答の数は同じでも、文章題で外した問題は違います。文章題は「17 個ずつりんごが入った箱が 20 箱あり、84 個売ると何個残るか」の形です。q4_K_M だけが外した問題が 2 問ある一方で、q8_0 が外した 3 問のうち 2 問（そのうち 1 問は FP16 も外した）は、q4_K_M が正しく解いています。

</details>

<br>

<details>
<summary>思考モードが本当に無効になっていたかの確認</summary>

全ての返答で、思考の出力（`message.thinking`）が空だったことを記録しています。別に [lab/check_thinking.py](https://github.com/nao1215/debimate/blob/main/content/notes/generative-ai/quantization/lab/check_thinking.py) で、1 問を `"think": false` と `"think": true` の両方で送り、思考の文の長さと生成したトークン数（`eval_count`）を比べました。

以下は q4_K_M の結果で、3 つのモデルの全体は [lab/output_check_thinking.txt](https://github.com/nao1215/debimate/blob/main/content/notes/generative-ai/quantization/lab/output_check_thinking.txt) にあります。

```text
qwen3:1.7b-q4_K_M
  quiz, think=False      thinking     0 chars | <think> in content: False | eval_count    4 | content: "São Paulo"
  quiz, think=True       thinking   404 chars | <think> in content: False | eval_count   99 | content: "Rio de Janeiro"
```

`"think": false` では思考の文は 0 文字で、答えは 4 トークンでした。`"think": true` にすると 99〜160 トークン（モデルによる）に増えます。q4_K_M は、思考させるとブラジルの首都を Rio de Janeiro と答え、思考させないと São Paulo と答えました。どちらも外れです。

[Qwen3-1.7B のモデルカード](https://huggingface.co/Qwen/Qwen3-1.7B)が勧める非思考モードの温度は 0.7 ですが、本記事では比べやすさを優先して 0 にしています。

</details>

<br>

---

### 得られるもの: 生成の速さ

最後に、小さくして何が得られるかです。ファイルとメモリが小さくなるのは、ここまでで見た通りです。生成の速さは、[ローカル LLM の速さのノート](/notes/generative-ai/local-llm-speed/)で説明している通り、1 トークンを出すたびにメモリから読むバイト数にほぼ反比例します。生成では、読んだ重み 1 個につき掛け算と足し算を 1 回ずつしかしないので、計算よりも読み出しの速さ（メモリ帯域）で決まりやすいからです。

前の節のファイルの重みのバイト数から、入力の埋め込み（1 トークンにつき 1 行しか読まない）を除くと、1 トークンあたりに読む重みは q4_K_M が約 1.18 GB、q8_0 が約 1.88 GB、FP16 が約 3.44 GB です。

生成では、過去のトークンの計算結果を取っておく KV キャッシュも 1 トークンごとに読みます。後の計測で送る 950 トークンの入力では約 0.11 GB で、3 つのモデルの読む量に同じだけ足されます。読む量の比から、FP16 に比べて q8_0 は 1.8 倍、q4_K_M は 2.8 倍速くなる計算です。

```text
q8_0   : (3.44 + 0.11) ÷ (1.88 + 0.11) ≈ 1.8
q4_K_M : (3.44 + 0.11) ÷ (1.18 + 0.11) ≈ 2.8
```

<br>

[lab/bench_speed.py](https://github.com/nao1215/debimate/blob/main/content/notes/generative-ai/quantization/lab/bench_speed.py) で、Ollama の [/api/chat](https://docs.ollama.com/api/chat) に 950 トークンのプロンプトを送り、128 トークンを生成させました。応答に入っている `eval_count`（生成したトークン数）を `eval_duration`（生成にかかったナノ秒）で割ると、生成の速さになります。

```python
# lab/bench_speed.py から抜粋
def generate(model, tag):
    # 先頭に毎回違う文字列を置き、前回のプロンプトのキャッシュを使わせない
    prompt = f"Request {tag}.\n{NOTES}\n\n{TASK}"
    return post("/api/chat", {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "think": False,
        "stream": False,
        "keep_alive": "10m",
        "options": {"temperature": 0, "seed": 1, "num_predict": 128, "num_ctx": 4096},
    })

# 速さ（トークン毎秒）は応答の値から出す
# res["eval_count"] / res["eval_duration"] * 1e9
```

3 つのモデルを 1 回ずつ順に回す周回を 9 回繰り返し、中央値を採りました。生成の中央値を FP16 との比にして、読む量から計算した比と並べると次の通りです。

{{< figure src="images/quantization_speedup.webp" alt="q8_0 と q4_K_M の 2 組の棒。白い棒は読む量からの計算で、FP16 に対して q8_0 が 1.8 倍、q4_K_M が 2.8 倍。青い棒は実測の中央値の比で、q8_0 が 2.2 倍、q4_K_M が 2.0 倍。q4_K_M だけ、実測が計算を大きく下回っている" caption="FP16 に対する生成の速さの比（読む量からの計算と実測）" align="center" >}}

q8_0 と q4_K_M は、どちらも FP16 の約 2 倍でした。q8_0 は計算の 1.8 倍をやや上回る 2.2 倍でした（9 回のぶれが大きく、計算との差は誤差の範囲です）。しかし、q4_K_M は q8_0 と同じくらいで、計算の 2.8 倍には届きませんでした。

<br>

ただし、他の作業と GPU を共有していたため、q4_K_M の 9 回の値は 21〜62 トークン毎秒に散らばり、q8_0 との差はこのぶれの中です。この結果から、q4_K_M が q8_0 より速くならないとまでは言えません。

<br>

<details>
<summary>計測の条件と、ぶれの詳細</summary>

- 計測は 2026 年 11 月 10 日、Ollama 0.22.1 で行いました。GPU は AMD Radeon 8060S（CPU と共有のメモリ）です。
- 各回の直前の負荷平均（1 分）は 4.6〜21.7 でした。同じ Ollama を他の作業も使っており、全ての回で他の作業の qwen3:4b が読み込まれていました。各回の前後に `/api/ps`（`ollama ps` と同じ情報）で、読み込まれていたモデルを記録しています。

以下は 2 周目と 5 周目の記録です（round は 0 から数えた周の番号、gen が生成の速さ、load が負荷平均、other models が他の作業のモデル）。同じ q4_K_M が 21.1 と 62.4 トークン毎秒の間で揺れています。

```text
round 1 qwen3:1.7b-q4_K_M  prompt  950 tok (cached   0)   2025.9 tok/s | gen  128 tok   21.1 tok/s | thinking 0 chars | load   14.6 | other models: qwen3:4b, qwen3:8b
round 1 qwen3:1.7b-q8_0    prompt  950 tok (cached   0)   1885.0 tok/s | gen  128 tok   35.2 tok/s | thinking 0 chars | load   12.5 | other models: qwen3:4b, qwen3:8b
round 4 qwen3:1.7b-q4_K_M  prompt  950 tok (cached   0)   3822.6 tok/s | gen  128 tok   62.4 tok/s | thinking 0 chars | load   19.2 | other models: qwen3:4b, qwen3:8b
round 4 qwen3:1.7b-q8_0    prompt  950 tok (cached   0)   1362.5 tok/s | gen  128 tok   24.0 tok/s | thinking 0 chars | load   14.1 | other models: qwen3:4b
```

- Ollama 0.22.1 は直前のプロンプトと先頭が同じ部分の計算を使い回すので、毎回先頭に違う文字列を置きました。思考モードは `"think": false` で無効にし、全ての回で思考の文が 0 文字だったことを確認しています。
- 生成の中央値は q4_K_M が 33.8、q8_0 が 36.3、FP16 が 16.5 トークン毎秒です。1 秒に読む重みの量に直すと、q4_K_M は 33.8 × 1.18 ≈ 40 GB/s、q8_0 は 36.3 × 1.88 ≈ 68 GB/s です。帯域だけで決まるなら近づく筈の 2 つの値が揃っていません。4 bit の整数を戻す計算など、帯域以外のものが効いている可能性もありますが、GPU の使用率までは測っていないので確かめられていません。
- 同じ q8_0 は、KV キャッシュのノートの実験 2 では約 540 トークンの入力で 92.0 トークン毎秒出ており、本記事の中央値の約 2.5 倍です。生成の速さが条件によって倍以上変わる環境でした。
- プロンプト処理の中央値は q4_K_M が 2,026、q8_0 が 1,505、FP16 が 1,354 トークン毎秒ですが、最大が最小の 2.5〜2.9 倍あり、順位を言える精度ではありません。プロンプト処理は計算の速さで決まりやすいので、重みを小さくしても生成ほどの差は出にくい処理です。

各回の値は [lab/output_speed.txt](https://github.com/nao1215/debimate/blob/main/content/notes/generative-ai/quantization/lab/output_speed.txt) にあります。

</details>

<br>

---

### 利点と欠点

量子化の利点は、同じモデルを小さく持てることです。ここまでの 3 つの図の値（ファイルの大きさ・生成の速さ・正答の数）を 1 枚に並べると、q8_0 は FP16 とほぼ同じ正答のまま、約半分の大きさになっています。

{{< figure src="images/quantization_tradeoff.webp" alt="3 つの棒グラフが横に並ぶ。ファイルの大きさは q4_K_M が 1.36、q8_0 が 2.22、fp16 が 4.07 GB。生成の中央値は 34、36、17 トークン毎秒で、9 回の最小から最大を示す縦線はどれも長く、q4_K_M と q8_0 の線は大きく重なる。100 問の正答は 89、95、96 問" caption="大きさ・生成の速さ（9 回の中央値、縦線は最小〜最大）・正答の数の並び" align="center" >}}

qwen3:1.7b では、q4_K_M にするとファイルが FP16 の 3 分の 1 になり、生成の中央値は q8_0 と q4_K_M のどちらも FP16 の約 2 倍でした。8 bit では、100 問の正答が FP16 と 1 問しか違いませんでした。

<br>

一方で、4 bit では答えが変わります。本記事の 100 問では、算数より、首都のような知識を問う問題で取りこぼしました。100 問は少ないので、差の大きさは目安です。誤差の出方もモデルや層によって違い、本記事で測ったのは 1.7B の 1 つのモデルと 1 つの行列だけです。

また、重みを量子化しても、文脈の長さに比例して増える KV キャッシュは小さくなりません。

例えば、q4_K_M のファイルは 1.36 GB ですが、一度に扱うトークン数の上限（Ollama の `num_ctx`）を指定せずに読み込んだ時（上限は 40,960 になりました）、`ollama ps` の SIZE は 6.2 GB でした（4,096 では 1.9 GB。[lab/README.txt](https://github.com/nao1215/debimate/blob/main/content/notes/generative-ai/quantization/lab/README.txt) に記録）。`num_ctx` の既定値と、その分だけ確保されるメモリは、[Ollama のコンテキスト長のノート](/notes/generative-ai/ollama-context-length/)で説明しています。

<br>

どの型を選ぶかは、載せたい機材のメモリと、許せる答えの変化で決まります。8 bit はファイルを約半分にしながら答えがほとんど変わらず、4 bit はさらに小さい代わりに、答えが変わる問題が出ます。

同じ 4 bit でも、Q4_K_M は一部の層にだけビットを足す組み合わせで、その分だけファイルは 4.5 bit の計算より大きくなります。

<br>

#### 関連する手法

[LoRA のノート](/notes/generative-ai/lora/)で説明した [LoRA](https://arxiv.org/abs/2106.09685)（Low-Rank Adaptation）も配るものを小さくする手法ですが、小さくする対象が違います。LoRA が小さくするのは追加学習（配られたモデルを自分の用途に合わせて学習し直すこと）で生じた重みの差分で、量子化は元のモデル（ベースモデル）の重み本体です。2 つは組み合わせられ、4 bit に量子化したベースモデルに LoRA を学習させる [QLoRA](https://arxiv.org/abs/2305.14314) という手法もあります。

1 トークンで読む量を減らす別の方法として、層の一部だけを動かす [MoE のノート](/notes/generative-ai/mixture-of-experts/)も参照してください。
