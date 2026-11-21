"""SQD squid-sdk（@subsquid/evm-processor）に reorg を当てる実験。ローカルの Anvil だけを使う。

- 源はノードの JSON-RPC だけ（setRpcEndpoint）。SQD Network / Portal は使わない。
- setFinalityConfirmation(10) にして、窓の内側（3 ブロック）と外側（30 ブロック）の reorg を当て、
  PostgreSQL の balance 表とノードの balanceOf を比べる。
- 公開ネットワーク・実資産・本物の秘密鍵は使わない。アカウントは Anvil のテスト用。

実行: ANVIL=... SOLC=... python3 drive.py  （npm install と npx tsc 済みであること）
"""
import json
import os
import re
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
LAB = Path(os.environ.get('LAB', HERE.parents[1]))
sys.path.insert(0, str(LAB))
from keccak import keccak256  # noqa: E402

ANVIL = os.environ.get('ANVIL', shutil.which('anvil'))
SOLC = os.environ.get('SOLC', shutil.which('solc'))
PORT, PG, METRICS = 18841, 15471, 18852
FINALITY = int(os.environ.get('FINALITY', '10'))
PGNAME = 'indexer-note-sqd-pg'
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


def psql(sql):
    return subprocess.run(['docker', 'exec', PGNAME, 'psql', '-U', 'postgres', '-d', 'squid', '-At', '-F', '\t', '-c', sql],
                          capture_output=True, text=True, timeout=10)


def db_balances():
    r = psql('SELECT id, amount FROM balance')
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip())
    return {line.split('\t')[0]: int(line.split('\t')[1]) for line in r.stdout.splitlines() if line}


def db_status():
    r = psql('SELECT height, hash FROM squid_processor.status WHERE id = 0')
    hot = psql('SELECT min(height), max(height), count(*) FROM squid_processor.hot_block')
    if r.returncode != 0:
        return r.stderr.strip()
    h, hs = r.stdout.strip().split('\t')
    lo, hi, n = (hot.stdout.strip().split('\t') + ['', '', ''])[:3]
    return {'status_height': int(h), 'status_hash': hs[:10], 'hot_min': lo or None, 'hot_max': hi or None, 'hot_count': int(n or 0)}


def metrics():
    try:
        text = urllib.request.urlopen(f'http://127.0.0.1:{METRICS}/metrics', timeout=2).read().decode()
    except Exception as e:  # noqa: BLE001
        return f'metrics に届かない（{type(e).__name__}）'
    out = {}
    for name in ('sqd_processor_last_block', 'sqd_processor_chain_height', 'sqd_processor_sync_ratio'):
        m = re.search(rf'^{name}(?:{{[^}}]*}})? (\S+)$', text, re.M)
        out[name] = float(m.group(1)) if m else None
    return out


