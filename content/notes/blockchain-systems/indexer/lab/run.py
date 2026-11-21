"""インデクサーの実験。ローカルの Anvil だけを使う。

- 公開ネットワーク・実資産・本物の秘密鍵は使わない。
- アカウントは Anvil が既定で作るテスト用のもの（鍵が広く公開されており、説明用で無価値）。
- 自動のマイニングを止め（--no-mining）、evm_mine で 1 ブロックずつ作る。
- reorg は Anvil の anvil_reorg で起こす（直近の depth 個のブロックを、別の中身のブロックに置き換える）。

実行: ANVIL=... SOLC=... python3 run.py  （PATH にあれば環境変数は不要）
"""
import json
import os
import shutil
import subprocess
import time
import urllib.request
from pathlib import Path

from keccak import keccak256

LAB = Path(__file__).resolve().parent
ANVIL = os.environ.get('ANVIL', shutil.which('anvil'))
SOLC = os.environ.get('SOLC', shutil.which('solc'))
PORT = 18771
ETH = 10**18
TRANSFER = '0x' + keccak256(b'Transfer(address,address,uint256)').hex()


def rpc(method, *params):
    body = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': list(params)}).encode()
    req = urllib.request.Request(f'http://127.0.0.1:{PORT}', body, {'Content-Type': 'application/json'})
    res = json.loads(urllib.request.urlopen(req).read())
    if 'error' in res:
        raise RuntimeError(res['error'])
    return res['result']


def word(v):
    if isinstance(v, str):
        return bytes.fromhex(v[2:]).rjust(32, b'\0')
    return v.to_bytes(32, 'big')


def calldata(signature, *args):
    return '0x' + (keccak256(signature.encode())[:4] + b''.join(word(a) for a in args)).hex()


def transfer_tx(token, sender, to, value):
    return {'from': sender, 'to': token, 'data': calldata('transfer(address,uint256)', to, value), 'gas': hex(100_000)}


def head():
    return int(rpc('eth_blockNumber'), 16)


def block(n):
    return rpc('eth_getBlockByNumber', hex(n), False)


def logs(token, frm, to):
    return rpc('eth_getLogs', {'address': token, 'topics': [TRANSFER], 'fromBlock': hex(frm), 'toBlock': hex(to)})


def addr(topic):
    return '0x' + topic[-40:]


def deltas(entries):
    """Transfer ログを (アドレス, 増減) の並びにする。"""
    out = []
    for e in entries:
        v = int(e['data'], 16)
        frm, to = addr(e['topics'][1]), addr(e['topics'][2])
        if int(frm, 16) != 0:
            out.append((frm, -v))
        out.append((to, v))
    return out


class NaiveIndexer:
    """最後に取り込んだブロック番号だけを記録し、新しい番号のログを足していく。"""

    def __init__(self, token):
        self.token, self.cursor, self.balance = token, 0, {}

    def poll(self):
        h = head()
        if h > self.cursor:
            for a, d in deltas(logs(self.token, self.cursor + 1, h)):
                self.balance[a] = self.balance.get(a, 0) + d
            self.cursor = h
        return []


class HashCheckingIndexer:
    """取り込んだブロックのハッシュと、ブロックごとの増減を記録する。
    次のブロックの parentHash が記録したハッシュと違えば、一致する所まで巻き戻して増減を取り消す。"""

    def __init__(self, token):
        self.token, self.hashes, self.undo, self.balance = token, {}, {}, {}

    def apply(self, n, sign, ds):
        for a, d in ds:
            self.balance[a] = self.balance.get(a, 0) + sign * d

    def poll(self):
        events = []
        n = max(self.hashes, default=0) + 1
        while n <= head():
            b = block(n)
            if n - 1 in self.hashes and b['parentHash'] != self.hashes[n - 1]:
                # 記録したブロックが今のチェーンに無い。一致する所まで戻る
                k = n - 1
                while k in self.hashes and block(k)['hash'] != self.hashes[k]:
                    self.apply(k, -1, self.undo.pop(k))
                    del self.hashes[k]
                    events.append(f'rollback block {k}')
                    k -= 1
                n = k + 1
                continue
            # ブロックのハッシュで取る。番号で取ると、取る間に置き換わったブロックを取得することがある
            ds = deltas(rpc('eth_getLogs', {'address': self.token, 'topics': [TRANSFER], 'blockHash': b['hash']}))
            self.apply(n, 1, ds)
            self.undo[n], self.hashes[n] = ds, b['hash']
            n += 1
        return events


