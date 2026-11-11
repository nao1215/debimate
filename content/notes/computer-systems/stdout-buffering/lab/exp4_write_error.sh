#!/usr/bin/env bash
# 実験 4: 書き込みが必ず失敗する出力先（/dev/full は書くと ENOSPC を返す）と、
# 閉じた標準出力（>&-）へ hello を 1 行書き、失敗を報告するか（終了コードと標準エラー）を見る。
set -u
cd "$(dirname "$0")"
printf 'hello\n' > hello.txt
for c in "bin/hello_c" "python3 src/hello.py" "bin/hello_go" "bin/hello_rs" "gnucat hello.txt" "cat hello.txt"; do
  for dst in "/dev/full" "closed"; do
    err=$(mktemp)
    if [ "$dst" = closed ]; then $c 2>"$err" >&-; else $c 2>"$err" >/dev/full; fi
    code=$?
    printf '== %s > %s\nexit=%s\n' "$c" "$dst" "$code"
    head -c 200 "$err"; echo
    rm -f "$err"
  done
done
rm -f hello.txt
