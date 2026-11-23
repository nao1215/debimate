"""Silverback 0.7.39 (eth-ape 0.8.54, ape-foundry 0.8.13) against data gaps (SCENARIOS.md S0-S5).
127.0.0.1 only, Anvil test accounts only.

Ports: anvil 18736, sbproxy (HTTP+WS fault proxy, control at /control) 18737, sink 18738.
The bot (botproj/bot.py) posts every Transfer to bob to the sink from its handler.
Default runner = WebsocketRunner; PollingRunner via --runner silverback.runner:PollingRunner.

Run: venv/bin/python drive.py S0 [S1 S2 S3 S4 S5 ...]  (or a variant name such as S0-poll)
Writes output/runs/<variant>/ and merges into output/results.json.
"""
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

from common import BOB, HERE, TOKEN, Env, summarize

ANVIL_P, PROXY_P, SINK_P = 18736, 18737, 18738
OUT = HERE / 'output'
SB = str(HERE / 'venv/bin/silverback')


class Bot:
    def __init__(self, env, runner, raise_on_500=True):
        self.env, self.runner = env, runner
        self.proc = None
        self.starts, self.exits, self.samples = [], [], []
        self.stop_s = threading.Event()
        for f in ('bot.py', 'ape-config.yaml', 'token_abi.json'):
            shutil.copy(HERE / 'botproj' / f, env.dir / f)
        self.envv = dict(os.environ, TOKEN=TOKEN, BOB=BOB, SINK_URL=env.sink_url, SINK_RAISE='1' if raise_on_500 else '0',
                         APE_DATA_FOLDER=str(HERE / '.ape'), SILVERBACK_BOT_NAME='monitornote', PYTHONUNBUFFERED='1')
        self.logf = open(env.dir / 'silverback.log', 'a')

    def start(self):
        args = [SB, 'run', 'bot:bot', '--network', 'ethereum:local:foundry', '-v', 'INFO']
        if self.runner == 'poll':
            args += ['--runner', 'silverback.runner:PollingRunner']
        self.logf.write(f'\n===== start {time.time()} {args} =====\n')
        self.logf.flush()
        self.proc = subprocess.Popen(args, cwd=self.env.dir, env=self.envv, stdout=self.logf, stderr=subprocess.STDOUT,
                                     start_new_session=True)
        self.stopping = False
        self.starts.append({'t': time.time(), 'head': self.env.head(), 'state_before': self.state()})
        self.env.note(f'silverback start runner={self.runner} state={self.starts[-1]["state_before"]}')

    def wait_ready(self, timeout=90):
        end = time.time() + timeout
        while time.time() < end:
            if 'Startup complete' in (self.env.dir / 'silverback.log').read_text(errors='replace').split('===== start')[-1]:
                self.env.note('silverback startup complete')
                return True
            if self.proc.poll() is not None:
                return False
            time.sleep(0.2)
        return False

    def state(self):
        p = list(self.env.dir.glob('.silverback-sessions/**/state.json'))
        if not p:
            return None
        try:
            return json.loads(p[0].read_text())
        except ValueError:
            return p[0].read_text()

    def alive(self):
        return self.proc is not None and self.proc.poll() is None

    def stop(self, sig):
        t = time.time()
        self.stopping = True
        os.killpg(self.proc.pid, sig)
        try:
            self.proc.wait(30)
        except subprocess.TimeoutExpired:
            os.killpg(self.proc.pid, signal.SIGKILL)
            self.proc.wait()
        d = {'t': t, 'signal': signal.Signals(sig).name, 'rc': self.proc.returncode,
             'exit_after_s': round(time.time() - t, 2), 'head': self.env.head(), 'state_after': self.state()}
        self.env.note(f'silverback stopped {d}')
        return d

    def start_sampler(self, every):
        def loop():
            was = None
            while not self.stop_s.wait(every):
                a = self.alive()
                s = {'t': time.time(), 'alive': a, 'node_head': self.env.head(), 'state': self.state()}
                if not a and self.proc is not None:
                    s['exit_code'] = self.proc.returncode
                self.samples.append(s)
                if was and not a and not getattr(self, 'stopping', False):
                    self.exits.append({'t': time.time(), 'rc': self.proc.returncode})
                    self.env.note(f'silverback exited by itself rc={self.proc.returncode}')
                was = a
        threading.Thread(target=loop, daemon=True).start()

    def close(self):
        self.stop_s.set()
        if self.alive():
            os.killpg(self.proc.pid, signal.SIGTERM)
            try:
                self.proc.wait(20)
            except subprocess.TimeoutExpired:
                os.killpg(self.proc.pid, signal.SIGKILL)


