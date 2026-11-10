#!/usr/bin/env python3
"""Local-only ERC-721 experiment. Requires Python 3, Anvil, cast and solc 0.8.28.

It starts its own loopback-only Anvil and a loopback HTTP server for the
metadata JSON, and stops both on exit. No external RPC or real key is used.
"""
import functools
import http.server
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.request

LAB = Path(__file__).resolve().parent
OUT = LAB / 'output'
WWW = Path(tempfile.mkdtemp(prefix='erc721-www-'))  # metadata server root, removed on exit
TOOLS = {n: os.environ.get(n.upper(), shutil.which(n)) for n in ('anvil', 'cast', 'solc')}
if not all(TOOLS.values()):
    raise SystemExit('Put anvil, cast and solc on PATH (or set ANVIL, CAST, SOLC).')


def cli(name, *args):
    return subprocess.check_output([TOOLS[name], *args], text=True).strip()


def free_port():
    # Select a free loopback port; fail if another process takes it first.
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


shutil.rmtree(OUT, ignore_errors=True)
OUT.mkdir()
(OUT / 'versions.txt').write_text('\n'.join(cli(n, '--version') for n in TOOLS) + '\n')
compiled = json.loads(cli('solc', '--evm-version', 'cancun', '--combined-json', 'abi,bin',
                          str(LAB / 'StudyNFT.sol'), str(LAB / 'Receivers.sol')))
BIN = {k.split(':')[1]: v['bin'] for k, v in compiled['contracts'].items()}
RPC = f'http://127.0.0.1:{free_port()}'
WEB_PORT = free_port()
WEB = f'http://127.0.0.1:{WEB_PORT}'


