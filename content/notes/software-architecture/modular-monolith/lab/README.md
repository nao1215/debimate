# ローカル実験: モジュール境界の違反をgo build と CI で止める

Go 1.22 以降で実行できます。外部の依存はありません。`output.txt` は Go 1.26.4 で実行した結果です。

```sh
./run.sh
```

`run.sh` は `shop/` を一時ディレクトリに複製し、境界を破る変更を 1 つずつ入れて `go build ./...` と `shop/depcheck.sh` を実行します。`shop/` 自体は変更せず、一時ディレクトリは終了時に削除します。

| 番号 | 入れる変更 | 止めるもの |
| --- | --- | --- |
| [0] | 変更なし | なし（成功） |
| [1] | `billing` が `orders/internal/store` を import | `go build`（internal の規則） |
| [2] | `orders` が `billing` を import | `go build`（import の循環） |
| [3] | `orders/notify` が `billing` を import | `depcheck.sh`（モジュール間の循環） |
| [4] | `billing` が Go モジュールの根の `internal/ordersql` を import | `depcheck.sh`（許可していない依存） |

`shop/` だけでも動かせます。

```sh
cd shop
go run ./cmd/shop   # charged 1200 yen for A-1
./depcheck.sh       # OK: モジュール間の import は全て許可された向きです
```

一時ディレクトリは git の管理外なので、`run.sh` は `GOFLAGS=-buildvcs=false` を設定してビルドします。
