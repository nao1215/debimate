"""Bitcoin の Electrum サーバー 3 つ（electrs、Blockstream electrs、Fulcrum）に reorg を当てる実験。

- bitcoind（Bitcoin Core 32.1、regtest）だけを使う。公開ネットワーク・実資産・本物の鍵は使わない。
- alice のアドレスへ 1 BTC ずつ送るブロックを並べ、各サーバーの残高・履歴を bitcoind の値と比べる。
- 窓の内側: 直近 3 ブロックを invalidateblock で外し、同じ入力を carol へ送る二重支払いのブロックに置き換える。
- 窓の外側: 直近 120 ブロックを外し、同じ入力を dave へ送るブロックに置き換える（Fulcrum の max_reorg 既定 100 を超える）。
  その後 60 秒、5 秒ごとに 1 ブロック進めながら記録する。

実行: python3 drive.py  （dl/ に bitcoind と Fulcrum、target-*/release に electrs 2 種があること）
"""
import base64
import hashlib
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
OUT = HERE / os.environ.get('OUT', 'output')
FULCRUM_MAX_REORG = os.environ.get('FULCRUM_MAX_REORG')  # 未設定なら既定（100）
RUN = HERE / 'run'  # データディレクトリ（毎回作り直す）
BITCOIND = HERE / 'dl/core/bitcoin-32.1/bin/bitcoind'
FULCRUM = HERE / 'dl/fulcrum/Fulcrum-2.1.4-x86_64-linux/Fulcrum'
ELECTRS = HERE / 'target-electrs/release/electrs'
BSELECTRS = HERE / 'target-bs/release/electrs'

RPC_PORT, P2P_PORT = 18901, 18902
EL_PORT, EL_MON = 18911, 18912
BS_HTTP, BS_MON = 18921, 18922
FU_TCP, FU_STATS = 18931, 18932
AUTH = base64.b64encode(b'note:note').decode()

INSIDE_DEPTH = int(os.environ.get('INSIDE_DEPTH', 3))
OUTSIDE_DEPTH = int(os.environ.get('OUTSIDE_DEPTH', 120))

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


# ---------- ノードの値 ----------

def node_view(addr, txids):
    """bitcoind の値: UTXO 集合の残高（scantxoutset）と、送った取引のうち今の鎖に載っているもの。"""
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


# ---------- Electrum プロトコル ----------

def scripthash(addr):
    spk = bytes.fromhex(rpc('getaddressinfo', addr, wallet='others')['scriptPubKey'])
    return hashlib.sha256(spk).digest()[::-1].hex()


def electrum(port, calls, timeout=3):
    s = socket.create_connection(('127.0.0.1', port), timeout=timeout)
    f = s.makefile('rwb')
    out = []
    try:
        for i, (m, p) in enumerate([('server.version', ['drive', '1.4'])] + calls):
            f.write((json.dumps({'jsonrpc': '2.0', 'id': i, 'method': m, 'params': p}) + '\n').encode())
            f.flush()
            while True:
                r = json.loads(f.readline())
                if r.get('id') == i:
                    break
            out.append(r.get('result', {'error': r.get('error')}))
    finally:
        s.close()
    return out[1:]


def electrum_view(port, sh):
    try:
        tip, bal, hist = electrum(port, [('blockchain.headers.subscribe', []),
                                         ('blockchain.scripthash.get_balance', [sh]),
                                         ('blockchain.scripthash.get_history', [sh])])
        conf = sorted(h['tx_hash'] for h in hist if h.get('height', 0) > 0) if isinstance(hist, list) else hist
        unconf = sorted(h['tx_hash'] for h in hist if h.get('height', 0) <= 0) if isinstance(hist, list) else []
        return {'up': True, 'height': tip.get('height') if isinstance(tip, dict) else tip,
                'balance': bal.get('confirmed') if isinstance(bal, dict) else bal,
                'unconfirmed': bal.get('unconfirmed') if isinstance(bal, dict) else None,
                'history': conf, 'mempool': unconf}
    except Exception as e:  # noqa: BLE001
        return {'up': False, 'error': f'{type(e).__name__}: {e}'}


def http_get(url, timeout=3):
    return urllib.request.urlopen(url, timeout=timeout).read().decode()


