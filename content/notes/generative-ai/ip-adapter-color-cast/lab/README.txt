IP-Adapter の参照で色が転ぶ話のノートの実験ファイル（2026-11-12 実施）

前提
----
- ComfyUI 0.35.0（/system_stats の comfyui_version）が http://127.0.0.1:8188 で動いていて、次のモデルと拡張がある
    models/checkpoints/waiIllustriousSDXL_v170.safetensors
      WAI-illustrious-SDXL v17.0  https://civitai.com/models/827184?modelVersionId=2883731
      （配布のファイル名は WAI-Nsfw-Illustrious-17.safetensors。名前だけ変えて置いた）
      ライセンス: Fair AI Public License 1.0-SD  https://freedevproject.org/faipl-1.0-sd/
      （生成した画像はライセンスの対象外。LoRA は使っていない）
    models/controlnet/xinsir_union_promax_sdxl.safetensors
      https://huggingface.co/xinsir/controlnet-union-sdxl-1.0 の diffusion_pytorch_model_promax.safetensors
      （リビジョン 801a4a3）ライセンス: Apache License 2.0
    models/ipadapter/ip-adapter-plus_sdxl_vit-h.safetensors
      https://huggingface.co/h94/IP-Adapter（リビジョン 018e402）の sdxl_models/ip-adapter-plus_sdxl_vit-h.safetensors
      ライセンス: Apache License 2.0
    models/clip_vision/CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors
      同じリポジトリの models/image_encoder（OpenCLIP の ViT-H-14）
    custom_nodes/ComfyUI_IPAdapter_plus（https://github.com/cubiq/ComfyUI_IPAdapter_plus、コミット a0f451a、GPL-3.0）
- 深度マップは ../../animation-flicker/lab の render_frames.py が書き出す depth_f0.png
  （標準体型の成人女性の 3D モデル、体を 35 度回した立ち姿、832 x 1216）
- 生成のスクリプト（comfy.py、run.py）は Python 標準ライブラリだけで動く
- 参照を作る・数えるスクリプトは uv の一時環境で動かした（バージョンを固定）
    uv run --with opencv-python-headless==4.10.0.84 --with numpy==2.1.3 --with scipy==1.14.1 \
           --with pillow==12.0.0 python measure.py ...
- 依頼は 1 枚ずつ送り、/prompt が返した自分の prompt_id だけを /history で待つ。
  待ち行列の削除やサーバーの設定変更はしない。seed は全て明示している

参照の絵
--------
run.py の workflow（参照なしの 1 段目）と同じ条件で、seed とプロンプトだけを変えて描いた。
  銀の参照（ref_plain/source.png）: seed 20261123、プロンプトは run.py の PROMPT のまま
  青い陣羽織の参照（ref/source.png）: seed 20261122、PROMPT の「silver plate armor,」の後に
    「red cape, blue tabard, gold trim,」を足した
  人物のいない参照（ref_blank/）: 1216 x 1216 の真っ白（255, 255, 255）と真っ緑（0, 177, 64）

手順
----
  python make_refs.py <作業先>/ref_plain/source.png <作業先>/ref_plain   # 白・黒・緑・透明の参照と mask.png
  python make_refs.py <作業先>/ref/source.png <作業先>/ref
  python3 run.py <深度マップ> <作業先>/ref <作業先>/gen grid                       # 42 枚
  cp <作業先>/gen/s?_none_*.png <作業先>/gen_plain/                                 # 参照なしは同じ絵を使う
  python3 run.py <深度マップ> <作業先>/ref_plain <作業先>/gen_plain grid           # 36 枚
  python3 run.py <深度マップ> <作業先>/ref_plain <作業先>/gen_plain weight white,green  # 12 枚
  cp <作業先>/gen/s1_none_*.png <作業先>/gen_blank/
  python3 run.py <深度マップ> <作業先>/ref_blank <作業先>/gen_blank first white,green  # 12 枚
  python measure.py <深度マップ> <作業先>/ref <作業先>/gen metrics_color.json
  python measure.py <深度マップ> <作業先>/ref_plain <作業先>/gen_plain metrics_plain.json
  python measure.py <深度マップ> <作業先>/ref_blank <作業先>/gen_blank metrics_blank.json
  uv run ...（--with matplotlib==3.9.2 も） python ../figures.py <作業先>

style transfer precise の割り当ては、拡張のコード（IPAdapterPlus.py の ipadapter_execute と CrossAttentionPatch.py の
ipadapter_attention）で確認した。SDXL では weight を {3: w, 6: w} とし、3 番では参照を打ち消す側（uncond）に回す。
番号は ComfyUI の transformer_index で、6 番は up_blocks.0.attentions.1、3 番は down_blocks.2.attentions.1 だった。

透明な参照の読まれ方は、LoadImage → SaveImage だけの流れに clear_black.png と clear_white.png（青い陣羽織の参照）と、
ref_plain/clear_black.png（銀の参照。図の中央に使った read_clear_black.png）を通して確かめた。
保存し直した絵は RGB で、透明だった画素は (0, 0, 0) と (255, 255, 255) になった（人物の画素は同じ）。

設定
----
- 共通: steps 28、CFG 5.5、euler_ancestral、scheduler normal、clip skip 2、seed 20261112 / 20261113 / 20261114
- 1 段目: 832 x 1216 の空の潜在から描く（txt2img）。深度マップは union depth、強さ 0.7、end 0.6
- 2 段目: 参照なしの 1 段目の絵を VAE で潜在に戻し、denoise 0.45 で描き直す（img2img）。深度マップは強さ 0.8、end 0.8
- IP-Adapter: IPAdapterAdvanced、weight 0.6（weight の計画では 0.3・0.9）、start_at 0、end_at 1、
  combine_embeds concat、embeds_scaling V only。weight_type は style transfer precise か linear
- 参照は 1216 x 1216 の正方形（縦長の絵の左右に背景を足した）。人物は全体の画素の約 15%（銀）・16%（青い陣羽織）
- プロンプト
    masterpiece, best quality, 1girl, solo, adult woman, long brown hair, ponytail, knight,
    silver plate armor, breastplate, pauldrons, gauntlets, armored boots, dark trousers,
    standing, full body, simple background, white background
- ネガティブプロンプト: lowres, worst quality, bad quality, low quality, jpeg artifacts, blurry, text, signature,
            watermark, logo, nsfw, nude, child, multiple girls, multiple views

出力
----
- metrics_plain.json（銀の参照）、metrics_color.json（青い陣羽織の参照）、metrics_blank.json（人物のいない参照）:
  絵ごとの back_dE（背景の平均色と白の差）、chroma（人物の彩度 C* の平均）、body_lab・back_lab（平均の L*a*b*）、
  body_dE（人物の平均色と参照の人物の平均色の差）。名前は <段>_<背景>_<型>[_w<重み x 10>]_<seed>。
  s?_none は参照なし。人物と背景の範囲は measure.py の先頭に書いた
- log_*.json: 1 枚ごとの prompt_id・実行秒数・送る直前の負荷（ComfyUI の待ち行列・GPU の使用率・load average）。
  他の生成と GPU を分け合っていたので、秒数（1 枚 29〜70 秒）は参考
