"""EIP-1559 の base fee をローカルの Anvil で実測し、仕様の式で計算した値と並べる。

- 公開ネットワーク・実資産・本物の秘密鍵は使わない。Anvil は 127.0.0.1 だけで待ち受ける。
- アカウントは Anvil が既定で作るテスト用のもの（鍵が広く公開されており、説明用で無価値）。
- 自動のマイニングを止め（--no-mining）、トランザクションを mempool に溜めてから evm_mine でブロックを作る。
- ブロックの gas 上限を 1,050,000（21,000 gas の送金 50 件分）に下げ、送金の件数で使用率を決める。

実行: ANVIL=... python3 run.py > output/output.txt  （anvil が PATH にあれば環境変数は不要）
"""
import json
import os
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

LAB = Path(__file__).resolve().parent
ANVIL = os.environ.get('ANVIL', shutil.which('anvil'))
PORT = 8547
GWEI = 10**9
TRANSFER_GAS = 21_000
GAS_LIMIT = 50 * TRANSFER_GAS  # 1,050,000。target はその半分の 525,000（送金 25 件）

# EIP-1559 の定数（https://eips.ethereum.org/EIPS/eip-1559）
BASE_FEE_MAX_CHANGE_DENOMINATOR = 8
ELASTICITY_MULTIPLIER = 2


def expected_base_fee(parent_base_fee, parent_gas_used, parent_gas_limit):
    """EIP-1559 の式で、親ブロックから次のブロックの base fee を計算する。"""
    target = parent_gas_limit // ELASTICITY_MULTIPLIER
    if parent_gas_used == target:
        return parent_base_fee
    if parent_gas_used > target:
        delta = parent_base_fee * (parent_gas_used - target) // target // BASE_FEE_MAX_CHANGE_DENOMINATOR
        return parent_base_fee + max(delta, 1)
    delta = parent_base_fee * (target - parent_gas_used) // target // BASE_FEE_MAX_CHANGE_DENOMINATOR
    return parent_base_fee - delta


# ---- JSON-RPC の最小限の道具 ---------------------------------------------------

def rpc(method, *params):
    body = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': list(params)}).encode()
    req = urllib.request.Request(f'http://127.0.0.1:{PORT}', body, {'Content-Type': 'application/json'})
    res = json.loads(urllib.request.urlopen(req).read())
    if 'error' in res:
        raise RuntimeError(res['error']['message'])
    return res['result']


def transfer(sender, to, max_fee, tip):
    """21,000 gas の単純な送金を 1 件送り、トランザクションのハッシュを返す。"""
    return rpc('eth_sendTransaction', {
        'from': sender, 'to': to, 'value': '0x1', 'gas': hex(TRANSFER_GAS),
        'maxFeePerGas': hex(max_fee), 'maxPriorityFeePerGas': hex(tip)})


def block(tag='latest'):
    b = rpc('eth_getBlockByNumber', tag, False)
    return {'number': int(b['number'], 16), 'gas_used': int(b['gasUsed'], 16),
            'gas_limit': int(b['gasLimit'], 16), 'base_fee': int(b['baseFeePerGas'], 16),
            'txs': b['transactions']}


def start_anvil(base_fee_wei, log_name):
    log = open(LAB / 'output' / log_name, 'w')
    node = subprocess.Popen(
        [ANVIL, '--host', '127.0.0.1', '--port', str(PORT), '--chain-id', '31337',
         '--hardfork', 'osaka', '--timestamp', '1700000000', '--accounts', '4',
         '--no-mining', '--order', 'fees',
         '--gas-limit', str(GAS_LIMIT), '--block-base-fee-per-gas', str(base_fee_wei)],
        stdout=log, stderr=log)
    for _ in range(100):
        try:
            return node, rpc('eth_accounts')
        except (OSError, urllib.error.URLError):
            time.sleep(0.1)
    raise RuntimeError('anvil did not start')


def mine_with(filler, to, n_transfers, tip=2 * GWEI, max_fee=1000 * GWEI):
    """filler から n 件の送金を mempool に入れてから、ブロックを 1 つ作る。"""
    for _ in range(n_transfers):
        transfer(filler, to, max_fee, tip)
    rpc('evm_mine')
    return block()


