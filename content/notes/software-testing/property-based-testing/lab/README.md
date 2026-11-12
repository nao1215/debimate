# Property-Based Testing ノートの実験

著者の環境: Ubuntu 26.04、Go 1.26.4（`output/go_version.txt`）、rapid v1.3.0、32 スレッドの CPU。

`distinct/` は、filesql の frame パッケージの `Distinct` と行の鍵を作る関数を写したものです。修正前は commit 014315b の `makeRowKey`、修正後は commit 305c7bf の鍵の作り方を、実験で使う型（nil・string・int64）の分だけ写しています。frame パッケージは filesql v0.48.0 で削除されました。

| ファイル | 内容 | 出力 |
|---|---|---|
| `exp1_shrink.sh` | 修正前の鍵に同じプロパティを testing/quick と rapid で掛ける。狭い・広いジェネレーター、種 1〜100、各 500 入力。種 1 で rapid が縮める途中の表も残す | `output/exp1_shrink.tsv`、`output/exp1_summary.txt`、`output/exp1_shrink_steps_seed1.txt` |
| `exp2_fixed.sh` | 修正後の鍵に rapid でプロパティを掛ける。狭い・広い・2^53 の前後を混ぜたジェネレーター、種 1〜100、各 500 入力 | `output/exp2_fixed.tsv`、`output/exp2_summary.txt` |
| `exp3_fuzz.sh` | 同じプロパティを `go test -fuzz` に掛ける。修正前と修正後の鍵で 5 回ずつ、1 回 60 秒まで。回ごとに fuzz のキャッシュを消す | `output/exp3_fuzz.txt`、`output/exp3_crashers/` |

```sh
./exp1_shrink.sh   # 1 分ほど
./exp2_fixed.sh    # 1 分ほど
./exp3_fuzz.sh     # 最大 10 分
```

一時ディレクトリは `$TMPDIR`、無ければ `$HOME/.cache` の下に作ります。

テストは環境変数で切り替えます。`GEN` はジェネレーター（`narrow`・`broad`・`edge`、無ければ `narrow`）、`KEY=fixed` は修正後の鍵、`SEEDS` は testing/quick を回す種の数、`SHRINKLOG` は rapid が縮める途中でプロパティが破れた表を書き出すファイルです。

```sh
cd distinct
GEN=edge KEY=fixed go test -run TestRapid -rapid.checks=500 -rapid.seed=1 .
```

図は 1 つ上の `figures.py` が `output/` を読んで描きます（`python3 figures.py`）。
