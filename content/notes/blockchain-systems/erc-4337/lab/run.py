#!/usr/bin/env python3
"""Local-only ERC-4337 experiment (EntryPoint v0.9.0). Run through run.sh.

The script plays the bundler itself: it builds UserOperations and calls
EntryPoint.handleOps directly from a funded test EOA. No bundler software,
no alt mempool, no external RPC. Keys are Anvil's public test mnemonic only.
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
    return subprocess.check_output([TOOLS['cast'], *map(str, args)], text=True).strip()


def artifact(suffix):
    return next(v for k, v in BUILD.items() if k.endswith(suffix))


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


def send(sender, data, to=None, value=0, gas=15_000_000):
    # Legacy gasPrice keeps the bundler's price fixed at 2 gwei in every block.
    tx = {'from': sender, 'data': data, 'value': hex(value), 'gas': hex(gas), 'gasPrice': hex(2 * GWEI)}
    if to:
        tx['to'] = to
    h = rpc('eth_sendTransaction', tx)
    for _ in range(200):
        r = rpc('eth_getTransactionReceipt', h)
        if r:
            assert int(r['status'], 16) == 1, r
            return r
        time.sleep(0.05)
    raise TimeoutError(h)


def deploy(sender, suffix, *ctor):
    a = artifact(suffix)
    args = cast('abi-encode', 'f(address)', *ctor)[2:] if ctor else ''
    return send(sender, '0x' + a['bin'] + args)['contractAddress']


def call(to, sig, *args):
    return cast('call', '--rpc-url', URL, to, sig, *args)


def balance(addr):
    return int(rpc('eth_getBalance', addr, 'latest'), 16)


def u128x2(hi, lo):  # two uint128 packed into one bytes32
    return '0x' + f'{hi:032x}{lo:032x}'


def op_tuple(op):
    return '(' + ','.join(str(op[k]) for k in (
        'sender', 'nonce', 'initCode', 'callData', 'accountGasLimits',
        'preVerificationGas', 'gasFees', 'paymasterAndData', 'signature')) + ')'


def sign(op, key):
    op['signature'] = '0x'
    h = call(entry_point, f'getUserOpHash({OP_TYPE})(bytes32)', op_tuple(op))
    # SimpleAccount v0.9 recovers the signer from the raw EIP-712 userOpHash.
    op['signature'] = cast('wallet', 'sign', '--no-hash', '--private-key', key, h)
    return h


def handle_ops(op, beneficiary):
    data = cast('calldata', f'handleOps({OP_TYPE}[],address)', f'[{op_tuple(op)}]', beneficiary)
    return data


def frames(txhash):
    """Gas of the call frames that ERC-4337 splits into validation and execution."""
    trace = rpc('debug_traceTransaction', txhash, {'tracer': 'callTracer'})
    names = {cast('sig', s): s.split('(')[0] for s in (
        'createSender(bytes)', 'validateUserOp(' + OP_TYPE + ',bytes32,uint256)',
        'validatePaymasterUserOp(' + OP_TYPE + ',bytes32,uint256)',
        'execute(address,uint256,bytes)')}
    found = {}

    def walk(f):
        name = names.get(f.get('input', '')[:10])
        if name and name not in found:
            found[name] = int(f['gasUsed'], 16)
        for c in f.get('calls', []):
            walk(c)
    walk(trace)
    return found


def user_op_event(receipt):
    topic = cast('sig-event', 'UserOperationEvent(bytes32,address,address,uint256,bool,uint256,uint256)')
    log = next(l for l in receipt['logs'] if l['topics'][0] == topic)
    words = [int(log['data'][2 + i * 64: 2 + (i + 1) * 64], 16) for i in range(4)]
    return {'success': words[1], 'actualGasCost': words[2], 'actualGasUsed': words[3]}


lines = []
log = (OUT / 'node.log').open('w')
node = subprocess.Popen([TOOLS['anvil'], '--host', '127.0.0.1', '--port', str(port),
                         '--chain-id', '31337', '--hardfork', 'prague', '--timestamp', '1700000000',
                         '--accounts', '3', '--quiet'], stdout=log, stderr=log)
try:
    for _ in range(200):
        try:
            bundler, funder, pm_owner = rpc('eth_accounts')[:3]
            break
        except (OSError, RuntimeError):
            time.sleep(0.05)
    else:
        raise TimeoutError('Anvil startup')
    owner_key = cast('wallet', 'private-key', MNEMONIC, 5)    # never funded
    owner = cast('wallet', 'address', '--private-key', owner_key)
    other_key = cast('wallet', 'private-key', MNEMONIC, 6)    # not the owner

    entry_point = deploy(bundler, ':EntryPoint')
    factory = deploy(bundler, ':SimpleAccountFactory', entry_point)
    paymaster = deploy(pm_owner, ':TestPaymasterAcceptAll', entry_point)
    send(pm_owner, cast('calldata', 'deposit()'), paymaster, value=1 * ETH)

    # --- 1. Address before deployment (CREATE2) ---
    salt = 0
    implementation = call(factory, 'accountImplementation()(address)')
    init_args = cast('abi-encode', 'f(address,bytes)', implementation,
                     cast('calldata', 'initialize(address)', owner))
    proxy_init_code = '0x' + artifact(':ERC1967Proxy')['bin'] + init_args[2:]
    by_formula = cast('compute-address', factory, '--salt', f'0x{salt:064x}',
                      '--init-code-hash', cast('keccak', proxy_init_code)).split()[-1]
    by_factory = call(factory, 'getAddress(address,uint256)(address)', owner, salt)
    init_code = factory + cast('calldata', 'createAccount(address,uint256)', owner, salt)[2:]
    try:
        rpc('eth_call', {'to': entry_point, 'data': cast('calldata', 'getSenderAddress(bytes)', init_code)}, 'latest')
        raise AssertionError('getSenderAddress must revert')
    except RuntimeError as e:
        by_entry_point = cast('decode-error', '--sig', 'SenderAddressResult(address)', e.args[0]['data'])
    sender = by_factory
    assert by_formula.lower() == by_factory.lower() == by_entry_point.lower()
    assert rpc('eth_getCode', sender, 'latest') == '0x'
    send(funder, '0x', sender, value=ETH // 10)
    lines += ['# 1. counterfactual address',
              f'CREATE2 formula      : {by_formula}',
              f'factory.getAddress   : {by_factory}',
              f'getSenderAddress     : {by_entry_point}',
              f'code before          : {rpc("eth_getCode", sender, "latest")}  balance: {balance(sender) / ETH} ETH']

    recipients = [cast('wallet', 'address', '--private-key', cast('wallet', 'private-key', MNEMONIC, i)) for i in (7, 8, 9)]

    def user_op(nonce, to, init=b'', pm='0x'):
        return {'sender': sender, 'nonce': nonce, 'initCode': init or '0x',
                'callData': cast('calldata', 'execute(address,uint256,bytes)', to, ETH // 100, '0x'),
                'accountGasLimits': u128x2(400_000, 60_000),   # verificationGasLimit, callGasLimit
                'preVerificationGas': 50_000,
                'gasFees': u128x2(2 * GWEI, 2 * GWEI),          # maxPriorityFeePerGas, maxFeePerGas
                'paymasterAndData': pm, 'signature': '0x'}

    # --- 2. Broken signatures are rejected in validation ---
    lines.append('# 2. validation failures (eth_call to handleOps, nothing is mined)')
    op = user_op(0, recipients[0], init_code)
    sign(op, owner_key)
    tampered = dict(op, callData=cast('calldata', 'execute(address,uint256,bytes)', recipients[0], ETH, '0x'))
    wrong_key = dict(op)
    sign(wrong_key, other_key)
    for label, bad in (('value changed after signing', tampered), ('signed by another key', wrong_key)):
        try:
            rpc('eth_call', {'from': bundler, 'to': entry_point, 'data': handle_ops(bad, bundler)}, 'latest')
            raise AssertionError('must fail')
        except RuntimeError as e:
            err = cast('decode-error', '--sig', 'FailedOp(uint256,string)', e.args[0]['data']).splitlines()
            lines.append(f'{label:28}: FailedOp({err[0]}, {err[1]})')
    assert rpc('eth_getCode', sender, 'latest') == '0x'

    # --- 3. Three UserOperations: deploy + self-paid, self-paid, paymaster ---
    lines.append('# 3. handleOps sent by the bundler EOA (beneficiary = bundler)')
    pm_data = paymaster + f'{100_000:032x}{0:032x}'  # paymaster, verification gas, postOp gas
    cases = [('op1 initCode, self-paid', op),
             ('op2 self-paid', user_op(1, recipients[1])),
             ('op3 paymaster', user_op(2, recipients[2], pm=pm_data))]
    rows, gas_rows = [], []
    for i, (label, o) in enumerate(cases):
        if i:
            sign(o, owner_key)
        before = {'bundler': balance(bundler), 'sender': balance(sender),
                  'sender_deposit': int(call(entry_point, 'balanceOf(address)(uint256)', sender).split()[0]),
                  'pm_deposit': int(call(entry_point, 'balanceOf(address)(uint256)', paymaster).split()[0]),
                  'owner': balance(owner)}
        r = send(bundler, handle_ops(o, bundler), entry_point, gas=3_000_000)
        ev = user_op_event(r)
        assert ev['success'] == 1
        after = {'bundler': balance(bundler), 'sender': balance(sender),
                 'sender_deposit': int(call(entry_point, 'balanceOf(address)(uint256)', sender).split()[0]),
                 'pm_deposit': int(call(entry_point, 'balanceOf(address)(uint256)', paymaster).split()[0]),
                 'owner': balance(owner)}
        d = {k: after[k] - before[k] for k in before}
        tx_fee = int(r['gasUsed'], 16) * int(r['effectiveGasPrice'], 16)
        assert d['owner'] == 0 and balance(owner) == 0
        assert d['bundler'] == ev['actualGasCost'] - tx_fee
        if i == 2:
            assert d['sender'] == -ETH // 100 and d['sender_deposit'] == 0
            assert d['pm_deposit'] == -ev['actualGasCost']
        else:
            assert d['sender'] + d['sender_deposit'] == -ETH // 100 - ev['actualGasCost']
        f = frames(r['transactionHash'])
        g = lambda wei: f'{wei // GWEI:>+10}'  # all values are multiples of 1 gwei here
        rows.append(f"{label:24}| {g(d['sender'] + d['sender_deposit'])} | {g(d['pm_deposit'])} | "
                    f"{g(-tx_fee)} | {g(ev['actualGasCost'])} | {g(d['owner'])}")
        gas_rows.append(f"{label:24}| {int(r['gasUsed'], 16):>8} | {ev['actualGasUsed']:>8} | "
                        f"{f.get('createSender', 0):>8} | {f['validateUserOp']:>8} | "
                        f"{f.get('validatePaymasterUserOp', 0):>8} | {f['execute']:>8}")
        if i == 0:
            code_len = (len(rpc('eth_getCode', sender, 'latest')) - 2) // 2
            lines.append(f'code after op1       : {code_len} bytes at {sender}')
    lines.append('change in gwei          | sender     | paymaster  | bundler    | bundler    | owner')
    lines.append('                        | ETH+deposit| deposit    | tx fee     | received   | EOA')
    lines += rows
    # --- 4. Baseline: plain EOA transfer of the same 0.01 ETH to a fresh address ---
    fresh = cast('wallet', 'address', '--private-key', cast('wallet', 'private-key', MNEMONIC, 10))
    base = send(funder, '0x', fresh, value=ETH // 100, gas=21_000)
    lines.append('# 4. gas (tx = handleOps receipt gasUsed, op = UserOperationEvent.actualGasUsed)')
    lines.append('case                    | tx gas   | op gas   | create   | validate | pm valid | execute')
    lines += gas_rows
    lines.append(f"{'EOA transfer (baseline)':24}| {int(base['gasUsed'], 16):>8} |")
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
