# ローカル実験

Confused Deputy を、パス名を渡す設計とファイルディスクリプタを渡す設計で比べます。Python 3.9 以降の標準ライブラリだけで動きますが、2 つの UID を切り替えるために root 権限で起動します。手元のユーザーやファイルを触らないように、使い捨てのコンテナで実行してください。

```sh
docker run --rm --network none -v "$PWD":/lab:ro python:3.13-slim python3 /lab/run.py
```

このディレクトリで実行します。`output.txt` は Python 3.13.18（`python:3.13-slim`）で実行した結果です。

- UID 2001 がコンパイラ、UID 2002 が利用者（alice）を演じます。
- コンテナ内の一時ディレクトリに `SYSX/`（コンパイラだけが読み書きできる）と `alice/`（alice だけが読み書きできる）を作り、終了時に削除します。
- 2 つのプロセスは一時ディレクトリ内の Unix ドメインソケットで通信します。ネットワークは使いません（`--network none`）。
