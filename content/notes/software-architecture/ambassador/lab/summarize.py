# 出来事（events.jsonl）からの経過秒で、書き込みの結果が変わった所だけを並べる。
# 成功（ok）と返った書き込みのうち、最後の master に残らなかった数も数える
import json, sys
d = sys.argv[1]
ev = [json.loads(l) for l in open(f"{d}/events.jsonl")]
t0, tend = ev[0]["t"], ev[-1]["t"]
for e in ev:
    print(f"{e['t'] - t0:7.2f}s  event {e['event']}")
for mode in ["static", "sentinel", "ambassador", "ambassador_new"]:
    rows = [json.loads(l) for l in open(f"{d}/{mode}.jsonl")]
    rows = [r for r in rows if t0 - 1 <= r["t"] <= tend]
    kept = {int(x) for x in open(f"{d}/kept_{mode}.txt").read().split()}
    print(f"-- {mode}")
    prev, start, n, lost = None, None, 0, 0
    for r in rows + [{"t": tend, "res": "END", "seq": -1}]:
        if r["res"] != prev:
            if prev is not None:
                note = f"  うち消えた {lost}" if prev == "ok" and lost else ""
                print(f"{start - t0:7.2f}s〜{r['t'] - t0:6.2f}s  {prev:9s} x{n}{note}")
            prev, start, n, lost = r["res"], r["t"], 0, 0
        n += 1
        if r["res"] == "ok" and r["seq"] not in kept:
            lost += 1
