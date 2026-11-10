ControlNet ノートの実験ファイル

前提
----
- ComfyUI（v0.35.0 のタグより後のコミット 19e1058。ControlNet に関わる comfy/controlnet.py・
  comfy/cldm/control_types.py・comfy_extras/nodes_controlnet.py・comfy/samplers.py はタグと同じ内容、
  nodes.py の ControlNetApplyAdvanced と model_sampling.py の percent_to_sigma も同じ）が
  http://127.0.0.1:8188 で動いていて、次のモデルがある
    models/checkpoints/waiIllustriousSDXL_v170.safetensors
      WAI-illustrious-SDXL v17.0  https://civitai.com/models/827184?modelVersionId=2883731
      ライセンス: Fair AI Public License 1.0-SD  https://freedevproject.org/faipl-1.0-sd/
      （生成した画像はライセンスの対象外。LoRA は使っていない）
    models/controlnet/xinsir_union_promax_sdxl.safetensors
      https://huggingface.co/xinsir/controlnet-union-sdxl-1.0 の diffusion_pytorch_model_promax.safetensors
      （リビジョン 801a4a3、sha256 9fae2e50cb431bfcbe05822b59ec2228df545ef27f711dea8949e9f4ed9f7cdc）
      ライセンス: Apache License 2.0
    models/controlnet/xinsir_openpose_sdxl.safetensors
      https://huggingface.co/xinsir/controlnet-openpose-sdxl-1.0 の diffusion_pytorch_model.safetensors
      （リビジョン 23f966c、sha256 b8524e557a7df60d081f5d4a0eb109967d107df217943bf88c2d99b9ebcc06c5）
      ライセンス: Apache License 2.0
- 人形は Blender 4.5.15 LTS（https://www.blender.org/）と MPFB 2.0.18（https://extensions.blender.org/add-ons/mpfb/、
  GPL-3.0-or-later）で作る。MPFB の人体と骨組み（game_engine）を使い、手足の位置は IK で置く
- 生成のスクリプト（comfy.py、run_controlnet.py）は Python 標準ライブラリだけで動く
- 画像の処理と計測は uv の一時環境で動かした（バージョンを固定）
    uv run --with pillow==12.0.0 python draw_openpose.py ...
    uv run --with opencv-python-headless==4.10.0.84 --with numpy==2.1.3 python make_canny.py ...
    uv run --with rtmlib==0.0.13 --with onnxruntime==1.20.1 --with opencv-python-headless==4.10.0.84 \
           --with numpy==2.1.3 --with tqdm==4.67.1 python pose_metrics.py ...
  rtmlib は初回に OpenMMLab の配布元から YOLOX-x（Human-Art）と RTMPose-x の ONNX を取ってくる
- 依頼は 1 枚ずつ送り、/prompt が返した自分の prompt_id だけを /history で待つ。
  待ち行列の削除やサーバーの設定変更はしない。seed は全て明示している

手順
----
  blender --background --python make_mannequin.py -- <作業先>/mannequin.blend
  blender --background <作業先>/mannequin.blend --python render_poses.py -- poses.json <条件の画像の保存先>
      # depth_<ポーズ>.png（奥行き）と keypoints.json（OpenPose の 18 点の画面上の座標）
  python3 draw_openpose.py <条件の画像の保存先>/keypoints.json <条件の画像の保存先>          # openpose_<ポーズ>.png
  python3 draw_openpose.py <条件の画像の保存先>/keypoints.json <条件の画像の保存先> --thin  # 細い骨格
  python3 make_canny.py <条件の画像の保存先>                                                 # canny_<ポーズ>.png
  python3 run_controlnet.py <条件の画像の保存先> <PNG の保存先> compare     # 18 枚
  python3 run_controlnet.py <条件の画像の保存先> <PNG の保存先> dedicated   # 3 枚
  python3 run_controlnet.py <条件の画像の保存先> <PNG の保存先> sweep       # 6 枚
  python3 run_controlnet.py <条件の画像の保存先> <PNG の保存先> thin        # 2 枚
  python3 run_controlnet.py <条件の画像の保存先> <PNG の保存先> canny       # 3 枚
  python3 pose_metrics.py <条件の画像の保存先>/keypoints.json <PNG の保存先> pose_metrics.json
  python3 control_steps.py                                                  # 出力は output_control_steps.txt
  python3 to_webp.py <条件の画像の保存先> <PNG の保存先> ../images

設定
----
- 1 枚は 832 x 1216、seed 20261111 / 20261112、steps 28、CFG 5.5、euler_ancestral、scheduler normal、
  clip skip 2（CLIPSetLastLayer -2）、txt2img（EmptyLatentImage、denoise 1.0）
- 文面（3 ポーズ共通の前半 + ポーズごとの後半）
    masterpiece, best quality, 1boy, solo, adult man, short black hair, white shirt, navy jacket,
    black trousers, brown boots, holding a long wooden staff, full body, simple background, white background,
    raise:    raising staff overhead with right hand, arm raised high, left hand on hip
    lunge:    lunging forward, thrusting staff forward with both hands, from side
    lookback: from behind, looking back over shoulder, staff resting on shoulder
  打ち消し: lowres, worst quality, bad quality, low quality, jpeg artifacts, blurry, text, signature,
            watermark, logo, nsfw, nude, child, 1girl, multiple boys, multiple views, extra arms
- 条件（compare）
    骨格: union（SetUnionControlNetType openpose）、strength 1.0、start 0、end 1.0
    奥行き: union（SetUnionControlNetType depth）、strength 0.7、start 0、end 0.6
- dedicated: 骨格の専用モデル xinsir_openpose_sdxl、strength 1.0、end 1.0
- sweep: 突き（lunge）の奥行き。strength 0.3 / 0.5 / 1.0（end 0.6）と end 0.2 / 0.4 / 1.0（strength 0.7）
- thin: comfyui_controlnet_aux の既定の太さ（棒の半幅 4 px = 太さ約 8 px、点の半径 4 px）で描いた骨格。他は compare の骨格と同じ
- canny: 人形の奥行きから作った輪郭。union（canny/lineart/anime_lineart/mlsd）、strength 0.7、end 0.6

計測
----
pose_metrics.py は、生成した絵から姿勢を検出し（rtmlib の Body、performance）、人形の 12 関節
（肩・肘・手首・腰・膝・足首）とのずれを、人形の背丈（首から両足首の中点まで）に対する % で出す。
左右の取り違えは問わない。人形の奥行きの画像そのものも同じ方法で数え（*_mannequin）、
検出器が見落とす分の目安にした（output_pose_metrics.txt）。
