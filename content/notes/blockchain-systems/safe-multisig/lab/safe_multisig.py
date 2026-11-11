#!/usr/bin/env python3
"""Local anvil only. 2-of-3 Safe (safe-smart-account v1.5.0) and execTransaction.

Run through run.sh. Keys are Anvil's public test mnemonic; never reuse them.
Owners: two EOAs and StudySigner (an ERC-1271 contract written for this lab).
"""
import json
import os
import socket
import subprocess
import time
import urllib.request

BIN = os.environ.get('ETH_BIN', '/opt/eth')
BUILD = json.load(open(os.environ['BUILD']))['contracts']
MNEMONIC = 'test test test test test test test test test test test junk'  # Anvil default, public
ZERO = '0x' + '00' * 20
SAFE_TX = ('SafeTx(address to,uint256 value,bytes data,uint8 operation,uint256 safeTxGas,'
           'uint256 baseGas,uint256 gasPrice,address gasToken,address refundReceiver,uint256 nonce)')
EXEC = 'execTransaction(address,uint256,bytes,uint8,uint256,uint256,uint256,address,address,bytes)'


def cast(*args):
    return subprocess.check_output([f'{BIN}/cast', *map(str, args)], text=True).strip()


with socket.socket() as s:
    s.bind(('127.0.0.1', 0))
    PORT = s.getsockname()[1]


