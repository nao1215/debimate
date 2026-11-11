# ローカル実験

Docker と `postgres:17` イメージが使える環境で実行できます。DB のコンテナは CPU の 30 番と 31 番の 2 コアに固定する（`--cpuset-cpus=30,31`）ので、コアが 32 個未満のマシンでは番号を変えてください。手元のマシンでは、30 番と 31 番は別々の物理コアの片側の論理 CPU で、対になる論理 CPU は固定していないので、pgbench や他の処理が同じ物理コアに乗ることがあります。

```sh
./run.sh > output.txt            # 接続数ごとの計測（bench.csv）
./run_rate.sh > output_rate.txt  # 毎秒の件数を固定した計測（rate.csv）、接続の張り直し（connect.csv）、max_connections
```

どちらも専用の docker network を作り、DB のコンテナと、別のコンテナで動かす pgbench をそこで繋ぎます。ホストのポートは公開せず、永続ボリュームも作りません。終わるとコンテナと network を消します。

- `run.sh`: pgbench の初期化（`-s 20`）の後、`pgbench -S`（主キーで 1 件を読む SELECT だけ）を接続数 1〜512 本で 10 秒ずつ、各 5 回流す。`output.txt` の `load1` は各回の後の load average で、pgbench が張った接続の数だけ DB のプロセスが動くので、接続数とともに上がる
- `run_rate.sh`: `pgbench -S -R` で毎秒 1 万〜4 万件に固定し、接続 8 本と 256 本で各 3 回流す。次に、接続 8 本で、使い回す場合と取引ごとに張り直す場合（`-C`）を各 3 回比べる。最後に、`max_connections` が既定（100）の DB に 101 本の接続を張る

PostgreSQL 17.11 で実行した結果です。値は手元のマシンの状態で揺れます（同じ条件でも、接続 4 本の 5 回は毎秒 7.4 万〜12.6 万件でした）。

`-R`・`-P`・`-L` を付けない pgbench の `latency average` は計測値ではなく、「接続数 × 計測時間 ÷ 件数」で求めた値です。
