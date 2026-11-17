"""UTXO experiments with real signed P2WPKH transactions, Python 3 standard library only.

The script builds and signs Bitcoin SegWit v0 (P2WPKH) transactions itself
(secp256k1 ECDSA with RFC 6979 nonces, BIP 143 signature hash), measures their
virtual size, and applies them to a small UTXO set that checks inputs and
signatures. It never connects to any network and uses throwaway keys derived
from fixed labels.

The BIP 143 "Native P2WPKH" test vector is checked first, so the signature hash
and the signature match what Bitcoin nodes compute.

    python3 utxo_lab.py        # writes output/results.json and output/summary.txt

Policy numbers (dust threshold, effective value) follow Bitcoin Core v30.0:
src/policy/policy.cpp GetDustThreshold and src/wallet/spend.cpp GroupOutputs.
"""
import hashlib
import hmac
import json
import math
from pathlib import Path

# --- secp256k1 / ECDSA -------------------------------------------------------
P = 2**256 - 2**32 - 977
N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
G = (0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798,
     0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8)


def point_add(a, b):
    if a is None:
        return b
    if b is None:
        return a
    if a[0] == b[0] and (a[1] + b[1]) % P == 0:
        return None
    if a == b:
        m = 3 * a[0] * a[0] * pow(2 * a[1], P - 2, P)
    else:
        m = (b[1] - a[1]) * pow(b[0] - a[0], P - 2, P)
    x = (m * m - a[0] - b[0]) % P
    return x, (m * (a[0] - x) - a[1]) % P


def point_mul(k, point=G):
    result = None
    while k:
        if k & 1:
            result = point_add(result, point)
        point = point_add(point, point)
        k >>= 1
    return result


def pubkey(secret):
    x, y = point_mul(secret)
    return bytes([2 + (y & 1)]) + x.to_bytes(32, 'big')


def rfc6979_k(secret, digest):
    x, h = secret.to_bytes(32, 'big'), digest
    v, k = b'\x01' * 32, b'\x00' * 32
    k = hmac.new(k, v + b'\x00' + x + h, hashlib.sha256).digest()
    v = hmac.new(k, v, hashlib.sha256).digest()
    k = hmac.new(k, v + b'\x01' + x + h, hashlib.sha256).digest()
    v = hmac.new(k, v, hashlib.sha256).digest()
    while True:
        v = hmac.new(k, v, hashlib.sha256).digest()
        candidate = int.from_bytes(v, 'big')
        if 1 <= candidate < N:
            return candidate
        k = hmac.new(k, v + b'\x00', hashlib.sha256).digest()
        v = hmac.new(k, v, hashlib.sha256).digest()


def der_int(value):
    raw = value.to_bytes(32, 'big').lstrip(b'\x00') or b'\x00'
    if raw[0] & 0x80:
        raw = b'\x00' + raw
    return b'\x02' + bytes([len(raw)]) + raw


def sign(secret, digest):
    k = rfc6979_k(secret, digest)
    r = point_mul(k)[0] % N
    s = pow(k, N - 2, N) * (int.from_bytes(digest, 'big') + r * secret) % N
    s = min(s, N - s)  # low-S, required by standardness rules
    body = der_int(r) + der_int(s)
    return b'\x30' + bytes([len(body)]) + body


