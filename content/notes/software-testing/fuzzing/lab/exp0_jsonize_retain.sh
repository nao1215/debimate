#!/usr/bin/env bash
# 冒頭の図: jsonize の表の読み取りが、入力の大きさに比べて何倍のメモリを保持するか。
#
# 修正前は 0e6b5cd の 1 つ前、修正後は 0e6b5cd。
# 機械を守るため、systemd-run でメモリを 8 GB に制限して走らせる。
set -eu
here=$(cd "$(dirname "$0")" && pwd)
work=$(mktemp -d "${TMPDIR:-$HOME/.cache}/fuzzlab.XXXXXX")
trap 'rm -rf "$work"' EXIT

git clone -q https://github.com/nao1215/jsonize "$work/jsonize"
for rev in 0e6b5cd^ 0e6b5cd; do
  git -C "$work/jsonize" checkout -q "$rev"
  mkdir -p "$work/jsonize/cmd/zzretain"
  cp "$here/jsonize/retain.go.txt" "$work/jsonize/cmd/zzretain/main.go"
  (cd "$work/jsonize" && go build -o "$work/retain" ./cmd/zzretain)
  rm -r "$work/jsonize/cmd/zzretain"
  echo "== jsonize $(git -C "$work/jsonize" rev-parse --short "$rev") ($rev)"
  for rows in 20000 40000 80000 160000; do
    systemd-run --user --scope -q -p MemoryMax=8G -p MemorySwapMax=0 "$work/retain" "$rows"
  done
done
