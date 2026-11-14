# Mutation Testing ノートの実験

著者の環境と各ツールのバージョンは `output/environment.txt` にあります（2026-11-14、filesql 21fbc9c、metamon 459ef87、gremlins v0.6.0、Gleam 1.18.1、PostgreSQL 18.6）。

どのスクリプトも、渡した checkout は書き換えず、作業ディレクトリへコピーしてから触ります。

| ファイル | 内容 | 出力 |
|---|---|---|
| （手で実行） | filesql の checkout の最上位で `gremlins unleash --workers 4 ./dialect`。全出力は大きいので、生き残りの一覧・最後の要約・パッケージごとの集計だけを残した | `output/gremlins_dialect_lived.txt`、`output/gremlins_dialect_summary.txt`、`output/gremlins_dialect_by_package.tsv` |
| （手で実行） | `--diff` を `./dialect` と最上位 `.` に渡した dry-run の比較 | `output/gremlins_diff_dryrun.txt` |
| `exp_width_bucket.sh` | filesql の `widthBucket` に、gremlins が生き残らせた書き換え 5 種類を 1 つずつ入れ、既存のテストと `width_bucket_extra_test.go.txt` で落ちるかを見る | `output/width_bucket.txt` |
| （手で実行） | PostgreSQL 18.6（docker の postgres:18-alpine）で `SELECT width_bucket(...)` を実行した答え | `output/postgresql_width_bucket.txt` |
| `gleam_mutate.py` | Gleam 向けの小さな mutation testing。演算子を 1 か所ずつ書き換えて `gleam test` を回す | `output/gleam_relation.json` |
| `exp_gleam.sh` | metamon の relation.gleam に `gleam_mutate.py` を掛け、生き残った行を `panic` にしてテストが届くかを見て、L235 のミュータントが `broken_sut_test.gleam.txt` の誤った関数を通すかを見る | `output/gleam.txt`、`output/gleam_relation.json` |

```sh
./exp_width_bucket.sh ~/ghq/github.com/nao1215/filesql "$HOME/.cache/mt-work"   # 1 分ほど
./exp_gleam.sh ~/ghq/github.com/nao1215/metamon "$HOME/.cache/mt-work"           # 2 分ほど（gleam と erl が PATH に要る）
```

gremlins は `go install github.com/go-gremlins/gremlins/cmd/gremlins@v0.6.0` で入れました。dialect 全体は 4 並列で 24 分 55 秒かかります。

図は 1 つ上の `figures.py` が `output/` を読んで描きます（`python3 figures.py`）。
