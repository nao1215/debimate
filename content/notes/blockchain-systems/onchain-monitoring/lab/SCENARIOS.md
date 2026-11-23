# 監視ツールの欠けの実験：共通シナリオ（2026-11-23 固定）

目的: オンチェーン監視の OSS が、データの欠け（1 ブロックだけ RPC が失敗・監視の停止・reorg・通知先の失敗・RPC の停止）に当たった時、
「鳴るべき通知が届いたか」「黙って消えたか」「二重に鳴ったか」「止まったことが外から分かるか」を数える。

## 安全
- すべて 127.0.0.1。Anvil の既定テスト用アカウントだけ。公開ネットワーク・実資産・実鍵は使わない。
- 一時物・ビルド・ログは各ツールの output/runs/ に置く。Docker コンテナ名は monitor-note-<tool>-... にし、終わったら消す。

## 共通の道具（このディレクトリ）
- bin/anvil: Foundry anvil 1.7.1
- faultproxy.py: Anvil の前に置く JSON-RPC 中継。POST /control {"fail_blocks":[n...], "mode":"error|timeout|empty", "down":bool}。全要求を JSONL に記録。
- sink.py: webhook の受け口。受信時刻と本文を JSONL に記録。第 3 引数で最初の N 件に 500 を返す（S4 では時間で切り替えたいなら sink.py をコピーして改造してよい）。
- 契約: ../indexer/lab/Token.sol（Transfer イベントを出す ERC-20 もどき）と同 lab/keccak.py。solc 0.8.28 を使う（環境変数 SOLC で場所を渡す）。

## チェーンの進め方（全シナリオ共通）
- anvil --no-mining --port <P> --host 127.0.0.1。driver が 1 秒ごとに evm_mine する（Silverback は新しいブロックが 10 秒来ないと落ちるので止めない）。
- block 1 で Token をデプロイ。以降、各ブロックに alice→bob の transfer を 1 件ずつ入れ、量 = そのブロックの番号（量から何番目のイベントかが分かる）。
- 監視の規則: Token の Transfer で to=bob のものを全部通知する（webhook を sink.py へ）。各ツールの webhook の形に合わせる。
- 監視は faultproxy.py 経由で Anvil を見る。

## シナリオ
- S0 基準: block 2..41 の 40 件。欠けなし。全件 1 回ずつ届くことを確かめる（届かなければ設定の問題）。
- S1 1 ブロックだけ失敗: 量 15 のイベントを含むブロックについて、eth_getLogs（とレシート・ブロック取得）を
  (a) 恒久に error、(b) 20 秒だけ error の後で回復。各 40 件で、量 15 が届いたか・他が届いたか・ログに何が出たか・チェックポイントの位置。
- S2 停止と再開: 量 1..10 が届いた後に監視を止める（SIGTERM と kill -9 の両方を試せれば）。止めている 60 秒（60 ブロック、1 件/ブロック）の後に再起動し、さらに 20 ブロック。停止中の 60 件のうち何件届いたか。ツールの設定で遡る上限があれば既定と「上限なし」の両方。
- S3 reorg: 量 1..20 が届いた後、anvil_reorg(depth=3) で直近 3 ブロックを、alice→bob 量 1000+元の量 の transfer を持つブロックに置き換える。その後 20 ブロック。置き換わった 3 件の通知が「残ったまま」「取り消された」「新しい 3 件が届いた」「二重」のどれか。確認数（confirmation）の設定があれば既定と、reorg より深い値（例 5）の両方。
- S4 通知先の失敗: sink が 60 秒間すべて 500 を返す。その間のイベントの通知は、再送で後から届いたか・捨てられたか・ログ/metrics に出たか。
- S5 RPC の停止: faultproxy の down=true を 5 分。監視のプロセスは生きているか・終了したか、health/metrics の値（あれば 10 秒ごとに記録）、ログ。回復後に停止中のイベント（Anvil は動き続ける）が届くか。

## 記録（ツールごとに <tool>/output/）
- results.json: シナリオごとに {expected:[量...], delivered:[{量, 受信時刻, 回数}], missing:[...], duplicated:[...], retractions:[...], notes}。
- 各シナリオの要点 summary.txt、ツールの版・commit・設定ファイル、実行したコマンド。ログは要点だけ（長い全ログは logs/ に置くが後で消してよい）。
- 時刻は実測。作らない。結果が予想と違えば、そのまま記録し、理由をソースで確かめて書く。
