#!/usr/bin/env bash
# Local-only check: safeTransferFrom to an EOA that delegated its code (EIP-7702)
# to Counter. Uses Anvil (Prague) and its well-known default test key only.
set -euo pipefail
cd "$(dirname "$0")"
PORT=$(python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1",0)); print(s.getsockname()[1])')
RPC=http://127.0.0.1:$PORT
anvil --host 127.0.0.1 --port "$PORT" --chain-id 31337 --hardfork prague --accounts 2 --quiet >/dev/null 2>&1 &
NODE=$!
trap 'kill $NODE' EXIT
for _ in $(seq 100); do cast chain-id --rpc-url "$RPC" >/dev/null 2>&1 && break; sleep 0.05; done
ALICE=0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266
DAVE=0x70997970C51812dc3A010C7d01b50e0d17dc79C8
DAVE_KEY=0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d  # Anvil default test key #1
bin() { solc --evm-version prague --combined-json bin StudyNFT.sol Receivers.sol |
  python3 -c "import json,sys; d=json.load(sys.stdin)['contracts']; print([v['bin'] for k,v in d.items() if k.endswith(':$1')][0])"; }
deploy() { cast send --rpc-url "$RPC" --unlocked --from $ALICE --create "$1" --json |
  python3 -c 'import json,sys; print(json.load(sys.stdin)["contractAddress"])'; }
ARGS=$(cast abi-encode 'f(string)' 'http://127.0.0.1/')
NFT=$(deploy "0x$(bin StudyNFT)${ARGS:2}")
COUNTER=$(deploy "0x$(bin Counter)")
cast send --rpc-url "$RPC" --unlocked --from $ALICE $NFT 'mint(address,uint256)' $ALICE 1 >/dev/null
{
  echo "dave code before: $(cast code $DAVE --rpc-url "$RPC")"
  echo "safeTransferFrom #1 -> dave (no code): $(cast call --rpc-url "$RPC" --from $ALICE $NFT 'safeTransferFrom(address,address,uint256)' $ALICE $DAVE 1 2>&1 | tail -1)"
  cast send --rpc-url "$RPC" --private-key $DAVE_KEY --auth "$COUNTER" $ALICE >/dev/null
  echo "dave code after EIP-7702 delegation to Counter: $(cast code $DAVE --rpc-url "$RPC")"
  echo "safeTransferFrom #1 -> dave (delegated): $(cast call --rpc-url "$RPC" --from $ALICE $NFT 'safeTransferFrom(address,address,uint256)' $ALICE $DAVE 1 2>&1 | tail -1 | sed 's/, data: .*//')"
} | tee output/eip7702.txt
