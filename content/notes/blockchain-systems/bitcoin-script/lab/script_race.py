#!/usr/bin/env python3
"""Local regtest only (Bitcoin Core 32.1). Run through run.sh (--network none).

1. hashlock:  witnessScript = OP_SHA256 <H> OP_EQUAL
   Bob spends it with the preimage. A watcher polls the mempool every 0.5 s,
   copies the preimage, and sends a replacement that pays itself a higher fee.
   One block is mined 5 s after Bob's broadcast.
2. hash+sig:  witnessScript = OP_SHA256 <H> OP_EQUALVERIFY <Bob pubkey> OP_CHECKSIG
   Same flow. The watcher copies the preimage and Bob's signature.
3. bare:      the hashlock script placed directly in an output's scriptPubKey
   (not hashed into P2WSH). testmempoolaccept, then generateblock.

Every key is a throwaway regtest key made in this process.
"""
import hashlib
import json
import os
import secrets
import shutil
import subprocess
import time

BIN = os.environ.get('BITCOIN_BIN', '/opt/bitcoin/bin')
DATA = '/tmp/regtest'
POLL = 0.5        # watcher polls the mempool every 0.5 s
BLOCK_AT = 5.0    # one block is mined 5 s after Bob's broadcast


def cli(*args, wallet=None, ok=True):
    cmd = [f'{BIN}/bitcoin-cli', '-regtest', f'-datadir={DATA}']
    if wallet:
        cmd.append(f'-rpcwallet={wallet}')
    r = subprocess.run(cmd + [str(a).lower() if isinstance(a, bool) else str(a) for a in args], capture_output=True, text=True)
    if r.returncode:
        if ok:
            raise RuntimeError(r.stderr.strip())
        return {'error': r.stderr.strip().splitlines()[-1]}
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        return r.stdout.strip()


def start():
    shutil.rmtree(DATA, ignore_errors=True)
    os.makedirs(DATA)
    subprocess.check_call([f'{BIN}/bitcoind', '-regtest', f'-datadir={DATA}', '-daemon',
                           '-listen=0', '-dnsseed=0', '-fixedseeds=0', '-fallbackfee=0.0001', '-txindex'],
                          stdout=subprocess.DEVNULL)
    for _ in range(300):
        if os.path.exists(f'{DATA}/regtest/.cookie'):
            break
        time.sleep(0.1)
    cli('-rpcwait', 'getblockcount')


# ---- secp256k1 ECDSA (only for signing throwaway regtest keys) ----
P = 2**256 - 2**32 - 977
N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
G = (0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798,
     0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8)


def add(a, b):
    if a is None:
        return b
    if b is None:
        return a
    if a[0] == b[0] and (a[1] + b[1]) % P == 0:
        return None
    if a == b:
        m = 3 * a[0] * a[0] * pow(2 * a[1], -1, P)
    else:
        m = (b[1] - a[1]) * pow(b[0] - a[0], -1, P)
    x = (m * m - a[0] - b[0]) % P
    return x, (m * (a[0] - x) - a[1]) % P


def mul(k, pt=G):
    r = None
    while k:
        if k & 1:
            r = add(r, pt)
        pt = add(pt, pt)
        k >>= 1
    return r


def pubkey(d):
    x, y = mul(d)
    return bytes([2 + (y & 1)]) + x.to_bytes(32, 'big')


def der(r, s):
    def enc(v):
        b = v.to_bytes(33, 'big').lstrip(b'\x00')
        return b'\x00' + b if b[0] & 0x80 else b
    rb, sb = enc(r), enc(s)
    body = b'\x02' + bytes([len(rb)]) + rb + b'\x02' + bytes([len(sb)]) + sb
    return b'\x30' + bytes([len(body)]) + body


def sign(d, z):
    while True:
        k = secrets.randbelow(N - 1) + 1
        r = mul(k)[0] % N
        s = pow(k, -1, N) * (z + r * d) % N
        if r and s:
            return der(r, min(s, N - s))   # low S (policy rule)


