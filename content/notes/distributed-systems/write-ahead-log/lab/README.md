# WAL のノートの実験

Docker と Go が要る。どれもローカルのコンテナだけを使い、終わるとコンテナと volume を消す。
2026-11-17 に Ubuntu 26.04.1、ext4、NVMe SSD（KIOXIA EXCERIA PLUS G4）、Docker 29.2.1 で取った。
同じ機械で他の処理も動いていたので、数は回ごとに揺れる。

| ファイル | 内容 |
|---|---|
| killtest/main.go | PostgreSQL 18.6 に 1 行ずつ INSERT し、2 秒後に docker kill（SIGKILL）で止め、起動し直して残った行を数える |
| killtest_output.txt | 既定・synchronous_commit=off・fsync=off を 5 回ずつ |
| killtest_async_timeline.json | synchronous_commit=off の 5 回目の最後の 1.2 秒（成功が返った行は 10 行おきに間引いた） |
| killtest_async_check.txt | synchronous_commit=off の 6 回目（-out 付き）を check_lost.py で突き合わせた結果。消えた行と、最後に OS へ渡した位置より後ろの行が一致するか |
| recovery_log.txt | 同じ 6 回目で、止めた後の起動で PostgreSQL が出した復旧のログ |
| check_lost.py | killtest -out の JSON で、消えた行と最後の write_lsn より後ろの行を比べる |
| killtest_mysql/main.go | 同じ実験を MySQL 8.4 で、innodb_flush_log_at_trx_commit を 1・2・0 に変えて行う |
| killtest_mysql_output.txt | binlog あり（既定）と --skip-log-bin を 3 回ずつ |
| groupcommit.sh | pgbench で同時に送る数を 1〜64 に変え、コミット数と WAL の fsync の回数（pg_stat_io）を数える |
| waldump.sh / waldump_output.txt | checkpoint の直後に UPDATE を 1 回だけ実行し、その WAL を pg_waldump で読む |
| slot.sh / slot_cap.sh | 読み手のいない replication slot があると pg_wal が膨らむこと、max_slot_wal_keep_size で止まること |

```sh
go run ./killtest -setting default
go run ./killtest -setting synchronous_commit=off -out out.json
go run ./killtest -setting fsync=off
go run ./killtest_mysql -skip-log-bin -trx-commit 0
python3 check_lost.py out.json > killtest_async_check.txt
sh waldump.sh > waldump_output.txt
sh groupcommit.sh > groupcommit_output.txt
sh slot.sh > slot_output.txt
sh slot_cap.sh > slot_cap_output.txt
```

注意

- docker kill はプロセスを止めるだけで、OS のページキャッシュは残る。電源断や OS の停止は試していない。
- killtest の「止めた時刻」は、成功が返った最後の行の時刻で数えている。docker kill を呼んでから、実際に止まるまで 20〜40 ms ほど INSERT が成功し続けた。
- MySQL の既定（binlog あり、sync_binlog=1）では、innodb_flush_log_at_trx_commit=0 でも消えた行は 3 回中 1 回の 1 行だけだった。
  コミットごとに binlog の同期を待つので、redo log の書き出しを待つ間が短くなったとみている（検証はしていない）。ノートでは binlog を切った結果を使った。
- groupcommit.sh は 2 回走らせ、ノートの図は 2 回目の出力（groupcommit_output.txt）。1 回目は既定の 1 クライアントで 1,586 回/秒、64 クライアントで fsync 1 回あたり 31.4 コミットだった。
