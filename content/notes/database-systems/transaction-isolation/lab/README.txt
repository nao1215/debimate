lost_update.py
  在庫の引き当て（残数を読み、自分で計算した値を書き戻す）を並行に流し、READ COMMITTED と
  SERIALIZABLE で失われた更新の件数と再試行の回数を PostgreSQL 17 で実測する。
  Docker で postgres:17 のコンテナ note-transaction-isolation を立て、中の pgbench で流し、
  終わったら削除する。ホストのポートは公開しない。所要時間は 1〜2 分。

    cd content/notes/database-systems/transaction-isolation/lab
    python3 lost_update.py > lost_update_output.txt
    cd .. && python3 figures.py   # images/transaction-isolation_lost_update.svg を作り直す（matplotlib が必要）

  クライアントの割り込み方は OS のスケジューラで決まるので、READ COMMITTED の失われた更新と
  SERIALIZABLE の再試行の回数は実行のたびに少し動く。SERIALIZABLE の失われた更新は毎回 0 になる。
  再試行が 10,000 回に達したトランザクションは gave_up に数え、コミットしない（今回の 2 回の実行では 0 件）。