def verify(pub, digest, der):
    rlen = der[3]
    r = int.from_bytes(der[4:4 + rlen], 'big')
    s = int.from_bytes(der[6 + rlen:], 'big')
    x = int.from_bytes(pub[1:], 'big')
    y = pow(x ** 3 + 7, (P + 1) // 4, P)
    if y & 1 != pub[0] & 1:
        y = P - y
    w = pow(s, N - 2, N)
    z = int.from_bytes(digest, 'big')
    point = point_add(point_mul(z * w % N), point_mul(r * w % N, (x, y)))
    return point is not None and point[0] % N == r


# --- transaction format --------------------------------------------------------
def sha256d(data):
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()


def hash160(data):
    return hashlib.new('ripemd160', hashlib.sha256(data).digest()).digest()


def varint(n):
    if n < 0xfd:
        return bytes([n])
    return b'\xfd' + n.to_bytes(2, 'little') if n <= 0xffff else b'\xfe' + n.to_bytes(4, 'little')


def p2wpkh_script(pub):
    return b'\x00\x14' + hash160(pub)


def bip143_sighash(tx, index, script_code, amount):
    prevouts = b''.join(i['txid'][::-1] + i['vout'].to_bytes(4, 'little') for i in tx['vin'])
    sequences = b''.join(i['sequence'].to_bytes(4, 'little') for i in tx['vin'])
    outputs = b''.join(o['value'].to_bytes(8, 'little') + varint(len(o['script'])) + o['script']
                       for o in tx['vout'])
    txin = tx['vin'][index]
    preimage = (tx['version'].to_bytes(4, 'little') + sha256d(prevouts) + sha256d(sequences)
                + txin['txid'][::-1] + txin['vout'].to_bytes(4, 'little')
                + varint(len(script_code)) + script_code + amount.to_bytes(8, 'little')
                + txin['sequence'].to_bytes(4, 'little') + sha256d(outputs)
                + tx['locktime'].to_bytes(4, 'little') + (1).to_bytes(4, 'little'))
    return sha256d(preimage)


def serialize(tx, with_witness=True):
    body = varint(len(tx['vin'])) + b''.join(
        i['txid'][::-1] + i['vout'].to_bytes(4, 'little') + varint(len(i.get('script_sig', b'')))
        + i.get('script_sig', b'') + i['sequence'].to_bytes(4, 'little') for i in tx['vin'])
    body += varint(len(tx['vout'])) + b''.join(
        o['value'].to_bytes(8, 'little') + varint(len(o['script'])) + o['script'] for o in tx['vout'])
    head = tx['version'].to_bytes(4, 'little')
    tail = tx['locktime'].to_bytes(4, 'little')
    if not with_witness:
        return head + body + tail
    witness = b''.join(varint(len(i['witness'])) + b''.join(varint(len(item)) + item for item in i['witness'])
                       for i in tx['vin'])
    return head + b'\x00\x01' + body + witness + tail


def vsize(tx):
    weight = len(serialize(tx, False)) * 3 + len(serialize(tx))
    return math.ceil(weight / 4)


def txid(tx):
    return sha256d(serialize(tx, False))[::-1]


# --- keys, a wallet, and a UTXO set ---------------------------------------------
class Key:
    def __init__(self, label):
        self.secret = int.from_bytes(hashlib.sha256(label.encode()).digest(), 'big') % N
        self.pub = pubkey(self.secret)
        self.script = p2wpkh_script(self.pub)


class UtxoSet:
    """Outpoint (txid, vout) -> (value, script). Applies transactions like a node would."""

    def __init__(self):
        self.coins = {}

    def apply(self, tx):
        spent = 0
        for index, txin in enumerate(tx['vin']):
            outpoint = (txin['txid'], txin['vout'])
            if outpoint not in self.coins:
                return f'rejected: input {index} is not in the UTXO set'
            value, script = self.coins[outpoint]
            sig, pub = txin['witness']
            code = b'\x76\xa9\x14' + script[2:] + b'\x88\xac'
            if p2wpkh_script(pub) != script or not verify(pub, bip143_sighash(tx, index, code, value), sig[:-1]):
                return f'rejected: input {index} has a bad signature'
            spent += value
        created = sum(o['value'] for o in tx['vout'])
        if created > spent:
            return 'rejected: outputs exceed inputs'
        for txin in tx['vin']:
            del self.coins[(txin['txid'], txin['vout'])]
        new_id = txid(tx)
        for n, o in enumerate(tx['vout']):
            self.coins[(new_id, n)] = (o['value'], o['script'])
        return f'accepted: fee {spent - created} sat'


def build(coins, key, outputs, signed=True):
    """coins: list of (txid, vout, value). outputs: list of (value, script).

    signed=False puts a 72-byte placeholder in each witness (a typical DER signature
    plus the sighash byte), which is how wallets estimate the size before signing."""
    tx = {'version': 2, 'locktime': 0,
          'vin': [{'txid': t, 'vout': v, 'sequence': 0xfffffffd} for t, v, _ in coins],
          'vout': [{'value': value, 'script': script} for value, script in outputs]}
    code = b'\x76\xa9\x14' + key.script[2:] + b'\x88\xac'
    for index, (_, _, value) in enumerate(coins):
        if not signed:
            tx['vin'][index]['witness'] = [bytes(72), key.pub]
            continue
        sig = sign(key.secret, bip143_sighash(tx, index, code, value))
        tx['vin'][index]['witness'] = [sig + b'\x01', key.pub]
    return tx


def fund(utxo, key, values, label):
    """Create coins for `key` out of thin air (stands in for earlier payments to the wallet)."""
    fake = hashlib.sha256(label.encode()).digest()
    for n, value in enumerate(values):
        utxo.coins[(fake, n)] = (value, key.script)
    return [(fake, n, value) for n, value in enumerate(values)]


def pay(coins, key, amount, to_script, rate):
    """Largest-first selection until inputs cover amount + fee; change back to `key`."""
    coins = sorted(coins, key=lambda c: -c[2])
    for count in range(1, len(coins) + 1):
        chosen = coins[:count]
        total = sum(c[2] for c in chosen)
        draft = build(chosen, key, [(amount, to_script), (0, key.script)], signed=False)
        fee = vsize(draft) * rate
        if total >= amount + fee:
            tx = build(chosen, key, [(amount, to_script), (total - amount - fee, key.script)])
            return tx, fee
    raise ValueError('insufficient funds')


def sweep(coins, key, to_script, rate, send_max):
    """Like Bitcoin Core sendall: one output; send_max drops coins that cannot pay for themselves."""
    spend = [c for c in coins if not send_max or c[2] - rate * INPUT_VB > 0]
    if not spend:
        return None
    draft = build(spend, key, [(0, to_script)], signed=False)
    fee = vsize(draft) * rate
    total = sum(c[2] for c in spend)
    return {'inputs': len(spend), 'vsize': vsize(draft), 'fee': fee, 'received': total - fee}


def dust_threshold(output_script, rate_sat_per_kvb=3000):
    """Bitcoin Core GetDustThreshold for witness outputs."""
    out_size = 8 + 1 + len(output_script)
    return (out_size + 32 + 4 + 1 + 107 // 4 + 4) * rate_sat_per_kvb // 1000


# --- BIP 143 test vector -------------------------------------------------------
def check_bip143():
    k = 0x619c335025c7f4012e556c2a58b2506e30b8511b53ade95ea316fd8c3286feb9
    assert pubkey(k).hex() == '025476c2e83188368da1ff3e292e7acafcdb3566bb0ad253f62fc70f07aeee6357'
    tx = {'version': 1, 'locktime': 17, 'vin': [
        {'txid': bytes.fromhex('fff7f7881a8099afa6940d42d1e7f6362bec38171ea3edf433541db4e4ad969f')[::-1], 'vout': 0, 'sequence': 0xffffffee},
        {'txid': bytes.fromhex('ef51e1b804cc89d182d279655c3aa89e815b1b309fe287d9b2b55d57b90ec68a')[::-1], 'vout': 1, 'sequence': 0xffffffff}],
        'vout': [{'value': 112340000, 'script': bytes.fromhex('76a9148280b37df378db99f66f85c95a783a76ac7a6d5988ac')},
                 {'value': 223450000, 'script': bytes.fromhex('76a9143bde42dbee7e4dbe6a21b2d50ce2f0167faa815988ac')}]}
    code = bytes.fromhex('76a9141d0f172a0ecb48aee1be1f2687d2963ae33f71a188ac')
    digest = bip143_sighash(tx, 1, code, 600000000)
    assert digest.hex() == 'c37af31116d1b27caf68aae9e3ac82f1477929014d5b917657d0eb49478cb670'
    sig = sign(k, digest)
    assert verify(pubkey(k), digest, sig)
    return sig.hex() == ('304402203609e17b84f6a7d30c80bfa610b5b4542f32a8a0d5447a12fb1366d7f01cc44a'
                         '0220573a954c4518331561406f90300e8f3358f51928d43c212a8caed02de67eebee')


def main():
    global INPUT_VB
    results = {'bip143_sighash': 'match', 'bip143_signature_rfc6979': 'match' if check_bip143() else 'differs'}
    utxo = UtxoSet()
    alice, bob, carol, shop = Key('alice'), Key('bob'), Key('carol'), Key('shop')
    BTC = 100_000_000

    # Marginal size of one P2WPKH input.
    probe = fund(utxo, alice, [10_000] * 3, 'probe')
    one_in, two_in = (vsize(build(probe[:n], alice, [(1, bob.script)], signed=False)) for n in (1, 2))
    INPUT_VB = two_in - one_in
    for c in probe:
        del utxo.coins[(c[0], c[1])]
    results['input_vbytes'] = INPUT_VB

    # 1. Same balance (1 BTC), different coins. Send 0.9 BTC at 10 sat/vB.
    one = fund(utxo, alice, [BTC], 'one')
    many = fund(utxo, carol, [BTC // 200] * 200, 'many')
    payments = {}
    for name, coins, key in [('one', one, alice), ('many', many, carol)]:
        tx, fee = pay(coins, key, 90_000_000, bob.script, 10)
        base = len(serialize(tx, False))
        payments[name] = {'coins_before': len(coins), 'balance_sat': sum(c[2] for c in coins),
                          'inputs': len(tx['vin']), 'outputs': len(tx['vout']), 'vsize': vsize(tx),
                          'fee_sat': fee, 'change_sat': tx['vout'][1]['value'],
                          'inputs_share': round(1 - (vsize(build([coins[0]], key, [(1, bob.script), (1, key.script)], signed=False)) - INPUT_VB) / vsize(tx), 3),
                          'base_bytes': base, 'total_bytes': len(serialize(tx)),
                          'result': utxo.apply(tx)}
        payments[name]['coins_after'] = sum(1 for v in utxo.coins.values() if v[1] == key.script)
        if name == 'one':
            results['one_tx'] = tx
    results['payment'] = payments

    # 2. Double spend: a second transaction that uses Alice's original 1 BTC coin again.
    again = build(one, alice, [(BTC - 2_000, shop.script)])
    results['double_spend'] = utxo.apply(again)
    first_out = (txid(results.pop('one_tx')), 1)
    value, _ = utxo.coins[first_out]
    change_coin = [(first_out[0], first_out[1], value)]
    results['spend_change'] = utxo.apply(build(change_coin, alice, [(value - 2_000, shop.script)]))

    # 3. A shop that received 100 payments of 1,000 sat. What can it send at each fee rate?
    small = fund(utxo, shop, [1_000] * 100, 'small')
    curve = []
    for rate in [1, 2, 4, 6, 8, 10, 12, 13, 14, 15, 16, 18, 20, 25, 30]:
        row = {'fee_rate': rate}
        for mode in [False, True]:
            r = sweep(small, shop, bob.script, rate, mode)
            row['send_max' if mode else 'all'] = r
        curve.append(row)
    results['small_coins'] = {'coins': 100, 'value_each': 1_000, 'balance': 100_000, 'curve': curve,
                              'break_even_rate': 1_000 / INPUT_VB}

    # 4. Dust thresholds (Bitcoin Core default dustrelayfee = 3,000 sat/kvB).
    results['dust_threshold'] = {
        'P2WPKH': dust_threshold(bob.script),
        'P2TR': dust_threshold(b'\x51\x20' + bytes(32)),
        'P2PKH': (34 + 148) * 3000 // 1000,
    }
    results['utxo_set_size'] = len(utxo.coins)
    return results


if __name__ == '__main__':
    res = main()
    out = Path(__file__).resolve().parent / 'output'
    out.mkdir(exist_ok=True)
    (out / 'results.json').write_text(json.dumps(res, indent=2, ensure_ascii=False) + '\n')
    p = res['payment']
    lines = [f"BIP143 vector: sighash {res['bip143_sighash']}, signature {res['bip143_signature_rfc6979']}",
             f"one P2WPKH input = {res['input_vbytes']} vB"]
    for w in ['one', 'many']:
        lines.append(f"{w}: balance={p[w]['balance_sat']} sat in {p[w]['coins_before']} coins -> send 90000000 sat at 10 sat/vB: "
                     f"inputs={p[w]['inputs']} vsize={p[w]['vsize']} vB fee={p[w]['fee_sat']} sat "
                     f"change={p[w]['change_sat']} sat coins_after={p[w]['coins_after']} ({p[w]['result']})")
    lines.append(f"spend alice's 1 BTC coin again: {res['double_spend']}")
    lines.append(f"spend alice's change coin: {res['spend_change']}")
    for row in res['small_coins']['curve']:
        a, m = row['all'], row['send_max']
        lines.append(f"100 x 1000 sat at {row['fee_rate']:>2} sat/vB: all inputs -> {a['received'] if a else 0} sat"
                     f" | send_max -> {m['received'] if m else 0} sat ({m['inputs'] if m else 0} inputs)")
    lines.append(f"break-even fee rate = {res['small_coins']['break_even_rate']:.1f} sat/vB")
    lines.append(f"dust threshold: {res['dust_threshold']}")
    (out / 'summary.txt').write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines))
