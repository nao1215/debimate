ローカル LLM の速さ（local-llm-speed）と MoE（mixture-of-experts）のノートの実験ファイル

2 本のノートは同じ計測を使う。図は ../figures.py（このノート）と
../../mixture-of-experts/figures.py（MoE のノート）が、ここの runs.jsonl・gguf.json・mem.json から作る。

環境（output_env.txt）
----------------------
  2026-11-11、Ollama 0.22.1（127.0.0.1:11434）、Linux 7.0.0
  AMD Ryzen AI Max+ 395、Radeon 8060S、RAM 128GB のうち 64GB を GPU に割り当て（mem_info_vram_total 68,719,476,736）
  Python 3.14.4（bench.py・gguf_bytes.py・mem.py・check_gptoss.py は標準ライブラリだけ）
  matplotlib 3.10.7・Pillow 12.1.1（figures.py）

モデル
------
  qwen3:8b                                 ollama list の ID 500a1f067a9f（Q4_K_M）
  qwen3-coder:30b                          06c1097efce0（Q4_K_M）
  hf.co/ggml-org/gpt-oss-20b-GGUF:latest   c6110f4035c3（エキスパートの重みは MXFP4、他は Q8_0）
  gpt-oss は、ollama pull gpt-oss:20b が「requires a newer version of Ollama」で失敗したので、
  Hugging Face の ggml-org/gpt-oss-20b-GGUF を ollama pull hf.co/... で取った

1. GGUF のヘッダーから 1 トークンで読む重みのバイト数を数える
----------------------------------------------------------------
  B=/usr/share/ollama/.ollama/models/blobs
  python3 gguf_bytes.py qwen3-8b=$B/sha256-a3de86cd... qwen3-coder-30b=$B/sha256-1194192c... \
      gpt-oss-20b=$B/sha256-27cd6c43... --json gguf.json > output_gguf.txt
  - blob のパスは ollama show --modelfile <モデル> の FROM 行
  - エキスパートの重み（名前に _exps を含むテンソル）は expert_used_count / expert_count の割合だけ、
    埋め込み（token_embd）は 1 行だけ、それ以外は全部を 1 トークンごとに読むとして数える

2. prefill と decode の速さ
---------------------------
  LOCK_DIR=<ロックを置くディレクトリ> python3 bench.py runs.jsonl 3 > output_bench.txt
  - 入力は灯台守の記録を 12・110・450・900 行（約 500・4K・16K・32K トークン）並べ、
    最後に「1 から 400 まで数字を書け」と頼む。生成は 128 トークンで打ち切る
  - num_ctx 36,864、temperature 0、seed 1。think は qwen3 系 false、gpt-oss "low"
  - 先頭に毎回違う札を置き、前回のプロンプトのキャッシュを使わせない
  - 各回の前に、他の作業のロックが無く、ComfyUI の待ち行列が空で、GPU の使用率が 3 秒続けて
    10% 以下になるまで待つ。各回の最中も 0.5 秒ごとに ComfyUI の待ち行列を見て、
    他の生成と重なった回には disturbed の印を付けて測り直す
  - 1 周目の途中で計測を止めて測り直しの形に直したので、output_bench.txt には 2 回分の開始がある
  - 全 42 回のうち、ComfyUI の生成と重なった 3 回（disturbed）と、印は付かなかったが ComfyUI の
    生成と生成の間 6 秒・2 秒に挟まれて decode が他の回より 3 割遅かった 1 回（12:38:44）を除いた
  - qwen3:8b の 4K と 16K は、追加で測った 4 周目も含めて 4 回、他は 3 回の中央値
  - 集計は output_summary.txt（figures.py の出力）

3. メモリ
---------
  python3 mem.py mem.json   # num_ctx 4,096 と 36,864 で読み込み、/api/ps の size を記録（run_all の後半）

4. gpt-oss の返答の中身
-----------------------
  python3 check_gptoss.py > output_check_gptoss.txt
  - この GGUF と Ollama 0.22.1 の組では、eval_count は 128（1024）まで進むが、
    message.content も message.thinking も空で返った。速さの計測（トークン数 ÷ 時間）には
    影響しないが、本文の中身は確かめていない
