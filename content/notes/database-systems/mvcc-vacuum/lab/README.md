# ローカル実験

Docker と `postgres:17` イメージが使える環境で実行できます。

```sh
./run.sh > output.txt
```

`run.sh` は `note-mvcc-vacuum` という名前の PostgreSQL 17 コンテナを起動し、`experiment.sql` を psql で流してから、コンテナを削除します。ホストのポートは公開せず、永続ボリュームも作りません。結果を比べるために、実験の表は `autovacuum_enabled = off` で作っています。

`hold.sql` は、`experiment.sql` がコンテナの中で別の接続として起動します。REPEATABLE READ のトランザクションを開いて表を 1 回読み、`experiment.sql` が持つ advisory lock が外れるまで待ってからコミットします。

`output.txt` は `experiment.sql` の結果、`sizes.csv` は 2 節の回ごとの表の大きさ（MB）と、統計情報の死んだ版の数（`n_dead_tup`、推定値）です。どちらも PostgreSQL 17.11 で実行したものです。

`experiment.sql` の節は次の通りです。

1. UPDATE・DELETE・VACUUM の後のブロックの中を pageinspect で見る
2. 10 万件の表の全件を 10 回更新し、回ごとに表の大きさを記録する（VACUUM しない / 毎回 VACUUM / 毎回 VACUUM するが古いスナップショットを持つ接続がある）
3. 古いスナップショットがある間の VACUUM (VERBOSE)
4. スナップショットを持つトランザクションが終わった後の VACUUM (VERBOSE)
5. VACUUM と VACUUM FULL の後の表の大きさ
6. トランザクション ID の年齢と、autovacuum の既定の設定