def rpc(method, *params):
    body = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params}).encode()
    req = urllib.request.Request(RPC, body, {'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=5) as res:
        result = json.load(res)
    if 'error' in result:
        raise RuntimeError(result['error'])
    return result['result']


def data(signature, *args):
    return cli('cast', 'calldata', signature, *map(str, args))


def send(label, sender, payload, to=None):
    """Send a transaction, save its receipt and return (status, revert reason)."""
    tx = {'from': sender, 'data': payload, 'gas': hex(3000000), 'gasPrice': hex(2000000000)}
    reason = ''
    if to:
        tx['to'] = to
        try:
            rpc('eth_call', tx, 'latest')
        except RuntimeError as e:
            reason = e.args[0].get('message', '')
    txhash = rpc('eth_sendTransaction', tx)
    for _ in range(100):
        receipt = rpc('eth_getTransactionReceipt', txhash)
        if receipt:
            (OUT / f'{label}.json').write_text(json.dumps(receipt, indent=2) + '\n')
            return receipt, reason
        time.sleep(0.05)
    raise TimeoutError(txhash)


def call(to, signature, *args):
    return rpc('eth_call', {'to': to, 'data': data(signature, *args)}, 'latest')


def word_addr(word):
    return '0x' + word[-40:]


def fetch(url):
    try:
        with urllib.request.urlopen(url, timeout=5) as res:
            return json.load(res)
    except urllib.error.HTTPError as e:
        return f'HTTP {e.code}'


def put(path, name, image):
    file = WWW / path
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(json.dumps({'name': name, 'image': f'{WEB}/img/{image}'}) + '\n')


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def main():
    web = http.server.ThreadingHTTPServer(
        ('127.0.0.1', WEB_PORT), functools.partial(QuietHandler, directory=str(WWW)))
    threading.Thread(target=web.serve_forever, daemon=True).start()
    log = (OUT / 'node.log').open('w')
    node = subprocess.Popen([TOOLS['anvil'], '--host', '127.0.0.1', '--port', RPC.rsplit(':', 1)[1],
                             '--chain-id', '31337', '--hardfork', 'cancun',
                             '--timestamp', '1700000000', '--accounts', '4', '--quiet'],
                            stdout=log, stderr=log)
    try:
        for _ in range(100):
            if node.poll() is not None:
                raise RuntimeError('Anvil exited; inspect output/node.log')
            try:
                accounts = rpc('eth_accounts')
                break
            except (OSError, RuntimeError):
                time.sleep(0.05)
        else:
            raise TimeoutError('Anvil startup')
        experiment(accounts)
    finally:
        node.terminate()
        try:
            node.wait(timeout=5)
        except subprocess.TimeoutExpired:
            node.kill()
            node.wait()
        log.close()
        web.shutdown()
        shutil.rmtree(WWW, ignore_errors=True)


def experiment(accounts):
    alice, bob, carol, keeper = accounts[:4]
    deploy = {}
    for name, sender, args in [('StudyNFT', alice, cli('cast', 'abi-encode', 'f(string)', f'{WEB}/v1/')),
                               ('Counter', alice, '0x'), ('StudyReceiver', keeper, '0x')]:
        receipt, _ = send(f'deploy-{name}', sender, '0x' + BIN[name] + args[2:])
        assert int(receipt['status'], 16) == 1
        deploy[name] = receipt['contractAddress']
    nft, counter, receiver = deploy['StudyNFT'], deploy['Counter'], deploy['StudyReceiver']
    names = {alice: 'alice', bob: 'bob', carol: 'carol', keeper: 'keeper',
             nft: 'nft', counter: 'Counter', receiver: 'StudyReceiver',
             '0x' + '0' * 40: 'zero'}
    lines = []

    # The experiment itself (shown in the note). ------------------------------
    TRANSFER = cli('cast', 'keccak', 'Transfer(address,address,uint256)')
    APPROVAL_FOR_ALL = cli('cast', 'keccak', 'ApprovalForAll(address,address,bool)')

    def owner(token):
        try:
            return names[word_addr(call(nft, 'ownerOf(uint256)', token))]
        except RuntimeError:
            return 'none'

    def balance(who):
        return int(call(nft, 'balanceOf(address)', who), 16)

    def events(receipt):
        out = []
        for log in receipt['logs']:
            t = log['topics']
            if t[0] == TRANSFER:
                out.append(f'Transfer({names[word_addr(t[1])]}->{names[word_addr(t[2])]}, '
                           f'id={int(t[3], 16)}) topics={len(t)} data={log["data"]}')
            elif t[0] == APPROVAL_FOR_ALL:
                out.append(f'ApprovalForAll({names[word_addr(t[1])]}, {names[word_addr(t[2])]}, '
                           f'{bool(int(log["data"], 16))})')
            else:
                out.append(f'Approval({names[word_addr(t[1])]}, {names[word_addr(t[2])]}, '
                           f'id={int(t[3], 16)})')
        return '; '.join(out) or 'no event'

    def step(label, sender, signature, *args, ok):
        receipt, reason = send(f'step-{len(lines):02d}', sender, data(signature, *args), nft)
        status = int(receipt['status'], 16)
        assert status == ok, (label, reason)
        detail = events(receipt) if status else reason
        lines.append(f'{label} | {names[sender]} | status={status} | {detail}')

    lines.append('== 1. mint and ownerOf')
    for token in (1, 2, 3):
        step(f'mint #{token} to alice', alice, 'mint(address,uint256)', alice, token, ok=1)
    assert [owner(t) for t in (1, 2, 3)] == ['alice'] * 3 and balance(alice) == 3
    lines.append(f'ownerOf(1..3)={[owner(t) for t in (1, 2, 3)]} balanceOf(alice)={balance(alice)}')
    lines.append(f'Transfer topic0 = {TRANSFER} (same as ERC-20)')
    ids = {'ERC165': '0x01ffc9a7', 'ERC721': '0x80ac58cd', 'Metadata': '0x5b5e139f',
           'Enumerable': '0x780e9d63', 'invalid': '0xffffffff'}
    support = {k: int(call(nft, 'supportsInterface(bytes4)', v), 16) == 1 for k, v in ids.items()}
    assert support == {'ERC165': True, 'ERC721': True, 'Metadata': True,
                       'Enumerable': False, 'invalid': False}
    lines.append(f'supportsInterface: {support}')

    lines.append('== 2. transfer to contracts')
    step('safeTransferFrom #1 -> Counter', alice,
         'safeTransferFrom(address,address,uint256)', alice, counter, 1, ok=0)
    step('safeTransferFrom #2 -> StudyReceiver', alice,
         'safeTransferFrom(address,address,uint256)', alice, receiver, 2, ok=1)
    step('transferFrom #1 -> Counter', alice,
         'transferFrom(address,address,uint256)', alice, counter, 1, ok=1)
    step('alice pulls #1 back from Counter', alice,
         'transferFrom(address,address,uint256)', counter, alice, 1, ok=0)
    step('alice approves herself for #1', alice, 'approve(address,uint256)', alice, 1, ok=0)
    receipt, _ = send(f'step-{len(lines):02d}', keeper,
                      data('withdraw(address,address,uint256)', nft, alice, 2), receiver)
    assert int(receipt['status'], 16) == 1
    lines.append(f'StudyReceiver.withdraw #2 -> alice | keeper | status=1 | {events(receipt)}')
    assert owner(1) == 'Counter' and owner(2) == 'alice'
    lines.append(f'ownerOf(1)={owner(1)} ownerOf(2)={owner(2)}')

    lines.append('== 3. approve vs setApprovalForAll')
    step('mint #4 to alice', alice, 'mint(address,uint256)', alice, 4, ok=1)
    step('approve carol for #3', alice, 'approve(address,uint256)', carol, 3, ok=1)
    step('carol moves #4', carol, 'transferFrom(address,address,uint256)', alice, carol, 4, ok=0)
    step('carol moves #3', carol, 'transferFrom(address,address,uint256)', alice, carol, 3, ok=1)
    lines.append(f'getApproved(3)={names[word_addr(call(nft, "getApproved(uint256)", 3))]} after the transfer')
    step('setApprovalForAll(bob, true)', alice, 'setApprovalForAll(address,bool)', bob, 'true', ok=1)
    step('bob moves #2', bob, 'transferFrom(address,address,uint256)', alice, bob, 2, ok=1)
    step('bob moves #4', bob, 'transferFrom(address,address,uint256)', alice, bob, 4, ok=1)
    step('mint #5 to alice (after the approval)', alice, 'mint(address,uint256)', alice, 5, ok=1)
    step('bob moves #5', bob, 'transferFrom(address,address,uint256)', alice, bob, 5, ok=1)
    step('setApprovalForAll(bob, false)', alice, 'setApprovalForAll(address,bool)', bob, 'false', ok=1)
    step('mint #6 to alice', alice, 'mint(address,uint256)', alice, 6, ok=1)
    step('bob moves #6', bob, 'transferFrom(address,address,uint256)', alice, bob, 6, ok=0)
    held = {who: [t for t in range(1, 7) if owner(t) == who] for who in ('alice', 'bob', 'carol')}
    assert held == {'alice': [6], 'bob': [2, 4, 5], 'carol': [3]}
    lines.append(f'holdings={held}')

    lines.append('== 4. tokenURI and metadata (token #2)')

    def show(label):
        uri = cli('cast', 'abi-decode', 'f()(string)', call(nft, 'tokenURI(uint256)', 2)).strip('"')
        block = int(rpc('eth_blockNumber'), 16)
        lines.append(f'{label} | block={block} owner={owner(2)} | {uri} -> {fetch(uri)}')
        return block

    put('v1/2.json', 'Study NFT #2', 'blue.svg')
    b0 = show('initial')
    put('v1/2.json', 'Study NFT #2', 'red.svg')
    assert show('server edits v1/2.json') == b0
    put('v2/2.json', 'Study NFT #2 (v2)', 'green.svg')
    step('setBaseURI(v2)', alice, 'setBaseURI(string)', f'{WEB}/v2/', ok=1)
    show('after setBaseURI')
    (WWW / 'v2' / '2.json').unlink()
    show('server deletes v2/2.json')
    assert owner(2) == 'bob'
    # -------------------------------------------------------------------------

    lines.append('Assertions: PASS')
    summary = '\n'.join(lines).replace(f':{WEB_PORT}', ':WEB') + '\n'
    (OUT / 'deploy.json').write_text(json.dumps(deploy, indent=2) + '\n')
    (OUT / 'summary.txt').write_text(summary)
    print(summary, end='')


if __name__ == '__main__':
    main()
