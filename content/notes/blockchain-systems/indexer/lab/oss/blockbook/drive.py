"""Trezor Blockbook v0.6.0 に reorg を当てる実験（bitcoind 32.1 の regtest）。

- 公開ネットワーク・実資産・本物の鍵は使わない。127.0.0.1 だけで待ち受ける。
- alice のアドレスへ 1 BTC ずつ送るブロックを並べ、Blockbook の /api/v2/address/<addr> を bitcoind の値と比べる。
- 窓の内側: 直近 3 ブロックを invalidateblock で外し、同じ入力を carol へ送る二重支払いのブロックに置き換える。
- 窓の外側: OUTSIDE_DEPTH（既定 320）ブロックを外し、同じ入力を dave へ送るブロックに置き換える
  （Blockbook の bitcoin_regtest の block_addresses_to_keep = 300 を超える）。
  その後 60 秒、5 秒ごとに 1 ブロック進めながら 1 秒ごとに記録し、最後に Blockbook を同じ DB で起動し直して 30 秒見る。

実行: python3 drive.py   （bin/blockbook がビルド済みであること）
"""
import base64
import json
import os
import shutil
import signal
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / os.environ.get('OUT', 'output')
RUN = HERE / os.environ.get('RUN', 'run')
SRC = HERE / 'src-v0.6.0'  # static/ と templates を読むので cwd にする
BITCOIND = HERE.parent / 'bitcoin/dl/core/bitcoin-32.1/bin/bitcoind'
BLOCKBOOK = HERE / 'bin/blockbook'

RPC_PORT, P2P_PORT, ZMQ_PORT = 18941, 18942, 18943
BB_PUBLIC, BB_INTERNAL = 18951, 18952
AUTH = base64.b64encode(b'note:note').decode()
INSIDE_DEPTH = int(os.environ.get('INSIDE_DEPTH', 3))
OUTSIDE_DEPTH = int(os.environ.get('OUTSIDE_DEPTH', 320))
# PAUSE=1 なら reorg を組む間 Blockbook を SIGSTOP し、組み終えてから SIGCONT する（途中の鎖を見せない）
PAUSE = os.environ.get('PAUSE') == '1'

LOG = []


def say(*a):
    line = f'[{time.strftime("%H:%M:%S")}] ' + ' '.join(str(x) for x in a)
    print(line, flush=True)
    LOG.append(line)


def rpc(method, *params, wallet=None):
    url = f'http://127.0.0.1:{RPC_PORT}/' + (f'wallet/{wallet}' if wallet else '')
    body = json.dumps({'jsonrpc': '1.0', 'id': 1, 'method': method, 'params': list(params)}).encode()
    req = urllib.request.Request(url, body, {'Content-Type': 'application/json', 'Authorization': 'Basic ' + AUTH})
    try:
        res = json.loads(urllib.request.urlopen(req, timeout=120).read())
    except urllib.error.HTTPError as e:
        res = json.loads(e.read())
    if res.get('error'):
        raise RuntimeError(f'{method}: {res["error"]}')
    return res['result']


def sats(btc):
    return int(round(float(btc) * 1e8))


def node_view(addr, txids):
    scan = rpc('scantxoutset', 'start', [f'addr({addr})'])
    confirmed = []
    for t in txids:
        try:
            r = rpc('getrawtransaction', t, 1)
        except RuntimeError:
            continue
        if r.get('confirmations', 0) > 0:
            confirmed.append(t)
    return {'height': rpc('getblockcount'), 'balance': sats(scan['total_amount']), 'history': sorted(confirmed)}


def http_get(url, timeout=5):
    try:
        r = urllib.request.urlopen(url, timeout=timeout)
        return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def bb_view(addr):
    base = f'http://127.0.0.1:{BB_PUBLIC}'
    try:
        _, st = http_get(f'{base}/api/')
        st = json.loads(st)
        code, a = http_get(f'{base}/api/v2/address/{addr}?details=txids&pageSize=1000')
        a = json.loads(a)
        if code != 200:
            return {'up': True, 'height': st['blockbook'].get('bestHeight'), 'address_error': a, 'code': code}
        return {'up': True, 'height': st['blockbook'].get('bestHeight'),
                'balance': int(a['balance']), 'unconfirmed': int(a.get('unconfirmedBalance', '0')),
                'unconfirmedTxs': a.get('unconfirmedTxs', 0),
                'txs': a.get('txs'), 'history': sorted(a.get('txids') or [])}
    except Exception as e:  # noqa: BLE001
        return {'up': False, 'error': f'{type(e).__name__}: {e}'}


