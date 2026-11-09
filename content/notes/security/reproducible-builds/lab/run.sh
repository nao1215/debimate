#!/bin/sh
# 条件の違う 2 つのビルダーで同じ build.sh を動かしてハッシュを比べます。
set -eu
IMAGE=debian:stable-slim
LAB=$(cd "$(dirname "$0")" && pwd)
OUT=$(mktemp -d)
trap 'rm -rf "$OUT"' EXIT
export SOURCE_DATE_EPOCH=1762732800   # 2025-11-10 00:00:00 UTC

# ビルダー A: root、tmpfs 上の /build、TZ=UTC、umask 022
builder_a() {
  docker run --rm --name note-reproducible-builds-a \
    -e SOURCE_DATE_EPOCH -e TZ=UTC --tmpfs /build -w /build \
    -v "$LAB":/lab:ro "$IMAGE" sh -c "umask 022; sh /lab/build.sh $1"
}
# ビルダー B: uid 1000、/tmp/work、TZ=Asia/Tokyo、umask 002
builder_b() {
  docker run --rm --name note-reproducible-builds-b \
    -e SOURCE_DATE_EPOCH -e TZ=Asia/Tokyo --user 1000:1000 \
    -v "$LAB":/lab:ro "$IMAGE" \
    sh -c "mkdir -p /tmp/work && cd /tmp/work && umask 002; sh /lab/build.sh $1"
}

for stage in 0 1 2 3 4 5; do
  builder_a "$stage" > "$OUT/a$stage.tar.gz"
  sleep 1
  builder_b "$stage" > "$OUT/b$stage.tar.gz"
  ha=$(sha256sum "$OUT/a$stage.tar.gz" | cut -c1-16)
  hb=$(sha256sum "$OUT/b$stage.tar.gz" | cut -c1-16)
  if [ "$ha" = "$hb" ]; then r=same; else r=DIFFERENT; fi
  echo "stage $stage  A=$ha  B=$hb  $r"
done

echo
echo "--- stage 0 の中身 (A) ---"
tar --full-time -tvzf "$OUT/a0.tar.gz"
echo "--- stage 0 の中身 (B) ---"
tar --full-time -tvzf "$OUT/b0.tar.gz"
echo "--- stage 0 の gzip ヘッダー (A, 先頭 24 byte) ---"
od -A d -t x1 -N 24 "$OUT/a0.tar.gz"
