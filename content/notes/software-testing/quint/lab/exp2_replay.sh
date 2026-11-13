#!/usr/bin/env bash
# 実験 2 の後半: trace を本物の .save に流すテストと、同じ失敗を rapid に引かせるテストを、
# 今の sqly と、過去の設計に戻した 3 つの変異で回す。
# 要るもの: SQLY に sqly の checkout（commit 4f67868、Go 1.26.11 以上）。先に exp2_traces.sh を回す。
set -u
LAB="$(cd "$(dirname "$0")" && pwd)"
: "${SQLY:?set SQLY to a checkout of github.com/nao1215/sqly at 4f67868}"
cp "$LAB/savemodel_test.go" "$SQLY/shell/savemodel_test.go"
cd "$SQLY"
run() {
  local name=$1
  QUINT_TRACES="$LAB/traces" go test ./shell/ -run 'TestSaveReplaysQuintTraces' -count=1 -v 2>&1 \
    | grep -E 'replayed|build failed' | sed "s/^ *savemodel_test.go:[0-9]*: /$name quint: /"
  for oracle in precise weak; do
    for seed in 1 2 3 4 5; do
      rm -rf shell/testdata/rapid
      if [ "$oracle" = weak ]; then w=1; else w=; fi
      WEAK_ORACLE=$w go test ./shell/ -run 'TestSaveRapidFaults' -count=1 -rapid.seed=$seed -v 2>&1 \
        | grep -oE '\[rapid\] (OK, passed [0-9]+ tests|failed after [0-9]+ tests: plan \{[^}]*\})' \
        | sed "s/^/$name rapid($oracle) seed=$seed: /"
    done
  done
}
show() {
  SAVE_SHOW=1 go test ./shell/ -run 'TestSaveShowOneRun' -count=1 -v 2>&1 | grep -E 'disk:|error:|oracle' | sed "s/^ *savemodel_test.go:[0-9]*: /$1 one run: /"
}
{
  go version
  run original
  show original
  # M1: 3036574・663bd7a と同じく、上書きの途中で失敗した対象自身を戻さない
  sed -i 's/^\t\tif touched {$/\t\tif false \&\& touched {/' shell/save.go; run M1_failed_target_not_restored; show M1_failed_target_not_restored; git checkout -q shell/save.go
  # M2: 3036574 と同じく、戻すのに失敗したことを捨てる
  sed -i 's/if rollbackErr := s.rollbackCommitted(done); rollbackErr != nil {/if rollbackErr := s.rollbackCommitted(done); false \&\& rollbackErr != nil {/' shell/save.go; run M2_restore_error_swallowed; git checkout -q shell/save.go
  # M3: 3036574 より前と同じく、移し終えた分を戻さない
  sed -i 's/if rollbackErr := s.rollbackCommitted(done); rollbackErr != nil {/if rollbackErr := func([]stagedWrite) error { return nil }(done); rollbackErr != nil {/' shell/save.go; run M3_no_rollback; git checkout -q shell/save.go
} | tee "$LAB/output/exp2_replay.txt"
rm -rf shell/testdata/rapid "$SQLY/shell/savemodel_test.go"
