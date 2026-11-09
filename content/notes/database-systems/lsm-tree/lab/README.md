# ローカル実験

Python 3.11 以降の標準ライブラリだけで実行できます。

```sh
python3 lsm.py
```

`lsm.py` は、Memtable・SSTable・Bloom filter・tombstone と、leveled / size-tiered の 2 つの compaction を実装した最小の LSM-Tree です。compaction を行わない `none` も含め、同じ負荷（2 万種類のキーに 10 万回 put、1 万キーを delete、2 万回 get）で書き込み・読み取り・容量の増幅を測ります。乱数の seed は固定しているので、何度実行しても同じ結果になります。

`output.txt` は Python 3.14 で実行した結果です。`results.json` は、ノートの図を作る `../figures.py` が読む計測結果です。

データはメモリ上にだけ置き、ファイルには `results.json` 以外を書きません。
