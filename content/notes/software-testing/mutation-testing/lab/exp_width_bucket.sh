#!/usr/bin/env bash
# filesql の width_bucket に、gremlins が生き残らせた書き換え 5 種類を 1 つずつ入れ、
# 既存のテストと、PostgreSQL の答えを足したテストで落ちるかを見る。
# 使い方: exp_width_bucket.sh <filesql の checkout> <作業ディレクトリ>
# filesql の checkout は書き換えず、作業ディレクトリへコピーしてから触る。
set -euo pipefail
src=$1; work=$2; here=$(cd "$(dirname "$0")" && pwd)
rm -rf "$work/filesql"; mkdir -p "$work"
rsync -a --exclude .git "$src/" "$work/filesql/"
cd "$work/filesql/dialect"
f=internal/runtime/operators.go
cp "$f" "$work/operators.go.orig"

# 行番号: 書き換える前の文字列: 書き換えた後の文字列
mutants=(
  "207|if low > high {|if low >= high {"
  "211|if x < low {|if x <= low {"
  "214|if x >= high {|if x > high {"
  "219|(x-low)|(x+low)"
  "219|/(high-low)|/(high+low)"
)

existing=TestArithmeticFunctionsAreTranslated
added=TestWidthBucketAwayFromZero

verdict() { # テストが落ちれば KILLED、通れば LIVED
  if go test ./internal/runtime/ -run "^$1\$" -count=1 >/dev/null 2>&1; then echo LIVED; else echo KILLED; fi
}

echo "元のコード: 既存のテスト $(verdict $existing | sed s/LIVED/通る/)"
cp "$here/width_bucket_extra_test.go.txt" internal/runtime/width_bucket_extra_test.go
echo "元のコード: 足したテスト $(verdict $added | sed s/LIVED/通る/)"
for m in "${mutants[@]}"; do
  IFS='|' read -r line from to <<<"$m"
  cp "$work/operators.go.orig" "$f"
  python3 - "$f" "$line" "$from" "$to" <<'PY'
import sys
p, line, a, b = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4]
lines = open(p).read().split('\n')
assert a in lines[line - 1], (line, lines[line - 1])
lines[line - 1] = lines[line - 1].replace(a, b, 1)
open(p, 'w').write('\n'.join(lines))
PY
  printf 'L%s %-22s → %-22s 既存 %-6s 追加 %s\n' "$line" "$from" "$to" "$(verdict $existing)" "$(verdict $added)"
  # 足したテストが落ちた時に、ミュータントが返した値
  go test ./internal/runtime/ -run "^$added\$" -count=1 2>&1 | sed -n 's/.*_test.go:[0-9]*: /    /p' || true
done
cp "$work/operators.go.orig" "$f"
