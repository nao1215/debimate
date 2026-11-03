"""Two isolated regtest nodes; no public peers or real wallet data.
Set BITCOIND to a Bitcoin Core executable. Python 3 standard library only.
"""
import base64
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request

binary = os.environ.get('BITCOIND', shutil.which('bitcoind'))
if not binary:
    raise SystemExit('Set BITCOIND or put bitcoind on PATH')
root = Path(__file__).resolve().parent
out = root / 'output'
out.mkdir(exist_ok=True)
(out / 'versions.txt').write_text(subprocess.check_output([binary, '--version'], text=True))

class Node:
    def __init__(self, path, fee):
        self.path = path
        path.mkdir()
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            self.port = sock.getsockname()[1]
        self.log = (path / 'console.log').open('w')
        self.process = subprocess.Popen([binary, f'-datadir={path}', '-regtest', '-server',
            '-listen=0', '-connect=0', '-dnsseed=0', '-discover=0', '-natpmp=0',
            '-rpcbind=127.0.0.1', '-rpcallowip=127.0.0.1', f'-rpcport={self.port}',
            f'-minrelaytxfee={fee}', '-blockmintxfee=0.00001', '-fallbackfee=0.00002'],
            stdout=self.log, stderr=self.log)

    def rpc(self, method, *params, wallet=False):
        cookie = (self.path / 'regtest' / '.cookie').read_text().strip()
        auth = base64.b64encode(cookie.encode()).decode()
        url = f'http://127.0.0.1:{self.port}' + ('/wallet/lab' if wallet else '')
        req = urllib.request.Request(url, json.dumps({'jsonrpc': '2.0', 'id': 1,
            'method': method, 'params': params}).encode(),
            {'Content-Type': 'application/json', 'Authorization': f'Basic {auth}'})
        try:
            response = urllib.request.urlopen(req, timeout=20)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            payload = json.load(response)
        if payload.get('error'):
            raise RuntimeError(payload['error'])
        return payload['result']

    def ready(self):
        for _ in range(200):
            if self.process.poll() is not None:
                raise RuntimeError((self.path / 'console.log').read_text())
            try:
                self.rpc('getblockcount')
                return
            except (OSError, RuntimeError):
                time.sleep(0.05)
        raise TimeoutError('node startup')

    def close(self):
        self.process.terminate()
        try:
            self.process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait()
        self.log.close()

nodes = []
with tempfile.TemporaryDirectory(prefix='debimate-mempool-') as directory:
    try:
        a = Node(Path(directory) / 'a', '0.00001'); nodes.append(a)
        b = Node(Path(directory) / 'b', '0.00010'); nodes.append(b)
        a.ready(); b.ready()
        a.rpc('createwallet', 'lab')
        address = a.rpc('getnewaddress', wallet=True)
        blocks = a.rpc('generatetoaddress', 101, address)
        for block in blocks:
            assert b.rpc('submitblock', a.rpc('getblock', block, 0)) is None
        assert a.rpc('getbestblockhash') == b.rpc('getbestblockhash')
        recipient = a.rpc('getnewaddress', wallet=True)
        raw = a.rpc('createrawtransaction', [], {recipient: 1})
        funded = a.rpc('fundrawtransaction', raw, {'fee_rate': 2}, wallet=True)
        signed = a.rpc('signrawtransactionwithwallet', funded['hex'], wallet=True)
        assert signed['complete']
        checks = {}
        for name, node in [('A', a), ('B', b)]:
            checks[name] = node.rpc('testmempoolaccept', [signed['hex']])[0]
            (out / f'accept-{name}.json').write_text(json.dumps(checks[name], indent=2) + '\n')
        assert checks['A']['allowed'] and not checks['B']['allowed']
        assert checks['B']['reject-reason'] == 'min relay fee not met'
        assert a.rpc('getrawmempool') == [] and b.rpc('getrawmempool') == []
        txid = a.rpc('sendrawtransaction', signed['hex'])
        assert a.rpc('getrawmempool') == [txid] and b.rpc('getrawmempool') == []
        new_block = a.rpc('generatetoaddress', 1, address)[0]
        decoded = a.rpc('getblock', new_block)
        assert txid in decoded['tx']
        assert b.rpc('submitblock', a.rpc('getblock', new_block, 0)) is None
        assert a.rpc('getbestblockhash') == b.rpc('getbestblockhash') == new_block
        assert txid in b.rpc('getblock', new_block)['tx']
        (out / 'block-B.json').write_text(json.dumps(b.rpc('getblock', new_block), indent=2) + '\n')
        summary = '\n'.join([
            'A minrelaytxfee: 1 sat/vB', 'B minrelaytxfee: 10 sat/vB',
            'transaction fee_rate: 2 sat/vB',
            'testmempoolaccept A: allowed=true',
            'testmempoolaccept B: allowed=false; min relay fee not met',
            'after preflight: mempool A=0 B=0',
            'after send to A: mempool A=1 B=0',
            'after mining on A and submitting block to B: same_tip=true',
            'B block contains transaction: true', 'Assertions: PASS', ''])
        (out / 'summary.txt').write_text(summary)
        print(summary, end='')
    finally:
        for node in reversed(nodes):
            node.close()
