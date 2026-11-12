# Transactional Outbox の実験

ノートの実験を再現するスクリプトです。PostgreSQL 18.6（Docker の postgres:18-alpine）、Python 3、psycopg 3.3.8 で動かしました。

```sh
docker run -d --name outbox-pg -p 55432:5432 -e POSTGRES_PASSWORD=pg \
  postgres:18-alpine -c wal_level=logical -c max_connections=200
python3 -m venv venv && venv/bin/pip install 'psycopg[binary]==3.3.8'
venv/bin/python outbox_lab.py crash      # コミットと送信の間で SIGKILL を 100 回
venv/bin/python outbox_lab.py overtake   # id 1 を先に取ったトランザクションが後でコミットする
venv/bin/python outbox_lab.py load       # 8 並列で 4,000 件、relay の読み方 3 通り × 処理時間 3 段 × 5 回
venv/bin/python outbox_lab.py stall      # 書き込み中の長いトランザクションと、トランザクション ID で読む relay
venv/bin/python outbox_lab.py ordering   # relay の数と、注文ごとのイベントの順番（5 回）
venv/bin/python outbox_lab.py ordering_trace  # relay 2 個で注文 4 の支払いが確定より先に届く様子（1 行の送信 0.2 秒）
venv/bin/python outbox_lab.py wal        # 論理デコーディングで読んだ順番
venv/bin/python outbox_lab.py wal_stall  # 長いトランザクションが開いている間の論理デコーディングと、SELECT だけのトランザクション
docker rm -f outbox-pg
```

各サブコマンドは表を作り直してから走り、結果を標準出力と `output/<名前>.json` に書きます。ブローカーの代わりに、別の DB（broker）の `events` 表へ届いた順に積みます。ノートの図は、1 つ上のディレクトリの `figures.py` が `output/` を読んで作ります。
