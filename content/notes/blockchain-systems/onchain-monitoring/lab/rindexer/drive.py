"""rindexer 1.0.0 against data gaps (SCENARIOS.md S0-S5). 127.0.0.1 only, Anvil test accounts only.

Ports: anvil 18730, faultproxy 18731 (control 18732), sink 18733, rindexer health 18734
(note: rindexer's health server binds 0.0.0.0, no setting changes it), PostgreSQL 127.0.0.1:18735.
Docker container: monitor-note-rindexer-pg (removed after each run).

Run: python3 drive.py S0 [S1a S1b S2 S3 S4 S5 ...]   (or a single variant name, e.g. S3-on-none)
Writes output/runs/<variant>/ (rindexer.yaml, rindexer.log, sink.jsonl, faultproxy.jsonl, samples)
and merges the result into output/results.json.
"""
import json
import os
import re
import signal
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

from common import BOB, HERE, TOKEN, Env, http_json, summarize

RINDEXER = os.environ.get('RINDEXER', str(HERE.parents[1] / 'indexer/rindexer/bin/rindexer_cli'))
ANVIL_P, PROXY_P, CTRL_P, SINK_P, HEALTH_P, PG_P = 18730, 18731, 18732, 18733, 18734, 18735
PG_NAME = 'monitor-note-rindexer-pg'
DB = f'postgresql://postgres:postgres@127.0.0.1:{PG_P}/postgres'
OUT = HERE / 'output'
NAME = 'monitornote'


def yaml_text(store, reorg, sink_url, proxy_url):
    """store: none|pg. reorg: none (no reorg_handling section) | on | fin (on + delivery: finalized)
    | safe5 (contract reorg_safe_distance: 5, no reorg_handling section)."""
    lines = [f'name: {NAME}', 'project_type: no-code', 'networks:', '  - name: anvil', '    chain_id: 31337',
             f'    rpc: {proxy_url}']
    if reorg in ('on', 'fin'):
        lines += ['    reorg_handling:', '      enabled: true']
    if store == 'pg':
        lines += ['storage:', '  postgres:', '    enabled: true']
    lines += ['contracts:', '  - name: Token', '    details:', '      - network: anvil',
              f'        address: "{TOKEN}"', '        start_block: "1"', '    abi: ./abis/Token.json',
              '    include_events:', '      - Transfer']
    if reorg == 'safe5':
        lines += ['    reorg_safe_distance: 5']
    lines += ['    streams:', '      webhooks:', f'        - endpoint: {sink_url}', '          shared_secret: local-test-secret',
              '          networks:', '            - anvil']
    if reorg == 'fin':
        lines += ['          delivery: finalized']
    lines += ['          events:', '            - event_name: Transfer', '              conditions:',
              f'                - "to": "{BOB}"']
    lines += ['global:', f'  health_port: {HEALTH_P}']
    return '\n'.join(lines) + '\n'


def pg_up():
    subprocess.run(['docker', 'rm', '-f', PG_NAME], capture_output=True)
    subprocess.check_call(['docker', 'run', '-d', '--name', PG_NAME, '-e', 'POSTGRES_PASSWORD=postgres',
                           '-p', f'127.0.0.1:{PG_P}:5432', 'postgres:16-alpine'], stdout=subprocess.DEVNULL)
    for _ in range(100):
        if subprocess.run(['docker', 'exec', PG_NAME, 'pg_isready', '-U', 'postgres'], capture_output=True).returncode == 0:
            time.sleep(1.5)
            return
        time.sleep(0.3)
    raise RuntimeError('postgres did not start')


def pg_down():
    subprocess.run(['docker', 'rm', '-f', PG_NAME], capture_output=True)


def psql(sql):
    r = subprocess.run(['docker', 'exec', PG_NAME, 'psql', '-U', 'postgres', '-At', '-F', '|', '-c', sql],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip())
    return [line.split('|') for line in r.stdout.strip().splitlines() if line]


METRIC_KEEP = re.compile(r'^rindexer_(last_synced_block|latest_chain_block|blocks_behind|active_indexing_tasks|'
                         r'events_processed_total|rpc_requests_total|reorgs_detected_total|reorg_events_deleted_total|'
                         r'stream_messages_total|stream_publish_dropped_total|stream_finalized_buffer_depth|'
                         r'blocks_indexed_total|shared_tip_logs_\w+_total)\b')


