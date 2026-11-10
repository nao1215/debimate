orders_pg.sql
  orders_sorted / orders_random を作り、user_id = 4242 の Index Scan が触るページ数を比べる（本文の 4 枚と 103 枚）。
    psql -f orders_pg.sql   （PostgreSQL 17。サーバーを再起動して共有バッファを空にしてから EXPLAIN を流す）

orders_sqlite.py / scan.py
  SQLite の実行計画（USING COVERING INDEX、SCAN と SEARCH）を確かめる。
    python3 orders_sqlite.py
    python3 scan.py

selectivity_pg.py
  orders_pg.sql と同じ 2 つの表で、一致する割合を 0.01〜100% に動かし、seq scan と index scan が
  触ったページの延べ枚数と時間を PostgreSQL 17 で実測する。Docker で postgres:17 のコンテナ
  note-index-scan を立て、終わったら削除する。ホストのポートは公開しない。所要時間は 2〜3 分。

    cd content/notes/database-systems/index-scan/lab
    python3 selectivity_pg.py > selectivity_pg_output.txt
    cd .. && python3 figures.py   # images/index-scan_selectivity.svg を作り直す（matplotlib が必要）

  setseed で並びを固定しているので、ページ数は再実行しても一致する。時間と correlation（ANALYZE の
  標本で動く）は実行のたびに少し動く。
