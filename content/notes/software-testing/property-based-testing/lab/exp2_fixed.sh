#!/bin/sh
# 実験 2: filesql の修正（305c7bf）の鍵の作り方に、同じプロパティを rapid で掛ける。
# ジェネレーターは、狭い（narrow）・広い（broad）・2^53 の前後を混ぜた（edge）の 3 つ。種 1〜100、各 500 入力。
set -eu
cd "$(dirname "$0")/distinct"
out=../output/exp2_fixed.tsv
work=$(mktemp -d "${TMPDIR:-$HOME/.cache}/pbtlab.XXXXXX")
trap 'rm -rf "$work"' EXIT
go test -c -o "$work/distinct.test" .
printf 'gen\tseed\tfound\tcase\trows\tcounterexample\n' > "$out"
for gen in narrow broad edge; do
  for seed in $(seq 1 100); do
    line=$(KEY=fixed GEN=$gen "$work/distinct.test" -test.run '^TestRapid$' -rapid.checks=500 \
      -rapid.seed="$seed" -rapid.nofailfile 2>&1 | grep 'failed after' || true)
    if [ -z "$line" ]; then
      printf '%s\t%s\tno\t-\t-\t-\n' "$gen" "$seed" >> "$out"
    else
      n=$(echo "$line" | sed -E 's/.*failed after ([0-9]+) tests.*/\1/')
      rows=$(echo "$line" | sed -E 's/.*反例 ([0-9]+) 行.*/\1/')
      ce=$(echo "$line" | sed -E 's/.*行: (\[.*\]): Distinct.*/\1/')
      printf '%s\t%s\tyes\t%s\t%s\t%s\n' "$gen" "$seed" "$n" "$rows" "$ce" >> "$out"
    fi
  done
done
awk -F'\t' 'NR>1 {n[$1]++; if ($3=="yes") {f[$1]++; ce[$1" "$6]++}}
  END {for (g in n) print g"\tfound "f[g]+0"/"n[g]; for (k in ce) print "  "ce[k]"\t"k}' "$out" | sort > ../output/exp2_summary.txt
cat ../output/exp2_summary.txt
