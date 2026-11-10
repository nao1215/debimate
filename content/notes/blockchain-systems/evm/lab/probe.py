#!/usr/bin/env python3
"""Probe the EVM on a local Anvil node pinned to Osaka.

Local-only. Called by run.sh inside a container on a private Docker network.
Hand-assembled bytecode and the Solidity files are educational and not audited.
"""
import hashlib
import json
import os
from pathlib import Path
import time
import urllib.request

NODE = os.environ['NODE']
OUT = Path('output')
BUILD = json.loads((OUT / 'build' / 'combined.json').read_text())['contracts']
lines = []
record = {}


class RpcError(Exception):
    pass


def rpc(method, *params):
    body = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params}).encode()
    request = urllib.request.Request(f'http://{NODE}:8545', body, {'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=20) as response:
        result = json.load(response)
    if 'error' in result:
        raise RpcError(result['error']['message'])
    return result['result']


def wait_ready():
    for _ in range(200):
        try:
            return rpc('eth_accounts')
        except OSError:
            time.sleep(0.1)
    raise TimeoutError(NODE)


def send(tx):
    tx = {'gas': hex(3_000_000), **tx}
    txhash = rpc('eth_sendTransaction', tx)
    for _ in range(100):
        receipt = rpc('eth_getTransactionReceipt', txhash)
        if receipt:
            return receipt
        time.sleep(0.05)
    raise TimeoutError(txhash)


def call(data, to=None, gas=10_000_000):
    tx = {'data': '0x' + data, 'gas': hex(gas)}
    if to:
        tx['to'] = to
    return rpc('eth_call', tx, 'latest')[2:]


def words(raw):
    return [int(raw[i:i + 64], 16) for i in range(0, len(raw), 64)]


def contract(name):
    return next(v for k, v in BUILD.items() if k.endswith(':' + name))


def deploy(me, initcode):
    receipt = send({'from': me, 'data': '0x' + initcode})
    assert int(receipt['status'], 16) == 1
    return receipt['contractAddress']


def initcode_for(runtime):
    """Init code that copies `runtime` (hex) into memory and returns it as the deployed code."""
    n = len(runtime) // 2
    assert n < 256
    return f'60{n:02x}600c600039{"60%02x" % n}6000f3' + runtime


def word(x):
    return f'{x:064x}'


def addr_word(a):
    return a[2:].lower().rjust(64, '0')


me, other = wait_ready()

# 1. Memory expansion: GAS, MLOAD(off), POP, GAS, MLOAD(off), POP, GAS.
#    Each gap = PUSH3(3) + MLOAD(3) + POP(2) + GAS(2) = 10, plus memory expansion.
def c_mem(size):
    a = (size + 31) // 32
    return 3 * a + a * a // 512


lines.append('== memory expansion (MLOAD at the last word of `size` bytes) ==')
lines.append('size_bytes | 1st MLOAD extra | 2nd MLOAD extra | formula 3a + a*a//512')
record['memory'] = []
for size in (32, 1024, 32768, 131072):
    off = f'{size - 32:06x}'
    code = ('5a' f'62{off}' '51' '50' '5a' f'62{off}' '51' '50' '5a'
            '604052' '602052' '600052' '60606000f3')
    g0, g1, g2 = words(call(code))
    first, second = g0 - g1 - 10, g1 - g2 - 10
    assert first == c_mem(size) and second == 0
    record['memory'].append({'size': size, 'measured': first, 'formula': c_mem(size)})
    lines.append(f'{size:>10} | {first:>15} | {second:>15} | {c_mem(size)}')

# 2. The 63/64 rule. The callee returns GAS at its entry (GAS costs 2, so entry = value + 2).
callee = deploy(me, initcode_for('5a5f5260205ff3'))  # GAS PUSH0 MSTORE PUSH1 32 PUSH0 RETURN
lines.append('')
lines.append('== CALL forwards at most g - floor(g/64) (g = gas left after the CALL costs) ==')
lines.append('request  | gas before CALL | CALL costs | callee entry | 63/64 limit')
record['call_gas'] = []
for label, gas_arg, push_cost in (('all', '5a', 2), ('10000', '612710', 3)):
    # GAS; PUSH1 32; PUSH0 x4; PUSH20 callee; <gas arg>; CALL; POP; MSTORE(32, first GAS); RETURN(0, 64)
    code = '5a' '6020' '5f5f5f5f' '73' + callee[2:].lower() + gas_arg + 'f1' '50' '602052' '60405ff3'
    ret, g0 = words(call(code))
    before = g0 - (3 + 2 * 4 + 3 + push_cost)   # gas available when CALL starts
    costs = 2600 + 3                             # cold account access + 1 word of memory for the return data
    limit = (before - costs) - (before - costs) // 64
    entry = ret + 2
    requested = before - costs if label == 'all' else 10000
    assert entry == min(requested, limit)
    record['call_gas'].append({'request': label, 'before': before, 'entry': entry, 'limit': limit})
    lines.append(f'{label:<8} | {before:>15} | {costs:>10} | {entry:>12} | {limit}')

# 3. Gas left at the entry of the deepest frame of down(d) (Solidity, this.down(d - 1)).
deep = deploy(me, contract('Deep')['bin'])
sel = contract('Deep')['hashes']['down(uint256)']
g = [words(call(sel + word(d), deep))[0] for d in range(0, 41)]
record['depth'] = g
lines.append('')
lines.append('== gasleft() at the entry of the deepest frame (eth_call gas 10,000,000) ==')
lines.append('depth | gasleft  | ratio to one level up')
for d in (0, 1, 2, 3, 10, 20, 30, 40):
    ratio = '' if d == 0 else f'{g[d] / g[d - 1]:.4f}'
    lines.append(f'{d:>5} | {g[d]:>8} | {ratio}')
lo, hi = 0, 1024
while lo < hi:  # deepest d for which down(d) still succeeds with 10M gas
    mid = (lo + hi + 1) // 2
    try:
        call(sel + word(mid), deep)
        lo = mid
    except RpcError:
        hi = mid - 1
record['max_depth'] = lo
record['max_depth_gas'] = words(call(sel + word(lo), deep))[0]
lines.append(f'deepest down() that succeeds with 10,000,000 gas: {lo} (gasleft there: {record["max_depth_gas"]})')

# 4. CALL / DELEGATECALL / STATICCALL from the same Caller to the same Target.
target = deploy(me, contract('Target')['bin'])
caller = deploy(me, contract('Caller')['bin'])
receipt = send({'from': me, 'to': caller, 'value': hex(7),
                'data': '0x' + contract('Caller')['hashes']['run(address)'] + addr_word(target)})
assert int(receipt['status'], 16) == 1
names = {me.lower(): 'EOA', caller.lower(): 'Caller', target.lower(): 'Target',
         '0x' + '0' * 40: '-'}
lines.append('')
lines.append('== Caller.run(target) sent by the EOA with 7 wei ==')
lines.append('mode                | ok | msg.sender | address(this) | msg.value')
record['context'] = []
for log in receipt['logs']:
    w = words(log['data'][2:])
    off, ok, sender, self_, value = w[0], w[1], w[2], w[3], w[4]
    n = w[off // 32]
    mode = bytes.fromhex(log['data'][2:][(off + 32) * 2:(off + 32 + n) * 2]).decode()
    s, t = names['0x' + f'{sender:040x}'], names['0x' + f'{self_:040x}']
    record['context'].append({'mode': mode, 'ok': ok, 'sender': s, 'self': t, 'value': value})
    lines.append(f'{mode:<19} | {ok:<2} | {s:<10} | {t:<13} | {value}')
count = contract('Target')['hashes']['count()']
counts = {n: words(call(count, a))[0] for n, a in (('Caller', caller), ('Target', target))}
balances = {n: int(rpc('eth_getBalance', a, 'latest'), 16) for n, a in (('Caller', caller), ('Target', target))}
record['counts'], record['balances'] = counts, balances
lines.append('storage slot 0 (count) after: ' + ', '.join(f'{k}={v}' for k, v in counts.items()))
lines.append('balance after (wei): ' + ', '.join(f'{k}={v}' for k, v in balances.items()))

# 5. The dispatcher: calldata, executed opcodes, and the gas of each transaction.
disp = deploy(me, contract('Dispatcher')['bin'])
set_sel = contract('Dispatcher')['hashes']['set(uint256)']
record['getter_selector'] = contract('Dispatcher')['hashes']['value()']


def intrinsic(data_hex):
    b = bytes.fromhex(data_hex)
    zeros = b.count(0)
    nonzero = len(b) - zeros
    return 21000 + 4 * zeros + 16 * nonzero, 21000 + 10 * (zeros + 4 * nonzero)


lines.append('')
lines.append('== Dispatcher.set(x): calldata and the gas of each transaction ==')
record['dispatcher'] = []
for x in (42, 43, 0):
    data = set_sel + word(x)
    receipt = send({'from': me, 'to': disp, 'data': '0x' + data})
    trace = rpc('debug_traceTransaction', receipt['transactionHash'], {'disableStorage': True})
    steps = trace['structLogs']
    execution = sum(s['gasCost'] for s in steps)
    by_op = {}
    for s in steps:
        by_op[s['op']] = by_op.get(s['op'], 0) + s['gasCost']
    base, floor = intrinsic(data)
    used = int(receipt['gasUsed'], 16)
    refund = base + execution - used
    item = {'x': x, 'calldata': data, 'intrinsic': base, 'floor': floor, 'execution': execution,
            'sstore': by_op.get('SSTORE', 0), 'log': by_op.get('LOG2', 0), 'gas_used': used,
            'refund': refund, 'steps': len(steps)}
    record['dispatcher'].append(item)
    if x == 42:
        lines.append('calldata of set(42): ' + data[:8] + ' ' + data[8:])
        assert receipt['logs'][0]['topics'][0] == os.environ['TOPIC0']
        lines.append('topic0 of Changed: ' + receipt['logs'][0]['topics'][0])
        lines.append('first executed opcodes (pc op gasCost):')
        for s in steps[:30]:
            lines.append(f'  {s["pc"]:>3} {s["op"]:<12} {s["gasCost"]}')
        record['trace_head'] = [[s['pc'], s['op'], s['gasCost']] for s in steps[:30]]
    lines.append(f'set({x}): intrinsic={base} floor={floor} execution={execution} '
                 f'(SSTORE={item["sstore"]} LOG2={item["log"]}) refund={refund} gasUsed={used}')
bad = send({'from': me, 'to': disp, 'data': '0xdeadbeef'})
record['unknown_selector_status'] = int(bad['status'], 16)
lines.append(f'unknown selector 0xdeadbeef: status={int(bad["status"], 16)}')

# 6. Precompiles: SHA-256 (0x02), ecrecover (0x01) and P-256 verification (0x100, Osaka).
lines.append('')
lines.append('== precompiles called with eth_call ==')
msg = b'abc'
out = call(msg.hex(), '0x' + '0' * 38 + '02')
assert out == hashlib.sha256(msg).hexdigest()
lines.append(f'0x02 sha256("abc") = {out[:16]}... matches hashlib: True')
h, sig = os.environ['MSG_HASH'][2:], os.environ['SIG'][2:]
r, s, v = sig[:64], sig[64:128], int(sig[128:130], 16)
out = call(h + word(v) + r + s, '0x' + '0' * 38 + '01')
assert out[24:] == me[2:].lower()
lines.append(f'0x01 ecrecover(hash, v={v}, r, s) = 0x{out[24:]} (the signing test account)')

# Minimal ECDSA over P-256 for the 0x100 input (educational, fixed k, never use for real keys).
P = 0xffffffff00000001000000000000000000000000ffffffffffffffffffffffff
N = 0xffffffff00000000ffffffffffffffffbce6faada7179e84f3b9cac2fc632551
A = P - 3
G = (0x6b17d1f2e12c4247f8bce6e563a440f277037d812deb33a0f4a13945d898c296,
     0x4fe342e2fe1a7f9b8ee7eb4a7c0f9e162bce33576b315ececbb6406837bf51f5)


def add(p1, p2):
    if p1 is None:
        return p2
    if p2 is None:
        return p1
    if p1[0] == p2[0] and (p1[1] + p2[1]) % P == 0:
        return None
    if p1 == p2:
        m = (3 * p1[0] * p1[0] + A) * pow(2 * p1[1], -1, P) % P
    else:
        m = (p2[1] - p1[1]) * pow(p2[0] - p1[0], -1, P) % P
    x = (m * m - p1[0] - p2[0]) % P
    return x, (m * (p1[0] - x) - p1[1]) % P


def mul(k, pt):
    acc = None
    while k:
        if k & 1:
            acc = add(acc, pt)
        pt, k = add(pt, pt), k >> 1
    return acc


d, k = 0x1234567, 0x7654321
qx, qy = mul(d, G)
z = int(hashlib.sha256(b'evm note').hexdigest(), 16)
r256 = mul(k, G)[0] % N
s256 = pow(k, -1, N) * (z + r256 * d) % N
good = f'{z:064x}{r256:064x}{s256:064x}{qx:064x}{qy:064x}'
bad = f'{z ^ 1:064x}{r256:064x}{s256:064x}{qx:064x}{qy:064x}'
p256 = '0x' + '0' * 37 + '100'
ok_out, bad_out = call(good, p256), call(bad, p256)
assert ok_out == word(1) and bad_out == ''
record['p256'] = {'valid': ok_out, 'tampered': bad_out}
lines.append(f'0x100 p256verify(valid signature) = 0x{ok_out[-2:]} (32 bytes), tampered hash = 0x{bad_out}')

summary = '\n'.join(lines) + '\n'
(OUT / 'summary.txt').write_text(summary)
(OUT / 'probe.json').write_text(json.dumps(record, indent=2) + '\n')
print(summary, end='')
