"""Turn the artifacts of ci-bench-noise into the CSV files of output/.

usage: python3 -I extract.py NOISE_DIR [NOISE_DIR...] --instr INSTR_DIR [--desktop DESKTOP_DIR]

NOISE_DIR holds the noise-* folders of one run of noise.yml, and INSTR_DIR the
instr-* folders of one run of instructions.yml (gh run download <id>).

- output/jobs.csv: one row per noise job (CPU, himorime's verdict and change).
- output/samples.csv: every latency sample, in the order it was measured.
  mode is interleaved (himorime compare) or sequential (himorime run twice),
  or hyperfine (base and head medians only, as run 0).
- output/instructions.csv: one row per instr job (instructions and time).
- output/desktop_samples.csv: with --desktop, the latency samples of
  himorime compare run on the author's desktop, one JSON report per
  comparison named s<slowdown>_r<n>.json, in round order.
"""
import csv
import json
import re
import statistics as st
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent / "output"


def main():
    args = sys.argv[1:]
    desktop = None
    if "--desktop" in args:
        k = args.index("--desktop")
        desktop = Path(args[k + 1])
        args = args[:k] + args[k + 2:]
    i = args.index("--instr")
    noise_dirs, instr_dir = args[:i], Path(args[i + 1])

    jobs, samples = [], []
    for d in noise_dirs:
        for p in sorted(Path(d).glob("noise-*")):
            m = json.loads((p / "machine.json").read_text())
            r = json.loads((p / "interleaved.json").read_text())
            c = r["suites"][0]["benchmarks"][0]["commands"][0]
            lat = c["comparisons"]["latency"]
            job = p.name.removeprefix("noise-")
            jobs.append({
                "job": job, "slowdown": int(m["slowdown"]), "cpu": m["cpu_model"],
                "image": m["image"].strip(), "started": m["started"], "seed": r["seed"],
                "himorime": r["himorime_version"], "result": c["result"],
                "latency_verdict": lat["verdict"], "latency_change": round(lat["change_percent"], 4),
            })
            for side in ("base", "head"):
                for n, v in enumerate(c[side]["metrics"]["latency"]["samples"], 1):
                    samples.append({"job": job, "mode": "interleaved", "side": side, "run": n, "ns": int(v)})
                for row in csv.DictReader((p / f"sequential-{side}.csv").open()):
                    if row["metric"] == "latency":
                        samples.append({"job": job, "mode": "sequential", "side": side,
                                        "run": int(row["run"]), "ns": int(float(row["value"]))})
            for res in json.loads((p / "hyperfine.json").read_text())["results"]:
                samples.append({"job": job, "mode": "hyperfine", "side": res["command"], "run": 0,
                                "ns": int(st.median(res["times"]) * 1e9)})
    write("jobs.csv", jobs)
    write("samples.csv", samples)

    rows = []
    for p in sorted(instr_dir.glob("instr-*")):
        m = json.loads((p / "machine.json").read_text())
        hf = {x["command"]: st.median(x["times"]) for x in json.loads((p / "hyperfine.json").read_text())["results"]}
        row = {"job": p.name.removeprefix("instr-"), "slowdown": int(m["slowdown"]), "cpu": m["cpu_model"],
               "avx512f": m["avx512f"], "perf": (p / "perf-base-1.err").read_text().strip().splitlines()[-2:]}
        row["perf"] = " / ".join(row["perf"])
        for side in ("base", "head"):
            for n in (1, 2, 3):
                text = (p / f"cg-{side}-{n}.txt").read_text()
                row[f"{side}_irefs_{n}"] = int(re.search(r"I\s+refs:\s+([\d,]+)", text).group(1).replace(",", ""))
            row[f"{side}_time_ms"] = round(hf[side] * 1e3, 3)
        rows.append(row)
    write("instructions.csv", rows)

    if desktop:
        rows = []
        for p in sorted(desktop.glob("s*_r*.json")):
            r = json.loads(p.read_text())
            c = r["suites"][0]["benchmarks"][0]["commands"][0]
            for side in ("base", "head"):
                for n, v in enumerate(c[side]["metrics"]["latency"]["samples"], 1):
                    rows.append({"job": p.stem, "slowdown": int(p.stem[1:p.stem.index("_")]),
                                 "cpu": r["environment"]["cpu_model"], "verdict": c["comparisons"]["latency"]["verdict"],
                                 "side": side, "round": n, "ns": int(v)})
        write("desktop_samples.csv", rows)


def write(name, rows):
    OUT.mkdir(exist_ok=True)
    with (OUT / name).open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"{name}: {len(rows)} rows")


main()
