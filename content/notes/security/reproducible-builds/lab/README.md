# ローカル実験

Reproducible Builds のノートに載せた実験の再現用ファイルです。外部のサービスには成果物を送りません。

| ファイル | 内容 |
| --- | --- |
| `build.sh` | `project/` を作って tar.gz を標準出力に書く。引数の段階 0〜5 で、固定する項目を 1 つずつ増やす |
| `run.sh` | `build.sh` を条件の違う 2 つのコンテナ（ビルダー A・B）で動かし、段階ごとに sha256 を比べる |
| `diff.sh` | 段階 3 の成果物を 2 つ作り、diffoscope で差分を表示する。diffoscope をコンテナ内で apt から入れるため、ネットワークに接続する |
| `main.go`・`go-build.sh` | 同じ `main.go` を 2 つのディレクトリで `go build` し、`-trimpath` の有無でハッシュを比べる |
| `output.txt`・`diff-output.txt`・`go-output.txt` | 上の 3 つのスクリプトを実行した結果 |

```sh
sh run.sh
sh diff.sh
sh go-build.sh
```

`run.sh` と `diff.sh` は Docker と `debian:stable-slim`（GNU tar 1.35、gzip 1.13、diffoscope 297）で、`go-build.sh` はホストの Go 1.26.4 で実行しました。コンテナは `--rm` で終了時に削除し、一時ディレクトリも終了時に消します。

段階 0〜1 のハッシュは実行した時刻で変わります。段階 2 以降は時刻を固定しているため、同じビルダーなら何度実行しても同じ値です。
