"""公開の CT ログから、STH・1 件の記録・証明を取って ct/ に保存する。

使い方: python3 ct_fetch.py first   … Google Argon 2026h2 の STH・記録・包含証明と、DigiCert Wyvern 2027h1 の STH
        python3 ct_fetch.py second  … しばらく後の Wyvern 2027h1 の STH と、2 つの STH の間の一貫性証明
Argon 2026h2 は 2026 年下半期に期限が切れる証明書のログで、取った時点（2026-11-13）で件数が増えていなかった。
一貫性証明には、STH の件数が数秒ごとに増えていた Wyvern 2027h1 を使う。要求は 1 回の実行で 4 件まで。
検証は ct_verify.py がオフラインで行う。
"""
import base64, hashlib, json, sys, urllib.parse, urllib.request

LOG = "https://ct.googleapis.com/logs/us1/argon2026h2/ct/v1/"
LOG2 = "https://wyvern.ct.digicert.com/2027h1/ct/v1/"
INDEX = 3_000_000_000


def get(path, log=LOG, **q):
    url = log + path + ("?" + urllib.parse.urlencode(q) if q else "")
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.load(r)


def save(name, obj):
    with open(f"ct/{name}.json", "w") as f:
        json.dump(obj, f, indent=1)


if sys.argv[1] == "first":
    sth = get("get-sth")
    save("sth1", sth)
    entry = get("get-entries", start=INDEX, end=INDEX)["entries"][0]
    save("entry", {"index": INDEX, **entry})
    leaf = hashlib.sha256(b"\x00" + base64.b64decode(entry["leaf_input"])).digest()
    proof = get("get-proof-by-hash", hash=base64.b64encode(leaf).decode(), tree_size=sth["tree_size"])
    save("inclusion", proof)
    save("cons_sth1", get("get-sth", log=LOG2))
else:
    first = json.load(open("ct/cons_sth1.json"))
    second = get("get-sth", log=LOG2)
    save("cons_sth2", second)
    save("consistency", get("get-sth-consistency", log=LOG2,
                            first=first["tree_size"], second=second["tree_size"]))
