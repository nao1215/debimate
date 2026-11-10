"""Rule-only simulation (no client): how many signers keep Clique and QBFT going.

Clique: one signer per SIGNER_LIMIT = N // 2 + 1 consecutive blocks; the online
signer that signed longest ago signs next. QBFT: quorum of ceil(2N / 3).
"""


def clique_blocks(n, online, steps=100):
    """Number of blocks `online` of `n` signers can add after a fresh start."""
    limit = n // 2 + 1
    recent = []  # signers of the latest blocks, newest last
    for made in range(steps):
        window = recent[-(limit - 1):] if limit > 1 else []
        free = [s for s in range(online) if s not in window]
        if not free:
            return made  # every online signer signed too recently
        last = {s: max([i for i, r in enumerate(recent) if r == s], default=-1)
                for s in free}
        recent.append(min(free, key=lambda s: last[s]))
    return steps


def qbft_quorum(n):
    return -(-2 * n // 3)  # ceil(2n/3)


print(" N | SIGNER_LIMIT | Clique min online | QBFT quorum (min online)")
for n in range(1, 11):
    need = min(k for k in range(1, n + 1) if clique_blocks(n, k) == 100)
    print(f"{n:2} | {n // 2 + 1:12} | {need:17} | {qbft_quorum(n):11}")

print()
print("Clique, N=4: blocks a group of k signers can add on its own")
for k in range(1, 5):
    got = clique_blocks(4, k)
    print(f"  k={k}: {got if got < 100 else 'unbounded'}")
