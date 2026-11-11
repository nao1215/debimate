#!/usr/bin/env bash
# 実験 3: 終わらずに書き続けるプログラムを head -n 1 につなぎ、
# head が先に終わった後、書く側がどう終わるか（終了コードと標準エラー）を見る。
set -u
cd "$(dirname "$0")"
for c in "bin/loop_c" "python3 src/loop.py" "bin/loop_go" "bin/loop_rs" "gnuyes" "yes"; do
  err=$(mktemp)
  $c 2>"$err" | head -n 1 >/dev/null
  code=${PIPESTATUS[0]}
  printf '== %s\nexit=%s\n' "$c" "$code"
  head -c 2000 "$err"; echo
  rm -f "$err"
done
