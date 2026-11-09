# ローカル実験

DuckDB の CLI だけで実行できます。`output.txt` は DuckDB v1.5.5（Linux、32 スレッド）で実行した結果です。計測の前に `enable_external_file_cache` を無効にし、キャッシュから返った読み込みがログから漏れないようにしています。

```sh
mkdir -p /tmp/columnar-lab && cd /tmp/columnar-lab
duckdb < /path/to/columnar.sql > output.txt
```

作業ディレクトリに CSV 1 個と Parquet 4 個（合計約 318 MB）を書き出します。データは `range()` と `hash()` から作るので、同じ版の DuckDB なら毎回同じファイルになります。ネットワークには接続しません。終わったらディレクトリごと削除してください。

- 読んだバイト数は、DuckDB の `FileSystem` ログ（`enable_logging`）から `op = READ` の `bytes` を合計した値です。
- 触れた row group は、読んだ位置（`pos`）を `parquet_metadata()` の列チャンクの範囲に当てはめて数えています。
- `Run Time` は環境とページキャッシュの状態で変わります。比べるなら同じマシンの 2 回目以降の値を見てください。
- `enable_logging` を呼ぶと CLI が WARNING を 1 回表示しますが、結果には影響しません。
