生成した立ち絵の背景を BiRefNet で除去する話のノートの実験ファイル（2026-11-12 実施）

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
    models/background_removal/birefnet.safetensors
      https://huggingface.co/Comfy-Org/BiRefNet の background_removal/birefnet.safetensors
      sha256 9ab37426bf4de0567af6b5d21b16151357149139362e6e8992021b8ce356a154。
      https://huggingface.co/ZhengPeng7/BiRefNet（リビジョン e2bf8e4）の model.safetensors と同じファイル。ライセンス: MIT
- 背景除去のノード（LoadBackgroundRemovalModel・RemoveBackground）は ComfyUI 0.35.0 の本体
  （comfy_extras/nodes_bg_removal.py、comfy/bg_removal_model.py、comfy/background_removal/birefnet.json）にある。拡張は要らない
- 深度マップは ../../animation-flicker/lab の render_frames.py が書き出す depth_f0.png
  （Blender で作った標準体型の成人女性の人体モデル、体を 35 度回した立ち姿、832 x 1216）
- run.py と comfyapi.py は Python 標準ライブラリだけで動く
- cutout.py は ComfyUI の venv の Python で動かす（ComfyUI のモデルの読み込みをそのまま使うため）。
  torch 2.12.0a0+rocm7.13.0、Radeon 8060S
- measure.py・figures.py は uv の一時環境で動かした（バージョンを固定）
    uv run --with opencv-python-headless==4.10.0.84 --with numpy==2.1.3 --with scipy==1.14.1 \
           --with pillow==12.0.0 --with matplotlib==3.9.2 python ...
- 依頼は 1 枚ずつ送り、/prompt が返した自分の prompt_id だけを /history で待つ。
  待ち行列の削除やサーバーの設定変更はしない。seed は全て明示している

手順
----
  python3 run.py <深度マップ> <作業先>/gen gen        # 18 枚（背景 3 × 髪 2 × seed 3）
  python3 run.py <深度マップ> <作業先>/gen node       # ComfyUI のノードのマスク（<名前>_node.png）
  python3 run.py <深度マップ> <作業先>/gen rgba       # 透過 PNG（rgba_green_brown_20261115.png）
  <ComfyUI の venv>/bin/python -I cutout.py <ComfyUI のディレクトリ> <作業先>/gen   # _plain.png と _imagenet.png
  python measure.py <作業先>/gen metrics.json
  python ../figures.py <作業先>

設定
----
- 描き方: steps 28、CFG 5.5、euler_ancestral、scheduler normal、clip skip 2、832 x 1216 の空の潜在から描く。
  深度マップは union depth、強さ 0.7、end 0.6。seed 20261115 / 20261116 / 20261117
- プロンプト（{hair} は brown hair か silver hair、{back} は white background・grey background・green background）
    masterpiece, best quality, 1girl, solo, adult woman, very long {hair}, floating hair,
    navy blue jacket, brown leather belt, black trousers, brown boots,
    standing, full body, simple background, {back}
- ネガティブプロンプト: lowres, worst quality, bad quality, low quality, jpeg artifacts, blurry, text, signature,
            watermark, logo, nsfw, nude, child, multiple girls, multiple views, gradient background, scenery
- マスクの前処理: 1024 x 1024 に縦横比を無視して縮める（bicubic）。ComfyUI のノードは正規化をしない
  （birefnet.json の image_mean 0・image_std 1）。BiRefNet の作者の推論例（Hugging Face の README の extract_object）は
  ImageNet の平均 (0.485, 0.456, 0.406) と標準偏差 (0.229, 0.224, 0.225) で正規化する。cutout.py は平均と標準偏差だけを変える。縮め方（README は torchvision の Resize、ComfyUI は bicubic）、
  半精度での実行、出力の戻し方は ComfyUI のままで、作者の推論例とは揃えていない

出力
----
- metrics.json: 絵ごとの背景の色（back_rgb）と、マスクごと（node・plain・imagenet）の数。項目は measure.py の先頭に書いた
- log_gen.json・log_node.json: 1 枚ごとの prompt_id・実行秒数・送る直前の負荷（ComfyUI の待ち行列・GPU の使用率・
  load average）。他の作業と GPU を分け合っていたので、秒数は参考
