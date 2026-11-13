#!/bin/sh
# Saleor の Order に「合計」の列が足された時期と PR を、migration の追加の履歴から出す。
# 使い方: sh saleor_history.sh <作業用のディレクトリ>
set -eu
dir=$(cd "${1:?作業用のディレクトリを指定する}" && pwd)
[ -d "$dir/saleor" ] || git clone -q --filter=blob:none https://github.com/saleor/saleor.git "$dir/saleor"
cd "$dir/saleor/saleor/order/migrations"
for m in 0001_initial.py 0098_discounts_relation.py 0105_order_total_paid_amount.py \
         0148_auto_20220519_1118.py 0180_auto_20231108_0908.py 0228_add_order_base_prices.py; do
  printf '%-40s ' "$m"
  git log --diff-filter=A --format='%cs %h %s' -- "$m" | tail -1
done
# 値引きの判定用の税抜きの合計を total に書き始めた PR と、それを別の列に移した PR
git -C "$dir/saleor" log -1 --format='%cs %h %s' eb0c3f25e
git -C "$dir/saleor" log -1 --format='%cs %h %s' c69c56cae
