#!/usr/bin/env bash
# 実験の準備: ライブラリを入れ、手元だけの powers of tau（2^15 の制約まで）を作り、回路をコンパイルする。
# 手元の 1 人の参加で作った setup なので、実験以外に使わない。
set -eu
cd "$(dirname "$0")"
npm install --no-audit --no-fund
S=node_modules/.bin/snarkjs
if [ ! -f pot15.ptau ]; then
  $S powersoftau new bn128 15 pot_0.ptau
  $S powersoftau contribute pot_0.ptau pot_1.ptau --name=local -e="local test entropy"
  $S powersoftau prepare phase2 pot_1.ptau pot15.ptau
  rm -f pot_0.ptau pot_1.ptau
fi
for f in iszero_ok iszero_bug iszero_bug_cheat iszero_ok_cheat; do
  npx circom2 c/$f.circom --r1cs --wasm -o c
done
for N in 256 1024 4096 16384 32000; do
  sed "s/__N__/$N/" c/chain.circom.tpl > c/chain$N.circom
  npx circom2 c/chain$N.circom --r1cs --wasm -o c
  $S groth16 setup c/chain$N.r1cs pot15.ptau c/chain$N.zkey
  $S zkey export verificationkey c/chain$N.zkey c/chain$N.vkey.json
done
