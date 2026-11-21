"""Ponder に reorg を当てる実験。ローカルの Anvil だけを使う。

- reorg の窓（reorgWindow、既定 180 秒）の内側（3 ブロック = 36 秒）と外側（30 ブロック = 360 秒）で、
  Ponder の表とノードの balanceOf を比べる。ブロックの間隔は anvil_setBlockTimestampInterval で 12 秒にする。
- 公開ネットワーク・実資産・本物の秘密鍵は使わない。アカウントは Anvil のテスト用。

実行: ANVIL=... SOLC=... python3 drive.py  （ponder/ で npm install 済みであること）
"""
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
LAB = Path(os.environ.get('LAB', HERE.parent))
sys.path.insert(0, str(LAB))
from keccak import keccak256  # noqa: E402

ANVIL = os.environ.get('ANVIL', shutil.which('anvil'))
SOLC = os.environ.get('SOLC', shutil.which('solc'))
PORT, API = 18781, 42071
OUT = HERE / 'output'


def rpc(method, *params):
    body = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': list(params)}).encode()
    req = urllib.request.Request(f'http://127.0.0.1:{PORT}', body, {'Content-Type': 'application/json'})
    res = json.loads(urllib.request.urlopen(req).read())
    if 'error' in res:
        raise RuntimeError(res['error'])
    return res['result']


def word(v):
    return bytes.fromhex(v[2:]).rjust(32, b'\0') if isinstance(v, str) else v.to_bytes(32, 'big')


def calldata(sig, *args):
    return '0x' + (keccak256(sig.encode())[:4] + b''.join(word(a) for a in args)).hex()


def tx(token, sender, to, value):
    return {'from': sender, 'to': token, 'data': calldata('transfer(address,uint256)', to, value), 'gas': hex(100_000)}


def api_balances():
    q = json.dumps({'query': '{ balances(limit: 100) { items { address amount } } }'}).encode()
    req = urllib.request.Request(f'http://127.0.0.1:{API}/graphql', q, {'Content-Type': 'application/json'})
    items = json.loads(urllib.request.urlopen(req, timeout=2).read())['data']['balances']['items']
    return {i['address'].lower(): int(i['amount']) for i in items}


