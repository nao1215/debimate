#!/usr/bin/env bash
# copy_post_images.sh
# Hugoのcontent/post以下の画像をstatic/imagesへコピーする

set -euo pipefail

CONTENT_DIR="content/post"
DEST_DIR="static/images"

mkdir -p "$DEST_DIR"

# 拡張子を指定して探索
find "$CONTENT_DIR" -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.webp" \) | while read -r img; do
    filename=$(basename "$img")
    echo "Copying: $img -> $DEST_DIR/$filename"
    cp -f "$img" "$DEST_DIR/$filename"
done

echo "✅ すべての画像を ${DEST_DIR}/ にコピーしました。"