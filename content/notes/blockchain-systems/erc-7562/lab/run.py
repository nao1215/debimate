#!/usr/bin/env python3
"""Local-only ERC-7562 experiment (EntryPoint v0.9.0). Run through run.sh.

The script plays a bundler itself. It simulates UserOperations with eth_call,
traces their validation with debug_traceCall, and checks the trace against a
subset of the ERC-7562 rules (check7562 below). No bundler software, no
external RPC. Keys are Anvil's public test mnemonic only.
"""
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import time
import urllib.request

HERE = Path(__file__).resolve().parent
OUT = HERE / 'output'
OUT.mkdir(exist_ok=True)
TOOLS = {n: os.environ.get(n.upper(), shutil.which(n)) for n in ('anvil', 'cast')}
if not all(TOOLS.values()):
    raise SystemExit('Put anvil and cast on PATH (or set ANVIL, CAST).')
BUILD = json.loads(Path(os.environ['BUILD']).read_text())['contracts']
MNEMONIC = 'test test test test test test test test test test test junk'  # Anvil default, public
GWEI = 10**9
ETH = 10**18
OP_TYPE = '(address,uint256,bytes,bytes,bytes32,uint256,bytes32,bytes,bytes)'


def cast(*args):
    return subprocess.check_output([TOOLS['cast'], *map(str, args)], text=True,
                                   stderr=subprocess.DEVNULL).strip()


def artifact(suffix):
    return next(v for k, v in BUILD.items() if k.endswith(suffix))


with socket.socket() as s:
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
URL = f'http://127.0.0.1:{port}'


