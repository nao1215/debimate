#!/usr/bin/env bash
# Local-only Bitcoin multisig experiments. See README.txt.
# The download happens on the host; the experiment runs in a container with --network none.
# The Safe (Ethereum) experiment lives in ../../safe-multisig/lab/.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
WORK="${MULTISIG_WORK:-${TMPDIR:-/tmp}/note-multisig-lab}"
PY=python:3.13-slim@sha256:e48f59cdba69a3cbd9ed2cf0f348d90d45a8d350d98134cf1070bc106ee9ed90
CORE=bitcoin-32.1
CORE_SHA256=61545c17c3120fb7412f896d248b11993af04ec8817aad3649c55b2afb044963
mkdir -p "$WORK" "$HERE/output"

# Bitcoin Core release binary from bitcoincore.org, checked against the published SHA256.
if [ ! -x "$WORK/$CORE/bin/bitcoind" ]; then
  curl -sSfL -o "$WORK/core.tar.gz" "https://bitcoincore.org/bin/bitcoin-core-32.1/$CORE-x86_64-linux-gnu.tar.gz"
  echo "$CORE_SHA256  $WORK/core.tar.gz" | sha256sum -c -
  tar xzf "$WORK/core.tar.gz" -C "$WORK"
fi

docker run --rm --name note-multisig-btc --network none \
  -v "$WORK/$CORE:/opt/bitcoin:ro" -v "$HERE:/lab:ro" "$PY" \
  python3 -I /lab/bitcoin_multisig.py | tee "$HERE/output/bitcoin.txt"

{
  echo "bitcoind: $("$WORK/$CORE/bin/bitcoind" -version | head -1)"
  echo "container: $PY"
} > "$HERE/output/versions.txt"
