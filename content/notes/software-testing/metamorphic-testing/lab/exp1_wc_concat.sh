#!/usr/bin/env bash
# 関係「jz run wc A B = jz run wc A ++ jz run wc B」を検証する。
# 2 回に分けて読んだ結果をつなげたものと、1 回で読んだ結果を比べる。
set -euo pipefail
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
cd "$work"

printf 'a b\nc\n' > a.txt   # 2 行 3 語 6 バイト
printf 'hello\n' > b.txt    # 1 行 1 語 6 バイト
printf 'x\n'     > total    # 「total」という名前のファイル

check() {
  local together separate
  together=$(jz run wc "$@")
  separate=$(for f in "$@"; do jz run wc "$f"; done | jq -cs 'add')
  echo "\$ jz run wc $*"
  echo "together: $together"
  echo "separate: $separate"
  if [ "$together" = "$separate" ]; then echo "relation: holds"; else echo "relation: BROKEN"; fi
  echo
}

jz --version
wc --version | head -1
echo
check a.txt b.txt
check a.txt total
echo "\$ jz run wc total"
jz run wc total
echo
echo "\$ jz run wc --total=never a.txt total"
jz run wc --total=never a.txt total

# GNU 版の wc があれば、日本語のロケールで合計行の名前が変わることも見る
if command -v gnuwc >/dev/null; then
  echo
  echo "\$ LANG=ja_JP.UTF-8 gnuwc a.txt b.txt | jz --parser wc"
  LANG=ja_JP.UTF-8 LC_ALL=ja_JP.UTF-8 gnuwc a.txt b.txt | jz --parser wc
fi
