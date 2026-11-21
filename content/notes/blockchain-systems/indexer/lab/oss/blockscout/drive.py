"""Blockscout（バックエンドと DB だけ）に reorg を当てる実験。ローカルの Anvil（Docker）だけを使う。

- 浅い reorg（3）と深い reorg（100、300）で、Blockscout の API が返すトークン残高・Transfer と、
  ノードの balanceOf を比べる。DB の blocks.consensus、missing_block_ranges、/api/health も記録する。
- 公開ネットワーク・実資産・本物の秘密鍵は使わない。アカウントは Anvil のテスト用。
- コンテナは indexer-note-blockscout-*。ポートは 127.0.0.1 だけに出す。

実行: python3 drive.py   （イメージ indexer-note-blockscout:12.0.4 を公式の docker/Dockerfile で build 済みであること）
"""
import json
import os
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

SOLC = os.environ.get('SOLC', 'solc')
OUT = HERE / (os.environ.get('OUT') or 'output')
NET = 'indexer-note-blockscout-net'
P = 'indexer-note-blockscout-'
ANVIL_PORT, PG_PORT, API_PORT = 18961, 15491, 18971
BS_IMAGE = os.environ.get('BS_IMAGE', 'indexer-note-blockscout:12.0.4')
ANVIL_IMAGE = 'ghcr.io/foundry-rs/foundry:v1.7.1'
PG_IMAGE = 'postgres:17'
HEAD_TARGET = int(os.environ.get('HEAD_TARGET', '360'))
DEPTHS = [int(x) for x in os.environ.get('DEPTHS', '3,100,300').split(',')]
API = f'http://127.0.0.1:{API_PORT}'

BS_ENV = {
    'ETHEREUM_JSONRPC_VARIANT': 'anvil',
    'ETHEREUM_JSONRPC_HTTP_URL': 'http://anvil:8545/',
    'ETHEREUM_JSONRPC_TRACE_URL': 'http://anvil:8545/',
    'ETHEREUM_JSONRPC_WS_URL': 'ws://anvil:8545/',
    'ETHEREUM_JSONRPC_TRANSPORT': 'http',
    # v12.0.4 の Anvil 用の設定（apps/indexer/config/prod/anvil.exs）は trace_urls を持たない。古いブロックの残高は
    # trace の URL へ投げるので "URL is nil" で失敗し続け、RPC の URL が使えない扱いになって取り込みが止まった（output-fail1/）。
    # そのため古いブロックの残高（archive balances）を切る。
    'ETHEREUM_JSONRPC_DISABLE_ARCHIVE_BALANCES': 'true',
    'INDEXER_DISABLE_INTERNAL_TRANSACTIONS_FETCHER': 'true',
    'INDEXER_DISABLE_PENDING_TRANSACTIONS_FETCHER': 'true',
    'CHAIN_ID': '31337',
    'DATABASE_URL': 'postgresql://blockscout:let-me-in@postgres:5432/blockscout',
    'ECTO_SSL_MODE': 'disable',
    'SECRET_KEY_BASE': '56NtB48ear7+wMSf0IQuWDAAazhpb31qyc7GiyspBP2vh7t5zlCsF5QDv76chXeN',
    'PORT': '4000',
    'DISABLE_MARKET': 'true',
    'POOL_SIZE': '40', 'POOL_SIZE_API': '10',
    'HEART_BEAT_TIMEOUT': '30',
    'ADMIN_PANEL_ENABLED': 'false',
    'API_V1_READ_METHODS_DISABLED': 'false', 'API_V1_WRITE_METHODS_DISABLED': 'false',
    'RE_CAPTCHA_DISABLED': 'true',
    'MICROSERVICE_SC_VERIFIER_ENABLED': 'false',
    'MICROSERVICE_VISUALIZE_SOL2UML_ENABLED': 'false',
    'MICROSERVICE_SIG_PROVIDER_ENABLED': 'false',
    'MICROSERVICE_ACCOUNT_ABSTRACTION_ENABLED': 'false',
    'ACCOUNT_ENABLED': 'false',
    'NFT_MEDIA_HANDLER_ENABLED': 'false',
    'DISABLE_FILE_LOGGING': 'true',
    'COIN': 'ETH', 'COIN_NAME': 'Ether',
}


