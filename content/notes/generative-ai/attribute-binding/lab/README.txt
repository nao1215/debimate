Attribute Binding ノートの実験ファイル

注意: 画風 LoRA を当てた条件（s_ で始まる条件）で使った LoRA（example_style_lora.safetensors）は、
本記事の説明用に用意した独自の画風 LoRA です。プロンプトの <trigger> は、この LoRA の起動語です。
再現する時は、環境変数 STYLE_LORA と STYLE_TRIGGER に、手元の画風 LoRA のファイル名と起動語を入れてください。

使ったモデルと道具（2026-11-10）
--------------------------------
  ベースモデル : waiIllustriousSDXL_v170.safetensors（WAI-illustrious-SDXL v17.0）
                 https://civitai.com/models/827184?modelVersionId=2883731
                 SHA-256 f116b0c78ff441467b0cdc8f1936e1ed18ea31e9997c7b132b1b8db533f0bd04
                 ライセンス: Illustrious License（Fair AI Public License 1.0-SD）
  画風 LoRA    : example_style_lora.safetensors（強さ 0.75。LoraLoader の strength_model と strength_clip の両方）
  ComfyUI      : v0.35.0（commit 19e1058f4c445ef74047e77a23f9ca7684c1e4b6）
                 PyTorch 2.12.0a0+rocm7.13、GPU は AMD Radeon 8060S
  領域の切り出し: CIDAS/clipseg-rd64-refined（Apache-2.0、
                 revision 999e0328d9e10b484360c477313983f9afdd7050）
  タグの推定    : SmilingWolf/wd-vit-tagger-v3（Apache-2.0、
                 revision 7f6b584d0bd3f55c4531f14ba3d4761b2bccdc0f）
  解析の環境    : ComfyUI の Python 環境（Python 3.12、transformers 5.17.0、
                 onnxruntime 1.31.0、NumPy 2.4.3、Pillow 12.2.0）を CPU で使った

実験 A: 色の語を 1 つ変えて text encoder の出力を比べる
------------------------------------------------------
  python clip_mix.py <ComfyUI のディレクトリ> <チェックポイント> clip_mix.json

  - ComfyUI のライブラリ（comfy）でチェックポイントの text encoder だけを CPU に読む。
    ComfyUI のサーバーには触れない
  - 結果は output_clip_mix.txt と clip_mix.json（figures.py が図に使う）

実験 1〜3 と余談: seed を変えて生成し、色と人数を数える
（照明の語の条件 *_light_* も生成・集計したが、本文には載せていない。照明の語の色かぶりは
  Prompt Weighting のノートの実験 3 で扱っている）
------------------------------------------------
  前提: ComfyUI が http://127.0.0.1:8188 で動いていて、models/checkpoints に
        waiIllustriousSDXL_v170.safetensors、models/loras に画風 LoRA がある

  STYLE_LORA=<LoRA のファイル名> STYLE_TRIGGER=<起動語> \
    python3 gen.py <PNG の保存先> <条件名> <seed の数>   # 標準ライブラリだけ
  python measure.py <PNG の保存先> measure.json        # CLIPSeg と WD tagger（CPU）
  python3 summarize.py measure.json labels.json summary.json
  python3 to_webp.py <PNG の保存先> ../images <項目> ...

  - gen.py は依頼を 1 枚ずつ送り、自分の prompt_id の完了を待ってから次を送る。
    待ち行列の削除や中断はしない。seed は 1000 から順に明示する
  - 条件とプロンプトの全文は gen.py の CONDITIONS にある。生成した枚数は次の通り
      ベースモデルだけ（1024 x 1024）
        eye_none / eye_aqua / eye_aqua_rev / eye_aqua_concat : 各 12 枚（seed 1000〜1011）
        tone_two / tone_parts                               : 各 6 枚（本文には載せていない）
      画風 LoRA あり（立ち絵の文面、既定は 768 x 1344）
        s_eye_none / s_eye_aqua                             : 各 12 枚
        s_rep_none / s_rep_aqua                             : 各 12 枚（髪を単色にする打ち消しと、
                                                              目をはっきり描く語を足した文面）
        s_rep_ar_832x1216 / s_rep_ar_1024x1024              : 各 6 枚（768 x 1344 は s_rep_none の
                                                              seed 1000〜1005 を使う）
        s_rep_light_sunset / s_rep_light_night              : 各 4 枚
        s_rep_tone_two / s_rep_tone_parts                   : 各 6 枚
        s_ar_832x1216 / s_ar_1024x1024                      : 各 6 枚（768 x 1344 は s_eye_none の
                                                              seed 1000〜1005 を使う）
        s_light_sunset / s_light_night                      : 各 4 枚（seed 1000〜1003）
        s_tone_two / s_tone_parts                           : 各 6 枚
  - labels.json は、本記事の執筆時に全ての画像を 1 枚ずつ目で見て付けたラベル。
    eye_aqua_concat/1007 は、1 回目の目視で「色移りなし」としたが、機械の判定と食い違ったので
    拡大して見直し、前髪の細い青緑の光沢を確認して直した
  - 結果は output_summary.txt（集計）、summary.json、measure.json（1 枚ごとの値）。
    髪の色移りの機械の判定は目視と 96 枚中 89 枚が一致した。食い違った 7 枚は全て画風 LoRA の
    条件で、髪の領域に重なった水色のシャツ・青い背景・黒髪の青みのある艶を青緑と数えた誤り。
    人数は判定した 78 枚全てで一致した。two-tone の左右の塗り分けの機械の判定（服の領域を中心で左右に
    割って黒の割合を比べる）は、目視と 12 枚中 9 枚しか一致しなかったので、本文は目視の値を使う

  生成の設定（workflow_api.json。条件ごとに変えるのはプロンプト・解像度・LoRA の有無だけ）
    steps 28、sampler euler_ancestral、scheduler normal、CFG 5.5、denoise 1.0
    CLIPSetLastLayer -2、batch 1
    画風 LoRA の条件は、CheckpointLoaderSimple の後に LoraLoader（strength_model と
    strength_clip を 0.75）を挟み、プロンプトの先頭に起動語を置く

