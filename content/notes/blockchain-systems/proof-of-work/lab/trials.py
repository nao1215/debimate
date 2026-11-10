"""Count trials until a double SHA-256 falls at or below target = 2^(256-k). No network access."""
from hashlib import sha256
import random
import statistics
import struct

K, RUNS = 16, 1000
target = 2 ** (256 - K) - 1  # about 2^(256-k), so the pass rate is 2^-k
rng = random.Random(20260810)
counts = []
for _ in range(RUNS):
    header76 = rng.randbytes(76)  # random stand-in for the first 76 bytes of a header
    for nonce in range(2**32):
        h = sha256(sha256(header76 + struct.pack('<I', nonce)).digest()).digest()
        if int.from_bytes(h, 'little') <= target:
            counts.append(nonce + 1)
            break
print(f'k={K} runs={RUNS} expected={2**K}')
print(f'min={min(counts)} median={statistics.median(counts):.0f} '
      f'mean={statistics.mean(counts):.0f} max={max(counts)}')
