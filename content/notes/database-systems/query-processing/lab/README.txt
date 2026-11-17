Query Processing のノートの実験

PostgreSQL 18 と MySQL 8.4 を docker compose で動かし、次を測る。

1. 500 万行の events で、ORDER BY id LIMIT n の n を変えた時の実行計画と実行時間
   （利用者 1 の 10,000 行は id の末尾に固まり、他の利用者の行は全体に散らばる）
2. 同じ SQL で利用者 500 と利用者 1 を比べる
3. (user_id, id) の複合索引を足した時の実行時間
4. 関係のある 3 列（city・pref・region）の条件で、見積もった行数と実際の行数
   （CREATE STATISTICS の前と後）
5. 1,000 行の表を 2〜14 個結合する SQL で、計画を作る時間
   （FROM に表を並べる書き方と、JOIN で順に書く書き方）
6. MySQL で同じ形の SQL（ORDER BY id と、id と同じ値の列 seq での ORDER BY）

環境（2026-11-17 に実行）
- docker compose v2、Python 3（標準ライブラリだけ）
- postgres:18-alpine（PostgreSQL 18.6）、mysql:8.4（MySQL 8.4.11）
- 設定はどちらも既定値。時間は 5 回（MySQL は 3 回）の中央値で、実行のたびにぶれる

実行
    cd lab
    python3 run.py          # 10 分ほど。終わるとコンテナを消す（--keep で残す）
    cd .. && python3 figures.py

ファイル
- pg_setup.sql・mysql_setup.sql: 表を作る SQL
- run.py: 測定の手順
- result.json: 全ての測定値（図はここから描く）
- output.txt: 実行中に表示した行と実行計画
