# Heartbeat ノートの実験

Linux と Python 3.10 以降で動きます。外部のパッケージは使いません。全て 127.0.0.1 の UDP で完結します。

| ファイル | 内容 |
|---|---|
| monitor_pause.py | monitor だけを SIGSTOP で 1.5 秒止め、動いている 2 台を落ちたと判定するかを、作り 4 通り × 20 回で数える（約 6 分） |
| monitor_pause_output.txt | 上の集計の出力 |
| monitor_pause.json | 試行ごとの送信・受信・判定の時刻 |
| gray_failure.py | 処理のループがデッドロックした node で、ハートビートと要求の結果を 5 秒記録する |
| gray_failure_output.txt | 上の集計の出力 |
| gray_failure.json | 送信元ごとの、ハートビートと要求の時刻 |

```sh
python3 monitor_pause.py 20 > monitor_pause_output.txt
python3 gray_failure.py > gray_failure_output.txt
```

時刻はどちらも `time.monotonic()` で、試行の開始からの秒数です。thread の作りで落ちたと判定するかはスレッドの順番で決まるので、回数は実行ごとに変わります。
