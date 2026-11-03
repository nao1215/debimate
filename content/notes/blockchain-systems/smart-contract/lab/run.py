#!/usr/bin/env python3
"""Local-only experiment. Requires Python 3, Anvil, cast and solc 0.8.28."""
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import time
import urllib.request

ROOT = Path(__file__).resolve().parent
MODE = os.environ.get('LAB_MODE', 'counter')
if MODE not in ('counter', 'token'):
    raise ValueError('LAB_MODE must be counter or token')
LAB = ROOT if MODE == 'counter' else ROOT.parent.parent / 'erc-20' / 'lab'
OUT = LAB / 'output'
OUT.mkdir(exist_ok=True)
TOOLS = {name: os.environ.get(name.upper(), shutil.which(name)) for name in ('anvil', 'cast', 'solc')}
if not all(TOOLS.values()):
    raise SystemExit('Put anvil, cast and solc on PATH (or set ANVIL, CAST, SOLC).')

def cli(name, *args):
    return subprocess.check_output([TOOLS[name], *args], text=True).strip()

versions = '\n'.join(cli(name, '--version') for name in TOOLS) + '\n'
(OUT / 'versions.txt').write_text(versions)
source = 'Counter.sol' if MODE == 'counter' else 'StudyToken.sol'
compiled = json.loads(cli('solc', '--evm-version', 'cancun', '--combined-json', 'abi,bin', str(LAB / source)))
contract = next(iter(compiled['contracts'].values()))
# Select a free loopback port; fail if another process acquires it before Anvil.
with socket.socket() as sock:
    sock.bind(('127.0.0.1', 0))
    port = sock.getsockname()[1]
url = f'http://127.0.0.1:{port}'

def rpc(method, *params):
    request = urllib.request.Request(url, json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params}).encode(), {'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=5) as response:
        result = json.load(response)
    if 'error' in result:
        raise RuntimeError(result['error'])
    return result['result']

def data(signature, *args):
    return cli('cast', 'calldata', signature, *map(str, args))

def send(label, sender, payload, to=None):
    tx = {'from': sender, 'data': payload, 'gas': hex(2000000), 'gasPrice': hex(2000000000)}
    if to:
        tx['to'] = to
    txhash = rpc('eth_sendTransaction', tx)
    for _ in range(100):
        receipt = rpc('eth_getTransactionReceipt', txhash)
        if receipt:
            (OUT / f'{label}.json').write_text(json.dumps(receipt, indent=2) + '\n')
            return receipt
        time.sleep(0.05)
    raise TimeoutError(txhash)

def read(signature, *args):
    return int(rpc('eth_call', {'to': address, 'data': data(signature, *args)}, 'latest'), 16)

def status(receipt):
    return int(receipt['status'], 16)

with (OUT / 'node.log').open('w') as log:
    node = subprocess.Popen([TOOLS['anvil'], '--host', '127.0.0.1', '--port', str(port), '--chain-id', '31337', '--hardfork', 'cancun', '--timestamp', '1700000000', '--accounts', '3', '--quiet'], stdout=log, stderr=log)
    try:
        for _ in range(100):
            if node.poll() is not None:
                raise RuntimeError('Anvil exited; inspect output/node.log')
            try:
                accounts = rpc('eth_accounts')
                break
            except (OSError, RuntimeError):
                time.sleep(0.05)
        else:
            raise TimeoutError('Anvil startup')
        owner, spender, receiver = accounts[:3]
        receipt = send('deploy', owner, '0x' + contract['bin'])
        assert status(receipt) == 1
        address = receipt['contractAddress']
        lines = []
        if MODE == 'counter':
            assert read('count()') == 0
            before_block = rpc('eth_blockNumber')
            rpc('eth_call', {'from': owner, 'to': address, 'data': data('increment()')}, 'latest')
            assert read('count()') == 0 and rpc('eth_blockNumber') == before_block
            lines.append('eth_call increment: count=0; block unchanged')
            for label, signature, expected in [('increment', 'increment()', 1), ('revert', 'incrementAndFail()', 0)]:
                nonce = int(rpc('eth_getTransactionCount', owner, 'latest'), 16)
                balance = int(rpc('eth_getBalance', owner, 'latest'), 16)
                receipt = send(label, owner, data(signature), address)
                fee = int(receipt['gasUsed'], 16) * int(receipt['effectiveGasPrice'], 16)
                assert status(receipt) == expected and read('count()') == 1
                assert int(rpc('eth_getTransactionCount', owner, 'latest'), 16) == nonce + 1
                assert balance - int(rpc('eth_getBalance', owner, 'latest'), 16) == fee
                assert len(receipt['logs']) == expected
                lines.append(f'{label}: status={status(receipt)}; count=1; logs={len(receipt["logs"])}; nonce_delta=1; fee_wei={fee}')
        else:
            lines.append('stage | owner | receiver | allowance | status')
            def snapshot(label, expected, receipt=None):
                values = (read('balanceOf(address)', owner), read('balanceOf(address)', receiver), read('allowance(address,address)', owner, spender))
                assert values == expected and read('totalSupply()') == 100
                lines.append(f'{label} | {values[0]} | {values[1]} | {values[2]} | {status(receipt) if receipt else "-"}')
            snapshot('initial', (100, 0, 0))
            cases = [('transfer 5', owner, 'transfer(address,uint256)', (receiver, 5), (95, 5, 0), 1), ('approve 30', owner, 'approve(address,uint256)', (spender, 30), (95, 5, 30), 1), ('spend 10', spender, 'transferFrom(address,address,uint256)', (owner, receiver, 10), (85, 15, 20), 1), ('overspend 21', spender, 'transferFrom(address,address,uint256)', (owner, receiver, 21), (85, 15, 20), 0), ('revoke', owner, 'approve(address,uint256)', (spender, 0), (85, 15, 0), 1), ('spend after revoke', spender, 'transferFrom(address,address,uint256)', (owner, receiver, 1), (85, 15, 0), 0)]
            for i, (label, sender, signature, args, expected, ok) in enumerate(cases):
                receipt = send(f'step-{i}', sender, data(signature, *args), address)
                assert status(receipt) == ok
                assert len(receipt['logs']) == ok
                snapshot(label, expected, receipt)
        lines.append('Assertions: PASS')
        summary = '\n'.join(lines) + '\n'
        (OUT / 'summary.txt').write_text(summary)
        print(summary, end='')
    finally:
        node.terminate()
        try:
            node.wait(timeout=5)
        except subprocess.TimeoutExpired:
            node.kill()
            node.wait()
