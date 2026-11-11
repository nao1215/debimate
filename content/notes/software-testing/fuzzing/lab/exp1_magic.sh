#!/usr/bin/env bash
# 実験 1: 同じ条件を 1 バイトずつ比べる関数と、4 バイトまとめて比べる関数に go test -fuzz を掛ける。
#
# 毎回 go clean -fuzzcache で前回の corpus を消してから走らせる。
set -u
cd "$(dirname "$0")/magic"
for i in 1 2 3 4 5; do
  go clean -fuzzcache; rm -rf testdata
  go test -run '^$' -fuzz '^FuzzCount$' -parallel 1 -fuzztime 60s . 2>&1 | grep -m1 -o 'found at call [0-9]*' | sed "s/^/FuzzByteByByte run$i: /"
done
for i in 1 2 3; do
  go clean -fuzzcache; rm -rf testdata
  go test -run '^$' -fuzz '^FuzzAtOnce$' -fuzztime 120s . 2>&1 | grep -E '^fuzz: elapsed' | tail -1 | sed "s/^/FuzzAtOnce run$i: /"
done
rm -rf testdata
go test -run '^TestRandom$' -v . | grep -E 'not found|found after|^ok'
