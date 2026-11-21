"""Substreams（RPC Poller 経由の Firehose + tier1/tier2）と `substreams sink postgres` に reorg を当てる実験。

- 源は手元の Anvil だけ。公開ネットワーク・API トークンは使わない。アカウントは Anvil のテスト用。
- 確定の境目（LIB）は RPC Poller が「ブロック番号 - 200」で決める（firehose-ethereum v2.25.0 blockfetcher/rpc.go）。
- 窓の内側: 直近 3 ブロックの置き換え。窓の外側: 直近 215 ブロックの置き換え（共通の祖先が LIB より下）。

実行: python3 drive.py  （bin/ に fireeth・substreams、module/ に spkg、postgres:16-alpine のイメージがあること）
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

FOUNDRY = Path(os.environ.get('FOUNDRY', Path(shutil.which('anvil') or 'anvil').parent))
ANVIL = str(FOUNDRY / 'anvil')
SOLC = os.environ.get('SOLC', 'solc')
BIN = HERE / 'bin'
SPKG = HERE / 'module' / 'token-transfers-v0.1.0.spkg'
PORT = 18981
PG_PORT = 15501
PG_NAME = 'indexer-note-substreams-pg'
DSN = f'postgres://postgres:pw@127.0.0.1:{PG_PORT}/sink?sslmode=disable'
SINK_METRICS = 18992
RELAYER_HZ, MERGER_HZ = 18996, 18994
OUT = HERE / 'output'
DATA = HERE / 'run-data'


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
    r = subprocess.run(['docker', 'exec', PG_NAME, 'psql', '-U', 'postgres', 'sink', '-At', '-F', '\t', '-c', sql],
                       capture_output=True, text=True, timeout=10)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip())
    return [line.split('\t') for line in r.stdout.splitlines() if line]


def http_status(port, path='/healthz'):
    try:
        return urllib.request.urlopen(f'http://127.0.0.1:{port}{path}', timeout=2).status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception as e:  # noqa: BLE001
        return type(e).__name__


def sink_metrics():
    try:
        text = urllib.request.urlopen(f'http://127.0.0.1:{SINK_METRICS}/metrics', timeout=2).read().decode()
    except Exception as e:  # noqa: BLE001
        return type(e).__name__
    out = {}
    for line in text.splitlines():
        if line.startswith('#'):
            continue
        for key in ('head_block_number{app="substreams_sink_postgres"}', 'substreams_sink_undo_message',
                    'substreams_sink_data_message ', 'substreams_sink_processed_blocks'):
            if line.startswith(key):
                out[key.split('{')[0].strip()] = float(line.split()[-1])
    return out


def killpg(p):
    if p is None or p.poll() is not None:
        return
    try:
        os.killpg(p.pid, signal.SIGTERM)
        p.wait(15)
    except (ProcessLookupError, subprocess.TimeoutExpired):
        try:
            os.killpg(p.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def main():
    OUT.mkdir(exist_ok=True)
    for p in [PORT, PG_PORT] + list(range(18991, 19000)):
        with socket.socket() as so:
            so.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            so.bind(('127.0.0.1', p))  # 使用中なら止める
    shutil.rmtree(DATA, ignore_errors=True)
    DATA.mkdir()
    subprocess.run(['docker', 'rm', '-f', PG_NAME], capture_output=True)
    subprocess.check_call(['docker', 'run', '-d', '--name', PG_NAME, '-e', 'POSTGRES_PASSWORD=pw', '-e', 'POSTGRES_DB=sink',
                           '-p', f'127.0.0.1:{PG_PORT}:5432', 'postgres:16-alpine'], stdout=subprocess.DEVNULL)
    code = next(iter(json.loads(subprocess.check_output(
        [SOLC, '--evm-version', 'cancun', '--combined-json', 'bin', str(LAB / 'Token.sol')], text=True))['contracts'].values()))['bin']
    alog = open(OUT / 'anvil.log', 'w')
    node = subprocess.Popen([ANVIL, '--host', '127.0.0.1', '--port', str(PORT), '--chain-id', '31337',
                             '--hardfork', 'cancun', '--timestamp', '1700000000', '--accounts', '4',
                             '--no-mining', '--quiet'], stdout=alog, stderr=alog)
    poller = stack = sink = None
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
        # block 2〜30: alice→bob 1 ずつ / block 31〜236: 空 / block 237〜240: alice→bob 1 ずつ
        for _ in range(29):
            rpc('eth_sendTransaction', tx(token, alice, bob, 1))
            rpc('evm_mine')
        rpc('anvil_mine', hex(206))
        for _ in range(4):
            rpc('eth_sendTransaction', tx(token, alice, bob, 1))
            rpc('evm_mine')
        result['history_head'] = int(rpc('eth_blockNumber'), 16)

        def head():
            return int(rpc('eth_blockNumber'), 16)

        def truth():
            return {names[a]: int(rpc('eth_call', {'to': token, 'data': calldata('balanceOf(address)', a)}, 'latest'), 16)
                    for a in accounts}

        def view():
            try:
                rows = psql('select from_addr, to_addr, amount from transfers')
            except Exception as e:  # noqa: BLE001
                return f'DB に届かない（{e}）'
            bal = {n: 0 for n in names.values()}
            for f, t, amt in rows:
                f, t, amt = '0x' + f, '0x' + t, int(amt)
                if f in names:
                    bal[names[f]] -= amt
                if t in names:
                    bal[names[t]] += amt
            return bal

        def db_state():
            try:
                cur = psql('select block_num from cursors')
                hist = psql('select count(*), min(block_num), max(block_num) from substreams_history')
                rows = psql('select count(*), max(block_num) from transfers')
                return {'cursor_block': int(cur[0][0]) if cur else None, 'history': hist[0], 'transfers': rows[0]}
            except Exception as e:  # noqa: BLE001
                return str(e)

        def health():
            return {'relayer_healthz': http_status(RELAYER_HZ), 'merger_healthz': http_status(MERGER_HZ),
                    'sink_metrics': sink_metrics(),
                    'poller_alive': poller.poll() is None, 'poller_exit': poller.poll(),
                    'fireeth_alive': stack.poll() is None, 'fireeth_exit': stack.poll(),
                    'sink_alive': sink.poll() is None, 'sink_exit': sink.poll()}

        # Firehose スタック: poller の標準出力を reader-node-stdin に流す
        fd = DATA / 'fh'
        plog = open(OUT / 'poller.log', 'w')
        slog = open(OUT / 'fireeth.log', 'w')
        poller = subprocess.Popen([str(BIN / 'fireeth'), 'tools', 'poller', 'generic-evm', f'http://127.0.0.1:{PORT}', '0',
                                   f'--data-dir={fd}', '--interval-between-fetch=200ms', '--parallel-workers=2'],
                                  stdout=subprocess.PIPE, stderr=plog, start_new_session=True)
        stack = subprocess.Popen([str(BIN / 'fireeth'), 'start',
                                  'reader-node-stdin,relayer,merger,firehose,substreams-tier1,substreams-tier2',
                                  '--config-file=', '--log-format=text', '--log-to-file=false', f'--data-dir={fd}',
                                  '--common-first-streamable-block=0',
                                  '--advertise-chain-name=local-ethereum', '--advertise-block-id-encoding=hex',
                                  '--ignore-advertise-validation',
                                  '--reader-node-grpc-listen-addr=127.0.0.1:18991', '--reader-node-manager-api-addr=',
                                  '--merger-grpc-listen-addr=127.0.0.1:18993', f'--merger-http-healthz-addr=127.0.0.1:{MERGER_HZ}',
                                  '--relayer-grpc-listen-addr=127.0.0.1:18995', f'--relayer-http-healthz-addr=127.0.0.1:{RELAYER_HZ}',
                                  '--common-live-blocks-addr=127.0.0.1:18995', '--relayer-source=127.0.0.1:18991',
                                  '--firehose-grpc-listen-addr=127.0.0.1:18997',
                                  '--substreams-tier1-grpc-listen-addr=127.0.0.1:18998',
                                  '--substreams-tier2-grpc-listen-addr=127.0.0.1:18999',
                                  '--substreams-tier1-subrequests-endpoint=127.0.0.1:18999',
                                  '--substreams-tier1-block-type=sf.ethereum.type.v2.Block',
                                  '--metrics-listen-addr=', '--pprof-listen-addr=', '--log-level-switcher-listen-addr='],
                                 stdin=poller.stdout, stdout=slog, stderr=subprocess.STDOUT, start_new_session=True)
        poller.stdout.close()
        for _ in range(100):
            try:
                psql('select 1')
                break
            except Exception:  # noqa: BLE001
                time.sleep(0.3)
        subprocess.check_call([str(BIN / 'substreams'), 'sink', 'postgres', 'setup', str(SPKG), '--dsn', DSN],
                              stdout=open(OUT / 'setup.log', 'w'), stderr=subprocess.STDOUT)
        klog = open(OUT / 'sink.log', 'w')
        sink = subprocess.Popen([str(BIN / 'substreams'), 'sink', 'postgres', str(SPKG), '--dsn', DSN,
                                 '-e', '127.0.0.1:18998', '--plaintext', '--prometheus-addr', f'127.0.0.1:{SINK_METRICS}'],
                                stdout=klog, stderr=subprocess.STDOUT, start_new_session=True)
        for _ in range(600):
            if view() == truth() and isinstance(db_state(), dict) and db_state()['cursor_block'] == head():
                break
            time.sleep(0.5)
        result['start'] = {'head': head(), 'truth': truth(), 'sink': view(), 'db': db_state(), 'health': health(), 't': now()}
        print('start', result['start'], flush=True)

        def scenario(label, depth, txs, mine_after):
            before = {'head': head(), 'truth': truth(), 'sink': view(), 'db': db_state()}
            t_reorg = now()
            rpc('anvil_reorg', depth, txs)
            samples = []
            for _ in range(15):  # 高さが変わらないまま 3 秒
                samples.append({'t': round(now() - t_reorg, 2), 'sink': view()})
                time.sleep(0.2)
            t_mine = now()
            for _ in range(mine_after):
                rpc('evm_mine')
            truth_after = truth()
            for _ in range(60):  # 1 ブロック進めた後 12 秒ほど
                samples.append({'t': round(now() - t_reorg, 2), 'sink': view(), 'after_mine': True})
                time.sleep(0.2)
            s = {'label': label, 'depth': depth, 'lib_rule': 'block_num - 200',
                 'before': before, 'head_after': head(), 'truth_after': truth_after,
                 'sink_after': view(), 'db_after': db_state(), 'health': health(), 'samples': samples}
            fm = next((x['t'] for x in samples if x.get('after_mine') and x['sink'] == truth_after), None)
            s['first_match_seconds_from_reorg'] = fm
            s['first_match_seconds_from_mine'] = round(fm - (t_mine - t_reorg), 2) if fm is not None else None
            result['scenarios'].append(s)
            print(label, 'truth', truth_after, 'sink', s['sink_after'], 'db', s['db_after'],
                  'first match(from mine)', s['first_match_seconds_from_mine'], 'health', s['health'], flush=True)

        # 窓の内側: 直近 3 ブロック（alice→bob を含む 238〜240）を alice→carol 7 の 1 ブロック + 空 2 ブロックに
        scenario('inside', 3, [[tx(token, alice, carol, 7), 0]], 1)
        # 窓の外側: 直近 215 ブロックを alice→dave 50 の 1 ブロック + 空 214 ブロックに（共通の祖先は LIB より下）
        scenario('outside', 215, [[tx(token, alice, dave, 50), 0]], 1)
        watch = []
        t_w = now()
        for _ in range(12):
            time.sleep(5)
            watch.append({'t': round(now() - t_w, 1), 'node_head': head(), 'truth': truth(), 'sink': view(),
                          'db': db_state(), 'health': health()})
            rpc('evm_mine')
        result['after_outside'] = watch
        print('after outside', watch[-1], flush=True)
    finally:
        for p in (sink, stack, poller):
            killpg(p)
        node.terminate()
        node.wait()
        try:
            result['final_db_dump'] = {
                'transfers': psql('select block_num, from_addr, to_addr, amount, block_hash from transfers order by block_num'),
                'history': psql('select op, pk, block_num from substreams_history order by id'),
                'cursors': psql('select block_num, block_id from cursors')}
        except Exception as e:  # noqa: BLE001
            result['final_db_dump'] = str(e)
        subprocess.run(['docker', 'rm', '-f', PG_NAME], capture_output=True)
    result['versions'] = {'anvil': subprocess.check_output([ANVIL, '--version'], text=True).splitlines()[0],
                          'fireeth': subprocess.check_output([str(BIN / 'fireeth'), '--version'], text=True).strip(),
                          'substreams': subprocess.check_output([str(BIN / 'substreams'), '--version'], text=True).strip(),
                          'postgres_image': 'postgres:16-alpine'}
    (OUT / 'results.json').write_text(json.dumps(result, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
