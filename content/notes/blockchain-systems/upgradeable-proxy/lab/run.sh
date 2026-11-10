#!/usr/bin/env bash
# Local-only upgradeable proxy experiment. See README.txt.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
OZ_COMMIT=cab19933c33c2ad1d4c7a84864a3601dddfd16f3    # OpenZeppelin/openzeppelin-contracts v5.7.0
OZU_COMMIT=14f52c54d3a1eefbda3d4071efba24d3c1e07e8a   # OpenZeppelin/openzeppelin-contracts-upgradeable v5.7.0
SRC="${OZ_SRC:-$(mktemp -d)}"

fetch() {  # fetch <dir> <repo> <tag> <commit>
  if [ ! -d "$SRC/$1" ]; then
    git clone -q --depth 1 --branch "$3" "https://github.com/$2" "$SRC/$1" 2>/dev/null
  fi
  test "$(git -C "$SRC/$1" rev-parse HEAD)" = "$4"
}
fetch oz OpenZeppelin/openzeppelin-contracts v5.7.0 "$OZ_COMMIT"
fetch ozu OpenZeppelin/openzeppelin-contracts-upgradeable v5.7.0 "$OZU_COMMIT"

SOLC="${SOLC:-solc}"
mkdir -p "$HERE/output"
cp "$HERE/Study.sol" "$HERE/Box.sol" "$SRC/"
(cd "$SRC" && "$SOLC" --optimize --evm-version prague --base-path . \
  @openzeppelin/contracts/=oz/contracts/ @openzeppelin/contracts-upgradeable/=ozu/contracts/ \
  --combined-json abi,bin,storage-layout Study.sol Box.sol) > "$SRC/build.json"
BUILD="$SRC/build.json" PYTHONDONTWRITEBYTECODE=1 python3 "$HERE/run.py"
"$SOLC" --version | tail -1 >> "$HERE/output/versions.txt"
