"""Ethereum address rules with the Python standard library only.

Educational code: not constant-time, not audited. Use only test keys.
"""

# --- keccak256 (the pre-NIST Keccak padding 0x01, not SHA3-256's 0x06) ---
_RC = [0x0000000000000001, 0x0000000000008082, 0x800000000000808A, 0x8000000080008000,
       0x000000000000808B, 0x0000000080000001, 0x8000000080008081, 0x8000000000008009,
       0x000000000000008A, 0x0000000000000088, 0x0000000080008009, 0x000000008000000A,
       0x000000008000808B, 0x800000000000008B, 0x8000000000008089, 0x8000000000008003,
       0x8000000000008002, 0x8000000000000080, 0x000000000000800A, 0x800000008000000A,
       0x8000000080008081, 0x8000000000008080, 0x0000000080000001, 0x8000000080008008]
_ROT = [[0, 36, 3, 41, 18], [1, 44, 10, 45, 2], [62, 6, 43, 15, 61],
        [28, 55, 25, 21, 56], [27, 20, 39, 8, 14]]
_M = (1 << 64) - 1


def _rol(v, n):
    return ((v << n) | (v >> (64 - n))) & _M if n else v


def _keccak_f(a):
    for rc in _RC:
        c = [a[x][0] ^ a[x][1] ^ a[x][2] ^ a[x][3] ^ a[x][4] for x in range(5)]
        d = [c[x - 1] ^ _rol(c[(x + 1) % 5], 1) for x in range(5)]
        a = [[a[x][y] ^ d[x] for y in range(5)] for x in range(5)]
        b = [[0] * 5 for _ in range(5)]
        for x in range(5):
            for y in range(5):
                b[y][(2 * x + 3 * y) % 5] = _rol(a[x][y], _ROT[x][y])
        a = [[b[x][y] ^ (~b[(x + 1) % 5][y] & b[(x + 2) % 5][y]) for y in range(5)]
             for x in range(5)]
        a[0][0] ^= rc
    return a


def keccak256(data: bytes) -> bytes:
    rate = 136
    msg = bytearray(data) + b'\x01' + b'\x00' * (-(len(data) + 1) % rate)
    msg[-1] |= 0x80
    a = [[0] * 5 for _ in range(5)]
    for off in range(0, len(msg), rate):
        for i in range(rate // 8):
            a[i % 5][i // 5] ^= int.from_bytes(msg[off + 8 * i:off + 8 * i + 8], 'little')
        a = _keccak_f(a)
    return b''.join(a[i % 5][i // 5].to_bytes(8, 'little') for i in range(4))


# --- secp256k1: private key -> uncompressed public key (x, y) ---
P = 2**256 - 2**32 - 977
N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
G = (0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798,
     0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8)


def _add(p, q):
    if p is None:
        return q
    if q is None:
        return p
    if p[0] == q[0] and (p[1] + q[1]) % P == 0:
        return None
    if p == q:
        m = 3 * p[0] * p[0] * pow(2 * p[1], -1, P) % P
    else:
        m = (q[1] - p[1]) * pow(q[0] - p[0], -1, P) % P
    x = (m * m - p[0] - q[0]) % P
    return x, (m * (p[0] - x) - p[1]) % P


def public_key(private_key: int):
    assert 0 < private_key < N
    point, addend = None, G
    while private_key:
        if private_key & 1:
            point = _add(point, addend)
        addend = _add(addend, addend)
        private_key >>= 1
    return point


# --- the three address rules ---
def eoa_address(private_key: int) -> bytes:
    x, y = public_key(private_key)
    return keccak256(x.to_bytes(32, 'big') + y.to_bytes(32, 'big'))[-20:]


def _rlp_bytes(b: bytes) -> bytes:
    if len(b) == 1 and b[0] < 0x80:
        return b
    assert len(b) < 56
    return bytes([0x80 + len(b)]) + b


def create_address(sender: bytes, nonce: int) -> bytes:
    # nonce is an RLP integer: 0 is the empty string, no leading zero bytes
    nonce_bytes = nonce.to_bytes((nonce.bit_length() + 7) // 8, 'big')
    payload = _rlp_bytes(sender) + _rlp_bytes(nonce_bytes)
    return keccak256(bytes([0xc0 + len(payload)]) + payload)[-20:]


def create2_address(sender: bytes, salt: bytes, initcode: bytes) -> bytes:
    assert len(sender) == 20 and len(salt) == 32
    return keccak256(b'\xff' + sender + salt + keccak256(initcode))[-20:]


def checksum(address: bytes) -> str:
    """EIP-55: the case of each hex letter comes from keccak256 of the lowercase hex."""
    hexaddr = address.hex()
    h = keccak256(hexaddr.encode()).hex()
    return '0x' + ''.join(c.upper() if int(h[i], 16) >= 8 else c for i, c in enumerate(hexaddr))
