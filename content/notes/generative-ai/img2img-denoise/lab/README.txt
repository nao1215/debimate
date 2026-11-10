img2img Denoise ノートの実験ファイル

前提
----
- ComfyUI（v0.35.0 のタグより後のコミット 19e1058 で確認）が http://127.0.0.1:8188 で動いていて、
  models/checkpoints に waiIllustriousSDXL_v170.safetensors がある
    WAI-illustrious-SDXL v17.0  https://civitai.com/models/827184?modelVersionId=2883731
    ライセンス: Fair AI Public License 1.0-SD  https://freedevproject.org/faipl-1.0-sd/
    （生成した画像はライセンスの対象外。実験 0〜2 は LoRA を使っていない。実験 3 の人物だけ、説明用の
    画風 LoRA example_style_lora.safetensors を models/loras に置いて使う）
- 生成スクリプト（comfy.py、run_sweep.py、run_extra.py、person_lora.py、determinism.py）は Python 標準ライブラリだけで動く
- 数える側は uv の一時環境で動かした（バージョンを固定）
    uv run --with numpy==2.5.4 --with pillow==13.0.0 --with scikit-image==0.26.0 --with scipy==1.18.1 python <script>
- 依頼は 1 枚ずつ送り、/prompt が返した自分の prompt_id だけを /history で待つ。
  待ち行列の削除やサーバーの設定変更はしない。seed は全て明示している

計測した環境
------------
ComfyUI 0.35.0（コミット 19e1058）、PyTorch 2.12.0a0+rocm7.13、GPU は AMD Radeon 8060S、2026-11-10。
同じ ComfyUI に他の作業の依頼も入っていた。送る直前の待ち行列の長さ、GPU の使用率
（/sys/class/drm/card1/device/gpu_busy_percent）、CPU の load average を、各ログの load_before に残した。
ComfyUI は依頼を 1 件ずつ実行するので、他の依頼は待ち時間を延ばすが、実行時間
（execution_start から execution_success まで）には入らない。CPU の負荷は実行時間にも影響した（実験 1 の crisp）。

実験 0: denoise と開始の段（ComfyUI も GPU も不要）
-----------------------------------------------------
  python3 schedule.py 28 schedule.json        # 出力は output_schedule.txt
  - comfy/model_sampling.py の ModelSamplingDiscrete と、comfy/samplers.py の normal_scheduler・
    KSampler.set_steps を NumPy で写した。SDXL（eps 予測）、scheduler=normal、28 ステップ

実験 1: 下絵 3 種 × denoise 7 段
---------------------------------
  python3 make_sketches.py <下絵の保存先>                   # sketch_crisp/blurred/gray.png と shapes.json
  python3 run_sweep.py <下絵の保存先> <PNG の保存先>        # 21 枚。sweep_log.json に prompt_id・秒数・負荷
  python3 run_extra.py control <PNG の保存先>               # 対照: 下絵なしの txt2img 1 枚
  python3 metrics.py <下絵の保存先> <PNG の保存先> metrics.json   # 出力は output_metrics.txt

  - workflow_img2img.json: LoadImage → VAEEncode → KSampler → VAEDecode → SaveImage
    run_sweep.py は LoadImage の image と KSampler の denoise（0.3 / 0.45 / 0.6 / 0.75 / 0.86 / 0.95 / 1.0）
    だけを書き換える
  - 下絵: 1024x1024。壁 (222,216,202)、机 (150,100,60、y=640 から下)、青い長方形 (30,60,220)、
    赤い円 (225,30,30)、黄色の楕円 (240,210,20)。blurred は Pillow の GaussianBlur(24)（標準偏差 24 px）、gray は blurred を
    明るさだけの灰色にした物
  - 設定: seed 20261110、steps 28、CFG 5.5、euler_ancestral、scheduler normal、clip skip 2（CLIPSetLastLayer -2）
    プロンプト: masterpiece, best quality, no humans, still life, red apple, blue book, lemon,
                wooden table, plain wall, indoors
    ネガティブ: lowres, worst quality, bad quality, low quality, jpeg artifacts, blurry, text,
                signature, watermark, logo, 1girl, 1boy, person
  - 対照の txt2img は workflows/control_txt2img.json（EmptyLatentImage 1024x1024、denoise 1.0、他は同じ）
  - 指標の定義は metrics.py の先頭。輪郭の正解は shapes.json から描いた crisp の図形の縁と机の線

実験 2: 全体の描き直しで物が化けるか
-------------------------------------
  python3 run_extra.py morph <PNG の保存先>
  - 1 枚目（workflows/morph_base_txt2img.json）: 金貨の静物を txt2img で 1024x1024
    プロンプト: masterpiece, best quality, no humans, still life, pile of gold coins,
                small wooden treasure chest, wooden table, candle, indoors
  - 描き直し（workflows/morph_redraw.json）: 1 枚目を lanczos で 1.5 倍（1536x1536）にし、VAEEncode して
    KSampler（28 ステップ）。denoise 0.3 / 0.45 / 0.5 / 0.6 / 0.75 は金貨を書かない文面
      masterpiece, best quality, no humans, still life, wooden table, indoors
    0.6 だけ、1 枚目と同じ金貨を書いた文面でも描いた（coins_c_060.png）
  - seed はどれも 20261110。化けたかどうかは、画像を目で見て判定した（正解のラベルは自分で付けた）

