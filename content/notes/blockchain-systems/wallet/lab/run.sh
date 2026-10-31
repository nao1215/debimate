#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
export BLOCK_HOME="$PWD/block-home"
mkdir -p output
rpc_a=http://127.0.0.1:18545
rpc_b=http://127.0.0.1:18546
# Refuse occupied ports; never stop someone else's node.
python3 - <<'PY'
import socket
for port in (18545,18546):
    with socket.socket() as s:
        s.bind(('127.0.0.1',port))
PY
pids=()
cleanup() {
  for pid in "${pids[@]}"; do kill -TERM "$pid" 2>/dev/null || true; done
  for pid in "${pids[@]}"; do wait "$pid" 2>/dev/null || true; done
}
trap cleanup EXIT
# Quiet mode avoids printing Anvil's development keys and mnemonic.
block exec anvil --host 127.0.0.1 --port 18545 --chain-id 31337 --accounts 2 --balance 10000 --timestamp 1700000000 --hardfork cancun --quiet >output/node-a.log 2>&1 &
pids+=("$!")
block exec anvil --host 127.0.0.1 --port 18546 --chain-id 31338 --accounts 2 --balance 10000 --timestamp 1700000000 --hardfork cancun --quiet >output/node-b.log 2>&1 &
pids+=("$!")
for rpc in "$rpc_a" "$rpc_b"; do
  ready=0
  for _ in {1..50}; do
    if block exec cast chain-id --rpc-url "$rpc" >/dev/null 2>&1; then ready=1; break; fi
    sleep 0.1
  done
  if [[ "$ready" != 1 ]]; then echo 'local node did not start' >&2; exit 1; fi
done
block --version >output/versions.txt
block exec anvil --version >>output/versions.txt
block exec cast --version >>output/versions.txt
block exec cast rpc eth_accounts --rpc-url "$rpc_a" >output/accounts.json
sender=$(jq -r '.[0]' output/accounts.json)
receiver=$(jq -r '.[1]' output/accounts.json)
# Anvil's built-in accounts are unlocked test accounts. No key is passed to cast.
capture() {
  local stage="$1"
  for chain in a b; do
    local rpc="$rpc_a"
    if [[ "$chain" == b ]]; then rpc="$rpc_b"; fi
    block exec cast balance "$sender" --rpc-url "$rpc" >"output/$stage-$chain-sender.wei"
    block exec cast balance "$receiver" --rpc-url "$rpc" >"output/$stage-$chain-receiver.wei"
    block exec cast chain-id --rpc-url "$rpc" >"output/chain-$chain.id"
  done
}
capture before
# Fixed legacy gas price makes the 21,000-gas fee easy to reproduce.
block exec cast send "$receiver" --value 1ether --from "$sender" --unlocked --legacy --gas-price 1gwei --gas-limit 21000 --rpc-url "$rpc_a" --json >output/receipt.json
transaction_hash=$(jq -r '.transactionHash' output/receipt.json)
block exec cast tx "$transaction_hash" --rpc-url "$rpc_a" --json >output/transaction.json
capture after
python3 - <<'PY'
from pathlib import Path
from decimal import Decimal
import json
p=Path('output');r=json.loads((p/'receipt.json').read_text())
accounts=json.loads((p/'accounts.json').read_text())
read=lambda stage,chain,role:int((p/f'{stage}-{chain}-{role}.wei').read_text())
parse=lambda n:int(n,16) if isinstance(n,str) and n.startswith('0x') else int(n)
fee=parse(r['gasUsed'])*parse(r['effectiveGasPrice'])
assert parse(r['status']) == 1
assert read('after','a','receiver')-read('before','a','receiver') == 10**18
assert read('before','a','sender')-read('after','a','sender') == 10**18+fee
for role in ('sender','receiver'):
    assert read('before','b',role)==read('after','b',role)
eth=lambda n:format(Decimal(n)/Decimal(10**18),'f')
lines=[f'Sender: {accounts[0]}',f'Receiver: {accounts[1]}','',
       'Chain | Role | Before (ETH) | After (ETH)']
for chain in ('a','b'):
    cid=(p/f'chain-{chain}.id').read_text().strip()
    for role in ('sender','receiver'):
        lines.append(f'{chain.upper()} ({cid}) | {role} | {eth(read("before",chain,role))} | {eth(read("after",chain,role))}')
lines += ['',f'Transaction hash: {r["transactionHash"]}',f'Status: {parse(r["status"])} (success)',
          f'Block: {parse(r["blockNumber"])}',f'Gas used: {parse(r["gasUsed"])}',
          f'Effective gas price: {parse(r["effectiveGasPrice"])} wei',f'Fee: {eth(fee)} ETH',
          'Assertions: receiver +1 ETH; sender -(1 ETH + fee); both B balances unchanged: PASS']
report='\n'.join(lines)+'\n';(p/'summary.txt').write_text(report);print(report,end='')
PY
