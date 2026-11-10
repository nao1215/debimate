Image Linting ノートの実験ファイル

1. 画像の生成（ComfyUI）
-----------------------------------------------------
  前提: ComfyUI（v0.35.0 で確認）が http://127.0.0.1:8188 で動いていて、
        models/checkpoints に waiIllustriousSDXL_v170.safetensors がある
        （WAI-illustrious-SDXL v17.0
          https://civitai.com/models/827184?modelVersionId=2883731
          ライセンス: Fair AI Public License 1.0-SD https://freedevproject.org/faipl-1.0-sd/ ）

  python3 run_generate.py <PNG の保存先>

  - 標準ライブラリだけで動く。依頼は 1 枚ずつ送り、自分の prompt_id の完了だけを待つ。
    待ち行列の削除・中断はしない。保存先に同じ名前の PNG があれば送らない
  - workflow_api.json が ComfyUI の API 形式のワークフロー（LoRA なし）。run_generate.py は
    ノード 4（プロンプト）・ノード 7 の seed・ノード 9 の保存名だけを書き換える
  - designs.json が服装 4 つ（A〜D）・条件 3 つ（plain / neon / pose）・seed の一覧。
    プロンプトは「subject, common, outfit, 条件の語」を ", " でつないだ文字列
  - 生成するのは、評価用の 72 枚（4 服装 x 3 条件 x seed 20261110〜20261115）と、
    服装ごとの基準の絵 4 枚（条件 plain、seed 20261100）。名前は A_plain_20261110 の形

  生成の設定（workflow_api.json と同じ）
    ベースモデル  : waiIllustriousSDXL_v170.safetensors（LoRA なし）
    steps / CFG   : 28 / 5.5
    sampler       : euler_ancestral、scheduler: normal
    解像度        : 832 x 1216、batch 1
    CLIP          : CLIPSetLastLayer -2
    ネガティブ    : nsfw, nude, cleavage, underwear, swimsuit, see-through, lowres,
                    worst quality, bad quality, low quality, jpeg artifacts, blurry,
                    text, signature, watermark, logo, child, loli, shota

  計測した環境: 2026-11-10、ComfyUI 0.35.0、GPU は AMD Radeon 8060S。
  他の 3 つの依頼元と同じ待ち行列を共有していたので、1 枚あたり 64〜182 秒
  （/prompt に送ってから /history に結果が出るまで。待ち時間を含む）。

  同じ seed で生成し直した時の一致:
    python3 run_generate.py <別の保存先> --only A_plain_20261110,D_neon_20261112
    python3 check_same.py <PNG の保存先> <別の保存先>      # 出力は output_same.txt
  2 枚とも、違う画素は 0 だった。GPU・ドライバ・PyTorch のバージョンが違うと、
  同じ seed でも画素が一致するとは限らない。

  メモ: 共通の語に最初は rating:general を入れていたが、試しの 1 枚（服装 A・seed 20261100）で
  画面の左上に文字が描かれたので、general に替えてから 76 枚を生成した。

2. 検品に使う値の計算（CPU）
-----------------------------------------------------
  uv run --python 3.12 --with onnxruntime==1.31.1 --with numpy --with pillow \
      python lint_features.py <PNG の保存先> <モデルのディレクトリ> features.json

  76 枚で約 1 分（CPU 8 スレッド）。モデルのディレクトリには、次の公開の重みを置く
  （2026-11-10 に取得）。
    wd-vit-tagger-v3/{model.onnx,selected_tags.csv}
      https://huggingface.co/SmilingWolf/wd-vit-tagger-v3
      （revision 7f6b584d0bd3f55c4531f14ba3d4761b2bccdc0f、Apache License 2.0）
    clip-vit-base-patch32-onnx/{vision_model.onnx,preprocessor_config.json}
      https://huggingface.co/Xenova/clip-vit-base-patch32 の onnx/vision_model.onnx
      （revision 6b7c523703ae26e39be4b03774966f8571c7f523、MIT。
        元は https://huggingface.co/openai/clip-vit-base-patch32 、
        コードは https://github.com/openai/CLIP （MIT））
    face_detect_v1.4_s/{model.onnx,threshold.json}
      https://huggingface.co/deepghs/anime_face_detection
      （revision 784dc4c0bb692351ddcdbe6131a050b17d3025d5、MIT）
    person_detect_v1.3_s/{model.onnx,threshold.json}
      https://huggingface.co/deepghs/anime_person_detection
      （revision e39c744c22432ad01f91dd254fe2b02c8d878b8c、MIT）

  features.json は大きい（タグ 10,861 個 x 枚数、約 10 MB）ので、リポジトリには入れていない。

3. 合否のラベルと評価
-----------------------------------------------------
  uv run --with numpy python evaluate.py features.json labels.json result.json

  - labels.json は、本記事の執筆時に 72 枚を 1 枚ずつ目で見て付けた合否と理由。
    全身の一覧と、顔から手までの拡大を並べて見た。1 人の判断で、別の人が付ければ変わり得る
  - 閾値（TAG・CLIP_MIN・BORDER_MAX・NEON_MAX）と、服装ごとの必須のタグは、
    ラベルを付ける前に evaluate.py に書き、その後は変えていない
  - 出力は output_evaluate.txt、図に使う値は result.json

4. 本文の人物の絵
-----------------------------------------------------
  「実際に外した絵と止めるべき検査」の節の人物の絵（images/lint_ng_*.webp）は、
  著者が以前に画風 LoRA で作った立ち絵の検品で外した絵で、weeknotes に載せた画像の再掲。
    https://debimate.jp/weeknotes/2026-10-26/8575939c5076/
    https://debimate.jp/weeknotes/2026-11-02/e2cecb994e2c/
  この lab のスクリプトでは再現できない。

5. 図
-----------------------------------------------------
  cd .. && uv run --with matplotlib --with numpy python figures.py --results
  # 表紙の図（image_linting_cover.svg）は標準ライブラリだけで描く。
  # --results を付けると、result.json から検査ごとの誤り・通過率・近さの分布の図を描く
