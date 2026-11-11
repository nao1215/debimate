#!/usr/bin/env bash
# 実験 2: 0.5 秒ごとに 1 行を流す上流の後ろに coreutils のフィルタを 1 つ挟み、
# GNU 版（gnu 接頭辞）と uutils 版（Ubuntu 26.04 の既定）で、各行が下流に届いた時刻を比べる。
set -u
cd "$(dirname "$0")"
FILTERS=(
  "cat"
  "tee /dev/null"
  "head -n 10"
  "tr a-z A-Z"
  "cut -c1-"
  "fold -w 80"
  "uniq"
  "nl"
)
run() { # $1=実装 $2=条件 $3=フィルタ $4=コマンド
  export T0
  T0=$(date +%s.%N)
  python3 -u src/slow.py | bash -c "$4" | python3 stamp.py | sed "s|^|$1\t$2\t$3\t|"
}
for f in "${FILTERS[@]}"; do
  run GNU    "そのまま"     "${f%% *}" "gnu$f"
  run GNU    "stdbuf -oL"   "${f%% *}" "gnustdbuf -oL gnu$f"
  run uutils "そのまま"     "${f%% *}" "/usr/lib/cargo/bin/coreutils/$f"
  run uutils "stdbuf -oL"   "${f%% *}" "/usr/lib/cargo/bin/coreutils/stdbuf -oL /usr/lib/cargo/bin/coreutils/$f"
done
