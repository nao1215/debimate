RAG ノートの実験

文書集合
  debimate のコミット 16c40d266f3b22752613f56f41fc1ca5e2f37c08 時点の
  content/notes/**/index.md（84 本）。rag_lab.py が git show で読むので、
  作業ツリーの変更には影響されない。前処理（コードブロック・画像・HTML・
  shortcode を除く）の後で 575,605 文字。

ファイル
  rag_lab.py        前処理・チャンク分割・埋め込み・全件検索
  questions.json    質問 30 個と正解（ノートの slug・### の節・根拠の文）。
                    筆者（この記事の執筆者）が各ノートを読んで作ったもの。
                    質問は本文の言い回しを避けて書いたが、作り手が正解を
                    知っているので、実際の利用者の質問より易しい可能性がある。
  eval_recall.py    チャンクの切り方ごとの Recall@k
  ask.py            上位 k 個のチャンクを qwen3:4b に渡して答えさせる
  output_*.txt      実行結果
  output_recall.json  figures.py がグラフに使う値

環境
  Ollama 0.22.1（OLLAMA_HOST=127.0.0.1:11435）
  bge-m3:latest   790764642607（埋め込み、1,024 次元）
  qwen3:4b        359d7dd4bcda（生成。中身は Qwen3-4B-Thinking-2507 で、
                  think=false を渡しても思考を止められない。think=true で
                  思考を回答と分け、回答だけを記録した。temperature 0、
                  seed 42、num_ctx 16384）
  Python 3 + numpy 2.3.4（uv で一時環境を作る）

再現手順
  export OLLAMA_HOST=127.0.0.1:11435
  CACHE=/path/to/cache   # 埋め込み（約 50 MB）の保存先。リポジトリの外でよい
  uv run --with numpy==2.3.4 python3 rag_lab.py build $CACHE > output_build.txt
  uv run --with numpy==2.3.4 python3 eval_recall.py $CACHE output_recall.json > output_recall.txt
  uv run --with numpy==2.3.4 python3 ask.py $CACHE 200 0 21 > output_ask_noctx.txt
  uv run --with numpy==2.3.4 python3 ask.py $CACHE section 5 21 27 > output_ask.txt
  uv run --with numpy==2.3.4 python3 ask.py $CACHE 1000 5 22 >> output_ask.txt
  図は ../figures.py（uv run --with matplotlib==3.10.7 python3 figures.py）

再実行で変わり得るもの
  埋め込みは GPU の浮動小数点演算の順序で末尾の桁が揺れることがあり、
  類似度がほぼ同じチャンクの順位が入れ替わる可能性がある。2026-11-10 に
  節単位の 33 個を埋め込み直した時と eval_recall.py を再実行した時は、
  どちらも結果が完全に一致した。
  埋め込みの作成時間（5 通り合わせて約 5,800 個で約 20 分）は、他の作業と
  GPU を共有した状態で 1 回だけ測った値で、負荷で大きく変わる。
  生成は temperature 0・seed 固定でも、Ollama やドライバの版で文面が変わり得る。
