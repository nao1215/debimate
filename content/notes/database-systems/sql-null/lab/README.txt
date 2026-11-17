NULL のノートの実験

run.py             同じ SQL を PostgreSQL 18・MySQL 8.4・SQLite 3.46・DuckDB 1.5 で実行する → output/results.json
orm.py             SQLAlchemy の not_in と exists が組み立てる SQL と結果（SQLite）→ output/orm.txt
perf.py            PostgreSQL で NOT IN と NOT EXISTS の時間を行数と work_mem を変えて測る → output/perf.json, perf_plans.txt
plan_threshold.py  既定の work_mem のまま行数を増やし、NOT IN の計画が変わる所を EXPLAIN で見る → output/plan_threshold.txt

準備:
  docker run -d --rm --name sqlnull-pg -e POSTGRES_PASSWORD=pw postgres:18
  docker run -d --rm --name sqlnull-my -e MYSQL_ROOT_PASSWORD=pw -e MYSQL_DATABASE=lab mysql:8.4
  DuckDB は CLI（duckdb）、SQLite は Python 標準の sqlite3、orm.py は pip install sqlalchemy（2.1.9 で実行）

perf.py は work_mem 64kB・80,000 行の NOT IN だけで約 4 分掛かる（2026-11-17、手元の PC）。
