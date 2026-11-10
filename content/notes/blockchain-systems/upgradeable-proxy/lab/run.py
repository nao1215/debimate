#!/usr/bin/env python3
"""Local-only upgradeable proxy experiment. Run through run.sh.

Starts its own loopback-only Anvil (Prague) and stops it on exit.
Accounts are Anvil's public test accounts only. No external RPC is used.
"""
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import time
import urllib.request

from slots import erc1967, erc7201

HERE = Path(__file__).resolve().parent
OUT = HERE / 'output'
OUT.mkdir(exist_ok=True)
TOOLS = {n: os.environ.get(n.upper(), shutil.which(n)) for n in ('anvil', 'cast')}
if not all(TOOLS.values()):
    raise SystemExit('Put anvil and cast on PATH (or set ANVIL, CAST).')
BUILD = json.loads(Path(os.environ['BUILD']).read_text())['contracts']
lines = []


def log(s=''):
    print(s)
    lines.append(s)


def cast(*args, check=True):
    p = subprocess.run([TOOLS['cast'], *map(str, args)], text=True, capture_output=True)
    if check and p.returncode:
        raise RuntimeError(p.stderr)
    return p.stdout.strip() if not p.returncode else 'REVERT ' + p.stderr.strip().splitlines()[-1]


def artifact(name):
    return next(v for k, v in BUILD.items() if k.endswith(':' + name))


with socket.socket() as s:
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
URL = f'http://127.0.0.1:{port}'


