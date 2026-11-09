# ローカル実験

Docker で PostgreSQL 17 のコンテナを起動し、全ての実験を順に流します。

```sh
./run.sh
```

コンテナ名は `note-partitioning` で、ホストのポートは公開しません。終了時にコンテナを削除します。`output.txt` は PostgreSQL 17.11 で実行した結果です。時間の値はマシンによって変わります。

| ファイル | 確かめること |
| --- | --- |
| `01_delete_vs_drop.sql` | 1 か月 500 万件を `DELETE` で消す場合と、パーティションを `DROP TABLE` で消す場合の時間と、回収待ちのレコード |
| `02_pruning.sql` | 範囲の条件と `date_trunc` で包んだ条件で、読むパーティションが変わるか。generic plan での実行時の刈り込み |
| `03_hot_partition.sql` | 時刻の Range と id の Hash で、1 日分の `INSERT` がどのパーティションに入るか |
| `04_unique.sql` | パーティションキーを含まない主キーのエラーと、含めた主キーで同じ id が入ること |
| `05_attach_detach.sql` | `CHECK` 制約の有無で `ATTACH PARTITION` の走査が変わるか。DEFAULT パーティションと `DETACH ... CONCURRENTLY` の制限 |
| `06_lock_queue.sh` | 長い読み出しがある間の `CREATE TABLE ... PARTITION OF` と `ATTACH PARTITION` で、後続の `SELECT` が待つか |
| `07_default_lock.sh` | DEFAULT パーティションがある表への `ATTACH PARTITION` で、CHECK 制約で走査を省いても後続の `SELECT` が待つか |

`06_lock_queue.sh` と `07_default_lock.sh` は単独でも動きますが、`note-partitioning` コンテナが起動している必要があります。
