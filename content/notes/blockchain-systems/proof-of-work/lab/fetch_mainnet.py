"""Fetch the mainnet data used in the note from mempool.space (3 requests).

Saved on 2026-11-13: output/tip.json (block 975640),
output/difficulty_adjustments.json ([timestamp, height, difficulty, ratio] per retarget),
and output/difficulty_adjustment.json (progress of the current 2,016-block period,
saved at 17:17 JST).
"""
import json
import urllib.request

API = "https://mempool.space/api"


def get(path):
    with urllib.request.urlopen(API + path) as r:
        return r.read().decode()


tip = json.loads(get("/block/" + get("/blocks/tip/hash")))
keys = ["id", "height", "timestamp", "bits", "nonce", "difficulty"]
json.dump({k: tip[k] for k in keys}, open("output/tip.json", "w"), indent=1)
open("output/difficulty_adjustments.json", "w").write(get("/v1/mining/difficulty-adjustments/all"))
open("output/difficulty_adjustment.json", "w").write(get("/v1/difficulty-adjustment"))
