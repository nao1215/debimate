#!/bin/sh
# 段階 3 の成果物を 2 つのビルダーで作り、diffoscope で差分を読みます。
set -eu
IMAGE=debian:stable-slim
LAB=$(cd "$(dirname "$0")" && pwd)
OUT=$(mktemp -d)
trap 'rm -rf "$OUT"' EXIT
export SOURCE_DATE_EPOCH=1762732800

docker run --rm --name note-reproducible-builds-a \
  -e SOURCE_DATE_EPOCH -e TZ=UTC --tmpfs /build -w /build \
  -v "$LAB":/lab:ro "$IMAGE" sh -c "umask 022; sh /lab/build.sh 3" > "$OUT/a3.tar.gz"
docker run --rm --name note-reproducible-builds-b \
  -e SOURCE_DATE_EPOCH -e TZ=Asia/Tokyo --user 1000:1000 \
  -v "$LAB":/lab:ro "$IMAGE" \
  sh -c "mkdir -p /tmp/work && cd /tmp/work && umask 002; sh /lab/build.sh 3" > "$OUT/b3.tar.gz"

# diffoscope は Debian のパッケージから入れます（ネットワークに接続します）。
docker run --rm --name note-reproducible-builds-diff -v "$OUT":/w:ro "$IMAGE" sh -c '
  apt-get update -qq >/dev/null
  DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends \
    diffoscope-minimal >/dev/null 2>&1
  diffoscope --version
  diffoscope /w/a3.tar.gz /w/b3.tar.gz' || true
