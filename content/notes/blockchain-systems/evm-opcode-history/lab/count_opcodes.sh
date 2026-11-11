#!/usr/bin/env bash
# Count the opcodes of each go-ethereum instruction set (core/vm/jump_table.go).
# Usage: GETH_SRC=/path/to/go-ethereum bash count_opcodes.sh
# The test file is copied into core/vm, run, and removed. Needs Go and network
# access for Go modules on the first run. Output: output/geth_tables.json
set -euo pipefail
LAB="$(cd "$(dirname "$0")" && pwd)"
GETH_COMMIT=ddaa6957127ef0c4b7d41e5cbd9c19e260c0a42f
SRC="${GETH_SRC:?set GETH_SRC to a go-ethereum checkout}"
test "$(git -C "$SRC" rev-parse HEAD)" = "$GETH_COMMIT"
mkdir -p "$LAB/output"
cp "$LAB/zz_count_opcodes_test.go" "$SRC/core/vm/"
trap 'rm -f "$SRC/core/vm/zz_count_opcodes_test.go"' EXIT
(cd "$SRC" && OPCODES_OUT="$LAB/output/geth_tables.json" go test ./core/vm -run TestZZCountOpcodes -count=1)
