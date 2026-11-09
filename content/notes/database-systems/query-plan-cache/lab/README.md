# ローカル実験

Docker と `postgres:17` イメージが使える環境で実行できます。

```sh
./run.sh
```

`run.sh` は `note-query-plan-cache` という名前の PostgreSQL 17 コンテナを起動し、`experiment.sql` を psql で流してから、コンテナを削除します。ホストのポートは公開せず、永続ボリュームも作りません。

`output.txt`・`output-2.txt`・`output-3.txt` は、PostgreSQL 17.11 で 3 回実行した結果です。`n_distinct` は `ANALYZE` の標本から推定されるので、実行のたびに変わり（257・261・265）、generic plan の推定件数もそれに合わせて変わります。実行時間も環境とキャッシュの状態で変わります。

`experiment.sql` の節は次の通りです。

1. 1 店舗が 99% を占める注文の表を作る
2. 同じ値で 7 回実行し、6 回目に generic plan へ切り替わる様子を見る
3. 同じ generic plan で小さい店舗を引く
4. `plan_cache_mode = force_custom_plan` で値ごとの計画に戻す
5. 最初の 5 回を小さい店舗で実行すると、切り替わらないことを見る
6. 索引の削除と作成で generic plan が作り直されることを見る
7. 列の追加で `SELECT *` の文がエラーになることを見る
8. `search_path` の変更で表の名前が解決し直されることを見る
9. 行数とページ数が変わらない `ANALYZE` では計画が作り直されないことを見る