def main():
    OUT.mkdir(exist_ok=True)
    for p in (PORT, PG, METRICS):
        with socket.socket() as so:
            so.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            so.bind(('127.0.0.1', p))  # 使用中なら止める
    subprocess.run(['docker', 'rm', '-f', PGNAME], capture_output=True)
    subprocess.check_call(['docker', 'run', '-d', '--name', PGNAME, '-p', f'127.0.0.1:{PG}:5432',
                           '-e', 'POSTGRES_PASSWORD=postgres', '-e', 'POSTGRES_DB=squid', 'postgres:16-alpine'],
                          stdout=subprocess.DEVNULL)
    src = LAB / 'Token.sol'
    code = next(iter(json.loads(subprocess.check_output(
        [SOLC, '--evm-version', 'cancun', '--combined-json', 'bin', str(src)], text=True))['contracts'].values()))['bin']
    alog = open(OUT / 'anvil.log', 'w')
    node = subprocess.Popen([ANVIL, '--host', '127.0.0.1', '--port', str(PORT), '--chain-id', '31337',
                             '--hardfork', 'cancun', '--timestamp', '1700000000', '--accounts', '4',
                             '--no-mining', '--quiet'], stdout=alog, stderr=alog)
    sqd = None
    slog = open(OUT / 'sqd.log', 'w')
    result = {'finality_confirmation': FINALITY, 'scenarios': []}
    t0 = time.monotonic()
    env = dict(os.environ, RPC_URL=f'http://127.0.0.1:{PORT}', FINALITY=str(FINALITY), METRICS_PORT=str(METRICS),
               DB_HOST='127.0.0.1', DB_PORT=str(PG), DB_NAME='squid', DB_USER='postgres', DB_PASS='postgres',
               FORCE_PRETTY_LOGGER='0', SQD_DEBUG=os.environ.get('SQD_DEBUG', 'sqd:processor'))

    def now():
        return round(time.monotonic() - t0, 2)

    def start_sqd(tag):
        slog.write(f'\n===== start {tag} at t={now()} =====\n')
        slog.flush()
        return subprocess.Popen(['node', 'lib/main.js'],
                                cwd=HERE, env=env, stdout=slog, stderr=subprocess.STDOUT, start_new_session=True)

    def stop(p):
        if p and p.poll() is None:
            os.killpg(p.pid, signal.SIGTERM)
            try:
                p.wait(10)
            except subprocess.TimeoutExpired:
                os.killpg(p.pid, signal.SIGKILL)

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
                b = db_balances()
            except Exception as e:  # noqa: BLE001
                return f'表を読めない（{str(e)[:80]}）'
            return {names[a]: b.get(a, 0) for a in accounts}

        # PostgreSQL の起動を待ち、balance 表を作る（squid-typeorm-migration apply）
        for _ in range(100):
            if psql('SELECT 1').returncode == 0:
                break
            time.sleep(0.3)
        subprocess.check_call(['npx', 'squid-typeorm-migration', 'apply'], cwd=HERE, env=env, stdout=slog, stderr=subprocess.STDOUT)

        sqd = start_sqd('initial')
        for _ in range(600):
            if sqd.poll() is not None:
                raise RuntimeError('squid が起動中に止まった（output/sqd.log）')
            if view() == truth():
                break
            time.sleep(0.2)
        result['start'] = {'head': int(rpc('eth_blockNumber'), 16), 'truth': truth(), 'sqd': view(),
                           'status': db_status(), 'metrics': metrics(), 't': now()}
        print('start', result['start'])

        def scenario(label, depth, txs, mine_after):
            for _ in range(300):
                if sqd.poll() is not None or view() == truth():
                    break
                time.sleep(0.2)
            before = {'head': int(rpc('eth_blockNumber'), 16), 'truth': truth(), 'sqd': view(), 'status': db_status(),
                      'metrics': metrics()}
            t_reorg = now()
            rpc('anvil_reorg', depth, txs)
            samples = []
            # 高さが変わらないまま 6 秒待つ
            for _ in range(20):
                samples.append({'t': round(now() - t_reorg, 2), 'sqd': view()})
                time.sleep(0.3)
            mined = []
            for _ in range(mine_after):
                rpc('evm_mine')
                mined.append(int(rpc('eth_blockNumber'), 16))
            for _ in range(20):
                samples.append({'t': round(now() - t_reorg, 2), 'sqd': view(), 'after_mine': True})
                time.sleep(0.3)
            s = {'label': label, 'depth': depth, 'finality_confirmation': FINALITY, 'before': before, 'mined': mined,
                 'truth_after': truth(), 'samples': samples, 'status_after': db_status(), 'metrics_after': metrics(),
                 'alive': sqd.poll() is None, 'exit_code': sqd.poll()}
            s['first_match_seconds'] = next((x['t'] for x in samples if x['sqd'] == s['truth_after']), None)
            result['scenarios'].append(s)
            print(label, 'truth', s['truth_after'], 'last sqd', samples[-1]['sqd'], 'first match', s['first_match_seconds'],
                  'alive', s['alive'], 'status', s['status_after'], 'metrics', s['metrics_after'])

        # 窓の内側: 直近 3 ブロックを alice→carol 7 の 1 ブロック + 空 2 ブロックに置き換える
        scenario('inside', 3, [[tx(token, alice, carol, 7), 0]], 1)
        # 窓の外側: 直近 30 ブロックを alice→dave 50 の 1 ブロック + 空 29 ブロックに置き換える
        scenario('outside', 30, [[tx(token, alice, dave, 50), 0]], 1)
        # 窓の外側の reorg の後、60 秒にわたって表・status・metrics を見続ける。5 秒ごとに 1 ブロック進める
        watch = []
        t_w = now()
        for _ in range(12):
            time.sleep(5)
            watch.append({'t': round(now() - t_w, 1), 'alive': sqd.poll() is None, 'exit_code': sqd.poll(),
                          'status': db_status(), 'metrics': metrics(), 'node_head': int(rpc('eth_blockNumber'), 16),
                          'sqd': view(), 'truth': truth()})
            rpc('evm_mine')
        result['after_outside'] = watch
        print('after outside', watch[-1])
        # 再起動したらどうなるか
        stop(sqd)
        sqd = start_sqd('restart')
        restart = []
        for _ in range(6):
            time.sleep(5)
            restart.append({'t': (len(restart) + 1) * 5, 'alive': sqd.poll() is None, 'exit_code': sqd.poll(),
                            'status': db_status(), 'metrics': metrics(), 'sqd': view(), 'truth': truth()})
            if sqd.poll() is not None:
                break
        result['restart'] = restart
        print('restart', restart[-1])
    finally:
        stop(sqd)
        node.terminate()
        node.wait()
        subprocess.run(['docker', 'rm', '-f', PGNAME], capture_output=True)
    pkg = lambda n: json.load(open(HERE / f'node_modules/{n}/package.json'))['version']  # noqa: E731
    result['versions'] = {'anvil': subprocess.check_output([ANVIL, '--version'], text=True).splitlines()[0],
                          'node': subprocess.check_output(['node', '--version'], text=True).strip(),
                          'postgres_image': 'postgres:16-alpine',
                          **{n: pkg(n) for n in ('@subsquid/evm-processor', '@subsquid/typeorm-store',
                                                 '@subsquid/util-internal-processor-tools', '@subsquid/util-internal-ingest-tools',
                                                 '@subsquid/typeorm-migration', 'typeorm')}}
    (OUT / 'results.json').write_text(json.dumps(result, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
