"""Analyze output/blocks.json (heights 973727..975743). Writes output/analyze.txt."""
import hashlib
import json
import statistics
import struct

rows = json.load(open("output/blocks.json"))
blocks = {b["height"]: b for b in rows}
period = rows[1:]                      # 973728..975743: one difficulty period
out = []


def p(*a):
    out.append(" ".join(str(x) for x in a))


def parse_header(hx):
    raw = bytes.fromhex(hx)
    version, = struct.unpack("<i", raw[0:4])
    prev = raw[4:36][::-1].hex()       # shown reversed, like explorers and RPC
    merkle = raw[36:68][::-1].hex()
    t, bits, nonce = struct.unpack("<III", raw[68:80])
    block_hash = hashlib.sha256(hashlib.sha256(raw).digest()).digest()
    return dict(size=len(raw), version=version, prev=prev, merkle=merkle,
                time=t, bits=bits, nonce=nonce,
                hash_raw=block_hash.hex(), hash_shown=block_hash[::-1].hex())


# 1. headers: hash from the 80 bytes, compared with the id from the API
ok = 0
for b in period:
    h = parse_header(b["header"])
    ok += (h["hash_shown"] == b["id"] and h["prev"] == blocks[b["height"] - 1]["id"]
           and h["time"] == b["timestamp"] and h["size"] == 80)
p("headers checked:", ok, "/", len(period))
ex = parse_header(blocks[973962]["header"])
p("973962 header:", json.dumps(ex, indent=1))

# 2. time compared with the parent block
diffs = [(b["height"], b["timestamp"] - blocks[b["height"] - 1]["timestamp"]) for b in period]
neg = [d for d in diffs if d[1] < 0]
p("time - parent time: n", len(diffs), "negative", len(neg),
  f"({100 * len(neg) / len(diffs):.1f}%)", "min", min(diffs, key=lambda d: d[1]),
  "max", max(diffs, key=lambda d: d[1]))

# 3. lower bound: median of the previous 11 times (MTP)
def mtp(height):
    return statistics.median(blocks[height - i]["timestamp"] for i in range(11))

checked = [b for b in period if b["height"] - 11 >= rows[0]["height"]]
same = sum(mtp(b["height"] - 1) == blocks[b["height"] - 1]["mediantime"] for b in checked)
p("our MTP == API mediantime:", same, "/", len(checked))
margin = [(b["height"], b["timestamp"] - blocks[b["height"] - 1]["mediantime"]) for b in period]
p("time - MTP of parent: min", min(margin, key=lambda d: d[1]),
  "median", statistics.median(m for _, m in margin))
p("negative blocks, time - MTP: min", min(m for h, m in margin if h in dict(neg)))

# 4. upper bound: the node's clock + 2 h; compare with when mempool.space first saw the block
seen = [(b["height"], b["timestamp"] - b["firstSeen"]) for b in period if b["firstSeen"]]
ahead = [s for s in seen if s[1] > 0]
p("time - firstSeen: n", len(seen), "ahead", len(ahead), f"({100 * len(ahead) / len(seen):.1f}%)",
  "max", max(seen, key=lambda s: s[1]), "min", min(seen, key=lambda s: s[1]),
  "median", statistics.median(s for _, s in seen))

# 5. nonce space and version rolling
difficulty = 148364561003867.4                 # at height 975000 (from the API)
p("expected hashes per block = difficulty * 2^32:", f"{difficulty * 2**32:.3e}",
  "nonce values:", 2**32, "ratio:", f"{difficulty:.3e}")
versions = {b["version"] for b in period}
p("distinct versions:", len(versions))
mask = 0
for v in versions:
    mask |= v ^ 0x20000000
p("bits that changed from 0x20000000:", hex(mask))
p("bit share:", json.dumps({i: sum((b["version"] >> i) & 1 for b in period) for i in range(32)}))

# 6. coinbase: height as the first push (BIP34)
def bip34(cb):
    raw = bytes.fromhex(cb)
    n = raw[0]
    return int.from_bytes(raw[1:1 + n], "little")

p("BIP34 height == height:", sum(bip34(b["coinbaseRaw"]) == b["height"] for b in period), "/", len(period))
cb = blocks[973962]["coinbaseRaw"]
p("973962 coinbase scriptSig:", cb[:8], "->", bip34(cb), "ascii:",
  "".join(chr(c) if 32 <= c < 127 else "." for c in bytes.fromhex(cb)))

# 7. size and weight
s = [b["size"] for b in period]
w = [b["weight"] for b in period]
p("size: median", statistics.median(s), "max", max(s), "min", min(s),
  "over 1,000,000:", sum(x > 1_000_000 for x in s))
p("weight: max", max(w), "over 3,990,000:", sum(x > 3_990_000 for x in w),
  "tx_count==1:", sum(b["tx_count"] == 1 for b in period))
open("output/analyze.txt", "w").write("\n".join(out) + "\n")
print("\n".join(out))
