"""Verify the mainnet genesis header, then change its nonce. No network access.
Reference: Bitcoin Core v30.0 src/kernel/chainparams.cpp (genesis constants).
This checks only the hash/target comparison, not full block validity.
"""
from hashlib import sha256
from pathlib import Path
import struct

merkle_root = '4a5e1e4baab89f3a32518a88c31bc87f618f76673e2cc77ab2127b7afdeda33b'
bits = 0x1d00ffff
nonce = 2083236893
header = (struct.pack('<I', 1) + bytes(32)
          + bytes.fromhex(merkle_root)[::-1]
          + struct.pack('<III', 1231006505, bits, nonce))
assert len(header) == 80
# For this known positive compact target (exponent >= 3).
# This is not a general-purpose decoder for untrusted nBits values.
exponent = bits >> 24
coefficient = bits & 0x007fffff
target = coefficient << (8 * (exponent - 3))


def block_hash(data):
    return sha256(sha256(data).digest()).digest()


original = block_hash(header)
assert original[::-1].hex() == '000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f'
changed = block_hash(header[:76] + struct.pack('<I', nonce + 1))
assert int.from_bytes(original, 'little') <= target
assert int.from_bytes(changed, 'little') > target
lines = [
    f'header_bytes={len(header)}',
    f'bits={bits:08x}',
    f'target={target:064x}',
    f'nonce={nonce}',
    f'hash={original[::-1].hex()}',
    'hash <= target: PASS',
    f'changed_nonce={nonce + 1}',
    f'changed_hash={changed[::-1].hex()}',
    'changed_hash <= target: FAIL',
    'Assertions: PASS',
]
summary = '\n'.join(lines) + '\n'
Path(__file__).with_name('output.txt').write_text(summary)
print(summary, end='')
