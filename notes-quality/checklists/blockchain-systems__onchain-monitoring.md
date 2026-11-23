# 完了のチェックリスト: blockchain-systems/onchain-monitoring（2026-11-23 新規）

| 項目 | 結果（数値・回数・URL など） |
|---|---|
| Skill ツールで debimate-visual-notes を起動した | はい（メイン。読解の確認・事実確認の担当にも起動させた） |
| 読解の確認（初学者役の別エージェントが上から読む）の回数と、最後の判定（A/B/C）と残った指摘 | 10 回（毎回新しい読み手）。止まる指摘（★）は 7・2・2・2・3・3・1・3・2・2 件で、どれも lab と一次資料で確かめてから直した（S1 の条件のツールごとの違い、339/330 の数え方、rindexer の finalized の深さは rindexer の値、Restart=on-failure に限る、reorg の誤検知、ICON の日付は UTC で 27 日など）。最後は B。2026-11-23 に読解の確認の回数に上限を置く規則（全文 1 回→★を直す→差分だけ 1 回）へ改めたので、11 回目は回さず打ち切った。残りの数値の照合は事実確認に回した |
| 事実確認（一次資料と照合。別エージェントか自分か）と、直した件数 | 別エージェント 1 回（lab の results.json・summary.txt、OZ Monitor・rindexer・Silverback のソース、ICON・Mezo・Forta・The Block・Infura の status ページと照合）。件数と既定値はすべて一致。直した 9 件: Infura の原因（古い Geth の部品が合意のバグに当たり API が約 6 時間止まった）、ICON の「重要度に下げた」→「設定してあった」と alert-tuning を「調整（tuning）」に、Euler は Euler の対応の遅れではなく Forta の評価として、Velar の時期（1 月下旬〜2 月 4 日）と無期限先物（perpetual）、Ronin は 6 億ドル超、block_checkpoint_lag は承認数を引いた番号との差、表紙の 295 件は止める少し前からの分、removed: true の根拠を ethereum.org の JSON-RPC の文書へ、precision・recall に適合率・再現率を併記。リプレイ攻撃の語も足した |
| 文体の照合: omokage nao-tech の点数と、本人の実文（最近の記事・weeknotes）と比べて直した言い回しの例 | omokage 90。style_check.sh の違反 0。「の」の連続（no_chain.py）0、「を、」0。接続詞が本人より少ない（千字あたり 0.3、本人 1.4）と出たが、段落の分け方で繋がっているので足していない |
| 訳語: 本文で英語と併記した訳語と、題材の中心の用語ごとに、英語の語・分野の日本語資料での言い方・URL | confirmations → 承認数（glossary.tsv の既存の行、finality ノートと同じ）、finalized → ファイナライズ済み（finality ノートと同じ。Ethereum 公式の日本語版 https://ethereum.org/ja/developers/docs/consensus-mechanisms/pos/ が「ファイナリティ」「ファイナライズ」）、reorg → reorg（indexer・finality ノートと同じ）、checkpoint → チェックポイント（indexer ノートと同じ）、webhook → webhook、dead man's switch → 英語のまま（heartbeat ノートと同じ）、precision → 適合率・recall → 再現率（glossary.tsv の一致の行。Google の機械学習集中講座の日本語版 https://developers.google.com/machine-learning/crash-course/classification/accuracy-precision-recall?hl=ja ）、perpetual → 無期限先物（暗号資産の取引所の日本語の説明で一般的。Mezo の報告の perpetual DEX）、tuning → 調整（ICON の報告の alert-tuning。アラートの閾値や重要度の調整の意味で、SRE の日本語の解説でも「アラートの調整」）、recovery → 機能（OZ Monitor の recovery の機能を指す語で、訳語ではない）、sink.py → 受け口・faultproxy.py → 中継（実験のファイル名に役割を添えただけで、訳語ではない） |
| 表記: 太字 0、「を、」0、ユーザー/サーバー/ブラウザ等の表記、形式名詞 | 太字 0、「を、」0、style_check.sh の NG 0 |
| 図: 全て WebP、背景が白、図の文字に太字なし、caption と alt あり | 8 枚（rpc_down・loop・setup・one_block・restart・reorg・sink・icon）。全て WebP・白背景・太字なし・caption と alt あり。Pillow と Noto Sans CJK で描いた。表の画像だった outside は Markdown の表に戻した |
| 図の入れ方（scripts/textruns.py の結果）: 700 字以上の文字だけの区間 0 個、200 字超の段落は基準の Wallet（5 個）並み | 700 字以上の区間 0、200 字超の段落 7。冒頭の 700 字超の区間は、表紙の図を先に置き、結果の要約を実験の節へ移して割った |
| 図の中の文字は日本語（コードの識別子・仕様の固有名・単位を除く）。英語のラベルが残っていない | 残っていない。OZ Monitor・rindexer・Silverback・Anvil・eth_getLogs・webhook など固有名とメソッド名だけ原文 |
| 図ごとの確認: (1) 理解を促すか、(2) 公式の図・実画面を出典付きで引用した方が伝わらないか、(3) 文章と食い違っていないか | rpc_down: RPC を 5 分止めた時に届いた数と消えた数が一目で分かる表紙。loop: 監視ツールの 1 周と欠けが入る 5 か所。setup: 実験の配線（Anvil・中継・受け口）。one_block: 黙って消す・止まって待つ・終了するの 3 つの型。restart・reorg: 動く WebP（下の行）。sink: 通知先の失敗で捨てた件数。icon: ICON の時刻の並び。公式の図に置き換えた方が良い物は無かった。件数と時刻は lab の results.json と合わせた |
| 図のラベルと本文の用語の併記（図の直後の初出） | 図と本文をチェックポイント・承認数・遅れの指標・取り消しの通知で揃えた |
| 副題: その技術の一般的な知見を現在形で書いたか | 「通知の欠けは監視ツールの外から確かめる」。現在形の一般論で、プロジェクト名・実験の値なし。節の見出し（欠けの 5 か所、気付けるか、外から確かめる）を覆う |
| 冒頭の型と選んだ理由 | 場面から。ICON の事故（7 分で鳴ったアラートに約 90 分気付かなかった）で、読者が監視を入れても気付けない場面を先に置くため。直前 3 本（予想・結果・一覧）と違う型 |
| 面白さの 4 因子（意外性・具体性・独自性・関連性、各 0〜3）と、その根拠 | 意外性 3（RPC を 5 分止めても遅れの指標が 0 のまま凍り、/health は 200、終了コード 0 で止まる。1 ブロックの失敗で 15 番の通知が黙って消える）、具体性 3（3 つの OSS × 欠け 5 種の実測と、ICON・Ronin・Velar・Euler の実例）、独自性 3（同じ欠けを 3 つのツールに入れて比べた実験は他に無い）、関連性 3（監視を入れる・使っている人の判断で閉じる） |
| 読者の場面（使おうとしている人 / 出会った人）と、書く前に挙げた「最初に知りたい問い」の箇条書き | 使おうとしている人と、監視を動かしている人。問い: 監視ツールはどこで通知を落とすか / 1 ブロック取れない時どうなるか / 止めて再起動したら止まっていた間はどうなるか / reorg で何が届くか / 通知先が落ちたら送り直すか / 監視が止まったことに気付けるか / 誤検知と取りこぼしをどう分けるか |
| 結び: 利点・欠点の型で閉じていないか | 型で閉じていない。使う前に確かめることで閉じた |
| 同じ題材の人気記事を見たか（はてブ・HN）と、取り入れた切り口 | HN を見た。Ronin の「6 日間気付かなかった」（569 点）、Ask HN の heartbeat（108 点、テレメトリが来なくなって誰も通知されなかった）、Show HN の dead man's switch（139 点）が読まれていた。オンチェーン監視そのものの人気記事は無かった。「止まったことに気付かない」の切り口を、監視が止まったことに気付けるかの節と外から確かめる節に取り入れた |
| 実験の図: 実験ごとに図があるか、図のラベル・数値がコードの出力と一致するか | S1 → one_block、S2 → restart、S3 → reorg、S4 → sink、S5 → rpc_down。数値は lab の results.json・summary.txt と一致 |
| 時間で変わる所を挙げ、それぞれ動く WebP にしたか、止め絵にした理由 | (1) 停止中に溜まったブロックが再開時に捨てられる → restart を動く WebP（実測の時刻を 10 倍速）。(2) reorg で古い通知が残り新しい通知が消える → reorg を動く WebP（10 倍速）。(3) RPC の停止 → 止め絵。比べたいのは最終の届いた数と消えた数だけのため。(4) ICON の時刻 → 止め絵の時刻の並び。90 分を目で追う必要が無いため |
| 前置き無しの固有名詞（EIP 番号・フォーク名・関数名・版）が無いこと | 無い。eth_getLogs・max_past_blocks・reorg_safe_distance などの設定とメソッドは使う所で何かを書いた |
| 版・digest・計測中の負荷の断り書きを本文から lab か details へ移したこと | 各ツールのバージョンは実験の節に 1 回だけ。細部は lab/SCENARIOS.md と各 summary.txt へ |
| 相互リンク: 他のノートへ足した数、逆向きに足すべきリンクの提案 | 本文から 10 本（blockchain-basics・bridge-incidents・heartbeat・retry-backoff・transactional-outbox・erc-20・evm・finality・indexer 2 か所）。逆向き 1 本（indexer の結びの監視の段落）を足した |
| 内部リンクが全て実在、外部リンクが 200 | 内部リンク 10 本とアンカーは実在。外部リンクは事実確認で 200（lab の GitHub の 2 本は push 後に有効）。足した ethereum.org の JSON-RPC の文書も 200 を確認 |
| PC 幅 1280 とダークモードで撮影して確かめた（スマホは横はみ出しだけ） | 撮影した（.note-review/work/shots/monitor/、ライトとダーク）。図は白背景でダークでも読める。表のマスは 2 行以内、横のはみ出し無し |
| ページと /notes/ が 200 | 200（hugo server、0.0.0.0:1313） |
| 著者の指定（2026-11-23）: OSS の中身を出さず、症状で実例を紹介する | 著者の OSS は出していない。kongo に関わる話も出していない |
| 本文の字数（前 → 後） | 新規 → 約 17,800 字（空白を除く） |
