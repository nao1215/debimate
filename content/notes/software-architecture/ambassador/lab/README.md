# Ambassador のノートの実験

Redis 3 台（redis-a が最初の master）と Sentinel 3 台を Docker Compose で動かし、100ms ごとに 1 回 RPUSH する書き込み役を 4 通りの繋ぎ方で並べます。外部のサービスには繋ぎません。

| 書き込み役 | 繋ぎ方 |
|---|---|
| writer-static | redis-a の IP（172.28.0.11）に直接 |
| writer-sentinel | redis-py の `Sentinel.master_for()` |
| writer-ambassador | 同じネットワークを共有する HAProxy（127.0.0.1:6380）に、接続を張ったまま |
| writer-ambassador-new | 同じ HAProxy に、書くたびに新しい接続で |

```sh
./run.sh stop              # redis-a を止め、20 秒後に戻す
./run.sh stop-minrep       # 上と同じ。Redis に --min-replicas-to-write 1
./run.sh failover          # SENTINEL FAILOVER で切り替える（止めない）
./run.sh failover-kill     # 上と同じ。HAProxy に on-marked-down shutdown-sessions
./run.sh failover-minrep   # 上と同じ。Redis に --min-replicas-to-write 1
python3 summarize.py output/stop
```

`output/<シナリオ>/` に、書き込み役ごとの結果（`<役>.jsonl`）、最後の master に残った通し番号（`kept_<役>.txt`）、Sentinel と HAProxy のログ、`summarize.py` の出力（`summary.txt`）があります。成功と返った通し番号が `kept_<役>.txt` に無ければ「消えた」と数えます。使った版は `output/versions.txt` にあります。

図はノートの `figures.py` がこの出力から作ります。
