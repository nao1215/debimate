#!/usr/bin/env bash
# Local-only ERC-7562 experiment. See README.txt.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
AA_COMMIT=b36a1ed52ae00da6f8a4c8d50181e2877e4fa410   # eth-infinitism/account-abstraction v0.9.0
OZ_COMMIT=69c8def5f222ff96f2b5beff05dfba996368aa79   # OpenZeppelin/openzeppelin-contracts v5.1.0
SRC="${AA_SRC:-$(mktemp -d)}"

fetch() {  # fetch <dir> <repo> <tag> <commit>
  if [ ! -d "$SRC/$1" ]; then
    git clone -q --depth 1 --branch "$3" "https://github.com/$2" "$SRC/$1" 2>/dev/null
  fi
  test "$(git -C "$SRC/$1" rev-parse HEAD)" = "$4"
}
fetch aa eth-infinitism/account-abstraction v0.9.0 "$AA_COMMIT"
fetch oz OpenZeppelin/openzeppelin-contracts v5.1.0 "$OZ_COMMIT"
cp "$HERE/Lab.sol" "$SRC/Lab.sol"

SOLC="${SOLC:-solc}"
mkdir -p "$HERE/output"
# Same settings as hardhat.config.ts of account-abstraction v0.9.0 (and the erc-4337 note).
(cd "$SRC" && "$SOLC" --via-ir --optimize --optimize-runs 1000000 --evm-version cancun \
  --base-path aa --include-path . @openzeppelin/contracts/=oz/contracts/ \
  --combined-json abi,bin \
  aa/contracts/core/EntryPoint.sol \
  aa/contracts/accounts/SimpleAccountFactory.sol \
  Lab.sol) > "$SRC/build.json"
BUILD="$SRC/build.json" python3 "$HERE/run.py"
"$SOLC" --version | tail -1 >> "$HERE/output/versions.txt"
