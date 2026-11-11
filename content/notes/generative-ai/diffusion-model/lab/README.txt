Diffusion Model ノートの実験ファイル

前提
----
- ComfyUI（v0.35.0 のタグより後のコミット 19e1058 で確認）が http://127.0.0.1:8188 で動いていて、
  models/checkpoints に waiIllustriousSDXL_v170.safetensors がある
    WAI-illustrious-SDXL v17.0  https://civitai.com/models/827184?modelVersionId=2883731
    ライセンス: Fair AI Public License 1.0-SD  https://freedevproject.org/faipl-1.0-sd/
    （生成した画像はライセンスの対象外。LoRA は使っていない。人物は描いていない）
- 本文で引用した ComfyUI のファイル（comfy/samplers.py、comfy/k_diffusion/sampling.py、
  comfy_extras/nodes_custom_sampler.py、comfy/sample.py、latent_preview.py）は、手元のコミットと
  v0.35.0 のタグで同一だった。comfy/model_sampling.py、comfy/latent_formats.py、comfy/supported_models.py は
  手元の方にクラスが足されているが、引用した行は同じ
- 生成を送るスクリプト（comfy.py、wf.py、run.py、summarize.py）は Python 標準ライブラリだけで動く
- 数える側は uv の一時環境で動かした
    uv run --with numpy==2.3.5 --with pillow==12.0.0 python <script>
- 依頼は 1 件ずつ送り、/prompt が返した自分の prompt_id だけを /history で待つ。
  待ち行列の削除やサーバーの設定変更はしない。seed は全て明示している

計測した環境
------------
ComfyUI 0.35.0（コミット 19e1058）、PyTorch 2.12.0a0+rocm7.13、GPU は AMD Radeon 8060S、2026-11-11。
同じ ComfyUI に他の作業の依頼も入っていた。送る直前の待ち行列の長さ、GPU の使用率
（/sys/class/drm/card1/device/gpu_busy_percent）、CPU の load average を、各ログの load_before に残した。
ComfyUI は依頼を 1 件ずつ実行するので、他の依頼は待ち時間を延ばすが、実行時間
（execution_start から execution_success まで）には入らない。

共通の設定（wf.py）
-------------------
  1024x1024、seed 20261111、CFG 5.5、clip skip 2（CLIPSetLastLayer -2）
  プロンプト: masterpiece, best quality, no humans, scenery, lighthouse, cliff, ocean, sunset,
              orange sky, cloud, horizon, waves
  ネガティブ: lowres, worst quality, bad quality, low quality, jpeg artifacts, blurry, text,
              signature, watermark, logo, 1girl, 1boy, person

sigma の列（ComfyUI も GPU も不要）
-----------------------------------
  python3 schedule.py 28 schedule.json                 # 出力は output_schedule.txt
  cd <ComfyUI> && <ComfyUI の python> <このディレクトリ>/check_schedule_comfy.py --cpu
                                                       # 出力は output_check_schedule_comfy.txt
  - schedule.py は comfy/model_sampling.py の ModelSamplingDiscrete と、comfy/samplers.py の
    normal_scheduler・simple_scheduler、comfy/k_diffusion/sampling.py の get_sigmas_karras を NumPy で写した
  - check_schedule_comfy.py は ComfyUI の calculate_sigmas を CPU で呼び、同じ値になることを確かめる

生成（1 件ずつ送る。合計 18 件）
-------------------------------
  python3 run.py trajectory <PNG の保存先>   # 8 件。28 ステップの列を k = 0, 2, 4, 7, 10, 14, 20, 28 で切る
  python3 run.py forward    <PNG の保存先>   # 1 件。描き終えた潜在に sigma のノイズを足す 7 通り＋SaveLatent
  python3 run.py steps      <PNG の保存先>   # 4 件。euler・normal で 8 / 16 / 28 / 50 ステップ
  python3 run.py samplers   <PNG の保存先>   # 2 件。euler_ancestral・normal と dpmpp_2m・karras
  python3 run.py cfg        <PNG の保存先>   # 2 件。CFG 1.0 と 9.0
  python3 run.py rerun      <PNG の保存先>   # 1 件。steps の 28 をもう一度送り、画素の一致を確かめる
  python3 summarize.py > output_runs.txt

  - trajectory: KSamplerSelect(euler) → BasicScheduler(normal, 28) → SplitSigmas(step=k) → SamplerCustom。
    SamplerCustom の出力 0（x_k）に LatentMultiply で 1/sqrt(1 + sigma_k^2) を掛けて VAEDecode、
    出力 1（最後のステップで予測した x0）はそのまま VAEDecode する。k = 0 はモデルを呼ばないので x0 は無い
  - forward: trajectory の k = 28 と同じノードで描き終えた潜在を作り、SplitSigmas を 2 回使って
    長さ 1 の列 [sigma_j]（j = 27, 24, 20, 14, 10, 4, 1）を SamplerCustom に渡す（noise_seed 1）。
    長さ 1 の列ではモデルを呼ばず、noise_scaling（x0 + sigma * ノイズ）の結果がそのまま返る。
    1/sqrt(1 + sigma_j^2) を掛けて VAEDecode。描き終えた潜在は SaveLatent で ComfyUI の出力
    ディレクトリの debimate_diffusion/final_00001_.latent に保存される
  - 各ログ（trajectory_log.json など）に prompt_id・実行秒数・cached_nodes・送る直前の負荷がある

潜在の色の近似
--------------
  uv run --with numpy==2.3.5 --with pillow==12.0.0 python latent_preview.py \
      <ComfyUI の出力>/debimate_diffusion/final_00001_.latent <PNG の保存先>/latent_rgb.png
                                                       # 出力は output_latent.txt

画像
----
  uv run --with pillow==12.0.0 python to_webp.py <PNG の保存先> ../images
  生成した PNG はリポジトリの外に置き、リポジトリには WebP だけを入れた。冒頭の並べた図
  （diffusion_trajectory.webp）も to_webp.py が作る。

図の再生成
----------
  cd .. && uv run --with matplotlib==3.10.7 --with pillow==12.0.0 python figures.py
  # 全体の流れの図は標準ライブラリで SVG を組み、google-chrome の headless で PNG にしてから WebP にする。
  # sigma のグラフと sigma・係数の図は matplotlib。lab/schedule.json・forward_log.json と images/fwd_*.webp
  # を読むので ComfyUI は不要。images/ には WebP だけを置く
