# Differential Testing ノートの実験

著者の環境: Ubuntu 26.04、GNU coreutils 9.7（`gnuls` など `gnu` を頭に付けた名前）、uutils coreutils 0.8.0 と 0.10.0（`/usr/lib/cargo/bin/coreutils/`。2026-11-12 07:00 に unattended-upgrades が 0.8.0 から 0.10.0 に上げた）、jz v0.9.1、iproute2 6.19.0 の `ip`、Docker の `postgres:17-alpine`、Python 3.14.4。

| ファイル | 内容 | 出力 |
|---|---|---|
| `exp1_gnu_uutils.py` | 同じ 32 個の呼び出しを GNU と uutils に渡し、stdout・stderr・終了コードを比べる | `output/exp1_gnu_uutils_0.8.0.txt`、`_0.10.0.txt`、各 `.json` |
| `exp2_native_json.py` | `ip -br link` / `ip -br addr` を jz で読んだ値と、`ip -j` の値を行ごとに比べる | `output/exp2_native_json.txt`、`exp2_before.json`、`exp2_after.json` |
| `exp3_group_by.sh` | GROUP BY に無い列を選ぶ SQL を SQLite と PostgreSQL に渡す | `output/exp3_group_by.txt` |

```sh
python3 exp1_gnu_uutils.py output/exp1_gnu_uutils_0.10.0.json
python3 exp2_native_json.py jz output/exp2_after.json
./exp3_group_by.sh                 # docker が要る
```

実験 2 の修正前の jz は、jsonize の e5f6c12 の 1 つ前（ab5ac30f）を `go build -buildvcs=false -o jz-old ./cmd/jz` でビルドし、`python3 exp2_native_json.py ./jz-old output/exp2_before.json` で走らせました。veth は docker のコンテナが動いている時にホストに現れます。公開用の出力では、ループバック以外のアドレスと MAC アドレス、`ls -l` の所有者を伏せています。

0.8.0 の結果は、更新の後に docker の `ubuntu:26.04` のイメージ（GNU 9.7、uutils 0.8.0）で python3 を入れ、一般ユーザーで同じスクリプトを実行して取りました。拡張属性を付けられるよう、作業ディレクトリはコンテナの中の /tmp です。

図は 1 つ上の `figures.py` が `output/` を読んで描きます（`python3 figures.py`）。
