"""再入攻撃の実験。ローカルの Anvil だけを使う。

- 公開ネットワーク・実資産・本物の秘密鍵は使わない。
- アカウントは Anvil が既定で作るテスト用のもの（鍵が広く公開されており、説明用で無価値）。
- Python 標準ライブラリだけで JSON-RPC を呼ぶ。

実行: ANVIL=... SOLC=... python3 run.py  （PATH にあれば環境変数は不要）
"""
import json
import os
import shutil
import subprocess
import time
import urllib.request
from pathlib import Path

from keccak import keccak256

LAB = Path(__file__).resolve().parent
ANVIL = os.environ.get('ANVIL', shutil.which('anvil'))
SOLC = os.environ.get('SOLC', shutil.which('solc'))
PORT = 8546
ETH = 10**18


# ---- JSON-RPC と ABI の最小限の道具 -------------------------------------------

def rpc(method, *params):
    body = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': list(params)}).encode()
    req = urllib.request.Request(f'http://127.0.0.1:{PORT}', body, {'Content-Type': 'application/json'})
    res = json.loads(urllib.request.urlopen(req).read())
    if 'error' in res:
        raise RuntimeError(res['error'])
    return res['result']


def word(v):
    if isinstance(v, bool):
        v = int(v)
    if isinstance(v, str):  # 0x 付きのアドレス
        return bytes.fromhex(v[2:]).rjust(32, b'\0')
    return v.to_bytes(32, 'big')


def selector(sig):
    return keccak256(sig.encode())[:4]


def calldata(sig, *args):
    return '0x' + (selector(sig) + b''.join(word(a) for a in args)).hex()


def send(sender, to, data='0x', value=0, gas=3_000_000):
    tx = {'from': sender, 'data': data, 'gas': hex(gas), 'value': hex(value)}
    if to:
        tx['to'] = to
    h = rpc('eth_sendTransaction', tx)  # 自動のマイニングで、すぐにブロックに入る
    for _ in range(200):
        r = rpc('eth_getTransactionReceipt', h)
        if r:
            return r
        time.sleep(0.01)
    raise RuntimeError(f'no receipt for {h}')


def balance(addr):
    return int(rpc('eth_getBalance', addr, 'latest'), 16)


def ledger(bank, addr):
    """銀行の帳簿 balances[addr]。"""
    return int(rpc('eth_call', {'to': bank, 'data': calldata('balances(address)', addr)}, 'latest'), 16)


def deploy(compiled, name, *args, sender):
    r = send(sender, None, '0x' + compiled[name] + b''.join(word(a) for a in args).hex(), gas=5_000_000)
    assert r['status'] == '0x1', f'deploy of {name} failed'
    return r['contractAddress']


def reason(data):
    """revert の理由のバイト列を読める形にする。"""
    if data[:4] == selector('Error(string)'):
        n = int.from_bytes(data[36:68], 'big')
        return data[68:68 + n].decode()
    if data[:4] == selector('ReentrancyGuardReentrantCall()'):
        return 'ReentrancyGuardReentrantCall()'
    return '0x' + data.hex()


def events(receipt):
    """Attacker の Received / Rejected を順に取り出す。"""
    received = '0x' + keccak256(b'Received(uint256,uint256)').hex()
    rejected = '0x' + keccak256(b'Rejected(uint256,bytes)').hex()
    out = []
    for log in receipt['logs']:
        data = bytes.fromhex(log['data'][2:])
        if log['topics'][0] == received:
            out.append(('received', int.from_bytes(data[:32], 'big'), int.from_bytes(data[32:64], 'big')))
        elif log['topics'][0] == rejected:
            n = int.from_bytes(data[64:96], 'big')
            out.append(('rejected', int.from_bytes(data[:32], 'big'), reason(data[96:96 + n])))
    return out


def eth(wei):
    return f'{wei / ETH:g} ETH'


# ---- 実験 ----------------------------------------------------------------------

BANKS = ['VulnerableBank', 'CeiBank', 'GuardedBank', 'TransientGuardedBank']


def setup_bank(compiled, name, a):
    bank = deploy(compiled, name, sender=a['deployer'])
    send(a['alice'], bank, calldata('deposit()'), value=5 * ETH)
    send(a['bob'], bank, calldata('deposit()'), value=5 * ETH)
    return bank


