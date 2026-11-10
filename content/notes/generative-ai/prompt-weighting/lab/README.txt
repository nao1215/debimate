Prompt Weighting のノートの実験ファイル

前提
----
  - ComfyUI（v0.35.0 で確認。手元はタグ v0.35.0 から 26 コミット先の 19e1058。
    本文で参照した comfy/sd1_clip.py・sdxl_clip.py・clip_model.py・samplers.py は
    タグ v0.35.0 と同一）が http://127.0.0.1:8188 で動いていて、
    models/checkpoints に waiIllustriousSDXL_v170.safetensors がある
      WAI-illustrious-SDXL v17.0
      https://civitai.com/models/827184?modelVersionId=2883731
      ライセンス: Illustrious License（Fair AI Public License 1.0-SD）
  - run.py は Python 標準ライブラリだけ。analyze.py・to_webp.py は NumPy と Pillow、
    token_chunks.py は transformers（tokenizer だけを使う。PyTorch は不要）を使う
  - LoRA・自作のモデルは使っていない

ファイル
--------
  workflow_api.json  ComfyUI の API 形式のワークフロー（8 ノード）。run.py が
                     ノード 4（プロンプト）・5（打ち消し）・7 の seed を書き換える
  conditions.py      5 つの実験の条件（プロンプト・打ち消し・seed）
  run.py             条件を 1 枚ずつ ComfyUI に送り、PNG を保存する
  analyze.py         PNG の色を数え、条件ごとに seed で平均する
  token_chunks.py    プロンプトを CLIP のトークンに分け、ComfyUI と同じ規則で
                     75 トークンの枠に詰める
  to_webp.py         本文に並べる WebP（448 px）を作る
  result_*.json      analyze.py の結果（../figures.py がグラフに使う）
  output_*.txt       analyze.py・token_chunks.py の表示

生成の設定（workflow_api.json と同じ）
------------------------------------
  モデル        : waiIllustriousSDXL_v170.safetensors（LoRA なし）
  steps         : 24
  sampler       : euler、scheduler: normal
  CFG           : 5.5
  解像度        : 1024 x 1024、batch 1
  CLIP          : CLIPSetLastLayer -2（clip skip 2）

  実験ごとのプロンプト・打ち消し・seed は conditions.py にある。
    positive  : 実験 1。blue ceramic teapot の重み 1.0〜2.0、seed 101〜103（18 枚）
    negative  : 実験 2。打ち消しの先頭 k 語（k = 1, 6, 12）の重み 1.0〜1.8 と、
                白黒の 2 語だけ・残りの 10 語だけに重みを付ける切り分け、
                seed 101〜103（57 枚）
    position  : 実験 3。red background を置く位置 5 通り、seed 201〜204（20 枚）
    ablation  : 実験 4。静物の 8 個の品の語を 1 つずつ外す 9 通り、seed 301・302（18 枚）
    lighting  : 実験 5。照明の語（なし / night / neon light / sunset / dramatic lighting）
                × 打ち消し 12 語の重み（なし / 1.2 / 1.3）、seed 101〜103（45 枚）。
                照明の語なしの 9 枚は negative と同じ文面なので、negative の
                w1.0・k12_w1.2・k12_w1.3 の PNG を none_neg1.0・none_neg1.2・none_neg1.3 の
                名前で lighting/ に写してから run.py を実行した（残り 36 枚を生成）

手順
----
  python3 run.py positive <PNG の保存先>      # negative / position / ablation も同じ
  uv run --with numpy --with pillow python analyze.py <PNG の保存先> positive result_positive.json
  uv run --with transformers python token_chunks.py <ComfyUI>/comfy/sd1_tokenizer "<プロンプト>"
  cd .. && uv run --with matplotlib python figures.py

  run.py は 1 枚送るごとに、その prompt_id の完了を /history で待ってから次を送る。
  待ち行列の他の依頼には触れない。保存済みの PNG は送り直さない。
  再現性の確認: python3 run.py <実験名> <保存先> --again <条件名> <seed>

結果の記録
----------
  output_positive.txt / output_negative.txt / output_position.txt / output_ablation.txt /
  output_lighting.txt
      analyze.py の表示（seed で平均した値）。seed ごとの値は result_*.json
  output_tokens.txt
      実験 3 の 4 通りのプロンプトと、括弧の入れ子の例を token_chunks.py に通した表示
  output_again.txt
      全ての生成の後に 3 条件（positive w1.4 / negative k12_w1.8 / ablation
      no_silver_spoon、seed は 101・101・301）を --again で生成し直し、元の PNG と
      画素を比べた結果。3 枚とも 1 画素も違わなかった。PNG のファイル自体は、
      ComfyUI が埋め込むワークフロー（保存名を含む）が違うのでハッシュが一致しない

  計測した環境: 2026-11-10、ComfyUI 0.35.0、PyTorch 2.12.0a0+rocm7.13、
  GPU は AMD Radeon 8060S。1 枚あたり 19〜24 秒（ComfyUI の execution_start から
  execution_success まで）。同じ ComfyUI を他の作業も使っていて、待ち行列の
  待ち時間は 1 枚あたり数十秒〜2 分あった（時間は本文の結論に使っていない）。

  人物の題材を試して捨てた絵: 実験 4 は最初、服を着た成人の上半身で試したが、
  露出のある絵・目元が髪で隠れた絵が出たため、掲載せずに静物に切り替えた
  （試した 20 枚はいずれも掲載していない。本文と result_ablation.json は静物の 18 枚）。