def sh(*a, check=True, **kw):
    return subprocess.run(list(a), check=check, text=True, capture_output=True, **kw)


def post(url, obj, timeout=5):
    req = urllib.request.Request(url, json.dumps(obj).encode(), {'Content-Type': 'application/json'})
    return json.loads(urllib.request.urlopen(req, timeout=timeout).read())


def get(path, timeout=10):
    try:
        with urllib.request.urlopen(API + path, timeout=timeout) as r:
            body = r.read().decode()
            code = r.status
    except urllib.error.HTTPError as e:
        body, code = e.read().decode(), e.code
    except Exception as e:  # noqa: BLE001
        return {'status': None, 'error': f'{type(e).__name__}: {e}'}
    try:
        return {'status': code, 'json': json.loads(body)}
    except ValueError:
        return {'status': code, 'text': body[:300]}


def rpc(method, *params):
    res = post(f'http://127.0.0.1:{ANVIL_PORT}', {'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': list(params)}, 60)
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
    r = sh('docker', 'exec', P + 'postgres', 'psql', '-U', 'blockscout', '-d', 'blockscout', '-At', '-F', '|', '-c', q, check=False)
    return r.stdout.strip() if r.returncode == 0 else f'ERR {r.stderr.strip()[:200]}'


def cleanup():
    names = sh('docker', 'ps', '-a', '--filter', f'name=^{P}', '--format', '{{.Names}}', check=False).stdout.split()
    if names:
        sh('docker', 'rm', '-f', *names, check=False)
    sh('docker', 'network', 'rm', NET, check=False)


