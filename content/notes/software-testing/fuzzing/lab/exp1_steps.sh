#!/usr/bin/env bash
# 実験 1 の補足: FuzzByteByByte と同じ対象で、"FUZZ" と一致した先頭のバイト数が
# 初めて増えた時の呼び出し回数と経過時間を記録する。5 回走らせる。
#
# 記録のための先頭の比較（prefixLen）も計測される側のコードなので、回数は exp1_magic.sh の
# FuzzCount とは別の条件の値になる。
#
# 出力の列: 回 一致したバイト数 呼び出し回数 経過ミリ秒 入力の先頭 4 バイト
set -u
cd "$(dirname "$0")/magic"
out=../output/exp1_steps.tsv
: > "$out"
for i in 1 2 3 4 5; do
  go clean -fuzzcache; rm -rf testdata
  log=$(mktemp "${TMPDIR:-$HOME/.cache}/steps.XXXXXX")
  STEPLOG=$log go test -run '^$' -fuzz '^FuzzSteps$' -parallel 1 -fuzztime 60s . >/dev/null 2>&1
  sed "s/^/$i\t/" "$log" >> "$out"
  rm -f "$log"
done
rm -rf testdata
cat "$out"
