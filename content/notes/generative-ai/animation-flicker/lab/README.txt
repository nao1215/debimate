生成した絵をコマにして動かすとちらつく話のノートの実験ファイル（2026-11-12 実施）

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
- 人形は Blender 4.5.15 LTS（https://www.blender.org/）と MPFB 2.0.18
  （https://extensions.blender.org/add-ons/mpfb/、GPL-3.0-or-later）で作る。
  人形そのもの（real.blend）は ../../depth-body-shape/lab/make_dolls.py が作る標準体型の成人女性
- 生成のスクリプト（comfy.py、run_frames.py）は Python 標準ライブラリと Pillow で動く
- 歪める・数える・図を描くスクリプトは uv の一時環境で動かした（バージョンを固定）
    uv run --with opencv-python-headless==4.10.0.84 --with numpy==2.1.3 --with scipy==1.14.1 \
           --with pillow==12.0.0 python warp.py ...
- 依頼は 1 枚ずつ送り、/prompt が返した自分の prompt_id だけを /history で待つ。
  待ち行列の削除やサーバーの設定変更はしない。seed は全て明示している

手順
----
  blender --background --python ../../depth-body-shape/lab/make_dolls.py -- <人形の置き場>
  blender --background <人形の置き場>/real.blend --python render_frames.py -- poses.json <作業先>/pass
      # depth_f0〜f3.png（深度マップ）、gen_f0〜f3.png・uv_f0〜f3.png（表面の座標）、cell_f0〜f3.png
  python3 run_frames.py <作業先>/pass <作業先>/gen redraw      # 1 コマずつ描く。12 枚
  python3 run_frames.py <作業先>/pass <作業先>/gen img2img     # 弱く描き直す denoise 0.45。12 枚
  python3 run_frames.py <作業先>/pass <作業先>/gen img2img60   # denoise 0.6。12 枚
  python3 run_frames.py <作業先>/pass <作業先>/gen img2img75   # denoise 0.75。12 枚
  python3 run_frames.py <作業先>/pass <作業先>/gen sheet       # 並べて 1 枚。3 枚
  for seed in 20261112 20261113 20261114; do for k in gen uv; do for s in 3 20; do
    uv run ...（前提の版） python warp.py <作業先>/gen/redraw_f0_$seed.png <作業先>/pass $k $s <作業先>/gen/warp_${k}_s${s}_$seed
  done; done; done
  uv run ...（前提の版） python measure.py <作業先>/pass <作業先>/gen metrics.json
  uv run ...（前提の版、--with matplotlib==3.9.2 も） python ../figures.py <作業先>/pass <作業先>/gen

設定
----
- 人形: 標準体型の成人女性。服の厚みは poses.json の _bulk（骨ごとの頂点グループを法線方向に何 m 膨らませるか）
- ポーズ: 体を 35 度回した斜め前の立ち姿。右腕は上腕の骨（upperarm_r）を 32 度下げたまま、
  左腕（upperarm_l）を -32 度から 10 度ずつ上げた 4 コマ（f0〜f3）
- カメラ: 平行投影、縦の写る範囲 2.1 m、中心 x 0.16 m・z 0.95 m。1 コマずつは 832 x 1216、並べて 1 枚の 1 コマは 384 x 768
- 共通: seed 20261112 / 20261113 / 20261114、steps 28、CFG 5.5、euler_ancestral、scheduler normal、clip skip 2
- redraw: txt2img（denoise 1.0）。深度マップは union（SetUnionControlNetType depth）、強さ 0.7、start 0、end 0.6
- img2img・img2img60・img2img75: redraw の 1 コマ目を VAE で潜在に戻し、各コマの深度マップで描き直す。
  denoise 0.45・0.6・0.75、深度マップは強さ 0.8、end 0.8。どのコマも元の 1 コマ目から描く（前のコマをつながない）
- sheet: 4 コマの小さい深度マップを横に並べた 1536 x 768 を txt2img で。強さ 0.7、end 0.6
- warp: 表面の座標が gen（Texture Coordinate の Generated）か uv（UV）、流れのならし（ガウスの sigma）3 か 20 画素
- 文面（redraw・img2img）
    masterpiece, best quality, 1girl, solo, adult woman, long brown hair, ponytail, knight,
    silver plate armor, breastplate, pauldrons, gauntlets, armored boots, dark trousers,
    standing, full body, simple background, white background
- 文面（sheet）: 上の「1girl, solo, 」を「multiple views, four views of the same woman, same outfit, same hairstyle, 」に替える
- 打ち消し: lowres, worst quality, bad quality, low quality, jpeg artifacts, blurry, text, signature,
            watermark, logo, nsfw, nude, child, multiple girls, multiple views
  （sheet では最後の multiple girls, multiple views を外す）

出力
----
- metrics.json: 作り方と seed ごとの、ちらつき（pairs はコマ 1→2・2→3・3→4、mean はその平均）と
  腕が付いてきた割合（arm_follow）。img2img_keep は、元の 1 コマ目のあとに img2img の 2〜4 コマ目を続けた場合。
  static_pixels・arm_pixels は 384 x 768 で数えた、止まっている所と腕が新しく入る所の画素数
- log_*.json: 1 枚ごとの prompt_id・実行秒数・送る直前の負荷（ComfyUI の待ち行列・GPU の使用率・load average）。
  他の生成と GPU を分け合っていたので、秒数（1 枚 29〜47 秒）は参考