def rpc(method, *params):
    body = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params}).encode()
    req = urllib.request.Request(f'http://127.0.0.1:{PORT}', body, {'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=10) as r:
        res = json.load(r)
    if 'error' in res:
        raise RuntimeError(res['error'])
    return res['result']


def send(sender, data, to=None, value=0):
    tx = {'from': sender, 'data': data, 'value': hex(value), 'gas': hex(8_000_000), 'gasPrice': hex(2 * 10**9)}
    if to:
        tx['to'] = to
    h = rpc('eth_sendTransaction', tx)
    for _ in range(200):
        receipt = rpc('eth_getTransactionReceipt', h)
        if receipt:
            return receipt
        time.sleep(0.05)
    raise TimeoutError(h)


def call(to, data, sender=None):
    """eth_call; returns (result, None) or (None, revert message)."""
    try:
        return rpc('eth_call', {'to': to, 'data': data, **({'from': sender} if sender else {})}, 'latest'), None
    except RuntimeError as e:
        return None, e.args[0]['message']


def deploy(sender, name, args=''):
    art = next(v for k, v in BUILD.items() if k.endswith(':' + name))
    receipt = send(sender, '0x' + art['bin'] + args)
    assert int(receipt['status'], 16) == 1
    return receipt['contractAddress']


def main():
    node = subprocess.Popen([f'{BIN}/anvil', '--host', '127.0.0.1', '--port', str(PORT), '--chain-id', '31337',
                             '--hardfork', 'prague', '--timestamp', '1700000000', '--accounts', '5', '--quiet'],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(200):
            try:
                accounts = rpc('eth_accounts')
                break
            except OSError:
                time.sleep(0.05)
        relayer, o1, o2, admin, receiver = accounts
        pk = {a: cast('wallet', 'private-key', '--mnemonic', MNEMONIC, '--mnemonic-index', i)
              for i, a in enumerate(accounts)}

        singleton = deploy(relayer, 'Safe')
        factory = deploy(relayer, 'SafeProxyFactory')
        signer = deploy(relayer, 'StudySigner', cast('abi-encode', 'f(address)', admin)[2:])
        owners = [o1, o2, signer]
        setup = cast('calldata', 'setup(address[],uint256,address,bytes,address,address,uint256,address)',
                     '[' + ','.join(owners) + ']', 2, ZERO, '0x', ZERO, ZERO, 0, ZERO)
        create = cast('calldata', 'createProxyWithNonce(address,bytes,uint256)', singleton, setup, 0)
        safe = '0x' + call(factory, create, relayer)[0][-40:]
        assert int(send(relayer, create, factory)['status'], 16) == 1
        send(relayer, '0x', safe, 10**18)
        threshold = int(call(safe, cast('calldata', 'getThreshold()'))[0], 16)
        print(f'Safe proxy: 3 owners (2 EOAs + 1 ERC-1271 contract), threshold = {threshold}')

        def nonce():
            return int(call(safe, cast('calldata', 'nonce()'))[0], 16)

        def safe_tx_hash(nonce_, operation=0, to=receiver, value=10**17, data='0x'):
            """EIP-712 hash computed off-chain, the same bytes each owner signs."""
            struct = cast('keccak', cast('abi-encode',
                          'f(bytes32,address,uint256,bytes32,uint8,uint256,uint256,uint256,address,address,uint256)',
                          cast('keccak', SAFE_TX), to, value, cast('keccak', data), operation, 0, 0, 0, ZERO, ZERO, nonce_))
            domain = cast('keccak', cast('abi-encode', 'f(bytes32,uint256,address)',
                          cast('keccak', 'EIP712Domain(uint256 chainId,address verifyingContract)'), 31337, safe))
            return cast('keccak', '0x1901' + domain[2:] + struct[2:])

        def sign(owner, h):  # 65 bytes r || s || v with v = 27/28
            return cast('wallet', 'sign', '--no-hash', '--private-key', pk[owner], h)[2:]

        def execute(signatures, dry=True):
            data = cast('calldata', EXEC, receiver, 10**17, '0x', 0, 0, 0, 0, ZERO, ZERO, '0x' + signatures)
            if dry:
                return call(safe, data, relayer)[1]
            return send(relayer, data, safe)

        h0 = safe_tx_hash(0)
        onchain = call(safe, cast('calldata', 'getTransactionHash(address,uint256,bytes,uint8,uint256,uint256,uint256,address,address,uint256)',
                                  receiver, 10**17, '0x', 0, 0, 0, 0, ZERO, ZERO, 0))[0]
        print('off-chain SafeTx hash == getTransactionHash:', h0 == onchain)
        print('same tx with operation=1 (delegatecall) hash:', safe_tx_hash(0, operation=1)[:18] + '..',
              'vs', h0[:18] + '..')

        lo, hi = sorted([o1, o2], key=lambda a: int(a, 16))
        ascending = sign(lo, h0) + sign(hi, h0)
        print('== nonce 0')
        for label, sigs in [('1 signature', sign(lo, h0)),
                            ('same owner twice', sign(lo, h0) * 2),
                            ('descending owners', sign(hi, h0) + sign(lo, h0))]:
            print(f'{label:24} -> {execute(sigs)}')
        before = int(rpc('eth_getBalance', receiver, 'latest'), 16)
        receipt = execute(ascending, dry=False)
        gained = int(rpc('eth_getBalance', receiver, 'latest'), 16) - before
        print(f'{"ascending owners":24} -> status {int(receipt["status"], 16)},',
              f'receiver +{gained / 1e18} ETH, nonce now {nonce()}')
        print(f'{"replay nonce-0 sigs":24} -> {execute(ascending)}')

        print('== nonce 1 (EOA + ERC-1271 owner)')
        h1 = safe_tx_hash(1)
        parts = sorted([lo, signer], key=lambda a: int(a, 16))
        # Contract signature: r = owner address, s = offset of the dynamic part, v = 0.
        contract_sig = '00' * 12 + signer[2:].lower() + format(65 * 2, '064x') + '00'
        sigs = ''.join(sign(lo, h1) if p == lo else contract_sig for p in parts) + format(0, '064x')
        print(f'{"before approve(hash)":24} -> {execute(sigs)}')
        assert int(send(admin, cast('calldata', 'approve(bytes32)', h1), signer)['status'], 16) == 1
        receipt = execute(sigs, dry=False)
        print(f'{"after approve(hash)":24} -> status {int(receipt["status"], 16)}, nonce now {nonce()}')
    finally:
        node.terminate()
        node.wait()


if __name__ == '__main__':
    main()
