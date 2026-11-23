"""Shared helpers for the monitor experiments (127.0.0.1 only, Anvil test accounts only).

- Chain: anvil --no-mining. A Miner thread puts one alice->bob transfer per block and calls
  evm_mine once a second; the amount equals the block number, so each amount names its block.
- faultproxy.py sits in front of Anvil; the monitor only talks to the proxy.
- sink_ctl.py records every webhook with its receive time; POST /__control {"fail": bool}
  switches it to answer 500.
"""
import json
import os
import subprocess
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
MON = HERE.parent
LAB = MON.parent.parent / 'indexer/lab'
ANVIL = str(MON / 'bin/anvil')
SOLC = os.environ.get('SOLC', str(Path.home() / '.local/share/block/tools/solc/0.8.28-9a0fb7e0db2c/solc'))

import sys  # noqa: E402
sys.path.insert(0, str(LAB))
from keccak import keccak256  # noqa: E402

ALICE = '0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266'
BOB = '0x70997970c51812dc3a010c7d01b50e0d17dc79c8'
TOKEN = '0x5fbdb2315678afecb367f032d93f642f64180aa3'
SUPPLY = 10**12


def word(v):
    return bytes.fromhex(v[2:]).rjust(32, b'\0') if isinstance(v, str) else v.to_bytes(32, 'big')


def calldata(sig, *args):
    return '0x' + (keccak256(sig.encode())[:4] + b''.join(word(a) for a in args)).hex()


def transfer_tx(value, to=BOB):
    return {'from': ALICE, 'to': TOKEN, 'data': calldata('transfer(address,uint256)', to, value), 'gas': hex(100_000)}


def token_bytecode():
    out = subprocess.check_output([SOLC, '--evm-version', 'cancun', '--combined-json', 'bin', str(LAB / 'Token.sol')], text=True)
    return next(iter(json.loads(out)['contracts'].values()))['bin']


