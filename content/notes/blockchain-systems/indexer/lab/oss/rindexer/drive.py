"""rindexer に reorg を当てる実験。ローカルの Anvil と、Docker の PostgreSQL だけを使う。

- rindexer 1.0.0 の reorg の窓は、既定で「2 × チェーンごとの安全距離」。Anvil の chain ID 31337 は
  安全距離 64 なので 128 ブロック。窓の内側（3 ブロック）と外側（150 ブロック）の置き換えを当てる。
- 表（Transfer のイベントの行）から足し引きした残高を、ノードの balanceOf と比べる。/health も記録する。
- 公開ネットワーク・実資産・本物の秘密鍵は使わない。アカウントは Anvil のテスト用。

- rindexer.yaml の networks に reorg_handling: {enabled: true} を書かないと、reorg の検出（ReorgCoordinator）が
  そもそも作られない。窓は live に入ってから見たブロックだけで埋まるので、LIVE_FILL 秒だけ live で送金してから当てる。
- ログの細かさは RUST_LOG ではなく RINDEXER_LOG（例: RINDEXER_LOG=debug）。

実行: LIVE_FILL=150 RINDEXER=... ANVIL=... SOLC=... LAB=... python3 drive.py
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
LAB = Path(os.environ.get('LAB', HERE.parents[1]))
sys.path.insert(0, str(LAB))
from keccak import keccak256  # noqa: E402

ANVIL = os.environ.get('ANVIL', shutil.which('anvil'))
SOLC = os.environ.get('SOLC', shutil.which('solc'))
RINDEXER = os.environ.get('RINDEXER', shutil.which('rindexer_cli') or shutil.which('rindexer'))
PORT, PG_PORT, HEALTH = 18791, 15433, 18812
PG_NAME = 'indexer-note-rindexer-pg'
DB = f'postgresql://postgres:postgres@127.0.0.1:{PG_PORT}/postgres'
OUT = HERE / 'output'
BLOCKS = int(os.environ.get('BLOCKS', 200))           # block 1 でトークンを作り、2〜200 で alice→bob に 1 ずつ
INSIDE, OUTSIDE = 3, int(os.environ.get('OUTSIDE', 150))
LIVE_FILL = int(os.environ.get('LIVE_FILL', 150))  # 窓 128 ブロックが live で埋まるまでの秒数


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
    r = subprocess.run(['docker', 'exec', PG_NAME, 'psql', '-U', 'postgres', '-At', '-F', '|', '-c', sql],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip())
    return [line.split('|') for line in r.stdout.strip().splitlines() if line]


def health():
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{HEALTH}/health', timeout=2) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b'{}')
    except Exception as e:  # noqa: BLE001
        return type(e).__name__, {}


def main():
    OUT.mkdir(exist_ok=True)
    for p in (PORT, PG_PORT, HEALTH):
        with socket.socket() as so:
            so.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            so.bind(('127.0.0.1', p))  # 使用中なら止める
    code = next(iter(json.loads(subprocess.check_output(
        [SOLC, '--evm-version', 'cancun', '--combined-json', 'bin', str(LAB / 'Token.sol')], text=True))['contracts'].values()))['bin']
    subprocess.run(['docker', 'rm', '-f', PG_NAME], capture_output=True)
    subprocess.check_call(['docker', 'run', '-d', '--name', PG_NAME, '-e', 'POSTGRES_PASSWORD=postgres',
                           '-p', f'127.0.0.1:{PG_PORT}:5432', 'postgres:16-alpine'], stdout=subprocess.DEVNULL)
    alog = open(OUT / 'anvil.log', 'w')
    node = subprocess.Popen([ANVIL, '--host', '127.0.0.1', '--port', str(PORT), '--chain-id', '31337',
                             '--hardfork', 'cancun', '--accounts', '4', '--block-time', '1', '--quiet'], stdout=alog, stderr=alog)
    indexer = None
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
        for _ in range(100):
            if subprocess.run(['docker', 'exec', PG_NAME, 'pg_isready', '-U', 'postgres'], capture_output=True).returncode == 0:
                break
            time.sleep(0.3)
        time.sleep(1)
        alice, bob, carol, dave = accounts
        names = {alice: 'alice', bob: 'bob', carol: 'carol', dave: 'dave'}
        h = rpc('eth_sendTransaction', {'from': alice, 'data': '0x' + code + word(1000).hex(), 'gas': hex(2_000_000)})
        rpc('evm_mine')
        token = rpc('eth_getTransactionReceipt', h)['contractAddress']
        for _ in range(BLOCKS - 1):
            rpc('eth_sendTransaction', tx(token, alice, bob, 1))
            rpc('evm_mine')

        def truth():
            return {names[a]: int(rpc('eth_call', {'to': token, 'data': calldata('balanceOf(address)', a)}, 'latest'), 16)
                    for a in accounts}

        table = {}

        def find_table():
            rows = psql("select table_schema||'.'||table_name from information_schema.tables "
                        "where table_name ilike 'transfer' and table_schema not like 'rindexer_internal%'")
            return rows[0][0] if rows else None

        def view():
            if 'name' not in table:
                t = find_table()
                if not t:
                    return 'まだ表が無い'
                table['name'] = t
                cols = [r[0] for r in psql(f"select column_name from information_schema.columns where table_schema||'.'||table_name = '{t}'")]
                table['cols'] = cols
            t = table['name']
            try:
                rows = psql(f'select "from", "to", value from {t}')
            except RuntimeError as e:
                return f'SQL エラー（{e}）'
            bal = {n: 0 for n in names.values()}
            for frm, to, v in rows:
                v = int(v)
                if frm.lower() in names:
                    bal[names[frm.lower()]] -= v
                if to.lower() in names:
                    bal[names[to.lower()]] += v
            return bal

        def last_synced():
            try:
                rows = psql("select last_synced_block from rindexer_internal.reorglab_token_transfer where network='anvil'")
                return int(rows[0][0]) if rows else None
            except RuntimeError:
                return None

        ilog = open(OUT / 'rindexer.log', 'w')
        env = dict(os.environ, DATABASE_URL=DB, RINDEXER_LOG=os.environ.get("RINDEXER_LOG","info"))
        indexer = subprocess.Popen([RINDEXER, 'start', 'indexer'], cwd=HERE, env=env,
                                   stdout=ilog, stderr=subprocess.STDOUT, start_new_session=True)
        for _ in range(600):
            if indexer.poll() is not None:
                raise RuntimeError('rindexer が起動中に止まった（output/rindexer.log）')
            if view() == truth():
                break
            time.sleep(0.3)
        result['start'] = {'head': int(rpc('eth_blockNumber'), 16), 'truth': truth(), 'rindexer': view(),
                           'table': table, 'health': health()}
        print('start', result['start']['truth'], result['start']['rindexer'], result['start']['health'][0])

        def window():
            try:
                r = psql("select count(*), min(block_number), max(block_number) from rindexer_internal.reorg_block_hashes where network='anvil'")
                return [int(x) if x else None for x in r[0]]
            except RuntimeError:
                return None

        # 窓（ブロックのハッシュの控え）は live に入ってから見たブロックだけで埋まる。
        # 窓が埋まるまで、alice→bob 1 を 1 秒に 1 回送り続ける（--block-time 1 なので 1 ブロック 1 件）。
        fill = []
        t_f = now()
        while now() - t_f < LIVE_FILL:
            rpc('eth_sendTransaction', tx(token, alice, bob, 1))
            time.sleep(1)
            if int(now() - t_f) % 10 == 0:
                fill.append({'t': round(now() - t_f, 1), 'node_head': int(rpc('eth_blockNumber'), 16),
                             'synced': last_synced(), 'window': window()})
        time.sleep(3)
        result['live_fill'] = fill
        print('live fill done', fill[-1] if fill else None, 'window', window())

        def scenario(label, depth, txs, mine_after):
            for _ in range(300):
                if indexer.poll() is not None or view() == truth():
                    break
                time.sleep(0.2)
            before = {'head': int(rpc('eth_blockNumber'), 16), 'truth': truth(), 'rindexer': view(), 'synced': last_synced(), 'window': window(), 'health': health()}
            t_reorg = now()
            rpc('anvil_reorg', depth, txs)
            samples = []
            for _ in range(30):
                samples.append({'t': round(now() - t_reorg, 2), 'rindexer': view(), 'synced': last_synced()})
                time.sleep(0.2)
            for _ in range(mine_after):
                rpc('evm_mine')
            for _ in range(60):
                samples.append({'t': round(now() - t_reorg, 2), 'rindexer': view(), 'synced': last_synced(), 'after_mine': True})
                time.sleep(0.2)
            st, body = health()
            s = {'label': label, 'depth': depth, 'before': before, 'truth_after': truth(), 'samples': samples,
                 'alive': indexer.poll() is None, 'health': st, 'health_body': body, 'synced': last_synced(), 'window': window(), 'node_head': int(rpc('eth_blockNumber'), 16)}
            s['first_match_seconds'] = next((x['t'] for x in samples if x['rindexer'] == s['truth_after']), None)
            result['scenarios'].append(s)
            print(label, 'truth', s['truth_after'], 'last', samples[-1]['rindexer'], 'first match',
                  s['first_match_seconds'], 'alive', s['alive'], 'health', st)

        # 窓の内側: 直近 3 ブロックを alice→carol 7 の 1 ブロック + 空 2 ブロックに置き換える
        scenario('inside', INSIDE, [[tx(token, alice, carol, 7), 0]], 1)
        # 窓の外側: 直近 150 ブロックを alice→dave 50 の 1 ブロック + 空 149 ブロックに置き換える
        scenario('outside', OUTSIDE, [[tx(token, alice, dave, 50), 0]], 1)
        watch = []
        t_w = now()
        for _ in range(12):
            time.sleep(5)
            st, body = health()
            watch.append({'t': round(now() - t_w, 1), 'alive': indexer.poll() is None, 'health': st, 'health_body': body, 'synced': last_synced(),
                          'node_head': int(rpc('eth_blockNumber'), 16), 'rindexer': view(), 'truth': truth(), 'window': window()})
            rpc('evm_mine')
        result['after_outside'] = watch
        print('after outside', watch[-1], 'truth', truth())
    finally:
        if indexer:
            try:
                os.killpg(indexer.pid, signal.SIGTERM)
                indexer.wait(10)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                try:
                    os.killpg(indexer.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
        node.terminate()
        node.wait()
        subprocess.run(['docker', 'rm', '-f', PG_NAME], capture_output=True)
    result['versions'] = {'anvil': subprocess.check_output([ANVIL, '--version'], text=True).splitlines()[0],
                          'rindexer': subprocess.check_output([RINDEXER, '--version'], text=True).strip()}
    (OUT / 'results.json').write_text(json.dumps(result, ensure_ascii=False, indent=1, default=str))


if __name__ == '__main__':
    main()
