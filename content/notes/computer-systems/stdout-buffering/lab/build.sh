#!/usr/bin/env bash
# 実験で使うプログラムを bin/ にビルドする。
set -eu
cd "$(dirname "$0")"
mkdir -p bin output
for n in slow loop hello; do
  gcc -O2 -o "bin/${n}_c" "src/${n}.c"
  go build -o "bin/${n}_go" "src/${n}.go"
  rustc -O -o "bin/${n}_rs" "src/${n}.rs"
done
go build -o bin/hello_checked_go src/hello_checked.go
