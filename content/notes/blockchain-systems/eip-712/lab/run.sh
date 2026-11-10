#!/usr/bin/env bash
# Local-only EIP-712 / ERC-2612 / ERC-1271 experiment. See README.txt.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
OZ_TAG=v5.1.0
OZ_COMMIT=69c8def5f222ff96f2b5beff05dfba996368aa79   # OpenZeppelin/openzeppelin-contracts v5.1.0 (MIT)
OZ_SRC="${OZ_SRC:-$(mktemp -d)}"
if [ ! -d "$OZ_SRC/oz" ]; then
  git clone -q --depth 1 --branch "$OZ_TAG" https://github.com/OpenZeppelin/openzeppelin-contracts "$OZ_SRC/oz" 2>/dev/null
fi
test "$(git -C "$OZ_SRC/oz" rev-parse HEAD)" = "$OZ_COMMIT"
OZ_SRC="$OZ_SRC" OZ_COMMIT="$OZ_TAG $OZ_COMMIT" python3 "$HERE/run.py"
