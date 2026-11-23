"""OpenZeppelin Monitor の欠けの実験（共通シナリオ S0〜S5、../SCENARIOS.md）。

127.0.0.1 だけを使う。Anvil の既定テスト用アカウントだけを使い、公開ネットワーク・実資産・実鍵は使わない。

実行例（そのまま再実行できる）:
  python3 drive.py --ver v170 --scen S0 --base 18720
  python3 drive.py --ver main --scen S2_kill_unlimited --base 18725

ポート: base=anvil, base+1=faultproxy, base+2=faultproxy の制御, base+3=sink, base+4=monitor の /metrics
成果物: runs/<ver>/<scen>/ に timeline.jsonl（時系列）, monitor.log, sink.jsonl, proxy.jsonl, config/, data/, run.json
"""
import argparse
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

OZ = Path(__file__).resolve().parent
MON = OZ.parent
LAB = MON.parent.parent / 'indexer/lab'
sys.path.insert(0, str(LAB))
from keccak import keccak256  # noqa: E402

ANVIL = str(MON / 'bin/anvil')
SOLC = str(Path.home() / '.local/share/block/tools/solc/0.8.28-9a0fb7e0db2c/solc')
BINS = {
    'v170': OZ / 'build/target-v170/release/openzeppelin-monitor',
    'main': OZ / 'build/target-main/release/openzeppelin-monitor',
}
SLUG = 'anvil_local'
BOB = '0x70997970c51812dc3a010c7d01b50e0d17dc79c8'

# シナリオ: (種類, 設定)
SCENARIOS = {
    'S0': ('base', {}),
    # 同じ S0 を繰り返して、欠けなしの条件で黙って消える件があるかを見る（v170 S2_kill_unlimited の量 7）
    'S0_r1': ('base', {}), 'S0_r2': ('base', {}), 'S0_r3': ('base', {}), 'S0_r4': ('base', {}),
    # S1: 量 15 = block 15。full は faultproxy の既定（ブロック取得も getLogs も失敗）、
    # logs は eth_getLogs とレシート系だけ失敗（フィルタ段の失敗だけを切り出す）。
    'S1a_full': ('s1', {'persist': True, 'methods': None}),
    'S1b_full': ('s1', {'persist': False, 'methods': None}),
    'S1a_logs': ('s1', {'persist': True, 'methods': ['eth_getLogs', 'eth_getTransactionReceipt', 'eth_getBlockReceipts']}),
    'S1b_logs': ('s1', {'persist': False, 'methods': ['eth_getLogs', 'eth_getTransactionReceipt', 'eth_getBlockReceipts']}),
    'S1a_logs_rec': ('s1', {'persist': True, 'methods': ['eth_getLogs', 'eth_getTransactionReceipt', 'eth_getBlockReceipts'], 'recovery': True}),
    'S1b_logs_rec': ('s1', {'persist': False, 'methods': ['eth_getLogs', 'eth_getTransactionReceipt', 'eth_getBlockReceipts'], 'recovery': True}),
    # recovery の cron を 15 秒にした版（3 回の再試行が 20 秒の障害より長く続く）
    'S1b_logs_rec15': ('s1', {'persist': False, 'methods': ['eth_getLogs', 'eth_getTransactionReceipt', 'eth_getBlockReceipts'], 'recovery': True, 'rec_cron': '*/15 * * * * *'}),
    'S2_term_default': ('s2', {'sig': 'TERM'}),
    'S2_kill_default': ('s2', {'sig': 'KILL'}),
    'S2_term_unlimited': ('s2', {'sig': 'TERM', 'max_past': 'unlimited'}),
    'S2_kill_unlimited': ('s2', {'sig': 'KILL', 'max_past': 'unlimited'}),
    'S2_term_default_rec': ('s2', {'sig': 'TERM', 'recovery': True}),
    'S3_c1': ('s3', {'conf': 1}),
    'S3_c5': ('s3', {'conf': 5}),
    'S4': ('s4', {}),
    'S5': ('s5', {}),
    'S5_unlimited': ('s5', {'max_past': 'unlimited'}),
}


