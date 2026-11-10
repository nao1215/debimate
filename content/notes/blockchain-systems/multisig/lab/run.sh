#!/usr/bin/env bash
# Local-only multisig experiments. See README.txt.
# Downloads happen on the host; the experiments run in containers with --network none.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
WORK="${MULTISIG_WORK:-${TMPDIR:-/tmp}/note-multisig-lab}"
PY=python:3.13-slim@sha256:e48f59cdba69a3cbd9ed2cf0f348d90d45a8d350d98134cf1070bc106ee9ed90
FOUNDRY=ghcr.io/foundry-rs/foundry:v1.7.1@sha256:8347b728d5d393dac1c018691b36f506d23b9dcd78341d40ea0fcb11c3a19cdd
SOLC=ethereum/solc:0.7.6@sha256:0a0ce55949d098cc432bb4f71c504e9a247cab2a6ead1cba0a5dbe0cb20c5d76
CORE=bitcoin-32.1
CORE_SHA256=61545c17c3120fb7412f896d248b11993af04ec8817aad3649c55b2afb044963
SAFE_COMMIT=dc437e8fba8b4805d76bcbd1c668c9fd3d1e83be   # safe-smart-account v1.5.0
mkdir -p "$WORK/bin" "$HERE/output"

# 1. Bitcoin Core release binary from bitcoincore.org, checked against the published SHA256.
if [ ! -x "$WORK/$CORE/bin/bitcoind" ]; then
  curl -sSfL -o "$WORK/core.tar.gz" "https://bitcoincore.org/bin/bitcoin-core-32.1/$CORE-x86_64-linux-gnu.tar.gz"
  echo "$CORE_SHA256  $WORK/core.tar.gz" | sha256sum -c -
  tar xzf "$WORK/core.tar.gz" -C "$WORK"
fi
# 2. Safe contracts at a fixed commit (LGPL-3.0-only).
if [ ! -d "$WORK/safe" ]; then
  git clone -q --depth 1 --branch v1.5.0 https://github.com/safe-global/safe-smart-account "$WORK/safe" 2>/dev/null
fi
test "$(git -C "$WORK/safe" rev-parse HEAD)" = "$SAFE_COMMIT"
# 3. anvil/cast and solc copied out of their official images.
for spec in "$FOUNDRY:/usr/local/bin/anvil" "$FOUNDRY:/usr/local/bin/cast" "$SOLC:/usr/bin/solc"; do
  image="${spec%:*}"; path="${spec##*:}"
  if [ ! -x "$WORK/bin/$(basename "$path")" ]; then
    c=$(docker create "$image"); docker cp "$c:$path" "$WORK/bin/" >/dev/null; docker rm "$c" >/dev/null
  fi
done

docker run --rm --name note-multisig-btc --network none \
  -v "$WORK/$CORE:/opt/bitcoin:ro" -v "$HERE:/lab:ro" "$PY" \
  python3 -I /lab/bitcoin_multisig.py | tee "$HERE/output/bitcoin.txt"

docker run --rm --name note-multisig-eth --network none \
  -v "$WORK/bin:/opt/eth:ro" -v "$WORK/safe:/safe:ro" -v "$HERE:/lab:ro" "$PY" sh -c '
    cd /safe && /opt/eth/solc --optimize --optimize-runs 200 --combined-json abi,bin \
      contracts/Safe.sol contracts/proxies/SafeProxyFactory.sol /lab/StudySigner.sol \
      --allow-paths /lab > /tmp/build.json 2>/dev/null
    BUILD=/tmp/build.json python3 -I /lab/safe_multisig.py' | tee "$HERE/output/safe.txt"

{
  echo "bitcoind: $("$WORK/$CORE/bin/bitcoind" -version | head -1)"
  echo "safe-smart-account: v1.5.0 ($SAFE_COMMIT)"
  docker run --rm --network none -v "$WORK/bin:/opt/eth:ro" "$PY" sh -c \
    '/opt/eth/anvil --version | head -1; /opt/eth/cast --version | head -1; /opt/eth/solc --version | tail -1'
  echo "container: $PY"
} > "$HERE/output/versions.txt"
