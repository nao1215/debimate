"""Two miners hash on a toy chain and see each other's blocks after a delay.

Miner A does 3 hashes per tick and miner B 2 hashes per tick, on the same
16-bit target as mine.py (65,536 trials per block on average). With 5 hashes
per tick, one block every 13,107 ticks is "10 minutes". Each miner mines on the
highest block it knows and keeps the first one it saw when two have the same
height. Run: python3 fork.py [delay_seconds] [blocks]
"""
import hashlib
import json
import struct
import sys

DELAY_S = float(sys.argv[1]) if len(sys.argv) > 1 else 60
BLOCKS = int(sys.argv[2]) if len(sys.argv) > 2 else 600
RATE = {"A": 3, "B": 2}                       # hashes per tick
TICK_S = 600 / (65536 / sum(RATE.values()))   # seconds per tick
DELAY = round(DELAY_S / TICK_S)               # ticks until the other miner sees a block


class Miner:
    def __init__(self, name, genesis):
        self.name = name
        self.merkle = hashlib.sha256(name.encode()).digest()   # each miner pays itself
        self.known = {genesis["hash"]: genesis}
        self.switch(genesis)

    def switch(self, tip):
        self.tip = tip
        self.nonce = 0
        self.head = struct.pack("<I", 0x20000000) + bytes.fromhex(tip["hash"])[::-1] + self.merkle
        self.tail = struct.pack("<II", 1700000000 + tip["height"] + 1, 0x1f010000)

    def work(self, n):
        for _ in range(n):
            d = hashlib.sha256(hashlib.sha256(self.head + self.tail + struct.pack("<I", self.nonce)).digest()).digest()
            self.nonce += 1
            if d[30] == 0 and d[31] == 0:
                return d[::-1].hex()
        return None

    def receive(self, block):
        self.known[block["hash"]] = block
        if block["height"] > self.tip["height"]:   # more work wins; a tie keeps the first seen
            self.switch(block)
            return True
        return False


def main():
    genesis = {"hash": "00" * 32, "height": 0, "parent": None, "miner": None, "tick": 0}
    miners = {n: Miner(n, genesis) for n in RATE}
    blocks, events, inflight = {genesis["hash"]: genesis}, [], []
    tick = 0
    while max(m.tip["height"] for m in miners.values()) < BLOCKS:
        tick += 1
        for at, to, block in [x for x in inflight if x[0] == tick]:
            switched = miners[to].receive(block)
            events.append({"tick": tick, "type": "recv", "miner": to, "hash": block["hash"], "switched": switched})
        inflight = [x for x in inflight if x[0] > tick]
        for name, m in miners.items():
            h = m.work(RATE[name])
            if h:
                block = {"hash": h, "height": m.tip["height"] + 1, "parent": m.tip["hash"], "miner": name, "tick": tick}
                blocks[h] = block
                m.known[h] = block
                m.switch(block)
                events.append({"tick": tick, "type": "found", "miner": name, "hash": h})
                for other in miners:
                    if other != name:
                        inflight.append((tick + DELAY, other, block))
    # the final chain: walk back from the highest tip
    best = max((m.tip for m in miners.values()), key=lambda b: b["height"])
    main_chain = set()
    b = best
    while b:
        main_chain.add(b["hash"])
        b = blocks.get(b["parent"]) if b["parent"] else None
    found = {n: sum(1 for x in blocks.values() if x["miner"] == n) for n in RATE}
    stale = {n: sum(1 for x in blocks.values() if x["miner"] == n and x["hash"] not in main_chain) for n in RATE}
    print(f"delay={DELAY_S:.0f}s ({DELAY} ticks) tick={TICK_S:.4f}s blocks_on_main={best['height']}")
    for n in RATE:
        print(f"miner {n}: found={found[n]} stale={stale[n]} stale_rate={stale[n] / found[n]:.3f}")
    total_stale = sum(stale.values())
    print(f"all: found={sum(found.values())} stale={total_stale} stale_rate={total_stale / sum(found.values()):.3f}")
    json.dump({"tick_s": TICK_S, "delay_ticks": DELAY, "blocks": list(blocks.values()),
               "main": sorted(main_chain), "events": events},
              open(f"output/fork_{DELAY_S:.0f}s.json", "w"))


if __name__ == "__main__":
    main()
