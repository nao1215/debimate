#!/usr/bin/env python3
"""Local-only experiment for the ethereum-address note.

Starts throwaway Anvil nodes in Docker (no published ports, RPC via docker exec),
compares the addresses computed by address.py with what the nodes report, and
checks the metamorphic redeploy before and after Cancun (EIP-6780).
Only Anvil's well-known test key is used. No public network is contacted.
"""
import json
from pathlib import Path
import subprocess
import sys

LAB = Path(__file__).resolve().parent
sys.path.insert(0, str(LAB))
from address import checksum, create2_address, create_address, eoa_address, keccak256  # noqa: E402

FOUNDRY = 'ghcr.io/foundry-rs/foundry:v1.7.1@sha256:8347b728d5d393dac1c018691b36f506d23b9dcd78341d40ea0fcb11c3a19cdd'
SOLC = 'ethereum/solc:0.8.28@sha256:b3b83d65e1eae916b58e0c19b9051afa7ffc93e00f8210196639dee794a2a98a'
# Anvil's first default account. Public test key: never send real funds to it.
TEST_KEY = 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
OUT = LAB / 'output'
OUT.mkdir(exist_ok=True)


def sh(*args):
    return subprocess.run(args, check=True, capture_output=True, text=True).stdout.strip()


def compile_contracts():
    out = sh('docker', 'run', '--rm', '--network', 'none', '-v', f'{LAB}:/src:ro', SOLC,
             '--evm-version', 'shanghai', '--combined-json', 'bin', '/src/Address.sol')
    contracts = json.loads(out)['contracts']
    return {name.split(':')[1]: bytes.fromhex(c['bin']) for name, c in contracts.items()}


class Node:
    def __init__(self, name, chain_id, hardfork):
        self.name = f'note-ethereum-address-{name}'
        subprocess.run(['docker', 'rm', '-f', self.name], capture_output=True)
        sh('docker', 'run', '-d', '--name', self.name, '--network', 'none', FOUNDRY,
           f'anvil --host 127.0.0.1 --chain-id {chain_id} --hardfork {hardfork} '
           '--timestamp 1700000000 --accounts 2 --quiet')
        for _ in range(100):
            try:
                self.rpc('eth_chainId')
                break
            except subprocess.CalledProcessError:
                pass
        self.accounts = self.rpc('eth_accounts')

    def rpc(self, method, *params):
        out = sh('docker', 'exec', self.name, 'cast', 'rpc', '--raw', method, json.dumps(params))
        return json.loads(out)

    def send(self, to, data=b'', sender=None):
        tx = {'from': sender or self.accounts[0], 'data': '0x' + data.hex(), 'gas': hex(3_000_000)}
        if to:
            tx['to'] = '0x' + to.hex()
        receipt = self.rpc('eth_getTransactionReceipt', self.rpc('eth_sendTransaction', tx))
        return receipt

    def call(self, to, data):
        return bytes.fromhex(self.rpc('eth_call', {'to': '0x' + to.hex(), 'data': '0x' + data.hex()}, 'latest')[2:])

    def code_size(self, address):
        return (len(self.rpc('eth_getCode', '0x' + address.hex(), 'latest')) - 2) // 2

    def nonce(self, address):
        return int(self.rpc('eth_getTransactionCount', '0x' + address.hex(), 'latest'), 16)

    def close(self):
        subprocess.run(['docker', 'rm', '-f', self.name], capture_output=True)


def selector(signature):
    return keccak256(signature.encode())[:4]


def word(n):
    return n.to_bytes(32, 'big')


def abi_bytes(b):
    return word(32) + word(len(b)) + b + b'\x00' * (-len(b) % 32)


def created(receipt):
    assert int(receipt['status'], 16) == 1, receipt
    return bytes.fromhex(receipt['contractAddress'][2:])


def ok(receipt):
    return int(receipt['status'], 16)


def short(address):
    return checksum(address)[:10] + '…'


def match(actual, predicted):
    return '= python' if actual == predicted else '!= python'


def returned_address(node, to, data):
    return node.call(to, data)[12:32]