class Rindexer:
    def __init__(self, env, store, reorg):
        self.env, self.store, self.reorg = env, store, reorg
        self.proc = None
        self.samples = []
        self.starts = []
        self.sampler_stop = threading.Event()
        (env.dir / 'abis').mkdir(exist_ok=True)
        (env.dir / 'abis/Token.json').write_text((HERE / 'abis/Token.json').read_text())
        (env.dir / 'rindexer.yaml').write_text(yaml_text(store, reorg, env.sink_url, env.proxy_url))
        self.logf = open(env.dir / 'rindexer.log', 'a')

    def start(self):
        envv = dict(os.environ, RINDEXER_LOG='info')
        if self.store == 'pg':
            envv['DATABASE_URL'] = DB
        self.logf.write(f'\n===== start {time.time()} =====\n')
        self.logf.flush()
        self.proc = subprocess.Popen([RINDEXER, 'start', 'indexer'], cwd=self.env.dir, env=envv,
                                     stdout=self.logf, stderr=subprocess.STDOUT, start_new_session=True)
        self.starts.append({'t': time.time(), 'head': self.env.head(), 'resume_from_checkpoint': self.checkpoint()})
        self.env.note(f'rindexer start (checkpoint before start={self.starts[-1]["resume_from_checkpoint"]})')

    def stop(self, sig):
        t = time.time()
        cp_before = self.checkpoint()
        os.killpg(self.proc.pid, sig)
        try:
            self.proc.wait(30)
        except subprocess.TimeoutExpired:
            os.killpg(self.proc.pid, signal.SIGKILL)
            self.proc.wait()
        self.env.note(f'rindexer stopped by {signal.Signals(sig).name} rc={self.proc.returncode} '
                      f'exit_after={time.time()-t:.2f}s checkpoint before={cp_before} after={self.checkpoint()}')
        return {'t': t, 'signal': signal.Signals(sig).name, 'rc': self.proc.returncode, 'exit_after_s': round(time.time() - t, 2),
                'checkpoint_before': cp_before, 'checkpoint_after': self.checkpoint(), 'head': self.env.head()}

    def alive(self):
        return self.proc is not None and self.proc.poll() is None

    def checkpoint(self):
        if self.store == 'pg':
            try:
                rows = psql(f"select last_synced_block from rindexer_internal.{NAME}_token_transfer where network='anvil'")
                return int(rows[0][0]) if rows else None
            except RuntimeError:
                return None
        files = list(self.env.dir.glob('.rindexer/**/last-synced-blocks/*.txt'))
        if not files:
            return None
        try:
            return int(files[0].read_text().strip() or 0)
        except ValueError:
            return files[0].read_text().strip()

    def health(self):
        try:
            with urllib.request.urlopen(f'http://127.0.0.1:{HEALTH_P}/health', timeout=2) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            try:
                return e.code, json.loads(e.read() or b'{}')
            except ValueError:
                return e.code, {}
        except Exception as e:  # noqa: BLE001
            return type(e).__name__, None

    def metrics(self):
        try:
            with urllib.request.urlopen(f'http://127.0.0.1:{HEALTH_P}/metrics', timeout=2) as r:
                text = r.read().decode()
        except Exception as e:  # noqa: BLE001
            return {'error': type(e).__name__}
        out = {}
        for line in text.splitlines():
            if line.startswith('#') or not METRIC_KEEP.match(line):
                continue
            k, _, v = line.rpartition(' ')
            try:
                out[k] = float(v)
            except ValueError:
                pass
        return out

    def sample(self):
        st, body = self.health()
        s = {'t': time.time(), 'alive': self.alive(), 'node_head': self.env.head(), 'checkpoint': self.checkpoint(),
             'health_status': st, 'health': body, 'metrics': self.metrics()}
        self.samples.append(s)
        return s

    def start_sampler(self, every):
        def loop():
            while not self.sampler_stop.wait(every):
                try:
                    self.sample()
                except Exception as e:  # noqa: BLE001
                    self.samples.append({'t': time.time(), 'error': repr(e)})
        threading.Thread(target=loop, daemon=True).start()

    def close(self):
        self.sampler_stop.set()
        if self.alive():
            os.killpg(self.proc.pid, signal.SIGTERM)
            try:
                self.proc.wait(20)
            except subprocess.TimeoutExpired:
                os.killpg(self.proc.pid, signal.SIGKILL)


def deliveries(env):
    out, retractions = [], []
    for r in env.sink_records():
        b = r.get('body')
        if not isinstance(b, dict):
            continue
        if b.get('event_name') == '__rindexer_reorg':
            retractions.append({'t': r['t'], 'status': r['status'], 'payload': b.get('event_data')})
            continue
        for ev in b.get('event_data') or []:
            out.append({'amount': int(ev['value']), 't': r['t'], 'status': r['status'], 'to': ev.get('to'),
                        'block': int(ev['transaction_information']['block_number']),
                        'block_hash': ev['transaction_information']['block_hash'],
                        'msg_id': r.get('headers', {}).get('x-rindexer-id')})
    return out, retractions


