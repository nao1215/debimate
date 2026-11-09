#!/bin/sh
# 同じ main.go を 2 つのディレクトリでビルドし、ハッシュを比べます。
set -eu
LAB=$(cd "$(dirname "$0")" && pwd)
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
export GOFLAGS=-buildvcs=false GOTOOLCHAIN=local CGO_ENABLED=0
go version

for d in alice/src bob/work/hello; do
  mkdir -p "$WORK/$d"
  cp "$LAB/main.go" "$WORK/$d/"
  (cd "$WORK/$d" && go mod init example.com/hello >/dev/null 2>&1 \
    && go build -o hello . && go build -trimpath -o hello-trim .)
done

echo "--- go build ---"
sha256sum "$WORK"/alice/src/hello "$WORK"/bob/work/hello/hello | sed "s|$WORK/||"
echo "--- 埋め込まれたパス ---"
strings "$WORK"/alice/src/hello | grep -m1 "alice/src/main.go" | sed "s|$WORK|<WORK>|"
echo "--- go build -trimpath ---"
sha256sum "$WORK"/alice/src/hello-trim "$WORK"/bob/work/hello/hello-trim | sed "s|$WORK/||"
strings "$WORK"/alice/src/hello-trim | grep -m1 "main.go"
