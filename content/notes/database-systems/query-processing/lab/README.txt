Query Processing ノートの 2 枚の図（images/query_processing_selectivity.svg、
images/query_processing_plan_cost.svg）の元になる PostgreSQL 17 の実測。

再現手順（Docker と postgres:17 のイメージが必要。約 30 秒）:

    ./run.sh > output.txt
    uv run --with matplotlib python ../figures.py

run.sh はコンテナ note-query-processing を起動し、ホストのポートは公開せずに
docker exec で experiment.sql を流し、終了時に削除する。

experiment.sql の内容:
  - users 1 万件（country と city はどの値も 1%、東京の 100 件は全て JP）で、
    country 単独・city 単独・両方の条件の推定と実際のレコード数を EXPLAIN ANALYZE で比べ、
    CREATE STATISTICS (dependencies) を作った後の推定も取る。
  - orders 100 万件（1 人 100 件、利用者ごとに連続）と結合する問い合わせで、
    enable_* で他の結合方法を外して 3 候補（hash join / nested loop + index scan /
    両方を整列した merge join）の見積もりコストと、EXPLAIN ANALYZE 5 回の実行時間の中央値を取る。
    並列実行と JIT は切る。
  - 比較用に、注文を利用者に散らして入れた orders_scattered での既定の計画と候補 2 のコスト。

output.txt は PostgreSQL 17.11、32 コアの Linux での結果。selectivity の部分は再実行で一致する。
結合の部分は ANALYZE の標本抽出で rows の推定と cost の小数がわずかに動き（例: rows=9985 と 9990）、
実行時間はマシンと実行ごとに変わる。
