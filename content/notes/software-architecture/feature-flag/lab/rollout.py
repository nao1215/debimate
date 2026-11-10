"""Percentage rollout: hash of user ID vs. a coin flip on every request.

Simulation (not a measurement of any product). Assumptions:
- 100,000 users with IDs "user-000000" .. "user-099999".
- Rollout stages: 1% -> 5% -> 25% -> 100% of users.
- Each user sends 10 requests during each stage.
- hash:   bucket = first 8 bytes of SHA-256("new-checkout:" + user_id) mod 10000,
          the new feature is on when bucket < percent * 100.
- random: the new feature is on with probability percent / 100 on every
          request (random.Random(42)), independent of the user.
- "mixed" counts users who saw both the old and the new checkout within
          one stage.
- The new feature is assumed to be broken, so "exposed" means the user hit
          the bug at least once during the stage.
"""

import hashlib
import random

USERS = [f"user-{i:06d}" for i in range(100_000)]
STAGES = [1, 5, 25, 100]
REQUESTS = 10
FLAG = "new-checkout"


def bucket(user_id):
    digest = hashlib.sha256(f"{FLAG}:{user_id}".encode()).digest()
    return int.from_bytes(digest[:8], "big") % 10_000


def run():
    buckets = {u: bucket(u) for u in USERS}
    rng = random.Random(42)
    rows = []
    prev_hash = set()
    for pct in STAGES:
        on_hash, exposed = set(), set()
        hash_mixed = mixed = 0
        for u in USERS:
            # hash: evaluated on every request, but depends only on the user.
            h_hits = sum(buckets[u] < pct * 100 for _ in range(REQUESTS))
            # random: each request decides on its own.
            hits = sum(rng.random() < pct / 100 for _ in range(REQUESTS))
            if h_hits:
                on_hash.add(u)
            if 0 < h_hits < REQUESTS:
                hash_mixed += 1
            if hits:
                exposed.add(u)
            if 0 < hits < REQUESTS:
                mixed += 1
        rows.append({
            "pct": pct,
            "hash_exposed": len(on_hash),
            "hash_mixed": hash_mixed,
            "hash_keeps_previous": prev_hash <= on_hash,
            "random_exposed": len(exposed),
            "random_mixed": mixed,
        })
        prev_hash = on_hash
    return rows


def main():
    print(f"users={len(USERS)} requests_per_user_per_stage={REQUESTS}")
    print("stage  hash_exposed  hash_mixed  keeps_previous  "
          "random_exposed  random_mixed")
    for r in run():
        print(f"{r['pct']:>4}%  {r['hash_exposed']:>12}  {r['hash_mixed']:>10}  "
              f"{str(r['hash_keeps_previous']):>14}  {r['random_exposed']:>14}  "
              f"{r['random_mixed']:>12}")


if __name__ == "__main__":
    main()
