KV キャッシュ（KV Cache）ノートの実験ファイル

使ったモデルと環境
------------------
  Ollama 0.22.1（OLLAMA_HOST=127.0.0.1:11435）。サーバーの環境変数は OLLAMA_HOST と
  OLLAMA_MODELS だけで、OLLAMA_CONTEXT_LENGTH・OLLAMA_KV_CACHE_TYPE・OLLAMA_NUM_PARALLEL は
  設定していない（KV キャッシュは既定の f16、並列数は既定の 1。ログの Parallel:1 で確認）
  ログには "enabling flash attention" と出ており、Flash Attention は有効
  モデル（manifest の SHA-256。ollama list の ID はこの先頭 12 桁）
    qwen3:1.7b-q8_0    29b6a7a420a42b7d58a17334049721746c35aec6084209ceed327e78a124d15f
    qwen3:1.7b-fp16    e9354f6174db6aa7af338e75b9087e3f4364c255ff96eb20c1805a2f786ed763
    qwen3:1.7b-q4_K_M  8f68893c685c3ddff2aa3fffce2aa60a30bb2da65ca488b61fff134a4d1730e7
  ollama list とバージョンの表示は output_ollama_list.txt
  モデルの構成は Qwen/Qwen3-1.7B の config.json と、/api/show の model_info で確認した
    層 28、Q ヘッド 16、KV ヘッド 8、head_dim 128、上限のコンテキスト長 40,960
  Python 3.14.4（実験は標準ライブラリだけ）、matplotlib 3.11.2（figures.py だけ）
  GPU は AMD Radeon 8060S（CPU と共有のメモリ、ROCm）。Ollama 0.22.1 が GPU のメモリと見なした量は
  94.7 GiB（2026-11-10 の journal の sched.go の行 total="94.7 GiB"。lab の出力には無い）。
  num_ctx を指定しない時の既定値はこの量から 262,144 になり、モデルの上限に切り詰められる
  実験 2・実験 3 の間は、他の作業の qwen3:4b（size 42.31 GB、ctx 262144）が同じ GPU に
  読み込まれたままだった（output_prefill.txt・output_prefix.txt の ps の行）
  他の作業が同じ Ollama と GPU を使っており、負荷平均が 10 前後の状態で測った
  思考モード（thinking）は全ての要求で "think": false を指定して無効にした。
  各出力の thinking の文字数は全て 0（output_*.txt の thinking 列、*.json の thinking_chars）

  図の再生成: uv run --with matplotlib==3.11.2 python ../figures.py

共通の道具: kvlab.py
--------------------
  - /api/generate を temperature 0、seed 1、"think": false、stream なしで呼ぶ
  - /api/ps（ollama ps と同じ情報）を各計測の前後で記録する
  - 読み込み時のサーバーのログ（KvSize と "kv cache" などの内訳）を journalctl で拾う。
    著者の環境では Ollama を systemd のユーザーサービス local-llm で動かしている。
    別の名前なら KVLAB_LOG_UNIT で変える。ログを読めない環境では log が空になるだけ
  - 詰め物の文章 filler() は 1 行がおよそ 25 トークン

実験 1: num_ctx とメモリ
-------------------------
  OLLAMA_HOST=127.0.0.1:11435 python3 exp_memory.py memory.json > output_memory.txt

  - モデルを一度降ろし（keep_alive 0）、num_ctx を指定して "Say hi." で読み込み直す
  - 読み込んだ直後の /api/ps と、約 1,800 トークンの入力を送った後の /api/ps を比べる
  - 表にした結果は python3 summarize_memory.py memory.json > output_memory_summary.txt
    （Ollama には接続しない）
  - 時間を測る実験ではないので、何度実行しても size は同じになる
    （1 回目の実行の記録は KvCacheType の列の読み取りを直す前のもので、
    size とログの値は 2 回目と一致した）

実験 2: 入力の長さと速さ
-------------------------
  OLLAMA_HOST=127.0.0.1:11435 python3 exp_prefill.py prefill.json > output_prefill.txt

  - qwen3:1.7b-q8_0、num_ctx 32768 で 1 度だけ読み込み、入力の長さだけを変える
  - 先頭に毎回違う文字列（uuid）を置き、前回の KV キャッシュを使わせない
  - 結果のぶれ: プロンプトの処理の時間は 3 巡の最小と最大の差が中央値の 1.3〜17%、
    生成の速さは 0.9〜11%（output_prefill.txt の median の行）
  - 生成は最大 64 トークン（1〜300 を書かせて途中で止める）
  - 7 段階の長さを 1 巡として 3 巡し、長さごとに中央値と最小・最大を出す
  - 各回の load_duration が 0.1 秒前後であること（途中で読み込み直していないこと）と、
    前後の /api/ps を記録している

実験 3: 同じ前置きの再利用
---------------------------
  OLLAMA_HOST=127.0.0.1:11435 python3 exp_prefix.py prefix.json > output_prefix.txt

  - 約 8,000 トークンの前置きに対して、5 通りの送り方を 3 巡する
  - Ollama 0.22.1 の prompt_eval_count は、使い回した分も含む入力の全トークン数を返した。
    使い回せたかどうかは prompt_eval_duration で見ている

実験 4: num_ctx を超えた入力
-----------------------------
  OLLAMA_HOST=127.0.0.1:11435 python3 exp_truncate.py truncate.json > output_truncate.txt

  - 先頭に合言葉を置いた約 3,100 トークンの入力を、num_ctx 2048 と 8192 で送る
  - 送る直前の journal の cursor を覚え、その後に出た "truncating input prompt" の行を記録する
