"""Mine a toy chain with Bitcoin's header layout and double SHA-256.

The target is 2**240, so one hash passes with probability 2**-16 and a block
needs 65,536 trials on average. The number of trials per block is written to
output/trials.csv. Run: python3 mine.py [blocks]
"""
import hashlib
import struct
import sys

BLOCKS = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
TARGET = 2 ** 240          # 16 leading zero bits
BITS = 0x1f010000          # compact form of 2**240
MERKLE = hashlib.sha256(b"toy merkle root").digest()


def mine(prev, height):
    # version | prev hash | merkle root | time | bits | nonce  (80 bytes)
    head = struct.pack("<I", 0x20000000) + prev + MERKLE
    tail = struct.pack("<II", 1700000000 + height, BITS)
    first = hashlib.sha256(head[:64])          # midstate of the first 64 bytes
    rest = head[64:] + tail
    nonce = 0
    while True:
        h = first.copy()
        h.update(rest + struct.pack("<I", nonce))
        d = hashlib.sha256(h.digest()).digest()
        # the hash is read as a little-endian number: the last 2 bytes are the top 16 bits
        if d[30] == 0 and d[31] == 0:
            assert int.from_bytes(d, "little") < TARGET
            return d, nonce + 1
        nonce += 1


def main():
    prev = bytes(32)
    total = 0
    with open("output/trials.csv", "w") as f:
        f.write("height,trials,hash\n")
        for height in range(1, BLOCKS + 1):
            prev, trials = mine(prev, height)
            total += trials
            f.write(f"{height},{trials},{prev[::-1].hex()}\n")
    print(f"blocks={BLOCKS} hashes={total} mean_trials={total / BLOCKS:.0f} expected=65536")


if __name__ == "__main__":
    main()
