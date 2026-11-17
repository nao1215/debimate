"""Fetch one difficulty period (2,016 blocks) of mainnet block data from mempool.space.

Heights 973727..975743 (one block before the period, for the first time difference).
About 135 requests, one every 0.5 s. Saved to output/blocks.json.
"""
import json
import time
import urllib.request

API = "https://mempool.space/api/v1/blocks/"
FIRST, LAST = 973727, 975743
KEEP = ["id", "height", "version", "timestamp", "mediantime", "bits", "nonce",
        "tx_count", "size", "weight"]

blocks = {}
h = LAST
while h >= FIRST:
    with urllib.request.urlopen(API + str(h)) as r:
        page = json.load(r)
    for b in page:
        if FIRST <= b["height"] <= LAST:
            row = {k: b[k] for k in KEEP}
            ex = b.get("extras", {})
            row["header"] = ex.get("header")
            row["coinbaseRaw"] = ex.get("coinbaseRaw")
            row["pool"] = (ex.get("pool") or {}).get("name")
            row["firstSeen"] = ex.get("firstSeen")
            blocks[b["height"]] = row
    h = min(b["height"] for b in page) - 1
    time.sleep(0.5)

rows = [blocks[k] for k in sorted(blocks)]
json.dump(rows, open("output/blocks.json", "w"), indent=0)
print(len(rows), rows[0]["height"], rows[-1]["height"])
