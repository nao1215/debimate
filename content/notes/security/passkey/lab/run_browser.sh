#!/bin/sh
# browser.mjs を走らせる。Chrome のプロファイルは使い捨ての一時ディレクトリに作る。
set -eu
cd "$(dirname "$0")"
work=${WORK:-$(mktemp -d)}
# Hugo の content に .html を置けないので、ページは .txt で持ち、配信の時に index.html として写す
mkdir -p "$work/page"
cp webauthn_page.html.txt "$work/page/index.html"
python3 -m http.server 18080 --bind 127.0.0.1 --directory "$work/page" >/dev/null 2>&1 &
srv=$!
google-chrome --headless=new --remote-debugging-port=9334 --user-data-dir="$work/chrome" about:blank >/dev/null 2>&1 &
chr=$!
trap 'kill $srv 2>/dev/null; kill $chr 2>/dev/null; pkill -f "remote-debugging-port=9334" 2>/dev/null || true' EXIT
sleep 2
node browser.mjs
