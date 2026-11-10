#!/usr/bin/env bash
# Local-only EVM experiment. One Anvil node pinned to Osaka runs on a private
# Docker network and publishes no host port. Only Anvil's default test
# accounts and key are used. No public network is contacted.
set -euo pipefail

LAB="$(cd "$(dirname "$0")" && pwd)"
OUT="$LAB/output"
FOUNDRY=ghcr.io/foundry-rs/foundry:v1.7.1
SOLC=ethereum/solc:0.8.28
PY=python:3.13-slim
NET=note-evm-net
NODE=note-evm-anvil
# Anvil's well-known default test key for account 0 (public, never use with real funds).
TEST_KEY=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80

cleanup() {
  docker rm -f "$NODE" >/dev/null 2>&1 || true
  docker network rm "$NET" >/dev/null 2>&1 || true
}
trap cleanup EXIT

rm -rf "$OUT/build" "$OUT/summary.txt" "$OUT/probe.json" "$OUT/versions.txt"
mkdir -p "$OUT/build"

# 1. Compile. Optimizer off, metadata hash off, evmVersion cancun.
docker run --rm -v "$LAB:/lab:ro" "$SOLC" --evm-version cancun --metadata-hash none \
  --combined-json abi,bin,bin-runtime,hashes /lab/Dispatcher.sol /lab/Context.sol /lab/Deep.sol \
  > "$OUT/build/combined.json"

# 2. Start Anvil (Osaka rules, fixed timestamp so gas and addresses repeat).
docker network create "$NET" >/dev/null
docker run -d --name "$NODE" --network "$NET" "$FOUNDRY" \
  "anvil --host 0.0.0.0 --hardfork osaka --chain-id 31337 --timestamp 1700000000 --accounts 2 --steps-tracing --quiet" >/dev/null

# 3. Values that need Keccak-256 or secp256k1: computed with cast in the node container.
runtime=$(python3 -c "import json,sys;c=json.load(open(sys.argv[1]))['contracts'];print([v for k,v in c.items() if k.endswith(':Dispatcher')][0]['bin-runtime'])" "$OUT/build/combined.json")
docker exec "$NODE" cast disassemble "0x$runtime" > "$OUT/build/dispatcher.disasm.txt"
MSG_HASH=$(docker exec "$NODE" cast keccak "evm note")
SIG=$(docker exec "$NODE" cast wallet sign --no-hash --private-key "$TEST_KEY" "$MSG_HASH")
TOPIC0=$(docker exec "$NODE" cast keccak "Changed(address,uint256)")

# 4. Probes from a Python container on the same network.
docker run --rm --network "$NET" --user "$(id -u):$(id -g)" -v "$LAB:/lab" -w /lab \
  -e NODE="$NODE" -e MSG_HASH="$MSG_HASH" -e SIG="$SIG" -e TOPIC0="$TOPIC0" \
  "$PY" python -I probe.py

{
  for img in "$FOUNDRY" "$SOLC" "$PY"; do
    echo "$img $(docker image inspect --format '{{index .RepoDigests 0}}' "$img")"
  done
  docker exec "$NODE" anvil --version | head -1
  docker run --rm "$SOLC" --version | tail -1
} > "$OUT/versions.txt"
