#!/bin/sh
# 実験 1・2: 修正前の Distinct に、同じ性質を testing/quick と rapid で掛ける。
# 種 1〜100 で回し、見つけたか・何回目の入力か・報告された反例の行数を TSV に出す。
# 狭い生成器（narrow）と広い生成器（broad）の両方。入力は 1 回の実行につき最大 500 個。
set -eu
cd "$(dirname "$0")/distinct"
out=../output/exp1_shrink.tsv
work=$(mktemp -d "${TMPDIR:-$HOME/.cache}/pbtlab.XXXXXX")
trap 'rm -rf "$work"' EXIT
go test -c -o "$work/distinct.test" .
printf 'tool\tgen\tseed\tfound\tcase\trows\tcounterexample\n' > "$out"
for gen in narrow broad; do
  SEEDS=100 GEN=$gen "$work/distinct.test" -test.run '^TestQuickSeeds$' -test.v \
    | grep '^quick' | sed "s/^quick\t\t/quick\tnarrow\t/" >> "$out"
  for seed in $(seq 1 100); do
    line=$(GEN=$gen "$work/distinct.test" -test.run '^TestRapid$' -rapid.checks=500 \
      -rapid.seed="$seed" -rapid.nofailfile 2>&1 | grep 'failed after' || true)
    if [ -z "$line" ]; then
      printf 'rapid\t%s\t%s\tno\t-\t-\t-\n' "$gen" "$seed" >> "$out"
    else
      n=$(echo "$line" | sed -E 's/.*failed after ([0-9]+) tests.*/\1/')
      rows=$(echo "$line" | sed -E 's/.*反例 ([0-9]+) 行.*/\1/')
      ce=$(echo "$line" | sed -E 's/.*行: (\[.*\]): Distinct.*/\1/')
      printf 'rapid\t%s\t%s\tyes\t%s\t%s\t%s\n' "$gen" "$seed" "$n" "$rows" "$ce" >> "$out"
    fi
  done
done
python3 - ../output/exp1_shrink.tsv > ../output/exp1_summary.txt <<'PY'
import csv, statistics, sys
rows = list(csv.DictReader(open(sys.argv[1]), delimiter='\t'))
for tool in ('quick', 'rapid'):
    for gen in ('narrow', 'broad'):
        g = [r for r in rows if r['tool'] == tool and r['gen'] == gen]
        f = [r for r in g if r['found'] == 'yes']
        line = f'{tool}\t{gen}\tfound {len(f)}/{len(g)}'
        if f:
            cs = [int(r['case']) for r in f]
            rs = [int(r['rows']) for r in f]
            line += f'\tcase median {statistics.median(cs)} max {max(cs)}'
            line += f'\trows min {min(rs)} median {statistics.median(rs)} max {max(rs)}'
        print(line)
PY
cat ../output/exp1_summary.txt
# 種 1 で rapid が縮める途中で破れた表を順に残す（続けて同じ表は 1 つにまとめる）。
rm -f "$work/steps.txt"
SHRINKLOG="$work/steps.txt" "$work/distinct.test" -test.run '^TestRapid$' -rapid.checks=500 \
  -rapid.seed=1 -rapid.nofailfile > /dev/null 2>&1 || true
uniq "$work/steps.txt" > ../output/exp1_shrink_steps_seed1.txt
