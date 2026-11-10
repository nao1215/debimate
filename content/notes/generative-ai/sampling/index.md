---
title: "Sampling - temperature と top-p で次のトークンを選ぶ仕組み"
date: 2026-11-10
draft: false
series: ["技術ノート", "Generative AI"]
tags: ["generative-ai", "llm", "sampling"]
weight: 40
wrapTables: true
topics: ["LLM"]
---

サンプリング（sampling）は、LLM（Large Language Model、大規模言語モデル）が次のトークンの候補ごとに出した確率から、実際に出力するトークンを 1 つ選ぶ処理です。temperature と top-p は、その選び方を調整するパラメータです。

LLM の API や、手元の PC で LLM を動かす [Ollama](https://ollama.com/) には、たいてい temperature の設定があります。「temperature を上げると賢くなる」「0 にすれば毎回同じ答えになる」と受け取られがちですが、どちらも正確ではありません。temperature はモデルの知識や能力を増やす設定ではなく、次のトークンを選ぶ確率の分布を変える設定です。

以下は、「今日の天気は」の次に来るトークンの確率を temperature ごとに並べた図（左）と、top-p で候補を絞る様子（右）です。確率は説明用に決めた値から計算しており、実在のモデルの出力ではありません。生成コードは [figures.py](https://github.com/nao1215/debimate/blob/main/content/notes/generative-ai/sampling/figures.py) です。

{{< figure src="images/sampling_concept.svg" alt="左は 7 個のトークンの確率を temperature 0.5、1.0、1.5 で並べた棒グラフ。0.5 では晴れが 0.74 と突出し、1.5 では 0.37 まで下がって他の候補が増える。右は temperature 1.0 の確率を大きい順に並べ、累積の折れ線が 0.9 を超えるまでの晴れ・雨・曇り・雪を濃い色、残りの最高・微妙・カレーを薄い色で示す" caption="temperature による確率の変化（左）と、top-p で残る候補（右）" align="center" >}}

左の図では、temperature が低いほど上位の「晴れ」に確率が集まり、高いほど下位の候補にも確率が回ります。右の図では、上位から確率を足していき、0.9 に届くまでの 4 個だけを候補に残しています。

<br>

本記事では、temperature と top-p による確率の変化を説明し、Python で 1 万回サンプリングして確かめます。扱う疑問は以下の通りです。

- temperature は確率の何を変えるのか。
- temperature を 0 にすると、何が起きるのか。毎回同じ答えになるのか。
- top-p は temperature と何が違うのか。
- 実際に設定する時は、どちらをどう触れば良いのか。

モデルが確率を計算する内部（注意機構など）は説明しません。トークンの区切り方は[トークナイザーのノート](/notes/generative-ai/tokenizer/)を参照してください。

---

### ロジットから確率へ

モデルは、語彙にある全トークンについて、次に来るもっともらしさを表す実数を出します。この値をロジット（logit）と呼びます。ロジットは確率ではないので、softmax 関数で合計 1 の確率に変換します。以下では T（temperature）を 0 より大きい値とします。

```text
p_i = exp(z_i / T) / (全トークン j についての exp(z_j / T) の合計)
```

`z_i` がトークン i のロジットです。T = 1 なら、モデルが出した確率をそのまま使います。T で割ることで、ロジットの差が広がったり縮んだりします。

- 0 < T < 1：差が広がり、上位のトークンに確率が集まる
- T > 1：差が縮み、下位のトークンにも確率が回る

どちらの場合も、トークンの順位は変わりません。temperature を上げても、モデルが知らない言葉を思いつくわけではなく、元々低い確率だった候補が選ばれやすくなるだけです。冒頭の図の「カレー」のように、文脈に合わない候補の確率も上がります。

---

### temperature を 0 にした場合

T を 0 に近づけると、最大のロジットを持つトークンが 1 個なら、そのトークンの確率が 1 に近づきます。T = 0 はそのままでは 0 で割ることになるので、多くの実装では、確率から選ぶ代わりに最大のトークンを選ぶ処理（greedy decoding）を使います。

指定の方法は実装によって違います。例えば、Python で LLM を扱うライブラリの [Hugging Face Transformers](https://huggingface.co/docs/transformers/generation_strategies) では、temperature を 0 にするのではなく、`do_sample=False` で greedy decoding を選びます。

greedy decoding は乱数を使いませんが、毎回同じ出力になるとは限りません。サーバー側で他のリクエストとまとめて計算すると、浮動小数点の足し算の順序が変わり、ロジットがわずかに変わることがあります。

上位 2 個のロジットが僅差なら、その差で選ばれるトークンが入れ替わり、以降の文章も変わります。この現象は、AI の研究企業である Thinking Machines Lab の「[Defeating Nondeterminism in LLM Inference](https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/)」で詳しく調べられています。

乱数を使うサンプリングでは、seed（乱数の種）を固定すると同じ乱数の列を再現できます。しかし、計算の順序によるロジットの差は、seed では防げません。

---

### top-p：候補の数を確率で決める

top-p は、確率の大きい順にトークンを並べ、累積の確率が p に届くまでの候補だけを残す方法です。[Holtzman 氏らの論文（2019）](https://arxiv.org/abs/1904.09751)で nucleus sampling として提案されました。残した候補の確率を合計 1 に正規化し直してから選びます。

temperature は全候補の確率を一律に変えますが、top-p は確率の低い候補を切り捨てます。冒頭の図の右側では、累積が 0.9 に届くまでの「晴れ」「雨」「曇り」「雪」が残り、「最高」「微妙」「カレー」は選ばれなくなります。

top-p の利点は、残る候補の数が状況で変わることです。次のトークンがほぼ決まっている箇所（「東京」の次の「都」など）では 1 個しか残らず、選択肢が多い箇所では多く残ります。似た方法に、上位 k 個を残す top-k がありますが、k は状況に関係なく固定です。

---

### 1 万回サンプリングして数える

ここまでの説明を実際に選ばれた回数で確かめます。以下のコードは、7 個のトークンに説明用のロジットを与え、temperature と top-p の組み合わせごとに 1 万回選んで数えます。乱数は数値計算ライブラリの [NumPy](https://numpy.org/doc/stable/reference/random/generator.html) で作り、seed は 1 に固定しています。

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

実行結果は以下の通りです。

```text
T=0.5             晴れ: 7339  雨: 1464  曇り: 1046  雪:   86  最高:   49  微妙:   16  カレー:    0
T=1.0             晴れ: 4935  雨: 2103  曇り: 1770  雪:  524  最高:  419  微妙:  218  カレー:   31
T=1.5             晴れ: 3674  雨: 2255  曇り: 1879  雪:  882  最高:  712  微妙:  472  カレー:  126
T=1.0, top_p=0.9  晴れ: 5200  雨: 2338  曇り: 1907  雪:  555  最高:    0  微妙:    0  カレー:    0
T→0 (greedy)      晴れ だけが選ばれる
```

temperature 0.5 では「晴れ」が 7,339 回と 7 割を超え、「カレー」は 1 回も選ばれません。temperature 1.5 では「晴れ」が 3,674 回まで減り、「カレー」も 126 回選ばれています。1 万回のうち 126 回でも、長い文章を生成すれば、どこかで文脈に合わないトークンを引く回数は増えます。

「T=1.0, top_p=0.9」では、「最高」「微妙」「カレー」が 0 回になり、残った 4 個の回数がその分だけ増えています。実験のスクリプトと出力は [lab/](https://github.com/nao1215/debimate/tree/main/content/notes/generative-ai/sampling/lab) にあります。

---

### 設定する時の考え方

temperature と top-p は、どちらも出力のばらつきを調整します。両方を同時に大きく動かすと、どちらの影響で出力が変わったのか分からなくなるので、片方を固定して片方だけを動かします。

決まった形式の出力（JSON、コード、分類のラベル）が欲しい時は、temperature を低くします。形式そのものを守らせたいなら、[構造化出力](/notes/generative-ai/structured-output/)を使います。文章の言い回しに幅が欲しい時は、temperature を 1 前後にし、top-p で確率の低い候補を切ります。

各パラメータの既定値は、API やライブラリで違います。以下は、2026 年 11 月時点の公式ドキュメントと Transformers のソースコード（v5.22.2 と main ブランチ）を元にした比較です。

| | temperature | top_p | top_k | 既定の選び方 |
|---|---|---|---|---|
| [Transformers の GenerationConfig](https://huggingface.co/docs/transformers/main/en/main_classes/text_generation) | 1.0 | 1.0 | 50 | greedy（`do_sample=False`） |
| [Ollama の Modelfile](https://docs.ollama.com/modelfile#valid-parameters-and-values) | 0.8 | 0.9 | 40 | サンプリング |

どちらの値も、モデルに付属する設定（Transformers は `generation_config.json`、Ollama はモデルの Modelfile）があれば、その値で上書きされます。同じ temperature を指定しても、top_p や top_k の既定値が違えば出力のばらつきも変わります。値を決める前に、使っている API の文書を確認してください。
