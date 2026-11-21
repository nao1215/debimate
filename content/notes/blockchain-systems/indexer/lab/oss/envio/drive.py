"""Envio HyperIndex に reorg を当てる実験。ローカルの Anvil だけを使う（RPC モード、HyperSync は使わない）。

- 既定の max_reorg_depth（chain ID 31337 では 199。envio_chains 表で確かめる）の内側（3 ブロック）と
  外側（250 ブロック）で、Envio の表（Hasura の GraphQL）とノードの balanceOf を比べる。
- 公開ネットワーク・実資産・本物の秘密鍵は使わない。アカウントは Anvil のテスト用。
- PostgreSQL と Hasura は Docker で先に起動しておく（run.sh）。

実行: ANVIL=... SOLC=... python3 drive.py  （proj/ で npm install 済みであること）
"""
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJ = HERE / 'proj'
LAB = Path(os.environ.get('LAB', HERE.parents[1]))
sys.path.insert(0, str(LAB))
from keccak import keccak256  # noqa: E402

ANVIL = os.environ.get('ANVIL', shutil.which('anvil'))
SOLC = os.environ.get('SOLC', shutil.which('solc'))
PORT, HASURA, SERVER, PG = 18821, 18831, 18832, 15461
OUT = HERE / 'output'
N_TRANSFERS = 300  # block 2〜301: alice→bob に 1 ずつ


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


def gql(query):
    req = urllib.request.Request(f'http://127.0.0.1:{HASURA}/v1/graphql', json.dumps({'query': query}).encode(),
                                 {'Content-Type': 'application/json', 'x-hasura-admin-secret': 'testing'})
    res = json.loads(urllib.request.urlopen(req, timeout=2).read())
    if 'errors' in res:
        raise RuntimeError(res['errors'])
    return res['data']


def http_status(path):
    try:
        return urllib.request.urlopen(f'http://127.0.0.1:{SERVER}{path}', timeout=2).status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception as e:  # noqa: BLE001
        return type(e).__name__


def metrics():
    """/metrics から reorg と進み具合に関する値だけを抜く。"""
    keys = ('envio_reorg_detected_total', 'envio_reorg_detected_block', 'envio_reorg_threshold',
            'envio_rollback_enabled', 'envio_rollback_total', 'envio_rollback_events',
            'envio_rollback_target_block', 'envio_progress_block', 'envio_indexing_known_height')
    try:
        text = urllib.request.urlopen(f'http://127.0.0.1:{SERVER}/metrics', timeout=2).read().decode()
    except Exception as e:  # noqa: BLE001
        return type(e).__name__
    out = {}
    for line in text.splitlines():
        if line.startswith('#'):
            continue
        name = line.split('{')[0].split(' ')[0]
        if name in keys:
            out[name] = float(line.rsplit(' ', 1)[1])
    return out


def pg(sql):
    return subprocess.run(['docker', 'exec', 'indexer-note-envio-pg', 'psql', '-U', 'postgres', '-d', 'envio-dev',
                           '-At', '-F', '|', '-c', sql], capture_output=True, text=True).stdout.strip()


