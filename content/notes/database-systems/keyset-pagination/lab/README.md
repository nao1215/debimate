# ローカル実験

Docker と `postgres:17` イメージが使える環境で実行できます。

```sh
./run.sh > output.txt
```

`run.sh` は `note-keyset-pagination` という名前の PostgreSQL 17 コンテナを起動し、`experiment.sql` と `bench.sql` を psql で流してから、コンテナを削除します。ホストのポートは公開せず、永続ボリュームも作りません。

`output.txt` は `experiment.sql` の結果、`bench.csv` は `bench.sql` の結果で、どちらも PostgreSQL 17.11 で実行したものです。時間は手元の環境とキャッシュの状態で変わります。

`experiment.sql` の節は次の通りです。

1. 投稿 100 万件の表を作る（`created_at` は 2 件ずつ同じ時刻）
2. OFFSET で 1 ページ目と最後のページを読む
3. キーセットで最後のページを読む
4. ページを読む間に 3 件増えると、OFFSET の 2 ページ目が 1 ページ目と重なる
5. ページを読む間に 2 件消えると、OFFSET の 2 ページ目が 2 件を飛ばす
6. 並びのキーに `created_at` しか使わないと、同じ時刻のレコードが消える
7. 行の比較を OR で書いた場合と、昇順と降順が混ざる並びの場合
8. 総件数を数える `COUNT(*)`

`bench.sql` は、読み始める位置を 10 通りに変えて、OFFSET とキーセットで同じ 20 件を読む時間を 7 回ずつ測り、中央値を出します（最初の 1 回は捨てる）。