def main():
    OUT.mkdir(exist_ok=True)
    cleanup()
    sh('docker', 'network', 'create', NET)
    # Anvil。時刻は実時間から始める（Blockscout の /api/health は最新ブロックの時刻と今の差で判定するため）
    sh('docker', 'run', '-d', '--name', P + 'anvil', '--network', NET, '--network-alias', 'anvil',
       '-p', f'127.0.0.1:{ANVIL_PORT}:8545', ANVIL_IMAGE,
       'anvil --host 0.0.0.0 --port 8545 --chain-id 31337 --hardfork cancun --accounts 4 --no-mining')
    sh('docker', 'run', '-d', '--name', P + 'postgres', '--network', NET, '--network-alias', 'postgres',
       '-p', f'127.0.0.1:{PG_PORT}:5432', '-e', 'POSTGRES_USER=blockscout', '-e', 'POSTGRES_PASSWORD=let-me-in',
       '-e', 'POSTGRES_DB=blockscout', '--shm-size', '256m', PG_IMAGE,
       'postgres', '-c', 'max_connections=200', '-c', 'client_connection_check_interval=60000')

    result = {'scenarios': [], 'head_target': HEAD_TARGET, 'depths': DEPTHS}
    t0 = time.monotonic()

    def now():
        return round(time.monotonic() - t0, 2)

    log = open(OUT / 'drive.txt', 'w')

    def say(*a):
        line = ' '.join(str(x) for x in a)
        print(line, flush=True)
        log.write(line + '\n')
        log.flush()

    try:
        for _ in range(200):
            try:
                accounts = [a.lower() for a in rpc('eth_accounts')]
                break
            except Exception:  # noqa: BLE001
                time.sleep(0.3)
        alice, bob, carol, dave = accounts
        names = {alice: 'alice', bob: 'bob', carol: 'carol', dave: 'dave'}
        rpc('anvil_setBlockTimestampInterval', 1)
        code = next(iter(json.loads(subprocess.check_output(
            [SOLC, '--evm-version', 'cancun', '--combined-json', 'bin', str(LAB / 'Token.sol')], text=True))['contracts'].values()))['bin']
        h = rpc('eth_sendTransaction', {'from': alice, 'data': '0x' + code + word(1000).hex(), 'gas': hex(2_000_000)})
        rpc('evm_mine')
        token = rpc('eth_getTransactionReceipt', h)['contractAddress'].lower()
        assert token == '0x5fbdb2315678afecb367f032d93f642f64180aa3', token
        for _ in range(HEAD_TARGET - 1):
            rpc('eth_sendTransaction', tx(token, alice, bob, 1))
            rpc('evm_mine')

        def head():
            return int(rpc('eth_blockNumber'), 16)

        def truth():
            return {names[a]: int(rpc('eth_call', {'to': token, 'data': calldata('balanceOf(address)', a)}, 'latest'), 16)
                    for a in accounts}

        def node_transfer_count():
            logs = rpc('eth_getLogs', {'fromBlock': '0x0', 'toBlock': 'latest', 'address': token})
            return len(logs)

        def api_balances():
            out = {}
            for a in accounts:
                r = get(f'/api/v2/addresses/{a}/token-balances')
                if r.get('status') != 200:
                    out[names[a]] = f"HTTP {r.get('status')} {r.get('error', '')}"[:120]
                    continue
                v = 0
                for it in r['json']:
                    if (it.get('token') or {}).get('address_hash', it.get('token', {}).get('address', '')).lower() == token:
                        v = int(it['value'])
                out[names[a]] = v
            return out

        def api_counters():
            r = get(f'/api/v2/tokens/{token}/counters')
            return r.get('json') if r.get('status') == 200 else r

        def api_latest_transfer():
            r = get(f'/api/v2/tokens/{token}/transfers')
            if r.get('status') != 200:
                return r
            items = r['json'].get('items', [])
            return [{'block': it.get('block_number'), 'to': (it.get('to') or {}).get('hash', '').lower()[:10],
                     'value': (it.get('total') or {}).get('value'), 'tx': it.get('transaction_hash', '')[:12]} for it in items[:3]]

        def health():
            h1 = get('/api/health')
            return {'status': h1.get('status'), 'body': h1.get('json', h1.get('text', h1.get('error')))}

        def db_state(lo, hi):
            rows = psql(f'select number, hash, consensus from blocks where number between {lo} and {hi} order by number')
            db = {}
            noncons = 0
            for ln in rows.splitlines():
                if '|' not in ln:
                    continue
                n, hsh, c = ln.split('|')
                if c == 't':
                    db[int(n)] = '0x' + hsh[2:] if hsh.startswith('\\x') else hsh
                else:
                    noncons += 1
            node = {n: rpc('eth_getBlockByNumber', hex(n), False)['hash'] for n in range(lo, hi + 1)}
            mismatch = [n for n in range(lo, hi + 1) if db.get(n) != node[n]]
            return {'consensus_hash_mismatch': len(mismatch), 'mismatch_min': min(mismatch) if mismatch else None,
                    'mismatch_max': max(mismatch) if mismatch else None, 'noncons_rows_in_range': noncons,
                    'missing_block_ranges': psql('select from_number, to_number from missing_block_ranges order by from_number desc limit 5'),
                    'noncons_total': psql('select count(*) from blocks where not consensus'),
                    'max_consensus_block': psql('select max(number) from blocks where consensus'),
                    'tt_noncons': psql('select count(*) from token_transfers where block_consensus = false'),
                    'tt_cons': psql('select count(*) from token_transfers where block_consensus')}

        # Blockscout のバックエンドを起動（公式 compose と同じ command：migrate してから start）
        envs = []
        for k, v in BS_ENV.items():
            envs += ['-e', f'{k}={v}']
        t_start = now()
        sh('docker', 'run', '-d', '--name', P + 'backend', '--network', NET, '-p', f'127.0.0.1:{API_PORT}:4000',
           # 1 回目は TIME_WAIT が 2.8 万を超えて eaddrnotavail になった（output-fail1/）。コンテナの中だけで広げる
           '--sysctl', 'net.ipv4.ip_local_port_range=1024 65000', '--sysctl', 'net.ipv4.tcp_tw_reuse=1',
           *envs, BS_IMAGE, 'sh', '-c',
           'bin/blockscout eval "Elixir.Explorer.ReleaseTasks.create_and_migrate()" && bin/blockscout start')
        say('backend started', t_start)
        while True:
            hh = health()
            b = api_balances()
            if b == truth():
                break
            if now() - t_start > 3600:
                raise RuntimeError('60 分で初期同期が終わらない')
            time.sleep(3)
        sync_s = round(now() - t_start, 1)
        # /api/health は Health.Monitor（既定 1 分ごと）が値を入れるまで 500 を返すので、200 になるまで待つ
        while health()['status'] != 200 and now() - t_start < 600:
            time.sleep(5)
        result['health_ok_seconds'] = round(now() - t_start, 1)
        result['start'] = {'sync_seconds': sync_s, 'health_ok_seconds': result['health_ok_seconds'], 'head': head(), 'truth': truth(), 'api': b,
                           'counters': api_counters(), 'node_transfer_logs': node_transfer_count(), 'health': health(),
                           'db': db_state(max(0, head() - 5), head())}
        say('start', json.dumps(result['start'], ensure_ascii=False))

        targets = {3: (carol, 7), 100: (dave, 50), 300: (dave, 50)}
        for depth in DEPTHS:
            to, val = targets.get(depth, (dave, 50))
            hb = head()
            before = {'head': hb, 'truth': truth(), 'api': api_balances(), 'health': health()}
            t_reorg = now()
            rpc('anvil_reorg', depth, [[tx(token, alice, to, val), 0]])
            rpc('evm_mine')
            lo = max(1, hb - depth - 2)
            samples = []
            limit = 180 if depth <= 3 else 1500
            matched_at = None
            fully_at = None
            last_mine = time.monotonic()
            k = 0
            while now() - t_reorg < limit:
                t = round(now() - t_reorg, 1)
                tr = truth()
                ab = api_balances()
                s = {'t': t, 'node_head': head(), 'truth': tr, 'api': ab}
                if k % 3 == 0 or ab == tr:
                    s['health'] = health()
                    s['counters'] = api_counters()
                    s['latest_transfers'] = api_latest_transfer()
                    s['db'] = db_state(lo, head())
                samples.append(s)
                if ab == tr and matched_at is None:
                    matched_at = t
                    say(depth, 'api balances match at', t, json.dumps(s.get('db'), ensure_ascii=False))
                if 'db' in s and s['db']['consensus_hash_mismatch'] == 0 and ab == tr:
                    fully_at = t
                    say(depth, 'api + db consensus match at', t)
                    break
                if k % 10 == 0:
                    say(depth, t, 'api', ab, 'truth', tr, 'db', json.dumps(s.get('db'), ensure_ascii=False)[:400] if 'db' in s else '')
                # 浅い reorg の後は 1 ブロックだけ。深い reorg の後は 5 秒ごとに 1 ブロック進める（チェーンが動き続ける状態）
                if depth > 3 and time.monotonic() - last_mine >= 5:
                    rpc('eth_sendTransaction', tx(token, alice, bob, 1))
                    rpc('evm_mine')
                    last_mine = time.monotonic()
                k += 1
                time.sleep(2)
            sc = {'depth': depth, 'to': names[to], 'value': val, 'before': before, 'samples': samples,
                  'api_match_seconds': matched_at, 'api_and_db_match_seconds': fully_at,
                  'after': {'head': head(), 'truth': truth(), 'api': api_balances(), 'counters': api_counters(),
                            'node_transfer_logs': node_transfer_count(), 'health': health(),
                            'readiness': get('/api/health/readiness'), 'db': db_state(lo, head())}}
            result['scenarios'].append(sc)
            say('scenario', depth, 'api_match', matched_at, 'full', fully_at, json.dumps(sc['after'], ensure_ascii=False)[:1500])
    finally:
        for c in ('backend', 'anvil', 'postgres'):
            r = sh('docker', 'logs', P + c, check=False)
            (OUT / f'{c}.log').write_text(r.stdout + r.stderr)
        result['versions'] = {
            'blockscout_image': BS_IMAGE,
            'blockscout_image_id': sh('docker', 'image', 'inspect', BS_IMAGE, '--format', '{{.Id}}', check=False).stdout.strip(),
            'blockscout_tag_commit': sh('git', '-C', str(HERE / 'src'), 'rev-parse', 'HEAD', check=False).stdout.strip(),
            'anvil_image': ANVIL_IMAGE, 'postgres_image': PG_IMAGE,
        }
        result['backend_env'] = {k: v for k, v in BS_ENV.items() if k != 'SECRET_KEY_BASE'}
        r = sh('docker', 'logs', P + 'backend', check=False)
        bl = r.stdout + r.stderr
        result['backend_log_counts'] = {k: bl.count(k) for k in ('URL is nil', 'eaddrnotavail', 'is unavailable', 'lost consensus', '"severity":"error"')}
        (OUT / 'results.json').write_text(json.dumps(result, ensure_ascii=False, indent=1))
        log.close()
        if not os.environ.get('KEEP'):
            cleanup()


if __name__ == '__main__':
    main()
