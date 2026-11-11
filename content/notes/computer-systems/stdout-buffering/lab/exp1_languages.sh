#!/usr/bin/env bash
# 実験 1: 0.5 秒ごとに 1 行ずつ出すプログラムを、端末・パイプ・stdbuf -oL 付きのパイプで動かし、
# 読む側に各行が届いた時刻（起動からの秒）を記録する。
set -u
cd "$(dirname "$0")"
declare -A CMD=(
  [C]="bin/slow_c"
  [Python]="python3 src/slow.py"
  [Go]="bin/slow_go"
  [Rust]="bin/slow_rs"
)
run() { # $1=言語 $2=出力先 $3=コマンド
  export T0
  T0=$(date +%s.%N)
  bash -c "$3" | python3 stamp.py | sed "s/^/$1\t$2\t/"
}
for lang in C Python Go Rust; do
  c=${CMD[$lang]}
  # script はコマンドに疑似端末（pty）を渡すので、プログラムからは端末に見える
  run "$lang" "端末" "script -qfec '$c' /dev/null"
  run "$lang" "パイプ" "$c"
  run "$lang" "パイプ+stdbuf -oL" "stdbuf -oL $c"
done | tr -d '\r'
