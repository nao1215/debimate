Tool Calling ノートの実験ファイル

全て Python 3.8 以降の標準ライブラリだけで動く（図の生成だけ matplotlib を使う）。
ツールは全て模擬で、ファイル操作・メール送信・ネットワークアクセスはしない。
外に出る通信は、OLLAMA_HOST の Ollama への HTTP だけ。

ファイル
--------
  agent.py          ループ・模擬ツール・引数の検証（JSON Schema の type / enum /
                    required / additionalProperties だけを見る最小の実装）
  tasks.py          本記事のために自作した 30 個の課題と採点（正規表現）
  run_bench.py      実験 1: 30 課題 x seed（既定 3 個）でループを回し、jsonl に記録する
  run_injection.py  実験 2: ツールの結果に指示を混ぜ、危険な模擬ツールを呼ぶかを数える
  *.jsonl           1 行が 1 回のループ（止まった理由・問い合わせの回数・全ての呼び出し・
                    最終回答）
  summarize.py      jsonl を集計して summary.json と output_summary.txt の表を出す
  show_raw.py       /api/chat の JSON の往復を 1 回分表示する（output_raw.txt）
  output_env.txt    Ollama のバージョンとモデルの digest

再現手順
--------
  export OLLAMA_HOST=127.0.0.1:11435        # 著者の環境。既定は 127.0.0.1:11434
  python3 show_raw.py qwen3:8b > output_raw.txt
  python3 run_bench.py qwen3:8b off bench_qwen3-8b_off.jsonl        # seed 3 個
  python3 run_bench.py qwen3:8b on  bench_qwen3-8b_on.jsonl 1       # seed 1 個
  python3 run_bench.py qwen3:4b on  bench_qwen3-4b_on.jsonl 1       # seed 1 個
  python3 run_injection.py qwen3:8b off inj_qwen3-8b_off.jsonl 10 summarize
  python3 run_injection.py qwen3:8b off inj_qwen3-8b_off_act.jsonl 10 act
  python3 run_injection.py qwen3:4b on  inj_qwen3-4b_on_act.jsonl 2 act
  python3 summarize.py > output_summary.txt
  cd .. && uv run --with matplotlib==3.10.7 python figures.py

  2 つ目の引数は思考モード。on は think: true、off は think: false を送る。
  qwen3:4b（Qwen3-4B-Thinking-2507）は思考モードしか持たず、think: false を送っても
  思考の文章が content に混ざるため、on で回した。混ざった出力の記録は、構造化出力のノートの
  ../../structured-output/lab/output_think.txt にある（qwen3:4b think=false format=none の行。
  このノートの実験では think: false の出力を残していない）。

生成の設定（agent.py）
----------------------
  temperature 0.6、num_ctx 8192、stream false
  seed は実験 1 が 1〜3（qwen3:8b think=off）と 1（他の 2 つ）、実験 2 が 1〜10（qwen3:8b）と
  1〜2（qwen3:4b）。qwen3:4b は思考の文章を毎回 数百〜千トークン書くため、負荷の高い
  共有マシンでは 1 回のループに 1〜3 分かかり、回数を減らした
  問い合わせの上限 8 回、同じ名前・同じ引数の呼び出しは 3 回目で打ち切り

計測した環境
------------
  Ollama 0.22.1（/api/version）
  qwen3:8b  digest 500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41
            Q4_K_M、8.2B
  qwen3:4b  digest 359d7dd4bcdab3d86b87d73ac27966f4dbb9f5efdfcc75d34a8764a09474fae7
            Q4_K_M、4.0B、general.finetune = Thinking、general.version = 2507
  GPU は AMD Radeon 8060S（共有メモリ）。他の作業と同じ Ollama を共有していた。

再実行と一致
------------
  seed と temperature を固定しても、Ollama の生成は毎回一致しなかった。原因は
  確かめていない（他のリクエストを同時に処理していたことが候補と考えているが推測）。
  実際に、qwen3:8b think=off の seed 1 の 30 課題を回し直したところ
  （rerun_qwen3-8b_off_seed1.jsonl）、回答の文字列が完全に一致したのは 30 回中 17 回、
  呼び出しの列が一致したのは 26 回で、正解の数は 26 から 29 に変わった。
  本文の割合は、1 回分の標本として読むこと。実験中は他の作業と同じ Ollama を
  共有し、自分の実験も最大 3 本を並行して流していた。

採点の注意
----------
  採点は tasks.py の正規表現による自動判定で、summarize.py が jsonl の回答に当て直す。
  不正解の回答は全て目で読み、採点の誤りで落としたものが無いことを確かめた
  （確かめた結果、2026-11-10 に「福岡の方が大阪より暖かい」と
  「〜する機能を持っていません」を正解にするよう規則を直した）。