def main():
    OUT.mkdir(exist_ok=True)
    for p in (PORT, SERVER):
        with socket.socket() as so:
            so.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            so.bind(('127.0.0.1', p))  # 使用中なら止める
    src = LAB / 'Token.sol'
    code = next(iter(json.loads(subprocess.check_output(
        [SOLC, '--evm-version', 'cancun', '--combined-json', 'bin', str(src)], text=True))['contracts'].values()))['bin']
    alog = open(OUT / 'anvil.log', 'w')
    node = subprocess.Popen([ANVIL, '--host', '127.0.0.1', '--port', str(PORT), '--chain-id', '31337',
                             '--hardfork', 'cancun', '--timestamp', '1700000000', '--accounts', '4',
                             '--no-mining', '--quiet'], stdout=alog, stderr=alog)
    envio = None
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
        assert token.lower() == '0x5fbdb2315678afecb367f032d93f642f64180aa3', token
        for _ in range(N_TRANSFERS):
            rpc('eth_sendTransaction', tx(token, alice, bob, 1))
            rpc('evm_mine')

        def head():
            return int(rpc('eth_blockNumber'), 16)

        def truth():
            return {names[a]: int(rpc('eth_call', {'to': token, 'data': calldata('balanceOf(address)', a)}, 'latest'), 16)
                    for a in accounts}

        def view():
            try:
                b = {i['id']: int(i['amount']) for i in gql('{ Balance { id amount } }')['Balance']}
            except Exception as e:  # noqa: BLE001
                return f'GraphQL に届かない（{type(e).__name__}）'
            return {names[a]: b.get(a, 0) for a in accounts}

        def meta():
            try:
                m = gql('{ _meta { chainId progressBlock sourceBlock bufferBlock isReady readyAt eventsProcessed } }')['_meta']
                return m[0] if m else None
            except Exception as e:  # noqa: BLE001
                return f'{type(e).__name__}: {e}'[:200]

        elog = open(OUT / 'envio.log', 'w')
        env = dict(os.environ, ENVIO_TUI='false', LOG_LEVEL='info')
        envio = subprocess.Popen(['npx', 'envio', 'start', '-r'], cwd=PROJ, env=env,
                                 stdout=elog, stderr=subprocess.STDOUT, start_new_session=True)
        for _ in range(900):
            if envio.poll() is not None:
                raise RuntimeError('envio が起動中に止まった（output/envio.log）')
            if http_status('/healthz') == 200:
                break
            time.sleep(0.2)
        for _ in range(600):
            if view() == truth():
                break
            time.sleep(0.2)
        result['start'] = {'t': now(), 'head': head(), 'truth': truth(), 'envio': view(), 'meta': meta(),
                           'envio_chains': pg('select id, max_reorg_depth, source_block, progress_block, '
                                              '_is_hyper_sync from envio_chains')}
        print('start', result['start'], flush=True)

        def scenario(label, depth, txs, mine_after, watch_seconds):
            for _ in range(300):
                if envio.poll() is not None or view() == truth():
                    break
                time.sleep(0.2)
            before = {'head': head(), 'truth': truth(), 'envio': view(), 'meta': meta(), 'metrics': metrics()}
            t_reorg = now()
            rpc('anvil_reorg', depth, txs)
            truth_after_reorg = truth()
            samples = []
            # 高さが変わらないまま 6 秒待つ
            for _ in range(30):
                samples.append({'t': round(now() - t_reorg, 2), 'envio': view()})
                time.sleep(0.2)
            mined = []
            for _ in range(mine_after):
                rpc('evm_mine')
                mined.append(head())
            t_mine = round(now() - t_reorg, 2)
            end = time.monotonic() + watch_seconds
            while time.monotonic() < end:
                samples.append({'t': round(now() - t_reorg, 2), 'envio': view(), 'after_mine': True})
                time.sleep(0.2)
            s = {'label': label, 'depth': depth, 'before': before, 'truth_after_reorg': truth_after_reorg,
                 'mined': mined, 't_mine': t_mine, 'truth_after': truth(), 'samples': samples,
                 'healthz': http_status('/healthz'), 'meta_after': meta(), 'metrics_after': metrics(),
                 'node_head': head(), 'alive': envio.poll() is None, 'exit_code': envio.poll()}
            s['first_match_seconds'] = next((x['t'] for x in samples if x['envio'] == s['truth_after']), None)
            s['last_envio'] = samples[-1]['envio']
            result['scenarios'].append(s)
            print(label, 'truth', s['truth_after'], 'last envio', s['last_envio'], 'first match',
                  s['first_match_seconds'], 'mine at', t_mine, 'alive', s['alive'], 'healthz', s['healthz'],
                  'meta', s['meta_after'], 'metrics', s['metrics_after'], flush=True)

        # 窓の内側: 直近 3 ブロックを alice→carol 7 の 1 ブロック + 空 2 ブロックに置き換え、1 ブロック進める
        scenario('inside', 3, [[tx(token, alice, carol, 7), 0]], 1, 30)
        # 窓の外側: 直近 250 ブロックを alice→dave 50 の 1 ブロック + 空 249 ブロックに置き換え、1 ブロック進める
        scenario('outside', 250, [[tx(token, alice, dave, 50), 0]], 1, 20)
        # 窓の外側の reorg の後、60 秒にわたって表・ヘルス・取り込み済みの番号を見続ける（5 秒ごとに 1 ブロック進める）
        watch = []
        t_w = now()
        for _ in range(12):
            time.sleep(5)
            watch.append({'t': round(now() - t_w, 1), 'alive': envio.poll() is None, 'healthz': http_status('/healthz'),
                          'meta': meta(), 'metrics': metrics(), 'node_head': head(), 'truth': truth(), 'envio': view()})
            rpc('evm_mine')
        result['after_outside'] = watch
        result['end_envio_chains'] = pg('select id, max_reorg_depth, source_block, progress_block from envio_chains')
        print('after outside', watch[-1], flush=True)
    finally:
        if envio:
            try:
                os.killpg(envio.pid, signal.SIGTERM)
                envio.wait(15)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                try:
                    os.killpg(envio.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
        node.terminate()
        node.wait()
    result['versions'] = {'anvil': subprocess.check_output([ANVIL, '--version'], text=True).splitlines()[0],
                          'envio': json.load(open(PROJ / 'node_modules/envio/package.json'))['version'],
                          'node': subprocess.check_output(['node', '--version'], text=True).strip(),
                          'postgres': 'postgres:18 (sha256:e3d24f6906d0760bf4da0dae872415391ededefad23fd471c47dc53b0ddf3c42)',
                          'hasura': 'hasura/graphql-engine:v2.43.0 (sha256:13bb9088f5b011b15af117fd1b175360f5205946bee1a78d9e0c846e5a38551c)'}
    (OUT / 'results.json').write_text(json.dumps(result, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