def bb_status():
    """/api の blockbook 節（inSync・bestHeight など）と backend.blocks、内部口の /metrics の要点。"""
    h = {}
    try:
        code, body = http_get(f'http://127.0.0.1:{BB_PUBLIC}/api/')
        st = json.loads(body)
        b = st.get('blockbook', {})
        h['api'] = {'status': code, **{k: b.get(k) for k in ('bestHeight', 'inSync', 'inSyncMempool', 'syncMode',
                                                              'lastBlockTime', 'initialSync', 'currentFiatRatesTime')},
                    'backend_blocks': st.get('backend', {}).get('blocks'),
                    'backend_bestBlockHash': st.get('backend', {}).get('bestBlockHash')}
    except Exception as e:  # noqa: BLE001
        h['api'] = {'status': f'{type(e).__name__}: {e}'}
    try:
        code, text = http_get(f'http://127.0.0.1:{BB_INTERNAL}/metrics')
        keys = ('blockbook_best_height', 'blockbook_backend_best_height', 'blockbook_synchronized',
                'blockbook_index_reorg_events', 'blockbook_index_resync_errors', 'blockbook_tip_age_seconds', 'blockbook_index_resync_duration_count')
        h['metrics'] = {'status': code, 'lines': [ln for ln in text.splitlines()
                                                  if not ln.startswith('#') and any(ln.startswith(k) for k in keys)]}
    except Exception as e:  # noqa: BLE001
        h['metrics'] = {'status': f'{type(e).__name__}: {e}'}
    return h


PROCS = {}


def start(name, args, cwd=None):
    log = open(OUT / f'{name}.log', 'wb')
    PROCS[name] = subprocess.Popen(args, stdout=log, stderr=subprocess.STDOUT, cwd=cwd)
    say('start', name, 'pid', PROCS[name].pid)


def alive():
    return {n: (p.poll() is None, p.returncode) for n, p in PROCS.items()}


def stop(name):
    p = PROCS[name]
    if p.poll() is None:
        p.send_signal(signal.SIGINT)
        try:
            p.wait(60)
        except subprocess.TimeoutExpired:
            p.kill()


def stop_all():
    for n in reversed(list(PROCS)):
        stop(n)


