# Secrets in Logs の実験

ノート「Secrets in Logs」で使った Go の実験です。シークレットの値は全て `CANARY-` で始まる説明用の偽物です。外部のサービスには何も送りません（OTel は手元の `SpanRecorder` だけを使います）。

| コマンド | 確かめること |
|---|---|
| `go run . filter` | slog の `ReplaceAttr` でキーの名前から消すフィルターを、`fmt.Sprint` で文字列にした値が素通りする |
| `go run . wrapped` | 書式化で中身を出さない型も、外側の構造体の非公開フィールドに置くと `%+v` で中身が出る |
| `go run . error` | `strconv.Atoi`・`url.Parse` のエラー文に入力が入る。`URL.Redacted` はパスワードを隠す |
| `go run . stack` | 値で渡した配列の中身が `debug.Stack()` に出る。`GOTRACEBACK=none` でも出る |
| `go run . panic` | 未回復の panic のスタックに引数が出る。`GOTRACEBACK=none` ではメッセージだけになる |
| `go run . otel` | OTel の `RecordError` が `err.Error()` とスタックを span に入れる |
| `go test -v ./...` | 出口のテスト。不具合のある版（`TestImportLeaks`）は意図して落ちる |

実行した環境と結果は `output.txt` にあります。ログの時刻、スタックのファイルパスの先頭、テストの所要時間は短くするために削りました。Go 1.26.4（linux/amd64）、OTel SDK v1.47.0 です。スタックの番地は実行のたびに変わります。

ノートの図は `../figures.py` が `output.txt` から作ります。
