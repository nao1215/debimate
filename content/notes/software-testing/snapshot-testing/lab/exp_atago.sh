#!/usr/bin/env bash
# Record and compare the same specs with atago v0.4.2 (before the normalization
# fixes) and v0.26.1, and write what each version stored to output/atago.txt.
#
#   ./exp_atago.sh [WORKDIR]
#
# WORKDIR holds the two atago binaries and a scratch copy of specs/
# (default: ./.work, which is not committed).
set -u
here=$(cd "$(dirname "$0")" && pwd)
work=${1:-$here/.work}
out=$here/output/atago.txt
mkdir -p "$work/bin" "$here/output"

for v in 0.4.2 0.26.1; do
  if [ ! -x "$work/bin/atago-$v" ]; then
    GOBIN="$work/bin/v$v" go install "github.com/nao1215/atago@v$v"
    mv "$work/bin/v$v/atago" "$work/bin/atago-$v"
  fi
done

: > "$out"
log() { printf '%s\n' "$*" >> "$out"; }
show() { # show the stored golden with control characters made visible
  sed -n 'l' "$1" | sed 's/^/    /' >> "$out"
}

# run VERSION SPEC RECORD_HOME VERIFY_HOME
run() {
  local v=$1 spec=$2 rec_home=$3 ver_home=$4
  local dir=$work/run-$v-${spec%.atago.yaml}
  rm -rf "$dir" && mkdir -p "$dir" && cp "$here/specs/$spec" "$dir/"
  (cd "$dir" && HOME=$rec_home "$work/bin/atago-$v" run --update-snapshots "$spec" > /dev/null)
  log "== atago v$v  $spec  (record: HOME=$rec_home, verify: HOME=$ver_home)"
  log "  golden:"
  show "$dir"/snapshots/*.txt
  local verdict
  verdict=$(cd "$dir" && HOME=$ver_home "$work/bin/atago-$v" run "$spec" | tail -1)
  log "  verify: $verdict"
}

for v in 0.4.2 0.26.1; do
  run "$v" root.atago.yaml / /home/nao
  run "$v" home.atago.yaml /home/nao /home/nao
  run "$v" crlf.atago.yaml "$HOME" "$HOME"
  run "$v" secret.atago.yaml "$HOME" "$HOME"
done

# Masking hides what it masks: record a 2026 timestamp, then verify an output
# whose timestamp went back to 1970, and one that lost the time of day.
v=0.26.1
dir=$work/run-$v-timestamp
rm -rf "$dir" && mkdir -p "$dir" && cp "$here/specs/timestamp.atago.yaml" "$dir/"
(cd "$dir" && "$work/bin/atago-$v" run --update-snapshots timestamp.atago.yaml > /dev/null)
log "== atago v$v  timestamp.atago.yaml"
log "  golden:"
show "$dir/snapshots/timestamp.txt"
for change in 's/2026-11-14T10:00:00Z/1970-01-01T00:00:00Z/' 's/2026-11-14T10:00:00Z/2026-11-14/'; do
  sed "$change" "$dir/timestamp.atago.yaml" > "$dir/changed.atago.yaml"
  printed=$(grep -o 'created: [^\\]*' "$dir/changed.atago.yaml")
  log "  verify with \"$printed\": $(cd "$dir" && "$work/bin/atago-$v" run changed.atago.yaml | tail -1)"
done
cat "$out"
