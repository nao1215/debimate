#!/usr/bin/env python3
"""Run the same EVM bytecode on Anvil nodes pinned to different hard forks.

Local-only. Called by run.sh inside a container on a private Docker network.
The bytecode below is hand-assembled for this experiment and is not audited.
"""
import json
import os
from pathlib import Path
import time
import urllib.request

FORKS = os.environ['FORKS'].split()
OUT = Path('output')
BUILD = OUT / 'build'
lines = []


class RpcError(Exception):
    pass


def rpc(fork, method, *params):
    url = f'http://note-ethereum-hard-forks-{fork}:8545'
    body = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params}).encode()
    request = urllib.request.Request(url, body, {'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=10) as response:
        result = json.load(response)
    if 'error' in result:
        raise RpcError(result['error']['message'])
    return result['result']


def wait_ready(fork):
    for _ in range(200):
        try:
            return rpc(fork, 'eth_accounts')
        except OSError:
            time.sleep(0.1)
    raise TimeoutError(fork)


def status(receipt):
    return int(receipt['status'], 16)


def send(fork, tx):
    tx = {'gas': hex(1_000_000), 'gasPrice': hex(2_000_000_000), **tx}
    txhash = rpc(fork, 'eth_sendTransaction', tx)
    for _ in range(100):
        receipt = rpc(fork, 'eth_getTransactionReceipt', txhash)
        if receipt:
            return receipt
        time.sleep(0.05)
    raise TimeoutError(txhash)


def initcode(runtime):
    """Init code that copies `runtime` (hex) into memory and returns it as the deployed code."""
    n = len(runtime) // 2
    assert n < 256
    return f'60{n:02x}600c600039{"60%02x" % n}6000f3' + runtime


def solc_output(name):
    text = (BUILD / name).read_text()
    sections = {}
    key = None
    for line in text.splitlines():
        if line.endswith(':') and not line.startswith(' '):
            key = line[:-1]
        elif key and line.strip():
            sections.setdefault(key, []).append(line.strip())
    return sections


accounts = {f: wait_ready(f) for f in FORKS}

# 1. New opcodes: run init code with eth_call (no `to` = simulated contract creation).
#    Each snippet leaves one 32-byte word in memory[0:32] and returns it.
RETURN_WORD = '60005260206000f3'  # PUSH1 0 MSTORE PUSH1 32 PUSH1 0 RETURN
PROBES = [
    ('BASEFEE', 'London', '48' + RETURN_WORD),
    ('PUSH0', 'Shanghai', '5f' + RETURN_WORD),
    ('TSTORE', 'Cancun', '6007' '6000' '5d' '6000' '5c' + RETURN_WORD),  # TSTORE(0, 7); TLOAD(0)
    ('MCOPY', 'Cancun', '602a600052' '6020' '6000' '6020' '5e' '60206020f3'),  # copy mem[0:32] to mem[32:64]
    ('CLZ', 'Osaka', '6001' '1e' + RETURN_WORD),  # count leading zeros of 1
]
lines.append('== opcode probes (eth_call of init code) ==')
lines.append('fork       | ' + ' | '.join(name for name, _, _ in PROBES))
errors = set()
for fork in FORKS:
    cells = []
    for name, _, code in PROBES:
        try:
            value = int(rpc(fork, 'eth_call', {'data': '0x' + code}, 'latest'), 16)
            cells.append(f'ok={value}')
        except RpcError as e:
            errors.add(str(e))
            cells.append('error')
    lines.append(f'{fork:<10} | ' + ' | '.join(cells))
lines.append('error messages: ' + '; '.join(sorted(errors)))

# 2. SLOAD gas: GAS, SLOAD(0), GAS, SLOAD(0), GAS. Each gap = PUSH1(3) + SLOAD + POP(2) + GAS(2).
SLOAD_TWICE = '5a' '600054' '50' '5a' '600054' '50' '5a' '604052' '602052' '600052' '60606000f3'
lines.append('')
lines.append('== SLOAD of the same slot twice in one call ==')
lines.append('fork       | 1st SLOAD | 2nd SLOAD')
for fork in FORKS:
    raw = rpc(fork, 'eth_call', {'data': '0x' + SLOAD_TWICE}, 'latest')[2:]
    g0, g1, g2 = (int(raw[i:i + 64], 16) for i in range(0, 192, 64))
    lines.append(f'{fork:<10} | {g0 - g1 - 7:>9} | {g1 - g2 - 7:>9}')

# 3. Solidity transfer() forwards 2300 gas. The receiver reads 3 storage slots on receipt.
RECEIVER = '600054' '50' '600154' '50' '600254' '50' '00'  # SLOAD(0), SLOAD(1), SLOAD(2), STOP
sender = solc_output('Sender.txt')
sender_bin = sender['Binary'][0]
pay = next(h.split(':')[0] for h in sender['Function signatures'] if h.endswith('pay(address)'))
lines.append('')
lines.append('== transfer(1 wei) to a receiver that reads 3 slots ==')
lines.append('fork       | plain tx | with access list')
for fork in FORKS:
    me = accounts[fork][0]
    receiver = send(fork, {'from': me, 'data': '0x' + initcode(RECEIVER)})['contractAddress']
    contract = send(fork, {'from': me, 'data': '0x' + sender_bin})['contractAddress']
    call = {'from': me, 'to': contract, 'value': '0x1', 'data': '0x' + pay + receiver[2:].lower().rjust(64, '0')}
    plain = status(send(fork, call))
    if fork in ('petersburg', 'istanbul'):
        listed = '-'  # access lists (EIP-2930) start at Berlin
    else:
        slots = ['0x' + f'{i:064x}' for i in range(3)]
        listed = status(send(fork, {**call, 'accessList': [{'address': receiver, 'storageKeys': slots}]}))
    lines.append(f'{fork:<10} | {plain:<8} | {listed}')

# 4. SELFDESTRUCT in a later transaction than the one that created the contract.
SELF_DESTRUCT = '33ff'  # CALLER SELFDESTRUCT
lines.append('')
lines.append('== SELFDESTRUCT called in a later transaction ==')
lines.append('fork       | code before | code after | balance after')
for fork in FORKS:
    me = accounts[fork][0]
    target = send(fork, {'from': me, 'value': hex(1000), 'data': '0x' + initcode(SELF_DESTRUCT)})['contractAddress']
    before = rpc(fork, 'eth_getCode', target, 'latest')
    assert status(send(fork, {'from': me, 'to': target})) == 1
    after = rpc(fork, 'eth_getCode', target, 'latest')
    balance = int(rpc(fork, 'eth_getBalance', target, 'latest'), 16)
    lines.append(f'{fork:<10} | {before:<11} | {after:<10} | {balance}')

# 5. The same Solidity source compiled for different evmVersion values.
lines.append('')
lines.append('== Copy.sol compiled with solc --evm-version ==')
lines.append('evmVersion | bytes | PUSH0 | MCOPY | deploy: london | shanghai | cancun')
for version in ('paris', 'shanghai', 'cancun'):
    out = solc_output(f'Copy.{version}.txt')
    code = out['Binary'][0]
    ops = out['Opcodes'][0].split()
    statuses = []
    for fork in ('london', 'shanghai', 'cancun'):
        statuses.append(str(status(send(fork, {'from': accounts[fork][0], 'data': '0x' + code}))))
    lines.append(f'{version:<10} | {len(code) // 2:>5} | {ops.count("PUSH0"):>5} | {ops.count("MCOPY"):>5} | '
                 + ' | '.join(statuses))
for version in ('shanghai', 'cancun'):
    text = (BUILD / f'Guard.{version}.txt').read_text()
    result = 'compiled' if 'Binary:' in text else next(l for l in text.splitlines() if l.strip())
    lines.append(f'Guard.sol (transient) with {version}: {result}')

summary = '\n'.join(lines) + '\n'
(OUT / 'summary.txt').write_text(summary)
print(summary, end='')
