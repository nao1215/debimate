fk_delete.py
  子のカラム orders.member_id に索引がある場合と無い場合で、親 members を 1 件 DELETE する時間を
  PostgreSQL 17 で実測する。Docker で postgres:17 のコンテナ note-foreign-key を立て、
  終わったら削除する。ホストのポートは公開しない。所要時間は 2〜3 分。

    cd content/notes/database-systems/foreign-key/lab
    python3 fk_delete.py > fk_delete_output.txt
    cd .. && python3 figures.py   # images/foreign-key_delete_time.svg を作り直す（matplotlib が必要）

  時間は実測なので実行のたびに動く（400 万件・索引なしで 141〜249 ms を見た）。
  索引の有無による 2 桁以上の差は変わらない。
  「scan of orders in the FK lookup」は、検査と同じ形の問い合わせを汎用プランで EXPLAIN した結果で、
  検査そのものの実行計画を写したものではない。
