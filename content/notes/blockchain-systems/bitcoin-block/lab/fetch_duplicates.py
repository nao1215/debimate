"""Coinbase txids of the 4 blocks behind BIP30's two exceptions (mempool.space, 8 requests).

Saved to output/duplicates.json.
"""
import json
import time
import urllib.request

API = "https://mempool.space/api"


def get(path):
    with urllib.request.urlopen(API + path) as r:
        return r.read().decode()


rows = []
for h in [91722, 91812, 91842, 91880]:
    block = get(f"/block-height/{h}")
    time.sleep(0.5)
    rows.append({"height": h, "block": block, "coinbase_txid": get(f"/block/{block}/txid/0")})
    time.sleep(0.5)
json.dump(rows, open("output/duplicates.json", "w"), indent=1)
for r in rows:
    print(r["height"], r["coinbase_txid"])
