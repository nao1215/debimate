# ローカル実験

Python 3.8 以降の標準ライブラリだけで実行できます。

```sh
python3 run.py --json   # 時計のずれなし。最初に記録された span の JSON も表示
python3 run.py -0.1     # inventory の時計を 100 ms 遅らせる
```

`output.txt` は Python 3.14 で上の 2 つを続けて実行した結果です。時間と span ID は実行ごとに変わります。

127.0.0.1 の空きポートで 3 つの HTTP サーバー（gateway・orders・inventory）を 1 つのプロセス内のスレッドとして起動し、キューは `queue.Queue` で代用します。外部には接続しません。span は一時ディレクトリの JSON Lines ファイルに書き、終了時に削除します。

- inventory は 1 回目の呼び出しに 503 を返し、orders が 1 回だけ再試行します
- mailer は 1 回目の配送で ack の前に落ちた扱いにし、同じメッセージを再配送します
- 時計のずれは、inventory の `Tracer` が記録する時刻に足す `clock_offset` で再現します。OS の時計は変更しません
