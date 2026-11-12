#!/usr/bin/env bash
# 本人の実文（content/post/ja + content/weeknotes）に、その表現があるかを数える。
#
#   bash author_grep.sh "壊れ方を持"
#   bash author_grep.sh "を取りこぼ" "が積み上が" "に書き直"
#
# 使い所は、名詞と動詞の結びつきに自信が無い時である。規則では判定できない
# （「壊れ方を持つ」は文法的に正しく、style_check.sh も omokage も通す）。
# 本人が 54 万字で 1 度も書いていない組み合わせなら、それは本人の言い方ではない。
#
# 0 件でも必ず誤りとは限らない。題材が違えば語も違う。判定は
# 「同じ意味を本人がどう書いているか」を次の検索で探して決める。
set -u
REPO="${DEBIMATE_REPO:-$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/.." && pwd)}"
CORPUS=("$REPO"/content/post/ja/*/index.md "$REPO"/content/weeknotes/*/*/index.md)
NOTES=("$REPO"/content/notes/*/*/index.md)

[ $# -eq 0 ] && { sed -n '2,14p' "$0" | sed 's/^# \?//'; exit 1; }

printf '%-24s %8s %8s   %s\n' "表現" "本人" "ノート" "判定"
printf '%-24s %8s %8s   %s\n' "------------------------" "--------" "--------" "----"
for q in "$@"; do
  a=$(grep -oh -- "$q" "${CORPUS[@]}" 2>/dev/null | wc -l)
  n=$(grep -oh -- "$q" "${NOTES[@]}" 2>/dev/null | wc -l)
  if [ "$a" -eq 0 ] && [ "$n" -gt 0 ]; then v="ノート専用。言い換える"
  elif [ "$a" -eq 0 ];                  then v="本人に用例なし"
  else                                        v="本人が使う"; fi
  printf '%-24s %8s %8s   %s\n' "$q" "$a" "$n" "$v"
done

echo
echo "本人の用例（最大 5 件）:"
for q in "$@"; do
  hits=$(grep -oh -- ".\{0,26\}$q.\{0,20\}" "${CORPUS[@]}" 2>/dev/null | head -5)
  if [ -n "$hits" ]; then echo "  [$q]"; echo "$hits" | sed 's/^/    /'; fi
done
