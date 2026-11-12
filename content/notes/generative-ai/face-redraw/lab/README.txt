全身の立ち絵で、顔だけを拡大して描き直す話のノートの実験ファイル（2026-11-12〜13 実施）

前提
----
- ComfyUI 0.35.0（/system_stats の comfyui_version。手元は v0.35.0 の 26 コミット先の master、19e1058f）が http://127.0.0.1:8188 で動いていて、次のモデルがある
    models/checkpoints/waiIllustriousSDXL_v170.safetensors
      WAI-illustrious-SDXL v17.0  https://civitai.com/models/827184?modelVersionId=2883731
      （配布のファイル名は WAI-Nsfw-Illustrious-17.safetensors。名前だけ変えて置いた）
      ライセンス: Fair AI Public License 1.0-SD  https://freedevproject.org/faipl-1.0-sd/
      （生成した画像はライセンスの対象外。LoRA は使っていない）
    models/controlnet/xinsir_union_promax_sdxl.safetensors
      https://huggingface.co/xinsir/controlnet-union-sdxl-1.0 の diffusion_pytorch_model_promax.safetensors
      （リビジョン 801a4a3）ライセンス: Apache License 2.0
    models/detection/mediapipe_face_fp32.safetensors
      https://huggingface.co/Comfy-Org/mediapipe（リビジョン f787efc）の detection/mediapipe_face_fp32.safetensors
      sha256 a98c4806081d40eba35102a0f6dc0000c2e1388b72cf24e691703d0605bd888a。ライセンス: Apache License 2.0
      （元は https://github.com/google-ai-edge/mediapipe の Face Landmarker）
- 顔検出のノード（LoadMediaPipeFaceLandmarker・MediaPipeFaceLandmarker）は ComfyUI 0.35.0 の本体
  （comfy_extras/nodes_mediapipe.py）にある。拡張は要らない
- 比べに使った face_yolov8n.pt は https://huggingface.co/Bingsu/adetailer（リビジョン 53cc19d）の face_yolov8n.pt。
  sha256 70b640f8f60b1cf0dcc72f30caf3da9495eb2fb6509da48c53374ad6806e6a9c。
  動かす ultralytics は AGPL-3.0。ComfyUI には入れず、uv の一時環境で動かした
    uv run --python 3.12 --with ultralytics==8.3.40 --with torch==2.5.1+cpu --with torchvision==0.20.1+cpu \
           --index https://download.pytorch.org/whl/cpu --index-strategy unsafe-best-match python detect_yolo.py ...
- 深度マップは ../../animation-flicker/lab の render_frames.py が書き出す depth_f0.png
  （Blender で作った標準体型の成人女性の 3D モデル、体を 35 度回した立ち姿、832 x 1216）
- run.py と comfyapi.py は Python 標準ライブラリだけで動く。detect.py は ComfyUI の venv の Python で動かす
  （torch 2.12.0a0+rocm7.13.0、Radeon 8060S）
- measure.py・figures.py は uv の一時環境で動かした（バージョンを固定）
    uv run --python 3.12 --with opencv-python-headless==4.10.0.84 --with numpy==2.1.3 --with scikit-image==0.24.0 \
           --with pillow==12.0.0 --with matplotlib==3.9.2 python ...
- 依頼は 1 枚ずつ送り、/prompt が返した自分の prompt_id だけを /history で待つ。
  待ち行列の削除やサーバーの設定変更はしない。seed は全て明示している

手順
----
  python3 run.py <深度マップ> <作業先> base                 # 全身の立ち絵 5 枚（<作業先>/gen/base_<seed>.png）
  <ComfyUI の venv>/bin/python -I detect.py <ComfyUI のディレクトリ> <作業先>/detect.json <作業先>/gen/base_*.png
  python detect_yolo.py <face_yolov8n.pt> <作業先>/detect_yolo.json <作業先>/gen/base_*.png
  python3 run.py <深度マップ> <作業先> face                 # 顔だけ描き直す（5 枚 × 6 条件）
  python3 run.py <深度マップ> <作業先> hires                # 全体を 2 倍で描き直す
  python3 run.py <深度マップ> <作業先> big                  # 最初から 2 倍で描く
  python measure.py <作業先> metrics.json
  python ../figures.py <作業先>
  顔検出は、背景除去のノート（../../background-removal/lab）で描いた 18 枚にも同じ detect.py・detect_yolo.py を通した
  <ComfyUI の venv>/bin/python -I detect_crop.py <ComfyUI のディレクトリ> <作業先> <背景除去のノートの gen> detect_crop.json
                                                          # 顔の周りで切り抜いてから short で検出する
  （detect.json・detect_yolo.json の white_*・grey_*・green_*）

設定
----
- 描き方: steps 28、CFG 5.5、euler_ancestral、scheduler normal、clip skip 2、832 x 1216 の空の潜在から描く。
  深度マップは union depth、強さ 0.7、end 0.6。seed 20261118〜20261122
- プロンプト（全身と同じ）
    masterpiece, best quality, 1girl, solo, adult woman, long brown hair, parted bangs, brown eyes,
    looking at viewer, open eyes, navy blue jacket, brown leather belt, black trousers, brown boots,
    standing, full body, simple background, white background
- 顔用のプロンプト: 上から構図の語（brown leather belt 以降の服と standing, full body）を外し、portrait, close-up, face を足した
- ネガティブプロンプト: lowres, worst quality, bad quality, low quality, jpeg artifacts, blurry, text, signature,
    watermark, logo, nsfw, nude, child, multiple girls, multiple views, gradient background, scenery,
    hair over eyes, closed eyes, half-closed eyes
- 顔の描き直し: MediaPipe の full（しきい値 0.5）の顔の枠の長い辺 × crop_factor（3.0。比べに 1.5）の正方形を切り抜き、
  1024 x 1024 に拡大（lanczos）、img2img（同じ seed・steps 28・denoise 0.3 / 0.45 / 0.6）、area で元の大きさへ縮め、
  顔の枠を 1.3 倍に広げてぼかした矩形のマスクで貼り戻す。ControlNet は掛けない
- 全体の描き直し（hires fix）: lanczos で 1664 x 2432 に拡大し、denoise 0.45 の img2img。ControlNet は掛けない
- 最初から 2 倍: 1664 x 2432 の空の潜在から、同じ設定で描く。5 枚とも人物が 2 人以上になった（目で数えた。
  20261122 は頭が 3 つ）。そのため measure.py は時間だけを記録する

出力
----
- metrics.json: 絵ごとの数。項目は measure.py の先頭に書いた
- detect.json・detect_yolo.json: 顔の枠と確信度。本文の「顔に当たった」は、face_yolov8n の枠との IoU が 0.3 以上
- detect_crop.json: 顔の周りで切り抜いた時に short が顔を拾った枚数
- log_*.json: 1 枚ごとの prompt_id・実行秒数・送る直前の負荷（ComfyUI の待ち行列・GPU の使用率・load average）。
  他の作業と GPU を分け合っていたので、秒数は参考。log_face.json には切り抜いた正方形（crop）と貼り戻すマスク（mask）も入れた
