"""コミット・リビールの実験。ローカルの Anvil だけを使う。

- 公開ネットワーク・実資産・本物の秘密鍵は使わない。
- アカウントは Anvil が既定で作るテスト用のもの（鍵が広く公開されており、説明用で無価値）。
- 自動のマイニングを止め（--no-mining）、トランザクションをメモリプールに溜めてから evm_mine でブロックを作る。

実行: ANVIL=... SOLC=... python3 run.py  （PATH にあれば環境変数は不要）
"""
import json
import os
import secrets
import shutil
import subprocess
import time
import urllib.request
from pathlib import Path

from keccak import keccak256

LAB = Path(__file__).resolve().parent
ANVIL = os.environ.get('ANVIL', shutil.which('anvil'))
SOLC = os.environ.get('SOLC', shutil.which('solc'))
PORT = 8561
GWEI = 10**9
ETH = 10**18


# ---- JSON-RPC と ABI の最小限の道具 -------------------------------------------

def rpc(method, *params):
    body = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': list(params)}).encode()
    req = urllib.request.Request(f'http://127.0.0.1:{PORT}', body, {'Content-Type': 'application/json'})
    res = json.loads(urllib.request.urlopen(req).read())
    if 'error' in res:
        raise RuntimeError(res['error'])
    return res['result']


def word(v):
    """uint256 / address / bytes32 を 32 バイトの語にする（abi.encode と同じ）。"""
    if isinstance(v, bytes):
        return v.rjust(32, b'\0')
    if isinstance(v, str):  # 0x 付きのアドレス
        return bytes.fromhex(v[2:]).rjust(32, b'\0')
    return v.to_bytes(32, 'big')


def calldata(signature, *args):
    return '0x' + (keccak256(signature.encode())[:4] + b''.join(word(a) for a in args)).hex()


def send(sender, to, data, tip_gwei=1, value=0, gas=300_000):
    # 上限の単価は base fee（この実験では 1 gwei 前後）に tip を足した程度にする
    tx = {'from': sender, 'data': data, 'gas': hex(gas), 'value': hex(value),
          'maxFeePerGas': hex((10 + tip_gwei) * GWEI), 'maxPriorityFeePerGas': hex(tip_gwei * GWEI)}
    if to:
        tx['to'] = to
    return rpc('eth_sendTransaction', tx)


def mine(n=1):
    for _ in range(n):
        rpc('evm_mine')


def call(to, signature, *args):
    return rpc('eth_call', {'to': to, 'data': calldata(signature, *args)}, 'latest')


def pending_from(sender):
    """メモリプールにある、sender の未処理のトランザクションを返す（後続の人が見る情報）。"""
    pool = rpc('txpool_content')['pending']
    for addr, txs in pool.items():
        if addr.lower() == sender.lower():
            return list(txs.values())
    return []


def revert_reason(tx_hash):
    trace = rpc('debug_traceTransaction', tx_hash, {'tracer': 'callTracer'})
    return trace.get('revertReason') or trace.get('error') or ''


