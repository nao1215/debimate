# ローカル実験

Docker で PostgreSQL 17 を起動し、500 万件の注文表と日別集計の materialized view で次を確かめます。

- (a) 元の表から集計する場合と、materialized view から読む場合の問い合わせ時間
- (b) 元の表に INSERT した後も、REFRESH するまで materialized view が古いままであること
- (c) REFRESH の実行中に別の接続の SELECT が待たされ、CONCURRENTLY なら待たされないこと（pg_locks で確認）
- (d) UNIQUE 索引が無いと CONCURRENTLY がエラーになること
- (e) REFRESH と最終更新時刻の記録を同じトランザクションで行うこと
- (f) REFRESH の前後で表と索引の格納先ファイル（relfilenode）が変わるか

ホストのポートは公開せず、`docker exec` で `psql` を呼びます。

```sh
docker run -d --name note-materialized-view -e POSTGRES_PASSWORD=pw postgres:17
# 起動を待ってから
docker exec -i note-materialized-view psql -U postgres -q < setup.sql
bash run.sh note-materialized-view > output.txt 2>&1
docker rm -f note-materialized-view
```

`output.txt` は PostgreSQL 17.11（`postgres:17` イメージ）で実行した結果です。時間の値は実行環境で変わります。`setup.sql` は乱数の種を固定しているので、売上の合計値は同じ PostgreSQL のバージョンなら一致します。

(c) では、`refresher` が `daily_sales` のロックを取ったことを `pg_locks` で確かめてから `reader` を動かし、`reader` がロック待ち（`granted = f`）になるか読み終わるまで `pg_locks` を読み続けます（どちらも上限 200 回、`docker exec` 1 回で約 0.1 秒）。そのため、固定の `sleep` に頼らず、REFRESH が 1 秒未満で終わる環境でも途中のロックを観測できます。前提は、REFRESH が `pg_locks` を数回読む間（数百 ms）より長く掛かることです。500 万件の集計ならこの条件を満たします。

`run.sh` は初期状態（`setup.sql` を流した直後）から 1 回だけ実行する前提です。もう一度実行する時は、`setup.sql` から流し直し、`DROP TABLE IF EXISTS mv_refresh_log;` も実行してください。
