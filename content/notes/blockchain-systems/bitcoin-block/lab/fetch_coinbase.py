"""Coinbase transaction of block 973962 (mempool.space, 2 requests). Saved to output/coinbase_973962.json."""
import json
import time
import urllib.request

API = "https://mempool.space/api"
BLOCK = "0000000000000000000043f040c89ba38896d91391d0329c5f10f6aea2514425"
with urllib.request.urlopen(f"{API}/block/{BLOCK}/txid/0") as r:
    txid = r.read().decode()
time.sleep(0.5)
with urllib.request.urlopen(f"{API}/tx/{txid}") as r:
    tx = json.load(r)
json.dump(tx, open("output/coinbase_973962.json", "w"), indent=1)
for i, o in enumerate(tx["vout"]):
    print(i, o["value"], o["scriptpubkey_type"], o["scriptpubkey"][:20])
print("locktime", tx["locktime"], "sequence", hex(tx["vin"][0]["sequence"]), "witness", tx["vin"][0].get("witness"))
