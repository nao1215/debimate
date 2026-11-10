"""Pages touched and time of seq scan vs index scan by selectivity (PostgreSQL 17, measured).

Tables are the ones of orders_pg.sql: 1,000,000 orders, 100 per user_id
(user_id 1..10,000), orders_sorted stored in user_id order and
orders_random in random order, one index on user_id each.
The query is SELECT status FROM <table> WHERE user_id BETWEEN 1 AND k,
so the selectivity is k / 10,000. The plan is forced with enable_* and
parallel query is off. "pages" is shared hit + read in EXPLAIN BUFFERS
(a page touched twice counts twice). All tables fit in shared_buffers
(1GB) and are read once before measuring, so the times are warm-cache
times, median of 7 runs (EXPLAIN ANALYZE with TIMING OFF).

Run: python3 selectivity_pg.py > selectivity_pg_output.txt   (needs docker)
"""

import re
import statistics
import subprocess

NAME = "note-index-scan"
IMAGE = "postgres:17"
# number of user_ids matched, out of 10,000
KS = [1, 3, 10, 30, 100, 300, 1000, 3000, 10000]
RUNS = 7

SETUP = """
SELECT setseed(0.42);
CREATE TABLE orders_sorted AS
  SELECT g AS id, (g - 1) / 100 + 1 AS user_id, g % 1000 AS amount,
         (ARRAY['paid', 'new', 'sent'])[g % 3 + 1] AS status
  FROM generate_series(1, 1000000) AS g;
CREATE TABLE orders_random AS SELECT * FROM orders_sorted ORDER BY random();
CREATE INDEX orders_sorted_user_id_idx ON orders_sorted(user_id);
CREATE INDEX orders_random_user_id_idx ON orders_random(user_id);
VACUUM ANALYZE;
CREATE EXTENSION pg_prewarm;
SELECT pg_prewarm(c) FROM unnest(ARRAY['orders_sorted', 'orders_random',
  'orders_sorted_user_id_idx', 'orders_random_user_id_idx']) AS c;
"""

PLANS = {
    "seq": "SET enable_indexscan = off; SET enable_bitmapscan = off;",
    "index": "SET enable_seqscan = off; SET enable_bitmapscan = off;",
}


def sh(*args, check=True, stdin=None):
    return subprocess.run(args, check=check, capture_output=True, text=True, input=stdin).stdout


def psql(sql):
    return sh("docker", "exec", "-i", NAME, "psql", "-U", "postgres", "-qAt",
              "-v", "ON_ERROR_STOP=1", stdin=sql)


def measure(table, plan, k):
    sql = ("SET max_parallel_workers_per_gather = 0;" + PLANS[plan] +
           "EXPLAIN (ANALYZE, BUFFERS, COSTS OFF, TIMING OFF) "
           f"SELECT status FROM {table} WHERE user_id BETWEEN 1 AND {k};")
    times, pages, node = [], None, None
    for _ in range(RUNS):
        out = psql(sql)
        node = out.splitlines()[0].split(" using ")[0].split(" on ")[0].strip()
        buf = re.search(r"Buffers: shared ([^\n]+)", out).group(1)
        p = sum(int(v) for v in re.findall(r"(?:hit|read)=(\d+)", buf))
        assert pages in (None, p)
        pages = p
        times.append(float(re.search(r"Execution Time: ([\d.]+) ms", out).group(1)))
    return node, pages, statistics.median(times)


def main():
    sh("docker", "rm", "-f", NAME, check=False)
    sh("docker", "run", "-d", "--name", NAME, "-e", "POSTGRES_HOST_AUTH_METHOD=trust",
       IMAGE, "-c", "shared_buffers=1GB")
    try:
        # TCP answers only after the image has finished its init and restarted the server
        sh("sh", "-c", f"until docker exec {NAME} psql -h 127.0.0.1 -U postgres -qc 'SELECT 1' >/dev/null 2>&1; do sleep 0.5; done")
        psql(SETUP)
        print(psql("SELECT version()").split(" on ")[0])
        print("table pages:", psql("SELECT relpages FROM pg_class WHERE relname = 'orders_sorted'").strip())
        for row in psql("SELECT tablename, round(correlation::numeric, 3) FROM pg_stats"
                        " WHERE attname = 'user_id' AND tablename LIKE 'orders_%'"
                        " ORDER BY tablename").split():
            print("correlation", row.replace("|", " "))
        print("table          plan   selectivity(%)  rows     pages  time_ms   node")
        for table in ("orders_sorted", "orders_random"):
            for plan in ("seq", "index"):
                for k in KS:
                    node, pages, ms = measure(table, plan, k)
                    print(f"{table:13s}  {plan:5s}  {100 * k / 10000:14.2f}  {k * 100:7d}  "
                          f"{pages:7d}  {ms:8.2f}   {node}")
    finally:
        sh("docker", "rm", "-f", NAME, check=False)


if __name__ == "__main__":
    main()
