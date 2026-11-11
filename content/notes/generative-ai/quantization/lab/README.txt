量子化（Quantization）ノートの実験ファイル

使ったモデルと環境
------------------
  Ollama 0.22.1（OLLAMA_HOST=127.0.0.1:11435）
  モデル（ollama list の ID は manifest の SHA-256 の先頭 12 桁）
    qwen3:1.7b-q4_K_M  8f68893c685c3ddff2aa3fffce2aa60a30bb2da65ca488b61fff134a4d1730e7
                       本体 blob sha256-3d0b790534fe4b79525fc3692950408dca41171676ed7e21db57af5c65ef6ab6
    qwen3:1.7b-q8_0    29b6a7a420a42b7d58a17334049721746c35aec6084209ceed327e78a124d15f
                       本体 blob sha256-48bffa1478e612465567147cae67bf5e1539ed3080ec5415a35789d6fd4c851d
    qwen3:1.7b-fp16    e9354f6174db6aa7af338e75b9087e3f4364c255ff96eb20c1805a2f786ed763
                       本体 blob sha256-ac95b7f076ba3ec24ddfd1a8c201edace65f77117dfc8ee3923beae48a4279c6
  ollama list の表示は output_ollama_list.txt
  Python 3.14.4、NumPy 2.3.5（block_error.py だけが NumPy を使う）、matplotlib 3.10.7（figures.py）
  GPU は AMD Radeon 8060S（CPU と共有のメモリ）。他の作業と同時に測った。実験 3 の各回の直前の
  負荷平均（1 分）は 4.6〜21.7（output_speed.txt の load 列）

  uv で一時環境を作る場合:
    uv run --with numpy==2.3.5 python block_error.py ...
    uv run --with matplotlib==3.10.7 python ../figures.py

実験 1: GGUF のヘッダーから型ごとの個数とバイト数を数える
--------------------------------------------------------
  B=<Ollama のモデルの置き場所>/blobs
  python3 gguf_header.py q4_K_M=$B/sha256-3d0b... q8_0=$B/sha256-48bf... fp16=$B/sha256-ac95... \
      --json gguf.json > output_gguf.txt

  - 標準ライブラリだけで動く。テンソルの中身は読まない
  - どの blob が本体かは manifests/registry.ollama.ai/library/qwen3/<タグ> の JSON で、
    mediaType が application/vnd.ollama.image.model の層の digest

実験 2: 1 つの行列を自分で Q8_0・Q4_0 に丸め、Ollama のファイルの値とも比べる
--------------------------------------------------------------------------
  python3 block_error.py $B/sha256-ac95... $B/sha256-48bf... $B/sha256-3d0b... block_error.json \
      > output_block.txt

  - 対象は blk.0.ffn_gate.weight（2048 x 6144）
  - Ollama の q8_0 / q4_K_M のファイルは、llama.cpp の dequantize_row_q8_0 /
    dequantize_row_q4_K と同じ計算で戻している
  - 丸めは llama.cpp の quantize_row_q8_0_ref / quantize_row_q4_0_ref（コミット 3837bf0 の
    ggml/src/ggml-quants.c）と同じく、FP32 のスケールの逆数で割り、Q8_0 は roundf（ちょうど 0.5 は
    0 から遠い側）で丸める。スケールを FP16 にするのはファイルに書く時だけ。この形で Ollama の q8_0 の
    ファイルと全ての重みが一致する（以前の版は FP16 に丸めたスケールの逆数と np.round を使い、99.2039 %）
  - 何度実行しても同じ結果になる

実験 3: 生成とプロンプト処理の速さ
----------------------------------
  OLLAMA_HOST=127.0.0.1:11435 python3 bench_speed.py speed.json > output_speed.txt

  - 思考モードは "think": false で無効。temperature 0、seed 1、num_ctx 4096、
    生成は最大 128 トークン、プロンプトは 950 トークン
  - 先頭に毎回違う文字列を置き、前回のプロンプトのキャッシュを使わせない
  - 最初に各モデルを 1 回ずつ動かして読み込み（計測しない）、その後
    q4_K_M → q8_0 → fp16 の順に 1 回ずつ測る周回を 9 回繰り返し、中央値を採る
  - 各回の前後に /api/ps（ollama ps と同じ情報）を取り、自分の 3 つ以外に
    読み込まれていたモデルを output_speed.txt の行末に書いた。同じ Ollama を
    他の作業も使っていて、他のモデルが読み込まれた状態の回がある
  - 各回の返答について、message.thinking の長さと content に <think> が
    含まれるかを記録した（thinking 0 chars なら思考の文は eval_count に入っていない）
  - 時間はマシンの負荷で大きくぶれる。再実行すると値は変わる
  - 1 回目の計測は、他の作業のモデル（qwen3:8b）の停止待ちで Ollama の待ち行列が
    15 分以上進まず、5 周目の途中でタイムアウトした。本文の値は 2 回目の計測

思考モードが無効になっているかの確認
------------------------------------
  OLLAMA_HOST=127.0.0.1:11435 python3 check_thinking.py > output_check_thinking.txt

  - 3 つのモデルは ollama show の Capabilities に thinking を持つ（思考と非思考を
    切り替えられる版）。"think": false で、実験 4 の 1 問と実験 3 のプロンプトを送り、
    thinking の長さ・content の <think>・eval_count を表示する。比較として
    "think": true でも 1 問送る

実験 4: 同じ問題集の正答率
--------------------------
  python3 make_problems.py problems.json
  OLLAMA_HOST=127.0.0.1:11435 python3 eval_accuracy.py problems.json accuracy.json \
      > output_accuracy.txt

  - 問題は本記事のために自作した 100 問（算数 40 問は seed 20261110 の乱数で生成、
    常識 60 問は手書き）。全て英語で、答えが 1 つに決まるものだけにした
  - system に "Answer with only the final answer. Do not explain."、
    "think": false で思考モードを無効にし、temperature 0、seed 1、num_predict 128
  - 採点: 算数は返答の中で最後に出た整数、常識は認める表記のどれかが単語として
    含まれていれば正解
  - 各問の返答は accuracy.json に残している

図の再生成
----------
  cd .. && python3 figures.py   # gguf.json・block_error.json・speed.json・accuracy.json から WebP を作る（images/）

本文の数値のうち lab の出力に無いもの
--------------------------------------
  - ollama ps の SIZE: qwen3:1.7b-q4_K_M を num_ctx の指定なし（文脈 40,960）で
    読み込んだ時 6.2 GB、num_ctx 4096 で読み込んだ時 1.9 GB（2026-11-10 に ollama ps で確認）