# ---- transaction serialization (1 input, 1 output, segwit) ----
def sha256(b):
    return hashlib.sha256(b).digest()


def dsha(b):
    return sha256(sha256(b))


def varint(n):
    return bytes([n]) if n < 0xfd else b'\xfd' + n.to_bytes(2, 'little')


def push(b):
    return varint(len(b)) + b if len(b) < 0x4c else b'\x4c' + bytes([len(b)]) + b


def outpoint(txid, vout):
    return bytes.fromhex(txid)[::-1] + vout.to_bytes(4, 'little')


SEQ = 0xffffffff   # no BIP125 opt-in signal


def bip143(txid, vout, value, script, out_value, out_spk):
    """Signature hash of a P2WSH input with SIGHASH_ALL (BIP143)."""
    op = outpoint(txid, vout)
    seq = SEQ.to_bytes(4, 'little')
    outs = out_value.to_bytes(8, 'little') + varint(len(out_spk)) + out_spk
    pre = (b'\x02\x00\x00\x00' + dsha(op) + dsha(seq) + op + varint(len(script)) + script
           + value.to_bytes(8, 'little') + seq + dsha(outs) + b'\x00\x00\x00\x00'
           + b'\x01\x00\x00\x00')
    return int.from_bytes(dsha(pre), 'big')


def spend(txid, vout, out_value, out_spk, witness):
    return (b'\x02\x00\x00\x00' + b'\x00\x01' + b'\x01' + outpoint(txid, vout) + b'\x00'
            + SEQ.to_bytes(4, 'little') + b'\x01' + out_value.to_bytes(8, 'little')
            + varint(len(out_spk)) + out_spk
            + varint(len(witness)) + b''.join(varint(len(w)) + w for w in witness)
            + b'\x00\x00\x00\x00').hex()


def spk_of(wallet):
    addr = cli('getnewaddress', '', 'bech32', wallet=wallet)
    return addr, bytes.fromhex(cli('getaddressinfo', addr, wallet=wallet)['scriptPubKey'])


def fund(script):
    info = cli('decodescript', script.hex())
    addr = info['segwit']['address']
    txid = cli('sendtoaddress', addr, 1, wallet='miner')
    cli('generatetoaddress', 1, MINER)
    tx = cli('getrawtransaction', txid, True)
    vout = next(o['n'] for o in tx['vout'] if o['scriptPubKey'].get('address') == addr)
    return addr, txid, vout, 100_000_000


def race(name, script, bob_witness_fn):
    """Bob broadcasts, the watcher copies what it can see, one block 5 s later."""
    addr, txid, vout, value = fund(script)
    bob_addr, bob_spk = spk_of('bob')
    w_addr, w_spk = spk_of('watcher')
    log = {'case': name, 'witnessScript': script.hex(), 'p2wsh_address': addr, 'events': []}
    t0 = time.monotonic()

    def ev(what, **kw):
        log['events'].append({'t': round(time.monotonic() - t0, 3), 'event': what, **kw})

    bob_fee = 1_000
    bob_raw = spend(txid, vout, value - bob_fee, bob_spk,
                    bob_witness_fn(txid, vout, value, value - bob_fee, bob_spk))
    bob_txid = cli('sendrawtransaction', bob_raw)
    ev('bob_broadcast', txid=bob_txid, fee_sat=bob_fee, to='bob')

    seen = False
    while time.monotonic() - t0 < BLOCK_AT:
        time.sleep(POLL)
        if seen:
            continue
        for mtxid in cli('getrawmempool'):
            tx = cli('getrawtransaction', mtxid, True)
            vin = tx['vin'][0]
            wit = vin.get('txinwitness', [])
            if vin.get('txid') != txid or not wit or wit[-1] != script.hex():
                continue
            seen = True
            ev('watcher_saw', txid=mtxid, witness=wit)
            # copy every witness item Bob revealed, change only the output
            w_fee = 10_000
            w_raw = spend(txid, vout, value - w_fee, w_spk, [bytes.fromhex(x) for x in wit])
            res = cli('sendrawtransaction', w_raw, ok=False)
            if isinstance(res, dict):
                ev('watcher_rejected', fee_sat=w_fee, error=res['error'])
            else:
                ev('watcher_broadcast', txid=res, fee_sat=w_fee, to='watcher',
                   mempool=cli('getrawmempool'))
    block = cli('generatetoaddress', 1, MINER)[0]
    included = [t for t in cli('getblock', block)['tx'][1:]]
    ev('block_mined', included=included,
       winner='bob' if bob_txid in included else 'watcher' if included else 'none')
    log['bob_balance_btc'] = cli('getbalance', wallet='bob')
    log['watcher_balance_btc'] = cli('getbalance', wallet='watcher')
    # empty the two wallets so the next case starts from 0
    for w in ('bob', 'watcher'):
        if float(cli('getbalance', wallet=w)) > 0:
            cli('sendtoaddress', MINER, cli('getbalance', wallet=w), '', '', True, wallet=w)
    cli('generatetoaddress', 1, MINER)
    return log


