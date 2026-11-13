"""Read the trials of mine.py as time and measure the wait of a transaction.

65,536 trials (the mean for the 16-bit target) are read as 10 minutes, i.e.
the hash rate is fixed. A transaction is sent at a uniformly random moment,
and we measure how long it waits for the next block and how long the block
interval it fell into was.
"""
import bisect
import csv
import json
import random

MIN_PER_TRIAL = 10 / 65536

trials = [int(r["trials"]) for r in csv.DictReader(open("output/trials.csv"))]
gaps = [t * MIN_PER_TRIAL for t in trials]          # block intervals in minutes
ends = []
t = 0.0
for g in gaps:
    t += g
    ends.append(t)

random.seed(1)
waits, hit = [], []
for _ in range(100_000):
    sent = random.uniform(0, ends[-1])
    i = bisect.bisect_right(ends, sent)              # the next block after sending
    waits.append(ends[i] - sent)
    hit.append(gaps[i])

mean = lambda xs: sum(xs) / len(xs)
long = [g - 10 for g in gaps if g > 10]          # no memory: what is left after minute 10
summary = {
    "blocks": len(gaps),
    "mean_gap": round(mean(gaps), 1),
    "gap_over_20": round(sum(g > 20 for g in gaps) / len(gaps), 3),
    "gap_over_30": round(sum(g > 30 for g in gaps) / len(gaps), 3),
    "longest_gap": round(max(gaps), 1),
    "shortest_gap_s": round(min(gaps) * 60, 1),
    "mean_wait": round(mean(waits), 1),
    "mean_gap_containing_send": round(mean(hit), 1),
    "gaps_over_10": len(long),
    "mean_rest_after_10": round(mean(long), 1),
}
for k, v in summary.items():
    print(f"{k}: {v}")
json.dump(summary, open("output/wait.json", "w"), indent=1)