def esplora_view(addr):
    base = f'http://127.0.0.1:{BS_HTTP}'
    try:
        a = json.loads(http_get(f'{base}/address/{addr}'))
        txs = json.loads(http_get(f'{base}/address/{addr}/txs'))
        cs = a['chain_stats']
        return {'up': True, 'height': int(http_get(f'{base}/blocks/tip/height')),
                'balance': cs['funded_txo_sum'] - cs['spent_txo_sum'],
                'unconfirmed': a['mempool_stats']['funded_txo_sum'] - a['mempool_stats']['spent_txo_sum'],
                'history': sorted(t['txid'] for t in txs if t['status']['confirmed']),
                'mempool': sorted(t['txid'] for t in txs if not t['status']['confirmed'])}
    except Exception as e:  # noqa: BLE001
        return {'up': False, 'error': f'{type(e).__name__}: {e}'}


def esplora_prefix(prefix):
    try:
        return json.loads(http_get(f'http://127.0.0.1:{BS_HTTP}/address-prefix/{prefix}'))
    except Exception as e:  # noqa: BLE001
        return f'{type(e).__name__}: {e}'


def health():
    """各サーバーの監視口。electrs 系は Prometheus の /metrics、Fulcrum は stats の /stats。"""
    h = {}
    for name, url, keys in [('electrs', f'http://127.0.0.1:{EL_MON}/metrics', ('tip_height', 'sync_height')),
                            ('bs-electrs', f'http://127.0.0.1:{BS_MON}/metrics',
                             ('tip_height', 'initial_sync_height', 'stale_cleanup_failing', 'electrs_main_loop_count'))]:
        try:
            text = http_get(url)
            h[name] = {'status': 200, 'lines': [ln for ln in text.splitlines()
                                                if not ln.startswith('#') and any(k in ln for k in keys)][:8]}
        except Exception as e:  # noqa: BLE001
            h[name] = {'status': f'{type(e).__name__}: {e}'}
    try:
        st = json.loads(http_get(f'http://127.0.0.1:{FU_STATS}/stats'))
        ctl = st.get('Controller', {})
        h['fulcrum'] = {'status': 200, 'Controller': {k: ctl.get(k) for k in ('Header count', 'Chain', 'State', 'TxNum', 'UTXO set')}}
    except Exception as e:  # noqa: BLE001
        h['fulcrum'] = {'status': f'{type(e).__name__}: {e}'}
    return h


# ---------- 起動 ----------

PROCS = {}


def start(name, args, env=None):
    log = open(OUT / f'{name}.log', 'wb')
    PROCS[name] = subprocess.Popen(args, stdout=log, stderr=subprocess.STDOUT, env={**os.environ, **(env or {})})
    say('start', name, 'pid', PROCS[name].pid)


def alive():
    return {n: (p.poll() is None, p.returncode) for n, p in PROCS.items()}


def stop_all():
    for n, p in PROCS.items():
        if p.poll() is None:
            p.send_signal(signal.SIGINT)
    for n, p in PROCS.items():
        try:
            p.wait(30)
        except subprocess.TimeoutExpired:
            p.kill()


