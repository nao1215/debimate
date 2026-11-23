# lab

「Unicode Text Length」ノートの実験です。Go 1.26、Python 3.14、Node.js 22、Rust 1.100 で動かしました。

| ディレクトリ | 内容 | 実行 |
|---|---|---|
| count | 文字列を UTF-8 のバイト・UTF-16 のコード単位・コードポイント・書記素クラスター・表示幅で数える | `go run ./count` |
| langs | 家族の絵文字の長さを Go・Python・JavaScript・Rust・SQLite で数える | `go run langs/count.go`、`python3 langs/count.py`、`node langs/count.js`、`python3 langs/count_sqlite.py`、`rustc langs/count.rs` |
| limits | Bluesky の投稿の上限と、excelize で書いた Excel のセルの上限 | `go run ./limits` |
| truncate | 表示幅に収まる書記素クラスターだけを残して切り詰める | `go run ./truncate` |
| width | go-runewidth の幅を東アジアの設定の有無で比べる | `go run ./width` |
| width-rs-0.2.2、width-rs-0.2.3 | unicode-width の 2 つのバージョンで半角濁点などの幅を比べる | `cargo run` |
| bom | BOM 付きの CSV を Go の encoding/csv と Python の csv で読む | `go run ./bom`、`python3 bom/read_bom.py` |
| encoding | Shift_JIS のバイト列を x/text で読み書きする | `go run ./encoding` |
| iso2022jp | ESC を含む CSV を ISO-2022-JP で書いて読み直す | `go run ./iso2022jp` |
| sheetname | xäy と xÄy の表とシートを SQLite と excelize で作り、σ と ς を比べる | `go run ./sheetname`、`python3 sheetname/sqlite_names.py` |
| fullwidth | embargo v0.13.0 と v0.20.1 で全角のメールアドレス・電話番号を探す（別モジュール） | `cd fullwidth && go get github.com/nao1215/embargo@v0.13.0 && go run .` |

sqly の実行例は、`go install github.com/nao1215/sqly@v0.27.0`（BOM を外す前）、`@v1.0.0-rc7`、`@v1.0.0-rc8`、`@v1.7.5` を入れて、ノートに書いたコマンドで再現できます。
