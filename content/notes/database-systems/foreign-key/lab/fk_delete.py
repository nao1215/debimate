"""Time a parent DELETE with and without an index on the child FK column (PostgreSQL 17, measured).

members has 100,000 rows. orders(member_id REFERENCES members) gets N rows
whose member_id is drawn from 1..50,000, so members 50,001..100,000 have
no orders and can be deleted. For each N we delete one such member and
read "Execution Time" of EXPLAIN ANALYZE (the FK check runs as a trigger
inside it), inside BEGIN ... ROLLBACK so the table does not change.
Each point is the median of 21 deletes of different members, warm cache
(shared_buffers = 1GB, the tables fit in it).

Run: python3 fk_delete.py > fk_delete_output.txt   (needs docker)
"""

import re
import statistics
import subprocess

NAME = "note-foreign-key"
IMAGE = "postgres:17"
CHILD_ROWS = [10_000, 30_000, 100_000, 300_000, 1_000_000, 4_000_000]
REPEAT = 21


def sh(*args, check=True, stdin=None):
    return subprocess.run(args, check=check, capture_output=True, text=True, input=stdin).stdout


def psql(sql):
    return sh("docker", "exec", "-i", NAME, "psql", "-U", "postgres", "-qAt",
              "-v", "ON_ERROR_STOP=1", stdin=sql)


def median_delete_ms():
    times, trig = [], []
    for i in range(REPEAT + 1):
        out = psql("BEGIN;\n"
                   f"EXPLAIN (ANALYZE, COSTS OFF) DELETE FROM members WHERE id = {60_000 + i};\n"
                   "ROLLBACK;\n")
        if i == 0:  # warm-up
            continue
        times.append(float(re.search(r"Execution Time: ([\d.]+) ms", out).group(1)))
        trig.append(float(re.search(r"Trigger for constraint \S+: time=([\d.]+)", out).group(1)))
    return statistics.median(times), statistics.median(trig)


def main():
    sh("docker", "rm", "-f", NAME, check=False)
    sh("docker", "run", "-d", "--name", NAME, "-e", "POSTGRES_HOST_AUTH_METHOD=trust",
       IMAGE, "-c", "shared_buffers=1GB")
    try:
        # TCP answers only after the image has finished its init and restarted the server
        sh("sh", "-c", f"until docker exec {NAME} psql -h 127.0.0.1 -U postgres -qc 'SELECT 1' >/dev/null 2>&1; do sleep 0.5; done")
        print(psql("SELECT version()").split(" on ")[0])
        print("child_rows  index  delete_ms  fk_check_ms   scan of orders in the FK lookup")
        for n in CHILD_ROWS:
            psql("DROP TABLE IF EXISTS orders; DROP TABLE IF EXISTS members;\n"
                 "CREATE TABLE members (id bigint PRIMARY KEY, name text NOT NULL);\n"
                 "INSERT INTO members SELECT g, 'm' || g FROM generate_series(1, 100000) g;\n"
                 "CREATE TABLE orders (id bigint PRIMARY KEY,"
                 " member_id bigint NOT NULL REFERENCES members (id), amount int NOT NULL);\n"
                 "SELECT setseed(0.42);\n"
                 f"INSERT INTO orders SELECT g, 1 + floor(random() * 50000)::bigint, g % 1000"
                 f" FROM generate_series(1, {n}) g;\n"
                 "VACUUM ANALYZE;\n")
            for idx in ("no", "yes"):
                if idx == "yes":
                    psql("CREATE INDEX orders_member_id_idx ON orders (member_id); ANALYZE orders;")
                ms, trig = median_delete_ms()
                # the lookup the FK trigger runs, as a prepared statement with a parameter
                plan = psql("SET plan_cache_mode = force_generic_plan;"
                            "PREPARE q(bigint) AS SELECT 1 FROM ONLY orders x"
                            " WHERE member_id = $1 FOR KEY SHARE OF x;"
                            "EXPLAIN (COSTS OFF) EXECUTE q(60000);")
                plan = plan.strip().splitlines()[1].strip(' ->').split(" on ")[0].strip()
                print(f"{n:10d}  {idx:5s}  {ms:9.3f}  {trig:11.3f}   {plan}")
    finally:
        sh("docker", "rm", "-f", NAME, check=False)


if __name__ == "__main__":
    main()