def start_servers(sh_list):
    (RUN / 'electrs').mkdir(parents=True, exist_ok=True)
    # auth はコマンド行で渡せない（パスワードの漏れを避けるため設定ファイル限定）
    (RUN / 'electrs.toml').write_text('auth = "note:note"\n')
    start('electrs', [str(ELECTRS), '--network', 'regtest', '--db-dir', str(RUN / 'electrs'),
                      '--daemon-dir', str(RUN / 'btc'), '--daemon-rpc-addr', f'127.0.0.1:{RPC_PORT}',
                      '--conf', str(RUN / 'electrs.toml'),
                      '--electrum-rpc-addr', f'127.0.0.1:{EL_PORT}', '--monitoring-addr', f'127.0.0.1:{EL_MON}',
                      '--log-filters', 'INFO'],
          # 既定では rayon が CPU 数（32）だけ REST の接続を開き、bitcoind の HTTP が詰まった。4 に絞る。
          env={'RAYON_NUM_THREADS': '4'})
    # Blockstream electrs は Electrum の口も必ず開く。割り当てが 2 つなので Electrum は OS が選ぶ一時ポート（:0）にする。
    start('bs-electrs', [str(BSELECTRS), '-vvv', '--network', 'regtest', '--db-dir', str(RUN / 'bs'),
                         '--daemon-dir', str(RUN / 'btc'), '--daemon-rpc-addr', f'127.0.0.1:{RPC_PORT}',
                         '--cookie', 'note:note', '--jsonrpc-import',
                         '--http-addr', f'127.0.0.1:{BS_HTTP}', '--monitoring-addr', f'127.0.0.1:{BS_MON}',
                         '--electrum-rpc-addr', '127.0.0.1:0', '--address-search'])
    (RUN / 'fulcrum').mkdir(parents=True, exist_ok=True)
    conf = RUN / 'fulcrum.conf'
    conf.write_text('\n'.join([
        f'datadir = {RUN / "fulcrum"}', f'bitcoind = 127.0.0.1:{RPC_PORT}', 'rpcuser = note', 'rpcpassword = note',
        f'tcp = 127.0.0.1:{FU_TCP}', f'stats = 127.0.0.1:{FU_STATS}', 'peering = false', 'announce = false',
        'polltime = 1'] + ([f'max_reorg = {FULCRUM_MAX_REORG}'] if FULCRUM_MAX_REORG else []) + ['']))
    start('fulcrum', [str(FULCRUM), str(conf)])


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    if RUN.exists():
        shutil.rmtree(RUN)
    (RUN / 'btc').mkdir(parents=True)
    start('bitcoind', [str(BITCOIND), f'-datadir={RUN / "btc"}', '-regtest', '-server', '-txindex', '-rest',
                       '-fallbackfee=0.0002', '-rpcuser=note', '-rpcpassword=note', '-rpcbind=127.0.0.1',
                       '-rpcallowip=127.0.0.1', f'-rpcport={RPC_PORT}', f'-bind=127.0.0.1:{P2P_PORT}',
                       '-listen=1', '-listenonion=0', '-rpcthreads=64', '-rpcworkqueue=1024', '-printtoconsole'])
    for _ in range(60):
        try:
            rpc('getblockcount')
            break
        except Exception:  # noqa: BLE001
            time.sleep(0.5)
    results = {'versions': {'bitcoind': rpc('getnetworkinfo')['subversion']}}
    rpc('createwallet', 'miner')
    rpc('createwallet', 'others')
    miner = rpc('getnewaddress', '', 'bech32', wallet='miner')
    alice, carol, dave, eve = (rpc('getnewaddress', n, 'bech32', wallet='others') for n in ('alice', 'carol', 'dave', 'eve'))
    rpc('generatetoaddress', 150, miner)
    # 入力に使う成熟した coinbase（高さ 1〜30。どちらの reorg でも外れない）
    coins = sorted((u for u in rpc('listunspent', 1, 9999999, wallet='miner') if u['confirmations'] >= 120),
                   key=lambda u: -u['confirmations'])
    coins = iter(coins)

    def raw(coin, to, amount, fee=0.0001):
        out = {to: amount, miner: round(coin['amount'] - amount - fee, 8)}
        h = rpc('createrawtransaction', [{'txid': coin['txid'], 'vout': coin['vout']}], out)
        signed = rpc('signrawtransactionwithwallet', h, wallet='miner')
        assert signed['complete']
        return signed['hex'], rpc('decoderawtransaction', signed['hex'])['txid']

    def block(txhexes=()):
        return rpc('generateblock', miner, list(txhexes))['hash']

    alice_txids = []
    spent = {}  # txid -> coin

    def pay(to, amount=1.0):
        c = next(coins)
        hx, txid = raw(c, to, amount)
        spent[txid] = c
        if to == alice:
            alice_txids.append(txid)
        return hx, txid

    # 1. alice へ 1 BTC ずつのブロックを 5 つ。最後のブロックには eve への支払いも入れる（前方一致の索引の確かめ用）。
    eve_tx = None
    for i in range(5):
        txs = [pay(alice)[0]]
        if i == 4:
            hx, eve_tx = pay(eve, 2.0)
            txs.append(hx)
        block(txs)
    sh = scripthash(alice)
    results['addresses'] = {'alice': alice, 'carol': carol, 'dave': dave, 'eve': eve, 'alice_scripthash': sh}

    start_servers([sh])

    def views():
        return {'node': node_view(alice, alice_txids),
                'electrs': electrum_view(EL_PORT, sh),
                'bs-electrs': esplora_view(alice),
                'fulcrum': electrum_view(FU_TCP, sh)}

    def match(v, name):
        s, n = v[name], v['node']
        return s.get('up') and s.get('height') == n['height'] and s.get('balance') == n['balance'] \
            and s.get('history') == n['history'] and not s.get('mempool')

    def wait_sync(label, limit=600):
        t0 = time.time()
        first = {}
        snaps = []
        while time.time() - t0 < limit:
            v = views()
            el = round(time.time() - t0, 1)
            snaps.append({'t': el, **v})
            for n in ('electrs', 'bs-electrs', 'fulcrum'):
                if n not in first and match(v, n):
                    first[n] = el
            if len(first) == 3:
                break
            time.sleep(0.5)
        say(label, 'first match (s):', first, 'node', v['node'])
        return first, snaps

    # 2. 初回の同期
    results['initial_sync'], _ = wait_sync('initial')
    results['initial_view'] = views()

    # 3. 窓の内側（3 ブロック）
    tip = rpc('getblockcount')
    gone = [rpc('getblockhash', h) for h in range(tip - INSIDE_DEPTH + 1, tip + 1)]
    gone_txs = [t for h in gone for t in rpc('getblock', h)['tx'][1:]]
    say('inside: invalidate', INSIDE_DEPTH, 'blocks from height', tip - INSIDE_DEPTH + 1, 'txs', gone_txs)
    rpc('invalidateblock', gone[0])
    ds = [raw(spent[t], carol, 7.0, fee=0.0002)[0] for t in gone_txs]
    block(ds)
    for _ in range(INSIDE_DEPTH - 1):
        block()
    block()  # その後 1 ブロック進める
    t_reorg = time.time()
    first, snaps = wait_sync('inside', limit=90)
    results['inside'] = {'depth': INSIDE_DEPTH, 'first_match_s': first, 'node_after': snaps[-1]['node'],
                         'trace': snaps[:6] + snaps[-1:], 'health': health(), 'alive': alive(),
                         'mempool_after': rpc('getrawmempool')}
    results['inside']['eve'] = {
        'node_utxo': sats(rpc('scantxoutset', 'start', [f'addr({eve})'])['total_amount']),
        'esplora_address': esplora_view(eve),
        'address_prefix_eve': esplora_prefix(eve[:10]),
        'address_prefix_carol': esplora_prefix(carol[:10])}
    say('inside eve check', results['inside']['eve'])

    # 4. 窓の外側（120 ブロック）。外れる最古のブロックに alice への支払い、真ん中と最新にも 1 つずつ。
    D = OUTSIDE_DEPTH
    for i in range(D):
        block([pay(alice)[0]] if i in (0, D // 2, D - 1) else [])
    results['before_outside'], _ = wait_sync('before outside')
    results['before_outside_view'] = views()
    tip = rpc('getblockcount')
    base = tip - D + 1
    gone = [rpc('getblockhash', h) for h in range(base, tip + 1)]
    gone_txs = [t for h in gone for t in rpc('getblock', h)['tx'][1:]]
    say('outside: invalidate', D, 'blocks from height', base, 'txs', gone_txs)
    rpc('invalidateblock', gone[0])
    ds = [raw(spent[t], dave, 10.0, fee=0.0002)[0] for t in gone_txs]
    block(ds)
    for _ in range(D):  # 元より 1 つ長い鎖にする
        block()
    say('outside: new tip', rpc('getblockcount'))
    trace = []
    t0 = time.time()
    next_mine = t0 + 5
    while time.time() - t0 < 60:
        v = views()
        trace.append({'t': round(time.time() - t0, 1), **v, 'health': health(), 'alive': alive()})
        if time.time() >= next_mine:
            block()
            next_mine += 5
        time.sleep(1)
    results['outside'] = {'depth': D, 'trace': trace, 'final': trace[-1],
                          'first_match_s': {n: next((x['t'] for x in trace if match(x, n)), None)
                                            for n in ('electrs', 'bs-electrs', 'fulcrum')}}
    say('outside final', json.dumps(trace[-1], default=str)[:2000])
    say('outside first match', results['outside']['first_match_s'])
    results['outside']['dave_prefix'] = esplora_prefix(dave[:10])
    # 落ちた Fulcrum を同じデータディレクトリで起動し直すとどうなるか
    if PROCS['fulcrum'].poll() is not None:
        start('fulcrum-restart', [str(FULCRUM), str(RUN / 'fulcrum.conf')])
        rt = []
        t0 = time.time()
        while time.time() - t0 < 30:
            rt.append({'t': round(time.time() - t0, 1), 'node': node_view(alice, alice_txids),
                       'fulcrum': electrum_view(FU_TCP, sh), 'alive': PROCS['fulcrum-restart'].poll()})
            time.sleep(2)
        results['fulcrum_restart'] = rt
        say('fulcrum restart last', json.dumps(rt[-1], default=str)[:800])
    stop_all()
    (OUT / 'results.json').write_text(json.dumps(results, indent=1, default=str))
    (OUT / 'drive.txt').write_text('\n'.join(LOG) + '\n')


if __name__ == '__main__':
    try:
        main()
    finally:
        stop_all()
