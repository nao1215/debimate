#!/usr/bin/env bash
# 実験 1: .save の 7 つの設計と、失敗の種類を減らした仕様を、Apalache で 6 手まで全部調べる。
# 要るもの: quint 0.33.1（PATH）、JDK 21 以上（Apalache 0.62.4 を動かす）
set -u
cd "$(dirname "$0")"
mkdir -p output
{
  quint --version | sed 's/^/quint /'
  java -version 2>&1 | head -1
  for m in direct staged copied selfRestore rollback reported touched \
           selfRestore_renameOnly selfRestore_noRestoreFail selfRestore_noCopyFail \
           rollback_renameOnly rollback_noRestoreFail rollback_noCopyFail \
           reported_renameOnly reported_noRestoreFail reported_noCopyFail \
           touched_renameOnly touched_noRestoreFail touched_noCopyFail; do
    start=$(date +%s.%N)
    out=$(quint verify save.qnt --main=$m --invariant=atomic --max-steps=6 2>&1)
    end=$(date +%s.%N)
    verdict=$(echo "$out" | grep -oE '\[(ok|violation)\][^(]*' | head -1)
    printf '== %s: %s(%.1f s)\n' "$m" "$verdict" "$(echo "$end - $start" | bc)"
    echo "$out" | sed -n '/^An example execution/,/^\[violation\]/p' | grep -E 'State|disk|event|outcome|reported' | sed "s/$m::saveproto:://"
  done
} | tee output/exp1_verify.txt
# 表紙の図のため: 同じ「a の上書きが途中で失敗」で、a を戻せる設計かを調べる
{
  for m in selfRestore rollback reported touched; do
    out=$(quint verify save.qnt --main=$m --invariant=noRestoreAfterCopyFailOnA --max-steps=6 2>&1)
    verdict=$(echo "$out" | grep -oE '\[(ok|violation)\][^(]*' | head -1)
    printf '== %s: %s\n' "$m" "$verdict"
    echo "$out" | sed -n '/^An example execution/,/^\[violation\]/p' | grep -E 'State|disk|event|outcome' | sed "s/$m::saveproto:://"
  done
} | tee output/exp1_witness.txt
rm -rf _apalache-out