class Run:
    def __init__(self, ver, scen, base):
        self.ver, self.scen, self.base = ver, scen, base
        self.kind, self.opts = SCENARIOS[scen]
        self.dir = OZ / 'runs' / ver / scen
        if self.dir.exists():
            shutil.rmtree(self.dir)
        (self.dir / 'data').mkdir(parents=True)
        self.tl = open(self.dir / 'timeline.jsonl', 'w', buffering=1)
        self.tl_lock = threading.Lock()
        self.procs = {}
        self.mon = None
        self.mon_log = open(self.dir / 'monitor.log', 'ab')
        self.stop_sampler = threading.Event()
        self.mined = []  # [(block, amount)]
        self.conf = self.opts.get('conf', 1)

    # ---- 記録 ----
    def ev(self, kind, **kw):
        rec = {'t': time.time(), 'ev': kind, **kw}
        with self.tl_lock:
            self.tl.write(json.dumps(rec) + '\n')
        return rec

    # ---- RPC（Anvil へ直接。監視は faultproxy 経由） ----
    def rpc(self, method, *params, port=None):
        body = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': list(params)}).encode()
        req = urllib.request.Request(f'http://127.0.0.1:{port or self.base}', body, {'Content-Type': 'application/json'})
        res = json.loads(urllib.request.urlopen(req, timeout=30).read())
        if 'error' in res:
            raise RuntimeError(res['error'])
        return res['result']

    def post(self, port, path, obj):
        req = urllib.request.Request(f'http://127.0.0.1:{port}{path}', json.dumps(obj).encode(),
                                     {'Content-Type': 'application/json'})
        return urllib.request.urlopen(req, timeout=10).read()

    def proxy(self, **cmd):
        out = json.loads(self.post(self.base + 2, '/control', cmd))
        self.ev('proxy_control', **out)

    def sink(self, fail):
        self.post(self.base + 3, '/control', {'fail': fail})
        self.ev('sink_control', fail=fail)

    def head(self):
        return int(self.rpc('eth_blockNumber'), 16)

    # ---- 起動 ----
    def start_chain(self):
        compiled = json.loads(subprocess.check_output(
            [SOLC, '--evm-version', 'cancun', '--combined-json', 'bin', str(LAB / 'Token.sol')], text=True))
        code = next(iter(compiled['contracts'].values()))['bin']
        self.versions = {
            'anvil': subprocess.check_output([ANVIL, '--version'], text=True).splitlines()[0],
            'solc': subprocess.check_output([SOLC, '--version'], text=True).splitlines()[-1],
        }
        log = open(self.dir / 'anvil.log', 'w')
        self.procs['anvil'] = subprocess.Popen(
            [ANVIL, '--host', '127.0.0.1', '--port', str(self.base), '--chain-id', '31337', '--hardfork', 'cancun',
             '--accounts', '4', '--no-mining', '--quiet'], stdout=log, stderr=log)
        for _ in range(100):
            try:
                accounts = self.rpc('eth_accounts')
                break
            except OSError:
                time.sleep(0.1)
        self.alice, self.bob = accounts[0].lower(), accounts[1].lower()
        assert self.bob == BOB, self.bob
        h = self.rpc('eth_sendTransaction', {'from': self.alice, 'data': '0x' + code + (10**12).to_bytes(32, 'big').hex(),
                                             'gas': hex(2_000_000)})
        self.rpc('evm_mine')
        self.token = self.rpc('eth_getTransactionReceipt', h)['contractAddress'].lower()
        self.ev('deployed', block=self.head(), token=self.token)

    def transfer_tx(self, amount):
        data = keccak256(b'transfer(address,uint256)')[:4] + bytes.fromhex(self.bob[2:]).rjust(32, b'\0') + amount.to_bytes(32, 'big')
        return {'from': self.alice, 'to': self.token, 'data': '0x' + data.hex(), 'gas': hex(100_000)}

    def mine(self, event=True):
        n = self.head() + 1
        if event:
            self.rpc('eth_sendTransaction', self.transfer_tx(n))
        self.rpc('evm_mine')
        assert self.head() == n
        if event:
            self.mined.append((n, n))
        self.ev('mined', block=n, amount=n if event else None)
        if self.mon is None and n - self.conf >= 1:
            # 監視は確定ブロック（頭 - confirmation_blocks）が 1 以上になってから起動する（確定 0 で tick が走ると、置いたチェックポイント 1 が
            # 0 に書き戻され、次の tick が初回扱いで先頭へ飛ぶため。runs/v170/_artifact_startup_S1a_full）
            self.start_monitor()
            time.sleep(1)
        return n

    def write_config(self):
        cfg = self.dir / 'config'
        for d in ('networks', 'monitors', 'triggers', 'filters'):
            (cfg / d).mkdir(parents=True, exist_ok=True)
        net = {
            'network_type': 'EVM', 'slug': SLUG, 'name': 'Anvil (Local)',
            'rpc_urls': [{'type_': 'rpc', 'url': {'type': 'plain', 'value': f'http://127.0.0.1:{self.base + 1}'}, 'weight': 100}],
            'chain_id': 31337, 'block_time_ms': 1000, 'confirmation_blocks': self.conf,
            'cron_schedule': '*/10 * * * * *', 'store_blocks': False,
        }
        # max_past_blocks を書かない = 既定（cron 間隔/ブロック時間 + confirmation_blocks + 1）
        if 'max_past' in self.opts:
            net['max_past_blocks'] = self.opts['max_past']
        if self.opts.get('recovery'):
            net['recovery_config'] = {'enabled': True, 'cron_schedule': self.opts.get('rec_cron', '*/5 * * * * *'), 'max_blocks_per_run': 10,
                                      'max_block_age': 1000, 'max_retries': 3, 'retry_delay_ms': 1000}
        transfer_event = {'anonymous': False, 'name': 'Transfer', 'type': 'event', 'inputs': [
            {'indexed': True, 'internalType': 'address', 'name': 'from', 'type': 'address'},
            {'indexed': True, 'internalType': 'address', 'name': 'to', 'type': 'address'},
            {'indexed': False, 'internalType': 'uint256', 'name': 'value', 'type': 'uint256'}]}
        mon = {
            'name': 'Transfer to bob', 'paused': False, 'networks': [SLUG],
            'addresses': [{'address': self.token, 'contract_spec': [transfer_event]}],
            'match_conditions': {'functions': [], 'transactions': [],
                                 'events': [{'signature': 'Transfer(address,address,uint256)', 'expression': f'to == {BOB}'}]},
            'trigger_conditions': [], 'triggers': ['sink_webhook'],
        }
        trig = {'sink_webhook': {'name': 'sink', 'trigger_type': 'webhook', 'config': {
            'url': {'type': 'plain', 'value': f'http://127.0.0.1:{self.base + 3}/hook'},
            'method': 'POST', 'headers': {'Content-Type': 'application/json'},
            'message': {'title': 'transfer', 'body': 'amount=${events.0.args.value} tx=${transaction.hash}'}}}}
        (cfg / 'networks/anvil_local.json').write_text(json.dumps(net, indent=2))
        (cfg / 'monitors/transfer_to_bob.json').write_text(json.dumps(mon, indent=2))
        (cfg / 'triggers/sink_webhook.json').write_text(json.dumps(trig, indent=2))
        # 初回（チェックポイント 0）は最新の確定ブロックから始まるので、block 2 から見るよう 1 を置く
        (self.dir / 'data' / f'{SLUG}_last_block.txt').write_text('1')
        self.ev('checkpoint_seeded', value=1)

    def start_tools(self):
        py = sys.executable
        self.procs['proxy'] = subprocess.Popen(
            [py, str(OZ / 'faultproxy_oz.py'), str(self.base + 1), f'http://127.0.0.1:{self.base}',
             str(self.dir / 'proxy.jsonl'), str(self.base + 2)])
        self.procs['sink'] = subprocess.Popen([py, str(OZ / 'sink_ctl.py'), str(self.base + 3), str(self.dir / 'sink.jsonl')])
        time.sleep(0.5)

    def start_monitor(self):
        env = dict(os.environ, LOG_LEVEL=os.environ.get('OZ_LOG_LEVEL', 'info'), NO_COLOR='1', RUST_LOG_STYLE='never')
        env.pop('RUST_LOG', None)
        self.mon_log.write(f'\n===== start {time.time()} =====\n'.encode())
        self.mon_log.flush()
        self.mon = subprocess.Popen([str(BINS[self.ver]), '--metrics', '--metrics-address', f'127.0.0.1:{self.base + 4}'],
                                    cwd=self.dir, env=env, stdout=self.mon_log, stderr=subprocess.STDOUT)
        self.ev('monitor_start', pid=self.mon.pid)

    def stop_monitor(self, sig):
        t0 = time.time()
        self.ev('monitor_signal', sig=sig, checkpoint=self.checkpoint())
        self.mon.send_signal(signal.SIGTERM if sig == 'TERM' else signal.SIGKILL)
        try:
            code = self.mon.wait(timeout=60)
        except subprocess.TimeoutExpired:
            self.mon.kill()
            code = self.mon.wait()
            self.ev('monitor_forced_kill')
        self.ev('monitor_exit', code=code, took=time.time() - t0, checkpoint=self.checkpoint())

    def checkpoint(self):
        try:
            return int((self.dir / 'data' / f'{SLUG}_last_block.txt').read_text().strip())
        except Exception:
            return None

    # ---- 観測 ----
    def metrics(self):
        try:
            text = urllib.request.urlopen(f'http://127.0.0.1:{self.base + 4}/metrics', timeout=3).read().decode()
        except Exception as e:
            return {'error': type(e).__name__}
        keep = ('block_checkpoint_lag', 'rpc_requests_total', 'rpc_request_errors_total', 'rpc_endpoint_rotations_total',
                'rpc_null_results_total', 'network_monitors', 'monitors_total')
        out = {}
        for line in text.splitlines():
            if line.startswith('#'):
                continue
            if line.startswith(keep):
                k, _, v = line.rpartition(' ')
                out[k] = float(v)
        return out

    def sampler(self):
        last_metrics = 0
        while not self.stop_sampler.is_set():
            alive = self.mon is not None and self.mon.poll() is None
            self.ev('sample', checkpoint=self.checkpoint(), head=self.head(), alive=alive,
                    exit=None if alive or self.mon is None else self.mon.returncode)
            if time.time() - last_metrics >= 10:
                last_metrics = time.time()
                self.ev('metrics', alive=alive, values=self.metrics() if alive else {'error': 'not running'})
            time.sleep(1)

    def delivered(self):
        out = []
        p = self.dir / 'sink.jsonl'
        if not p.exists():
            return out
        for line in p.read_text().splitlines():
            r = json.loads(line)
            if 'control' in r:
                continue
            body = r['body'].get('body', '') if isinstance(r['body'], dict) else str(r['body'])
            m = re.search(r'amount=(\d+)', body)
            out.append({'t': r['t'], 'status': r['status'], 'amount': int(m.group(1)) if m else None})
        return out

    def ok_amounts(self):
        return {d['amount'] for d in self.delivered() if d['status'] == 200}

    def tick_until(self, cond, timeout, event=True):
        """1 秒に 1 ブロック掘りながら cond() を待つ。"""
        end = time.time() + timeout
        while time.time() < end:
            if cond():
                return True
            self.mine(event)
            time.sleep(1)
        return cond()

    def run_blocks(self, n, event=True, each=None):
        for _ in range(n):
            b = self.mine(event)
            if each:
                each(b)
            time.sleep(1)

    def drain(self, timeout=60):
        """イベント無しのブロックを掘りながら、チェックポイントが最後のイベントのブロックに届くまで待つ。"""
        last = self.mined[-1][0] if self.mined else 0
        ok = self.tick_until(lambda: (self.checkpoint() or 0) >= last, timeout, event=False)
        time.sleep(3)  # 通知は投げっぱなし（tokio::spawn）なので少し待つ
        self.ev('drained', reached=ok, checkpoint=self.checkpoint(), last_event_block=last)

    # ---- シナリオ ----
    def scenario(self):
        k, o = self.kind, self.opts
        if k == 'base':
            self.run_blocks(40)
            self.drain()
        elif k == 's1':
            self.proxy(fail_blocks=[15], mode='error', fail_methods=o['methods'])
            state = {'cleared': False}

            def first_fault():
                p = self.dir / 'proxy.jsonl'
                for line in p.read_text().splitlines():
                    r = json.loads(line)
                    if r.get('fault'):
                        return r['t']
                return None

            def each(b):
                if o['persist'] or state['cleared']:
                    return
                t = first_fault()
                if t and time.time() - t >= 20:
                    self.proxy(fail_blocks=[], fail_methods=None)
                    state['cleared'] = True
                    self.ev('fault_cleared', first_fault=t)

            self.run_blocks(40, each=each)
            if not o['persist']:
                # 40 件を掘り終えても 20 秒が経っていなければ、経つまで待つ
                self.tick_until(lambda: (each(0) or state['cleared']), 60, event=False)
            self.drain(timeout=90 if o.get('recovery') else 60)
            if o.get('recovery'):
                # recovery は */5 秒。もう少し様子を見る
                self.tick_until(lambda: False, 40, event=False)
        elif k == 's2':
            self.tick_until(lambda: 10 in self.ok_amounts(), 60)
            self.stop_monitor(o['sig'])
            self.run_blocks(60)
            self.start_monitor()
            self.run_blocks(20)
            self.drain(timeout=90)
        elif k == 's3':
            self.tick_until(lambda: 20 in self.ok_amounts(), 90)
            # 掘るのを止め、監視が確定ブロックまで処理し終えるのを待つ（置き換える 3 つのうち通知済みの分を決める）
            h = self.head()
            reached = self.wait(lambda: self.checkpoint() == h - self.conf, 30)
            time.sleep(3)
            before = sorted(self.ok_amounts())
            replaced = [h - 2, h - 1, h]
            old_hashes = {n: self.rpc('eth_getBlockByNumber', hex(n), False)['hash'] for n in replaced}
            self.ev('reorg_before', head=h, checkpoint=self.checkpoint(), checkpoint_reached=reached,
                    delivered_before=before, replaced=replaced, old_hashes=old_hashes)
            txs = [[self.transfer_tx(1000 + n), i] for i, n in enumerate(replaced)]
            self.rpc('anvil_reorg', 3, txs)
            new_hashes = {n: self.rpc('eth_getBlockByNumber', hex(n), False)['hash'] for n in replaced}
            self.mined = [(b, a) for b, a in self.mined if b not in replaced] + [(n, 1000 + n) for n in replaced]
            self.ev('reorg', depth=3, head=self.head(), new_hashes=new_hashes,
                    new_amounts=[1000 + n for n in replaced])
            self.run_blocks(20)
            self.drain(timeout=60)
        elif k == 's4':
            self.run_blocks(9)  # block 2..10
            self.sink(True)
            t0 = time.time()
            while time.time() - t0 < 60:
                self.mine()
                time.sleep(1)
            self.sink(False)
            self.run_blocks(20)
            self.drain(timeout=60)
            self.tick_until(lambda: False, 30, event=False)  # 再送が遅れて来るかを見る
        elif k == 's5':
            self.run_blocks(11)  # block 2..12
            self.proxy(down=True)
            t0 = time.time()
            while time.time() - t0 < 300:
                self.mine()
                time.sleep(1)
            self.proxy(down=False)
            self.run_blocks(20)
            self.drain(timeout=120)

    def wait(self, cond, timeout):
        end = time.time() + timeout
        while time.time() < end:
            if cond():
                return True
            time.sleep(0.5)
        return False

    def canonical(self):
        """最後のチェーンでの bob 宛ての Transfer の量（Anvil へ直接）。"""
        topic = '0x' + keccak256(b'Transfer(address,address,uint256)').hex()
        logs = self.rpc('eth_getLogs', {'address': self.token, 'topics': [topic, None, '0x' + self.bob[2:].rjust(64, '0')],
                                        'fromBlock': '0x0', 'toBlock': 'latest'})
        return sorted(int(l['data'], 16) for l in logs)

    def main(self):
        self.ev('run_start', ver=self.ver, scen=self.scen, opts=self.opts)
        sampler = None
        try:
            self.start_chain()
            self.write_config()
            self.start_tools()
            sampler = threading.Thread(target=self.sampler, daemon=True)
            sampler.start()
            self.scenario()
            canon = self.canonical()
            health = None
            try:
                urllib.request.urlopen(f'http://127.0.0.1:{self.base + 4}/health', timeout=3)
                health = 'ok'
            except Exception as e:
                health = str(e)
            self.ev('run_end', canonical=canon, health_probe=health)
            run = {'ver': self.ver, 'scen': self.scen, 'opts': self.opts, 'versions': self.versions,
                   'binary': str(BINS[self.ver]), 'token': self.token, 'canonical': canon,
                   'mined': self.mined, 'health_probe': health,
                   'monitor_alive_at_end': self.mon.poll() is None}
            (self.dir / 'run.json').write_text(json.dumps(run, indent=1))
        finally:
            self.stop_sampler.set()
            if sampler:
                sampler.join(timeout=5)
            if self.mon and self.mon.poll() is None:
                self.mon.send_signal(signal.SIGTERM)
                try:
                    self.mon.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    self.mon.kill()
            for p in self.procs.values():
                p.terminate()
                try:
                    p.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    p.kill()


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--ver', choices=list(BINS), required=True)
    ap.add_argument('--scen', choices=list(SCENARIOS), required=True)
    ap.add_argument('--base', type=int, required=True)
    a = ap.parse_args()
    assert 18720 <= a.base and a.base + 4 <= 18729
    Run(a.ver, a.scen, a.base).main()
