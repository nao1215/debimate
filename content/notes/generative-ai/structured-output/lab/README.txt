Structured Output ノートの実験

入力文（texts.py）は本記事のために作った架空の文で、人物も実在しない。
テンプレートに名前・日付・金額を差し込んで作るので、正解は作る時点で決まる。

ファイル
  texts.py        入力文 40 件と正解を作る（乱数の seed は固定）
  run.py          Ollama の /api/chat に 3 方式（＋追加の schema_bare）で解かせ、応答と時間を JSON Lines に保存
  evaluate.py     パース・スキーマ・値の 3 段で採点し、時間をまとめる
  probe.py        応答の 1 トークン目の候補の確率を取り出す（冒頭の図の元データ）
  missing.py      金額が書かれていない文をスキーマで縛って解かせる
  think.py        think と format の組み合わせで、思考の文がどこに返るかを見る
  results.jsonl   run.py の出力（実験に使った全応答）
  summary.json    evaluate.py の集計（figures.py が読む）
  logprobs.json   probe.py の出力（figures.py が読む）
  output_*.txt    本文に載せた出力

環境（2026-11-10 に計測）
  Ollama 0.22.1（OLLAMA_HOST=127.0.0.1:11435 で起動しているもの）
  GPU: AMD Radeon 8060S（共有メモリ）。計測中は他の作業も同じ Ollama と GPU を使っていた
  モデル（ollama list の ID と、/api/tags の digest）
    qwen3:1.7b-q4_K_M  8f68893c685c3ddff2aa3fffce2aa60a30bb2da65ca488b61fff134a4d1730e7
    qwen3:4b           359d7dd4bcdab3d86b87d73ac27966f4dbb9f5efdfcc75d34a8764a09474fae7
    qwen3:8b           500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41
  qwen3:1.7b-q4_K_M は Ollama の qwen3:1.7b と同じ量子化（Q4_K_M）のタグ。
  qwen3:4b はメタデータの general.finetune が Thinking のモデルで、think: false を指定しても
  チャットテンプレートが応答の頭に <think> を置く。本文の「思考モードと format」を参照。
  Python 3（標準ライブラリ）。evaluate.py だけ jsonschema 4.25.1 を uv の一時環境で使う。

再現手順
  export OLLAMA_HOST=127.0.0.1:11435
  python3 run.py results.jsonl qwen3:1.7b-q4_K_M 3
  python3 run.py results.jsonl qwen3:8b 1
  python3 run.py results.jsonl qwen3:4b 1      # 本文の結果は先頭 20 件（60 行）で止めたもの
  python3 run.py results.jsonl qwen3:1.7b-q4_K_M 1 schema_bare
  python3 run.py results.jsonl qwen3:8b 1 schema_bare
  uv run --with jsonschema==4.25.1 python3 evaluate.py results.jsonl summary.json
  python3 probe.py qwen3:1.7b-q4_K_M 3 logprobs.json > output_probe.txt
  python3 missing.py qwen3:1.7b-q4_K_M qwen3:8b > output_missing.txt
  (python3 think.py qwen3:1.7b-q4_K_M 3; python3 think.py qwen3:4b 3) > output_think.txt
  cd .. && python3 figures.py     # matplotlib 3.10.7

  qwen3:4b は、他の作業と GPU を共有していて 1 件に数十秒かかったので、先頭の 20 件で止めた。
  run.py は、1 回目は 40 件全て、2 回目以降は先頭の 20 件だけを解かせる（時間のぶれを見るため）。
  出力に既にある組は飛ばすので、止めても同じコマンドで続きから再開できる。

再実行で一致しないもの
  - 時間。他のモデルとの入れ替えで毎回モデルの読み込みが入ったので、total_duration ではなく
    prompt_eval_duration + eval_duration で比べた。それでも負荷で 2 倍程度ぶれる（本文の幅）。
  - prompt 方式の応答。temperature 0、seed 42 でも、同じ入力を 3 回送ると 20 件中 7 件で
    応答の文字列が変わった（Markdown の囲みの有無、和暦から変換した年）。json・schema 方式は
    20 件とも 3 回同じだった。採点には 1 回目（rep 0）の応答を使う。
  - probe.py の確率。同じ入力でも実行ごとに 10 ポイント以上変わった。2026-11-10 に、テンプレートが
    think: false の時に足す " /no_think" をプロンプトに加えて取り直した（それ以前の版は付けて
    いなかった）。``` の確率は 4 回で 0.5988（査読時の 1 回）、0.7192、0.7619、0.7619。
    {" は 0.3544、0.2699、0.2255、0.2255。どの回も ``` が首位で、外した後は {" が選ばれる。
    図は最後に実行した logprobs.json（0.7619 の回）から描いている。
  - think.py の thinking の長さ。qwen3:1.7b の think: true は、実行ごとに 1,116〜6,885 文字とぶれた。
