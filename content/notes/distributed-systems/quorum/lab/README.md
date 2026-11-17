# Quorum の実験

Docker と、Python の cassandra-driver 3.29.2（`pip install cassandra-driver==3.29.2`）が要る。この lab/ の中で実行する。
Docker のネットワーク q-net と、コンテナ q1・q2・q3 を使う。1 台あたりのヒープは 768MB。

| ファイル | 中身 |
|---|---|
| cluster.sh | Cassandra 5.0.6 の 3 台を作る（`./cluster.sh up`、3 分ほど掛かる）・消す（`./cluster.sh down`）。キースペース lab をレプリカ 3 つで作る |
| timeout_write.py | q2・q3 を docker pause で止めて QUORUM で書き、戻した後に各台の値を 0.5 秒ごとに読む。出力は out_timeout_write.txt と out_timeout_write.json |
| out_timeout_write_logs.txt | 同じ回の q2 のログ（古すぎる書き込みを捨てた行）と q1 のログ（hint を送り終えた行）。`docker logs` から grep で抜いた |

```sh
./cluster.sh up
python timeout_write.py > out_timeout_write.txt
./cluster.sh down
```

各台を coordinator にした ONE の読み取りが自分のレプリカを読むように、cluster.sh は snitch を GossipingPropertyFileSnitch にし、dynamic snitch を切っている。
時刻はマシンの負荷で変わる。出力は 2026-11-17 に 1 台のマシン（Docker 29.2.1、Python 3.12）で取ったもの。
時刻と結果は回ごとに揺れる。同じマシンで回し直すと、DOWN の判定は約 19〜23 秒、戻してから hint が届くまでは 0〜5 秒で、戻した瞬間に hint が届いて古い v1 が見えない回もあった。
q2 を coordinator にした QUORUM の読み取りがどの 2 台を読むかもリングの並びで決まり、q2 と q3 を読む回では、hint が届くまで QUORUM でも v1 が返る。