def bare_case():
    """The hashlock script placed directly in an output (not hashed into P2WSH)."""
    secret = b'bare secret'
    script = b'\xa8' + push(sha256(secret)) + b'\x87'
    out = {}
    for label, spk in (('bare', script), ('p2wsh', b'\x00\x20' + sha256(script))):
        utxo = next(u for u in cli('listunspent', wallet='miner') if u['amount'] >= 1)
        placeholder, ph_spk = spk_of('miner')
        raw = cli('createrawtransaction',
                  json.dumps([{'txid': utxo['txid'], 'vout': utxo['vout']}]),
                  json.dumps({placeholder: round(utxo['amount'] - 0.0001, 8)}))
        raw = raw.replace(varint(len(ph_spk)).hex() + ph_spk.hex(), varint(len(spk)).hex() + spk.hex())
        signed = cli('signrawtransactionwithwallet', raw, wallet='miner')['hex']
        r = cli('testmempoolaccept', json.dumps([signed]))[0]
        entry = {'scriptPubKey': spk.hex(), 'allowed': r['allowed'], 'reject': r.get('reject-reason')}
        if not r['allowed']:
            g = cli('generateblock', MINER, json.dumps([signed]), ok=False)
            entry['generateblock'] = 'error: ' + g['error'] if isinstance(g, dict) and 'error' in g else 'block ' + g['hash'][:16]
        out[label] = entry
    return {'case': 'bare_vs_p2wsh', 'witnessScript': script.hex(), 'result': out}


def main():
    global MINER
    start()
    for w in ('miner', 'bob', 'watcher'):
        cli('createwallet', w)
    MINER = cli('getnewaddress', wallet='miner')
    cli('generatetoaddress', 110, MINER)

    results = {'bitcoind': cli('getnetworkinfo')['subversion'], 'poll_s': POLL, 'block_at_s': BLOCK_AT}

    # 1. hashlock: anyone who knows the preimage can spend
    secret = secrets.token_bytes(16)
    hashlock = b'\xa8' + push(sha256(secret)) + b'\x87'          # OP_SHA256 <H> OP_EQUAL
    results['hashlock'] = race('hashlock', hashlock, lambda *a: [secret, hashlock])

    # 2. hash + Bob's signature
    d = secrets.randbelow(N - 1) + 1
    secret2 = secrets.token_bytes(16)
    hashsig = (b'\xa8' + push(sha256(secret2)) + b'\x88'          # OP_SHA256 <H> OP_EQUALVERIFY
               + push(pubkey(d)) + b'\xac')                       # <Bob pubkey> OP_CHECKSIG

    def bob_sig(txid, vout, value, out_value, out_spk):
        z = bip143(txid, vout, value, hashsig, out_value, out_spk)
        return [sign(d, z) + b'\x01', secret2, hashsig]

    results['hashsig'] = race('hashsig', hashsig, bob_sig)

    # 3. the same hashlock as a bare output vs wrapped in P2WSH
    results['bare'] = bare_case()

    print(json.dumps(results, indent=1))
    cli('stop')


if __name__ == '__main__':
    main()
