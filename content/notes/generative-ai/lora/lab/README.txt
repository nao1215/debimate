注意: 実験に使った LoRA（example_style_lora.safetensors）は、本記事の説明用に用意した独自の画風 LoRA です。プロンプトの <trigger> は、この LoRA の起動語です。再現する時は、手元の画風 LoRA とその起動語に読み替えてください。

LoRA ノートの実験ファイル

実験 1: safetensors のヘッダーからパラメータ数を数える
-----------------------------------------------------
  python3 count_params.py <LoRA の .safetensors> <ベースモデルの .safetensors> params.json

  - Python 3.8 以降の標準ライブラリだけで動く。テンソルの中身は読まない
  - 使ったファイル
      LoRA       : example_style_lora.safetensors（説明用の画風 LoRA。170,570,692 bytes）
      ベース     : waiIllustriousSDXL_v170.safetensors（6,938,040,682 bytes）
                   WAI-illustrious-SDXL v17.0（LoRA の学習に使ったモデル）
                   https://civitai.com/models/827184?modelVersionId=2883731
                   SHA-256 f116b0c78ff441467b0cdc8f1936e1ed18ea31e9997c7b132b1b8db533f0bd04
  - 出力は params.json（figures.py がグラフに使う）。表示は output_count.txt

実験 2: LoRA の強さを変えて同じ条件で 5 枚生成する
-----------------------------------------------------
  前提: ComfyUI（v0.35.0 で確認）が http://127.0.0.1:8188 で動いていて、
        models/checkpoints に waiIllustriousSDXL_v170.safetensors、
        models/loras に example_style_lora.safetensors がある

  python3 run_sweep.py <PNG の保存先>            # euler_ancestral（本文の 1 段目）
  python3 run_sweep.py <PNG の保存先> euler      # euler（本文の 2 段目）
  python3 to_webp.py <PNG の保存先> ../images ancestral   # または euler
  python3 seed_baseline.py <PNG の保存先>       # 比べる基準（seed だけ違う 5 枚）

  - run_sweep.py は標準ライブラリだけ、to_webp.py と seed_baseline.py は Pillow と
    NumPy を使う
  - workflow_api.json が ComfyUI の API 形式のワークフロー。run_sweep.py は
    LoraLoader の strength_model / strength_clip（0, 0.25, 0.5, 0.75, 1.0）と、
    指定された時だけ sampler_name を書き換えて /prompt に送る
  - to_webp.py は本文に並べる 5 枚の WebP（lora_<名前>_000.webp など）と、
    強さ 0 の画像との画素の差・各画像の明るさ（pixel_change_<名前>.json）を出す
  - seed_baseline.py は LoRA なし（強さ 0）で seed だけを 20261110〜20261114 に
    変えた 5 枚を生成し、全ての組（10 組）の画素の差を seed_baseline.json に出す。
    seed 20261110 の 1 枚は run_sweep.py の強さ 0 の画像と同じになる

  生成の設定（workflow_api.json と同じ）
    ベースモデル  : waiIllustriousSDXL_v170.safetensors
    LoRA          : example_style_lora.safetensors（強さ 0 / 0.25 / 0.5 / 0.75 / 1.0）
    seed          : 20261110
    steps         : 28
    sampler       : euler_ancestral（対照として euler）、scheduler: normal
    CFG           : 5.5
    解像度        : 1024 x 1024、batch 1
    CLIP          : CLIPSetLastLayer -2（clip skip 2）
    プロンプト    : <trigger>, masterpiece, best quality, no humans, still life,
                    owl figurine, stack of books, wooden desk, desk lamp, indoors
    ネガティブ    : lowres, worst quality, bad quality, low quality, jpeg artifacts,
                    blurry, text, signature, watermark, logo, 1girl, person

  計測した環境: ComfyUI 0.35.0、PyTorch 2.12.0a0+rocm7.13、GPU は AMD Radeon 8060S。
  1 枚あたり 23.5〜26.0 秒（ComfyUI の execution_start から execution_success まで）。
  同じ環境で euler_ancestral の 5 枚を 2 回生成すると、5 枚とも画素が完全に一致した
  （output_sweep.txt の末尾）。GPU・ドライバ・PyTorch の版が違うと、同じ seed でも
  画素が一致するとは限らない。

図の再生成
----------
  cd .. && python3 figures.py   # params.json・pixel_change_*.json・seed_baseline.json
                                # から SVG を作る

別のベースモデルでの結果（本文の「欠点」の節）
--------------------------------------------
  2026-11-10 に、ckpt_name を Illustrious-XL-v1.0.safetensors にした同じワークフローで
  euler_ancestral の 5 枚を生成した時の、強さ 0 との画素の差は 0.25: 36.16、
  0.5: 40.46、0.75: 44.85、1.0: 42.91 だった（画像は本文に載せていない）。