def main():
    bins = compile_contracts()
    lines = []
    me = eoa_address(TEST_KEY)
    nodes = []
    try:
        # 1. EOA: the same key gives the same address on two chains.
        a, b, c = Node('a', 31337, 'cancun'), Node('b', 31338, 'cancun'), Node('c', 31339, 'cancun')
        nodes += [a, b, c]
        lines.append('== EOA')
        lines.append(f'python      {checksum(me)}')
        for n in (a, b, c):
            assert n.accounts[0] == checksum(me).lower()
            lines.append(f'chain {int(n.rpc("eth_chainId"), 16)} {checksum(me)} (eth_accounts[0])')
        # The chain ID is in the signed data (EIP-155 / typed tx), not in the address.
        tx = {'from': a.accounts[0], 'to': a.accounts[1], 'value': '0x1', 'gas': '0x5208', 'nonce': '0x0',
              'maxFeePerGas': '0x77359400', 'maxPriorityFeePerGas': '0x1'}
        raw_a, raw_b = a.rpc('eth_signTransaction', tx), b.rpc('eth_signTransaction', tx)
        assert raw_a != raw_b
        for label, raw in (('A', raw_a), ('B', raw_b)):
            lines.append(f'signed for chain {label}: chainId=0x{raw[10:14]} tx hash={keccak256(bytes.fromhex(raw[2:])).hex()[:16]}…')
        try:
            b.rpc('eth_sendRawTransaction', raw_a)
            raise AssertionError('chain B accepted a tx signed for chain A')
        except subprocess.CalledProcessError as e:
            lines.append('chain B rejects the chain A tx: ' + e.stderr.strip().rsplit(': ', 1)[-1])

        # 2. CREATE: rlp(sender, nonce). Same nonce on A, shifted nonce on B.
        lines.append('== CREATE')
        factory_a = created(a.send(None, bins['Factory']))
        assert factory_a == create_address(me, 0)
        lines.append(f'chain A nonce 0 Factory {short(factory_a)} {match(factory_a, create_address(me, 0))}')
        lines.append(f'chain B {short(factory_a)} before: {b.code_size(factory_a)} bytes of code')
        v2_b = created(b.send(None, bins['V2']))
        assert v2_b == factory_a
        lines.append(f'chain B nonce 0 V2      {short(v2_b)} {b.code_size(v2_b)} bytes of code')
        factory_b = created(b.send(None, bins['Factory']))
        assert factory_b == create_address(me, 1)
        lines.append(f'chain B nonce 1 Factory {short(factory_b)} {match(factory_b, create_address(me, 1))}')
        factory_c = created(c.send(None, bins['Factory']))
        assert factory_c == factory_a
        lines.append(f'chain C nonce 0 Factory {short(factory_c)} {match(factory_c, create_address(me, 0))}')

        # 3. CREATE2: 0xff ++ factory ++ salt ++ keccak256(initcode).
        lines.append('== CREATE2 (Child with constructor arg v)')
        cases = [('A', a, factory_a, 0, 1), ('A', a, factory_a, 1, 1), ('A', a, factory_a, 0, 2),
                 ('B', b, factory_b, 0, 1), ('C', c, factory_c, 0, 1)]
        for label, node, factory, salt, v in cases:
            initcode = bins['Child'] + word(v)
            predicted = create2_address(factory, word(salt), initcode)
            data = selector('deploy(bytes32,uint256)') + word(salt) + word(v)
            actual = returned_address(node, factory, data)
            assert ok(node.send(factory, data)) == 1 and actual == predicted
            assert node.code_size(actual) > 0
            lines.append(f'chain {label} salt={salt} v={v} {short(actual)} {match(actual, predicted)}')
        again = a.send(factory_a, selector('deploy(bytes32,uint256)') + word(0) + word(1))
        lines.append(f'chain A salt=0 v=1 again: status={ok(again)} (address already used)')
        for n in (a, b, c):
            n.close()

        # 4. Metamorphic: CREATE2 a Deployer, CREATE V1 from it, destroy both, redeploy V2.
        lines.append('== metamorphic (each step is a separate transaction)')
        lines.append('fork     | 1st target | v | code after kill | redeploy Deployer | 2nd target | v | v at 1st')
        for fork in ('shanghai', 'cancun', 'prague'):
            n = Node(fork, 31337, fork)
            nodes.append(n)
            factory = created(n.send(None, bins['Factory']))
            dd = selector('deployDeployer(bytes32)') + word(0)
            deployer = returned_address(n, factory, dd)
            assert ok(n.send(factory, dd)) == 1
            assert deployer == create2_address(factory, word(0), bins['Deployer'])
            deploy = selector('deploy(bytes)')
            target = returned_address(n, deployer, deploy + abi_bytes(bins['V1']))
            assert ok(n.send(deployer, deploy + abi_bytes(bins['V1']))) == 1
            assert target == create_address(deployer, 1)
            v_before = int.from_bytes(n.call(target, selector('version()')), 'big')
            assert ok(n.send(target, selector('kill()'))) == 1    # V1 SELFDESTRUCT
            assert ok(n.send(deployer, selector('kill()'))) == 1  # Deployer SELFDESTRUCT
            sizes = f'{n.code_size(target)}/{n.code_size(deployer)} bytes'
            redeploy = ok(n.send(factory, dd))                     # CREATE2 the Deployer again
            if redeploy:
                assert n.nonce(deployer) == 1
            target2 = returned_address(n, deployer, deploy + abi_bytes(bins['V2']))
            assert ok(n.send(deployer, deploy + abi_bytes(bins['V2']))) == 1
            assert target2 == create_address(deployer, 1 if redeploy else 2)
            v_after = int.from_bytes(n.call(target2, selector('version()')), 'big')
            v_old = int.from_bytes(n.call(target, selector('version()')) or bytes(32), 'big')
            lines.append(f'{fork:8} | {checksum(target)[:10]} | {v_before} | {sizes:15} | '
                         f'status={redeploy:<10} | {checksum(target2)[:10]} | {v_after} | {v_old}')
            n.close()
        lines.append('Assertions: PASS')
    finally:
        for n in nodes:
            n.close()
    versions = sh('docker', 'run', '--rm', '--network', 'none', FOUNDRY, 'anvil --version | head -1') + '\n'
    versions += sh('docker', 'run', '--rm', '--network', 'none', SOLC, '--version').splitlines()[-1] + '\n'
    versions += f'{FOUNDRY}\n{SOLC}\n'
    (OUT / 'versions.txt').write_text(versions)
    summary = '\n'.join(lines) + '\n'
    (OUT / 'summary.txt').write_text(summary)
    print(summary, end='')


if __name__ == '__main__':
    main()
