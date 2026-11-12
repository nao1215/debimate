Character Consistency ノートの実験ファイル

前提
----
- ComfyUI（v0.35.0 のタグより後のコミット 19e1058）が http://127.0.0.1:8188 で動いていて、次がある
    models/checkpoints  waiIllustriousSDXL_v170.safetensors
        WAI-illustrious-SDXL v17.0  https://civitai.com/models/827184?modelVersionId=2883731
        ライセンス: Fair AI Public License 1.0-SD  https://freedevproject.org/faipl-1.0-sd/
    models/loras        説明用の画風 LoRA（本記事では example_style_lora.safetensors、起動語 <trigger> と書く）
    models/ipadapter    ip-adapter-plus_sdxl_vit-h.safetensors    https://huggingface.co/h94/IP-Adapter
    models/clip_vision  CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors
    models/controlnet   xinsir_union_promax_sdxl.safetensors     https://huggingface.co/xinsir/controlnet-union-sdxl-1.0
- カスタムノード
    ComfyUI_IPAdapter_plus  https://github.com/cubiq/ComfyUI_IPAdapter_plus  コミット a0f451a
    comfyui_controlnet_aux  https://github.com/Fannovel16/comfyui_controlnet_aux  コミット a587a4c（DWPreprocessor）
- 生成の台本（comfy.py、run.py）は Python 標準ライブラリだけで動く。依頼は 1 枚ずつ送り、/prompt が返した
  自分の prompt_id だけを /history で待つ。待ち行列の削除やサーバーの設定変更はしない。
  環境変数 COMFY_LOCK のファイルがある間は送らない（GPU を他の作業と分け合ったため）

生成
----
  STYLE_LORA=<loras/ の中のファイル名> STYLE_TRIGGER=<起動語> python3 run.py <PNG の保存先> seed_0 seed_1 seed_2 seed_3
  cp <PNG の保存先>/seed_3.png <PNG の保存先>/base.png        # 4 枚の候補から基準の絵を選ぶ（下記）
  STYLE_LORA=... STYLE_TRIGGER=... BASE_PICK=20261114 python3 run.py <PNG の保存先> $(python3 run.py --list | grep -v '^seed_')

  - 依頼は全部で 36 件（python3 run.py --list）。送ったワークフローは workflows/<名前>.json、
    prompt_id・実行秒数・送る直前の負荷は gen_log.json（他の作業の依頼と交互に流れたので、秒数は 27〜162 秒とばらつく）
  - 共通の設定: 832x1216、28 ステップ、CFG 5.5、euler_ancestral、scheduler normal、clip skip 2、画風 LoRA の強さ 0.75
  - プロンプト（{scene} に場面の語が入る。<trigger> は LoRA の起動語）
      <trigger>, 1girl, solo, adult woman, mature female, 20s, brown hair, medium hair, low ponytail,
      parted bangs, forehead, open eyes, visible eyes, green eyes, eye highlights, long eyelashes, lips, earrings,
      jewelry, nail polish, medium breasts, white collared shirt, navy cardigan, long sleeves, {scene},
      masterpiece, best quality, highly detailed
  - 場面の語
      base   neutral expression, closed mouth, standing, arms at sides, upper body, looking at viewer,
             simple background, white background
      smile  smile, closed mouth, standing, arms at sides, upper body, looking at viewer, simple background, white background
      wave   smile, waving, hand up, standing, upper body, looking at viewer, simple background, white background
      cafe   smile, sitting, holding cup, coffee cup, table, cafe, indoors, upper body, looking at viewer
  - ネガティブ
      lowres, bad quality, bad anatomy, bad hands, extra limbs, text, signature, watermark, logo, collage,
      (multiple views:1.2), inset, zoom layer, variations, border, frame, heart, hair over eyes, hair over one eye,
      covered eyes, blunt bangs, closed eyes, half-closed eyes, multicolored hair, streaked hair, two-tone hair,
      oversaturated, neon colors, nsfw, nude, nipples, cleavage, underwear, child, loli, aged down, 2girls,
      multiple girls, large breasts, huge breasts, sleepy eyes, sultry
  - 依頼の種類（名前の頭）
      seed_     同じプロンプト（base）で seed だけ 20261111〜20261114。4 枚目 seed_3 を基準の絵 base.png にした
      nolora_   seed_ と同じで、画風 LoRA と起動語を外す
      fixed_    seed を基準と同じ 20261114 にして、場面の語だけ smile / wave / cafe に変える
      newseed_  場面の語を変え、seed も 20261211 に変える（参照画像の対照）
      ipa       newseed_ に IP-Adapter Plus（IPAdapterAdvanced、weight_type linear、V only）で基準の絵を参照させる。
                ipa50 / ipa80 は重み 0.5 / 0.8 で全ステップ、ipa35s0 は 0.35、ipa60s3 は 0.6 で 3 割の位置から
      redraw_   newseed_ の絵を下絵に、denoise 0.5 の img2img で描き直し、その段に参照（重み 0.7）を掛ける
      i2i       基準の絵を下絵にした img2img。i2i50 / i2i70 / i2i85 は denoise 0.5 / 0.7 / 0.85、seed は基準と同じ
      pose_     基準の絵から DWPose で骨格を取り（DWPreprocessor、resolution 1024、scale_stick_for_xinsr_cn enable）、
                ControlNet Union の openpose（強さ 1.0、0〜1）で縛って seed を 20261312 / 20261313 にする。骨格は *_skeleton
      other_    物差しの目盛り用の別人（blonde hair, short hair, bob cut, blue eyes, black turtleneck）。seed 20261411 / 20261412

