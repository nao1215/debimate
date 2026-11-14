#!/usr/bin/env bash
# metamon の relation.gleam にミュータントを入れて gleam test を回し、
# 生き残った行にテストが届いているかと、L235 のミュータントが誤った関数を通すかを見る。
# 使い方: exp_gleam.sh <metamon の checkout> <作業ディレクトリ>
# metamon の checkout は書き換えず、作業ディレクトリへコピーしてから触る。
set -euo pipefail
src=$1; work=$2; here=$(cd "$(dirname "$0")" && pwd)
rm -rf "$work/metamon"; mkdir -p "$work"
rsync -a --exclude .git --exclude build "$src/" "$work/metamon/"
cd "$work/metamon"
f=src/metamon/relation.gleam
cp "$f" "$work/relation.gleam.orig"
plain() { sed 's/\x1b\[[0-9;]*m//g'; }

echo "== 0. 元のコードで gleam test を 1 回回す時間"
gleam test >/dev/null 2>&1   # 依存のコンパイルを済ませる
s=$(date +%s.%N); gleam test >/dev/null 2>&1; e=$(date +%s.%N)
printf 'gleam test 1 回: %.1f 秒\n' "$(echo "$e - $s" | bc)"

echo "== 1. ミュータントを 1 個ずつ入れて gleam test"
s=$(date +%s.%N)
python3 "$here/gleam_mutate.py" . "$f" "$here/output/gleam_relation.json"
e=$(date +%s.%N)
printf '全ミュータント: %.1f 秒\n' "$(echo "$e - $s" | bc)"

echo "== 2. 生き残った行の分岐を panic にして、テストが届くかを見る"
for spec in "55|left >=. right|{ panic } >=. right" "230|-> True|-> panic" "235|False -> False|False -> panic" \
            "252|-> True|-> panic" "257|False -> False|False -> panic"; do
  IFS='|' read -r line from to <<<"$spec"
  cp "$work/relation.gleam.orig" "$f"
  python3 - "$f" "$line" "$from" "$to" <<'PY'
import sys
p, line, a, b = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4]
lines = open(p).read().split('\n')
assert a in lines[line - 1], (line, lines[line - 1])
lines[line - 1] = lines[line - 1].replace(a, b, 1)
open(p, 'w').write('\n'.join(lines))
PY
  printf 'L%s: %s\n' "$line" "$(gleam test 2>&1 | plain | grep -oE '[0-9]+ passed.*' | tail -1)"
done

echo "== 3. 逆順で結果が変わる関数を all_equal で検査する"
cp "$work/relation.gleam.orig" "$f"
cp "$here/broken_sut_test.gleam.txt" test/zz_broken_sut_test.gleam
out=$(gleam test 2>&1 | plain || true)
printf '元のコード: %s\n' "$(echo "$out" | grep -oE '[0-9]+ passed.*' | tail -1)"
echo "$out" | grep -A6 "source input" | head -7 || true
sed -i '235s/False -> False/False -> True/' "$f"
printf 'L235 のミュータント: %s\n' "$(gleam test 2>&1 | plain | grep -oE '[0-9]+ passed.*' | tail -1)"
cp "$work/relation.gleam.orig" "$f"
rm test/zz_broken_sut_test.gleam
