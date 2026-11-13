"""Double spending on a toy chain: an attacker mines a hidden chain.

The honest miners do 3 hashes per tick and the attacker 2 hashes per tick
(q = 40%), on the same 16-bit target as mine.py. With 5 hashes per tick,
13,107 ticks are "10 minutes" (the same scale as fork.py). There is no network
delay.

In each attempt, the first honest block carries the payment to the shop. The
attacker mines from the block before it, with a block that pays the same coin
back to itself, and keeps the chain hidden. The shop hands over the goods when
the payment has Z confirmations. The attacker publishes its chain once it is
longer than the public chain after that point, and gives up when it is GIVE_UP
blocks behind. Run: python3 double_spend.py [attempts]
"""
import hashlib
import json
import struct
import sys

ATTEMPTS = int(sys.argv[1]) if len(sys.argv) > 1 else 200
RATE = {"honest": 3, "attacker": 2}           # hashes per tick
TICK_S = 600 / (65536 / sum(RATE.values()))   # seconds per tick
Z = 2                                          # confirmations the shop waits for
GIVE_UP = 5                                    # blocks behind


class Chain:
    def __init__(self, who, attempt):
        self.merkle = hashlib.sha256(f"{who} {attempt}".encode()).digest()
        self.prev = bytes(32)
        self.height = 0
        self.nonce = 0

    def work(self, n):
        for _ in range(n):
            head = struct.pack("<I", 0x20000000) + self.prev + self.merkle
            tail = struct.pack("<III", 1700000000 + self.height + 1, 0x1f010000, self.nonce)
            d = hashlib.sha256(hashlib.sha256(head + tail).digest()).digest()
            self.nonce += 1
            if d[30] == 0 and d[31] == 0:
                self.prev, self.height, self.nonce = d, self.height + 1, 0
                return True
        return False


def attempt(k):
    chains = {who: Chain(who, k) for who in RATE}
    events, tick, paid_at = [], 0, None
    while True:
        tick += 1
        for who, c in chains.items():
            if c.work(RATE[who]):
                events.append({"tick": tick, "who": who, "height": c.height})
        h, a = chains["honest"].height, chains["attacker"].height
        if paid_at is None and h >= Z:
            paid_at = tick                     # the shop hands over the goods
        if paid_at is not None and a > h:
            return True, tick, paid_at, events # publish: the payment disappears
        if h - a >= GIVE_UP:
            return False, tick, paid_at, events


def main():
    runs = []
    for k in range(ATTEMPTS):
        ok, end, paid_at, events = attempt(k)
        runs.append({"attempt": k, "success": ok, "end": end, "paid": paid_at, "events": events})
    wins = [r for r in runs if r["success"]]
    print(f"q=0.40 z={Z} give_up={GIVE_UP} tick={TICK_S:.4f}s attempts={ATTEMPTS}")
    print(f"success={len(wins)} rate={len(wins) / ATTEMPTS:.3f}")
    json.dump({"tick_s": TICK_S, "z": Z, "give_up": GIVE_UP, "runs": runs},
              open("output/double_spend.json", "w"))


if __name__ == "__main__":
    main()
