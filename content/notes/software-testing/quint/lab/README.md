# Quint のノートの実験

[Quint のノート](https://debimate.jp/notes/software-testing/quint/) の実験です。sqly の `.save` が複数のファイルを書き戻す手順を Quint で書き、モデル検査と、本物の `.save` への trace の再生を行います。

## 要るもの

- quint 0.33.1（`npm i -g @informalsystems/quint@0.33.1`、または [GitHub Releases](https://github.com/quint-co/quint/releases/tag/v0.33.1) の実行ファイル）
- JDK 21 以上（`quint verify` が使う Apalache 0.62.4。JDK 17 では起動しない）
- Go 1.26.11 以上と、[sqly](https://github.com/nao1215/sqly) の commit 4f67868 の checkout（実験 2）

手元では Linux（amd64）、Node.js 22.22.1、Temurin 21.0.13、Go 1.26.11 で回しました。

## ファイル

| ファイル | 中身 |
|---|---|
| `counter.qnt` | 本文の最初の小さな例 |
| `save.qnt` | `.save` の 7 つの設計（220a85f より前、220a85f、23dcc5a、ff97dc2・0ee1d88、3036574、663bd7a、1742eca）と、失敗の種類を減らした仕様 |
| `exp1_verify.sh` | 実験 1。全ての設計を `quint verify` で 6 ステップまで調べる → `output/exp1_verify.txt`。表紙の図の、a を戻せるかの確認 → `output/exp1_witness.txt` |
| `exp2_traces.sh` | 実験 2 の前半。1742eca の設計から trace を 500 本書き出す → `traces/`、`output/exp2_traces.txt` |
| `exp2_replay.sh` | 実験 2 の後半。`SQLY=<checkout>` を付けて回す。trace の再生と rapid を、今の sqly と 3 つの変異で回す → `output/exp2_replay.txt` |
| `savemodel_test.go` | 実験 2 の Go のテスト。`exp2_replay.sh` が sqly の `shell/` に写して回し、終わったら消す |
| `exp3_runtime.sh` | 実験 3。空の HOME と、node を外した PATH で、何をダウンロードし、何が必要かを測る → `output/exp3_runtime.txt` |

```sh
./exp1_verify.sh
./exp2_traces.sh
SQLY=$HOME/src/sqly ./exp2_replay.sh
WORK=/path/to/scratch ./exp3_runtime.sh
```

`exp2_replay.sh` は sqly の `shell/save.go` を `sed` で書き換えて変異を作り、`git checkout` で戻します。作業中の変更がある checkout では回さないでください。
