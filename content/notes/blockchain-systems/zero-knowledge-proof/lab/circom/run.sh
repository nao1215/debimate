#!/usr/bin/env bash
# 実験を走らせて、結果を ../output/ に書く（先に setup.sh）
set -eu
cd "$(dirname "$0")"
./iszero.sh 2>&1 | sed 's/\x1b\[[0-9;]*m//g' | tee ../output/iszero.txt
node bench.mjs | tee ../output/bench.tsv
{ node --version; npm ls --depth=0 2>/dev/null | tail -n +2; npx circom2 --version; } > ../output/versions.txt
