"""Minimal LSM-tree: compare write, read and space amplification per compaction style."""
import bisect
import hashlib
import json
import pathlib
import random

TOMBSTONE = None       # a delete is stored as this marker
MEMTABLE_LIMIT = 1000  # entries per flush
FANIN = 4              # tiered: runs merged at once / leveled: L0 files before compaction
RATIO = 10             # leveled: each level holds 10 times more than the previous one


class Bloom:
    """Bloom filter with about 10 bits per key."""

    def __init__(self, keys, bits_per_key=10, k=7):
        self.m, self.k = max(64, len(keys) * bits_per_key), k
        self.bits = bytearray(self.m // 8 + 1)
        for key in keys:
            for p in self._probes(key):
                self.bits[p // 8] |= 1 << (p % 8)

    def _probes(self, key):
        d = hashlib.blake2b(key.encode(), digest_size=16).digest()
        h1, h2 = int.from_bytes(d[:8]), int.from_bytes(d[8:]) | 1
        return [(h1 + i * h2) % self.m for i in range(self.k)]

    def may_contain(self, key):
        return all(self.bits[p // 8] >> (p % 8) & 1 for p in self._probes(key))


class SSTable:
    """Immutable sorted run of (key, value) pairs."""

    def __init__(self, items):
        self.keys = [k for k, _ in items]
        self.values = [v for _, v in items]
        self.bloom = Bloom(self.keys)

    def get(self, key):
        i = bisect.bisect_left(self.keys, key)
        if i < len(self.keys) and self.keys[i] == key:
            return True, self.values[i]
        return False, None


class LSM:
    def __init__(self, style):
        self.style = style        # "leveled", "tiered" or "none"
        self.memtable = {}
        self.levels = [[]]        # levels[i] = SSTables, newest first
        self.user_writes = 0      # entries written by the user
        self.disk_writes = 0      # entries written by flush and compaction

    def put(self, key, value):
        self.user_writes += 1
        self.memtable[key] = value
        if len(self.memtable) >= MEMTABLE_LIMIT:
            self.flush()

    def delete(self, key):
        self.put(key, TOMBSTONE)  # deleting is appending a marker

    def flush(self):
        self.levels[0].insert(0, self._write(self.memtable.items()))
        self.memtable = {}
        self.compact()

    def _write(self, items):
        self.disk_writes += len(items)
        return SSTable(sorted(items))

    def _merge(self, runs, bottom):
        merged = {}
        for run in reversed(runs):  # oldest first, newer values overwrite
            merged.update(zip(run.keys, run.values))
        if bottom:  # nothing older remains below, so markers can go
            merged = {k: v for k, v in merged.items() if v is not TOMBSTONE}
        return self._write(merged.items())

    def _target(self, level):
        if self.style == "tiered" or level == 0:
            return len(self.levels[level]) >= FANIN
        size = sum(len(r.keys) for r in self.levels[level])
        return size > MEMTABLE_LIMIT * RATIO ** level

    def compact(self):
        if self.style == "none":
            return
        level = 0
        while level < len(self.levels):
            if not self._target(level):
                level += 1
                continue
            if level + 1 == len(self.levels):
                self.levels.append([])
            bottom = not any(self.levels[level + 2:])
            if self.style == "tiered":  # merge runs of one tier, push down
                bottom = bottom and not self.levels[level + 1]
                out = self._merge(self.levels[level], bottom)
                self.levels[level + 1].insert(0, out)
            else:                       # merge into the single run below
                runs = self.levels[level] + self.levels[level + 1]
                self.levels[level + 1] = [self._merge(runs, bottom)]
            self.levels[level] = []

    def get(self, key):
        """Return (value, SSTables visited, SSTables read after the Bloom filter)."""
        if key in self.memtable:
            return self.memtable[key], 0, 0
        visited = reads = 0
        for run in (r for level in self.levels for r in level):
            visited += 1
            if not run.bloom.may_contain(key):
                continue
            reads += 1
            found, value = run.get(key)
            if found:
                return value, visited, reads
        return TOMBSTONE, visited, reads

    def compact_all(self):
        """Merge every SSTable into one; tombstones and old values disappear."""
        if self.memtable:
            self.flush()
        runs = [r for level in self.levels for r in level]
        self.levels = [[], [self._merge(runs, bottom=True)]]

    def stored(self):
        return sum(len(r.keys) for level in self.levels for r in level)

    def runs(self):
        return sum(len(level) for level in self.levels)


def run(style, seed=1):
    rng = random.Random(seed)
    keys = [f"user{i:05d}" for i in range(20_000)]
    db, live, timeline = LSM(style), set(), []
    ops = [("put", rng.choice(keys)) for _ in range(100_000)]
    ops += [("delete", k) for k in rng.sample(keys, 10_000)]
    loaded = None
    for n, (op, key) in enumerate(ops, 1):
        if op == "put":
            db.put(key, "v" * 100)
            live.add(key)
        else:
            db.delete(key)
            live.discard(key)
        if n % 1000 == 0:
            timeline.append((n, db.stored(), db.runs(), len(live)))
        if n == 100_000:  # end of the put phase, before any delete
            loaded = db.stored() / len(live)
    gets = [db.get(rng.choice(keys)) for _ in range(20_000)]
    result = {
        "style": style,
        "write_amp": db.disk_writes / db.user_writes,
        "visited": sum(g[1] for g in gets) / len(gets),
        "read_amp": sum(g[2] for g in gets) / len(gets),
        "space_amp_loaded": loaded,
        "space_amp": db.stored() / len(live),
        "runs": db.runs(),
        "stored": db.stored(),
        "live": len(live),
        "timeline": timeline,
    }
    db.compact_all()
    result["stored_after_full"] = db.stored()
    return result


if __name__ == "__main__":
    results = [run(s) for s in ("leveled", "tiered", "none")]
    print("style   write visited read space(load) space(end) runs stored  live full")
    for r in results:
        print(f"{r['style']:<7} {r['write_amp']:5.2f} {r['visited']:7.2f} "
              f"{r['read_amp']:4.2f} {r['space_amp_loaded']:11.2f} "
              f"{r['space_amp']:10.2f} {r['runs']:4d} {r['stored']:6d} "
              f"{r['live']:5d} {r['stored_after_full']:5d}")
    out = pathlib.Path(__file__).with_name("results.json")
    out.write_text(json.dumps(results))
