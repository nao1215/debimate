# 完了のチェックリスト: math/kde（2026-11-12 書く担当）

対象: projects/ml/notes/math/kde/index.md。構成から書き直した（題・冒頭・節の並び・図 7 枚・生成元を全て差し替え、旧 SVG 4 枚を削除）。報告は .note-review/interest-review/stage3/math__kde.writer.md。2026-11-12 に読解の確認 1 回目（判定 B、13 件）を受けて直し、報告は math__kde.writer2.md。

| 項目 | 結果（数値・回数・URL など） |
|---|---|
| Skill ツールで debimate-visual-notes を起動した | はい（create-ml-notes も起動して読んだ） |
| 読解の確認（初学者役の別エージェントが上から読む）の回数と、最後の判定（A/B/C）と残った指摘 | 1 回（.note-review/interest-review/stage3/math__kde.read1.md）。判定 B、指摘 13 件を全て直した: 特徴量の「面積」を mean area に揃え曲線の面積と区別、Silverman の本の式と scipy の "silverman" の関係を段落を分けて説明、kde.factor と ddof=1 を使う前に定義（実験 3 も std(ddof=1) に揃えた）、GridSearchCV が score（対数尤度の和）の 5 回の平均を最大にすること・80 点の由来、/ area.std() の換算、0 を含む列では対数が使えず折り返しを使うこと、結びの段落を分割、395 個の数え方と KernelDensity を異常検知・生成に使う理由を冒頭へ。2 回目の読解の確認は確かめ役に回す |
| 事実確認（一次資料と照合。別エージェントか自分か）と、直した件数 | 自分で一次資料と照合: scikit-learn 1.9.1 の _kde.py（bandwidth_ = n ** (-1/(d+4))、σ を掛けない）、scipy の gaussian_kde の文書（規則は単峰向けで多峰は平滑しすぎる、カーネルの形よりバンド幅が効く）、seaborn 0.13.2 の _statistics.py（gaussian_kde を呼ぶ）、Scott・Silverman・Epanechnikov の DOI を crossref で照合。数値は全て gen の出力（.note-review/work/kde/gen_out.txt）と一致。別エージェントの事実確認は確かめ役に回す |
| 文体の照合: omokage nao-tech の点数と、本人の実文（最近の記事・weeknotes）と比べて直した言い回しの例 | 前回の照合に加え、読解の確認で出た本人に用例の無い語を直した: 「KDE を当てる」6 か所を「使う」「計算する」へ（author_grep: 計算し 本人 7 件）、「桁違い」→「極端に」（本人 1 件）、「1 つの値を正解として扱わず」→「決め打ちせず」（本人 3 件）、見出し「"scott" が見ないもの」→「"scott" は標準偏差を掛けない」、「形の歪み」→「曲線の形に出ます」、「そろえる」→「揃える」 |
| 表記: 太字 0、「を、」0、ユーザー/サーバー/ブラウザ等の表記、形式名詞 | style_check.sh 違反なし。太字 0、「を、」0（「幅を、列の…」を語順で直した）、「時」は漢字、形式名詞「こと」 |
| 図: 全て WebP、背景が白、図の文字に太字なし、caption と alt あり | 7 枚（kde_cover・kde_per_point・kde_bandwidth・kde_cv・kde_scott_width・kde_boundary・kde_class）とも WebP・白背景・figure shortcode で caption と alt あり。旧 SVG 4 枚は削除 |
| 図の入れ方（scripts/textruns.py の結果）: 700 字以上の文字だけの区間 0 個、200 字超の段落は基準の Wallet（5 個）並み。長さは削らなくてよいが、文字だけの区間は図か区切りで割る | 700 字以上の区間 0 個、200 字超の段落 2 個（前回 1 個。説明を足した分。0 が下限の節の長い段落は 2 つに分けた） |
| 図の中の文字は日本語（コードの識別子・仕様の固有名・単位を除く）。英語のラベルが残っていない | はい。英語は列名の mean area・mean concavity、関数名の bandwidth="scott"・load_breast_cancer、ライブラリ名、軸の x だけ（7 枚を Read で 1 枚ずつ見た） |
| 図ごとの確認（別エージェントの読解の確認で、図 1 枚ずつ）: (1) 理解を促すか（読者が何を掴めるか、文章の言い直しでないか）、(2) 公式の図・実画面を出典付きで引用した方が伝わらないか、(3) 文章と食い違っていないか（用語・数値・要素） | 読解の確認 1 回目で 7 枚を見てもらい、kde_cv の凡例の Scott/silverman の大小文字を "scott"・"silverman" に揃えた（alt も）。縦軸の「検証用の 80 点」は本文に 400 点の 5 分割で 80 点ずつと書いた。kde_class の題「それぞれ面積 1」→「曲線の面積はそれぞれ 1」、表紙の題「KDE を当てた」→「計算した」。生成元を回し直し、7 枚を Read で 1 枚ずつ見た。出力は前回と数値の差なし（.note-review/work/kde/gen_out3.txt） |
| 図のラベルと本文の用語の併記（図の直後の初出） | 図と本文の語を揃えた（scipy の scott・scikit-learn の scott・バンド幅 h・0 未満にはみ出した面積・0 で折り返した KDE・件数を掛けた曲線）。過小平滑（under-smoothing）・過剰平滑（over-smoothing）は本文で併記 |
| 冒頭の型（フラット/場面/結果/誤解/問い）と選んだ理由 | 誤解。直前の 3 本（information-theory・joint-marginal-conditional・property-based-testing）とは別の型。題材の核心が「同じ "scott" なら同じ幅になる」という思い込みそのもので、名前の一致を置いてから表紙の図で解く。notes-quality/opening_log.tsv に kde の行を足した。題の「腫瘍の面積」は特徴量の名前に合わせ「細胞核の面積」に直した |
| 面白さの 4 因子（意外性・具体性・独自性・関連性、各 0〜3）と、その根拠（冒頭か本筋のどこにあるか） | 意外性 3（冒頭の図: 同じ "scott" で幅が 352 倍、山 395 個、mean concavity では面積の 38% が 0 未満、エラー・警告なし）、具体性 2（同梱の load_breast_cancer の実測と版付き。実在の障害報告は無し）、独自性 2（30 列の標準偏差と幅の図で、scikit-learn の scott が σ を見ないことを示した。seaborn との一致も実測）、関連性 3（seaborn で見た形を KernelDensity で異常検知・生成に移す場面を冒頭に置き、標準化で揃える手当てまで渡す） |
| 読者の場面（使おうとしている人 / 出会った人）と、書く前に挙げた「最初に知りたい問い」の箇条書き | 使おうとしている人（seaborn で EDA をして、scikit-learn の KernelDensity で異常検知・生成に使う人）と、ML の説明の KDE を自分で計算したい人。問い: 1 点ずつ何を足すか／バンド幅で山の数はどう変わるか／規則と交差検証の幅はどれだけ違うか／scikit-learn の "scott" は scipy と何が違うか／0 が下限の値で曲線のどこが誤るか／診断ごとに重ねた曲線をどう読むか |
| 結び: 利点・欠点の型で閉じていないか。閉じるなら、比べて選ぶのが核心の題材である理由 | 型で閉じていない。旧版の「使いどころ」「適さないケース」の節を消し、異常検知・生成は scikit-learn の節へ、少数データ・次元の呪い・PCA は結びへ配り直した。結びは、幅を単位付きで出す → 何本かの h で描く → 下限・上限を見る → クラスの件数を掛ける、の判断で閉じ、冒頭の図の 2 本の曲線に戻る |
| 同じ題材の人気記事を見たか（はてブ・HN）と、取り入れた切り口 | 今回は検索していない（ネットワークの取得は配布元の文書と DOI の照合だけにした）。stage1 の improve_ideas（ライブラリごとの既定のバンド幅の違いを実測、下限のある実データで境界の密度、山の数を見誤る場面）を切り口にした |
| 実験の図: 実験ごとに図があるか、図のラベル・数値がコードの出力と一致するか | 実験 7 つに図 7 枚。本文のコードは kde_gen.py の該当部分の抜粋で、出力は gen_out.txt と一致（生成元を 2 回実行し、出力の差分なし） |
| 時間で変わる所（順番・遅れ・溜まる・消える・入れ替わる・段階・どれが残るか）を挙げ、それぞれ動く WebP にしたか、止め絵にした理由。無ければ「無し」と書く | 無し（KDE は 1 回の推定で、時間で状態が変わる所が無い。バンド幅を連続に変える動画も考えたが、比べたいのは 3 通りの h と 2 つのライブラリの最終の形なので止め絵にした） |
| 前置き無しの固有名詞（EIP 番号・フォーク名・関数名・版）が無いこと | gaussian_kde・kdeplot・KernelDensity は冒頭で役割と一緒に出し、bw_method・bandwidth_・score_samples・sample は使う所で何をするかを書いた。版は「本記事では」の後の 1 文と、実装のリンクの 1.9.1 だけ |
| 版・digest・計測中の負荷の断り書きを本文から lab か details へ移したこと | 版は 1 文だけ。digest・負荷の断り書きは無し |
| 相互リンク: 他のノートへ足した数、逆向きに足すべきリンクの提案 | 本文から 11 本（probability-distributions・stddev・log-exp-logodds・quantile・cross-validation・standardization・anomaly-detection・bayes-theorem・confusion-matrix・curse-of-dimensionality・pca）。関門の注意の「標準偏差」→ stddev を初出に足した。逆向きは standardization の「標準化が必要なモデル」の表に KernelDensity の行を 1 行足した（skewness・median・stddev・anomaly-detection からは既にリンクあり） |
| 内部リンクが全て実在、外部リンクが 200 | 内部 11 本は projects/ml/notes に実在し、hugo のビルドでページ生成を確認。外部は gaussian_kde・kdeplot・KernelDensity・load_breast_cancer・_kde.py（1.9.1 のタグ）・scikit-learn の密度推定の文書が curl で 200、DOI 3 本は 302 で出版社へ転送 |
| PC 幅 1280 とダークモードで撮影して確かめた（スマホは横はみ出しだけ） | 撮影できず（今回も headless の Chrome が 60 秒で打ち切り）。今回足した表は 3 行 2 列で、最長のマスは全角 19 字なので 1 行に収まる。箇条書きの数式 2 項目は表に移した。撮影は確かめ役かメインに回す |
| ページと /notes/ が 200 | hugo -d .note-review/work/kde/public で /ml/math/kde/ を生成（表 1 つ、図 7 枚、新しい見出し）。hugo server は起動していない |
| 本文の字数（前 → 後） | style_check.sh の読者向け本文 8404 字 → 9273 字（定義と説明の補い。数え方は前回と同じスクリプト） |