実験 3: hires fix の時間と効果
------------------------------
  人物の例は、本記事の説明用に用意した独自の画風 LoRA（example_style_lora.safetensors、強さ 1.0）を
  ベースモデルに当てて描いた。プロンプトの <trigger> は、この LoRA の起動語。再現する時は、手元の画風
  LoRA とその起動語を環境変数で渡す（ログと workflows/hires_fix.json には既定の名前が入る）。

  STYLE_LORA=<loras/ の中のファイル名> STYLE_TRIGGER=<起動語> \
    python3 person_lora.py candidates <PNG の保存先> <seed> ...        # 1 段目だけの候補
  STYLE_LORA=... STYLE_TRIGGER=... \
    python3 person_lora.py hires <PNG の保存先> 20261190 20261193 20261190
  python3 hires_metrics.py <PNG の保存先> hires_metrics.json        # 出力は output_hires.txt

  - 1 段目: 768x1344、28 ステップ、CFG 5.5、euler_ancestral、clip skip 2（workflows/hires_fix.json のノード 1〜9 と 20）
    プロンプト: <trigger>, masterpiece, best quality, rating:general, 1girl, solo, adult woman,
                mature female, 20s, black hair, multicolored hair, streaked hair, long hair,
                parted bangs, open eyes, visible eyes, forehead, sharp eyes, almond-shaped eyes,
                long eyelashes, eye highlights, calm dignified expression, lips, earrings, jewelry,
                nail polish, white blouse, long sleeves, black wide-leg pants, black loafers, full body,
                standing, standing straight, arms at sides, front view, simple background,
                grey background, looking at viewer
    ネガティブ: lowres, worst quality, bad quality, low quality, jpeg artifacts, blurry, bad anatomy,
                bad hands, extra fingers, missing fingers, extra limbs, deformed, text, signature,
                watermark, logo, multiple views, 2girls, multiple girls, character sheet,
                reference sheet, child, loli, aged down, nude, nipples, nsfw, cleavage, midriff, navel,
                underwear, swimsuit, school uniform, serafuku, blunt bangs, hair over eyes,
                hair over one eye, covered eyes, closed eyes, half-closed eyes, sleepy eyes, sultry,
                bare shoulders, off-shoulder, leaning forward
  - 2 段目（hires fix）: 1 段目の画像を lanczos で 1.5 倍（1152x2016）にし、VAEEncode して 20 ステップ・
    denoise 0.45 で描き直す（ノード 10〜14）。LoRA は 2 段目にも同じ強さで掛かる
  - seed 20261190 と 20261193 は、1 段目だけの依頼の後に、2 段目まで通した依頼を送った。間に他の依頼が
    入るので、通した依頼でもキャッシュから出るのはモデルの読み込み（ノード 1。依頼によっては空の潜在の
    ノード 5 も）だけで（hires_log.json の cached_nodes）、hires_chain の秒数は 1 段目と 2 段目の通しの時間。
    3 回目の計測として、seed 20261190 の通した依頼をもう一度送った（画像は 1 回目と同じ）
  - boxes.json は、1 段目の絵を目で見て付けた顔（face）と白い服（shirt）の矩形（768x1344 の座標）。
    白い服の範囲は、20261190 が白いブラウスの左袖のあたり、20261193 は服が黒いので左の白い袖口だけ
  - 生成した人物の絵は、1 段目も hires fix の後も全て目で確かめた。載せる条件は、成人、服を着ている、
    露出や性的な姿勢が無い、1 人、両目が開いて前髪で隠れていない、の全て

  人物の候補で外した絵（全て目で判定。性的に寄った構図は理由だけを書く）
    832x1216・最初の文面（4 枚）: 性的に寄った姿勢 2、2 人並び 1。残った 1 枚は文面が違うので使わない
    832x1216・打ち消しに重み 1.3 を 2 語足した文面（4 枚）: 緑・青緑の蛍光色に転んだ 4（うち 1 枚は性的に寄った構図も）
    832x1216・重みを外した文面（4 枚）: 2 人並び 2、性的に寄った構図 1。残った 1 枚は解像度を変えたので使わない
    768x1344・同じ文面（6 枚）: 性的に寄った構図 2、2 人並び 1、前髪で目が隠れる・目を閉じる 3
    768x1344・目を見せる語を足した文面（8 枚）: 性的に寄った構図 5、目を閉じる 3（1 枚は片目をつぶる大写し）
    768x1344・目の語と構図の語を足した文面（6 枚）: 2 人並び 1、肩の出た服で上からの構図 1。残った 4 枚は
      髪に色の筋が入っていたので、髪を 1 色にする文面に変えた（3 枚で一度撮った実験 3 の画像も消した）
    768x1344・髪を 1 色にした今の文面（4 枚、seed 20261190〜20261193）: 半眼 2（うち 1 枚は透ける服）。
      残った 20261190 と 20261193 を使った

画像
----
  python3 to_webp.py <下絵の保存先> <PNG の保存先> ../images
  生成した PNG はリポジトリの外に置き、リポジトリには WebP だけを入れた。

再現性
------
  STYLE_LORA=... STYLE_TRIGGER=... python3 determinism.py <下絵の保存先> <PNG の保存先> 20261190
                                                            # 出力は output_determinism.txt
  - crisp・denoise 0.6 と、実験 3 の 1 段目（seed 20261190）を同じ設定でもう一度生成し、PNG の画素
    （IDAT を展開したバイト列）が元の画像と完全に一致することを確かめた。GPU・ドライバ・PyTorch のバージョンが
    違うと、同じ seed でも画素が一致するとは限らない
  - 各実験のログ（prompt_id・実行秒数・cached_nodes・送る直前の負荷）は sweep_log.json、control_log.json、
    morph_log.json、hires_log.json。実験 3 の 1 段目は、候補を描いた時の画像とも画素が一致した

図の再生成
----------
  cd .. && uv run --with matplotlib==3.11.2 python figures.py
  # グラフは matplotlib、冒頭の概念図は標準ライブラリだけ。lab/ の JSON を読むので ComfyUI は不要
