#!/usr/bin/env bash
# blob の基本: 5 バイトの blob を送り、コントラクトから見えるものと gas を記録する。
# Foundry (anvil/cast) 1.7.1、ループバックだけで動く。公開ネットワーク・実資産は使わない。
set -euo pipefail
cd "$(dirname "$0")"
port=18611
rpc=http://127.0.0.1:$port
out=output
mkdir -p "$out"

anvil --port "$port" --hardfork osaka --silent &
anvil_pid=$!
trap 'kill "$anvil_pid" 2>/dev/null || true' EXIT
until cast chain-id --rpc-url "$rpc" >/dev/null 2>&1; do sleep 0.2; done

from=$(cast rpc eth_accounts --rpc-url "$rpc" | jq -r '.[0]')

# BLOBHASH(0)・BLOBHASH(1)・CALLDATASIZE をスロット 0・1・2 に書くだけのコントラクト
#   runtime: PUSH1 0 BLOBHASH PUSH1 0 SSTORE  PUSH1 1 BLOBHASH PUSH1 1 SSTORE
#            CALLDATASIZE PUSH1 2 SSTORE  STOP
runtime=6000496000556001496001553660025500
initcode=0x6011600c60003960116000f3$runtime
probe=$(cast send --from "$from" --unlocked --rpc-url "$rpc" --json --create "$initcode" | jq -r .contractAddress)

# 5 バイトの "hello" を blob に入れて、コントラクトへ送る（calldata は空）
printf 'hello' > "$out/hello.bin"
cast send "$probe" --blob --path "$out/hello.bin" \
  --from "$from" --unlocked --rpc-url "$rpc" --json > "$out/blob_receipt.json"
tx=$(jq -r .transactionHash "$out/blob_receipt.json")
cast tx "$tx" --rpc-url "$rpc" --json > "$out/blob_tx.json"   # 保存後に blobs と cellProofs を省略した

{
  echo "receipt.type        $(jq -r .type "$out/blob_receipt.json")"
  echo "receipt.gasUsed     $(cast to-dec "$(jq -r .gasUsed "$out/blob_receipt.json")")"
  echo "receipt.blobGasUsed $(cast to-dec "$(jq -r .blobGasUsed "$out/blob_receipt.json")")"
  echo "tx.input            $(jq -r .input "$out/blob_tx.json")"
  echo "tx.blobVersionedHashes[0] $(jq -r '.blobVersionedHashes[0]' "$out/blob_tx.json")"
  echo "slot0 BLOBHASH(0)   $(cast storage "$probe" 0 --rpc-url "$rpc")"
  echo "slot1 BLOBHASH(1)   $(cast storage "$probe" 1 --rpc-url "$rpc")"
  echo "slot2 CALLDATASIZE  $(cast to-dec "$(cast storage "$probe" 2 --rpc-url "$rpc")")"
  # versioned hash は、KZG commitment の SHA-256 の先頭 1 バイトを 0x01 に替えた値
  echo "0x01 + sha256(commitment)[1:] $(jq -r '.commitments[0]' "$out/blob_tx.json" |
    python3 -c 'import hashlib,sys; c=bytes.fromhex(sys.stdin.read().strip()[2:]); print("0x01" + hashlib.sha256(c).hexdigest()[2:])')"
} | tee "$out/basics.txt"

# 同じ大きさのデータを calldata で送った時の gasUsed（中身は 0 でない 'a' の並び）
echo "bytes gasUsed" > "$out/calldata_gas.txt"
for n in 5 100 1000 10000 100000; do
  # 長いデータはコマンドの引数に収まらないので、JSON-RPC の本文をファイルにして送る
  printf '{"jsonrpc":"2.0","id":1,"method":"eth_sendTransaction","params":[{"from":"%s","to":"0x000000000000000000000000000000000000dEaD","data":"0x%s"}]}' \
    "$from" "$(head -c "$n" /dev/zero | tr '\0' 'a' | xxd -p | tr -d '\n')" > "$out/req.json"
  tx=$(curl -s -H 'content-type: application/json' --data @"$out/req.json" "$rpc" | jq -r .result)
  echo "$n $(cast receipt "$tx" gasUsed --rpc-url "$rpc")" >> "$out/calldata_gas.txt"
done
rm -f "$out/req.json"

# 上限（9 個）の blob を 3 ブロック続けて入れ、anvil が excessBlobGas を進めるかを見る
head -c $((126945 * 6)) /dev/zero | tr '\0' 'a' > "$out/six.bin"
head -c $((126945 * 3)) /dev/zero | tr '\0' 'a' > "$out/three.bin"
cast rpc evm_setAutomine false --rpc-url "$rpc" >/dev/null
echo "block blobs excessBlobGas" > "$out/anvil_excess.txt"
nonce=$(cast nonce "$from" --rpc-url "$rpc")
for i in 1 2 3 4; do
  if [ "$i" -le 3 ]; then
    for f in six three; do
      cast send "$probe" --blob --path "$out/$f.bin" --async --nonce "$nonce" \
        --from "$from" --unlocked --rpc-url "$rpc" >/dev/null
      nonce=$((nonce + 1))
    done
  fi
  cast rpc evm_mine --rpc-url "$rpc" >/dev/null
  cast block latest --json --rpc-url "$rpc" | python3 -c 'import json,sys
b = json.load(sys.stdin)
print(int(b["number"], 16), int(b["blobGasUsed"], 16) // 131072, int(b["excessBlobGas"], 16))' \
    >> "$out/anvil_excess.txt"
done
rm -f "$out/six.bin" "$out/three.bin"
cat "$out/anvil_excess.txt"
cat "$out/calldata_gas.txt"
