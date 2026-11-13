"""前のブロックのハッシュ値を持たせた列で、古いブロックを 1 か所書き換える。

実行: python3 hash_link.py
"""

import hashlib
import json


def block_hash(prev, txs):
    data = json.dumps({"prev": prev, "txs": txs}, sort_keys=True).encode()
    return hashlib.sha256(data).hexdigest()


def build(blocks):
    chain, prev = [], "0" * 64
    for txs in blocks:
        h = block_hash(prev, txs)
        chain.append({"prev": prev, "txs": txs, "hash": h})
        prev = h
    return chain


def broken_links(chain):
    """各ブロックが持つ prev と、手元で計算し直した前のブロックのハッシュ値を比べる。"""
    out = []
    for i in range(1, len(chain)):
        actual = block_hash(chain[i - 1]["prev"], chain[i - 1]["txs"])
        out.append((i, chain[i]["prev"] == actual))
    return out


chain = build([["alice -> bob 5"], ["bob -> carol 2"], ["carol -> dave 1"]])
for i, b in enumerate(chain):
    print(f"block {i}: prev={b['prev'][:8]} hash={b['hash'][:8]}")

chain[1]["txs"] = ["bob -> carol 200"]          # 中身だけ書き換え、prev と hash は残す
print("rewrite block 1:", chain[1]["txs"][0])
print("block 1 hash now:", block_hash(chain[1]["prev"], chain[1]["txs"])[:8])
for i, ok in broken_links(chain):
    print(f"link {i - 1} -> {i}:", "ok" if ok else "mismatch")