def deliveries(env):
    out = []
    for r in env.sink_records():
        b = r.get('body')
        if isinstance(b, dict) and 'amount' in b:
            out.append({'amount': b['amount'], 't': r['t'], 'status': r['status'], 'block': b['block'],
                        'block_hash': b['block_hash'], 'removed': b.get('removed')})
    return out


def wait_delivered(env, amount, timeout):
    end = time.time() + timeout
    while time.time() < end:
        if any(d['amount'] == amount and d['status'] == 200 for d in deliveries(env)):
            return True
        time.sleep(0.2)
    return False


def log_highlights(env):
    text = (env.dir / 'silverback.log').read_text(errors='replace')
    ansi = re.compile(r'\x1b\[[0-9;]*m')
    pats = ('WARNING', 'ERROR', 'Error', 'error', 'Exception', 'Traceback', 'Halt', 'Shutdown', 'shutdown', 'signal',
            'Startup', 'timed out', 'Timeout', 'reorg', 'Reorg', '=====', 'Using ', 'snapshot', 'state')
    keep = [ansi.sub('', l) for l in text.splitlines() if any(p in l for p in pats)]
    out, last, n = [], None, 0
    for l in keep:
        key = re.sub(r'\d+', 'N', l)
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
    runner = 'poll' if 'poll' in parts else 'ws'
    run_dir = OUT / 'runs' / variant
    if run_dir.exists():
        shutil.rmtree(run_dir)
    env = Env(run_dir, ANVIL_P, PROXY_P, None, SINK_P)
    bot = None
    res = {'variant': variant, 'runner': runner}
    try:
        env.start()
        t0 = time.time()
        res['t0_epoch'] = t0
        bot = Bot(env, runner, raise_on_500='noraise' not in parts)
        res['handler_raises_on_500'] = 'noraise' not in parts
        last = [41]
        env.mint_amount_fn = lambda b: None  # empty blocks until the bot is up
        # Silverback: keep blocks coming (the polling runner gives up after 10 s without a new block).
        env.start_miner()
        bot.start()
        res['ready'] = bot.wait_ready()
        res['ready_t'] = round(time.time() - t0, 3)
        start_block = env.head() + 1
        res['first_event_block'] = start_block
        last[0] = start_block + 39
        env.mint_amount_fn = lambda b: b if start_block <= b <= last[0] else None
        bot.start_sampler(10 if sc == 'S5' else 2)
        if sc == 'S1':
            fb = start_block + 13  # the 14th event, like amount 15 for a monitor started at block 1
            res['fail_block'] = fb
            env.fault(fail_blocks=[fb], mode='error')

        if sc == 'S0':
            env.wait_block(last[0])
            wait_delivered(env, last[0], 30)
            time.sleep(10)
        elif sc == 'S1':
            env.wait_block(fb)
            if parts[1] == 'b':
                time.sleep(20)
                env.fault(fail_blocks=[])
            env.wait_block(last[0])
            wait_delivered(env, last[0], 40)
            time.sleep(20)
        elif sc == 'S2':
            sig = signal.SIGKILL if 'kill' in parts else signal.SIGTERM
            last[0] = 10 ** 6
            tenth = start_block + 8  # 9 events delivered = "1..10" scaled to this start
            assert wait_delivered(env, tenth, 60)
            res['stop'] = bot.stop(sig)
            k = env.head()
            env.wait_block(k + 60)
            bot.start()
            res['ready2'] = bot.wait_ready()
            last[0] = env.head() + 20
            env.wait_block(last[0])
            wait_delivered(env, last[0], 60)
            time.sleep(15)
            res['stop_head'] = k
        elif sc == 'S3':
            r_head = start_block + 18
            env.wait_block(r_head)
            env.mining.clear()
            res['last_before_reorg_delivered'] = wait_delivered(env, r_head, 20)
            time.sleep(1)
            new = [1000 + b for b in range(r_head - 2, r_head + 1)]
            env.reorg(3, new)
            res['reorg_t'] = time.time()
            last[0] = r_head + 20
            env.mining.set()
            env.wait_block(last[0])
            wait_delivered(env, last[0], 40)
            time.sleep(15)
        elif sc == 'S4':
            last[0] = 10 ** 6
            assert wait_delivered(env, start_block + 8, 60)
            env.sink_fail(True)
            res['sink_fail_from'] = time.time()
            time.sleep(60)
            env.sink_fail(False)
            res['sink_fail_to'] = time.time()
            last[0] = env.head() + 20
            env.wait_block(last[0])
            wait_delivered(env, last[0], 30)
            time.sleep(15)
        elif sc == 'S5':
            last[0] = 10 ** 6
            assert wait_delivered(env, start_block + 8, 60)
            env.fault(down=True)
            res['down_from'] = time.time()
            time.sleep(300)
            env.fault(down=False)
            res['down_to'] = time.time()
            last[0] = env.head() + 30
            env.wait_block(last[0])
            wait_delivered(env, last[0], 60)
            time.sleep(20)
        env.mining.clear()
        res['alive_at_end'] = bot.alive()
        res['exit_code'] = None if bot.alive() else bot.proc.returncode
        dl = deliveries(env)
        expected = [e['amount'] for e in env.events if not e.get('reorged_out')]
        retr = [d for d in dl if d.get('removed')]
        res.update(summarize(expected, [d for d in dl if not d.get('removed')], [], t_ref=t0))
        res['retractions'] = [{'t': round(d['t'] - t0, 3), 'amount': d['amount'], 'block': d['block']} for d in retr]
        res['reorged_out_amounts'] = [e['amount'] for e in env.events if e.get('reorged_out')]
        res['reorged_out_delivered'] = [a for a in res['reorged_out_amounts'] if any(d['amount'] == a and d['status'] == 200 for d in dl)]
        res['emitted'] = [{'amount': e['amount'], 'block': e['block'], 't': round(e['t'] - t0, 3),
                           **({'reorged_out_t': round(e['reorged_out'] - t0, 3)} if e.get('reorged_out') else {}),
                           **({'reorg_in': True} if e.get('reorg_in') else {})} for e in env.events]
        res['webhook_posts'] = [{'t': round(d['t'] - t0, 3), 'status': d['status'], 'amount': d['amount'], 'block': d['block'],
                                 'block_hash': d['block_hash'][:12], 'removed': d['removed']} for d in dl]
        res['controls'] = [{'t': round(c['t'] - t0, 3), 'what': c['what']} for c in env.controls]
        res['starts'] = [{**s, 't': round(s['t'] - t0, 3)} for s in bot.starts]
        res['self_exits'] = [{**s, 't': round(s['t'] - t0, 3)} for s in bot.exits]
        if 'stop' in res:
            res['stop']['t'] = round(res['stop']['t'] - t0, 3)
        for k in ('sink_fail_from', 'sink_fail_to', 'down_from', 'down_to', 'reorg_t'):
            if k in res:
                res[k] = round(res[k] - t0, 3)
        res['samples'] = [{**s, 't': round(s['t'] - t0, 3)} for s in bot.samples]
        prox = env.proxy_records()
        res['proxy_faulted'] = sum(1 for p in prox if p.get('fault'))
        res['proxy_methods'] = {}
        for p in prox:
            if p.get('method'):
                res['proxy_methods'][p['method']] = res['proxy_methods'].get(p['method'], 0) + 1
        res['ws_notifications'] = sum(1 for p in prox if p.get('dir') == 'notif')
        res['ws_events'] = [{'t': round(p['t'] - t0, 3), 'event': p['event']} for p in prox if p.get('event')]
        res['log_highlights'] = log_highlights(env)
    finally:
        if bot:
            bot.close()
        env.close()
    p = OUT / 'results.json'
    allr = json.loads(p.read_text()) if p.exists() else {}
    allr[variant] = res
    import importlib.metadata as md
    allr['_versions'] = {k: md.version(k) for k in ('silverback', 'eth-ape', 'ape-foundry', 'web3', 'taskiq')}
    allr['_versions']['anvil'] = subprocess.check_output([str(HERE.parent / 'bin/anvil'), '--version'], text=True).splitlines()[0]
    p.write_text(json.dumps(allr, ensure_ascii=False, indent=1, default=str))
    print(f'== {variant}: expected {len(res["expected"])} delivered {len(res["delivered"])} missing {res["missing"]} '
          f'dup {res["duplicated"]} retractions {len(res["retractions"])} alive {res["alive_at_end"]} rc {res["exit_code"]}', flush=True)


GROUPS = {
    'S0': ['S0-ws', 'S0-poll'],
    'S1': ['S1-a', 'S1-b'],
    'S2': ['S2-term', 'S2-kill'],
    'S3': ['S3-ws'],
    'S4': ['S4-raise', 'S4-noraise'],
    'S5': ['S5-ws'],
}

if __name__ == '__main__':
    for a in sys.argv[1:]:
        for v in GROUPS.get(a, [a]):
            run(v)
