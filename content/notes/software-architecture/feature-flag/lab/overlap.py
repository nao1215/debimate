"""Two flags at 10%: how many users get both, and who stays in when the percentage goes up.

  shared   murmur3("user") % 100 + 1 <= p       the same number for every flag
  per-flag murmur3("flag:user") % 100 + 1 <= p  Unleash's gradual rollout

Run: python overlap.py
"""

USERS = [f"u-{i:06d}" for i in range(100_000)]
FLAGS = ["new-checkout", "new-search"]


def murmur3_32(data: bytes, seed: int = 0) -> int:
    """MurmurHash3 x86 32-bit, the hash Unleash's SDKs use."""
    c1, c2, h = 0xCC9E2D51, 0x1B873593, seed
    n = len(data) // 4 * 4
    for i in range(0, n, 4):
        k = int.from_bytes(data[i:i + 4], "little")
        k = (k * c1) & 0xFFFFFFFF
        k = ((k << 15) | (k >> 17)) & 0xFFFFFFFF
        k = (k * c2) & 0xFFFFFFFF
        h ^= k
        h = ((h << 13) | (h >> 19)) & 0xFFFFFFFF
        h = (h * 5 + 0xE6546B64) & 0xFFFFFFFF
    k = 0
    tail = data[n:]
    for i, b in enumerate(tail):
        k |= b << (8 * i)
    if tail:
        k = (k * c1) & 0xFFFFFFFF
        k = ((k << 15) | (k >> 17)) & 0xFFFFFFFF
        k = (k * c2) & 0xFFFFFFFF
        h ^= k
    h ^= len(data)
    h ^= h >> 16
    h = (h * 0x85EBCA6B) & 0xFFFFFFFF
    h ^= h >> 13
    h = (h * 0xC2B2AE35) & 0xFFFFFFFF
    h ^= h >> 16
    return h


assert murmur3_32(b"hello") == 0x248BFA47


def shared(flag: str, user: str, p: int) -> bool:
    return murmur3_32(user.encode()) % 100 + 1 <= p


def per_flag(flag: str, user: str, p: int) -> bool:
    return murmur3_32(f"{flag}:{user}".encode()) % 100 + 1 <= p


if __name__ == "__main__":
    for name, rule in [("shared", shared), ("per-flag", per_flag)]:
        a = {u for u in USERS if rule(FLAGS[0], u, 10)}
        b = {u for u in USERS if rule(FLAGS[1], u, 10)}
        print(f"== {name}")
        print(f"  {FLAGS[0]} on {len(a)} ({len(a) / len(USERS):.1%}), {FLAGS[1]} on {len(b)}")
        print(f"  both on {len(a & b)} ({len(a & b) / len(USERS):.2%} of users,"
              f" {len(a & b) / len(a):.1%} of {FLAGS[0]})")
        prev = a
        for p in [20, 50, 100]:
            now = {u for u in USERS if rule(FLAGS[0], u, p)}
            print(f"  {FLAGS[0]} 10% -> {p}%: on {len(now)}, still on {len(prev & now)} of {len(prev)}")
