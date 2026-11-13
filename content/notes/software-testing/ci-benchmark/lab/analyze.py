"""Count everything the note states, from output/*.csv.

usage: python3 -I analyze.py > output/analysis.txt

The verdict rule is a simplified copy of himorime's latency comparison
(median, max_percent 10, confidence 0.95, percentile bootstrap). It leaves out
the max_cv and min_difference gates, which none of these jobs reached.
"""
import csv
import itertools
import random
import statistics as st
from collections import Counter, defaultdict
from pathlib import Path

OUT = Path(__file__).resolve().parent / "output"


def read(name):
    with (OUT / name).open() as f:
        return list(csv.DictReader(f))


def verdict(base, head, max_percent=10.0, conf=0.95, n=2000, seed=1):
    rnd = random.Random(seed)
    obs = (st.median(head) / st.median(base) - 1) * 100
    reg = imp = within = 0
    for _ in range(n):
        ch = (st.median(rnd.choices(head, k=len(head))) / st.median(rnd.choices(base, k=len(base))) - 1) * 100
        reg += ch > max_percent
        imp += ch < -max_percent
        within += -max_percent <= ch <= max_percent
    if obs > max_percent and reg / n >= conf:
        return "regression", obs
    if obs < -max_percent and imp / n >= conf:
        return "improved", obs
    if within / n >= conf:
        return "pass", obs
    return "inconclusive", obs


