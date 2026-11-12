"""Replay の実験。ローカルの Anvil を 2 つだけ使う（127.0.0.1 の 8548 と 8549）。

- チェーン A（8548, chain ID 31337）でコントラクトを置いた後、そのブロックから
  チェーン B（8549, chain ID 31338）を分岐させる（anvil --fork-url）。分岐の時点の残高・nonce・
  コントラクトは両方のチェーンで同じになる。
- トランザクションの署名と検証は secp256k1.py（純 Python）で手で行う。秘密鍵は説明用の無価値なもの
  （Anvil の既定のテスト用の鍵と、文字列のハッシュから作った鍵）だけを使う。
- 公開ネットワーク・実資産・本物の秘密鍵は使わない。

実行: ANVIL=... SOLC=... CAST=... python3 run.py  （PATH にあれば環境変数は不要。CAST は照合用）
"""
import json
import os
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

import secp256k1
from keccak import keccak256

LAB = Path(__file__).resolve().parent
ANVIL = os.environ.get('ANVIL', shutil.which('anvil'))
SOLC = os.environ.get('SOLC', shutil.which('solc'))
CAST = os.environ.get('CAST', shutil.which('cast'))
GWEI, ETH = 10**9, 10**18
ISSUER_KEY = 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80  # Anvil の既定の鍵 0（公開済み）
ALICE_KEY = int.from_bytes(keccak256(b'replay-protection lab alice'), 'big')    # 説明用の鍵
ALICE = secp256k1.address_from_key(ALICE_KEY)
BOB = '0x000000000000000000000000000000000000b0b0'


class Node:
    def __init__(self, port):
        self.url = f'http://127.0.0.1:{port}'

    def rpc(self, method, *params):
        body = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': list(params)}).encode()
        req = urllib.request.Request(self.url, body, {'Content-Type': 'application/json'})
        res = json.loads(urllib.request.urlopen(req).read())
        if 'error' in res:
            raise RuntimeError(res['error'].get('message'))
        return res['result']

    def wait(self):
        for _ in range(100):
            try:
                return self.rpc('eth_chainId')
            except (OSError, urllib.error.URLError):
                time.sleep(0.1)
        raise SystemExit(f'{self.url} did not start')

    def send_raw(self, raw):
        """署名済みのトランザクションのバイト列をそのまま流す。自動のマイニングなので、受け付けられればすぐブロックに入る。"""
        try:
            h = self.rpc('eth_sendRawTransaction', raw)
        except RuntimeError as e:
            return f'rejected: {e}'
        receipt = self.receipt(h)
        if receipt is None:  # ハッシュは返ったが、ブロックを作る段階で外された
            return f'hash {h[:18]}… returned, but not included (receipt null)'
        return f'included {h[:18]}… status {int(receipt["status"], 16)}'

    def receipt(self, h):
        for _ in range(50):  # 自動のマイニングでも、レシートが引けるまで少し待つことがある
            r = self.rpc('eth_getTransactionReceipt', h)
            if r is not None:
                return r
            time.sleep(0.05)
        return None

    def balance(self, addr):
        return int(self.rpc('eth_getBalance', addr, 'latest'), 16) / ETH

    def nonce(self, addr):
        return int(self.rpc('eth_getTransactionCount', addr, 'latest'), 16)

    def now(self):
        return int(self.rpc('eth_getBlockByNumber', 'latest', False)['timestamp'], 16)


# ---- RLP と ABI の最小限の道具 -------------------------------------------------

