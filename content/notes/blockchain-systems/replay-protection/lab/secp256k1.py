"""secp256k1 ECDSA for the lab: signing (RFC 6979 nonces, low-s) and public key recovery.

Pure Python and unoptimized. It is a teaching aid, not constant-time code: never use it
with keys that protect anything of value.
"""
import hashlib
import hmac

from keccak import keccak256

P = 2**256 - 2**32 - 977
N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
G = (0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798,
     0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8)


def _add(a, b):
    if a is None:
        return b
    if b is None:
        return a
    if a[0] == b[0] and (a[1] + b[1]) % P == 0:
        return None
    if a == b:
        lam = 3 * a[0] * a[0] * pow(2 * a[1], -1, P) % P
    else:
        lam = (b[1] - a[1]) * pow(b[0] - a[0], -1, P) % P
    x = (lam * lam - a[0] - b[0]) % P
    return x, (lam * (a[0] - x) - a[1]) % P


def _mul(k, pt):
    out = None
    while k:
        if k & 1:
            out = _add(out, pt)
        pt = _add(pt, pt)
        k >>= 1
    return out


def address_of(point):
    """Ethereum address: the last 20 bytes of keccak256(x || y)."""
    return '0x' + keccak256(point[0].to_bytes(32, 'big') + point[1].to_bytes(32, 'big'))[-20:].hex()


def address_from_key(key):
    return address_of(_mul(key, G))


def _rfc6979_k(key, h):
    x, m = key.to_bytes(32, 'big'), h
    v, k = b'\x01' * 32, b'\x00' * 32
    k = hmac.new(k, v + b'\x00' + x + m, hashlib.sha256).digest()
    v = hmac.new(k, v, hashlib.sha256).digest()
    k = hmac.new(k, v + b'\x01' + x + m, hashlib.sha256).digest()
    v = hmac.new(k, v, hashlib.sha256).digest()
    while True:
        v = hmac.new(k, v, hashlib.sha256).digest()
        cand = int.from_bytes(v, 'big')
        if 1 <= cand < N:
            return cand
        k = hmac.new(k, v + b'\x00', hashlib.sha256).digest()
        v = hmac.new(k, v, hashlib.sha256).digest()


def sign(key, h):
    """Sign a 32-byte hash. Returns (y_parity, r, s) with s in the lower half (EIP-2)."""
    z = int.from_bytes(h, 'big')
    k = _rfc6979_k(key, h)
    R = _mul(k, G)
    r = R[0] % N
    s = pow(k, -1, N) * (z + r * key) % N
    parity = R[1] & 1
    if s > N // 2:
        s, parity = N - s, parity ^ 1
    return parity, r, s


def recover(h, parity, r, s):
    """Recover the signer's address from a hash and a signature (what ecrecover does)."""
    x = r
    y = pow((x * x * x + 7) % P, (P + 1) // 4, P)
    if y & 1 != parity:
        y = P - y
    z = int.from_bytes(h, 'big')
    rinv = pow(r, -1, N)
    q = _add(_mul(s * rinv % N, (x, y)), _mul((-z * rinv) % N, G))
    return address_of(q)
