deadlock_rate.py
  並行する送金のデッドロックの発生率を PostgreSQL 17 で実測する（シミュレーションではない）。
  Docker で postgres:17 のコンテナ note-deadlock を立て、中の pgbench で送金を流し、終わったら削除する。
  ホストのポートは公開しない。所要時間は 5 分程度。

    cd content/notes/database-systems/deadlock/lab
    python3 deadlock_rate.py > deadlock_rate_output.txt
    cd .. && python3 figures.py   # images/deadlock_rate.svg を作り直す（matplotlib が必要）

  クライアントの割り込み方は OS のスケジューラで決まるので、受け付けた順（random）の件数は
  実行のたびに少し動く。ID の昇順（ordered）は毎回 0 件になる。
