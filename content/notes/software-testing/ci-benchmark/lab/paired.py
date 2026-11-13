"""Independent versus paired bootstrap on measured samples.

usage: python3 -I paired.py > output/paired.txt

himorime compare runs base and head once per round, in a random order, and
keeps the samples in round order, so base[i] and head[i] come from the same
round. himorime resamples the two sides independently. A paired bootstrap
resamples rounds instead, so a slow moment that hit both sides of a round
stays paired. This script judges the same samples both ways:

- independent: himorime's rule (median of each side, resampled separately)
- paired: resample round indices, median(head[idx]) / median(base[idx])
- ratio: resample round indices, median of head[i] / base[i]

for the GitHub Actions jobs in output/samples.csv and for himorime compare run
on the author's desktop (output/desktop_samples.csv).
Every rule uses confidence 0.95 and 2,000 resamples; max_percent varies.
"""
import csv
import random
import statistics as st
from collections import Counter, defaultdict
from pathlib import Path

OUT = Path(__file__).resolve().parent / "output"
N = 2000


def judge(changes, obs, maxp, conf=0.95):
    reg = sum(c > maxp for c in changes) / len(changes)
    imp = sum(c < -maxp for c in changes) / len(changes)
    within = sum(-maxp <= c <= maxp for c in changes) / len(changes)
    if obs > maxp and reg >= conf:
        return "regression"
    if obs < -maxp and imp >= conf:
        return "improved"
    if within >= conf:
        return "pass"
    return "inconclusive"


def resampled(base, head, method, seed):
    rnd = random.Random(seed)
    n = len(base)
    out = []
    for _ in range(N):
        if method == "independent":
            b = st.median(rnd.choices(base, k=n))
            h = st.median(rnd.choices(head, k=n))
            out.append((h / b - 1) * 100)
        else:
            idx = rnd.choices(range(n), k=n)
            if method == "paired":
                out.append((st.median(head[i] for i in idx) / st.median(base[i] for i in idx) - 1) * 100)
            else:
                out.append((st.median(head[i] / base[i] for i in idx) - 1) * 100)
    return out


def observed(base, head, method):
    if method == "ratio":
        return (st.median(h / b for b, h in zip(base, head)) - 1) * 100
    return (st.median(head) / st.median(base) - 1) * 100


def load_ci():
    s = defaultdict(list)
    for r in csv.DictReader((OUT / "samples.csv").open()):
        if r["mode"] == "interleaved":
            s[(r["job"], r["side"])].append((int(r["run"]), int(r["ns"])))
    jobs = []
    for j in csv.DictReader((OUT / "jobs.csv").open()):
        b = [v for _, v in sorted(s[(j["job"], "base")])]
        h = [v for _, v in sorted(s[(j["job"], "head")])]
        jobs.append((int(j["slowdown"]), b, h))
    return jobs


def load_desktop():
    s = defaultdict(list)
    sd = {}
    for r in csv.DictReader((OUT / "desktop_samples.csv").open()):
        s[(r["job"], r["side"])].append((int(r["round"]), int(r["ns"])))
        sd[r["job"]] = int(r["slowdown"])
    return [(sd[j], [v for _, v in sorted(s[(j, "base")])], [v for _, v in sorted(s[(j, "head")])]) for j in sorted(sd)]


def report(name, jobs):
    print(f"\n# {name}: {len(jobs)} comparisons")
    aa = [(b, h) for s, b, h in jobs if s == 0]
    cvs = [st.stdev(b) / st.mean(b) * 100 for _, b, _ in jobs]
    rcv = [st.stdev([y / x for x, y in zip(b, h)]) / st.mean([y / x for x, y in zip(b, h)]) * 100 for _, b, h in jobs]
    corr = [st.correlation(b, h) for b, h in aa if st.stdev(b) and st.stdev(h)]
    print(f"  base cv per comparison: median {st.median(cvs):.2f}%  max {max(cvs):.2f}%")
    print(f"  cv of the per-round ratio head/base: median {st.median(rcv):.2f}%  max {max(rcv):.2f}%")
    print(f"  A/A correlation of base[i] and head[i] (same round): median {st.median(corr):+.2f}  "
          f"min {min(corr):+.2f}  max {max(corr):+.2f}")
    slows = sorted({s for s, _, _ in jobs})
    for rounds in (20, 10):
        for maxp in (10, 3, 2):
            print(f"  rounds {rounds}, max_percent {maxp}%:")
            for method in ("independent", "paired", "ratio"):
                row = []
                for s in slows:
                    vs = Counter()
                    for k, (sd, b, h) in enumerate(jobs):
                        if sd != s:
                            continue
                        b, h = b[:rounds], h[:rounds]
                        vs[judge(resampled(b, h, method, k), observed(b, h, method), maxp)] += 1
                    tot = sum(vs.values())
                    row.append(f"{s:>2}%: reg {vs['regression']:>2}/{tot} inc {vs['inconclusive']:>2}")
                print(f"    {method:11} " + " | ".join(row))


def main():
    report("GitHub Actions (output/samples.csv)", load_ci())
    if (OUT / "desktop_samples.csv").exists():
        report("author's desktop (output/desktop_samples.csv)", load_desktop())


main()
