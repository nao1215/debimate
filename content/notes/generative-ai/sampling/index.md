---
title: "Sampling - temperature を指定しない時に何が使われ、0 にすると毎回同じになるのか"
date: 2026-11-10
draft: false
series: ["技術ノート", "Generative AI"]
tags: ["generative-ai", "llm", "sampling"]
weight: 40
wrapTables: true
topics: ["LLM"]
---

サンプリング（sampling）は、LLM（Large Language Model、大規模言語モデル）が次のトークンの候補ごとに出した確率から、実際に出力するトークンを 1 つ選ぶ処理です。トークンは LLM が文章を扱う単位で、日本語では 1〜数文字ほどの断片です。LLM はトークンを 1 つずつ選んで文章を作ります。temperature・top-p・top-k は、その選び方を調整するパラメータです。

以下は、手元の PC で LLM を動かす [Ollama](https://ollama.com/) 0.22.1 で、Qwen3 の 8B のモデル（`qwen3:8b`）に「日本の首都について 3 文で説明してください。」を 30 回ずつ送り、返ってきた文が何種類あったかを数えた結果です。同じ文は同じ色の点にしています。

{{< figure src="images/sampling_repeat.webp" alt="4 行の点の並び。1 行目の指定なしは 30 個の点が全て違う色で 30 種類。2 行目の temperature 0 と 3 行目の temperature 0 を 8 並列で送った場合は、30 個とも同じ色で 1 種類、2 行と 3 行も同じ色。4 行目の temperature 0.6 と seed 42 は 30 個とも同じ色で 1 種類だが、2・3 行目とは別の色" caption="同じ問いを 30 回送った時の出力の種類（qwen3:8b、Ollama 0.22.1、上の行から順に実行）" align="center" >}}

何も指定しないと 30 回とも違う文になり、temperature を 0 にすると 30 回とも同じ文になりました。指定しない時に使われた値は Ollama の文書にある既定の temperature 0.8 ではなく、モデルに付いてきた 0.6 でした。temperature を 0.6 のままシード（seed）を固定しても、30 回とも同じ文になります。

ただし、この 4 つの条件は上から順に続けて実行したもので、temperature 0 の 30 回は、直前に同じ問いを送った後に始まっています。モデルを読み込み直した直後に送ると、temperature 0 でも 1 回目だけは別の文が返りました。その理由は temperature 0 の節で確認します。

クラウドの API で使う LLM では、temperature を 0 にしても答えが揃わないことが報告されています。どちらも、確率から 1 つ選ぶまでに何が起きているかを知ると説明できます。

<br>

本記事では、手元の Ollama で既定の値・実際の確率・繰り返しの結果を確認しながら、次の疑問に答えます。

- 指定しない時、実際にはどの値が使われるのか。
- temperature は確率の何を変えるのか。
- temperature を 0 にすれば、いつでも毎回同じになるのか。
- 読み込み直した後の 1 回目だけ違う文になるのは、なぜか。
- top-p・top-k は temperature と何が違い、どの順に掛かるのか。

トークンの区切り方は[トークナイザーのノート](/notes/generative-ai/tokenizer/)で説明しています。実験の PC は、weeknotes の「[ローカル LLM（ollama）を導入したが、実用的ではない](/weeknotes/2026/09-28/)」で紹介したものです。

---

### 指定しない時に使われる値

Ollama の値は 3 段で決まります。Ollama 本体の既定の値があり、モデルに付いてくる設定（Modelfile の `PARAMETER`）がそれを上書きし、API のリクエストの `options` がさらに上書きします。モデルに付いてくる値は `ollama show --parameters` で見られます。以下は、手元の 3 つのモデルで確認した値です。

| | temperature | top_p | top_k |
|---|---|---|---|
| Ollama 本体の既定 | 0.8 | 0.9 | 40 |
| qwen3:8b | 0.6 | 0.95 | 20 |
| qwen3-coder:30b | 0.7 | 0.8 | 20 |
| gpt-oss-20b | 指定なし | 指定なし | 指定なし |

本体の既定は、[Modelfile の文書](https://docs.ollama.com/modelfile#valid-parameters-and-values)と、v0.22.1 のソースの [`DefaultOptions`](https://github.com/ollama/ollama/blob/v0.22.1/api/types.go) で同じ値でした。Ollama の公式のライブラリから取った Qwen3 の 2 つは、モデルの作者が勧める値を持っています。Hugging Face から [GGUF](https://github.com/ggml-org/ggml/blob/master/docs/gguf.md) で直接取った gpt-oss-20b は何も持っていないので、v0.22.1 では本体の既定の 0.8 で動きます。GGUF は、llama.cpp や Ollama が読み込むモデルを収めるファイル形式です。同じ Ollama でも、モデルの取り方で既定が変わるということです。

コンテキストの長さを決める `num_ctx` も同じ 3 段で上書きされ、その既定値の落とし穴は [Ollama のコンテキスト長のノート](/notes/generative-ai/ollama-context-length/)で扱っています。

[Qwen3-8B のモデルの説明](https://huggingface.co/Qwen/Qwen3-8B)は、考えてから答える思考モードと、考えずに答えるモードで、別の値を勧めています。

| Qwen3-8B の推奨 | temperature | top_p | top_k |
|---|---|---|---|
| 思考モード | 0.6 | 0.95 | 20 |
| 考えずに答えるモード | 0.7 | 0.8 | 20 |

Ollama の `qwen3:8b` が持つのは思考モードの値なので、思考を切って使う時（上の実験も `"think": false` です）は、勧められた値とずれます。思考の切り替えは[量子化のノート](/notes/generative-ai/quantization/)の実験でも使っています。

Python で LLM を扱う [Hugging Face Transformers](https://huggingface.co/docs/transformers/main/en/main_classes/text_generation) も同じ形です。`GenerationConfig` の既定は temperature 1.0・top_p 1.0・top_k 50 ですが、同時に `do_sample=False` が既定です。これは確率から選ばずに最大のトークンを選ぶ設定なので、既定のままでは temperature などの値は使われません。モデルに `generation_config.json` があれば、その値が上書きします。

---

### ロジットから確率へ

モデルは、語彙にある全トークンについて、次に来るもっともらしさを表す実数を出します。この値をロジット（logit）と呼びます。ロジットは確率ではないので、[softmax 関数](/ml/ml/loss-functions/)で合計 1 の確率に変換します。temperature を T とすると、トークン i の確率は次の式です。

```text
p_i = exp(z_i / T) / (全トークン j についての exp(z_j / T) の合計)
```

`z_i` がトークン i のロジットです。T = 1 ならモデルが出した確率をそのまま使い、1 より小さいとロジットの差が広がって上位に確率が集まり、1 より大きいと差が縮んで下位にも確率が回ります。どちらでもトークンの順位は変わりません。

実際のモデルの確率を見ます。Ollama の API は、選ばれたトークンと、上位にある候補の対数確率（logprobs）を返せます。以下のスクリプトで、`qwen3:8b` に「今日の天気は」の続きを 1 トークンだけ出させました。

```python
"""qwen3:8b に「今日の天気は」の続きを 1 トークンだけ出させ、上位 10 個の候補の確率を取る。

temperature を変えて、返る確率が変わるか（temperature を掛けた後の値か）も確かめる。
使い方: python3 nexttoken.py > output_nexttoken.txt
前提: Ollama 0.22.1 が localhost:11434 で動き、qwen3:8b を pull 済み。
"""
import json
import math
import urllib.request

URL = "http://localhost:11434/api/generate"


def top(temperature):
    body = {"model": "qwen3:8b", "prompt": "今日の天気は", "raw": True, "stream": False,
            "options": {"temperature": temperature, "num_predict": 1},
            "logprobs": True, "top_logprobs": 10}
    req = urllib.request.Request(URL, json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.load(r)["logprobs"][0]["top_logprobs"]


for t in [0.5, 1.0, 1.5]:
    print(f"== temperature {t}")
    for c in top(t):
        tok = bytes(c["bytes"]).decode("utf-8", errors="replace")
        print(f"  {tok!r:12} {math.exp(c['logprob']):.4f}")
```

返ってきた対数確率は、temperature を 0.5・1.0・1.5 のどれにしても同じでした。出力の全体は [lab/](https://github.com/nao1215/debimate/tree/main/content/notes/generative-ai/sampling/lab) にあります。Ollama が返す logprobs は、temperature を掛ける前のモデルの確率です。そこで、上位 10 個だけを取り出し、その 10 個の中で合計 1 になるように temperature を掛けて計算し直したのが次の図の左です。後の節で見るように、Ollama も上位 k 個に絞ってから同じ計算をします。

{{< figure src="images/sampling_nexttoken.webp" alt="左は qwen3:8b が「今日の天気は」の次に出した上位 10 個のトークンについて、10 個の中で計算し直した確率を temperature 0.5、1.0、1.5 で並べた棒グラフ。1 位の晴は temperature 1.0 で 0.40、0.5 では 0.67 に上がり、1.5 では 0.29 に下がる。右は同じ確率の上位からの累積で、0.95 の点線を超えるまでに残る候補は temperature 0.5 で 4 個、1.0 で 8 個、1.5 で 9 個" caption="qwen3:8b の次のトークンの確率（上位 10 個の中で計算し直した値）" align="center" >}}

1 位の「晴」は、temperature 1.0 で 0.40、0.5 では 0.67 まで上がり、1.5 では 0.29 まで下がります。2 位が「、」なのは、「今日の天気は、」と読点を打つ続け方もあるからです。3 位の「文字の途中」は、1 つの文字を表すバイト列の前半だけのトークンです。日本語の 1 文字が 2 つのトークンに分かれることがあるのは[トークナイザーのノート](/notes/generative-ai/tokenizer/)の話で、サンプリングはこうした断片も他の候補と同じように選びます。

右の図は、上位から確率を足していった累積です。top-p は、この累積が p に届くまでの候補だけを残す方法で、後の節で詳しく見ます。0.95 で切ると、temperature 0.5 では 4 個ほど、1.0 では 8 個が残ります。0.5 の 3 個目までの累積は 0.949 で、0.95 とほぼ同じなので、境目は 3 個と 4 個の間です。

temperature を下げると上位に確率が集まるので、同じ top-p でも残る候補が減ります。モデルの出力は 10 個の外にも続いていて、語彙の十数万個のトークンのうち、上位 10 個の元の確率の合計は 0.80 でした。

---

### temperature を 0 にした場合

T を 0 に近づけると、最大のロジットを持つトークンの確率が 1 に近づきます。T = 0 はそのままでは 0 で割ることになるので、多くの実装は、確率から選ぶ代わりに最大のトークンを選びます。この選び方を greedy decoding と呼びます。Ollama も、temperature が 0 なら greedy decoding に切り替えることを、後の節でソースから確認します。

冒頭の実験は、確率から選ぶ既定の動きと greedy decoding を並べたものです。サーバーが複数のリクエストをまとめて計算すると結果が揺れることがあるので、8 並列で送る条件も入れました。使ったスクリプトは次の通りで、同じ問いを 30 回送り、返ってきた文の種類を数えます。

```python
"""同じ問いを Ollama に何度も投げ、出力が何種類になるかを数える。

使い方: python3 repeat.py > output_repeat.txt
前提: Ollama 0.22.1 が localhost:11434 で動き、qwen3:8b を pull 済み。
"""
import collections
import concurrent.futures
import hashlib
import json
import urllib.request

URL = "http://localhost:11434/api/generate"
MODEL = "qwen3:8b"
PROMPT = "日本の首都について 3 文で説明してください。"
N = 30


def ask(options):
    body = {"model": MODEL, "prompt": PROMPT, "stream": False, "think": False,
            "options": {"num_predict": 120, **options}}
    req = urllib.request.Request(URL, json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.load(r)["response"]


def run(name, options, parallel=1):
    if parallel == 1:
        outs = [ask(options) for _ in range(N)]
    else:
        with concurrent.futures.ThreadPoolExecutor(parallel) as ex:
            outs = list(ex.map(lambda _: ask(options), range(N)))
    c = collections.Counter(outs)
    print(f"== {name}: {N} 回 → {len(c)} 種類")
    for i, (text, k) in enumerate(c.most_common()):
        h = hashlib.sha1(text.encode()).hexdigest()[:8]
        print(f"  {k:3d} 回 [{h}] {text[:60].replace(chr(10), ' ')}")
    print(flush=True)


if __name__ == "__main__":
  run("指定なし（モデルの既定 temperature 0.6, top_k 20, top_p 0.95）", {})
  run("temperature 0、1 つずつ", {"temperature": 0})
  run("temperature 0、8 並列", {"temperature": 0}, parallel=8)
  run("temperature 0.6、seed 42、1 つずつ", {"temperature": 0.6, "seed": 42})
```

出力の抜粋です。指定なしの 30 種類は、どれも「日本の首都は東京」で始まり、「東京です」「東京都です」「東京である」のように数トークン目から分かれていきます。

```text
== 指定なし（モデルの既定 temperature 0.6, top_k 20, top_p 0.95）: 30 回 → 30 種類
    1 回 [49e4a3d4] 日本の首都は東京です。東京は日本の最大の都市であり、
    1 回 [c0fc4226] 日本の首都は東京都です。東京都は日本の政治、経済、
    1 回 [1de89900] 日本の首都は東京である。東京は日本の最大の都市であり、
（27 行略）

== temperature 0、1 つずつ: 30 回 → 1 種類
   30 回 [bbdc1719] 日本の首都は東京都です。東京都は日本の政治、経済、文化の

== temperature 0、8 並列: 30 回 → 1 種類
   30 回 [bbdc1719] 日本の首都は東京都です。東京都は日本の政治、経済、文化の
```

8 並列で送っても同じ文になったのは、手元の Ollama がモデルを並列数 1 で読み込んでいて、リクエストを 1 つずつ順に処理したからです。並列数は、Ollama の起動のログの `Parallel:1` で確認しました。

<br>

#### 1 回目だけ違う文になる

この実験の前には、同じ問いを指定なしで 30 回送っていました。モデルを読み込み直して temperature 0 で送り直すと、1 回目だけ別の文が返り、2 回目からは上の `bbdc1719` に揃いました。読み込み直しを 3 回繰り返しても、`num_ctx` を変えても同じです。そこで、問いを A・A・A・B・A・A の順に送り、応答に含まれる問いの処理の時間（`prompt_eval_duration`）と並べました。

{{< figure src="images/sampling_cache.webp" alt="6 本の棒グラフ。A の 1 回目は読み込み直後で 181 ms、出力 1。A の 2・3 回目は 46 ms と 37 ms で出力 2。次の B（別の問い）は 190 ms。B の後の A の 4 回目は 159 ms で出力 1 に戻り、A の 5 回目は 54 ms で出力 2" caption="temperature 0 で A・A・A・B・A・A の順に送った時の出力と問いの処理の時間（lab/cache.py）" align="center" >}}

A のうち、問いの処理に 159〜181 ms 掛かった回は出力 1（`832a7755`）になり、37〜54 ms で済んだ回は、図 1 の temperature 0 と同じ出力 2（`bbdc1719`）になりました。

Ollama は直前に処理した問いの計算結果をプロンプトのキャッシュとして残しておき、同じ問いが来るとその部分を使い回します。この仕組みと、使い回せたかを処理の時間で見分ける方法は、[KV Cache のノートの実験 3](/notes/generative-ai/kv-cache/#実験-3-同じプレフィックスの再利用) で詳しく扱っています。v0.22.1 の [runner/ollamarunner/cache.go](https://github.com/ollama/ollama/blob/v0.22.1/runner/ollamarunner/cache.go) を読むと、問いが丸ごと一致した時は末尾の 1 トークンだけを計算し直します。多くのトークンをまとめて計算した回とは計算の形が変わり、ロジットがわずかに変わると考えられます。その差で上位の 2 つが入れ替わる所があれば、以降の文も変わります。

同じ設定で回し直しても結果が一致しなかったことは、[Tool Calling](/notes/generative-ai/tool-calling/) と[構造化出力](/notes/generative-ai/structured-output/)のノートの実験でも起きています。Tool Calling は temperature 0.6 と seed を使い、他の実験と同時に流していたので条件は本記事と違いますが、この使い回しも原因の候補の 1 つです。temperature 0 で揃えたい時は、1 回目の結果を捨てるか、比べる全ての回で条件をそろえます。毎回モデルを読み込み直せば、全ての回が問いを最初から計算します。別の問いを挟む方法では、2 つの問いに共通する先頭の部分は使い回されるので、問いの大部分を計算し直す形になります。

<br>

#### 0 でも揃わない場合

API の LLM のように、サーバー側で他の人のリクエストとまとめて計算する環境では、temperature 0 でも揃わないことがあります。まとめる数が変わると浮動小数点の足し算の順序が変わり、ロジットがわずかに変わるからです。上位 2 個のロジットが僅差なら、その差で選ばれるトークンが入れ替わり、以降の文も変わります。

AI の研究企業の Thinking Machines Lab は「[Defeating Nondeterminism in LLM Inference](https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/)」で、temperature 0 で同じ問いを 1,000 回送ると 80 種類の答えが返ったと報告し、まとめる数に左右されない計算の方法を示しています。手元の 1 回目だけ違う現象も、計算の形が変わると答えが変わるという点で同じ種類の問題です。

[シード（seed）](/notes/security/random-number/)の固定も同じで、同じ乱数の列は再現できますが、計算の順序によるロジットの差は防げません。

<br>

#### greedy decoding を避けるモデル

毎回同じになるからといって、temperature 0 が良い答えになるとは限りません。[Qwen3-8B の説明](https://huggingface.co/Qwen/Qwen3-8B)は、思考モードについて "DO NOT use greedy decoding, as it can lead to performance degradation and endless repetitions." と書いています。greedy decoding を使うと性能が落ちたり、同じ言い回しを延々と繰り返したりすることがある、という警告です。

思考モードで再現性が欲しい時は、勧められた temperature のまま seed を固定する方法があり、手元では冒頭の 4 行目のように揃いました。seed を固定した時に、使い回しの有無で 1 回目が変わるかは確認していません。

---

### top-p と top-k、掛ける順序

temperature が全候補の確率を一律に変えるのに対して、top-p と top-k は確率の低い候補を切り捨てます。

top-p は、確率の大きい順に並べて、累積が p に届くまでの候補だけを残す方法です。2019 年の [Holtzman 氏らの論文](https://arxiv.org/abs/1904.09751)で nucleus sampling として提案されました。残す数は状況で変わり、「日本の首都は東」の次の「京」のように次のトークンがほぼ決まっている所では 1 個、選択肢が多い所では多く残ります。top-k は上位 k 個を残す方法で、k は状況に関係なく固定です。

どちらを先に掛けるかは実装で違います。v0.22.1 の Ollama の [sample/samplers.go](https://github.com/ollama/ollama/blob/v0.22.1/sample/samplers.go) は、temperature が 0 なら greedy decoding を返します。それ以外は、top-k で上位 k 個を残し、temperature で割り、残った k 個の中で softmax を計算し直してから、top-p で切り、最後に min-p で切ります。min-p は、1 位の確率に対する割合で下限を決めて切る方法です。

{{< figure src="images/sampling_order.webp" alt="左から右へ 7 つの箱が矢印でつながる。全語彙のロジット、top-k で上位 k 個を残す、temperature でロジットを T で割る、softmax で残った k 個を合計 1 にする、top-p で累積 p まで残す、min-p で 1 位の割合で切る、乱数で 1 つ選ぶ。上に赤い破線の矢印があり、temperature が 0 なら途中を飛ばして最大の 1 つを選ぶ" caption="Ollama v0.22.1 が次のトークンを選ぶ順（sample/samplers.go）" align="center" >}}

Ollama には、モデルを llama.cpp を通して動かす経路と、Ollama 自身のエンジンで動かす経路があり、上のソースは後者のものです。手元の `qwen3:8b` は、起動のログに `--ollama-engine` とあったので後者で動き、この順で選ばれています。

`qwen3:8b` の既定の top_k 20・top_p 0.95 に当てはめると、まず 20 個に絞り、その 20 個の中で計算し直した確率の累積で top-p が切ります。先ほどの右の図は、これを 10 個で試したものです。temperature が低いほど上位に確率が集まるので、top-p で残る数は減ります。

<br>

#### 1 万回選んで数える

切り捨ての効き方を回数で見るため、7 個のトークンに説明用のロジットを与え、temperature と top-p の組み合わせごとに 1 万回選んで数えました。ロジットは実在のモデルの出力ではありません。乱数は [NumPy](https://numpy.org/doc/stable/reference/random/generator.html) で作り、seed は 1 です。

```python
"""temperature と top-p で次のトークンの選ばれ方がどう変わるかを数える。

ロジットは説明用に決めた値で、実在のモデルの出力ではない。
    python3 lab/sampling.py
"""
import numpy as np

TOKENS = ["晴れ", "雨", "曇り", "雪", "最高", "微妙", "カレー"]
LOGITS = np.array([3.0, 2.2, 2.0, 0.8, 0.5, 0.0, -2.0])


def probs(logits, temperature):
    z = logits / temperature
    z = z - z.max()  # exp の桁あふれを防ぐ
    p = np.exp(z)
    return p / p.sum()


def top_p_filter(p, top_p):
    order = np.argsort(p)[::-1]
    keep = np.cumsum(p[order]) - p[order] < top_p  # 累積が top_p に届くまで残す
    q = np.zeros_like(p)
    q[order[keep]] = p[order[keep]]
    return q / q.sum()


def main():
    rng = np.random.default_rng(1)
    N = 10_000
    for label, t, top_p in [("T=0.5", 0.5, 1.0), ("T=1.0", 1.0, 1.0),
                            ("T=1.5", 1.5, 1.0), ("T=1.0, top_p=0.9", 1.0, 0.9)]:
        p = top_p_filter(probs(LOGITS, t), top_p)
        counts = np.bincount(rng.choice(len(TOKENS), size=N, p=p), minlength=len(TOKENS))
        row = "  ".join(f"{tok}:{c:5d}" for tok, c in zip(TOKENS, counts))
        print(f"{label:<17} {row}")
    print("T→0 (greedy)     ", TOKENS[int(np.argmax(LOGITS))], "だけが選ばれる")


if __name__ == "__main__":
    main()
```

{{< figure src="images/sampling_counts.webp" alt="4 本の横の帯グラフ。T=0.5 は晴れが 7,339 回で、カレーは 0 回。T=1.0 は晴れ 4,935 回、カレー 31 回。T=1.5 は晴れ 3,674 回、カレー 126 回。T=1.0 で top_p=0.9 は晴れ 5,200 回、雨 2,338 回、曇り 1,907 回、雪で終わり、最高・微妙・カレーは 0 回" caption="説明用のロジットで 1 万回選んだ回数（lab/sampling.py の出力）" align="center" >}}

temperature 1.5 では、文脈に合わない「カレー」も 126 回選ばれました。1 万回のうちの 126 回でも、数百トークンの文章を生成すれば、どこかで外れた候補を引く回数は増えます。top-p 0.9 を足すと「最高」「微妙」「カレー」が 0 回になり、その分が残った 4 個に配られています。temperature で裾野を持ち上げても、top-p か top-k で切れば外れた候補は選ばれません。

---

### temperature を決める前に確かめること

まず、今どの値で動いているかを確認します。Ollama なら `ollama show --parameters`、Transformers ならモデルの `generation_config.json` です。冒頭の実験の `qwen3:8b` のように、文書の既定の値とは別の値で動いていることがあります。

毎回同じ答えが欲しいなら、temperature 0 か seed の固定で揃うかを、実際に使う環境で数十回送って確認します。手元の並列数 1 の Ollama でも、問いの計算を使い回すかどうかで 1 回目だけ違う文になりました。比べる時は、1 回目を捨てるか、全ての回を同じ条件にそろえます。決まった形式の出力が欲しいだけなら、[構造化出力](/notes/generative-ai/structured-output/)で形式を守らせる方が確実です。

<br>

次に、モデルの作者が勧める値を読みます。Qwen3 のように greedy decoding を避けるよう書いているモデルでは、temperature 0 で品質が下がることがあります。思考モードの有無のように、使い方で勧める値が変わるモデルもあります。

最後に、値を動かす時は 1 つずつにします。Ollama は top-k → temperature → top-p の順に掛けるので、temperature を変えると top-p で残る数も変わり、2 つを同時に動かすとどちらの影響か分からなくなります。temperature を上げてばらつかせたい時は、top-p か top-k で裾野を切っておくと、外れた候補を引かずに済みます。

実験のスクリプトと出力は [lab/](https://github.com/nao1215/debimate/tree/main/content/notes/generative-ai/sampling/lab) にあります。