再現の確認
----------
  eye_aqua と s_eye_aqua の seed 1000 を同じ環境でもう一度生成すると、2 枚とも 1 画素も違わない
  画像になった（途中で ComfyUI が再起動した前後をまたいでも同じ）。GPU・ドライバ・PyTorch の
  バージョンが違うと、同じ seed でも画素が一致するとは限らない。

本文に載せた画像
----------------
  冒頭の 2 枚の並び、実験 2 の立ち絵と顔の切り抜きは、集計に使った画像をそのまま WebP にした。
    python3 to_webp.py <PNG の保存先> ../images "eye_none/1000+eye_aqua/1000%560" \
      s_rep_none/1000 s_rep_aqua/1000 "s_rep_none/1000@244,10,280,240" "s_rep_aqua/1000@244,10,280,240"
  「画像の色を数える方法」の図は、measure.py と同じ手順で eye_aqua の seed 1000 を測って描いた
  （CLIPSeg・matplotlib・SciPy を使う）。
    python measure_figure.py <PNG の保存先> eye_aqua 1000 ../images/attribute-binding_measure.webp

  以前の版では、s_rep_none と s_rep_aqua の seed 1000 を、hires.py で仕上げて載せていた（1.5 倍に拡大し、同じプロンプト・
  LoRA・seed で denoise 0.4・20 ステップの img2img）。集計には仕上げ前の画像を使っている。

    STYLE_LORA=... STYLE_TRIGGER=... python3 hires.py <PNG の保存先> s_rep_none 1000
    STYLE_LORA=... STYLE_TRIGGER=... python3 hires.py <PNG の保存先> s_rep_aqua 1000
    python3 to_webp.py <PNG の保存先> ../images hires/s_rep_none_1000 hires/s_rep_aqua_1000 \
      "hires/s_rep_none_1000@316,20,520,520" "hires/s_rep_aqua_1000@316,20,520,520"

人物の画像について
------------------
  人物は成人で、服を着た姿に限った。プロンプトで体の部位を強調する語は書いていない。
  生成した全ての画像を目で確かめた。露出のある絵として捨てた枚数は 0 枚。
  s_eye_none の 12 枚のうち 7 枚は目を閉じていた。髪の色移りの判定には使い、本文には載せていない。
  目の色の語を足した組では、全ての絵で目が開いていた。
  本文に載せる人物の絵は、両目が開いて見え、髪が単色（色移りの結果を見せる絵を除く）で、
  スリットや性的な構図の無い絵だけにした。この条件に合う絵が無かった縦横比と照明の実験は、
  絵を載せずにグラフと表で示している。

最初に試した条件（本文には使っていない）
----------------------------------------
  ベースモデルだけの two-tone（6 枚ずつ）は、two-tone の 6 枚中 4 枚が体の左右で白と黒に
  塗り分けられ（目視）、部位ごとに書いた 6 枚は全て上着が黒・スカートが白だった。
  服の領域を左右に割って黒の割合を比べる機械の判定は、目視と 12 枚中 9 枚しか一致しなかった。
  この結果は output_summary_v1.txt と measure_v1.json にある。

  画風 LoRA の条件は、前髪で目が隠れる絵や、顔の大写しばかりになる文面を避けるため、文面を
  作り直している。作り直す前の画像は集計に入れていない。

図の再生成
----------
  cd .. && python3 figures.py   # 概念図（SVG を Chrome で PNG にする）とグラフを WebP で作る
