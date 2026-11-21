"""Shovel に reorg を当てる実験。ローカルの Anvil と Docker の PostgreSQL だけを使う。

- Shovel の Converge は、取り込んだ最新のブロックの hash と、次のブロックの parent が食い違うと
  shovel.task_updates の最新の行（と表の行）を消して取り直す。1 回の Converge で取り直す回数に上限がある
  （v1.6 は reorgs <= 10 で 11 回、main の aea8d42 は reorgs <= 1000 で 1001 回）。
  batch_size 1（既定）では 1 行 = 1 ブロックなので、上限はおおよそブロック数になる。
- さらに shovel.task_updates は起動時と 10 分ごとに最新 200 行まで刈り込まれる（PruneTask(ctx, pg, 200)）。
- 公開ネットワーク・実資産・本物の秘密鍵は使わない。アカウントは Anvil のテスト用。

実行: python3 drive.py <label> <shovel のバイナリ> <ブロック数> <シナリオ...>
  シナリオ: in:<深さ>（窓の内側として見る）、out:<深さ>（外側として見て 60 秒観察）、restart（Shovel を再起動して刈り込みを起こす）
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
LAB = Path(os.environ.get('LAB', Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(LAB))
from keccak import keccak256  # noqa: E402

ANVIL = os.environ.get('ANVIL', 'anvil')
SOLC = os.environ.get('SOLC', 'solc')
PORT, PG, DASH = 18861, 15481, 18871
PGC = 'indexer-note-shovel-pg'
PGPW = 'shovel-local-test'


def rpc(method, *params):
    body = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': list(params)}).encode()
    req = urllib.request.Request(f'http://127.0.0.1:{PORT}', body, {'Content-Type': 'application/json'})
    res = json.loads(urllib.request.urlopen(req, timeout=60).read())
    if 'error' in res:
        raise RuntimeError(res['error'])
    return res['result']


def word(v):
    return bytes.fromhex(v[2:]).rjust(32, b'\0') if isinstance(v, str) else v.to_bytes(32, 'big')


def calldata(sig, *args):
    return '0x' + (keccak256(sig.encode())[:4] + b''.join(word(a) for a in args)).hex()


def tx(token, sender, to, value):
    return {'from': sender, 'to': token, 'data': calldata('transfer(address,uint256)', to, value), 'gas': hex(100_000)}


def psql(q):
    r = subprocess.run(['docker', 'exec', PGC, 'psql', '-U', 'postgres', '-d', 'shovel', '-At', '-F', '|', '-c', q],
                       capture_output=True, text=True, timeout=20)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip())
    return [line.split('|') for line in r.stdout.strip().splitlines() if line]


def http(path):
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{DASH}{path}', timeout=3) as r:
            return r.status, r.read().decode(errors='replace')
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors='replace')
    except Exception as e:  # noqa: BLE001
        return type(e).__name__, ''


def main():
    label, binary, nblocks, *steps = sys.argv[1:]
    nblocks = int(nblocks)
    out = HERE / 'output' / label
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    for p in (PORT, PG, DASH):
        with socket.socket() as so:
            so.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            so.bind(('127.0.0.1', p))  # 使用中なら止める
    subprocess.run(['docker', 'rm', '-f', PGC], capture_output=True)
    subprocess.check_call(['docker', 'run', '-d', '--name', PGC, '-p', f'127.0.0.1:{PG}:5432',
                           '-e', f'POSTGRES_PASSWORD={PGPW}', '-e', 'POSTGRES_DB=shovel', 'postgres:16-alpine'],
                          stdout=subprocess.DEVNULL)
    code = next(iter(json.loads(subprocess.check_output(
        [SOLC, '--evm-version', 'cancun', '--combined-json', 'bin', str(LAB / 'Token.sol')], text=True))['contracts'].values()))['bin']
    alog = open(out / 'anvil.log', 'w')
    node = subprocess.Popen([ANVIL, '--host', '127.0.0.1', '--port', str(PORT), '--chain-id', '31337',
                             '--hardfork', 'cancun', '--timestamp', '1700000000', '--accounts', '4',
                             '--no-mining', '--quiet', *os.environ.get('ANVIL_EXTRA', '').split()], stdout=alog, stderr=alog)
    proc = {'p': None, 'n': 0}
    result = {'label': label, 'binary': binary, 'nblocks': nblocks, 'steps': steps, 'scenarios': []}
    t0 = time.monotonic()

    def now():
        return round(time.monotonic() - t0, 2)

    def start_shovel():
        proc['n'] += 1
        log = open(out / f'shovel-{proc["n"]}.log', 'w')
        proc['p'] = subprocess.Popen([binary, '-config', str(out / 'config.json'), '-l', f'127.0.0.1:{DASH}', '-v'],
                                     stdout=log, stderr=subprocess.STDOUT, start_new_session=True)

    def stop_shovel():
        p = proc['p']
        if p and p.poll() is None:
            os.killpg(p.pid, signal.SIGTERM)
            try:
                p.wait(10)
            except subprocess.TimeoutExpired:
                os.killpg(p.pid, signal.SIGKILL)
                p.wait()

    try:
        for _ in range(100):
            try:
                accounts = [a.lower() for a in rpc('eth_accounts')]
                break
            except OSError:
                time.sleep(0.1)
        for _ in range(100):
            try:
                psql('select 1')
                break
            except Exception:  # noqa: BLE001
                time.sleep(0.3)
        alice, bob, carol, dave = accounts
        names = {alice: 'alice', bob: 'bob', carol: 'carol', dave: 'dave'}
        rpc('anvil_setBlockTimestampInterval', 12)
        h = rpc('eth_sendTransaction', {'from': alice, 'data': '0x' + code + word(1_000_000).hex(), 'gas': hex(2_000_000)})
        rpc('evm_mine')
        token = rpc('eth_getTransactionReceipt', h)['contractAddress']
        # block 2〜nblocks: alice→bob に 1 ずつ
        for _ in range(nblocks - 1):
            rpc('eth_sendTransaction', tx(token, alice, bob, 1))
            rpc('evm_mine')
        conf = {
            'pg_url': f'postgres://postgres:{PGPW}@127.0.0.1:{PG}/shovel?sslmode=disable',
            'eth_sources': [{'name': 'anvil', 'chain_id': 31337, 'url': f'http://127.0.0.1:{PORT}',
                             'batch_size': 1, 'concurrency': 1, 'poll_duration': '500ms'}],
            'integrations': [{
                'name': 'token_transfers', 'enabled': True,
                'sources': [{'name': 'anvil', 'start': 1}],
                'table': {'name': 'transfers', 'columns': [
                    {'name': 'log_addr', 'type': 'bytea'},
                    {'name': 'f', 'type': 'bytea'}, {'name': 't', 'type': 'bytea'}, {'name': 'v', 'type': 'numeric'}]},
                'block': [{'name': 'log_addr', 'column': 'log_addr', 'filter_op': 'contains', 'filter_arg': [token[2:].lower()]}],
                'event': {'name': 'Transfer', 'type': 'event', 'anonymous': False, 'inputs': [
                    {'indexed': True, 'name': 'from', 'type': 'address', 'column': 'f'},
                    {'indexed': True, 'name': 'to', 'type': 'address', 'column': 't'},
                    {'indexed': False, 'name': 'value', 'type': 'uint256', 'column': 'v'}]},
            }],
        }
        if os.environ.get('BLOCK_TIME') == '1':
            # block_time（ヘッダーの項目）を選ぶと、Shovel は eth_getBlockByNumber でヘッダーを取り、parent を比べられる
            conf['integrations'][0]['table']['columns'].append({'name': 'block_time', 'type': 'numeric'})
            conf['integrations'][0]['block'].append({'name': 'block_time', 'column': 'block_time'})
        result['block_time_selected'] = os.environ.get('BLOCK_TIME') == '1'
        (out / 'config.json').write_text(json.dumps(conf, indent=1))

        def truth():
            return {names[a]: int(rpc('eth_call', {'to': token, 'data': calldata('balanceOf(address)', a)}, 'latest'), 16)
                    for a in accounts}

        def view():
            try:
                rows = psql("select encode(f,'hex'), encode(t,'hex'), v::text from transfers")
            except Exception as e:  # noqa: BLE001
                return f'表に届かない（{str(e)[:80]}）'
            b = {a: 0 for a in accounts}
            for f, t, v in rows:
                f, t = '0x' + f, '0x' + t
                if f in b:
                    b[f] -= int(v)
                if t in b:
                    b[t] += int(v)
            return {names[a]: b[a] for a in accounts}

        def internal():
            try:
                r = psql("select coalesce(max(num),-1)::text, count(*)::text, coalesce(min(num),-1)::text from shovel.task_updates")[0]
                rows = psql('select count(*)::text, coalesce(max(block_num),-1)::text from transfers')[0]
                return {'task_max': int(r[0]), 'task_rows': int(r[1]), 'task_min': int(r[2]),
                        'transfer_rows': int(rows[0]), 'transfer_max_block': int(rows[1])}
            except Exception as e:  # noqa: BLE001
                return str(e)[:120]

        def metrics():
            st, body = http('/metrics')
            m = {}
            for line in body.splitlines():
                if line.startswith('shovel_') and ' ' in line:
                    k, v = line.rsplit(' ', 1)
                    m[k] = v
            return {'status': st, 'values': m} if m else {'status': st, 'body': body[:80]}

        def wait_match(limit=600):
            for _ in range(limit):
                if proc['p'].poll() is not None or view() == truth():
                    return True
                time.sleep(0.5)
            return False

        start_shovel()
        t_start = now()
        ok = wait_match(1200)
        result['start'] = {'head': int(rpc('eth_blockNumber'), 16), 'truth': truth(), 'shovel': view(),
                           'seconds': round(now() - t_start, 1), 'matched': ok, 'internal': internal(),
                           'dashboard_status': http('/')[0]}
        print('start', result['start'], flush=True)

        for step in steps:
            if step == 'restart':
                stop_shovel()
                before = internal()
                start_shovel()
                time.sleep(5)
                result['scenarios'].append({'label': 'restart', 'before': before, 'after': internal(),
                                            'alive': proc['p'].poll() is None})
                print('restart', result['scenarios'][-1], flush=True)
                continue
            kind, depth = step.split(':')
            depth = int(depth)
            wait_match()
            before = {'head': int(rpc('eth_blockNumber'), 16), 'truth': truth(), 'shovel': view(), 'internal': internal()}
            t_reorg = now()
            rpc('anvil_reorg', depth, [[tx(token, alice, carol if kind == 'in' else dave, 7 if kind == 'in' else 50), 0]])
            samples = []
            for _ in range(6):
                samples.append({'t': round(now() - t_reorg, 2), 'shovel': view()})
                time.sleep(0.5)
            rpc('evm_mine')
            t_mine = now()
            for _ in range(20):
                samples.append({'t': round(now() - t_reorg, 2), 'shovel': view(), 'after_mine': True})
                time.sleep(0.5)
            s = {'label': step, 'depth': depth, 'before': before, 'truth_after': truth(), 'samples': samples,
                 'internal': internal(), 'metrics': metrics(), 'node_head': int(rpc('eth_blockNumber'), 16),
                 'alive': proc['p'].poll() is None, 'exit_code': proc['p'].poll(),
                 'seconds_reorg_to_mine': round(t_mine - t_reorg, 2)}
            fm = next((x['t'] for x in samples if x.get('after_mine') and x['shovel'] == s['truth_after']), None)
            s['first_match_seconds_after_reorg'] = fm
            s['first_match_seconds_after_mine'] = None if fm is None else round(fm - (t_mine - t_reorg), 2)
            if kind == 'out':
                watch = []
                t_w = now()
                for _ in range(12):
                    time.sleep(5)
                    time.sleep(1.1)
                    st, diag = http('/diag')
                    watch.append({'t': round(now() - t_w, 1), 'alive': proc['p'].poll() is None,
                                  'internal': internal(), 'node_head': int(rpc('eth_blockNumber'), 16),
                                  'shovel': view(), 'truth': truth(), 'diag': [st, diag[:300]], 'dashboard': http('/')[0]})
                    time.sleep(1.1)
                    watch[-1]['metrics'] = metrics()
                    rpc('evm_mine')
                s['watch'] = watch
            result['scenarios'].append(s)
            print(step, 'truth', s['truth_after'], 'last', samples[-1]['shovel'], 'match', fm,
                  'alive', s['alive'], 'internal', s['internal'], flush=True)
            if kind == 'out':
                print('watch last', s['watch'][-1], flush=True)
    finally:
        stop_shovel()
        node.terminate()
        node.wait()
        subprocess.run(['docker', 'rm', '-f', PGC], capture_output=True)
    result['versions'] = {'anvil': subprocess.check_output([ANVIL, '--version'], text=True).splitlines()[0],
                          'shovel': subprocess.check_output([binary, '-version'], text=True).strip(),
                          'postgres': 'postgres:16-alpine', 'anvil_extra': os.environ.get('ANVIL_EXTRA', '')}
    (out / 'results.json').write_text(json.dumps(result, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