def main():
    OUT.mkdir(exist_ok=True)
    import socket
    for p in (PORT, API):
        with socket.socket() as so:
            so.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            so.bind(('127.0.0.1', p))  # 使用中なら止める
    shutil.rmtree(HERE / '.ponder', ignore_errors=True)
    src = LAB / 'Token.sol'
    code = next(iter(json.loads(subprocess.check_output(
        [SOLC, '--evm-version', 'cancun', '--combined-json', 'bin', str(src)], text=True))['contracts'].values()))['bin']
    alog = open(OUT / 'anvil.log', 'w')
    node = subprocess.Popen([ANVIL, '--host', '127.0.0.1', '--port', str(PORT), '--chain-id', '31337',
                             '--hardfork', 'cancun', '--timestamp', '1700000000', '--accounts', '4',
                             '--no-mining', '--quiet'], stdout=alog, stderr=alog)
    ponder = None
    result = {'scenarios': []}
    t0 = time.monotonic()

    def now():
        return round(time.monotonic() - t0, 2)

    try:
        for _ in range(100):
            try:
                accounts = [a.lower() for a in rpc('eth_accounts')]
                break
            except OSError:
                time.sleep(0.1)
        alice, bob, carol, dave = accounts
        names = {alice: 'alice', bob: 'bob', carol: 'carol', dave: 'dave'}
        rpc('anvil_setBlockTimestampInterval', 12)
        h = rpc('eth_sendTransaction', {'from': alice, 'data': '0x' + code + word(1000).hex(), 'gas': hex(2_000_000)})
        rpc('evm_mine')
        token = rpc('eth_getTransactionReceipt', h)['contractAddress']
        # block 2〜50: alice→bob に 1 ずつ
        for _ in range(49):
            rpc('eth_sendTransaction', tx(token, alice, bob, 1))
            rpc('evm_mine')

        def truth():
            return {names[a]: int(rpc('eth_call', {'to': token, 'data': calldata('balanceOf(address)', a)}, 'latest'), 16)
                    for a in accounts}

        def view():
            try:
                b = api_balances()
            except Exception as e:  # noqa: BLE001
                return f'API に届かない（{type(e).__name__}）'
            return {names[a]: b.get(a, 0) for a in accounts}

        plog = open(OUT / 'ponder.log', 'w')
        env = dict(os.environ, RPC_URL=f'http://127.0.0.1:{PORT}', PONDER_LOG_LEVEL='info')
        ponder = subprocess.Popen(['npx', 'ponder', 'start', '--port', str(API), '--schema', 'public'], cwd=HERE, env=env,
                                  stdout=plog, stderr=subprocess.STDOUT, start_new_session=True)
        for _ in range(600):
            if ponder.poll() is not None:
                raise RuntimeError('ponder が起動中に止まった（output/ponder.log）')
            try:
                if urllib.request.urlopen(f'http://127.0.0.1:{API}/ready', timeout=1).status == 200:
                    break
            except Exception:  # noqa: BLE001
                time.sleep(0.2)
        # 最新のブロックまで取り込み終わる（表がノードと一致する）まで待つ
        for _ in range(300):
            if view() == truth():
                break
            time.sleep(0.2)
        result['start'] = {'head': int(rpc('eth_blockNumber'), 16), 'truth': truth(), 'ponder': view()}
        print('start', result['start'])

        def scenario(label, depth, txs, mine_after):
            for _ in range(300):
                if ponder.poll() is not None or view() == truth():
                    break
                time.sleep(0.2)
            before = {'head': int(rpc('eth_blockNumber'), 16), 'truth': truth(), 'ponder': view()}
            t_reorg = now()
            rpc('anvil_reorg', depth, txs)
            samples = []
            # 高さが変わらないまま 6 秒待つ
            for _ in range(30):
                samples.append({'t': round(now() - t_reorg, 2), 'ponder': view()})
                time.sleep(0.2)
            mined = []
            for _ in range(mine_after):
                rpc('evm_mine')
                mined.append(int(rpc('eth_blockNumber'), 16))
            for _ in range(30):
                samples.append({'t': round(now() - t_reorg, 2), 'ponder': view(), 'after_mine': True})
                time.sleep(0.2)
            def status(path):
                try:
                    return urllib.request.urlopen(f'http://127.0.0.1:{API}{path}', timeout=2).status
                except urllib.error.HTTPError as e:
                    return e.code
                except Exception as e:  # noqa: BLE001
                    return type(e).__name__
            s = {'ready': status('/ready'), 'health': status('/health'), 'label': label, 'depth': depth, 'window_seconds': 180, 'depth_seconds': depth * 12,
                 'before': before, 'truth_after': truth(), 'samples': samples,
                 'alive': ponder.poll() is None, 'exit_code': ponder.poll()}
            first_match = next((x['t'] for x in samples if x['ponder'] == s['truth_after']), None)
            s['first_match_seconds'] = first_match
            result['scenarios'].append(s)
            print(label, 'truth', s['truth_after'], 'last ponder', samples[-1]['ponder'],
                  'first match', first_match, 'alive', s['alive'], 'ready', s['ready'], 'health', s['health'])

        # 窓の内側: 直近 3 ブロック（36 秒分）を alice→carol 7 の 1 ブロック + 空 2 ブロックに置き換える
        scenario('inside', 3, [[tx(token, alice, carol, 7), 0]], 1)
        # 窓の外側: 直近 30 ブロック（360 秒分）を alice→dave 50 の 1 ブロック + 空 29 ブロックに置き換える
        scenario('outside', 30, [[tx(token, alice, dave, 50), 0]], 1)
        # 窓の外側の reorg の後、60 秒にわたって表と /ready を見続ける
        watch = []
        t_w = now()
        for _ in range(12):
            time.sleep(5)
            try:
                ready = urllib.request.urlopen(f'http://127.0.0.1:{API}/ready', timeout=2).status
            except urllib.error.HTTPError as e:
                ready = e.code
            except Exception as e:  # noqa: BLE001
                ready = type(e).__name__
            try:
                st = json.loads(urllib.request.urlopen(f'http://127.0.0.1:{API}/status', timeout=2).read())
                indexed = st['anvil']['block']['number']
            except Exception as e:  # noqa: BLE001
                indexed = type(e).__name__
            watch.append({'t': round(now() - t_w, 1), 'alive': ponder.poll() is None, 'ready': ready,
                          'status_block': indexed, 'node_head': int(rpc('eth_blockNumber'), 16), 'ponder': view()})
            # 監視の目安を見るため、5 秒ごとに 1 ブロック進める
            rpc('evm_mine')
        result['after_outside'] = watch
        print('after outside', watch[-1], 'truth', truth())
    finally:
        if ponder:
            # npx の子の node まで止める
            import signal
            try:
                os.killpg(ponder.pid, signal.SIGTERM)
                ponder.wait(10)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                try:
                    os.killpg(ponder.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
        node.terminate()
        node.wait()
    result['versions'] = {'anvil': subprocess.check_output([ANVIL, '--version'], text=True).splitlines()[0],
                          'ponder': json.load(open(HERE / 'node_modules/ponder/package.json'))['version'],
                          'node': subprocess.check_output(['node', '--version'], text=True).strip()}
    (OUT / 'results.json').write_text(json.dumps(result, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
