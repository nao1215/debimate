"""Check the proof of work of Bitcoin's genesis block with one double SHA-256.

The header fields are the values in Bitcoin Core's chainparams.cpp
(CreateGenesisBlock(1231006505, 2083236893, 0x1d00ffff, 1, 50 * COIN)).
"""
import hashlib
import struct

version = 1
prev = bytes(32)
merkle = bytes.fromhex("4a5e1e4baab89f3a32518a88c31bc87f618f76673e2cc77ab2127b7afdeda33b")[::-1]
time, bits, nonce = 1231006505, 0x1d00ffff, 2083236893

header = struct.pack("<I", version) + prev + merkle + struct.pack("<III", time, bits, nonce)
digest = hashlib.sha256(hashlib.sha256(header).digest()).digest()
value = int.from_bytes(digest, "little")

# bits: 1 byte of exponent and 3 bytes of mantissa (genesis only;
# a general decoder must also reject the sign bit 0x00800000 and out-of-range values)
target = (bits & 0xFFFFFF) << (8 * ((bits >> 24) - 3))
expected = 2 ** 256 // (target + 1)          # GetBlockProof in Bitcoin Core v30.0

print("header bytes :", len(header))
print("hash         :", digest[::-1].hex())
print("target       :", f"{target:064x}")
print("hash <= target:", value <= target)
print("leading zero bits:", 256 - value.bit_length())
print(f"expected trials : {expected:,}")
