#!/usr/bin/env bash
# 実験 2 の前半: 1742eca の設計（touched）から、モデルベースドテスト用の trace を 500 本書き出す。
set -u
cd "$(dirname "$0")"
rm -rf traces && mkdir -p traces output
quint run save.qnt --main=touched --mbt --max-steps=6 --max-samples=500 --n-traces=500 --seed=7 \
  --out-itf='traces/t{seq}.itf.json' 2>&1 | tail -3
python3 - <<'PY' | tee output/exp2_traces.txt
import collections, glob, json
seen = collections.Counter()
for p in glob.glob("traces/*.itf.json"):
    states = json.load(open(p))["states"]
    steps = tuple((s["touched::saveproto::event"]["step"], s["touched::saveproto::event"]["target"],
                   s["touched::saveproto::event"]["outcome"]) for s in states if s["mbt::actionTaken"] != "done")
    last = states[-1]
    disk = ",".join(f"{k}={v}" for k, v in last["touched::saveproto::disk"]["#map"])
    seen[steps + (disk, tuple(last["touched::saveproto::reported"]["#set"]))] += 1
print(f"traces: {sum(seen.values())}, distinct behaviors: {len(seen)}")
for k, n in sorted(seen.items(), key=lambda kv: -kv[1]):
    print(n, " -> ".join(f"{s}:{t}:{o}" for s, t, o in k[1:-2]), "| disk " + k[-2], "| reported=" + ",".join(k[-1]))
PY
