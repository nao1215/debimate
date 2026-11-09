"""Reproduce the four header values without network access.
Run: python3 verify-headers.py
Genesis: https://github.com/bitcoin/bitcoin/blob/master/src/kernel/chainparams.cpp
Block 1: https://blockstream.info/api/block/00000000839a8e6886ab5951d76f411475428afc90947ee320161bbf18eb6048/header
"""

from hashlib import sha256
import struct, sys


def block_hash(header):
    assert len(header) == 80
    return sha256(sha256(header).digest()).digest()[::-1].hex()


# Genesis fields from Bitcoin Core src/kernel/chainparams.cpp.
merkle = bytes.fromhex("4a5e1e4baab89f3a32518a88c31bc87f618f76673e2cc77ab2127b7afdeda33b")[::-1]
genesis = (
    struct.pack("<I", 1)
    + bytes(32)
    + merkle
    + struct.pack("<III", 1231006505, 0x1D00FFFF, 2083236893)
)
block1 = bytes.fromhex(
    '010000006fe28c0ab6f1b372c1a6a246ae63f74f931e8365e15a089c68d6190000000000982051fd1e4ba744bbbe680e1fee14677ba1a3c3540bf7b1cdb606e857233e0e61bc6649ffff001d01e36299'
)
changed = genesis[:68] + struct.pack("<I", 1231006506) + genesis[72:]
actual = [block_hash(genesis), block1[4:36][::-1].hex(), block_hash(block1), block_hash(changed)]
expected = [
    "000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f",
    "000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f",
    "00000000839a8e6886ab5951d76f411475428afc90947ee320161bbf18eb6048",
    "775212d740bc3900e6c050f43c2cb2db9218b3981e5d11bb0abadf9d9f164b69",
]
assert actual == expected
labels = ["block0_hash", "block1_prev_hash", "block1_hash", "block0_time+1s_hash"]
print(sys.version)
for label, value in zip(labels, actual):
    print(f"{label:<20} {value}")
print('PASS: all 4 article values match')
