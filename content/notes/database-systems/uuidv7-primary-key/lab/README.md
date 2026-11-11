# ローカル実験

Docker と `postgres:18` イメージが使える環境で実行できます。

```sh
./run.sh > output.txt
```

`run.sh` は `note-uuidv7-primary-key` という名前の PostgreSQL 18 コンテナを起動し、`experiment.sql` を psql で流してから、コンテナを削除します。ホストのポートは公開せず、永続ボリュームも作りません。設定は全て既定のままです（shared_buffers 128MB、full_page_writes on）。

`output.txt` は `experiment.sql` の結果、`dirty_blocks.csv` は 4 節で書き換わった索引のブロックの番号で、どちらも PostgreSQL 18.6 で実行したものです。時間は手元の環境の負荷で変わります。

`experiment.sql` の節は次の通りです。

1. uuidv4() と uuidv7() の値と、取り出した版・時刻
2. 主キーだけが違う 3 つの表（bigint の連番・UUIDv4・UUIDv7）に、100 万件を 1 万件ずつ入れる
3. 主キーの索引の大きさと、葉のブロックの充填率（pgstattuple）
4. CHECKPOINT の直後に 1 万件を足し、書き換わった索引のブロック（pg_buffercache）と WAL の量を見る
5. 主キーを参照する子の表と、その索引の大きさ
6. 1 つの接続で 10 万件の UUIDv7 を作り、順に並ぶかを見る
7. uuidv7() の shift 引数で時刻をずらす

`switch.sql` は、UUIDv4 で 100 万件を入れた表の既定値を途中から uuidv7() に変え、20 万件を足した後・v4 の行を消して VACUUM した後・REINDEX した後の葉の充填率を見ます（結果は `output_switch.txt`。`run.sh` が別の DB で流します）。