def rpc(method, *params):
    body = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params}).encode()
    req = urllib.request.Request(URL, body, {'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=60) as r:
        res = json.load(r)
    if 'error' in res:
        raise RuntimeError(res['error'])
    return res['result']


def submit(sender, data, to=None, value=0, gas=15_000_000, price=2 * GWEI):
    # Legacy gasPrice keeps the price fixed, as in the erc-4337 note.
    tx = {'from': sender, 'data': data, 'value': hex(value), 'gas': hex(gas), 'gasPrice': hex(price)}
    if to:
        tx['to'] = to
    return rpc('eth_sendTransaction', tx)


def receipt(h):
    for _ in range(400):
        r = rpc('eth_getTransactionReceipt', h)
        if r:
            return r
        time.sleep(0.05)
    raise TimeoutError(h)


def send(*args, **kw):
    r = receipt(submit(*args, **kw))
    assert int(r['status'], 16) == 1, r
    return r


def deploy(sender, suffix, sig='', *ctor):
    a = artifact(suffix)
    args = cast('abi-encode', f'f({sig})', *ctor)[2:] if ctor else ''
    return send(sender, '0x' + a['bin'] + args)['contractAddress']


def call(to, sig, *args):
    return cast('call', '--rpc-url', URL, to, sig, *args)


def balance(addr):
    return int(rpc('eth_getBalance', addr, 'latest'), 16)


def deposit_of(addr):
    return int(call(entry_point, 'balanceOf(address)(uint256)', addr).split()[0])


def u128x2(hi, lo):
    return '0x' + f'{hi:032x}{lo:032x}'


def op_tuple(op):
    return '(' + ','.join(str(op[k]) for k in (
        'sender', 'nonce', 'initCode', 'callData', 'accountGasLimits',
        'preVerificationGas', 'gasFees', 'paymasterAndData', 'signature')) + ')'


def user_op(sender, to):
    return {'sender': sender, 'nonce': 0, 'initCode': '0x',
            'callData': cast('calldata', 'execute(address,uint256,bytes)', to, 0, '0x'),
            'accountGasLimits': u128x2(200_000, 50_000),   # verificationGasLimit, callGasLimit
            'preVerificationGas': 50_000,
            'gasFees': u128x2(2 * GWEI, 2 * GWEI),          # maxPriorityFeePerGas, maxFeePerGas
            'paymasterAndData': '0x', 'signature': '0x'}


def handle_ops(ops):
    return cast('calldata', f'handleOps({OP_TYPE}[],address)',
                '[' + ','.join(op_tuple(o) for o in ops) + ']', bundler)


def simulate(ops):
    """First validation of a naive bundler: eth_call handleOps. Returns 'ok' or the FailedOp text."""
    try:
        rpc('eth_call', {'from': bundler, 'to': entry_point, 'data': handle_ops(ops), 'gas': hex(3_000_000)}, 'latest')
        return 'ok'
    except RuntimeError as e:
        data = e.args[0].get('data', '')
        for sig in ('FailedOpWithRevert(uint256,string,bytes)', 'FailedOp(uint256,string)'):
            try:
                idx, msg = cast('decode-error', '--sig', sig, data).splitlines()[:2]
                return f'op {idx}: {msg}'
            except subprocess.CalledProcessError:
                pass
        return str(e.args[0])


# ---------------------------------------------------------------------------
# A small ERC-7562 checker over the default (struct log) tracer of debug_traceCall.
# It covers OP-011, OP-012, OP-080 and the storage rules for an existing,
# unstaked account without paymaster or factory (STO-010, STO-021).
BANNED = {'ORIGIN', 'GASPRICE', 'BLOCKHASH', 'COINBASE', 'TIMESTAMP', 'NUMBER', 'PREVRANDAO',
          'DIFFICULTY', 'GASLIMIT', 'BASEFEE', 'BLOBHASH', 'BLOBBASEFEE', 'CREATE', 'INVALID',
          'SELFDESTRUCT'}                                   # OP-011 (CREATE: no factory here)
STAKED_ONLY = {'BALANCE', 'SELFBALANCE'}                    # OP-080
CALLS = {'CALL', 'STATICCALL', 'DELEGATECALL', 'CALLCODE'}
STORAGE = {'SLOAD', 'SSTORE', 'TLOAD', 'TSTORE'}


def mem(log, off, size):
    blob = bytes.fromhex(''.join(w.removeprefix('0x') for w in log.get('memory') or []))
    return blob[off:off + size].ljust(size, b'\0')


NAMES = {}  # address (int) -> short name, for printing only


def label(a):
    return NAMES.get(a, f'{a:#x}'[:10])


def check7562(sender, struct_logs):
    """Return (opcodes, slots, violations, validUntil) for the frames of `sender` and below."""
    sender = int(sender, 16)
    stack = []            # [(depth, code_addr, storage_addr)] of frames under the sender
    pending = None        # call seen at depth d; resolved by the next log
    hashes = {}           # keccak result -> preimage, as seen in the trace
    opcodes, slots, violations, valid_until = {}, [], [], None
    for i, log in enumerate(struct_logs):
        d, op, st = log['depth'], log['op'], [int(x, 16) for x in log['stack']]
        if pending:
            pd, code, store = pending
            pending = None
            if d == pd + 1 and (stack or code == sender):
                stack.append((d, code, store))
        while stack and d < stack[-1][0]:
            stack.pop()
        if op in CALLS:
            target = st[-2]
            store = stack[-1][2] if op in ('DELEGATECALL', 'CALLCODE') and stack else target
            pending = (d, target, store)
        if not stack or d != stack[-1][0]:
            continue
        code, store = stack[-1][1], stack[-1][2]
        opcodes[op] = opcodes.get(op, 0) + 1
        where = label(code)
        if op in BANNED:
            violations.append(f'OP-011 {op} in {where}')
        if op in STAKED_ONLY:
            violations.append(f'OP-080 {op} in {where} (unstaked)')
        if op == 'GAS' and struct_logs[i + 1]['op'] not in CALLS:
            violations.append(f'OP-012 GAS not followed by CALL in {where}')
        if op == 'KECCAK256':
            pre = mem(log, st[-1], st[-2])
            hashes[int(struct_logs[i + 1]['stack'][-1], 16)] = pre
        if op in STORAGE:
            slot = st[-1]
            if store == sender:
                rule, ok = 'own storage (STO-010)', True
            elif associated(slot, sender, hashes):
                rule, ok = 'associated (STO-021)', True
            else:
                rule, ok = 'not associated', False
                violations.append(f'STO-021 {op} slot {slot:#x} of {label(store)}')
            short = f'{slot:#x}' if slot < 2**32 else f'{slot:#x}'[:12] + '..'
            slots.append(f'{op} {label(store)} slot {short}: {rule}')
        if op == 'RETURN' and len(stack) == 1 and st[-2] == 32:
            valid_until = int.from_bytes(mem(log, st[-1], 32), 'big') >> 160 & (2**48 - 1)
    return opcodes, slots, violations, valid_until


def associated(slot, addr, hashes):
    """ERC-7562 'associated storage': slot == A, or slot == keccak(A || x) + n, 0 <= n <= 128."""
    if slot == addr:
        return True
    for n in range(129):
        pre = hashes.get(slot - n)
        if pre is not None and len(pre) == 64 and int.from_bytes(pre[:32], 'big') == addr:
            return True
    return False


def trace_validation(op):
    """debug_traceCall of handleOps([op, stopper]): the stopper fails with AA20,
    so the bundle reverts before any execution and the trace holds validation only."""
    stopper = dict(op, sender=cast('wallet', 'address', '--private-key', cast('wallet', 'private-key', MNEMONIC, 19)))
    tx = {'from': bundler, 'to': entry_point, 'data': handle_ops([op, stopper]), 'gas': hex(3_000_000)}
    res = rpc('debug_traceCall', tx, 'latest', {'enableMemory': True, 'disableStorage': True})
    return res['structLogs']


lines = []
log = (OUT / 'node.log').open('w')
node = subprocess.Popen([TOOLS['anvil'], '--host', '127.0.0.1', '--port', str(port),
                         '--chain-id', '31337', '--hardfork', 'prague', '--timestamp', '1700000000',
                         '--accounts', '4', '--quiet'], stdout=log, stderr=log)
try:
    for _ in range(200):
        try:
            bundler, deployer, attacker = rpc('eth_accounts')[:3]
            break
        except (OSError, RuntimeError):
            time.sleep(0.05)
    else:
        raise TimeoutError('Anvil startup')
    rpc('anvil_setBlockTimestampInterval', 1)                 # +1 s per block: reproducible times
    owner_key = cast('wallet', 'private-key', MNEMONIC, 5)    # never funded
    owner = cast('wallet', 'address', '--private-key', owner_key)
    recipient = cast('wallet', 'address', '--private-key', cast('wallet', 'private-key', MNEMONIC, 7))

    entry_point = deploy(deployer, ':EntryPoint')
    factory = deploy(deployer, ':SimpleAccountFactory', 'address', entry_point)
    token = deploy(deployer, ':LabToken')
    gate = deploy(attacker, ':Gate')                          # the attacker owns the switch
    t0 = int(rpc('eth_getBlockByNumber', 'latest', False)['timestamp'], 16)
    deadline = t0 + 60
    acct = {
        'SimpleAccount v0.9.0': None,
        'TokenAccount': deploy(deployer, ':TokenAccount', 'address,address', entry_point, token),
        'DeadlineAccount': deploy(deployer, ':DeadlineAccount', 'address,uint48', entry_point, deadline),
        'TimeAccount': deploy(deployer, ':TimeAccount', 'address,uint256', entry_point, deadline),
        'BalanceAccount': deploy(deployer, ':BalanceAccount', 'address', entry_point),
        'GateAccount': deploy(deployer, ':GateAccount', 'address,address', entry_point, gate),
    }
    acct['SimpleAccount v0.9.0'] = call(factory, 'getAddress(address,uint256)(address)', owner, 0)
    NAMES.update({int(v, 16): k.split()[0] for k, v in acct.items()})
    NAMES.update({int(token, 16): 'LabToken', int(gate, 16): 'Gate'})
    send(deployer, cast('calldata', 'mint(address,uint256)', acct['TokenAccount'], 1), token)
    send(deployer, '0x', acct['BalanceAccount'], value=ETH // 100)
    for a in acct.values():   # prepaid deposit, so validation never sends ETH (missingAccountFunds = 0)
        send(deployer, cast('calldata', 'depositTo(address)', a), entry_point, value=ETH // 10)

    def op_for(name, init='0x'):
        o = user_op(acct[name], recipient)
        o['nonce'] = int(call(entry_point, 'getNonce(address,uint192)(uint256)', acct[name], 0).split()[0])
        o['initCode'] = init
        if name.startswith('SimpleAccount'):
            h = call(entry_point, f'getUserOpHash({OP_TYPE})(bytes32)', op_tuple(o))
            o['signature'] = cast('wallet', 'sign', '--no-hash', '--private-key', owner_key, h)
        return o

    # SimpleAccount is created by its first UserOperation (initCode = factory + createAccount).
    init = factory + cast('calldata', 'createAccount(address,uint256)', owner, 0)[2:]
    send(bundler, handle_ops([op_for('SimpleAccount v0.9.0', init)]), entry_point, gas=3_000_000)

    # --- 1. trace each validation and check it ---
    now = int(rpc('eth_getBlockByNumber', 'latest', False)['timestamp'], 16)
    lines.append(f'# 1. validation traced with debug_traceCall (block time {now}, deadline {deadline})')
    lines.append(f'{"account":21}| eth_call | ERC-7562 check')
    details = []
    for name in acct:
        o = op_for(name)
        sim = simulate([o])
        opcodes, slots, bad, vu = check7562(acct[name], trace_validation(o))
        verdict = 'accept' if not bad else 'reject: ' + bad[0].split(' in ')[0].split(' slot')[0]
        lines.append(f'{name:21}| {sim:8} | {verdict}')
        details.append(f'[{name}] {sum(opcodes.values())} opcodes executed in the account frames'
                       + (f', validUntil {vu}' if vu else ''))
        details += [f'  {s}' for s in slots]
        details += [f'  violation: {v}' for v in bad]
    lines += details
    expected = {'SimpleAccount v0.9.0': [], 'TokenAccount': [], 'DeadlineAccount': []}
    for name in expected:
        assert not check7562(acct[name], trace_validation(op_for(name)))[2], name

    # --- 2. TIMESTAMP: passes the simulation, fails in the block, the bundler pays ---
    lines.append('# 2. TimeAccount: simulated now, mined at the deadline')
    o = op_for('TimeAccount')
    b0, d0 = balance(bundler), deposit_of(acct['TimeAccount'])
    now = int(rpc('eth_getBlockByNumber', 'latest', False)['timestamp'], 16)
    lines.append(f'simulation at {now}  : {simulate([o])}')
    rpc('evm_setNextBlockTimestamp', hex(deadline))
    r = receipt(submit(bundler, handle_ops([o]), entry_point, gas=1_000_000))
    gas_used, price = int(r['gasUsed'], 16), int(r['effectiveGasPrice'], 16)
    assert int(r['status'], 16) == 0
    lines.append(f'mined at {deadline}       : status {int(r["status"], 16)} (reverted), gasUsed {gas_used}')
    lines.append(f'bundler balance change : {(balance(bundler) - b0) / GWEI:+.0f} gwei'
                 f' (= {gas_used} gas x {price // GWEI} gwei)')
    lines.append(f'account deposit change : {(deposit_of(acct["TimeAccount"]) - d0) / GWEI:+.0f} gwei')
    assert balance(bundler) - b0 == -gas_used * price and deposit_of(acct['TimeAccount']) == d0
    lines.append(f'DeadlineAccount now    : {simulate([op_for("DeadlineAccount")])}'
                 f' (validUntil {deadline - 1} was visible in the trace)')

    # --- 3. one storage write invalidates many UserOperations ---
    lines.append('# 3. ten GateAccounts and one Gate.close() from the attacker')
    gates = [deploy(deployer, ':GateAccount', 'address,address', entry_point, gate) for _ in range(10)]
    for a in gates:
        send(deployer, cast('calldata', 'depositTo(address)', a), entry_point, value=ETH // 10)
    ops = [user_op(a, recipient) for a in gates]
    lines.append(f'first validation  : {sum(simulate([x]) == "ok" for x in ops)}/10 ok, '
                 f'bundle of 10: {simulate(ops)}')
    b0, a0 = balance(bundler), balance(attacker)
    g0 = sum(deposit_of(a) + balance(a) for a in gates)
    rpc('evm_setAutomine', False)
    hb = submit(bundler, handle_ops(ops), entry_point, gas=3_000_000, price=2 * GWEI)
    ha = submit(attacker, cast('calldata', 'close()'), gate, gas=100_000, price=3 * GWEI)  # front-runs
    rpc('evm_mine')
    rpc('evm_setAutomine', True)
    rb, ra = receipt(hb), receipt(ha)
    assert rb['blockNumber'] == ra['blockNumber'] and int(ra['transactionIndex'], 16) < int(rb['transactionIndex'], 16)
    assert int(ra['status'], 16) == 1 and int(rb['status'], 16) == 0
    cost = lambda x: int(x['gasUsed'], 16) * int(x['effectiveGasPrice'], 16)
    lines.append(f'same block        : close() index {int(ra["transactionIndex"], 16)} status 1, '
                 f'handleOps index {int(rb["transactionIndex"], 16)} status 0')
    lines.append(f'attacker paid     : {cost(ra) // GWEI} gwei ({int(ra["gasUsed"], 16)} gas x 3 gwei)')
    paid = g0 - sum(deposit_of(a) + balance(a) for a in gates)
    lines.append(f'bundler paid      : {cost(rb) // GWEI} gwei ({int(rb["gasUsed"], 16)} gas x 2 gwei)')
    lines.append(f'10 GateAccounts   : {paid // GWEI} gwei (deposit + balance change)')
    assert b0 - balance(bundler) == cost(rb) and a0 - balance(attacker) == cost(ra) and paid == 0
    after = [simulate([x]) for x in ops]
    lines.append(f'second validation : {sum(x == "ok" for x in after)}/10 ok ({after[0]})')

    # --- 4. same sender twice in one bundle (two nonce keys, ETH for one prefund) ---
    lines.append('# 4. one sender, two UserOperations, ETH for one prefund only')
    solo = deploy(deployer, ':TokenAccount', 'address,address', entry_point, token)
    send(deployer, cast('calldata', 'mint(address,uint256)', solo, 1), token)
    prefund = (200_000 + 50_000 + 50_000) * 2 * GWEI
    send(deployer, '0x', solo, value=prefund * 3 // 2)
    pair = [dict(user_op(solo, recipient), nonce=k << 64) for k in (0, 1)]  # nonce keys 0 and 1
    lines.append(f'prefund per op    : {prefund // GWEI} gwei, account balance {balance(solo) // GWEI} gwei')
    lines.append(f'op(key 0) alone   : {simulate(pair[:1])}')
    lines.append(f'op(key 1) alone   : {simulate(pair[1:])}')
    lines.append(f'both in one bundle: {simulate(pair)}')
    assert simulate(pair[:1]) == simulate(pair[1:]) == 'ok' and simulate(pair) != 'ok'
    lines.append('Assertions: PASS')
    summary = '\n'.join(lines) + '\n'
    (OUT / 'summary.txt').write_text(summary)
    (OUT / 'versions.txt').write_text('\n'.join(
        subprocess.check_output([t, '--version'], text=True).splitlines()[0] for t in TOOLS.values()) + '\n')
    print(summary, end='')
finally:
    node.terminate()
    try:
        node.wait(timeout=5)
    except subprocess.TimeoutExpired:
        node.kill()
    log.close()
