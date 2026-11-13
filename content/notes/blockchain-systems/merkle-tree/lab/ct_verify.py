"""ct_fetch.py が保存した応答だけを使い、手元で包含証明と一貫性証明を検証する（通信しない）。"""
import base64, json, os
from merkle import leaf_hash, verify_inclusion, verify_consistency

load = lambda name: json.load(open(f"ct/{name}.json"))
b64 = base64.b64decode

sth = load("sth1")
size, signed_root = sth["tree_size"], b64(sth["sha256_root_hash"])
entry, proof = load("entry"), load("inclusion")
data = b64(entry["leaf_input"])
path = [b64(p) for p in proof["audit_path"]]

print(f"ログの件数        : {size:,}")
print(f"記録の位置        : {entry['index']:,}")
print(f"記録の大きさ      : {len(data):,} バイト")
print(f"包含証明          : {len(path)} 個 = {len(path) * 32:,} バイト")
print(f"葉のハッシュを全件: {size * 32 / 1e9:,.1f} GB")
print("検証              :", verify_inclusion(entry["index"], size, leaf_hash(data), path, signed_root))

# 記録の 1 ビットを反転する
bad = bytearray(data)
bad[len(bad) // 2] ^= 0x01
print("1 ビット反転       :", verify_inclusion(entry["index"], size, leaf_hash(bytes(bad)), path, signed_root))
# 同じ証明を隣の位置として出す
print("位置を 1 つずらす  :", verify_inclusion(entry["index"] + 1, size, leaf_hash(data), path, signed_root))

if os.path.exists("ct/cons_sth2.json"):
    a, b, cons = load("cons_sth1"), load("cons_sth2"), load("consistency")
    c = [b64(x) for x in cons["consistency"]]
    print(f"\nWyvern 2027h1     : {a['tree_size']:,} 件 → {b['tree_size']:,} 件"
          f"（{(b['timestamp'] - a['timestamp']) / 60000:.0f} 分後、{b['tree_size'] - a['tree_size']:,} 件増加）")
    print(f"一貫性証明        : {len(c)} 個 = {len(c) * 32:,} バイト")
    print("検証              :", verify_consistency(a["tree_size"], b["tree_size"],
                                                   b64(a["sha256_root_hash"]), b64(b["sha256_root_hash"]), c))
    bad_root = bytearray(b64(a["sha256_root_hash"]))
    bad_root[0] ^= 0x01
    print("前のルートを 1 ビット反転:", verify_consistency(a["tree_size"], b["tree_size"], bytes(bad_root),
                                                       b64(b["sha256_root_hash"]), c))