def wait_delivered(env, amount, timeout):
    end = time.time() + timeout
    while time.time() < end:
        if any(d['amount'] == amount and d['status'] == 200 for d in deliveries(env)[0]):
            return True
        time.sleep(0.2)
    return False


def log_highlights(env, pats=('WARN', 'ERROR', 'reorg', 'Reorg', 'dropped', 'retry', 'Retry', 'fail', 'Fail', 'stuck', 'behind', 'resum', 'Resum', 'last synced', 'Shutting', 'shutdown')):
    lines = (env.dir / 'rindexer.log').read_text(errors='replace').splitlines()
    ansi = re.compile(r'\x1b\[[0-9;]*m')
    keep = [ansi.sub('', l) for l in lines if any(p in l for p in pats) or l.startswith('=====')]
    # collapse repeats
    out, last, n = [], None, 0
    for l in keep:
        key = re.sub(r'^\S+\s+', '', l)
        key = re.sub(r'\d+', 'N', key)
        if key == last:
            n += 1
            continue
        if n:
            out.append(f'   ... repeated {n} more times')
        out.append(l[:400])
        last, n = key, 0
    if n:
        out.append(f'   ... repeated {n} more times')
    return out


def run(variant):
    parts = variant.split('-')
    sc = parts[0]
    store = 'pg' if 'pg' in parts else 'none'
    reorg = next((p for p in parts[1:] if p in ('none', 'on', 'fin', 'safe5')), 'none') if sc == 'S3' else 'none'
    run_dir = OUT / 'runs' / variant
    if run_dir.exists():
        subprocess.run(['rm', '-rf', str(run_dir)])
    env = Env(run_dir, ANVIL_P, PROXY_P, CTRL_P, SINK_P)
    rx = None
    res = {'variant': variant, 'store': store, 'reorg_config': reorg}
    try:
        if store == 'pg':
            pg_up()
        env.start()
        t0 = time.time()
        res['t0_epoch'] = t0
        rx = Rindexer(env, store, reorg)
        last = [41]
        env.mint_amount_fn = lambda b: b if 2 <= b <= last[0] else None
        if sc == 'S1':
            env.fault(fail_blocks=[15], mode='error')
        if reorg == 'safe5' and 'head1' not in parts:
            # rindexer 1.0.0 panics (divide by zero, core/src/indexer/progress.rs:366) when started with
            # reorg_safe_distance larger than the chain head (variant S3-safe5-*-head1 keeps that run).
            # Start it at head 8 instead; it catches up blocks 2..3 historically, then goes live.
            env.start_miner()
            env.wait_block(8)
            rx.start()
            rx.start_sampler(2)
        else:
            rx.start()
            rx.start_sampler(10 if sc == 'S5' else 2)
            time.sleep(3)
            env.start_miner()

        if sc == 'S0':
            env.wait_block(last[0])
            wait_delivered(env, last[0], 30)
            time.sleep(10)
        elif sc == 'S1':
            env.wait_block(15)
            if parts[1] == 'b':
                time.sleep(20)
                env.fault(fail_blocks=[])
            env.wait_block(last[0])
            wait_delivered(env, last[0], 40)
            time.sleep(20)
            if 'long' in parts:  # watch the stuck indexer past the 300 s heartbeat (empty blocks keep coming)
                time.sleep(330)
        elif sc == 'S2':
            sig = signal.SIGKILL if 'kill' in parts else signal.SIGTERM
            last[0] = 10_000
            assert wait_delivered(env, 10, 60)
            stop = rx.stop(sig)
            res['stop'] = stop
            k = env.head()
            env.wait_block(k + 60)
            rx.start()
            last[0] = k + 80
            env.wait_block(last[0])
            wait_delivered(env, last[0], 60)
            time.sleep(15)
            res['stop_head'] = k
        elif sc == 'S3':
            env.wait_block(20)
            env.mining.clear()
            if reorg in ('none', 'on'):
                res['amount20_delivered_before_reorg'] = wait_delivered(env, 20, 20)
            else:
                time.sleep(3)
            time.sleep(1)
            pre = rx.sample()
            res['before_reorg'] = pre
            env.reorg(3, [1018, 1019, 1020])
            res['reorg_t'] = time.time()
            after = 80 if reorg == 'fin' else 20
            last[0] = 20 + after
            env.mining.set()
            env.wait_block(last[0])
            wait_delivered(env, last[0] - (64 if reorg == 'fin' else 0), 60)
            time.sleep(15)
            if reorg == 'fin':
                # let the 64-block finality catch up with the last event blocks (empty blocks)
                env.wait_block(last[0] + 66)
                time.sleep(10)
        elif sc == 'S4':
            last[0] = 10_000
            assert wait_delivered(env, 10, 60)
            env.sink_fail(True)
            res['sink_fail_from'] = time.time()
            time.sleep(60)
            env.sink_fail(False)
            res['sink_fail_to'] = time.time()
            k = env.head()
            last[0] = k + 20
            env.wait_block(last[0])
            wait_delivered(env, last[0], 30)
            time.sleep(15)
        elif sc == 'S5':
            last[0] = 10_000
            assert wait_delivered(env, 10, 60)
            env.fault(down=True)
            res['down_from'] = time.time()
            time.sleep(300)
            env.fault(down=False)
            res['down_to'] = time.time()
            k = env.head()
            last[0] = k + 30
            env.wait_block(last[0])
            wait_delivered(env, last[0], 120)
            time.sleep(20)
        env.mining.clear()
        rx.sample()
        res['alive_at_end'] = rx.alive()
        res['exit_code'] = None if rx.alive() else rx.proc.returncode
        dl, rt = deliveries(env)
        expected = [e['amount'] for e in env.events if not e.get('reorged_out')]
        res.update(summarize(expected, dl, rt, t_ref=t0))
        res['reorged_out_amounts'] = [e['amount'] for e in env.events if e.get('reorged_out')]
        res['reorged_out_delivered'] = [a for a in res['reorged_out_amounts'] if any(d['amount'] == a and d['status'] == 200 for d in dl)]
        res['emitted'] = [{'amount': e['amount'], 'block': e['block'], 't': round(e['t'] - t0, 3),
                           **({'reorged_out_t': round(e['reorged_out'] - t0, 3)} if e.get('reorged_out') else {}),
                           **({'reorg_in': True} if e.get('reorg_in') else {})} for e in env.events]
        res['webhook_posts'] = [{'t': round(d['t'] - t0, 3), 'status': d['status'], 'amount': d['amount'], 'block': d['block'],
                                 'block_hash': d['block_hash'][:12], 'msg_id': d['msg_id']} for d in dl]
        res['retractions'] = [{'t': round(r['t'] - t0, 3), 'status': r['status'], 'payload': r['payload']} for r in rt]
        res['controls'] = [{'t': round(c['t'] - t0, 3), 'what': c['what']} for c in env.controls]
        res['starts'] = [{**s, 't': round(s['t'] - t0, 3)} for s in rx.starts]
        if 'stop' in res:
            res['stop']['t'] = round(res['stop']['t'] - t0, 3)
        for k in ('sink_fail_from', 'sink_fail_to', 'down_from', 'down_to', 'reorg_t'):
            if k in res:
                res[k] = round(res[k] - t0, 3)
        res['samples'] = [{**s, 't': round(s['t'] - t0, 3)} for s in rx.samples]
        if 'before_reorg' in res:
            res['before_reorg']['t'] = round(res['before_reorg']['t'] - t0, 3)
        prox = env.proxy_records()
        res['proxy_faulted_requests'] = sum(1 for p in prox if p.get('fault'))
        res['proxy_requests'] = sum(1 for p in prox if 'method' in p)
        res['log_highlights'] = log_highlights(env)
        if store == 'pg':
            try:
                res['pg_rows'] = [int(r[0]) for r in psql(f'select value from {NAME}_token.transfer order by block_number, log_index')]
            except RuntimeError as e:
                res['pg_rows'] = str(e)
    finally:
        if rx:
            rx.close()
        env.close()
        if store == 'pg':
            pg_down()
    p = OUT / 'results.json'
    allr = json.loads(p.read_text()) if p.exists() else {}
    allr[variant] = res
    allr['_versions'] = {'rindexer': subprocess.check_output([RINDEXER, '--version'], text=True).strip(),
                         'anvil': subprocess.check_output([str(HERE.parent / 'bin/anvil'), '--version'], text=True).splitlines()[0]}
    p.write_text(json.dumps(allr, ensure_ascii=False, indent=1, default=str))
    print(f'== {variant}: expected {len(res["expected"])} delivered {len(res["delivered"])} missing {res["missing"]} '
          f'dup {res["duplicated"]} unexpected {res["unexpected"]} retractions {len(res["retractions"])} '
          f'alive {res["alive_at_end"]}', flush=True)


GROUPS = {
    'S0': ['S0-none', 'S0-pg'],
    'S1': ['S1-a', 'S1-b'],
    'S2': ['S2-term-none', 'S2-kill-none', 'S2-term-pg', 'S2-kill-pg'],
    'S3': [f'S3-{r}-{s}' for s in ('none', 'pg') for r in ('none', 'on', 'fin', 'safe5')],
    'S4': ['S4-none'],
    'S5': ['S5-none'],
}

if __name__ == '__main__':
    for a in sys.argv[1:]:
        for v in GROUPS.get(a, [a]):
            run(v)