def single_function(compiled, a, trajectory):
    print('\n== (1) single-function reentrancy: mallory deposits 1 ETH and calls withdraw() once')
    for name in BANKS:
        bank = setup_bank(compiled, name, a)
        attacker = deploy(compiled, 'Attacker', bank, a['mallory'], sender=a['mallory'])
        before = balance(bank) + 1 * ETH
        r = send(a['mallory'], attacker, calldata('attack(bool)', False), value=1 * ETH)
        evs = events(r)
        received = [e for e in evs if e[0] == 'received']
        print(f'  {name}: tx {"ok" if r["status"] == "0x1" else "reverted"}, gas used {int(r["gasUsed"], 16):,}')
        print(f'    bank balance after each ETH arrival: '
              + ' -> '.join(f'{e[2] // ETH}' for e in received) + ' ETH')
        for e in evs:
            if e[0] == 'rejected':
                print(f'    reentry #{e[1]} rejected: {e[2]}')
        print(f'    bank {eth(balance(bank))} (was {eth(before)}), attacker contract {eth(balance(attacker))}, '
              f'alice ledger {eth(ledger(bank, a["alice"]))}')
        w = send(a['alice'], bank, calldata('withdraw()'))
        print(f'    alice withdraw() -> {"ok" if w["status"] == "0x1" else "reverted"}')
        trajectory[name] = [before] + [e[2] for e in received]


def cross_function(compiled, a):
    print('\n== (2) cross-function reentrancy: during the callback, move the not-yet-zeroed balance '
          'to mallory with transferBalance()')
    for name in ['GuardedBank', 'TransientGuardedBank', 'CeiBank']:
        bank = setup_bank(compiled, name, a)
        attacker = deploy(compiled, 'Attacker', bank, a['mallory'], sender=a['mallory'])
        r = send(a['mallory'], attacker, calldata('attack(bool)', True), value=1 * ETH)
        for e in events(r):
            if e[0] == 'rejected':
                print(f'  {name}: transferBalance rejected: {e[2]}')
        moved = ledger(bank, a['mallory'])
        w = send(a['mallory'], bank, calldata('withdraw()')) if moved else None
        print(f'  {name}: attacker contract got {eth(balance(attacker))}, mallory ledger {eth(moved)}'
              + (f', mallory withdraws it -> {"ok" if w["status"] == "0x1" else "reverted"}' if w else ''))
        print(f'    bank {eth(balance(bank))} (victims deposited 10 ETH)')


def gas_cost(compiled, a, costs):
    print('\n== (3) gas of a normal deposit + withdraw by alice (1 ETH, fresh bank)')
    for name in BANKS:
        bank = deploy(compiled, name, sender=a['deployer'])
        d = send(a['alice'], bank, calldata('deposit()'), value=1 * ETH)
        w = send(a['alice'], bank, calldata('withdraw()'))
        costs[name] = {'deposit': int(d['gasUsed'], 16), 'withdraw': int(w['gasUsed'], 16)}
        print(f'  {name:<21} deposit {costs[name]["deposit"]:>6,}  withdraw {costs[name]["withdraw"]:>6,}')


def stipend(compiled, a):
    print('\n== (4) 2300 gas stipend: receiver reads one storage slot and emits a log')
    receiver = deploy(compiled, 'Receiver', sender=a['deployer'])
    payer = deploy(compiled, 'Payer', sender=a['deployer'])
    for fn in ('payWithTransfer(address)', 'payWithCall(address)'):
        r = send(a['alice'], payer, calldata(fn, receiver), value=1)
        h = r['transactionHash']
        trace = rpc('debug_traceTransaction', h, {'tracer': 'callTracer'})
        inner = trace.get('calls', [{}])[0]
        print(f'  {fn.split("(")[0]:<15} -> {"ok" if r["status"] == "0x1" else "reverted"}; '
              f'gas given to receiver {int(inner.get("gas", "0x0"), 16):,}, used {int(inner.get("gasUsed", "0x0"), 16):,}'
              + (f', error: {inner["error"]}' if 'error' in inner else ''))


def main():
    src = LAB / 'Bank.sol'
    out = json.loads(subprocess.check_output(
        [SOLC, '--evm-version', 'cancun', '--combined-json', 'bin', 'Bank.sol'],
        text=True, cwd=LAB, stderr=subprocess.DEVNULL))
    compiled = {k.split(':')[1]: v['bin'] for k, v in out['contracts'].items() if k.startswith('Bank.sol:')}

    print(subprocess.check_output([ANVIL, '--version'], text=True).splitlines()[0])
    print(subprocess.check_output([SOLC, '--version'], text=True).splitlines()[-1])
    log = open(LAB / 'output' / 'anvil.log', 'w')
    node = subprocess.Popen([ANVIL, '--host', '127.0.0.1', '--port', str(PORT), '--chain-id', '31337',
                             '--hardfork', 'cancun', '--timestamp', '1700000000', '--accounts', '4'],
                            stdout=log, stderr=log)
    try:
        for _ in range(100):
            try:
                accounts = rpc('eth_accounts')
                break
            except OSError:
                time.sleep(0.1)
        a = dict(zip(['deployer', 'alice', 'bob', 'mallory'], accounts))
        trajectory, costs = {}, {}
        single_function(compiled, a, trajectory)
        cross_function(compiled, a)
        gas_cost(compiled, a, costs)
        stipend(compiled, a)
        (LAB / 'output' / 'results.json').write_text(
            json.dumps({'trajectory_wei': trajectory, 'gas': costs}, indent=2) + '\n')
    finally:
        node.terminate()
        node.wait()


if __name__ == '__main__':
    main()
