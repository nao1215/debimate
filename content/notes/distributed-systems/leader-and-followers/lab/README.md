# Leader and Followers の実験

Docker と Python 3 と psycopg 3（`pip install "psycopg[binary]"`）が要る。この lab/ の中で実行する。
ポート 55432・55433 と、Docker のネットワーク lf-net・lf-raft を使う。

| ファイル | 中身 |
|---|---|
| cluster.sh | PostgreSQL 17 の Leader 1 台と Follower 1 台を作る（`./cluster.sh up`）・消す（`./cluster.sh down`） |
| stale_read.py | コミットの直後に Follower を読む 2000 回を、4 つの設定で数える。出力は out_stale_read.txt と out_stale_read.json |
| failover.py | Follower を外して書き、Leader を落として Follower を昇格させる。`python failover.py async`・`sync`・`sync-cancel`。出力は out_failover_*.txt |
| raft.py | etcd v3.5.17 の 3 台で Leader をネットワークから外し、外した Leader が降りる時刻とログも記録する（標準ライブラリだけ）。出力は out_raft.txt |

```sh
./cluster.sh up && python stale_read.py
python failover.py async      # failover.py は毎回 cluster.sh up で作り直す
python raft.py
./cluster.sh down
```

時刻はマシンの負荷で変わる。出力は 2026-11-17 に 1 台のマシン（Docker 29.2.1、PostgreSQL 17.11）で取ったもの。
