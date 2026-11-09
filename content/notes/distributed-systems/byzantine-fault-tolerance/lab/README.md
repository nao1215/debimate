# ローカル実験

Python 3.8 以降の標準ライブラリだけで実行できます。ネットワークには接続しません。

```sh
python3 bft_quorum.py
```

`output.txt` は Python 3.14 で実行した結果です。

- 前半: n 台から n−f 台を選ぶ quorum の全ての組と、嘘つき f 台の全ての選び方を列挙し、2 つの quorum の重なりに残る正直なノードの最小数を出します。
- 後半: PBFT の pre-prepare と prepare だけを取り出した 1 ラウンドを、嘘つき 1 台（primary または backup）が送り先ごとに commit・abort・沈黙を選ぶ全通りで試します。commit と View Change は含めず、メッセージは全て届くものとしています。
