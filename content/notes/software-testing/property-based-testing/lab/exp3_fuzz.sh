#!/bin/sh
# 実験 3: 同じ性質を go test -fuzz に掛ける。バイト列を表に読み替える（distinct_test.go の decode）。
# 修正前の鍵（KEY 無し）と修正後の鍵（KEY=fixed）で、それぞれ 5 回、1 回 60 秒まで回す。
# 見つけるまでの秒数と、fuzz が縮めた入力を読み替えた表を記録する。縮めた入力のバイト列は output/exp3_crashers/ に残す。回ごとに fuzz のキャッシュを消す。
set -eu
here=$(cd "$(dirname "$0")" && pwd)
out=$here/output/exp3_fuzz.txt
work=$(mktemp -d "${TMPDIR:-$HOME/.cache}/pbtlab.XXXXXX")
trap 'rm -rf "$work"' EXIT
: > "$out"
rm -rf "$here/output/exp3_crashers" && mkdir -p "$here/output/exp3_crashers"
for key in buggy fixed; do
  for run in 1 2 3 4 5; do
    rm -rf "$work/d" && cp -r "$here/distinct" "$work/d"
    cd "$work/d"
    go clean -fuzzcache # 前の回が見つけた入力を引き継がない
    start=$(date +%s.%N)
    log=$(KEY=$key go test -run '^$' -fuzz '^FuzzDistinct$' -fuzztime 60s -parallel 4 . 2>&1 || true)
    end=$(date +%s.%N)
    sec=$(echo "$end - $start" | bc)
    if echo "$log" | grep -q '反例'; then
      ce=$(echo "$log" | grep '反例' | tail -1 | sed -E 's/.*(反例 .*)/\1/')
      printf '%s\trun %s\tfound in %.1f s\t%s\n' "$key" "$run" "$sec" "$ce" >> "$out"
      cp testdata/fuzz/FuzzDistinct/* "$here/output/exp3_crashers/${key}_run$run.txt"
    else
      execs=$(echo "$log" | grep -o 'execs: [0-9]*' | tail -1)
      printf '%s\trun %s\tnot found in %.1f s\t%s\n' "$key" "$run" "$sec" "$execs" >> "$out"
    fi
    cd "$here"
  done
done
cat "$out"