def start_blockbook(name):
    cfg = RUN / 'blockchaincfg.json'
    cfg.write_text(json.dumps({
        # bitcoin_regtest.json の値。手数料推定の外部 URL（mempool.space）は入れない。
        'coin_name': 'Regtest', 'coin_shortcut': 'rBTC', 'coin_label': 'Bitcoin Regtest',
        'rpc_url': f'http://127.0.0.1:{RPC_PORT}', 'rpc_user': 'note', 'rpc_pass': 'note', 'rpc_timeout': 25,
        'parse': True, 'message_queue_binding': f'tcp://127.0.0.1:{ZMQ_PORT}',
        'subversion': '', 'address_format': '',
        'xpub_magic': 70617039, 'xpub_magic_segwit_p2sh': 71979618, 'xpub_magic_segwit_native': 73342198,
        'slip44': 1, 'mempool_workers': 8, 'mempool_sub_workers': 2,
        'block_addresses_to_keep': int(os.environ.get('KEEP', 300)),
    }, indent=1))
    start(name, [str(BLOCKBOOK), f'-blockchaincfg={cfg}', f'-datadir={RUN / "bbdb"}', '-sync',
                 f'-internal=127.0.0.1:{BB_INTERNAL}', f'-public=127.0.0.1:{BB_PUBLIC}',
                 '-logtostderr', '-explorer='], cwd=SRC)


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    if RUN.exists():
        shutil.rmtree(RUN)
    (RUN / 'btc').mkdir(parents=True)
    start('bitcoind', [str(BITCOIND), f'-datadir={RUN / "btc"}', '-regtest', '-server', '-txindex',
                       '-fallbackfee=0.0002', '-rpcuser=note', '-rpcpassword=note', '-rpcbind=127.0.0.1',
                       '-rpcallowip=127.0.0.1', f'-rpcport={RPC_PORT}', f'-bind=127.0.0.1:{P2P_PORT}',
                       '-listen=1', '-listenonion=0', '-rpcworkqueue=1100', '-deprecatedrpc=warnings',
                       f'-zmqpubhashtx=tcp://127.0.0.1:{ZMQ_PORT}', f'-zmqpubhashblock=tcp://127.0.0.1:{ZMQ_PORT}',
                       '-printtoconsole'])
    for _ in range(60):
        try:
            rpc('getblockcount')
            break
        except Exception:  # noqa: BLE001
            time.sleep(0.5)
    results = {'versions': {'bitcoind': rpc('getnetworkinfo')['subversion']},
               'params': {'inside_depth': INSIDE_DEPTH, 'outside_depth': OUTSIDE_DEPTH,
                          'block_addresses_to_keep': int(os.environ.get('KEEP', 300))}}
    rpc('createwallet', 'miner')
    rpc('createwallet', 'others')
    miner = rpc('getnewaddress', '', 'bech32', wallet='miner')
    alice, carol, dave = (rpc('getnewaddress', n, 'bech32', wallet='others') for n in ('alice', 'carol', 'dave'))
    rpc('generatetoaddress', 150, miner)
    coins = iter(sorted((u for u in rpc('listunspent', 1, 9999999, wallet='miner') if u['confirmations'] >= 120),
                        key=lambda u: -u['confirmations']))

    def raw(coin, to, amount, fee=0.0001):
        out = {to: amount, miner: round(coin['amount'] - amount - fee, 8)}
        h = rpc('createrawtransaction', [{'txid': coin['txid'], 'vout': coin['vout']}], out)
        signed = rpc('signrawtransactionwithwallet', h, wallet='miner')
        assert signed['complete']
        return signed['hex'], rpc('decoderawtransaction', signed['hex'])['txid']

    def block(txhexes=()):
        return rpc('generateblock', miner, list(txhexes))['hash']

    alice_txids = []
    spent = {}

    def pay(to, amount=1.0):
        c = next(coins)
        hx, txid = raw(c, to, amount)
        spent[txid] = c
        if to == alice:
            alice_txids.append(txid)
        return hx

    for _ in range(5):
        block([pay(alice)])
    results['addresses'] = {'alice': alice, 'carol': carol, 'dave': dave}

    start_blockbook('blockbook')

    def views():
        return {'node': node_view(alice, alice_txids), 'blockbook': bb_view(alice)}

    def match(v):
        s, n = v['blockbook'], v['node']
        return bool(s.get('up') and s.get('height') == n['height'] and s.get('balance') == n['balance']
                    and s.get('history') == n['history'] and not s.get('unconfirmedTxs'))

    def wait_sync(label, limit=600):
        t0 = time.time()
        snaps = []
        first = None
        while time.time() - t0 < limit:
            v = views()
            snaps.append({'t': round(time.time() - t0, 1), **v})
            if match(v):
                first = snaps[-1]['t']
                break
            time.sleep(0.5)
        say(label, 'first match (s):', first, 'node', v['node']['height'], v['node']['balance'],
            'bb', {k: v['blockbook'].get(k) for k in ('up', 'height', 'balance', 'unconfirmedTxs', 'error')})
        return first, snaps

    results['initial_sync'], _ = wait_sync('initial')
    results['initial_view'] = views()
    results['initial_status'] = bb_status()

    # 窓の内側
    tip = rpc('getblockcount')
    gone = [rpc('getblockhash', h) for h in range(tip - INSIDE_DEPTH + 1, tip + 1)]
    gone_txs = [t for h in gone for t in rpc('getblock', h)['tx'][1:]]
    say('inside: invalidate', INSIDE_DEPTH, 'blocks from height', tip - INSIDE_DEPTH + 1, 'txs', gone_txs)
    rpc('invalidateblock', gone[0])
    block([raw(spent[t], carol, 7.0, fee=0.0002)[0] for t in gone_txs])
    for _ in range(INSIDE_DEPTH - 1):
        block()
    block()
    first, snaps = wait_sync('inside', limit=120)
    results['inside'] = {'depth': INSIDE_DEPTH, 'first_match_s': first, 'node_after': snaps[-1]['node'],
                         'bb_after': snaps[-1]['blockbook'], 'trace': snaps[:6] + snaps[-1:],
                         'status': bb_status(), 'alive': alive(), 'mempool_after': rpc('getrawmempool'),
                         'carol': {'node': sats(rpc('scantxoutset', 'start', [f'addr({carol})'])['total_amount']),
                                   'blockbook': bb_view(carol)}}

    # 窓の外側。外れる最古のブロック・真ん中・最新に alice への支払い。
    D = OUTSIDE_DEPTH
    t_mine = time.time()
    for i in range(D):
        block([pay(alice)] if i in (0, D // 2, D - 1) else [])
    say('mined', D, 'blocks in', round(time.time() - t_mine, 1), 's')
    results['before_outside'], _ = wait_sync('before outside')
    results['before_outside_view'] = views()
    results['before_outside_status'] = bb_status()
    tip = rpc('getblockcount')
    base = tip - D + 1
    gone = [rpc('getblockhash', h) for h in range(base, tip + 1)]
    gone_txs = [t for h in gone for t in rpc('getblock', h)['tx'][1:]]
    say('outside: invalidate', D, 'blocks from height', base, 'txs', gone_txs, 'pause', PAUSE)
    if PAUSE:
        PROCS['blockbook'].send_signal(signal.SIGSTOP)
    rpc('invalidateblock', gone[0])
    block([raw(spent[t], dave, 10.0, fee=0.0002)[0] for t in gone_txs])
    for _ in range(D):
        block()
    say('outside: new tip', rpc('getblockcount'))
    if PAUSE:
        PROCS['blockbook'].send_signal(signal.SIGCONT)
    trace = []
    t0 = time.time()
    next_mine = t0 + 5
    while time.time() - t0 < 60:
        v = views()
        trace.append({'t': round(time.time() - t0, 1), **v, 'status': bb_status(), 'alive': alive()})
        if time.time() >= next_mine:
            block()
            next_mine += 5
        time.sleep(1)
    results['outside'] = {'depth': D, 'base_height': base, 'trace': trace, 'final': trace[-1],
                          'first_match_s': next((x['t'] for x in trace if match(x)), None),
                          'dave': {'node': sats(rpc('scantxoutset', 'start', [f'addr({dave})'])['total_amount']),
                                   'blockbook': bb_view(dave)}}
    say('outside final', json.dumps(trace[-1], default=str)[:2500])
    say('outside first match', results['outside']['first_match_s'])

    # 掘らずに 30 秒。/api の inSync と、Blockbook が持つ高さごとのブロック（block-index）を見る。
    def block_index(h):
        code, body = http_get(f'http://127.0.0.1:{BB_PUBLIC}/api/v2/block-index/{h}')
        try:
            return code, json.loads(body)
        except ValueError:
            return code, body[:200]
    quiet = []
    t0 = time.time()
    while time.time() - t0 < 30:
        quiet.append({'t': round(time.time() - t0, 1), 'node_height': rpc('getblockcount'),
                      'blockbook': bb_view(alice), 'status': bb_status()})
        time.sleep(1)
    tipnow = rpc('getblockcount')
    probe = sorted({base - 1, base, base + D // 2, tip - 11, tip - 10, tip, tipnow})
    results['quiet'] = {'trace': quiet,
                        'block_index': {h: {'blockbook': block_index(h),
                                            'node': rpc('getblockhash', h) if h <= tipnow else None,
                                            'orphan': gone[h - base] if base <= h <= tip else None} for h in probe}}
    say('quiet inSync', [(q['t'], q['status']['api'].get('inSync')) for q in quiet])
    say('block_index', json.dumps(results['quiet']['block_index'])[:2500])

    # 同じ DB で起動し直す
    stop('blockbook')
    start_blockbook('blockbook-restart')
    rt = []
    t0 = time.time()
    while time.time() - t0 < 30:
        v = views()
        rt.append({'t': round(time.time() - t0, 1), **v, 'status': bb_status(),
                   'alive': PROCS['blockbook-restart'].poll()})
        time.sleep(2)
    results['restart'] = {'trace': rt, 'first_match_s': next((x['t'] for x in rt if match(x)), None)}
    say('restart last', json.dumps(rt[-1], default=str)[:1500])
    stop_all()
    (OUT / 'results.json').write_text(json.dumps(results, indent=1, default=str))
    (OUT / 'drive.txt').write_text('\n'.join(LOG) + '\n')


if __name__ == '__main__':
    try:
        main()
    finally:
        stop_all()