def row(phase, b, parent, note=''):
    exp = expected_base_fee(parent['base_fee'], parent['gas_used'], parent['gas_limit'])
    used = b['gas_used'] / b['gas_limit'] * 100
    mark = 'ok' if exp == b['base_fee'] else 'DIFF'
    print(f"{phase:<7} {b['number']:>5} {len(b['txs']):>4} {used:>6.1f}% "
          f"{b['base_fee']:>14} {exp:>14} {mark:>4}  {note}")


HEADER = f"{'phase':<7} {'block':>5} {'txs':>4} {'used':>7} {'base fee(wei)':>14} {'EIP-1559':>14} {'cmp':>4}"


# ---- 実験 1: 満杯のブロック・target のブロック・空のブロック ------------------------

def run_main():
    node, (filler, alice, bob, carol) = start_anvil(GWEI, 'anvil.log')
    to = '0x000000000000000000000000000000000000dEaD'
    alice_max_fee = 2 * GWEI
    try:
        print('== (1) base fee per block: gas limit 1,050,000, target 525,000, start 1 gwei')
        print(HEADER)
        parent = block()
        print(f"genesis {parent['number']:>5} {0:>4} {0:>6.1f}% {parent['base_fee']:>14}")

        # target ちょうど（25 件）を 3 ブロック
        for _ in range(3):
            b = mine_with(filler, to, 25)
            row('target', b, parent)
            parent = b

        # Alice は単価の上限 2 gwei、Carol は 5 gwei で、どちらも上乗せ 1 gwei の送金を 1 件ずつ送る
        alice_tx = transfer(alice, to, alice_max_fee, 1 * GWEI)
        carol_tx = transfer(carol, to, 5 * GWEI, 1 * GWEI)
        print(f'  alice sends: maxFeePerGas 2 gwei, maxPriorityFeePerGas 1 gwei (base fee {parent["base_fee"] / GWEI:.3f} gwei)')
        print('  carol sends: maxFeePerGas 5 gwei, maxPriorityFeePerGas 1 gwei')

        def status(b):
            pool = rpc('txpool_content')['pending']
            in_pool = {a.lower() for a in pool}
            out = []
            for name, addr, h in (('alice', alice, alice_tx), ('carol', carol, carol_tx)):
                if h in b['txs']:
                    r = rpc('eth_getTransactionReceipt', h)
                    paid = int(r['effectiveGasPrice'], 16)
                    out.append(f'{name} included (price {paid / GWEI:.3f} = base fee + tip {(paid - b["base_fee"]) / GWEI:.3f} gwei)')
                elif addr.lower() in in_pool:
                    out.append(f'{name} pending')
                elif rpc('eth_getTransactionByHash', h) is None:
                    out.append(f'{name} gone')
            return ', '.join(out)

        # 満杯（filler の 50 件、上乗せ 2 gwei）を 12 ブロック。2 人のトランザクションは上乗せで負けて入らない
        bob_tried = False
        for _ in range(12):
            b = mine_with(filler, to, 50)
            row('full', b, parent, status(b))
            parent = b
            if b['base_fee'] > alice_max_fee and not bob_tried:
                bob_tried = True
                try:
                    transfer(bob, to, alice_max_fee, 1 * GWEI)
                    print('  bob sends the same 2 gwei transaction: accepted')
                except RuntimeError as e:
                    print(f'  bob sends the same 2 gwei transaction: rejected ({e})')

        # 空のブロック（filler は送らない）
        for _ in range(12):
            rpc('evm_mine')
            b = block()
            row('empty', b, parent, status(b))
            parent = b
    finally:
        node.terminate()
        node.wait()


# ---- 実験 2: 小さな base fee が空のブロックでどこまで下がるか -----------------------

def run_floor():
    node, (filler, *_) = start_anvil(20, 'anvil_floor.log')
    to = '0x000000000000000000000000000000000000dEaD'
    try:
        print()
        print('== (2) start at 20 wei: empty blocks, then full blocks')
        print(HEADER)
        parent = block()
        print(f"genesis {parent['number']:>5} {0:>4} {0:>6.1f}% {parent['base_fee']:>14}")
        for _ in range(14):
            rpc('evm_mine')
            b = block()
            row('empty', b, parent)
            parent = b
        for _ in range(3):
            b = mine_with(filler, to, 50, tip=1, max_fee=1000)
            row('full', b, parent)
            parent = b
    finally:
        node.terminate()
        node.wait()


def main():
    print(subprocess.check_output([ANVIL, '--version'], text=True).splitlines()[0])
    run_main()
    run_floor()


if __name__ == '__main__':
    main()
