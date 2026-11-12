# Fuzzing ノートの実験

著者の環境: Ubuntu 26.04、Go 1.26.4（実験 0〜2）と 1.26.9（補足の実験 3）、32 スレッドの CPU、メモリはシステムに 64 GB。

| ファイル | 内容 | 出力 |
|---|---|---|
| `exp0_jsonize_retain.sh` | 修正前後の jsonize の表の読み取りに、256 列の見出しと `x` だけの行を渡し、保持したヒープを測る（`jsonize/retain.go.txt`） | `output/exp0_jsonize_retain.txt` |
| `exp1_magic.sh` | 1 バイトずつ比べる関数と 4 バイトまとめて比べる関数に fuzz を掛け、乱数の 1 億回とも比べる（`magic/`） | `output/exp1_magic.txt` |
| `exp1_steps.sh` | 1 バイトずつ比べる関数で、FUZZ と一致した先頭のバイト数が初めて増えた時の回数と経過時間を 5 回記録する（`magic/steps_test.go`） | `output/exp1_steps.tsv` |
| `exp2_parquet.sh` | filesql の修正前後で 473 バイトの Parquet を読む。`fuzz 300s` を付けると確保の上限を検査する fuzz を掛ける（`parquet/`） | `output/exp2_parquet.txt`、`output/exp2_fuzz_ceiling.txt`、`output/crashers/` |
| `exp3_hang.sh` | 1 つの入力で 3・8・12 秒眠る fuzz の関数で、`go test -fuzz` が失敗にする時間を確かめる（`hang/`） | `output/exp3_hang.txt` |

```sh
./exp0_jsonize_retain.sh   # systemd-run でメモリを 8 GB に制限して走らせる
./exp1_magic.sh            # 10 分ほど
./exp1_steps.sh            # 1 分ほど
./exp2_parquet.sh          # 473 バイトのファイルを修正前後で 1 回ずつ読む
./exp2_parquet.sh fuzz 300s
./exp3_hang.sh
```

exp0 と exp2 は jsonize・filesql を一時ディレクトリに clone します。一時ディレクトリは `$TMPDIR`、無ければ `$HOME/.cache` の下に作ります。/tmp が RAM 上の tmpfs の環境では、clone とビルドの成果物がメモリを圧迫するためです。

exp0 の修正前の jsonize は、表の読み取りに行の数の上限が無いので、行を増やすとヒープがそのまま増えます。160,000 行で 4.6 GB を保持するので、メモリに余裕の無い環境では行の数を減らしてください。

図は 1 つ上の `figures.py` が `output/` を読んで描きます（`python3 figures.py`）。