def http_json(url, body=None, timeout=5):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data, {'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
    try:
        return json.loads(raw)
    except ValueError:
        return raw.decode(errors='replace')


class Env:
    """anvil + faultproxy + sink for one scenario run."""

    def __init__(self, run_dir, anvil_port, proxy_port, control_port, sink_port):
        self.dir = Path(run_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.anvil_port, self.proxy_port, self.control_port, self.sink_port = anvil_port, proxy_port, control_port, sink_port
        self.procs = []
        self.events = []          # [{'amount', 'block', 't'}] what the chain emitted (to bob)
        self.controls = []        # [{'t', 'what'}]
        self.lock = threading.Lock()
        self.mining = threading.Event()
        self.stop_flag = threading.Event()
        self.miner = None
        self.mint_amount_fn = None  # optional: block -> amount or None (no transfer)

    @property
    def anvil_url(self):
        return f'http://127.0.0.1:{self.anvil_port}'

    @property
    def proxy_url(self):
        return f'http://127.0.0.1:{self.proxy_port}'

    @property
    def sink_url(self):
        return f'http://127.0.0.1:{self.sink_port}/hook'

    def rpc(self, method, *params):
        res = http_json(self.anvil_url, {'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': list(params)}, timeout=30)
        if 'error' in res:
            raise RuntimeError(res['error'])
        return res['result']

    def _spawn(self, name, args):
        log = open(self.dir / f'{name}.log', 'w')
        p = subprocess.Popen(args, stdout=log, stderr=subprocess.STDOUT)
        self.procs.append(p)
        return p

    def start(self):
        self._spawn('anvil', [ANVIL, '--host', '127.0.0.1', '--port', str(self.anvil_port), '--chain-id', '31337',
                              '--hardfork', 'cancun', '--accounts', '4', '--no-mining', '--quiet'])
        if self.control_port is None:  # Silverback: HTTP+WS proxy on one port (sbproxy.py), control at /control
            self._spawn('faultproxy', [str(HERE / 'venv/bin/python'), str(HERE / 'sbproxy.py'), str(self.proxy_port),
                                       self.anvil_url, f'ws://127.0.0.1:{self.anvil_port}', str(self.dir / 'faultproxy.jsonl')])
        else:
            self._spawn('faultproxy', ['python3', str(MON / 'faultproxy.py'), str(self.proxy_port), self.anvil_url,
                                       str(self.dir / 'faultproxy.jsonl'), str(self.control_port)])
        self._spawn('sink', ['python3', str(HERE / 'sink_ctl.py'), str(self.sink_port), str(self.dir / 'sink.jsonl')])
        for _ in range(200):
            try:
                self.rpc('eth_chainId')
                http_json(self.proxy_url, {'jsonrpc': '2.0', 'id': 1, 'method': 'eth_chainId', 'params': []})
                http_json(f'http://127.0.0.1:{self.sink_port}/__control', {'fail': False})
                break
            except Exception:  # noqa: BLE001
                time.sleep(0.1)
        code = token_bytecode()
        self.rpc('eth_sendTransaction', {'from': ALICE, 'data': '0x' + code + word(SUPPLY).hex(), 'gas': hex(2_000_000)})
        self.rpc('evm_mine')
        assert int(self.rpc('eth_blockNumber'), 16) == 1
        assert self.rpc('eth_getCode', TOKEN, 'latest') != '0x'

    def head(self):
        return int(self.rpc('eth_blockNumber'), 16)

    def mine_one(self):
        with self.lock:
            b = self.head() + 1
            amount = b if self.mint_amount_fn is None else self.mint_amount_fn(b)
            if amount is not None:
                self.rpc('eth_sendTransaction', transfer_tx(amount))
            self.rpc('evm_mine')
            t = time.time()
            if amount is not None:
                self.events.append({'amount': amount, 'block': b, 't': t})
            return b

    def _miner_loop(self):
        nxt = time.time()
        while not self.stop_flag.is_set():
            if self.mining.is_set():
                try:
                    self.mine_one()
                except Exception as e:  # noqa: BLE001
                    self.note(f'miner error {e}')
            nxt += 1.0
            time.sleep(max(0, nxt - time.time()))

    def start_miner(self):
        self.mining.set()
        self.miner = threading.Thread(target=self._miner_loop, daemon=True)
        self.miner.start()

    def wait_block(self, n, timeout=600):
        end = time.time() + timeout
        while time.time() < end:
            if self.head() >= n:
                return
            time.sleep(0.1)
        raise TimeoutError(f'block {n}')

    def reorg(self, depth, new_amounts):
        """Replace the last `depth` blocks; block i of the new ones gets transfer new_amounts[i]."""
        with self.lock:
            h = self.head()
            dropped = [e for e in self.events if e['block'] > h - depth]
            self.rpc('anvil_reorg', depth, [[transfer_tx(a), i] for i, a in enumerate(new_amounts)])
            t = time.time()
            for e in dropped:
                e['reorged_out'] = t
            for i, a in enumerate(new_amounts):
                self.events.append({'amount': a, 'block': h - depth + 1 + i, 't': t, 'reorg_in': True})
            self.note(f'anvil_reorg depth={depth} head={h} dropped={[e["amount"] for e in dropped]} new={new_amounts}')
            return h

    def fault(self, **cmd):
        url = f'http://127.0.0.1:{self.control_port}/control' if self.control_port else f'{self.proxy_url}/control'
        r = http_json(url, cmd)
        self.note(f'faultproxy {r}')
        return r

    def sink_fail(self, fail):
        http_json(f'http://127.0.0.1:{self.sink_port}/__control', {'fail': fail})
        self.note(f'sink fail={fail}')

    def note(self, what):
        self.controls.append({'t': time.time(), 'what': what})
        print(time.strftime('%H:%M:%S'), what, flush=True)

    def sink_records(self):
        p = self.dir / 'sink.jsonl'
        if not p.exists():
            return []
        return [json.loads(line) for line in p.read_text().splitlines() if line.strip()]

    def proxy_records(self):
        p = self.dir / 'faultproxy.jsonl'
        return [json.loads(line) for line in p.read_text().splitlines() if line.strip()] if p.exists() else []

    def close(self):
        self.stop_flag.set()
        if self.miner:
            self.miner.join(3)
        for p in reversed(self.procs):
            p.terminate()
            try:
                p.wait(5)
            except subprocess.TimeoutExpired:
                p.kill()


def summarize(expected, deliveries, retractions=None, t_ref=None):
    """deliveries: [{'amount', 't', 'status'}] counted only when status==200 (what the receiver accepted).
    Also returns attempts (incl. 500s) per amount."""
    acc, att = {}, {}
    for d in deliveries:
        att.setdefault(d['amount'], []).append(round(d['t'] - (t_ref or 0), 3))
        if d.get('status', 200) == 200:
            acc.setdefault(d['amount'], []).append(round(d['t'] - (t_ref or 0), 3))
    delivered = [{'amount': a, 't': ts[0], 'times': ts, 'count': len(ts)} for a, ts in sorted(acc.items())]
    missing = [a for a in expected if a not in acc]
    dup = [a for a, ts in sorted(acc.items()) if len(ts) > 1]
    unexpected = [a for a in sorted(acc) if a not in expected]
    return {'expected': expected, 'delivered': delivered, 'missing': missing, 'duplicated': dup,
            'unexpected': unexpected, 'retractions': retractions or [],
            'attempts_incl_failed': {str(a): ts for a, ts in sorted(att.items())}}
