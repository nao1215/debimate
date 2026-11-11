#!/usr/bin/env bash
# 実験 2: filesql の Parquet の読み取りに、メモリの上限を検査する fuzz を掛ける。
#
#   ./exp2_parquet.sh            fuzz が縮めた 473 バイトの Parquet を、修正前と修正後で 1 回ずつ読む
#   ./exp2_parquet.sh fuzz 300s  修正前と修正後に FuzzParquetCeiling を 300 秒ずつ掛ける
#
# 修正前は bd2f9e9 の 1 つ前、修正後は bd2f9e9。
set -eu
here=$(cd "$(dirname "$0")" && pwd)
mode=${1:-replay}
fuzztime=${2:-300s}
work=$(mktemp -d "${TMPDIR:-$HOME/.cache}/fuzzlab.XXXXXX")
trap 'rm -rf "$work"' EXIT

git clone -q https://github.com/nao1215/filesql "$work/filesql"
for rev in bd2f9e9^ bd2f9e9; do
  git -C "$work/filesql" checkout -q "$rev"
  echo "== filesql $(git -C "$work/filesql" rev-parse --short "$rev") ($rev)"
  if [ "$mode" = fuzz ]; then
    cp "$here/parquet/ceiling_test.go.txt" "$work/filesql/parser/zz_ceiling_test.go"
    go clean -fuzzcache
    (cd "$work/filesql" && go test ./parser -run '^$' -fuzz '^FuzzParquetCeiling$' -fuzztime "$fuzztime" 2>&1 |
      grep -E '^fuzz: elapsed|allocated|^ok|^FAIL' | tail -3) || true
    rm "$work/filesql/parser/zz_ceiling_test.go"
  else
    cp "$here/parquet/cost_test.go.txt" "$work/filesql/internal/reader/zz_cost_test.go"
    (cd "$work/filesql" && PAGE_HEADER_B64="$here/parquet/page_header.b64" \
      go test ./internal/reader -run '^TestPageHeaderCost$' -count=1 -v | grep 'allocated')
    rm "$work/filesql/internal/reader/zz_cost_test.go"
  fi
done