def rlp(item):
    if isinstance(item, list):
        body, prefix = b''.join(rlp(x) for x in item), 0xc0
    else:
        body, prefix = item, 0x80
        if len(body) == 1 and body[0] < 0x80:
            return body
    if len(body) < 56:
        return bytes([prefix + len(body)]) + body
    n = len(body).to_bytes((len(body).bit_length() + 7) // 8, 'big')
    return bytes([prefix + 55 + len(n)]) + n + body


def num(n):
    return n.to_bytes((n.bit_length() + 7) // 8, 'big')  # 0 は空のバイト列


def word(v):
    if isinstance(v, bytes):
        return v.rjust(32, b'\0')
    if isinstance(v, str):
        return bytes.fromhex(v[2:]).rjust(32, b'\0')
    return v.to_bytes(32, 'big')


def calldata(signature, *args):
    return '0x' + (keccak256(signature.encode())[:4] + b''.join(word(a) for a in args)).hex()


# ---- トランザクションの署名（legacy transaction） --------------------------------------------

def legacy_fields(nonce, to, value, gas_price=10 * GWEI):
    return [num(nonce), num(gas_price), num(21000), bytes.fromhex(to[2:]), num(value), b'']


def sighash(fields, chain_id=None):
    """EIP-155 より前は 6 項目、EIP-155 では chainId, 0, 0 を足した 9 項目をハッシュする。"""
    if chain_id is None:
        return keccak256(rlp(fields))
    return keccak256(rlp(fields + [num(chain_id), b'', b'']))


def sign_legacy(key, nonce, to, value, chain_id=None, gas_price=10 * GWEI):
    fields = legacy_fields(nonce, to, value, gas_price)
    parity, r, s = secp256k1.sign(key, sighash(fields, chain_id))
    v = 27 + parity if chain_id is None else chain_id * 2 + 35 + parity
    return '0x' + rlp(fields + [num(v), num(r), num(s)]).hex(), (v, r, s)


def sender_of(fields, v, r, s):
    """ノードと同じ規則で、v から chain ID を読み取り、送り主を復元する。"""
    if v in (27, 28):
        return None, secp256k1.recover(sighash(fields), v - 27, r, s)
    chain_id = (v - 35) // 2
    return chain_id, secp256k1.recover(sighash(fields, chain_id), (v - 35) % 2, r, s)


# ---- EIP-712 の引換券 -----------------------------------------------------------

def domain_separator(mode, chain_id, contract):
    if mode == 0:
        return keccak256(word(keccak256(b'EIP712Domain(string name,string version)'))
                         + word(keccak256(b'Voucher')) + word(keccak256(b'1')))
    return keccak256(word(keccak256(
        b'EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)'))
        + word(keccak256(b'Voucher')) + word(keccak256(b'1')) + word(chain_id) + word(contract))


def sign_claim(separator, to, amount, nonce, deadline):
    type_hash = keccak256(b'Claim(address to,uint256 amount,uint256 nonce,uint256 deadline)')
    struct_hash = keccak256(type_hash + word(to) + word(amount) + word(nonce) + word(deadline))
    digest = keccak256(b'\x19\x01' + separator + struct_hash)
    parity, r, s = secp256k1.sign(ISSUER_KEY, digest)
    return (to, amount, nonce, deadline, 27 + parity, r.to_bytes(32, 'big'), s.to_bytes(32, 'big'))


EIP155_EXAMPLE = ('0xf86c098504a817c800825208943535353535353535353535353535353535353535880de0b6b3a7640000'
                  '8025a028ef61340bd939bc2195fe537567866003e1a15d3c71ff63e1590620aa636276a067cbe9d8997f761aecb70330'
                  '4b3800ccf555c9f3dc64214b297fb1966a3b6d83')
CLAIM = 'claim(address,uint256,uint256,uint256,uint8,bytes32,bytes32)'


def try_claim(node, relayer, contract, args):
    data = calldata(CLAIM, *args)
    try:
        node.rpc('eth_call', {'from': relayer, 'to': contract, 'data': data}, 'latest')
    except RuntimeError as e:
        return 'revert ' + str(e).split('revert: ')[-1]
    before = node.balance(args[0])
    node.receipt(node.rpc('eth_sendTransaction', {'from': relayer, 'to': contract, 'data': data, 'gas': hex(200_000)}))
    return f'ok, paid {node.balance(args[0]) - before:g} ETH'


def deploy(node, compiled, sender, *args, value=0):
    code = compiled['bin'] + b''.join(word(a) for a in args).hex()
    h = node.rpc('eth_sendTransaction', {'from': sender, 'data': '0x' + code, 'value': hex(value),
                                         'gas': hex(2_000_000)})
    receipt = node.receipt(h)
    assert receipt['status'] == '0x1'
    return receipt['contractAddress']


def main():
    out = json.loads(subprocess.check_output(
        [SOLC, '--evm-version', 'cancun', '--combined-json', 'abi,bin', str(LAB / 'Voucher.sol')], text=True))
    compiled = next(iter(out['contracts'].values()))
    print(subprocess.check_output([ANVIL, '--version'], text=True).splitlines()[0])
    print(subprocess.check_output([SOLC, '--version'], text=True).splitlines()[-1])

    logs = open(LAB / 'output' / 'anvil.log', 'w')
    common = ['--host', '127.0.0.1', '--hardfork', 'cancun', '--accounts', '3']
    procs = [subprocess.Popen([ANVIL, *common, '--port', '8548', '--chain-id', '31337'], stdout=logs, stderr=logs)]
    try:
        a, b = Node(8548), Node(8549)
        a.wait()
        issuer, relayer = a.rpc('eth_accounts')[:2]
        assert issuer.lower() == secp256k1.address_from_key(ISSUER_KEY)

        # 照合: 手で書いた署名が cast（alloy）と同じ 65 バイトになるか
        h = keccak256(b'check')
        p, r, s = secp256k1.sign(ISSUER_KEY, h)
        ours = '0x' + r.to_bytes(32, 'big').hex() + s.to_bytes(32, 'big').hex() + f'{27 + p:02x}'
        theirs = subprocess.check_output([CAST, 'wallet', 'sign', '--no-hash', '--private-key',
                                          hex(ISSUER_KEY), '0x' + h.hex()], text=True).strip()
        print(f'secp256k1.py signature == cast wallet sign: {ours == theirs}')
        # 照合: EIP-155 の仕様にある例（nonce 9, chain ID 1）と同じトランザクションのバイト列になるか
        example, _ = sign_legacy(0x46 * sum(256**i for i in range(32)), 9, '0x' + '35' * 20, ETH,
                                 chain_id=1, gas_price=20 * GWEI)
        print(f'EIP-155 example transaction reproduced: {example == EIP155_EXAMPLE}')

        # ---- 分岐の前: Alice に資金を送り、引換券のコントラクトを 3 種類 x 2 個置く ----
        a.rpc('eth_sendTransaction', {'from': issuer, 'to': ALICE, 'value': hex(5 * ETH)})
        vouchers = {mode: [deploy(a, compiled, issuer, issuer, mode, value=10 * ETH) for _ in range(2)]
                    for mode in (0, 1, 2)}
        fork_block = int(a.rpc('eth_blockNumber'), 16)
        procs.append(subprocess.Popen([ANVIL, *common, '--port', '8549', '--chain-id', '31338',
                                       '--fork-url', a.url, '--fork-block-number', str(fork_block)],
                                      stdout=logs, stderr=logs))
        b.wait()

        print(f'\n== 0. chain B forks chain A at block {fork_block}')
        for name, node in (('A', a), ('B', b)):
            print(f'  chain {name}: eth_chainId={int(node.rpc("eth_chainId"), 16)} block={int(node.rpc("eth_blockNumber"), 16)}'
                  f' alice nonce={node.nonce(ALICE)} balance={node.balance(ALICE):g} ETH'
                  f' voucher code={keccak256(bytes.fromhex(node.rpc("eth_getCode", vouchers[0][0], "latest")[2:])).hex()[:12]}…')

        # ---- 1. EIP-155 より前の形式: chain ID を含めずに署名する ----
        print('\n== 1. pre-EIP-155 transfer (alice nonce 0, 1 ETH to bob, signed without chain ID)')
        raw, (v, r, s) = sign_legacy(ALICE_KEY, 0, BOB, ETH)
        print(f'  raw {raw[:20]}… v={v}; recovered sender {sender_of(legacy_fields(0, BOB, ETH), v, r, s)}')
        print(f'  send to A: {a.send_raw(raw)}')
        print(f'  send to B: {b.send_raw(raw)}')
        print(f'  send to A again: {a.send_raw(raw)}')
        print(f'  bob balance: A {a.balance(BOB):g} ETH, B {b.balance(BOB):g} ETH; '
              f'alice nonce: A {a.nonce(ALICE)}, B {b.nonce(ALICE)}')

        # ---- 2. EIP-155: chain ID 31337 を署名に含める ----
        print('\n== 2. EIP-155 transfer for chain 31337 (alice nonce 1)')
        raw, (v, r, s) = sign_legacy(ALICE_KEY, 1, BOB, ETH, chain_id=31337)
        fields = legacy_fields(1, BOB, ETH)
        print(f'  raw {raw[:20]}… v={v} = 31337*2+35+{v - 31337 * 2 - 35}; recovered (chain, sender) '
              f'{sender_of(fields, v, r, s)}')
        print(f'  send to A: {a.send_raw(raw)}')
        print(f'  send to B: {b.send_raw(raw)}')
        v_b = v - 31337 * 2 + 31338 * 2  # v だけを chain B 向けに書き換える
        forged = '0x' + rlp(fields + [num(v_b), num(r), num(s)]).hex()
        print(f'  v rewritten to {v_b}: recovered (chain, sender) {sender_of(fields, v_b, r, s)}')
        print(f'  send rewritten to B: {b.send_raw(forged)}')
        print(f'  bob balance: A {a.balance(BOB):g} ETH, B {b.balance(BOB):g} ETH; '
              f'alice nonce: A {a.nonce(ALICE)}, B {b.nonce(ALICE)}')

        # ---- 3. EIP-712 の引換券: domain の作り方で、同じ署名の通る範囲が変わる ----
        print('\n== 3. one EIP-712 voucher signature (signed for voucher #1 on chain 31337), sent 4 ways')
        deadline = a.now() + 3600
        labels = {0: 'mode 0 (no chainId / verifyingContract)', 1: 'mode 1 (both, fixed at deploy)',
                  2: 'mode 2 (both, computed per call)'}
        for mode, (first, second) in vouchers.items():
            sep = domain_separator(mode, 31337, first)
            on_chain = {n: n.rpc('eth_call', {'to': first, 'data': calldata('domainSeparator()')}, 'latest')
                        for n in (a, b)}
            print(f'  {labels[mode]}: separator == Python on A {on_chain[a] == "0x" + sep.hex()}, '
                  f'on B {on_chain[b] == "0x" + sep.hex()}')
            args = sign_claim(sep, BOB, ETH, 0, deadline)
            print(f'    voucher #1 on A          -> {try_claim(a, relayer, first, args)}')
            print(f'    voucher #1 on B (fork)   -> {try_claim(b, relayer, first, args)}')
            print(f'    voucher #2 on A          -> {try_claim(a, relayer, second, args)}')
            print(f'    voucher #1 on A again    -> {try_claim(a, relayer, first, args)}')

        # ---- 4. 時間: トランザクションには期限が無く、引換券には期限がある ----
        print('\n== 4. a year later on chain A')
        held, _ = sign_legacy(ALICE_KEY, 2, BOB, ETH, chain_id=31337)
        late = sign_claim(domain_separator(2, 31337, vouchers[2][0]), BOB, ETH, 1, a.now() + 3600)
        t0 = a.now()
        a.rpc('evm_increaseTime', 365 * 24 * 3600)
        a.rpc('evm_mine')
        print(f'  block time {t0} -> {a.now()} (+{(a.now() - t0) / 86400:.0f} days)')
        print(f'  transfer signed a year ago (nonce 2) -> {a.send_raw(held)}')
        print(f'  voucher signed a year ago (deadline +1 h) -> {try_claim(a, relayer, vouchers[2][0], late)}')
    finally:
        for p in procs:
            p.terminate()


if __name__ == '__main__':
    main()