def show_block(names):
    block = rpc('eth_getBlockByNumber', 'latest', True)
    print(f'  block {int(block["number"], 16)}:')
    for i, tx in enumerate(block['transactions']):
        r = rpc('eth_getTransactionReceipt', tx['hash'])
        ok = r['status'] == '0x1'
        tip = int(tx['maxPriorityFeePerGas'], 16) // GWEI
        sel = tx['input'][2:10]
        args = [tx['input'][10 + 64 * k: 74 + 64 * k] for k in range((len(tx['input']) - 10) // 64)]
        shown = ', '.join(str(int(a, 16)) if int(a, 16) < 10**12 else '0x' + a[:8] + '..' for a in args)
        status = 'ok' if ok else f'reverted ({revert_reason(tx["hash"])})'
        print(f'    #{i} {names[tx["from"].lower()]:<5} tip {tip} gwei  {FUNCS.get(sel, sel)}({shown})  -> {status}')


def deploy(compiled, name, *args, sender):
    code = compiled[name]['bin'] + b''.join(word(a) for a in args).hex()
    h = send(sender, None, '0x' + code, gas=2_000_000)
    mine()
    receipt = rpc('eth_getTransactionReceipt', h)
    assert receipt['status'] == '0x1', f'deploy of {name} failed'
    return receipt['contractAddress']


def commitment(addr, amount, salt):
    return keccak256(word(addr) + word(amount) + word(salt))


def brute_force(addr, target, candidates, salt=b'\0' * 32):
    """候補の入札額を全部ハッシュして、メモリプールで見たコミットと比べる。"""
    start = time.perf_counter()
    for n, amount in enumerate(candidates, 1):
        if commitment(addr, amount, salt) == target:
            return amount, n, time.perf_counter() - start
    return None, len(candidates), time.perf_counter() - start


FUNCS = {}


def main():
    src = LAB / 'Auction.sol'
    out = json.loads(subprocess.check_output(
        [SOLC, '--evm-version', 'cancun', '--combined-json', 'abi,bin', str(src)], text=True))
    compiled = {k.split(':')[1]: v for k, v in out['contracts'].items()}
    for sig in ('bid(uint256)', 'commit(bytes32)', 'reveal(uint256,bytes32)'):
        FUNCS[keccak256(sig.encode())[:4].hex()] = sig.split('(')[0]

    print(subprocess.check_output([ANVIL, '--version'], text=True).splitlines()[0])
    print(subprocess.check_output([SOLC, '--version'], text=True).splitlines()[-1])
    log = open(LAB / 'output' / 'anvil.log', 'w')
    node = subprocess.Popen([ANVIL, '--host', '127.0.0.1', '--port', str(PORT), '--chain-id', '31337',
                             '--hardfork', 'cancun', '--timestamp', '1700000000', '--accounts', '4',
                             '--no-mining', '--order', 'fees'], stdout=log, stderr=log)
    try:
        for _ in range(100):
            try:
                accounts = rpc('eth_accounts')
                break
            except OSError:
                time.sleep(0.1)
        deployer, alice, bob, carol = accounts
        names = {deployer.lower(): 'owner', alice.lower(): 'alice', bob.lower(): 'bob', carol.lower(): 'carol'}

        # ---- (1) 入札額をそのまま送る: 後から送った bob が先に処理される ----
        print('\n== (1) open bid: bob reads alice\'s pending bid and outbids with a higher tip')
        auction = deploy(compiled, 'OpenAuction', sender=deployer)
        send(alice, auction, calldata('bid(uint256)', 50), tip_gwei=1)
        seen = pending_from(alice)[0]['input']
        alice_bid = int(seen[10:], 16)
        print(f'  bob sees in txpool: bid({alice_bid}) from alice')
        send(bob, auction, calldata('bid(uint256)', alice_bid + 1), tip_gwei=3)
        mine()
        show_block(names)
        winner = '0x' + call(auction, 'highestBidder()')[-40:]
        print(f'  winner {names[winner]}, highest {int(call(auction, "highestBid()"), 16)}')

        # ---- (2) salt 無しのコミット: 候補の総当たりで中身が分かる ----
        print('\n== (2) commit without salt (salt = 0): bob brute-forces 1..10000')
        auction = deploy(compiled, 'CommitRevealAuction', 3, 3, sender=deployer)
        zero = b'\0' * 32
        send(alice, auction, calldata('commit(bytes32)', commitment(alice, 50, zero)), value=ETH)
        seen = bytes.fromhex(pending_from(alice)[0]['input'][10:])
        found, tries, sec = brute_force(alice, seen, range(1, 10_001))
        print(f'  bob sees commitment 0x{seen.hex()[:16]}.. ; found amount={found} after {tries} hashes, {sec:.3f} s')
        bob_salt = secrets.token_bytes(32)
        send(bob, auction, calldata('commit(bytes32)', commitment(bob, found + 1, bob_salt)), value=ETH)
        mine()
        mine(3)  # コミットの締め切りを過ぎるまでブロックを進める
        send(alice, auction, calldata('reveal(uint256,bytes32)', 50, zero))
        send(bob, auction, calldata('reveal(uint256,bytes32)', found + 1, bob_salt))
        mine()
        show_block(names)
        winner = '0x' + call(auction, 'highestBidder()')[-40:]
        print(f'  winner {names[winner]}, highest {int(call(auction, "highestBid()"), 16)}')

        # 2 択の投票なら、候補は 2 つしかない
        vote = commitment(alice, 1, zero)  # 1 = 賛成
        print(f'  vote yes/no without salt: found choice={brute_force(alice, vote, [0, 1])[0]} after '
              f'{brute_force(alice, vote, [0, 1])[1]} hashes')

        # ---- (3) salt ありのコミット: 見破れない。写したコミットも使えない。リビールしない人の預け金は残る ----
        print('\n== (3) commit with a 32-byte random salt')
        auction = deploy(compiled, 'CommitRevealAuction', 3, 3, sender=deployer)
        alice_salt = secrets.token_bytes(32)
        carol_salt = secrets.token_bytes(32)
        send(alice, auction, calldata('commit(bytes32)', commitment(alice, 50, alice_salt)), value=ETH)
        seen = bytes.fromhex(pending_from(alice)[0]['input'][10:])
        found, tries, sec = brute_force(alice, seen, range(1, 10_001))
        print(f'  bob brute-forces 1..10000 with salt=0: found={found} after {tries} hashes, {sec:.3f} s')
        send(bob, auction, calldata('commit(bytes32)', seen), value=ETH)  # alice のコミットをそのまま写す
        send(carol, auction, calldata('commit(bytes32)', commitment(carol, 70, carol_salt)), value=ETH)
        mine()
        show_block(names)
        mine(3)
        send(alice, auction, calldata('reveal(uint256,bytes32)', 50, alice_salt), tip_gwei=1)
        seen = pending_from(alice)[0]['input']
        print('  bob copies alice\'s pending reveal (amount and salt) with a higher tip')
        send(bob, auction, '0x' + seen[2:], tip_gwei=3)
        mine()
        show_block(names)
        mine(4)  # carol はリビールせずに締め切りが過ぎる
        winner = '0x' + call(auction, 'highestBidder()')[-40:]
        balance = int(rpc('eth_getBalance', auction, 'latest'), 16)
        print(f'  winner {names[winner]}, highest {int(call(auction, "highestBid()"), 16)}; '
              f'deposits left in contract {balance / ETH:g} ETH (bob and carol did not reveal)')

        # ---- ハッシュの速さ（この Python 実装での目安） ----
        n = 20_000
        start = time.perf_counter()
        for i in range(n):
            commitment(alice, i, zero)
        rate = n / (time.perf_counter() - start)
        print(f'\n== hash rate of this pure-Python keccak: {rate:,.0f} hashes/s')
    finally:
        node.terminate()
        node.wait()


if __name__ == '__main__':
    (LAB / 'output').mkdir(exist_ok=True)
    main()
