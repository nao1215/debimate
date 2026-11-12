# 完了のチェックリスト: generative-ai/face-redraw（2026-11-13）

| 項目 | 結果（数値・回数・URL など） |
|---|---|
| Skill ツールで debimate-visual-notes を起動した | はい |
| 読解の確認（初学者役の別エージェントが上から読む）の回数と、最後の判定（A/B/C）と残った指摘 | 2 回、どちらも B。1 回目の指摘（img2img・denoise・seed・検出枠・hires fix の定義不足、実験の条件が結果より後、線の太さの図と本文の食い違い、手順の図に大きさが無い、コードの前にノードの流れが無い、6 条件の内訳、時間に何が含まれるか、同じ見出し 2 回）は全て直した。2 回目の指摘（手順の図の赤とオレンジの食い違い、描き直しが速い理由、線の太さの節の順、細くなる理由の 1 文、seed を caption に、表示する大きさの定義、表情差分、HTTP API、Mermaid にプロンプトの入口、full が 5 枚とも当たったか、ぼかしの幅、RGB の差の物差し、1.5 倍の条件の扱い）も全て直した。3 回目の読解の確認はしていない |
| 事実確認（一次資料と照合。別エージェントか自分か）と、直した件数 | 別エージェント 1 回。metrics.json・detect*.json・log_*.json から再計算、ComfyUI v0.35.0（nodes_mediapipe.py・samplers.py）、ADetailer（3a599f5）の args.py・README・ui.py・common.py、Impact Pack（ed1bd80）の impact_pack.py、SDXL の論文 2.3・2.5 節、Wikipedia の CIE76 と照合。反証 2 件（1.5 倍の条件の差は 3 倍と「ほぼ同じ」ではない、full 0.1 で顔に当たったのは 23 でなく 22 枚。IoU 0.3 以上を当たりと定義した）、本文の食い違い 1 件（結びの「0.45 以上で」を 0.3 からに）、裏付け不足 2 件（切り抜いてからの short の検出を lab/detect_crop.py に入れた、人物が増える話を今回の 5 枚の観察に限定し A1111 の wiki にリンク）、補足 10 件（ぼかしの幅、hires fix のリンク、ADetailer だけの話に限定、拡張と値が違うこと、Mermaid のノード名、8〜9 画素、1〜2.5 割、README に ComfyUI の commit、fr_big の alt、both の検出器）、計 16 件を直した。lab へのリンクは push 後に有効になる |
| 文体の照合: omokage nao-tech の点数と、本人の実文（最近の記事・weeknotes）と比べて直した言い回しの例 | omokage 90%。接続詞が千字あたり 0 件（本人 1.4）だったので「しかし」「つまり」「そのため」「なお」を足し、逆接が「ただし」だけだった所を「しかし」に。「確かめ」→「確認」、「を、」を語順で直した（6 件）。名詞を「の」で 3 つ以上つなぐ表現は書いた時点で 31 個あり、0 個にした（「顔の枠の中の差」→「バウンディングボックスの中で比べた差」、「成人の女性の全身」→「成人の女性が全身で写る絵」など） |
| 訳語: 本文で英語と併記した訳語と、題材の中心の用語ごとに、英語の語・分野の日本語資料での言い方・URL | bounding box → バウンディングボックス（Ultralytics の日本語文書 https://docs.ultralytics.com/ja/tasks/detect 、用語集 https://ultralytics.com/ja/glossary/bounding-box 。初稿は自作の「検出枠」で、事実確認で多数派でないと分かり直した。style/terms.tsv に検出枠を避ける語として、glossary.tsv に行を足した）。英語との併記はバウンディングボックス（bounding box）と VAE（Variational Autoencoder）、brown eyes（茶色の目）、solo（1 人）、full body（全身）。seed → seed（シード値）（glossary.tsv の修正済みの行に合わせた）。hires fix → hires fix（A1111 の UI は「Hires. fix」と本文で併記。https://github.com/AUTOMATIC1111/stable-diffusion-webui/wiki/Features ）。denoise は ComfyUI のパラメータ名（A1111 は denoising strength、img2img Denoise のノートと揃えた）。描き直し: ADetailer の日本語解説（https://weel.co.jp/media/innovator/adetailer/ ）は「再生成」「修正」だが、img2img Denoise のノートと揃えて描き直しにした。表情差分は立ち絵の制作で使う言い方 |
| 表記: 太字 0、「を、」0、ユーザー/サーバー/ブラウザ等の表記、形式名詞 | style_check.sh 違反なし |
| 図: 全て WebP、背景が白、図の文字に太字なし、caption と alt あり | 9 枚とも WebP・白背景・figure shortcode で caption と alt あり。Mermaid の図 1 つ（ノードのつながり） |
| 図の入れ方（scripts/textruns.py の結果）: 700 字以上の文字だけの区間 0 個、200 字超の段落は基準の Wallet（5 個）並み | 700 字以上の区間 0 個、200 字超の段落 5 個 |
| 図の中の文字は日本語（コードの識別子・仕様の固有名・単位を除く）。英語のラベルが残っていない | はい。英語は MediaPipe・short・full・face_yolov8n・denoise と seed の番号だけ |
| 図ごとの確認（別エージェントの読解の確認で、図 1 枚ずつ） | 9 枚を確認。cover・latent・detect・eyes・denoise・big は理解を促す。食い違いは lines（全体の描き直しが太く見えた。seed を 20261122 に替え、各列に測った値を入れ、あごの下に濃い線が残ることと口が開いたことを本文に書いた）、steps（大きさを入れ、塗りを boxes のオレンジに揃えた）、big の alt（20261120 は上半身だけ）。引用の候補は ComfyUI の画面だったが、Mermaid のノードの流れで代えた |
| 図のラベルと本文の用語の併記（図の直後の初出） | 図と本文の語を揃えた（バウンディングボックス・貼り戻すマスク・切り抜く正方形・描いたまま・顔だけ描き直した・全体を描き直して縮めた） |
| 冒頭の型（フラット/場面/結果/誤解/問い）と選んだ理由 | フラット（定義 → 道具 → 表紙の図 → 本記事では）。直前の 3 本が場面・問い・結果で、表紙の図で目の色の違いが一目で分かるので、結果を前置きにせず定義から入った |
| 面白さの 4 因子（意外性・具体性・独自性・関連性、各 0〜3）と、その根拠 | 意外性 2（表紙で左右の目の色が揃う代わりに表情も変わる、denoise 0.3 でも口が変わり目つきが 1 つに寄る、ComfyUI の顔検出の既定は全身の顔を 1 枚も拾わない、最初から 2 倍で 5 枚とも人物が増える）、具体性 3（5 枚 × 6 条件の実測、23 枚の検出、ComfyUI・ADetailer・Impact Pack のソース）、独自性 2（拡張を使わず本体のノードで組んだ手順、描いた解像度で測る線の太さ、3 つの方法の比較）、関連性 3（全身の立ち絵を作る人の場面から入り、使う前に決める 3 つで閉じた） |
| 読者の場面（使おうとしている人 / 出会った人）と、書く前に挙げた「最初に知りたい問い」の箇条書き | 使おうとしている人（全身の立ち絵を画像生成で作り、顔が崩れる）。問い: 全身の絵で顔は何画素か、顔だけ描き直す手順、顔の見つけ方、描き直すと何が変わるか、全体を大きく描き直す方法と何が違うか |
| 結び: 利点・欠点の型で閉じていないか | 型を使わず、「顔だけ描き直す前に決めること」（検出器の設定・denoise・線の太さを揃えるか）で閉じた |
| 同じ題材の人気記事を見たか（はてブ・HN）と、取り入れた切り口 | はてブ「ADetailer」「Hires.fix」「FaceDetailer」「顔 崩れ 画像生成」（dskjal の waifu-diffusion のワークフロー 36 users、テクノエッジの連載 22 users など）、HN は該当なし。どれも使い方と設定の紹介が中心で、描き直すと何が変わるかを数えた記事は無かった。切り口は、全身の立ち絵で目の色が左右で違う場面から取った |
| 実験の図: 実験ごとに図があるか、図のラベル・数値がコードの出力と一致するか | 顔の大きさ（latent）、手順（boxes・steps）、検出（detect）、目の色（eyes）、表情（denoise）、線の太さ（lines）、最初から 2 倍（big）。数値は lab/metrics.json・detect*.json と一致（事実確認で再計算） |
| 時間で変わる所を挙げ、それぞれ動く WebP にしたか、止め絵にした理由 | 無し。比べるのは描き直した後の最終結果だけ。手順の 5 段は時刻を追う話ではないので、横に並べた止め絵にした |
| 前置き無しの固有名詞が無いこと | はい。ADetailer・ComfyUI・Impact Pack・FaceDetailer・SDXL・VAE・MediaPipe・face_yolov8n・WAI-illustrious-SDXL・ControlNet は初出で説明 |
| 版・digest・計測中の負荷の断り書きを本文から lab か details へ移したこと | はい。版・sha256・ComfyUI の commit・負荷は details と lab/README.txt・log_*.json |
| 相互リンク: 他のノートへ足した数、逆向きに足すべきリンクの提案 | 本記事から LoRA・Diffusion Model・img2img Denoise・Depth Body Shape・ControlNet・Background Removal へ。逆向きに img2img Denoise（hires fix で目の色が変わった段落）から 1 本足した |
| 内部リンクが全て実在、外部リンクが 200 | 内部 6 先とも 200。外部 16 本とも 200（事実確認）。lab への GitHub のリンクは push 後に 200 |
| PC 幅 1280 とダークモードで撮影して確かめた（スマホは横はみ出しだけ） | はい（Chrome の headless で 1280 幅のライト・ダーク、Mermaid は virtual-time-budget で描画を確認、390 幅。layout_check.py も上限内） |
| ページと /notes/ が 200 | はい |
| 本文の字数（前 → 後） | 新規 → 約 6,500 字（コードと図と表と details を除く） |
