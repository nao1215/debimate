---
title: "KV Cache - 読んだトークンの計算結果を取っておく仕組みとコンテキスト長"
date: 2026-11-10
draft: false
series: ["技術ノート", "Generative AI"]
tags: ["generative-ai", "llm", "kv-cache", "ollama"]
weight: 30
wrapTables: true
topics: ["LLM"]
---

KV キャッシュ（key-value cache）は、LLM（Large Language Model、大規模言語モデル）が文章を生成する時に、既に読んだトークンの計算結果をメモリに取っておく仕組みです。トークンは、LLM が文章を読み書きする単位で、単語や単語の一部にあたります（[トークナイザーのノート](../tokenizer/)）。

取っておく計算結果は、各トークンから作る K と V という 2 種類のベクトルで、名前の KV はここから来ています（K と V の中身は次の節で説明します）。

LLM は 1 トークンずつ文章を生成し、[次のトークンを選ぶ](../sampling/)たびに、それまでの全てのトークンの K と V を使います。KV キャッシュがあれば、過去のトークンの K と V を毎回計算し直さずに済みます。その代わりに、取っておく量はトークンの数に比例して増えます。以下は、KV キャッシュの枠が前から埋まっていく様子を描いた図です。

{{< figure src="images/kv-cache_concept.webp" alt="横に並んだ 22 個の縦長の枠が KV キャッシュを表す。各枠は上半分が K、下半分が V で、奥に 2 枚重なり、層ごとに K と V を持つことを示す。左の 9 個は青で「プロンプト（まとめて計算）」、続く 3 個は黄土で「生成」、黒枠の 1 個が次のトークンで、そこから左端へ曲線の矢印が伸び「次のトークンは、埋まった枠の K と V を全部読む」と書かれている。右の 9 個は点線の空き枠。下の括弧は全体を囲み「枠の数 = コンテキスト長（Ollama では num_ctx）」" caption="前から埋まり、次のトークンが埋まった枠を全部読む KV キャッシュ" align="center" >}}