def main():
    jobs = {j["job"]: j for j in read("jobs.csv")}
    s = defaultdict(list)
    hf = {}
    for r in read("samples.csv"):
        if r["mode"] == "hyperfine":
            hf[(r["job"], r["side"])] = int(r["ns"])
        else:
            s[(r["job"], r["mode"], r["side"])].append(int(r["ns"]))
    for j in jobs.values():
        j["slowdown"] = int(j["slowdown"])
        j["base"], j["head"] = s[(j["job"], "interleaved", "base")], s[(j["job"], "interleaved", "head")]
        j["sbase"], j["shead"] = s[(j["job"], "sequential", "base")], s[(j["job"], "sequential", "head")]
    J = list(jobs.values())
    aa = [j for j in J if j["slowdown"] == 0]
    slows = sorted({j["slowdown"] for j in J})
    print(f"noise jobs: {len(J)} (A/A {len(aa)}), runner images: {sorted({j['image'] for j in J})}, "
          f"himorime {sorted({j['himorime'] for j in J})}")

    print("\n## CPU models (base median of the interleaved runs, ms)")
    by = defaultdict(list)
    for j in J:
        by[j["cpu"]].append(j)
    for cpu, js in sorted(by.items(), key=lambda kv: -len(kv[1])):
        med = sorted(st.median(j["base"]) / 1e6 for j in js)
        cv = [st.stdev(j["base"]) / st.mean(j["base"]) * 100 for j in js]
        print(f"  {cpu:46} jobs {len(js):2}  median {st.median(med):6.1f}  min {med[0]:6.1f}  max {med[-1]:6.1f}  "
              f"in-job cv median {st.median(cv):.2f}%")
    allm = [st.median(j["base"]) / 1e6 for j in J]
    print(f"  all jobs: min {min(allm):.1f} max {max(allm):.1f} (x{max(allm) / min(allm):.2f})")
    allcv = [st.stdev(j["base"]) / st.mean(j["base"]) * 100 for j in J]
    print(f"  in-job cv of base: median {st.median(allcv):.2f}%  max {max(allcv):.2f}%")
    for cpu in by:
        med = sorted(st.median(j["base"]) / 1e6 for j in by[cpu])
        groups = Counter(round(x / 5) * 5 for x in med)
        if len(groups) > 1:
            print(f"  {cpu}: base medians rounded to 5 ms -> {dict(sorted(groups.items()))}")

    print("\n## himorime compare in the same job (latency)")
    for sd in slows:
        js = [j for j in J if j["slowdown"] == sd]
        ch = [float(j["latency_change"]) for j in js]
        print(f"  slowdown {sd:2}%: jobs {len(js):2}  {dict(Counter(j['latency_verdict'] for j in js))}  "
              f"change median {st.median(ch):+.2f}% min {min(ch):+.2f} max {max(ch):+.2f}")
    mism = [j["job"] for j in J if verdict(j["base"], j["head"])[0] != j["latency_verdict"]]
    print(f"  recomputed from the samples: {len(J) - len(mism)}/{len(J)} verdicts agree {mism}")

    print("\n## sequential in the same job (all base runs, then all head runs)")
    for sd in slows:
        js = [j for j in J if j["slowdown"] == sd]
        ch = [(st.median(j["shead"]) / st.median(j["sbase"]) - 1) * 100 for j in js]
        print(f"  slowdown {sd:2}%: {dict(Counter(verdict(j['sbase'], j['shead'])[0] for j in js))}  "
              f"change median {st.median(ch):+.2f}% min {min(ch):+.2f} max {max(ch):+.2f}")

    print("\n## hyperfine on the same runner")
    gap = [(hf[(j["job"], "head")] / hf[(j["job"], "base")] - 1) * 100 - float(j["latency_change"]) for j in J]
    print(f"  change by hyperfine minus change by himorime (points): median {st.median(gap):+.2f} "
          f"min {min(gap):+.2f} max {max(gap):+.2f}")

    print("\n## A/A across jobs: the base of one job against the base of another")
    res = {"same CPU model": Counter(), "different CPU model": Counter()}
    for a, b in itertools.permutations(aa, 2):
        res["same CPU model" if a["cpu"] == b["cpu"] else "different CPU model"][verdict(a["base"], b["base"], n=500)[0]] += 1
    for k, v in res.items():
        tot = sum(v.values())
        print(f"  {k}: pairs {tot}  " + "  ".join(f"{x} {v[x]} ({v[x] / tot:.1%})" for x in sorted(v)))

    print("\n## compare with a stored result (github-action-benchmark style)")
    print("  alert when the new median exceeds a stored median of another A/A job by the threshold")
    for t in (5, 10, 20, 50, 100):
        pairs = list(itertools.permutations(aa, 2))
        fa = sum(st.median(b["base"]) > st.median(a["base"]) * (1 + t / 100) for a, b in pairs) / len(pairs)
        row = [f"threshold {t:3}%: false alarm {fa:6.1%}"]
        for sd in (5, 10, 20):
            det = [st.median(h["head"]) > st.median(a["base"]) * (1 + t / 100) for h in J if h["slowdown"] == sd for a in aa]
            row.append(f"caught {sd:2}%: {sum(det) / len(det):6.1%}")
        print("  " + "  ".join(row))
    for sd in (5, 10, 12, 15, 20):
        js = [j for j in J if j["slowdown"] == sd]
        print(f"  same job, himorime, slowdown {sd:2}%: caught {sum(j['latency_verdict'] == 'regression' for j in js)}/{len(js)}")
    print(f"  same job, himorime, A/A: false alarm {sum(j['latency_verdict'] == 'regression' for j in aa)}/{len(aa)}")

    print("\n## within a job (A/A, interleaved base, 20 runs in order)")
    half = [(st.median(j["base"][10:]) / st.median(j["base"][:10]) - 1) * 100 for j in aa]
    spikes = [j["job"] for j in aa if max(j["base"]) > st.median(j["base"]) * 1.10]
    print(f"  second half vs first half: median {st.median(half):+.2f}% min {min(half):+.2f} max {max(half):+.2f}")
    print(f"  jobs with a run over 10% above the job's median: {len(spikes)}/{len(aa)} {spikes}")

    print("\n## instructions (cachegrind) and time (hyperfine) on the same runners")
    ins = read("instructions.csv")
    print(f"  jobs {len(ins)}; perf: {sorted({r['perf'] for r in ins})}")
    base_ir = [int(r[f"base_irefs_{n}"]) for r in ins for n in (1, 2, 3)]
    times = [float(r["base_time_ms"]) for r in ins]
    print(f"  base instructions: min {min(base_ir):,} max {max(base_ir):,} (spread {(max(base_ir) / min(base_ir) - 1) * 100:.3f}%)")
    print(f"  base time: min {min(times):.1f} ms max {max(times):.1f} ms (x{max(times) / min(times):.2f})")
    byc = defaultdict(list)
    for r in ins:
        byc[r["cpu"]].append(r)
    for cpu, rs in sorted(byc.items(), key=lambda kv: -len(kv[1])):
        ir = [int(r[f"base_irefs_{n}"]) for r in rs for n in (1, 2, 3)]
        print(f"  {cpu:46} jobs {len(rs):2}  instructions median {st.median(ir):,.0f}  time median "
              f"{st.median(float(r['base_time_ms']) for r in rs):.1f} ms")
    for sd in sorted({int(r["slowdown"]) for r in ins}):
        rs = [r for r in ins if int(r["slowdown"]) == sd]
        ic = [(st.median(int(r[f"head_irefs_{n}"]) for n in (1, 2, 3)) /
               st.median(int(r[f"base_irefs_{n}"]) for n in (1, 2, 3)) - 1) * 100 for r in rs]
        tc = [(float(r["head_time_ms"]) / float(r["base_time_ms"]) - 1) * 100 for r in rs]
        print(f"  slowdown {sd}%: instructions {min(ic):+.3f}..{max(ic):+.3f}%  time {min(tc):+.2f}..{max(tc):+.2f}%")


main()
