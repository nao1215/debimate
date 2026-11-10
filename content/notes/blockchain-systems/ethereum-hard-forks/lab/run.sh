#!/usr/bin/env bash
# Local-only experiment: run the same bytecode on Anvil nodes pinned to
# different hard forks. Containers join a private Docker network and publish
# no host ports. Only Anvil's default test accounts are used.
set -euo pipefail

LAB="$(cd "$(dirname "$0")" && pwd)"
OUT="$LAB/output"
FOUNDRY=ghcr.io/foundry-rs/foundry:v1.7.1
SOLC=ethereum/solc:0.8.28
PY=python:3.13-slim
NET=note-ethereum-hard-forks-net
FORKS="petersburg istanbul berlin london shanghai cancun prague osaka"

cleanup() {
  for f in $FORKS; do docker rm -f "note-ethereum-hard-forks-$f" >/dev/null 2>&1 || true; done
  docker network rm "$NET" >/dev/null 2>&1 || true
}
trap cleanup EXIT

rm -rf "$OUT"
mkdir -p "$OUT/build"

# 1. Compile the same source for several EVM versions.
solc() { docker run --rm -v "$LAB:/lab:ro" "$SOLC" "$@"; }
for v in paris shanghai cancun; do
  solc --evm-version "$v" --bin --opcodes /lab/Copy.sol > "$OUT/build/Copy.$v.txt"
done
solc --evm-version petersburg --bin --hashes /lab/Sender.sol > "$OUT/build/Sender.txt"
for v in shanghai cancun; do
  solc --evm-version "$v" --bin /lab/Guard.sol > "$OUT/build/Guard.$v.txt" 2>&1 || true
done

# 2. Start one Anvil per hard fork.
docker network create "$NET" >/dev/null
for f in $FORKS; do
  docker run -d --name "note-ethereum-hard-forks-$f" --network "$NET" "$FOUNDRY" \
    "anvil --host 0.0.0.0 --hardfork $f --chain-id 31337 --timestamp 1700000000 --accounts 2 --quiet" >/dev/null
done

# 3. Run the probes from a Python container on the same network.
docker run --rm --network "$NET" --user "$(id -u):$(id -g)" -v "$LAB:/lab" -w /lab \
  -e FORKS="$FORKS" "$PY" python -I probe.py

{
  for img in "$FOUNDRY" "$SOLC" "$PY"; do
    echo "$img $(docker image inspect --format '{{index .RepoDigests 0}}' "$img")"
  done
  docker run --rm "$FOUNDRY" "anvil --version" | head -1
  solc --version | tail -1
} > "$OUT/versions.txt"