1 つの枠が、1 トークン分の K と V です。最初に渡した文章（プロンプト）の分はまとめて計算して埋め、その後は生成した 1 トークンごとに 1 枠ずつ埋めます。モデルが一度に扱えるトークン数の上限をコンテキスト長（context length）と呼びます。本記事の実験で使う [Ollama](https://ollama.com/)（手元の PC で LLM を動かすソフトウェア）では、コンテキスト長を `num_ctx` というオプションで指定し、図のように枠をその数だけ最初に用意します（使った分だけ確保する実装もあり、「KV キャッシュを小さくする方法」の節で触れます）。

<br>

本記事では、KV キャッシュで生成が速くなる理由と、KV キャッシュが何にどれだけメモリを使うかを説明します。Ollama でコンテキスト長と入力の長さを変えて測り、次の疑問に答えます。

- KV キャッシュが無いと、生成の何が遅くなるのか。
- KV キャッシュの大きさは、モデルのどの設定から計算できるのか。
- コンテキスト長を大きくすると、メモリはどれだけ増えるのか。
- 入力が長いと、最初のトークンまでの時間と生成の速さはどう変わるのか。
- 同じ前置きを送り直した時に、計算はどれだけ省けるのか。

num_ctx を指定しない時の既定値や、num_ctx を超えた入力の扱いなど、Ollama の設定の話は [Ollama の num_ctx のノート](../ollama-context-length/)に分けています。注意機構の計算の細部（Softmax の数値の扱いや位置の埋め込み）は説明しません。

---

### 前提: 注意機構の Q・K・V

LLM は、テキストをトークンの列として読み、次に来るトークンを予測するモデルです。本記事で扱う [Qwen3](https://github.com/QwenLM/Qwen3) は、[Transformer](https://arxiv.org/abs/1706.03762) というネットワークの構造を使い、同じ形の層（Qwen3-1.7B では 28 層）を積み重ねています。

各層は、学習で決まった大量の数値を持っており、これを重み（weight）と呼びます。モデルのファイルの大部分は、この重みです。

各層の中心にある注意機構（attention）は、トークンごとに 3 種類のベクトルを作ります。Q（query）は「自分はどんな情報を探しているか」、K（key）は「自分はどんな情報を持っているか」、V（value）は「実際に渡す中身」を表します。

あるトークンの Q と、自分を含むそれまでの全トークンの K を比べて（[内積](/ml/math/vector-matrix-ops/)を取って）配分の比率を決め、その比率で V を混ぜたものが、その層の注意機構の出力になります。V は比べる相手ではなく、比率を掛けて足し合わせる中身です。以下は、「今日は雨なので傘を」まで読んだ時の、最後のトークン「を」の計算を描いた図です。

{{< figure src="images/kv-cache_qkv.webp" alt="横に 6 つのトークン（今日、は、雨、なので、傘、を）が並び、それぞれの下に K の枠と V の枠がある。右に今のトークン「を」の Q の枠があり、黄土の線で 6 つの K 全てにつながる。左に「① Q と各 K の内積」「② 比率（合計 1）」「③ 比率で V を混ぜる」と書かれ、K の下に 0.05、0.03、0.30、0.07、0.45、0.10 の比率が並ぶ。6 つの V から線が集まり「「を」の注意機構の出力」の枠になる。下に、比率は説明用の例で、K と V は後のトークンでも同じ値を使うのでキャッシュに取っておける、と書かれている" caption="今のトークンの Q と各トークンの K から比率を求め、その比率で V を混ぜる" align="center" >}}

Q は、そのトークン自身の出力を作る時に 1 度使えば済みます。K と V は、比べられる側・混ぜられる側として、後のトークンの計算でも繰り返し使われます。

Q・K・V は層ごとに作るので、K と V は層の数だけあります。注意機構は、この Q・K・V の組を並列にいくつも持ち、その 1 組をヘッド（head）と呼びます。Q のヘッドの数と、K・V のヘッドの数は違うことがあります（後のキャッシュの大きさの節で説明します）。

文章の生成では、後ろのトークンが前のトークンを参照することはあっても、前のトークンが後ろを参照することはありません（causal attention）。各層で、あるトークンの出力はそれ以前のトークンだけから作られます。層の出力は次の層の入力になり、次の層の K と V はその出力から作られます。そのため、一度計算したトークンの K と V は、後ろにトークンが増えても変わりません。KV キャッシュは、この性質を使っています。

---

### KV キャッシュで速くなる理由

生成は、次の 1 トークンを選び、それを入力の末尾に足して、また次の 1 トークンを選ぶ、の繰り返しです。本記事では、この 1 回をステップと呼びます。以下は、1 トークンずつ順に読む場合を模式にして、5 トークン目までの各ステップで K・V を計算するトークンを塗った図です。

{{< figure src="images/kv-cache_steps.webp" alt="左右 2 つの階段状の図。縦はステップ 1〜5、横はトークン 1〜5。左のキャッシュ無しは、ステップ t で 1〜t の全てのトークンが黄土（K・V を計算する）で、計 1+2+3+4+5=15 回。右のキャッシュ有りは、各ステップで最後の 1 トークンだけが黄土で、それより前は青（キャッシュから読む）。計 1+1+1+1+1=5 回" caption="各ステップで K・V を計算するトークン（キャッシュ無しと有り）" align="center" >}}

KV キャッシュが無い場合（図の左）、ステップごとに、それまでの全てのトークンの K と V を全ての層で計算し直します。n トークン目まで進むと、K と V の計算は合わせて `1 + 2 + … + n` 回で、n の 2 乗に比例して増えます。

KV キャッシュがあれば（図の右）、新しく計算するのは、新しいトークンの Q・K・V だけです。K と V はキャッシュの末尾に足し、Q は自分を含むそれまでの K と比べて、その比率で V を混ぜるために使います。K・V を計算する回数は n に比例するまで減ります（Q と過去の K を比べる回数は、ステップごとに増えたままです）。

ただし、過去の K・V をメモリから読む量（図の右の青い枠）は、トークンが増えるほど増えます。この読む量が、後の実験 2 で生成を遅くする原因になります。

<br>

KV キャッシュを使う LLM の処理は、次の 2 つの段階に分かれます。表の右の列は、Ollama の応答に含まれる、その段階のトークン数と時間の値です。

| 段階 | 何をするか | Ollama の応答の値 |
|---|---|---|
| プロンプトの処理（prefill） | 入力の全トークンの Q・K・V をまとめて計算する。K・V はキャッシュに入れ、各トークンの Q は自分とそれより前の K と比べる。最後に最初の出力トークンを選ぶ | `prompt_eval_count`、`prompt_eval_duration` |
| 生成（decode） | 1 トークンずつ、新しいトークンの Q を自分を含む全ての K と比べ、その比率で V を混ぜる。新しい K・V はキャッシュに足す | `eval_count`、`eval_duration` |

入力が長い時は、プロンプトの処理が、最初のトークンが出るまでの待ち時間の大部分になります（モデルの読み込みなどは、`load_duration` として別に返ります）。

生成の速さは、1 トークンを出すたびにメモリから読む量で決まりやすくなります。生成では 1 トークンごとにモデルの重みのほとんどをメモリから読み出しますが、その割に計算は少ないので、読み出しの速さが上限になるからです（詳しくは[ローカル LLM の速さのノート](../local-llm-speed/)）。生成のたびに読むのは、モデルの重みだけでなく、キャッシュに溜まった K・V もです。

---

### キャッシュの大きさ

KV キャッシュの大きさは、モデルの構成から計算できます。1 トークンあたりのバイト数は次の式です。

```text
1 トークンあたり = 2（K と V）× 層の数 × KV ヘッドの数 × ヘッドの次元 × 1 個のバイト数
全体            = 1 トークンあたり × コンテキスト長
```

ヘッドの次元は、1 つのヘッドの K（または V）の数値の個数です。[Qwen3-1.7B の config.json](https://huggingface.co/Qwen/Qwen3-1.7B/blob/main/config.json) では、層の数（`num_hidden_layers`）が 28、KV ヘッドの数（`num_key_value_heads`）が 8、ヘッドの次元（`head_dim`）が 128 です。

K・V の数値 1 個を f16（16 ビットの浮動小数点数、2 バイト。Ollama の既定。モデルの型の名前では fp16 と書きます）で持つと、1 トークンあたり `2 × 28 × 8 × 128 × 2 = 114,688` バイト（112 KiB。KiB は 1,024 バイト）になります。

コンテキスト長が 4,096 なら 448 MiB（MiB は 2 の 20 乗バイト）、Qwen3-1.7B の上限の 40,960（config.json の `max_position_embeddings`。モデルカードのコンテキスト長は 32,768）なら 4.375 GiB です。

<br>

Qwen3-1.7B は Q を 16 ヘッド持ちますが、K と V は 8 ヘッドしか持ちません。Q ヘッドをいくつかの組に分け、組ごとに 1 組の K・V を共有する方式を GQA（[Grouped-Query Attention](https://arxiv.org/abs/2305.13245)）と呼び、Qwen3-1.7B では 2 つの Q ヘッドが 1 組を共有します。以下は、通常の注意機構・GQA・MQA で、Q ヘッドと K・V の組の対応を並べた図です。

{{< figure src="images/kv-cache_gqa.webp" alt="3 段の図。どの段も上に 16 個の小さな青い枠（Q ヘッド）が並び、縦の線で下の黄土色の枠（K・V の組）につながる。通常の段は K・V も 16 個で 224 KiB / トークン、GQA（Qwen3）の段は 2 つの Q が 1 つの K・V を共有して 8 個で 112 KiB / トークン、MQA の段は 16 個の Q が 1 つの横長の K・V を共有して 14 KiB / トークン" caption="Q ヘッドと K・V の組の対応（通常・GQA・MQA）" align="center" >}}

共有しない通常の注意機構で Q と同じ 16 ヘッド分の K・V を持つと、KV キャッシュは 2 倍の 224 KiB / トークンになります。全ての Q ヘッドで 1 組だけを共有するのが [MQA](https://arxiv.org/abs/1911.02150)（Multi-Query Attention）で、14 KiB / トークンまで減ります。GQA は、MQA ほど共有せずに精度をなるべく保ちながら、KV キャッシュを減らすための方式です。

重みの量子化（重みを 8 ビットや 4 ビットに詰めること。[量子化のノート](../quantization/)）は、この式のどこにも入っていません。重みが q4_K_M（主に 4 ビット）でも fp16（16 ビット）でも、KV キャッシュの大きさは同じです。

---

### 実験 1: num_ctx とメモリ

実験は、2026 年 11 月 10 日に手元の PC の Ollama で行いました。モデルは qwen3:1.7b で、重みの持ち方が違う 3 つの型（8 ビットの q8_0、16 ビットの fp16、主に 4 ビットの q4_K_M）を使い、上記の式が成り立つかを確認します。

<br>

<details>
<summary>実験の環境（Ollama の版、GPU、計測中の負荷）</summary>

- Ollama 0.22.1。サーバーの設定は既定のままで、KV キャッシュは f16 です。
- GPU は CPU とメモリを共有するタイプ（AMD の [Ryzen AI Max+ 395](https://www.amd.com/en/products/processors/laptop/ryzen/ai-300-series/amd-ryzen-ai-max-plus-395.html) に内蔵された Radeon 8060S）です。
- 全ての実験の間、他の作業の qwen3:4b が同じ GPU に読み込まれたままでした。そのため、時間を測る実験 2・3 は 3 巡して中央値を採っています。
- 思考モードを切ったことや、モデルの digest は [lab/README.txt](https://github.com/nao1215/debimate/blob/main/content/notes/generative-ai/kv-cache/lab/README.txt) に記録しています。

</details>

<br>

モデルを一度メモリから降ろしてから num_ctx を指定して読み込み直し、[/api/ps](https://docs.ollama.com/api/ps)（`ollama ps` と同じ情報）の `size` を記録します。`size` は、読み込んだモデルが使うメモリの量です。あわせて、読み込み時にサーバーのログに出る KV キャッシュの大きさを拾い、同じ num_ctx のまま約 1,800 トークンの入力を送った後の `size` も記録します。

以下は、Ollama の API を呼ぶ補助関数と、実験 1 の繰り返しの部分です。ログを拾う関数などを含む全体は、下の折りたたみに置いています。

```python
# lab/kvlab.py から抜粋
def generate(model, prompt, num_ctx=None, num_predict=64, keep_alive="10m"):
    opts = {"temperature": 0, "seed": 1, "num_predict": num_predict}
    if num_ctx is not None:
        opts["num_ctx"] = num_ctx
    body = {"model": model, "prompt": prompt, "stream": False, "think": False,
            "options": opts, "keep_alive": keep_alive}
    t0 = time.time()
    r = api("/api/generate", body)
    r["wall"] = time.time() - t0
    r["thinking_chars"] = len(r.get("thinking") or "")
    return r

# lab/exp_memory.py から抜粋（unload は keep_alive 0 で降ろして消えるまで待つ関数、
# load_log は読み込み時のログから "kv cache" などの行を拾う関数）
for model, ctx in CASES:
    print(f"## {model} num_ctx={ctx}", flush=True)
    print("  ps before:", ps_line(ps()), flush=True)
    gone = unload(model)
    t0 = time.time() - 2
    r = generate(model, "Say hi.", num_ctx=ctx, num_predict=1, keep_alive="5m")
    time.sleep(1)
    after = ps()
    mine = [x for x in after if x["name"] == model]
    log = load_log(model, t0)
    row = {"model": model, "num_ctx": ctx, "unloaded_first": gone,
           "ps": mine[0] if mine else None, "log": log,
           "load_duration_s": r["load_duration"] / 1e9, "thinking_chars": r["thinking_chars"]}
    # 同じ num_ctx のまま長い入力（約 1,800 トークン）を送り、size が変わるかを見る
    r2 = generate(model, filler(70) + "\nHow many records are listed above? Answer with a number.",
                  num_ctx=ctx, num_predict=8, keep_alive="5m")
    mine2 = [x for x in ps() if x["name"] == model]
```

<br>

<details>
<summary>kvlab.py と exp_memory.py の全体</summary>

```python
"""KV キャッシュの実験で共通に使う道具（Python 標準ライブラリだけ）。

- Ollama の HTTP API を呼ぶ
- /api/ps を記録する
- サーバーのログ（systemd の journal）から、読み込み時の "kv cache" などの行を拾う
- 長さを変えられる詰め物の文章を作る
"""
import json
import os
import subprocess
import time
import urllib.request

HOST = os.environ.get("OLLAMA_HOST", "127.0.0.1:11435")
# ログを読むコマンド。著者の環境では Ollama を systemd のユーザーサービス local-llm で動かしている
LOG_UNIT = os.environ.get("KVLAB_LOG_UNIT", "local-llm")
MODELS_DIR = os.environ.get("OLLAMA_MODELS", os.path.expanduser("~/.ollama/models"))


def api(path, body=None, timeout=900):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(f"http://{HOST}{path}", data=data,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def ps():
    """/api/ps を短い形にする（名前・size・size_vram・context_length）。"""
    out = []
    for m in api("/api/ps")["models"]:
        out.append({"name": m["name"], "size": m["size"], "size_vram": m["size_vram"],
                    "context_length": m.get("context_length")})
    return out


def ps_line(rows):
    return "; ".join(f'{r["name"]} size={r["size"]/1e9:.2f}GB vram={r["size_vram"]/1e9:.2f}GB '
                     f'ctx={r["context_length"]}' for r in rows) or "(none)"


def blob_of(model):
    """モデル名から重みの blob（sha256-...）を引く。ログの "starting runner" 行と照合するため。"""
    name, tag = model.split(":")
    path = os.path.join(MODELS_DIR, "manifests/registry.ollama.ai/library", name, tag)
    with open(path) as f:
        man = json.load(f)
    for layer in man["layers"]:
        if layer["mediaType"] == "application/vnd.ollama.image.model":
            return layer["digest"].replace(":", "-")
    raise RuntimeError(model)


def load_log(model, since_epoch):
    """since_epoch 以降のログから、model を読み込んだ時の行（KvSize と device.go の内訳）を返す。"""
    try:
        txt = subprocess.run(["journalctl", "--user", "-u", LOG_UNIT, "--since", f"@{since_epoch:.0f}",
                              "--no-pager", "-o", "cat"], capture_output=True, text=True,
                             timeout=30).stdout
    except Exception as e:  # ログが読めない環境では空で返す
        return {"error": str(e)}
    blob = blob_of(model)
    lines = txt.splitlines()
    found = None
    for i, ln in enumerate(lines):
        if "starting runner" in ln and blob in ln:
            found = i
    if found is None:
        return {}
    info = {}
    for ln in lines[found:found + 80]:
        if "KvSize:" in ln and "Operation:commit" in ln:
            info["KvSize"] = int(ln.split("KvSize:")[1].split()[0])
            info["KvCacheType"] = ln.split("KvCacheType:")[1].split(" ")[0] or "(empty)"
        if "source=device.go" in ln:
            msg = ln.split('msg="')[1].split('"')[0]
            dev = ln.split("device=")[1].split()[0] if "device=" in ln else "-"
            size = ln.split('size="')[1].split('"')[0]
            info[f"{msg} {dev}"] = size
            if msg == "total memory":
                break
    return info


def unload(model):
    try:
        api("/api/generate", {"model": model, "keep_alive": 0})
    except Exception:
        pass
    # 実際に消えるまで待つ（他の作業の都合で長引いた時は記録して先へ進む）
    for _ in range(60):
        if all(r["name"] != model for r in ps()):
            return True
        time.sleep(1)
    return False


def filler(n_lines, seed=0):
    """数えやすい詰め物。1 行はおよそ 25 トークン（qwen3 で prompt_eval_count を見て調整）。"""
    rows = []
    for i in range(n_lines):
        k = (i * 7919 + seed * 104729) % 100000
        rows.append(f"Record {i + 1}: sensor S{k % 97:02d} reported {k % 1000} units "
                    f"at hour {k % 24} on day {k % 31 + 1}.")
    return "\n".join(rows)


def generate(model, prompt, num_ctx=None, num_predict=64, keep_alive="10m"):
    opts = {"temperature": 0, "seed": 1, "num_predict": num_predict}
    if num_ctx is not None:
        opts["num_ctx"] = num_ctx
    body = {"model": model, "prompt": prompt, "stream": False, "think": False,
            "options": opts, "keep_alive": keep_alive}
    t0 = time.time()
    r = api("/api/generate", body)
    r["wall"] = time.time() - t0
    r["thinking_chars"] = len(r.get("thinking") or "")
    return r
```

```python
"""実験 1: num_ctx を変えて読み込み、/api/ps の size と、ログの KV キャッシュの大きさを記録する。

同じ num_ctx で短いプロンプトと長いプロンプトを送り、size が入力の長さで変わるかも見る。
"""
import json
import sys
import time

from kvlab import filler, generate, load_log, ps, ps_line, unload

CASES = [
    ("qwen3:1.7b-q8_0", None), ("qwen3:1.7b-q8_0", 2048), ("qwen3:1.7b-q8_0", 4096),
    ("qwen3:1.7b-q8_0", 8192), ("qwen3:1.7b-q8_0", 16384), ("qwen3:1.7b-q8_0", 32768),
    ("qwen3:1.7b-q8_0", 40960),
    # 重みの形式だけを変える（KV キャッシュは同じ大きさになるはず）
    ("qwen3:1.7b-fp16", 4096), ("qwen3:1.7b-fp16", 32768),
    ("qwen3:1.7b-q4_K_M", None), ("qwen3:1.7b-q4_K_M", 4096),
]

results = []
for model, ctx in CASES:
    print(f"## {model} num_ctx={ctx}", flush=True)
    print("  ps before:", ps_line(ps()), flush=True)
    gone = unload(model)
    t0 = time.time() - 2
    r = generate(model, "Say hi.", num_ctx=ctx, num_predict=1, keep_alive="5m")
    time.sleep(1)
    after = ps()
    mine = [x for x in after if x["name"] == model]
    log = load_log(model, t0)
    row = {"model": model, "num_ctx": ctx, "unloaded_first": gone,
           "ps": mine[0] if mine else None, "log": log,
           "load_duration_s": r["load_duration"] / 1e9, "thinking_chars": r["thinking_chars"]}
    # 同じ num_ctx のまま長い入力（約 1,800 トークン）を送り、size が変わるかを見る
    r2 = generate(model, filler(70) + "\nHow many records are listed above? Answer with a number.",
                  num_ctx=ctx, num_predict=8, keep_alive="5m")
    mine2 = [x for x in ps() if x["name"] == model]
    row["long_prompt_eval_count"] = r2["prompt_eval_count"]
    row["ps_after_long"] = mine2[0] if mine2 else None
    row["long_load_duration_s"] = r2["load_duration"] / 1e9
    print("  ps after :", ps_line(after), flush=True)
    print("  log      :", json.dumps(log, ensure_ascii=False), flush=True)
    print(f"  long prompt {r2['prompt_eval_count']} tok -> size "
          f"{(mine2[0]['size'] / 1e9) if mine2 else float('nan'):.3f} GB", flush=True)
    results.append(row)
    unload(model)

json.dump(results, open(sys.argv[1] if len(sys.argv) > 1 else "memory.json", "w"),
          indent=1, ensure_ascii=False)
```

</details>

<br>

記録した `memory.json` は、[lab/summarize_memory.py](https://github.com/nao1215/debimate/blob/main/content/notes/generative-ai/kv-cache/lab/summarize_memory.py) で表に整形しました（計測の前後の `/api/ps` を含む生の出力は [lab/output_memory.txt](https://github.com/nao1215/debimate/blob/main/content/notes/generative-ai/kv-cache/lab/output_memory.txt)）。

<br>

<details>
<summary>num_ctx ごとの size とログの KV キャッシュの表</summary>

`ps size` は読み込んだ直後、`after 1.8k` は約 1,800 トークンを送った後の `size`（バイト）、`calc kv cache` は前の節の式で計算した値です。

```text
model              num_ctx  loaded        ps size     after 1.8k log kv cache calc kv cache
qwen3:1.7b-q8_0       None   40960  7,070,831,488  7,070,831,488      4.4 GiB     4.375 GiB
qwen3:1.7b-q8_0       2048    2048  2,517,914,496  2,517,914,496    224.0 MiB     224.0 MiB
qwen3:1.7b-q8_0       4096    4096  2,754,892,672  2,754,892,672    448.0 MiB     448.0 MiB
qwen3:1.7b-q8_0       8192    8192  3,237,237,632  3,237,237,632    896.0 MiB     896.0 MiB
qwen3:1.7b-q8_0      16384   16384  4,189,344,640  4,189,344,640      1.8 GiB     1.750 GiB
qwen3:1.7b-q8_0      32768   32768  6,106,141,568  6,106,141,568      3.5 GiB     3.500 GiB
qwen3:1.7b-q8_0      40960   40960  7,070,831,488  7,070,831,488      4.4 GiB     4.375 GiB
qwen3:1.7b-fp16       4096    4096  4,605,426,560  4,605,426,560    448.0 MiB     448.0 MiB
qwen3:1.7b-fp16      32768   32768  7,956,675,456  7,956,675,456      3.5 GiB     3.500 GiB
qwen3:1.7b-q4_K_M     None   40960  6,210,022,272  6,210,022,272      4.4 GiB     4.375 GiB
qwen3:1.7b-q4_K_M     4096    4096  1,894,083,456  1,894,083,456    448.0 MiB     448.0 MiB
```

</details>

<br>

読み込み時のログの KV キャッシュは、num_ctx 2,048 で 224.0 MiB、4,096 で 448.0 MiB、40,960 で 4.4 GiB でした。前の節の式で計算した 224 MiB・448 MiB・4.375 GiB と一致します。以下は、num_ctx と `size` の関係をグラフにしたものです。グラフの GB は 10 の 9 乗バイトで、前の節の GiB（2 の 30 乗バイト）とは単位が違います。

{{< figure src="images/kv-cache_memory.webp" alt="qwen3:1.7b-q8_0 の size は num_ctx 2,048 で 2.52 GB、4,096 で 2.75 GB、8,192 で 3.24 GB、16,384 で 4.19 GB、32,768 で 6.11 GB、40,960 で 7.07 GB。2,048 の値から 1 トークンあたり 114,688 バイトずつ増やした破線とほぼ重なる。fp16 は 4,096 で 4.61 GB、32,768 で 7.96 GB、q4_K_M は 4,096 で 1.89 GB、40,960 で 6.21 GB で、どの型も同じ傾きで増える" caption="num_ctx と読み込んだモデルの size（qwen3:1.7b の 3 つの型）" align="center" >}}

3 つの型は重みの分だけ上下にずれていますが、傾きは同じです。num_ctx を 4,096 から 32,768 に上げた時の増え方は、q8_0 と fp16 のどちらも 3,351,248,896 バイトで、1 バイトも違いませんでした。

このうち 3,288,334,336 バイトは、増えた 28,672 トークン分の KV キャッシュ（`28,672 × 114,688`）です。残りの約 63 MB は、ログに出る計算用の作業領域（compute graph）が num_ctx に合わせて大きくなった分です。

<br>

もう 1 つ分かるのは、`size` が入力の長さで変わらないことです。約 1,800 トークンを送った後の `size` は、全ての行で読み込み直後と同じでした。冒頭の図の通り、Ollama は読み込んだ時点で num_ctx 個の枠の分を全部確保し（同時に処理する要求の数が 1 の時）、プロンプトが短くても空きの枠の分のメモリを使ったままにします。

ただし、`/api/ps` の `size` は、Ollama が読み込み時に割り当てた量の報告で、プロンプトの長さに応じて増減する使用量ではありません。枠の分が実際に確保されたことは、ログの `kv cache ROCm0`（ROCm0 は GPU を指すログ上の名前。num_ctx 32,768 で 3.5 GiB など。上の表の `log kv cache`）で確認しています。

num_ctx を指定しない時は上限の 40,960 で読み込まれ、短い質問でも 4.4 GiB の KV キャッシュを確保しました。既定値の決まり方は [Ollama の num_ctx のノート](../ollama-context-length/)で説明しています。

---

### 実験 2: 入力の長さと速さ

次に、num_ctx を 32,768 に固定し、入力の長さだけを約 540 トークンから約 30,800 トークンまで 7 段階に変えて、プロンプトの処理の時間（`prompt_eval_duration`）と生成の速さ（`eval_count / eval_duration`）を測りました。

毎回、入力の先頭に違う文字列を置いて、前の回の KV キャッシュを使わせないようにしています。生成は最大 64 トークンで、64 トークンを確実に出させるために、1〜300 の数を書かせて途中で止めます。7 段階を 3 巡して、長さごとに中央値を採りました。

```python
# lab/exp_prefill.py から抜粋（全体は下の折りたたみ）
MODEL = "qwen3:1.7b-q8_0"
NUM_CTX = 32768
LINES = [19, 39, 79, 159, 319, 639, 1170]  # およそ 512〜30,000 トークン
ROUNDS = 3
TAIL = "\nIgnore the records. Write the integers from 1 to 300 separated by commas."

generate(MODEL, "Say hi.", num_ctx=NUM_CTX, num_predict=1)  # 読み込みを先に済ませる
rows = []
for rnd in range(ROUNDS):
    for n in LINES:
        before = ps()
        prompt = f"Session {uuid.uuid4().hex}\n" + filler(n, seed=rnd) + TAIL
        r = generate(MODEL, prompt, num_ctx=NUM_CTX, num_predict=64)
```

<br>

<details>
<summary>exp_prefill.py の全体</summary>

```python
"""実験 2: num_ctx を 32768 に固定し、入力の長さだけを変えて、
プロンプトの処理の時間（prompt_eval_duration）と生成の速さを測る。

毎回、先頭に違う札（nonce）を置き、前回の KV キャッシュを使い回させない。
3 巡して、長さごとに中央値と最小・最大を出す。
"""
import json
import statistics
import sys
import time
import uuid

from kvlab import filler, generate, ps, ps_line

MODEL = "qwen3:1.7b-q8_0"
NUM_CTX = 32768
LINES = [19, 39, 79, 159, 319, 639, 1170]  # およそ 512〜30,000 トークン
ROUNDS = 3
TAIL = "\nIgnore the records. Write the integers from 1 to 300 separated by commas."

generate(MODEL, "Say hi.", num_ctx=NUM_CTX, num_predict=1)  # 読み込みを先に済ませる
rows = []
for rnd in range(ROUNDS):
    for n in LINES:
        before = ps()
        prompt = f"Session {uuid.uuid4().hex}\n" + filler(n, seed=rnd) + TAIL
        r = generate(MODEL, prompt, num_ctx=NUM_CTX, num_predict=64)
        after = ps()
        row = {"round": rnd + 1, "lines": n,
               "prompt_eval_count": r["prompt_eval_count"],
               "prompt_eval_s": r["prompt_eval_duration"] / 1e9,
               "eval_count": r["eval_count"], "eval_s": r["eval_duration"] / 1e9,
               "load_s": r["load_duration"] / 1e9, "thinking_chars": r["thinking_chars"],
               "ps_before": before, "ps_after": after, "time": time.strftime("%H:%M:%S")}
        rows.append(row)
        print(f"round {rnd + 1} prompt {row['prompt_eval_count']:6d} tok "
              f"prefill {row['prompt_eval_s']:7.3f} s ({row['prompt_eval_count'] / row['prompt_eval_s']:7.1f} tok/s) "
              f"| gen {row['eval_count']} tok {row['eval_count'] / row['eval_s']:5.1f} tok/s "
              f"| load {row['load_s']:.2f} s | thinking {row['thinking_chars']} chars", flush=True)
        print("    ps after:", ps_line(after), flush=True)

print("\n# median (min - max) over rounds")
for n in LINES:
    rs = [x for x in rows if x["lines"] == n]
    pe = [x["prompt_eval_s"] for x in rs]
    gen = [x["eval_count"] / x["eval_s"] for x in rs]
    print(f"prompt {statistics.median(x['prompt_eval_count'] for x in rs):6.0f} tok  "
          f"prefill {statistics.median(pe):7.3f} s ({min(pe):.3f}-{max(pe):.3f})  "
          f"gen {statistics.median(gen):5.1f} tok/s ({min(gen):.1f}-{max(gen):.1f})")

json.dump(rows, open(sys.argv[1] if len(sys.argv) > 1 else "prefill.json", "w"), indent=1)
```

</details>

<br>

以下は、3 巡の中央値をグラフにしたものです（縦の線は最小から最大の幅）。

{{< figure src="images/kv-cache_prefill.webp" alt="左のグラフは入力のトークン数とプロンプトの処理の時間で、542 トークンで 0.12 秒、8,305 トークンで 2.65 秒、30,759 トークンで 21.0 秒と、長いほど傾きが急になる。右のグラフは生成の速さで、542 トークンの 92.0 トークン毎秒から、30,759 トークンの 38.8 トークン毎秒まで下がる" caption="入力の長さと、プロンプトの処理の時間・生成の速さ" align="center" >}}

<br>

<details>
<summary>3 巡の中央値（括弧内は最小と最大）の出力</summary>

各回の値は [lab/output_prefill.txt](https://github.com/nao1215/debimate/blob/main/content/notes/generative-ai/kv-cache/lab/output_prefill.txt) にあります。

```text
# median (min - max) over rounds
prompt    542 tok  prefill   0.122 s (0.120-0.122)  gen  92.0 tok/s (91.9-93.2)
prompt   1047 tok  prefill   0.236 s (0.235-0.276)  gen  88.4 tok/s (81.8-91.2)
prompt   2046 tok  prefill   0.435 s (0.435-0.450)  gen  85.2 tok/s (84.8-85.6)
prompt   4129 tok  prefill   1.048 s (1.035-1.067)  gen  76.6 tok/s (75.6-77.1)
prompt   8305 tok  prefill   2.647 s (2.632-2.666)  gen  66.1 tok/s (65.6-66.5)
prompt  16692 tok  prefill   7.581 s (7.550-7.905)  gen  51.9 tok/s (47.6-52.2)
prompt  30759 tok  prefill  21.030 s (20.626-21.253)  gen  38.8 tok/s (36.2-39.0)
```

</details>

<br>

プロンプトの処理の時間（図の左）は、入力の長さに比例するより速く増えました。1 秒あたりに処理したトークン数は、2,000 トークン前後の約 4,700 から、30,759 トークンでは約 1,460 まで落ちています。注意機構では、各トークンの Q を自分とそれより前の全ての K と比べるので、比べる回数は入力の長さの 2 乗に比例します。入力が短いうちはモデルの重みの掛け算が時間の大半を占め、長くなるとこの 2 乗の部分が効いてきます。

<br>

生成の速さ（図の右）も、入力が長いほど落ちました。KV キャッシュがあっても、新しい 1 トークンを出すたびに、それまでの全てのトークンの K・V を読む必要があるからです。

30,759 トークンの K・V は `30,759 × 114,688 バイト ≒ 3.5 GB` で、q8_0 のファイル（約 2.2 GB）より大きくなります。

生成のたびに読む重みは、ファイルの約 2.2 GB から、入力の埋め込み（トークンを最初のベクトルに変える表で、1 トークンにつき 1 行しか読まない部分）を除いた約 1.88 GB です（[量子化のノート](../quantization/)と同じ見積もり）。生成の速さがメモリから読む量で決まるなら、1 トークンあたりに読む量は、K・V を足して約 1.95 GB から約 5.41 GB になり、速さは 2.8 分の 1 程度になる計算です。以下は、この読む量と実測の速さを並べた図です。

{{< figure src="images/kv-cache_read_per_token.webp" alt="2 本の横棒。入力 542 トークンでは、青の重み 1.88 GB に細い黄土の K・V 0.06 GB が付いて計 1.95 GB、実測の速さは 92.0 トークン毎秒。入力 30,759 トークンでは、重みに K・V 3.53 GB が付いて計 5.41 GB、速さは 38.8 トークン毎秒。下に、読む量は約 2.8 倍、速さは約 2.4 分の 1" caption="1 トークンの生成ごとに読む量と、実測の速さ" align="center" >}}

実測は 92.0 から 38.8（2.4 分の 1）で、見積もりより少し小さい落ち方でした。読み出し以外の要因を分けて測ったわけではないので、ずれの理由は分かっていません。

---

### 実験 3: 同じ前置きの再利用

KV キャッシュは、1 回の生成の中だけでなく、次の要求にも使い回せます。チャットで会話を続ける時や、同じ長い資料に別の質問をする時、要求の先頭の部分（前置き、プレフィックス）は前回と同じです。前回の K・V がキャッシュに残っていれば、一致した部分の計算を省けます。K・V はそれより前のトークンにだけ依存するので、使い回せるのは先頭から一致している部分だけです。

これを確認するために、約 8,300 トークンの前置き（実験 2 と同じ詰め物）に対して、次の 5 通りの送り方を順に試しました。num_ctx は 32,768 で、3 巡しています。

```python
# lab/exp_prefix.py から抜粋（全体は下の折りたたみ）
head = f"Session {uuid.uuid4().hex}\n"
lines = filler(320, seed=10 + rnd).split("\n")
base = head + "\n".join(lines)
mid = len(lines) // 2
changed_mid = head + "\n".join(lines[:mid] + ["Record X: this line was edited."] + lines[mid + 1:])
cases = [
    ("1 first send", base + Q1),
    ("2 same prompt again", base + Q1),
    ("3 same prefix, new question", base + Q2),
    ("4 one line edited in the middle", changed_mid + Q1),
    ("5 one char added at the head", "X" + base + Q1),
]
for label, prompt in cases:
    r = generate(MODEL, prompt, num_ctx=NUM_CTX, num_predict=16)
```

<br>

<details>
<summary>exp_prefix.py の全体</summary>

```python
"""実験 3: 同じプレフィックスを送り直した時に、KV キャッシュが使い回されるかを見る。

Ollama 0.22.1 の prompt_eval_count は、使い回した分も含めた入力の全トークン数を返す。
使い回せたかどうかは、prompt_eval_duration（キャッシュに無かった分を計算した時間）で見る。
"""
import json
import sys
import uuid

from kvlab import filler, generate, ps, ps_line

MODEL = "qwen3:1.7b-q8_0"
NUM_CTX = 32768
Q1 = "\nWhich sensor appears in Record 5? Answer briefly."
Q2 = "\nWhich sensor appears in Record 9? Answer briefly."

rows = []
generate(MODEL, "Say hi.", num_ctx=NUM_CTX, num_predict=1)
for rnd in range(3):
    head = f"Session {uuid.uuid4().hex}\n"
    lines = filler(320, seed=10 + rnd).split("\n")
    base = head + "\n".join(lines)
    mid = len(lines) // 2
    changed_mid = head + "\n".join(lines[:mid] + ["Record X: this line was edited."] + lines[mid + 1:])
    cases = [
        ("1 first send", base + Q1),
        ("2 same prompt again", base + Q1),
        ("3 same prefix, new question", base + Q2),
        ("4 one line edited in the middle", changed_mid + Q1),
        ("5 one char added at the head", "X" + base + Q1),
    ]
    for label, prompt in cases:
        r = generate(MODEL, prompt, num_ctx=NUM_CTX, num_predict=16)
        row = {"round": rnd + 1, "case": label, "prompt_eval_count": r["prompt_eval_count"],
               "prompt_eval_s": r["prompt_eval_duration"] / 1e9, "load_s": r["load_duration"] / 1e9,
               "thinking_chars": r["thinking_chars"], "response": r["response"], "ps": ps()}
        rows.append(row)
        print(f"round {rnd + 1} {label:34s} prompt {row['prompt_eval_count']:5d} tok "
              f"prompt_eval {row['prompt_eval_s']:6.3f} s | load {row['load_s']:.2f} s "
              f"| thinking {row['thinking_chars']} chars | {r['response'].strip()[:40]!r}", flush=True)
    print("    ps:", ps_line(ps()), flush=True)

json.dump(rows, open(sys.argv[1] if len(sys.argv) > 1 else "prefix.json", "w"), indent=1,
          ensure_ascii=False)
```

</details>

<br>

使い回せたかどうかは、`prompt_eval_duration` で見ます。`prompt_eval_count` は、使い回した回でも入力の全トークン数（8,325 など）を返すからです。Ollama で使い回しを確認する方法は、[Ollama の num_ctx のノート](../ollama-context-length/)にまとめています。

以下は 3 巡目の結果です（`ps` の行は省略。3 巡の全体は [lab/output_prefix.txt](https://github.com/nao1215/debimate/blob/main/content/notes/generative-ai/kv-cache/lab/output_prefix.txt)）。

```text
round 3 1 first send                       prompt  8325 tok prompt_eval  2.604 s | load 0.07 s | thinking 0 chars | 'Sensor S57.'
round 3 2 same prompt again                prompt  8325 tok prompt_eval  0.016 s | load 0.08 s | thinking 0 chars | 'Sensor S57.'
round 3 3 same prefix, new question        prompt  8325 tok prompt_eval  0.033 s | load 0.07 s | thinking 0 chars | 'Sensor S21.'
round 3 4 one line edited in the middle    prompt  8307 tok prompt_eval  1.573 s | load 0.07 s | thinking 0 chars | 'Sensor S57.'
round 3 5 one char added at the head       prompt  8326 tok prompt_eval  2.607 s | load 0.07 s | thinking 0 chars | 'Sensor S57.'
```

次の図は、3 巡の中央値と、先頭からどこまでキャッシュを使えたかを並べたものです。帯の塗り分けは、送った内容から見た模式です。

{{< figure src="images/kv-cache_prefix.webp" alt="5 本の帯。1 初回は全体が黄土（計算し直す）で 2.609 秒。2 同じ入力をもう一度は、右端の細い黄土（応答を作るための末尾の 1 トークン）を除いて青（キャッシュから使う）で 0.016 秒。3 同じ前置き・別の質問は末尾のわずかだけ黄土で 0.033 秒。4 真ん中の 1 行を変更は前半が青、後半が黄土で 1.573 秒。5 先頭に 1 文字を追加は全体が黄土で 2.618 秒。下に、2・3 の右端の黄土は幅を誇張していると書かれている" caption="5 通りの送り方で、使い回せた範囲と処理の時間" align="center" >}}

前回と同じ前置きを送った 2 と 3 では、プロンプトの処理が 2.6 秒から 0.016〜0.033 秒に縮みました。

Ollama 0.22.1 は、キャッシュに残ったトークン列と新しい入力のトークン列を先頭から比べ、一致した数だけ使い回します（[runner/ollamarunner/cache.go](https://github.com/ollama/ollama/blob/v0.22.1/runner/ollamarunner/cache.go) の `LoadCacheSlot`）。入力の全体が一致した 2 でも、応答の最初のトークンを選ぶために、末尾の 1 トークンだけは計算し直します。3 は質問の文の途中（Record の番号）からトークンが違うので、コード上は、そこから後ろ（質問の残りと、Ollama が付けるチャットのテンプレートの末尾）の十数トークンだけを計算したことになります。どちらも、計算し直したトークン数は応答に出ないので、時間と実装からの推定です。

真ん中の 1 行を変えた 4 は約 1.6 秒で、変えた行より前の半分だけが使い回されたと考えられます。時間が半分より多くかかったのは、後ろの半分のトークンほど比べる相手（前の K）が多いからだと考えられます。先頭に 1 文字足した 5 は、中身がほとんど同じでも、1 回目と同じ時間がかかりました。

この結果から、長い前置きを持つプロンプトでは、毎回変わる値（日時、要求ごとの ID など）を先頭に置かず、変わらない部分を前に、変わる部分を後ろに置くのが良いことが分かります。

この実験の短い答えは、使い回しても変わりませんでした。ただし、qwen3:8b に 3 文の説明を書かせた実験では、使い回した回と計算し直した回で、temperature 0 でも出力が数トークン目から変わりました。その結果は [Sampling のノート](/notes/generative-ai/sampling/)にあります。

---

### KV キャッシュを小さくする方法

ここまでの通り、KV キャッシュはトークン数に比例して大きくなり、長い入力では生成も遅くします。小さくする方法は、キャッシュの大きさの式のどの項を減らすかで分けられます。

| 減らす項 | 方法 | 代わりに失うもの |
|---|---|---|
| KV ヘッドの数 | GQA、MQA | モデルの構造で決まるので、使う側では変えられない。共有するほど精度が落ちやすい |
| 1 個のバイト数 | KV キャッシュの量子化（f16 を 8 ビットや 4 ビットにする） | 精度が少し落ちる |
| トークン数 | コンテキスト長を必要な長さに絞る、入力を短くする | 超えた入力は扱えない |

GQA と MQA はモデルを作る側の選択で、Qwen3 は GQA を採っています。使う側で選べるのは、下の 2 行です。Ollama での設定の仕方は [Ollama の num_ctx のノート](../ollama-context-length/)にあります。入力のトークン数そのものを減らすには、文書の全体ではなく質問に近い断片だけを渡す方法があり、[RAG のノート](../rag/)で説明しています。

<br>

式の項は変えずに、確保の仕方で無駄を減らす方法もあります。Ollama はコンテキスト長の分の枠を先に全部確保しますが、[vLLM](https://github.com/vllm-project/vllm) の [PagedAttention](https://arxiv.org/abs/2309.06180) は、KV キャッシュを固定長のブロックに分け、使った分だけブロックを割り当てます。多数の要求を同時に処理する[推論サーバー](/ml/mlops/inference-serving/)で、空きの枠に使われないメモリを減らすための方式です。

---

### 利点と欠点

KV キャッシュの利点は、過去のトークンの K・V を一度だけ計算すればよいことです。生成の 1 ステップで計算するのは新しいトークンの分だけになり、同じ前置きを送り直した時も、実験 3 の通りプロンプトの処理をほぼ省けます。

一方で、次の欠点があります。

- メモリはトークン数に比例して増えます。Qwen3-1.7B では 1 トークン 112 KiB で、上限の 40,960 トークンでは KV キャッシュ（4.4 GiB）が q8_0 の重み（約 2.1 GiB）の 2 倍になりました。重みを量子化しても、この部分は小さくなりません。
- 枠を先に全部確保する実装（本記事の Ollama など）では、入力が短くてもコンテキスト長の分のメモリを使います。
- 入力が長いほど、プロンプトの処理の時間（最初のトークンまでの待ち時間の大部分）と、生成の 1 トークンあたりの時間が延びます。実験 2 では、約 30,800 トークンの入力で、プロンプトの処理に 21 秒かかり、生成は約 540 トークンの時の 2.4 分の 1 の速さになりました。

<br>

コンテキスト長は、大きくするほど長い入力を扱える代わりに、メモリで払う設定です。速さを落とすのは、実験 2 の通り、実際に読ませた入力の長さです（num_ctx を大きくしただけで速さが変わるかは、本記事では測っていません）。実験の数字は 1.7B のモデル 1 つと、他の作業と共有した 1 台の GPU での値なので、手元のモデルでは、上記の式でモデルの構成から 1 トークンあたりの大きさを計算して確認してください。
