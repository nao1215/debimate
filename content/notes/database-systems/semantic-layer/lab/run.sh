#!/bin/sh
# 実験の再現手順。sqly（v1.7.3 で確認）と、dbt-metricflow[duckdb] と dbt-duckdb を入れた Python 環境が要る。
#   uv venv .venv -p 3.12 && uv pip install -p .venv "dbt-metricflow[duckdb]" dbt-duckdb
set -eu
cd "$(dirname "$0")"
S=seeds
{ sqly --version; dbt --version 2>&1 | grep -E "installed|duckdb"; mf --version; python -c "import importlib.metadata as m; print(\"metricflow\", m.version(\"metricflow\"))"; } > output_versions.txt
sqly --sql-file naive.sql   $S/customers.csv $S/orders.csv $S/order_items.csv $S/payments.csv < /dev/null > output_naive.txt
sqly --sql-file revenue.sql $S/orders.csv $S/order_items.csv $S/payments.csv < /dev/null > output_revenue.txt
export DBT_PROFILES_DIR="$PWD"
dbt seed --full-refresh -q
dbt build -q
{
  echo '$ mf query --metrics paid_amount,items_sold --group-by order__customer__region'
  mf query --metrics paid_amount,items_sold --group-by order__customer__region
  echo '$ mf query --metrics revenue'
  mf query --metrics revenue
} 2>&1 | grep -v Initiating > output_mf.txt
mf query --metrics paid_amount,items_sold --group-by order__customer__region --explain 2>&1 | grep -v Initiating > output_mf_sql.txt
{
  echo '$ mf query --metrics paid_amount --group-by order_item__category'
  mf query --metrics paid_amount --group-by order_item__category || true
} 2>&1 | grep -v Initiating > output_mf_error.txt
