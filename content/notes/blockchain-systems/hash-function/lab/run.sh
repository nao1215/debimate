#!/usr/bin/env bash
# Hash Function ノートの実験を再現する。gcc（OpenMP 付き）と python3 だけを使う。
# 公開ネットワークには接続しない。結果は output/ に書く。
#
#   bash run.sh            # 全部（32 スレッドで 10 分ほど）
#   bash run.sh poly       # Poly Network の名前の再探索だけ（同 90 秒ほど）
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p output
bin=$(mktemp -d "${TMPDIR:-.}/hashlab.XXXXXX")/selector_search
trap 'rm -rf "$(dirname "$bin")"' EXIT
gcc -O3 -march=native -fopenmp -o "$bin" selector_search.c

python3 keccak.py | tee output/keccak.txt
python3 length_extension.py | tee output/length_extension.txt

suffix='(bytes,bytes,uint64)'
"$bin" target 41973cd9 32 f "$suffix" | tee output/poly.txt
if [[ "${1:-}" == poly ]]; then exit 0; fi

# 先頭 n ビットだけを比べた時の、狙った値とどれでもよい 2 つの試行回数
printf 'kind\tn\ttries\n' >output/measure.tsv
for n in 8 12 16 20 24 28 32; do
  for seed in $(seq 1 200); do
    t=$("$bin" collide "$n" "$seed" "$suffix" | sed -E 's/.*tries=([0-9]+).*/\1/')
    printf 'collide\t%s\t%s\n' "$n" "$t" >>output/measure.tsv
  done
done
python3 -c 'import random; random.seed(1); print(" ".join(f"{random.getrandbits(32):08x}" for _ in range(30)))' >output/targets.txt
for n in 8 12 16 20 24 28; do
  count=30
  if [[ $n == 28 ]]; then count=8; fi
  for target in $(tr ' ' '\n' <output/targets.txt | head -n "$count"); do
    t=$("$bin" target "$target" "$n" f "$suffix" | sed -E 's/.*tries=([0-9]+).*/\1/')
    printf 'target\t%s\t%s\n' "$n" "$t" >>output/measure.tsv
  done
done
"$bin" collide 32 1 "$suffix" | tee output/collide32.txt