人物の絵の確かめ
----------------
  全ての絵を目で確かめた。載せる条件は、成人、服を着ている、露出や性的な姿勢が無い、1 人、両目が開いて前髪で隠れていない。
  外した絵: 最初のプロンプト（medium breasts・large breasts のネガティブプロンプト・目の語が無い版）で描いた候補 3 枚。胸が強調された構図で、
  目が半眼に寄ったため、プロンプトを上の形に直して seed_0〜seed_3 を描き直した（3 枚目は受け取る前に打ち切ったので画像は無い）。
  別人の 2 枚は体の線の出るセーターになったので、本文には載せず、数値の物差しにだけ使った。

計測
----
  python3 metrics.py faces <PNG のディレクトリ> faces.json              # 1 段目: 顔の切り抜きと CLIP の埋め込み
  python3 metrics.py tags  <PNG のディレクトリ> faces.json metrics.json # 2 段目: WD tagger のタグ（出力は output_metrics.txt）
  - <PNG のディレクトリ> には seed_3.png を除いた 36 枚（seed_3 と同じ画像を base.png として置く）
  - 1 段目は ComfyUI の venv（torch 2.12.0a0+rocm7.13、transformers 5.17.0、CPU で実行）、
    2 段目は onnxruntime 1.30.0・numpy 2.5.3・Pillow 12.3.0 の venv で動かした
  - 顔の切り抜き: CLIPSeg に "face" の範囲を推定させ、確率 0.4 を超えた範囲を囲む正方形
    （OpenCV の lbpcascade_animeface も試したが、上半身の大きな顔を半分以上取り逃したので使わなかった）
  - 組の中の総当たりの近さ（画風 LoRA の有無の比較）は figures.py が faces.json の埋め込みから数える（output_pairwise.txt）

画像
----
  python3 to_webp.py <PNG のディレクトリ> ../images
  生成した PNG はリポジトリの外に置き、リポジトリには本文で使った WebP（24 枚）だけを入れた。

図の再生成
----------
  cd .. && uv run --with matplotlib==3.11.2 --with numpy==2.5.4 --with pillow==13.0.0 python figures.py

計測した環境
------------
  2026-11-11、AMD Ryzen AI Max+ 395、Radeon 8060S（RAM 128GB のうち 64GB を GPU に割り当て）、
  ComfyUI 0.35.0（コミット 19e1058）、PyTorch 2.12.0a0+rocm7.13
