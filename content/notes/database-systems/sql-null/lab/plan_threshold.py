"""既定の work_mem（4MB）のまま行数を増やし、NOT IN の計画が hashed SubPlan かを EXPLAIN で見る（実行はしない）。

実行: python3 plan_threshold.py → output/plan_threshold.txt
"""
import pathlib
import subprocess

HERE = pathlib.Path(__file__).resolve().parent
lines = []
for n in [100000, 200000, 250000, 300000, 500000, 1000000]:
    sql = f"""
    DROP TABLE IF EXISTS big; CREATE TABLE big (id INT PRIMARY KEY, referred_by INT);
    SELECT setseed(0.42);
    INSERT INTO big SELECT g, CASE WHEN g % 10 = 0 OR g = 1 THEN NULL
        ELSE (random() * (g - 1))::int + 1 END FROM generate_series(1, {n}) g;
    VACUUM ANALYZE big; SET max_parallel_workers_per_gather = 0;
    EXPLAIN (COSTS OFF) SELECT count(*) FROM big b WHERE b.id NOT IN
        (SELECT referred_by FROM big WHERE referred_by IS NOT NULL);
    """
    out = subprocess.run(["docker", "exec", "-i", "sqlnull-pg", "psql", "-U", "postgres", "-Atq"],
                         input=sql, capture_output=True, text=True, check=True).stdout
    filt = next(l.strip() for l in out.splitlines() if "Filter: (NOT" in l)
    lines.append(f"rows={n:>8}  work_mem=4MB  {filt}")
    print(lines[-1], flush=True)
(HERE / "output" / "plan_threshold.txt").write_text("\n".join(lines) + "\n")
