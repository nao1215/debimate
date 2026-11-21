"""Graph Node に reorg を当てる実験。ローカルの Anvil（Docker）だけを使う。

- 既定の ETHEREUM_REORG_THRESHOLD（250 ブロック）の内側（3 ブロック）と外側（300 ブロック）で、
  subgraph の Balance の表とノードの balanceOf を比べる。
- 公開ネットワーク・実資産・本物の秘密鍵は使わない。アカウントは Anvil のテスト用。
- コンテナは indexer-note-graphnode-*。ポートは 127.0.0.1 だけに出す。

実行: SOLC=... python3 drive.py   （subgraph/ で npm install・graph build 済みであること）
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
LAB = Path(os.environ.get('LAB', Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(LAB))
from keccak import keccak256  # noqa: E402

SOLC = os.environ.get('SOLC', 'solc')
PRUNE = os.environ.get('PRUNE')  # 例: 260。indexerHints.prune に入れる
OUT = HERE / (os.environ.get('OUT') or 'output')
SUB = HERE / 'subgraph'
NET = 'indexer-note-graphnode-net'
P = 'indexer-note-graphnode-'
ANVIL_PORT, PG_PORT, IPFS_PORT = 18801, 15441, 15051
QUERY, ADMIN, INDEX, METRICS = 18021, 18020, 18030, 18040
GN_IMAGE = 'graphprotocol/graph-node:v0.45.0'
ANVIL_IMAGE = 'ghcr.io/foundry-rs/foundry:v1.7.1'
PG_IMAGE = 'postgres:16-alpine'
IPFS_IMAGE = 'ipfs/kubo:v0.39.0'
NAME = 'indexer-note/token'
HEAD_TARGET = int(os.environ.get('HEAD_TARGET', '360'))  # 300 ブロックの reorg ができるだけの長さ


def sh(*a, check=True, **kw):
    return subprocess.run(list(a), check=check, text=True, capture_output=True, **kw)


def post(url, obj, timeout=5):
    req = urllib.request.Request(url, json.dumps(obj).encode(), {'Content-Type': 'application/json'})
    return json.loads(urllib.request.urlopen(req, timeout=timeout).read())


def rpc(method, *params):
    res = post(f'http://127.0.0.1:{ANVIL_PORT}', {'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': list(params)}, 30)
    if 'error' in res:
        raise RuntimeError(res['error'])
    return res['result']


def word(v):
    return bytes.fromhex(v[2:]).rjust(32, b'\0') if isinstance(v, str) else v.to_bytes(32, 'big')


def calldata(sig, *args):
    return '0x' + (keccak256(sig.encode())[:4] + b''.join(word(a) for a in args)).hex()


def tx(token, sender, to, value):
    return {'from': sender, 'to': token, 'data': calldata('transfer(address,uint256)', to, value), 'gas': hex(100_000)}


def gql(q):
    return post(f'http://127.0.0.1:{QUERY}/subgraphs/name/{NAME}', {'query': q}, 5)


STATUS_Q = ('{ indexingStatuses { subgraph synced health entityCount fatalError { message deterministic block { number hash } } '
            'nonFatalErrors { message } chains { network chainHeadBlock { number hash } latestBlock { number hash } } } }')


def index_status():
    try:
        r = post(f'http://127.0.0.1:{INDEX}/graphql', {'query': STATUS_Q}, 5)
        s = r['data']['indexingStatuses']
        return s[0] if s else None
    except Exception as e:  # noqa: BLE001
        return f'{type(e).__name__}: {e}'


def metrics():
    try:
        text = urllib.request.urlopen(f'http://127.0.0.1:{METRICS}/metrics', timeout=5).read().decode()
    except Exception as e:  # noqa: BLE001
        return f'{type(e).__name__}'
    keep = ('deployment_head', 'ethereum_chain_head_number', 'deployment_failed', 'deployment_reverted_blocks')
    return [ln for ln in text.splitlines() if ln.startswith(keep)]


def cleanup():
    names = sh('docker', 'ps', '-a', '--filter', f'name=^{P}', '--format', '{{.Names}}', check=False).stdout.split()
    if names:
        sh('docker', 'rm', '-f', *names, check=False)
    sh('docker', 'network', 'rm', NET, check=False)


def main():
    OUT.mkdir(exist_ok=True)
    cleanup()
    sh('docker', 'network', 'create', NET)
    # Anvil（公式の foundry イメージ）。コンテナの中では 0.0.0.0、ホストには 127.0.0.1 だけ
    sh('docker', 'run', '-d', '--name', P + 'anvil', '--network', NET, '--network-alias', 'anvil',
       '-p', f'127.0.0.1:{ANVIL_PORT}:8545', ANVIL_IMAGE,
       'anvil --host 0.0.0.0 --port 8545 --chain-id 31337 --hardfork cancun --timestamp 1700000000 --accounts 4 --no-mining')
    sh('docker', 'run', '-d', '--name', P + 'postgres', '--network', NET, '--network-alias', 'postgres',
       '-p', f'127.0.0.1:{PG_PORT}:5432', '-e', 'POSTGRES_USER=graph-node', '-e', 'POSTGRES_PASSWORD=let-me-in',
       '-e', 'POSTGRES_DB=graph-node', '-e', 'POSTGRES_INITDB_ARGS=-E UTF8 --locale=C', PG_IMAGE,
       'postgres', '-cshared_preload_libraries=pg_stat_statements', '-cmax_connections=200')
    sh('docker', 'run', '-d', '--name', P + 'ipfs', '--network', NET, '--network-alias', 'ipfs',
       '-p', f'127.0.0.1:{IPFS_PORT}:5001', IPFS_IMAGE)

    result = {'scenarios': [], 'prune': PRUNE, 'head_target': HEAD_TARGET}
    t0 = time.monotonic()

    def now():
        return round(time.monotonic() - t0, 2)

    try:
        for _ in range(200):
            try:
                accounts = [a.lower() for a in rpc('eth_accounts')]
                break
            except Exception:  # noqa: BLE001
                time.sleep(0.2)
        alice, bob, carol, dave = accounts
        names = {alice: 'alice', bob: 'bob', carol: 'carol', dave: 'dave'}
        rpc('anvil_setBlockTimestampInterval', 12)
        code = next(iter(json.loads(subprocess.check_output(
            [SOLC, '--evm-version', 'cancun', '--combined-json', 'bin', str(LAB / 'Token.sol')], text=True))['contracts'].values()))['bin']
        h = rpc('eth_sendTransaction', {'from': alice, 'data': '0x' + code + word(1000).hex(), 'gas': hex(2_000_000)})
        rpc('evm_mine')
        token = rpc('eth_getTransactionReceipt', h)['contractAddress']
        assert token.lower() == '0x5fbdb2315678afecb367f032d93f642f64180aa3', token
        # block 2〜HEAD_TARGET: 毎ブロック alice→bob に 1
        for _ in range(HEAD_TARGET - 1):
            rpc('eth_sendTransaction', tx(token, alice, bob, 1))
            rpc('evm_mine')

        def head():
            return int(rpc('eth_blockNumber'), 16)

        def truth():
            return {names[a]: int(rpc('eth_call', {'to': token, 'data': calldata('balanceOf(address)', a)}, 'latest'), 16)
                    for a in accounts}

        def view():
            try:
                r = gql('{ balances(first: 100) { id amount } transfers(first: 1000) { id } '
                        '_meta { block { number hash } hasIndexingErrors } }')
            except Exception as e:  # noqa: BLE001
                return {'error': f'{type(e).__name__}'}
            if 'errors' in r and not r.get('data'):
                return {'error': r['errors'][0]['message'][:200]}
            d = r['data']
            b = {x['id'].lower(): int(x['amount']) for x in d['balances']}
            meta = d['_meta']['block']
            n = meta['number']
            node_hash = rpc('eth_getBlockByNumber', hex(n), False)['hash']
            return {'balances': {names[a]: b.get(a, 0) for a in accounts}, 'transfers': len(d['transfers']),
                    'meta_block': n, 'meta_hash_matches_node': meta['hash'] == node_hash,
                    'hasIndexingErrors': d['_meta']['hasIndexingErrors']}

        # graph-node を起動（チェーン名 mainnet は graph-cli が知っている名前にするため。中身は Anvil）
        sh('docker', 'run', '-d', '--name', P + 'node', '--network', NET,
           '-p', f'127.0.0.1:{QUERY}:8000', '-p', f'127.0.0.1:{ADMIN}:8020',
           '-p', f'127.0.0.1:{INDEX}:8030', '-p', f'127.0.0.1:{METRICS}:8040',
           '-e', 'postgres_host=postgres', '-e', 'postgres_user=graph-node', '-e', 'postgres_pass=let-me-in',
           '-e', 'postgres_db=graph-node', '-e', 'ipfs=ipfs:5001', '-e', 'ethereum=mainnet:http://anvil:8545',
           '-e', 'GRAPH_LOG=info', GN_IMAGE)
        for _ in range(300):
            try:
                post(f'http://127.0.0.1:{ADMIN}', {'jsonrpc': '2.0', 'id': 1, 'method': 'subgraph_create', 'params': {'name': NAME}}, 3)
                break
            except Exception:  # noqa: BLE001
                time.sleep(1)
        else:
            raise RuntimeError('graph-node の admin に届かない')
        manifest = 'subgraph.yaml'
        if PRUNE:
            manifest = 'subgraph-prune.yaml'
            text = (SUB / 'subgraph.yaml').read_text().replace('schema:\n', f'indexerHints:\n  prune: {PRUNE}\nschema:\n', 1)
            (SUB / manifest).write_text(text)
        dep = subprocess.run(['npx', 'graph', 'deploy', NAME, manifest, '--node', f'http://127.0.0.1:{ADMIN}',
                              '--ipfs', f'http://127.0.0.1:{IPFS_PORT}', '--version-label', 'v1'],
                             cwd=SUB, text=True, capture_output=True)
        (OUT / 'deploy.txt').write_text(dep.stdout + dep.stderr)
        if dep.returncode != 0:
            raise RuntimeError('graph deploy に失敗（output/deploy.txt）')
        t_dep = now()
        for _ in range(600):
            v = view()
            if v.get('balances') == truth():
                break
            time.sleep(0.5)
        result['start'] = {'head': head(), 'truth': truth(), 'graph': view(), 'status': index_status(),
                           'sync_seconds': round(now() - t_dep, 1)}
        print('start', result['start'])

        def wait_match(limit=120):
            for _ in range(int(limit / 0.5)):
                v = view()
                if v.get('balances') == truth() and v.get('meta_block') == head():
                    return True
                time.sleep(0.5)
            return False

        def scenario(label, depth, txs, mine_after):
            wait_match()
            before = {'head': head(), 'truth': truth(), 'graph': view(), 'status': index_status()}
            t_reorg = now()
            rpc('anvil_reorg', depth, txs)
            samples = []
            # 高さが変わらないまま 6 秒待つ
            for _ in range(12):
                samples.append({'t': round(now() - t_reorg, 2), 'graph': view()})
                time.sleep(0.5)
            for _ in range(mine_after):
                rpc('evm_mine')
            for _ in range(40):
                samples.append({'t': round(now() - t_reorg, 2), 'graph': view(), 'after_mine': True})
                time.sleep(0.5)
            s = {'label': label, 'depth': depth, 'reorg_threshold': 250, 'before': before,
                 'truth_after': truth(), 'head_after': head(), 'samples': samples,
                 'status': index_status(), 'metrics': metrics()}
            s['first_match_seconds'] = next((x['t'] for x in samples if x['graph'].get('balances') == s['truth_after']), None)
            result['scenarios'].append(s)
            print(label, 'truth', s['truth_after'], 'last', samples[-1]['graph'], 'first match', s['first_match_seconds'],
                  'status', s['status'])

        # 窓の内側: 直近 3 ブロックを alice→carol 7 の 1 ブロック + 空 2 ブロックに置き換える
        scenario('inside', 3, [[tx(token, alice, carol, 7), 0]], 1)
        # 窓の外側: 直近 300 ブロックを alice→dave 50 の 1 ブロック + 空 299 ブロックに置き換える
        scenario('outside', 300, [[tx(token, alice, dave, 50), 0]], 1)
        watch = []
        t_w = now()
        for _ in range(12):
            time.sleep(5)
            st = index_status()
            watch.append({'t': round(now() - t_w, 1), 'node_head': head(), 'graph': view(), 'truth': truth(),
                          'status': st, 'metrics': metrics()})
            rpc('evm_mine')
        result['after_outside'] = watch
        print('after outside', json.dumps(watch[-1], ensure_ascii=False))
    finally:
        for c in ('node', 'anvil', 'ipfs', 'postgres'):
            r = sh('docker', 'logs', P + c, check=False)
            (OUT / f'{c}.log').write_text(r.stdout + r.stderr)
        result['versions'] = {
            'graph_node_image': sh('docker', 'image', 'inspect', GN_IMAGE, '--format', '{{index .RepoDigests 0}}', check=False).stdout.strip(),
            'anvil_image': ANVIL_IMAGE, 'postgres_image': PG_IMAGE, 'ipfs_image': IPFS_IMAGE,
            'graph_cli': json.load(open(SUB / 'node_modules/@graphprotocol/graph-cli/package.json'))['version'],
            'graph_ts': json.load(open(SUB / 'node_modules/@graphprotocol/graph-ts/package.json'))['version'],
        }
        (OUT / 'results.json').write_text(json.dumps(result, ensure_ascii=False, indent=1))
        if not os.environ.get('KEEP'):
            cleanup()


if __name__ == '__main__':
    main()