def main():
    out_dir = LAB / 'output'
    out_dir.mkdir(exist_ok=True)
    src = LAB / 'Token.sol'
    compiled = json.loads(subprocess.check_output(
        [SOLC, '--evm-version', 'cancun', '--combined-json', 'bin', str(src)], text=True))
    code = next(iter(compiled['contracts'].values()))['bin']
    versions = [subprocess.check_output([ANVIL, '--version'], text=True).splitlines()[0],
                subprocess.check_output([SOLC, '--version'], text=True).splitlines()[-1]]
    log = open(out_dir / 'anvil.log', 'w')
    node = subprocess.Popen([ANVIL, '--host', '127.0.0.1', '--port', str(PORT), '--chain-id', '31337',
                             '--hardfork', 'cancun', '--timestamp', '1700000000', '--accounts', '4',
                             '--no-mining', '--quiet'], stdout=log, stderr=log)
    result = {'versions': versions, 'steps': []}
    try:
        for _ in range(100):
            try:
                accounts = rpc('eth_accounts')
                break
            except OSError:
                time.sleep(0.1)
        alice, bob, carol, dave = [a.lower() for a in accounts]
        names = {alice: 'alice', bob: 'bob', carol: 'carol', dave: 'dave'}

        # block 1: トークンを作り、alice に 1000 を渡す
        h = rpc('eth_sendTransaction', {'from': alice, 'data': '0x' + code + word(1000).hex(), 'gas': hex(2_000_000)})
        rpc('evm_mine')
        token = rpc('eth_getTransactionReceipt', h)['contractAddress']

        naive, careful = NaiveIndexer(token), HashCheckingIndexer(token)

        def truth():
            return {names[a]: int(rpc('eth_call', {'to': token, 'data': calldata('balanceOf(address)', a)}, 'latest'), 16)
                    for a in names}

        def chain():
            rows = []
            for n in range(1, head() + 1):
                b = rpc('eth_getBlockByNumber', hex(n), True)
                txs = []
                for tx in b['transactions']:
                    if tx['to'] is None:
                        txs.append('トークンを作る（alice に 1000）')
                    elif tx['to'].lower() == token.lower():
                        to, v = '0x' + tx['input'][34:74], int(tx['input'][74:], 16)
                        txs.append(f'{names[tx["from"].lower()]}→{names[to]} {v}')
                    else:
                        txs.append(f'{names[tx["from"].lower()]}→{names[tx["to"].lower()]} {int(tx["value"], 16) // ETH} ETH')
                rows.append({'number': n, 'hash': b['hash'][:8], 'parent': b['parentHash'][:8], 'txs': txs})
            return rows

        def view(ix):
            # truth と同じ alice・bob・carol・dave の順に並べる
            return {n: ix.balance.get(a, 0) for a, n in names.items()}

        def step(label):
            ev = careful.poll()
            naive.poll()
            s = {'label': label, 'chain': chain(), 'truth': truth(), 'naive': view(naive),
                 'careful': view(careful), 'careful_events': ev}
            result['steps'].append(s)
            print(f'== {label}')
            for r in s['chain']:
                print(f'  block {r["number"]} {r["hash"]} (parent {r["parent"]}): {", ".join(r["txs"]) or "-"}')
            for k in ('truth', 'naive', 'careful'):
                print(f'  {k:<8} {s[k]}')
            for e in ev:
                print(f'  careful: {e}')

        step('block 1: トークンを作る')

        # block 2: alice→bob 100
        rpc('eth_sendTransaction', transfer_tx(token, alice, bob, 100))
        rpc('evm_mine')
        step('block 2')

        # block 3: alice→carol 50 と、alice→carol に 1 ETH をそのまま送る（ログが出ない）
        rpc('eth_sendTransaction', transfer_tx(token, alice, carol, 50))
        eth_tx = rpc('eth_sendTransaction', {'from': alice, 'to': carol, 'value': hex(ETH)})
        rpc('evm_mine')
        receipt = rpc('eth_getTransactionReceipt', eth_tx)
        result['eth_transfer'] = {'status': receipt['status'], 'logs': receipt['logs'],
                                  'carol_wei': int(rpc('eth_getBalance', carol, 'latest'), 16)}
        print(f'== ETH の送金: status {receipt["status"]}, logs {receipt["logs"]}')
        step('block 3')

        # block 4: bob→carol 30
        rpc('eth_sendTransaction', transfer_tx(token, bob, carol, 30))
        rpc('evm_mine')
        step('block 4')

        all_logs = logs(token, 0, head())
        result['log_count'] = len(all_logs)
        print(f'== eth_getLogs の件数（block 0〜{head()}、Transfer）: {len(all_logs)}')

        # reorg: block 3 と 4 を、alice→dave 100 だけを含む 2 ブロックに置き換える
        rpc('anvil_reorg', 2, [[transfer_tx(token, alice, dave, 100), 0]])
        step('reorg: block 3 と 4 を置き換えた直後（高さは同じ）')

        # block 5: dave→carol 10
        rpc('eth_sendTransaction', transfer_tx(token, dave, carol, 10))
        rpc('evm_mine')
        step('block 5')
    finally:
        node.terminate()
        node.wait()
    (out_dir / 'results.json').write_text(json.dumps(result, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
