深度マップと体型・服の厚みのノートの実験ファイル（2026-11-12 実施）

前提
----
- ComfyUI 0.35.0（/system_stats の comfyui_version）が http://127.0.0.1:8188 で動いていて、次のモデルがある
    models/checkpoints/waiIllustriousSDXL_v170.safetensors
      WAI-illustrious-SDXL v17.0  https://civitai.com/models/827184?modelVersionId=2883731
      （配布のファイル名は WAI-Nsfw-Illustrious-17.safetensors。名前だけ変えて置いた）
      ライセンス: Fair AI Public License 1.0-SD  https://freedevproject.org/faipl-1.0-sd/
      （生成した画像はライセンスの対象外。LoRA は使っていない）
    models/controlnet/xinsir_union_promax_sdxl.safetensors
      https://huggingface.co/xinsir/controlnet-union-sdxl-1.0 の diffusion_pytorch_model_promax.safetensors
      （リビジョン 801a4a3）ライセンス: Apache License 2.0
- 3D モデルは Blender 4.5.15 LTS（https://www.blender.org/）と MPFB 2.0.18
  （https://extensions.blender.org/add-ons/mpfb/、GPL-3.0-or-later）で作る
- 生成のスクリプト（comfy.py、run_depth.py）は Python 標準ライブラリだけで動く
- 計測は uv の一時環境で動かした（バージョンを固定）
    uv run --with rtmlib==0.0.13 --with onnxruntime==1.20.1 --with opencv-python-headless==4.10.0.84 \
           --with numpy==2.1.3 --with tqdm==4.67.1 python body_metrics.py ...
    uv run --with onnxruntime==1.20.1 --with pillow==12.0.0 --with numpy==2.1.3 python clothes_tags.py ...
  rtmlib は初回に OpenMMLab の配布元から YOLOX-x（Human-Art）と RTMPose-x の ONNX を取ってくる。
  clothes_tags.py のモデルは https://huggingface.co/SmilingWolf/wd-eva02-large-tagger-v3 の
  model.onnx と selected_tags.csv を 1 つのディレクトリに置いて渡す
- 依頼は 1 枚ずつ送り、/prompt が返した自分の prompt_id だけを /history で待つ。
  待ち行列の削除やサーバーの設定変更はしない。seed は全て明示している

手順
----
  blender --background --python make_dolls.py -- <作業先>                 # real.blend、anime.blend、dolls.json
  blender --background <作業先>/real.blend  --python render_depth.py -- poses.json <作業先>/depth real
  blender --background <作業先>/anime.blend --python render_depth.py -- poses.json <作業先>/depth anime
      # <3D モデル>_<plain|bulk>_<front|turn>.png の 8 枚
  python3 run_depth.py <作業先>/depth <作業先>/gen compare   # 18 枚
  python3 run_depth.py <作業先>/depth <作業先>/gen sweep     # 16 枚
  python3 run_depth.py <作業先>/depth <作業先>/gen loose     # 10 枚
  uv run ...（前提の版） python body_metrics.py metrics.json <作業先>/gen/*.png <作業先>/depth/*.png
  uv run ...（前提の版） python clothes_tags.py <tagger のディレクトリ> tags.json <作業先>/gen/*.png
  uv run --with pillow==12.0.0 --with matplotlib==3.9.2 --with numpy==2.1.3 \
    python ../figures.py <作業先>/depth <作業先>/gen          # ../images/*.webp

設定
----
- 3D モデル: 成人女性（MPFB の macro: gender 0、age 0.5、他は 0.5。race は asian・caucasian・african に 1/3 ずつ）。anime は脚を長く・頭を小さくする target を足す
  （make_dolls.py の ANIME）。服の厚みは poses.json の _bulk（骨ごとの頂点グループを法線方向に何 m 膨らませるか）
- ポーズ: front（正面）と turn（35 度回した斜め前）。腕は上腕の骨（upperarm）を 32 度下げるだけ
- 1 枚は 832 x 1216、seed 20261112 / 20261113、steps 28、CFG 5.5、euler_ancestral、scheduler normal、
  clip skip 2、txt2img（denoise 1.0）
- 深度マップ: union（SetUnionControlNetType depth）、start 0、end 0.6。強さは compare・loose が 0.7、sweep が 0.4 と 1.0
- プロンプト（鎧、compare と sweep）
    masterpiece, best quality, 1girl, solo, adult woman, long brown hair, ponytail, knight,
    silver plate armor, breastplate, pauldrons, gauntlets, armored boots, dark trousers,
    standing, full body, simple background, white background
- プロンプト（ゆったりした服、loose）
    masterpiece, best quality, 1girl, solo, adult woman, long brown hair, ponytail,
    oversized grey hoodie, baggy cargo pants, white sneakers, standing, full body, simple background, white background
- ネガティブプロンプト: lowres, worst quality, bad quality, low quality, jpeg artifacts, blurry, text, signature,
            watermark, logo, nsfw, nude, child, multiple girls, multiple views

出力
----
- dolls.json: 3D モデルの身長・頭の高さ・頭身・股下の比（Blender の頂点から計算）
- metrics.json: 3D モデルの深度マップと生成した絵の、脚の比・肩より上の比・太ももの幅（body_metrics.py）
- tags.json: 生成した絵の服のタグの確率（clothes_tags.py）
- log_*.json: 1 枚ごとの prompt_id・実行秒数・送る直前の負荷（ComfyUI の待ち行列・GPU の使用率・load average）。
  他の生成と GPU を分け合っていたので、秒数は参考
