"""PostgreSQL で、NOT IN と NOT EXISTS の実行時間を行数と work_mem を変えて測る。

前提: docker の sqlnull-pg（postgres:18）が動いている。
実行: python3 perf.py  → output/perf.json と output/perf_plans.txt
"""
import json
import pathlib
import re
import subprocess

HERE = pathlib.Path(__file__).resolve().parent
NOT_IN = ("SELECT count(*) FROM big b WHERE b.id NOT IN "
          "(SELECT referred_by FROM big WHERE referred_by IS NOT NULL)")
NOT_EXISTS = ("SELECT count(*) FROM big b WHERE NOT EXISTS "
              "(SELECT 1 FROM big r WHERE r.referred_by = b.id)")


def psql(sql):
    p = subprocess.run(["docker", "exec", "-i", "sqlnull-pg", "psql", "-U", "postgres", "-At", "-q",
                        "-v", "ON_ERROR_STOP=1"], input=sql, capture_output=True, text=True, check=True)
    return p.stdout


def setup(n):
    # 会員 n 人。referred_by は 1 割が NULL、残りは自分より前の会員（乱数は種を固定）
    psql(f"""
    DROP TABLE IF EXISTS big;
    CREATE TABLE big (id INT PRIMARY KEY, referred_by INT);
    SELECT setseed(0.42);
    INSERT INTO big
    SELECT g, CASE WHEN g % 10 = 0 OR g = 1 THEN NULL ELSE (random() * (g - 1))::int + 1 END
    FROM generate_series(1, {n}) g;
    CREATE INDEX ON big (referred_by);
    VACUUM ANALYZE big;
    """)


def measure(sql, work_mem, reps=3):
    best, plan = None, ""
    for _ in range(reps):
        out = psql(f"SET max_parallel_workers_per_gather = 0; SET work_mem = '{work_mem}';\n"
                   f"EXPLAIN (ANALYZE, COSTS OFF, TIMING OFF) {sql};")
        ms = float(re.search(r"Execution Time: ([\d.]+) ms", out).group(1))
        best = ms if best is None else min(best, ms)
        plan = out
    return best, plan


def main():
    rows = []
    plans = []
    for n in [5000, 10000, 20000, 40000, 80000]:
        setup(n)
        for wm in ["4MB", "64kB"]:
            for label, sql in [("not_in", NOT_IN), ("not_exists", NOT_EXISTS)]:
                reps = 1 if (label == "not_in" and wm == "64kB" and n >= 40000) else 3
                ms, plan = measure(sql, wm, reps)
                rows.append({"rows": n, "work_mem": wm, "query": label, "ms": ms})
                print(n, wm, label, ms, flush=True)
                if n == 20000:
                    plans.append(f"-- rows={n} work_mem={wm} {label}\n{plan}")
    (HERE / "output" / "perf.json").write_text(json.dumps(rows, indent=1) + "\n")
    (HERE / "output" / "perf_plans.txt").write_text("\n".join(plans))


if __name__ == "__main__":
    main()
