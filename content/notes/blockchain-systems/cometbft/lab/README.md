# ローカル実験

Docker と Python 3.8 以降の標準ライブラリで実行できます。公式の `cometbft/cometbft:v0.38.26` イメージ（digest 固定）と、CometBFT に組み込まれた kvstore アプリケーションだけを使います。

```sh
python3 run.py      # 3 回繰り返す（1 回あたり約 4 分）
python3 run.py 1    # 1 回だけ
```

- コンテナ名は `note-cometbft-node0`〜`3`、ネットワークは `note-cometbft-net` `-a` `-b` で、全て `--internal`（外部に出られない）です。ホストのポートは公開しません。RPC はコンテナの中から `docker exec ... curl` で呼びます。
- バリデータの鍵は `cometbft testnet` が一時ディレクトリに生成する使い捨ての物です。公開のネットワークには接続しません。
- 終了時に（失敗した場合も）コンテナとネットワークと一時ディレクトリを削除します。
- `output.txt` は 2026-11-10 に 3 回実行した結果、`timeline.csv` はその 1 回目の 1 秒ごとの記録です。`../figures.py` が `timeline.csv` から図を作ります。
- 時刻と回数は、他の処理で負荷の高いマシン（負荷平均 20 前後）での実測です。
