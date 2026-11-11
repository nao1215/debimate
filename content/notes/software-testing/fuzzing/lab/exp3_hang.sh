#!/usr/bin/env bash
# 補足の実験: go test -fuzz は、1 つの入力の実行が何秒を超えると失敗にするか。
#
# 5 バイト以上の入力で SLEEP 秒眠る fuzz の関数を、3・8・12 秒で 40 秒ずつ走らせる。
set -u
cd "$(dirname "$0")/hang"
for s in 3 8 12; do
  go clean -fuzzcache; rm -rf testdata
  echo "== sleep ${s}s"
  SLEEP=$s go test -run '^$' -fuzz '^FuzzSleep$' -fuzztime 40s -parallel 1 . 2>&1 | grep -E '^--- FAIL|hung|^ok|^PASS'
done
rm -rf testdata