def rpc(method, *params):
    body = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params}).encode()
    req = urllib.request.Request(URL, body, {'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=10) as r:
        res = json.load(r)
    if 'error' in res:
        raise RuntimeError(res['error'])
    return res['result']


def send(sender, data, to=None, ok=True):
    tx = {'from': sender, 'data': data, 'gas': hex(3_000_000)}
    if to:
        tx['to'] = to
    h = rpc('eth_sendTransaction', tx)
    for _ in range(200):
        r = rpc('eth_getTransactionReceipt', h)
        if r:
            assert (int(r['status'], 16) == 1) == ok, r
            return r
        time.sleep(0.05)
    raise TimeoutError(h)


def deploy(sender, name, ctor_sig=None, *args):
    code = '0x' + artifact(name)['bin']
    if ctor_sig:
        code += cast('abi-encode', ctor_sig, *args)[2:]
    return send(sender, code)['contractAddress']


def tx(sender, to, sig, *args, ok=True):
    return send(sender, cast('calldata', sig, *args), to, ok)


ERRORS = ('UUPSUnauthorizedCallContext()', 'InvalidInitialization()')


def call(to, sig, *args):
    out = cast('call', '--rpc-url', URL, to, sig, *args, check=False)
    for e in ERRORS:
        if out.startswith('REVERT') and cast('sig', e) in out:
            return 'revert ' + e
    return out


def storage(addr, slot):
    return cast('storage', '--rpc-url', URL, addr, slot)


def word(v):
    return '0x' + v[2:].rjust(64, '0') if isinstance(v, str) else '0x' + f'{v:064x}'


anvil = subprocess.Popen([TOOLS['anvil'], '--host', '127.0.0.1', '--port', str(port),
                          '--hardfork', 'prague', '--silent'])
try:
    for _ in range(100):
        try:
            rpc('eth_chainId')
            break
        except OSError:
            time.sleep(0.1)
    admin, alice, mallory = rpc('eth_accounts')[:3]   # Anvil test accounts 0, 1, 2

    log('== 1. naive proxy: implementation address in slot 0 ==')
    counter = deploy(admin, 'CounterV1')
    naive = deploy(admin, 'NaiveProxy', 'f(address)', counter)
    before = storage(naive, 0)
    assert before == word(counter.lower())
    tx(alice, naive, 'increment()')
    after = storage(naive, 0)
    assert int(after, 16) == int(counter, 16) + 1
    log(f'slot 0 before increment(): {before}')
    log(f'slot 0 after  increment(): {after}')
    raw = rpc('eth_call', {'to': naive, 'data': cast('sig', 'count()')}, 'latest')
    log(f'count() through the proxy now returns: {raw!r} (delegates to an address without code)')
    assert raw == '0x'

    log()
    log('== 2. ERC-1967 slots: Python vs constants in the spec and OpenZeppelin ==')
    impl_slot, admin_slot = erc1967('eip1967.proxy.implementation'), erc1967('eip1967.proxy.admin')
    log(f'implementation  {impl_slot}')
    log(f'admin           {admin_slot}')
    assert impl_slot == '0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'
    assert admin_slot == '0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103'
    v1 = deploy(admin, 'VaultV1')
    proxy = deploy(admin, 'StudyProxy', 'f(address)', v1)
    assert storage(proxy, impl_slot) == word(v1.lower())
    assert storage(proxy, admin_slot) == word(admin.lower())
    assert cast('implementation', '--rpc-url', URL, proxy).lower() == v1.lower()
    assert cast('admin', '--rpc-url', URL, proxy).lower() == admin.lower()
    log('cast storage / cast implementation / cast admin agree with the computed slots')

    log()
    log('== 3. layout shift on upgrade ==')
    tx(alice, proxy, 'setUp(address,uint256)', alice, 100)
    s0, s1 = storage(proxy, 0), storage(proxy, 1)
    log(f'V1      owner()={call(proxy, "owner()(address)")} balance()={call(proxy, "balance()(uint256)")}')
    log(f'        slot 0={s0}')
    log(f'        slot 1={s1}')
    bad, good = deploy(admin, 'VaultV2Bad'), deploy(admin, 'VaultV2Good')
    r = tx(admin, proxy, 'upgradeTo(address)', bad)
    upgraded = cast('keccak', 'Upgraded(address)')
    assert r['logs'][0]['topics'] == [upgraded, word(bad.lower())]
    log(f'Upgraded(address) topic0={upgraded}')
    log(f'V2Bad   owner()={call(proxy, "owner()(address)")} balance()={call(proxy, "balance()(uint256)")}')
    log(f'        fee()={call(proxy, "fee()(uint256)")}')
    assert storage(proxy, 0) == s0 and storage(proxy, 1) == s1
    log('        slot 0 and slot 1 are unchanged; only the meaning of each slot changed')
    tx(alice, proxy, 'setFee(uint256)', 5)
    tx(admin, proxy, 'upgradeTo(address)', good)
    log(f'V2Good  owner()={call(proxy, "owner()(address)")} balance()={call(proxy, "balance()(uint256)")}'
        ' (after setFee(5) under V2Bad)')
    assert int(storage(proxy, 0), 16) == 5

    log()
    log('== 4. constructor writes to the implementation, not the proxy ==')
    box = deploy(admin, 'CtorBox')
    p2 = deploy(admin, 'StudyProxy', 'f(address)', box)
    log(f'implementation value()={call(box, "value()(uint256)")}  proxy value()={call(p2, "value()(uint256)")}')

    log()
    log('== 5. ERC-7201 namespace ==')
    loc = erc7201('debimate.vault')
    log(f'erc7201:debimate.vault  {loc}')
    ns = deploy(admin, 'NamespacedVault')
    p3 = deploy(admin, 'StudyProxy', 'f(address)', ns)
    tx(alice, p3, 'setUp(address,uint256)', alice, 100)
    assert storage(p3, loc) == word(alice.lower())
    assert int(storage(p3, hex(int(loc, 16) + 1)), 16) == 100
    assert int(storage(p3, 0), 16) == 0
    log(f'slot {loc[:10]}..00 = owner, ..01 = balance 100, slot 0 = 0')
    layout = {n: [(v['label'], int(v['slot'])) for v in artifact(n)['storage-layout']['storage']]
              for n in ('PlainAB', 'PlainBA', 'BoxOpen')}
    for n, v in layout.items():
        log(f'solc storage layout {n:<8} {v}')

    log()
    log('== 6. uninitialized implementation (OpenZeppelin v5.7.0) ==')
    own_slot = erc7201('openzeppelin.storage.Ownable')
    init_slot = erc7201('openzeppelin.storage.Initializable')
    impl = deploy(admin, 'BoxOpen')
    init = cast('calldata', 'initialize(address)', alice)
    oz_proxy = deploy(admin, 'ERC1967Proxy', 'f(address,bytes)', impl, init)
    assert storage(oz_proxy, own_slot) == word(alice.lower())
    log(f'proxy owner()={call(oz_proxy, "owner()(address)")} (alice); impl owner()={call(impl, "owner()(address)")}')
    tx(mallory, impl, 'initialize(address)', mallory)
    log(f'mallory calls impl.initialize(mallory): impl owner()={call(impl, "owner()(address)")}')
    assert storage(impl, own_slot) == word(mallory.lower())
    r = tx(mallory, impl, 'upgradeToAndCall(address,bytes)', impl, '0x', ok=False)
    reason = call(impl, 'upgradeToAndCall(address,bytes)', impl, '0x', '--from', mallory)
    log(f'mallory calls impl.upgradeToAndCall directly: status={int(r["status"], 16)} {reason}')
    log(f'proxy owner() is still {call(oz_proxy, "owner()(address)")}')
    locked = deploy(admin, 'BoxLocked')
    r = tx(mallory, locked, 'initialize(address)', mallory, ok=False)
    log(f'BoxLocked.initialize by mallory: status={int(r["status"], 16)} {call(locked, "initialize(address)", mallory, "--from", mallory)}')
    log(f'BoxLocked Initializable slot = {storage(locked, init_slot)}')
    assert int(storage(locked, init_slot), 16) == 2**64 - 1

    log()
    log('Assertions: PASS')
    (OUT / 'summary.txt').write_text('\n'.join(lines) + '\n')
    (OUT / 'versions.txt').write_text(
        subprocess.check_output([TOOLS['anvil'], '--version'], text=True).splitlines()[0] + '\n')
finally:
    anvil.terminate()
    anvil.wait()
