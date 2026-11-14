#!/usr/bin/env bash
# Pin the flowchart that markdown v0.13.0 generates in a golden file, run the
# golden test three times, render it with mermaid, then move to markdown v1.0.0
# and do the same. Writes output/flowchart.txt and the two renderings.
#
#   ./exp_flowchart.sh RENDER_DIR
#
# RENDER_DIR must contain render/render.mjs's dependencies (mermaid 11.16.1 and
# puppeteer 25.6.0) in node_modules; see README.md.
set -u
here=$(cd "$(dirname "$0")" && pwd)
render_dir=$1
out=$here/output/flowchart.txt
mkdir -p "$here/output"
cp "$here/render/render.mjs" "$render_dir/"
: > "$out"

for v in v0.13.0 v1.0.0; do
  (
    cd "$here/flowchart" || exit 1
    go get "github.com/nao1215/markdown@$v" > /dev/null 2>&1
    {
      echo "== markdown $v"
      echo "-- go test against the golden recorded with the previous version"
      go test -count=1 ./... 2>&1 | sed 's/^/    /'
    } >> "$out"
    UPDATE_GOLDEN=1 go test -count=1 ./... > /dev/null
    {
      echo "-- golden after UPDATE_GOLDEN=1"
      sed 's/^/    /' testdata/deploy.mmd
      echo
      echo "-- go test -count=3"
      go test -count=3 ./... 2>&1 | sed 's/^/    /'
    } >> "$out"
    cp testdata/deploy.mmd "$render_dir/deploy-$v.mmd"
  )
  (cd "$render_dir" && node render.mjs --png "$here/output" "deploy-$v.mmd") | sed 's/^/    /' >> "$out"
done
cat "$out"
