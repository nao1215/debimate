#!/usr/bin/env python3
"""Local-only experiment for the mainnet-and-testnet note (Ethereum part).

Starts two throwaway Anvil nodes in Docker with --network none: one with
chain ID 1 (the same number as Ethereum mainnet) and one with chain ID
11155111 (the same number as Sepolia). Neither is connected to anything.
RPC goes through `docker exec ... cast`, so no port is published.

1. Read the labels each node reports (eth_chainId, net_version) and the state
   at a well-known mainnet contract address.
2. Sign an EIP-1559 transfer for chain 1 and send the same bytes to both nodes.
3. Sign a pre-EIP-155 legacy transfer (no chain ID, v = 27/28) and send the
   same bytes to both nodes.

Only Anvil's public test key is used. Never send real funds to it.
"""
import json
from pathlib import Path
import subprocess

FOUNDRY = 'ghcr.io/foundry-rs/foundry:v1.7.1@sha256:8347b728d5d393dac1c018691b36f506d23b9dcd78341d40ea0fcb11c3a19cdd'
# Anvil's first default account (public test key, published by Foundry).
KEY = '0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80'
BOB = '0x70997970C51812dc3A010C7d01b50e0d17dc79C8'  # Anvil's second account
USDC_ON_MAINNET = '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'
OUT = Path(__file__).resolve().parent / 'output'


def sh(*args, check=True):
    p = subprocess.run(args, capture_output=True, text=True)
    if check and p.returncode != 0:
        raise RuntimeError(p.stderr.strip())
    return p


class Node:
    def __init__(self, chain_id):
        self.chain_id = chain_id
        self.name = f'note-mainnet-and-testnet-eth-{chain_id}'
        sh('docker', 'rm', '-f', self.name, check=False)
        sh('docker', 'run', '-d', '--name', self.name, '--network', 'none', FOUNDRY,
           f'anvil --host 127.0.0.1 --chain-id {chain_id} --accounts 2 '
           '--timestamp 1700000000 --quiet')
        for _ in range(100):
            if sh('docker', 'exec', self.name, 'cast', 'chain-id', check=False).returncode == 0:
                break

    def cast(self, *args, check=True):
        p = sh('docker', 'exec', self.name, 'cast', *args, check=check)
        return p.stdout.strip() if p.returncode == 0 else 'error: ' + p.stderr.strip().splitlines()[-1]

    def rpc(self, method, *params):
        return json.loads(self.cast('rpc', '--raw', method, json.dumps(params)))

    def publish(self, raw):
        out = self.cast('publish', raw, check=False)
        return out if out.startswith('error') else 'accepted ' + json.loads(out)['transactionHash'][:18] + '…'

    def balance(self, who):
        return self.cast('balance', who, '--ether')

    def close(self):
        sh('docker', 'rm', '-f', self.name, check=False)


def rlp(item):
    """Minimal RLP: item is bytes or a list of items."""
    if isinstance(item, list):
        body = b''.join(rlp(x) for x in item)
        prefix = 0xc0
    else:
        body = item
        if len(body) == 1 and body[0] < 0x80:
            return body
        prefix = 0x80
    if len(body) < 56:
        return bytes([prefix + len(body)]) + body
    n = len(body).to_bytes((len(body).bit_length() + 7) // 8, 'big')
    return bytes([prefix + 55 + len(n)]) + n + body


def num(n):
    return n.to_bytes((n.bit_length() + 7) // 8, 'big')  # 0 -> b''


def pre_eip155_transfer(node, nonce, value_wei):
    """Legacy transaction signed over 6 fields only: no chain ID anywhere."""
    fields = [num(nonce), num(10**9 * 2), num(21000), bytes.fromhex(BOB[2:]), num(value_wei), b'']
    sighash = node.cast('keccak', '0x' + rlp(fields).hex())
    sig = bytes.fromhex(node.cast('wallet', 'sign', '--no-hash', '--private-key', KEY, sighash)[2:])
    r, s, v = sig[:32], sig[32:64], sig[64]  # v is 27 or 28
    return '0x' + rlp(fields + [num(v), r.lstrip(b'\0'), s.lstrip(b'\0')]).hex(), v


def main():
    OUT.mkdir(exist_ok=True)
    lines = []

    def log(s=''):
        print(s)
        lines.append(s)

    a, b = Node(1), Node(11155111)
    try:
        log('== 1. labels and state')
        for n in (a, b):
            log(f'chain {n.chain_id:>8}: eth_chainId={n.rpc("eth_chainId")} net_version={n.rpc("net_version")} '
                f'code at USDC mainnet address={n.rpc("eth_getCode", USDC_ON_MAINNET, "latest")}')

        log('== 2. EIP-1559 transfer signed for chain 1')
        raw = a.cast('mktx', '--private-key', KEY, '--chain', '1', '--nonce', '0',
                     '--gas-limit', '21000', '--gas-price', '2gwei', '--priority-gas-price', '1gwei',
                     '--value', '1ether', BOB)
        log(f'raw tx: {raw[:12]}… ({(len(raw) - 2) // 2} bytes, type 0x{raw[2:4]})')
        decoded = json.loads(a.cast('decode-tx', raw))
        decoded = json.loads(decoded) if isinstance(decoded, str) else decoded
        log(f'decoded: chainId={decoded["chainId"]} signer={decoded["signer"]}')
        for n in (a, b):
            log(f'send to chain {n.chain_id:>8}: {n.publish(raw)}')

        log('== 3. pre-EIP-155 legacy transfer (signed without chain ID)')
        # Chain 1 already used nonce 0 in step 2; chain 11155111 has not.
        # nonce 0: accepted only where nonce 0 is unused. nonce 1: the same bytes run on both.
        raw0, v = pre_eip155_transfer(a, 0, 10**18)
        log(f'raw tx: {raw0[:12]}… ({(len(raw0) - 2) // 2} bytes, v={v})')
        log(f'send to chain {b.chain_id:>8}: {b.publish(raw0)}')
        log(f'send to chain {a.chain_id:>8}: {a.publish(raw0)}')
        raw1, v = pre_eip155_transfer(b, 1, 10**18)
        log(f'second raw tx (nonce 1): {raw1[:12]}…, v={v}')
        for n in (b, a):
            log(f'send to chain {n.chain_id:>8}: {n.publish(raw1)}')
        for n in (a, b):
            log(f'chain {n.chain_id:>8}: Bob balance {n.balance(BOB)} ETH')
    finally:
        a.close()
        b.close()
    (OUT / 'eth_replay.txt').write_text('\n'.join(lines) + '\n')


if __name__ == '__main__':
    main()
